"""Stage C: the gist (spec section 7). The only place Baseline Engine v2 calls a model, and the model writes only {headline, sentences}.

Everything else about a window (numbers, tags, material changes, is_notable, notable_reason, the code lines) is code. This module builds the
prompt from the gist view, calls the model (one call per window or several windows per call), runs the four output checks, retries a failed
window ONCE on its own with the failures appended, and stores either the gist (gist_ok / gist_retry_ok) or the code line
(code_line_fallback). Settings come from config `gist:`; the SDK itself never retries.
"""

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.gist_check import check_gist, finalize_headline, parse_batch, parse_json
from v0_code.baseline_v2.gist_view import build_gist_view, diary_texts, wording_tags
from v0_code.baseline_v2.render import fallback_code_line

SYSTEM_PROMPT = """You write a short plain-words summary of one time window in a person's health record. The person has diabetes.

You receive a GIST VIEW: a list of measures with direction and size, which measures moved with or against glucose, medicines missed, unusual statuses, diary entries, and data-quality notes. All numbers were removed on purpose. Code already stores every number.

Write:
1. headline: one sentence, at most 15 words.
2. sentences: 2 to 4 short sentences.

RULES. Follow all of them.
1. Do not write any digit, date, month name, count, or number word used as a count. Say "on a few days", "most days", "sharply", not figures.
2. Use only the facts in the GIST VIEW. Do not invent settings, reasons, or details. In particular, do not say where or how something was measured unless the view says so.
3. Direction words (up, down, higher, lower, rose, fell, more, fewer) must match the direction given for that measure, and intensity words must match its size: small = "a little" or "slightly"; moderate = "clearly" or "noticeably"; large = "sharply", "markedly" or "much". Never describe a measure whose direction is "not_enough_data".
4. One measure per direction claim. Do not write one direction word that covers two measures.
5. Describe relationships only as co-occurrence: "alongside", "while", "in a week when", "at the same time as". Never use: caused, because, due to, led to, resulted in, triggered, explains, driven by.
6. If the view contains diary entries, name the main theme in plain words in the headline (for example "a family member's hospitalization" or "a work trip"). Paraphrase. Do not quote the diary. Do not repeat numbers or dates from it.
7. Mention every missed medicine and every unusual status in the view that matters to the picture. Do not mention measures that are steady.
8. If the view says the window is not reliable, say that comparisons are tentative.
9. Do not give advice, diagnoses, or predictions.
10. Do not use these words: anchor, tag, stream, record, field, flag, window, tier, notable.
11. Refer to the person with the pronoun in the view.
12. The headline must cover the first item in TOP ITEMS; mention the others in the sentences.

Return only JSON: {"headline": "...", "sentences": ["...", "..."]}"""

USER_TEMPLATE = """TIER: {tier}
PRONOUN: {pronoun}

TIER GUIDANCE:
{tier_guidance}

GIST VIEW:
{gist_view_json}"""

TIER_GUIDANCE = {
    "day": "Say what stood out about this one day: what changed against the previous day, which medicine was missed, and what the diary says. Keep it to what is in the view.",
    "week": "Say what the week looked like overall and what moved with or against glucose. If there were diary entries, give the main theme. Do not list single days.",
    "month": ("Say how the period compares with the previous checkpoint and how the long-run picture looks. If a lab result and the glucose-based estimate differ, say they differ, in words only. "
              "Name any measure that has been non-normal on most days as a long-standing pattern."),
}

RETRY_ADDENDUM = """Your previous answer failed these checks: {failure_list}.
Rewrite it. Keep to the facts in the view. Do not use digits or dates. Make every direction word match the stated direction and size for its own measure."""

BATCH_NOTE = 'There are several GIST VIEWs below, keyed "1", "2", .... Return one JSON object with the same keys: {"1": {"headline": "...", "sentences": ["...", "..."]}, "2": {...}}.'


def needs_gist(row: dict) -> bool:
    """Early and quiet windows already carry a code line; only a window with no gist status yet (material changes, enough history) is sent to the model."""
    return row["gist"]["status"] is None


def user_prompt(cfg: Config, tier: str, views: dict[str, dict]) -> str:
    """One view is sent as itself; several are sent keyed "1", "2", ... (spec 7.5 batching)."""
    body = next(iter(views.values())) if len(views) == 1 else views
    text = USER_TEMPLATE.format(tier=tier, pronoun=cfg.pronoun, tier_guidance=TIER_GUIDANCE[tier], gist_view_json=json.dumps(body, indent=2, ensure_ascii=False))
    return text if len(views) == 1 else text.replace("GIST VIEW:", BATCH_NOTE + "\n\nGIST VIEWS:", 1)


def failure_text(failures: list[dict]) -> str:
    return "; ".join(f"{f['check']}: {f['detail']}" for f in failures)


def make_client(cfg: Config):
    """OpenRouter through the OpenAI SDK: timeout from config, SDK retries 0. The key is read from the environment and never printed."""
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv()
    return OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://openrouter.ai/api/v1", timeout=float(cfg.gist["timeout_seconds"]), max_retries=int(cfg.gist["sdk_retries"]))


def llm_call(client, cfg: Config, messages: list[dict]) -> tuple[str | None, dict, str | None]:
    """One model call. Returns (text, usage, error); usage always has wall seconds, and tokens (input, output, reasoning) when the call returned."""
    t0 = time.monotonic()
    try:
        resp = client.chat.completions.create(model=cfg.gist["model"], messages=messages, response_format={"type": "json_object"},
                                              extra_body={"reasoning": {"effort": cfg.gist["reasoning_effort"]}})
    except Exception as e:                                                   # timeout, 4xx/5xx, connection: one failed attempt
        return None, {"wall_seconds": round(time.monotonic() - t0, 2)}, f"{type(e).__name__}: {str(e)[:200]}"
    u = resp.usage
    details = getattr(u, "completion_tokens_details", None)
    usage = {"input_tokens": getattr(u, "prompt_tokens", None), "output_tokens": getattr(u, "completion_tokens", None),
             "reasoning_tokens": getattr(details, "reasoning_tokens", None) if details else None, "wall_seconds": round(time.monotonic() - t0, 2)}
    return resp.choices[0].message.content, usage, None


@dataclass
class WindowResult:
    window_id: str
    tier: str
    view: dict
    prompt: str                                    # the user prompt exactly as sent on the first attempt
    status: str = ""
    headline: str | None = None
    sentences: list[str] = field(default_factory=list)
    attempts: list[dict] = field(default_factory=list)   # {n, mode: single|batch, raw, usage, error, failures, passed}


def _validate(cfg: Config, row: dict, obj, parse_failures: list[dict], mode: str, warnings: list) -> list[dict]:
    """Code finishes the headline (capital letter, full stop) first, then the four checks run on the finished text."""
    if obj is None or parse_failures:
        return parse_failures
    if isinstance(obj.get("headline"), str):
        obj["headline"] = finalize_headline(obj["headline"])
    return check_gist(cfg, obj, wording_tags(cfg, row), diary_texts(row), sentence_mode=mode, warnings=warnings, reliable=bool(row["reliable"]))


def run_gist(cfg: Config, rows: list[dict], client, store=None, log=None, batch_size: dict | None = None, sentence_mode: str | None = None, usual_places_for=None) -> list[WindowResult]:
    """Run the gist for rows that need one (stored rows with facts). Saves each window as soon as it is decided (resumable). `log(dict)` is
    called with every call's prompt, raw answer, usage and failures."""
    sizes = batch_size or cfg.gist["batch_size"]
    mode = sentence_mode or cfg.gist.get("sentence_direction", "strict")           # strict | warn (sentence-level direction check only)
    workers = int(cfg.gist.get("concurrency", 1))
    save_lock = threading.Lock()
    results = {r["window_id"]: WindowResult(r["window_id"], r["tier"], build_gist_view(cfg, r, usual_places_for(r) if usual_places_for else None), "") for r in rows}
    by_id = {r["window_id"]: r for r in rows}

    def emit(entry: dict) -> None:
        if log:
            log(entry)

    def finish(wid: str) -> None:
        res, row = results[wid], by_id[wid]
        if not res.status:
            res.status = "code_line_fallback"
            res.headline, res.sentences = fallback_code_line(cfg, row), []
        if store:
            with save_lock:
                store.save_gist(wid, res.headline, res.sentences, res.status, json.dumps([a["raw"] for a in res.attempts]), [a["usage"] for a in res.attempts])

    # ---- first attempt: chunks of the configured batch size, per tier
    chunks = []
    for tier in ("day", "week", "month"):
        ids = [r["window_id"] for r in rows if r["tier"] == tier]
        n = int(sizes.get(tier, 1))
        chunks += [ids[i:i + n] for i in range(0, len(ids), n)]

    def first(chunk: list[str]) -> list[str]:
        tier = results[chunk[0]].tier
        keys = {str(i + 1): wid for i, wid in enumerate(chunk)}
        prompt = user_prompt(cfg, tier, {k: results[w].view for k, w in keys.items()})
        raw, usage, err = llm_call(client, cfg, [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}])
        if len(chunk) == 1:
            parsed = {"1": parse_json(raw) if raw is not None else (None, [])}
        else:
            parsed = parse_batch(raw, list(keys)) if raw is not None else {k: (None, []) for k in keys}
        failed = []
        for k, wid in keys.items():
            res, row = results[wid], by_id[wid]
            obj, pf = parsed[k]
            piece = json.dumps(obj, ensure_ascii=False) if obj else raw                  # this window's own part of the answer, before code finishes the headline
            warns: list = []
            failures = [{"check": "api_error", "detail": err}] if err else _validate(cfg, row, obj, pf, mode, warns)
            res.prompt = prompt if len(chunk) == 1 else user_prompt(cfg, tier, {"1": res.view})
            res.attempts.append({"n": 1, "mode": "single" if len(chunk) == 1 else f"batch of {len(chunk)}", "raw": raw if len(chunk) == 1 else piece,
                                 "usage": usage, "error": err, "failures": failures, "warnings": warns, "passed": not failures, "prompt_sent": prompt, "call_id": f"{tier}:{chunk[0]}"})
            emit({"window_id": wid, "attempt": 1, **{k2: res.attempts[-1][k2] for k2 in ("mode", "usage", "error", "failures", "warnings", "passed", "prompt_sent", "call_id")}, "raw": raw})
            if not failures:
                res.status, res.headline, res.sentences = "gist_ok", obj["headline"], obj["sentences"]
                finish(wid)
            else:
                failed.append(wid)
        return failed

    def retry(wid: str) -> None:
        res, row = results[wid], by_id[wid]
        prompt = user_prompt(cfg, res.tier, {"1": res.view})
        prev = res.attempts[-1]
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
        if prev["raw"]:
            msgs.append({"role": "assistant", "content": prev["raw"]})
        msgs.append({"role": "user", "content": RETRY_ADDENDUM.format(failure_list=failure_text(prev["failures"]))})
        raw, usage, err = llm_call(client, cfg, msgs)
        obj, pf = parse_json(raw) if raw is not None else (None, [])
        warns: list = []
        failures = [{"check": "api_error", "detail": err}] if err else _validate(cfg, row, obj, pf, mode, warns)
        res.attempts.append({"n": 2, "mode": "single", "raw": raw, "usage": usage, "error": err, "failures": failures, "warnings": warns, "passed": not failures,
                             "prompt_sent": msgs[-1]["content"], "call_id": f"retry:{wid}"})
        emit({"window_id": wid, "attempt": 2, "mode": "single", "usage": usage, "error": err, "failures": failures, "warnings": warns, "passed": not failures,
              "prompt_sent": msgs[-1]["content"], "raw": raw, "call_id": f"retry:{wid}"})
        if not failures:
            res.status, res.headline, res.sentences = "gist_retry_ok", obj["headline"], obj["sentences"]
        finish(wid)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        failed = [w for ws in pool.map(first, chunks) for w in ws]
        list(pool.map(retry, failed))
    return [results[r["window_id"]] for r in rows]
