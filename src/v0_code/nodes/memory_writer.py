"""Memory entries, version 2: code renders every fact, the model writes only the interpretation.

Code (logic/render.py) writes the material changes, numbers, what changed, co-movement, trajectory, caveats,
diary quotes and dates. The model gets those sections as plain text and returns three things per window:
  headline         one sentence
  what_stood_out   3-5 short sentences: what matters and how things moved together
  notable_reason   one sentence, only when code says the window is notable

`is_notable` is decided by code (anchors crossed on cleaned values, and not all of them questionable), never by the model.

Checks kept (they protect the few things the model still writes):
  1. numbers are grounded (within the V0 tolerance) in the rendered text
  2. no causal language
  3. every up/down claim agrees with the code's direction tag for each measure it names (and 'same way' / 'opposite way' claims match the tags)
  4. notable follows the code rule (forced, not asked)
  5. the model writes no dates          (code prints them)
  6. the model quotes no diary text     (code prints it verbatim)
The older validators (voice, refs, caveat scoping, flag names, ...) are kept in nodes/memory_llm.py and run only when
STRICT_VALIDATORS is switched on; a window failing twice is stored code-rendered with llm_status='rejected' — the numeric
record and every rendered fact survive any LLM failure.
"""

import asyncio
import json
import re
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from v0_code.logic.record_view import annotate
from v0_code.logic.render import direction_tags, render_text, render_window
from v0_code.nodes import memory_llm as legacy
from v0_code.nodes.memory_llm import (
    FORBIDDEN_RE, LABEL_THRESHOLDS, NUMBER_RE, _check_numbers, _llm, _call, _strip_non_metric_numbers,
)

# Legacy validators (voice, refs, caveat scoping, flag names, ...) behind one switch, default OFF. When on they run on
# the model's sentences in addition to the six checks above, minus the ones about content code now renders.
STRICT_VALIDATORS = False
LEGACY_SKIP_PREFIXES = ("co_movement", "material_change_omitted", "too_many_items", "evidence_ref_not_found", "quote_not_exact")

BATCH_SIZE = {"day": 8, "week": 4, "month": 2}  # the model reads ~0.7-1.3k tokens per window now and writes ~150
MAX_CONCURRENT_BATCH_CALLS = 6
MIN_SENTENCES, MAX_SENTENCES = 3, 5
MIN_SENTENCES_QUIET = 1


SYSTEM_PROMPT = """You write the interpretation for a personal health memory entry. The patient has diabetes. Write about HER.

Code has already written every fact: the things that deviated, the numbers, what changed, what moved together with glucose, the trajectory, the caveats and any diary entries. You receive those sections as plain text for each window. You do NOT repeat them. You write only:
  headline        one sentence (at most 30 words) saying what this window was like for her. If the window lists diary events of moderate or worse severity, the headline names their theme in plain words (for example "a family health scare"), without dates or quotes.
  what_stood_out  3 to 5 sentences (each at most 35 words): what matters most and how things moved together — for example, sleep, heart rate and medicines getting worse while glucose rose. Interpret and prioritise; do not recite the lists.
  notable_reason  one sentence in plain words saying what changed — ONLY if the window says "Notable: yes". If it says "Notable: no", return null.

RULES. Follow all of them.
1. Numbers. Every number must come from the text you were given. You may round it or give a range close to it (within about a tenth); never calculate, and never state a number that is not in the text.
2. Direction. DIRECTION TAGS give, for each key measure, whether it went up, down or stayed flat versus the previous window. Use an up or down word (rose, fell, higher, lower, up, down, more, fewer) ONLY for a measure whose tag says so, in the tag's direction; if a tag says flat, do not say it rose or fell. Make each direction claim about ONE measure ("sleep fell and steps rose", never "sleep and steps changed"). A claim that two measures moved "the same way" or "the opposite way" must match their tags (both must be up or down). "N fewer strained periods of the day" is an improvement; "N more" is worse. Do not use up or down words for patterns inside a day or between meals — describe those without them (for example "peaked after breakfast").
3. No dates and no quotes. Never write a date, a month name with a day, or a quotation. Refer to days by role ("the worst day", "midway through the week", "early on"). Paraphrase diary entries in your own words; never reuse four or more consecutive words from one.
4. No causes. Forbidden: cause, caused, causing, because, due to, led to, result, resulted, resulting, trigger, triggered, explains, attributable, driven by, responsible. Allowed: "coincided with", "alongside", "on the same days as", "moved the same way as", "moved the opposite way to".
5. No diagnosis, advice, recommendation or prediction.
6. Describe only what the text says. Never say where, how or by whom something was measured or happened (for example "supervised", "at a clinic", "at home", "fasting", "morning reading") unless the text says so. Never add a detail that is not there.
7. Do not mention readings that were removed, caveats, data gaps or the sections themselves — code states those. Do not use the words "anchor", "section", "record" or "code".
8. If the text says the window is not clinically reliable, keep every sentence tentative.
9. Return valid JSON only, matching the schema. No text before or after it."""

USER_TEMPLATE = """TIER: {tier}

WINDOWS (keyed by window_id):
{windows_text}

Return a single JSON object keyed by each window_id above (no other keys), each value exactly:
{{"headline": "string", "what_stood_out": ["sentence", "..."], "notable_reason": "string or null"}}"""


class ModelEntry(BaseModel):
    headline: str
    what_stood_out: list[str] = Field(default_factory=list)
    notable_reason: str | None = None


# ---- code decisions ----------------------------------------------------------------------------------------------------

def is_notable_by_code(record: dict) -> bool:
    """Forced false when anchors_crossed is empty or every crossing is questionable; true otherwise. Never asked of the model."""
    crossed = record.get("anchors_crossed") or []
    return bool(crossed) and not set(crossed) <= set(record.get("anchors_questionable") or [])


def check_notable(entry: dict, record: dict) -> list[str]:
    """The notability rule as a check on a finished entry (always satisfied by assemble(); kept as the guard)."""
    want = is_notable_by_code(record)
    fails = []
    if entry["is_notable"] != want:
        fails.append(f"is_notable_must_be_{str(want).lower()}")
    if not want and entry.get("notable_reason"):
        fails.append("notable_reason_must_be_null_when_not_notable")
    if want and not entry.get("notable_reason"):
        fails.append("notable_reason_missing_for_notable_window")
    return fails


STATUS_OK, STATUS_EARLY, STATUS_FALLBACK = "ok", "code_only_early", "code_only_fallback"


def is_early(record: dict) -> bool:
    """No flat band yet, so no direction can be stated: day/week windows whose glucose direction is 'insufficient_data'
    (the first 14 days of the record), and the first month checkpoint (no previous checkpoint). These get no model call."""
    if record["tier"] == "month":
        return (record.get("deltas") or {}).get("glucose_tir_pct") is None
    return (record.get("stream_direction_table") or {}).get("glucose") == "insufficient_data"


def code_headline_early(record: dict) -> str:
    return f"Not enough history yet to compare this {record['tier']} with her usual."


def code_headline_fallback(rendered: dict[str, list[str]]) -> str:
    """The top two material changes, straight from the code-rendered section; if nothing deviated, say so."""
    top = [x.rstrip(".") for x in rendered["material_changes"][:2]]
    return ("; ".join(top) + ".") if top else "Nothing deviated from her usual."


def assemble_code_only(record: dict, status: str) -> dict:
    """An entry with no model text at all: code-rendered sections, a code-made headline, and (when the window is notable) a
    code-made notable reason from the large-change lines. Used for early windows and when the model's reply was rejected."""
    rendered = render_window(record)
    notable = is_notable_by_code(record)
    reason = None
    if notable:
        lines = [x.rstrip(".") for x in rendered["material_changes"] if x.startswith("Large change")]
        reason = "; ".join(lines) + "." if lines else "A large change was found (see the rendered section)."
    return {
        "window_id": record["window_id"], "tier": record["tier"],
        "headline": code_headline_early(record) if status == STATUS_EARLY else code_headline_fallback(rendered),
        "what_stood_out": [], "notable_reason": reason, "is_notable": notable,
        "confidence": "low" if status == STATUS_EARLY else record.get("confidence", ""), "reliable": record.get("reliable"),
        "rendered": rendered, "source": status,
    }


def assemble(record: dict, model: ModelEntry | None) -> dict:
    """The stored memory: code-rendered sections plus the model's three fields. With no model output (LLM failed or was
    rejected) the entry still carries every rendered fact; headline/what_stood_out are simply empty."""
    notable = is_notable_by_code(record)
    return {
        "window_id": record["window_id"], "tier": record["tier"],
        "headline": model.headline if model else None,
        "what_stood_out": list(model.what_stood_out) if model else [],
        "notable_reason": (model.notable_reason if model and notable else None),
        "is_notable": notable, "confidence": record.get("confidence", ""), "reliable": record.get("reliable"),
        "rendered": render_window(record),
    }


# ---- checks -------------------------------------------------------------------------------------------------------------

_MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
DATE_RES = (
    re.compile(r"\b\d{4}-\d{2}(?:-\d{2})?\b"),                                                   # 2025-12-09, 2025-12
    re.compile(r"(?<![\d.])(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12]\d|3[01])(?:[-/]\d{2,4})?(?![\d%])(?!\.\d)"),  # 12-24, 12/24/2025
    re.compile(rf"\b{_MONTHS}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?\b", re.I),                           # Dec 9
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{_MONTHS}\b", re.I),                     # 9 December
    re.compile(r"\b(?:on|by|since|until)\s+the\s+\d{1,2}(?:st|nd|rd|th)\b", re.I),                 # on the 9th
)
QUOTE_MARKS_RE = re.compile(r"[\"“”]")


def find_date(text: str) -> str | None:
    for rx in DATE_RES:
        if m := rx.search(text):
            return m.group(0)
    return None


def _diary_texts(record: dict) -> list[str]:
    events = list(record.get("diary_events", [])) + list(record.get("events_in_window", []))
    return [e["text"] for e in events if e.get("text")]


def copies_diary_text(text: str, diary_texts: list[str], n: int = 4) -> str | None:
    """A run of n or more consecutive words shared with a diary entry (paraphrase is fine; copying is code's job)."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    grams = {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}
    for d in diary_texts:
        dw = re.findall(r"[a-z0-9']+", d.lower())
        for i in range(len(dw) - n + 1):
            if tuple(dw[i : i + n]) in grams:
                return " ".join(dw[i : i + n])
    return None


def _rendered_numbers(rendered: dict[str, list[str]]) -> list[float]:
    nums = []
    for lines in rendered.values():
        for line in lines:
            nums += [float(n) for n in NUMBER_RE.findall(_strip_non_metric_numbers(line))]
    return nums + [float(t) for t in LABEL_THRESHOLDS]


# --- direction: every up/down claim must agree with the code's tag for each measure it names ----------------------------------
_TERMS: list[tuple[str, str]] = [  # (regex, tag term) — longest / most specific first; a matched span is consumed
    (r"daily resting heart rate", "daily resting heart rate"),
    (r"(?:average )?(?:heart rate at rest|resting heart rate)", "resting heart rate"),
    (r"heart rate", "heart rate"),
    (r"post-meal (?:glucose )?peaks?|peaks? (?:glucose )?after meals|(?:after-)?meal peaks?", "post-meal glucose peak"),
    (r"time in range", "time in range"), (r"variability", "variability"), (r"\bGMI\b", "GMI"),
    (r"(?:average |mean )?glucose", "average glucose"),
    (r"\bsleep\b", "sleep"), (r"\bsteps?\b", "steps"), (r"sedentary(?: time)?", "sedentary time"),
    (r"(?:medication )?adherence|medicines taken|medications taken", "medication adherence"),
    (r"hydration", "hydration"), (r"screen time", "screen time"), (r"strained periods?|\bmood\b", "mood"),
]
_UP_RE = re.compile(r"\b(?:up|rose|rise[sn]?|rising|risen|higher|increas\w*|climb\w*|more(?! than)|gained|went up|jumped)\b", re.I)
_DOWN_RE = re.compile(r"\b(?:down|fell|fall(?:s|en|ing)?|drop\w*|lower\w*|declin\w*|decreas\w*|fewer|less(?! than)|shorter|dipped|went down)\b", re.I)
_REL = [
    ("same", re.compile(r"(?:in )?the same (?:way|direction) as|moving together with|moved together with|in line with|in step with", re.I)),
    ("opposite", re.compile(r"(?:in )?the opposite (?:way|direction)? ?(?:to|of|from)|opposite (?:to|of)|opposed to|inversely to|contrary to", re.I)),
]
_SPLIT = re.compile(r"[,;:()]|\b(?:and|while|but|whereas|although|though|with|which|where|compared|versus|vs|alongside|along with|coinciding with|coincided with|matching|mirroring)\b", re.I)
_FILLER = {"the", "her", "and", "both", "all", "average", "mean", "daily", "also", "overall", "a", "an", "of", "time", "were", "was", "is", "are"}


def _measures(segment: str) -> list[str]:
    """Tag terms named in a segment, in order of appearance (a matched span can't match a shorter term)."""
    hits: list[tuple[int, str]] = []
    work = segment
    for rx, term in _TERMS:
        for m in re.finditer(rx, work, re.I):
            hits.append((m.start(), term))
        work = re.sub(rx, lambda m: " " * len(m.group(0)), work, flags=re.I)
    return [t for _, t in sorted(hits)]


def _list_only(segment: str) -> bool:
    """A segment that is only measure names ('Sleep', 'steps'): it is a subject waiting for a direction word."""
    if re.search(r"\d", segment):
        return False  # it carries a value, so it is a statement of its own ("100% time in range")
    rest = segment
    for rx, _ in _TERMS:
        rest = re.sub(rx, " ", rest, flags=re.I)
    return {w for w in re.findall(r"[a-z]+", rest.lower())} <= _FILLER


_NEGATION = re.compile(r"\b(?:no|not|none|neither|nor|nothing|never|without|n't)\b", re.I)


def direction_failures(text: str, tags: list) -> list[str]:
    """Every up/down word must agree with the tag of the measure named in its own clause, and each direction claim names ONE
    measure. A 'same way as' / 'opposite way to' between measures must match their tags. A claim about a measure whose tag
    is flat (or has no data) fails. Ambiguous clauses (both an up and a down word) are not judged."""
    by_term: dict[str, list] = {}
    for t in tags:
        by_term.setdefault(t.term, []).append(t)
    fails: list[str] = []

    def tag_text(term: str) -> str:
        return " / ".join(t.text for t in by_term[term])

    # 1. relations ("moved the opposite way to glucose"): the objects are the measures right after the phrase; the subjects are the
    #    measures since the previous relation / strong boundary (; . while but), so one relation never judges another's subject
    found = sorted(((m.start(), m.end(), kind) for kind, rx in _REL for m in rx.finditer(text)), key=lambda x: x[0])
    spans: list[tuple[int, int]] = []
    boundary = 0
    for start, end, kind in found:
        tail = re.split(r"[,;.()]|\b(?:while|but|and)\b", text[end:], maxsplit=1)[0]
        strong = [m.end() for m in re.finditer(r"[;]|\.(?=\s)|\b(?:while|but|whereas)\b", text[boundary:start])]
        lo = boundary + (strong[-1] if strong else 0)
        objects = [o for o in _measures(tail) if o in by_term]
        subjects = [x for x in _measures(text[lo:start]) if x in by_term and x not in objects]
        negated = bool(_NEGATION.search(text[max(0, start - 40):start]))  # "no other measure moved together with glucose"
        if not negated:
            for sub in dict.fromkeys(subjects):
                for obj in objects:
                    ok = any(a.direction in ("up", "down") and b.direction in ("up", "down") and ((a.direction == b.direction) == (kind == "same"))
                             for a in by_term[sub] for b in by_term[obj])
                    if not ok:
                        fails.append(f"wrong_direction: the text says {sub} moved the {'same way as' if kind == 'same' else 'opposite way to'} {obj}, "
                                     f"but the tags are '{tag_text(sub)}' and '{tag_text(obj)}': {text!r}")
        spans.append((start, end + len(tail)))
        boundary = end + len(tail)
    work = text
    for start, end in reversed(spans):  # the relation and its object are not direction claims
        work = work[:start] + " " + work[end:]
    # 2. direction words, clause by clause, sentence by sentence
    for sentence in (x for x in re.split(r"[.!?]+(?=\s|$)", work) if x.strip()):  # not inside a decimal like 121.25
        pending: list[str] = []
        for seg in (x for x in _SPLIT.split(sentence) if x and x.strip()):
            ms = _measures(seg)
            up, down = bool(_UP_RE.search(seg)), bool(_DOWN_RE.search(seg))
            if not up and not down:
                if ms and _list_only(seg):
                    pending += ms
                else:
                    pending = []
                continue
            if up and down:
                pending = []
                continue
            fam = "up" if up else "down"
            # A direction word is a claim only about the measures named in its own clause (or a bare list just before it). With none,
            # it is not attached to the sentence's first measure: "slightly higher blood pressure" is not a claim about sleep.
            claim = list(dict.fromkeys(pending + ms))
            pending = []
            for term in claim:  # every measure named in the claim must match its own tag; the prompt asks for one measure per claim
                if term in by_term and not any(t.direction == fam for t in by_term[term]):
                    why = " (one direction word cannot cover several measures: make a separate claim for each)" if len(claim) > 1 else ""
                    fails.append(f"wrong_direction: the text says {term} went {fam}, but its tag is '{tag_text(term)}'{why}: {text!r}")
    return list(dict.fromkeys(fails))


def validate_light(model: ModelEntry, record: dict, rendered: dict[str, list[str]]) -> list[str]:
    """The kept checks. Returns specific failure strings; empty means valid."""
    fails: list[str] = []
    quiet = bool(record.get("quiet"))
    lo = MIN_SENTENCES_QUIET if quiet else MIN_SENTENCES
    if not lo <= len(model.what_stood_out) <= MAX_SENTENCES:
        fails.append(f"what_stood_out_count:{len(model.what_stood_out)} sentences, need {lo} to {MAX_SENTENCES}")
    if not model.headline.strip():
        fails.append("headline_empty")
    pool = _rendered_numbers(rendered)
    diary = _diary_texts(record)
    tags = direction_tags(record)
    texts = [("headline", model.headline)] + [(f"what_stood_out[{i}]", s) for i, s in enumerate(model.what_stood_out)]
    if model.notable_reason:
        texts.append(("notable_reason", model.notable_reason))
    for where, text in texts:
        if m := FORBIDDEN_RE.search(text):
            fails.append(f"forbidden_language:'{m.group(0)}' in {where}: {text!r}")
        if d := find_date(text):
            fails.append(f"date_written_by_model:'{d}' in {where} (code prints dates; refer to days by role): {text!r}")
        if QUOTE_MARKS_RE.search(text):
            fails.append(f"quote_marks_in_{where} (code prints diary text; paraphrase instead): {text!r}")
        if g := copies_diary_text(text, diary):
            fails.append(f"diary_text_copied:'{g}' in {where} (paraphrase, do not reuse four or more words): {text!r}")
        _check_numbers(text, [], pool, False, [], text, fails)
        fails += [f"{x} [{where}]" for x in direction_failures(text, tags)]
    if is_notable_by_code(record) and not (model.notable_reason or "").strip():
        fails.append("notable_reason_missing_for_notable_window (the window is notable: say in one sentence what changed)")
    return fails


def legacy_failures(model: ModelEntry, record: dict, prior: dict | None, window_id: str) -> list[str]:
    """The older validators, run on the model's sentences (STRICT_VALIDATORS). Content code now renders is not checked."""
    k = legacy.caps_for(record)["co_movement"]
    entry = legacy.MemoryEntry(window_id=window_id, tier=record["tier"], headline=model.headline,
                               key_observations=[legacy.Statement(statement=s) for s in model.what_stood_out],
                               is_notable=is_notable_by_code(record), notable_reason=model.notable_reason)
    resolver = legacy.Refs(annotate(record, k), annotate(prior, k) if prior else None, window_id)
    return [f for f in legacy.validate_entry(entry, record, prior, resolver, window_id) if not f.startswith(LEGACY_SKIP_PREFIXES)]


def validate_window(raw: dict, record: dict, prior: dict | None, window_id: str) -> tuple[ModelEntry | None, list[str]]:
    try:
        model = ModelEntry.model_validate(raw)
    except ValidationError as exc:
        return None, [f"schema_invalid:{exc}"]
    fails = validate_light(model, record, render_window(record))
    if STRICT_VALIDATORS:
        fails += legacy_failures(model, record, prior, window_id)
    return (model if not fails else None), fails


# ---- model calls ---------------------------------------------------------------------------------------------------------------

def window_text(w: dict) -> str:
    r = w["record"]
    head = (f"=== WINDOW {w['window_id']} ({r['tier']}) ===\nNotable: {'yes' if is_notable_by_code(r) else 'no'} | "
            f"Reliable: {'yes' if r.get('reliable') else 'no'} | Confidence: {r.get('confidence', '')}\n")
    return head + render_text(render_window(r))


def batch_prompt(tier: str, batch: list[dict]) -> str:
    return USER_TEMPLATE.format(tier=tier, windows_text="\n\n".join(window_text(w) for w in batch))


async def _attempt(llm, tier: str, batch: list[dict], extra: str = "") -> dict[str, dict]:
    raw = await _call(llm, SYSTEM_PROMPT, batch_prompt(tier, batch) + extra)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object keyed by window_id, got {type(raw).__name__}")
    return raw


def _result(w: dict, status: str, model: ModelEntry | None, raw: Any, failures: list[str], first_ok: bool | None, first_failures: list[str] | None = None) -> dict:
    """first_ok is None for a window that never reached the model (code_only_early)."""
    memory = assemble_code_only(w["record"], status) if status in (STATUS_EARLY, STATUS_FALLBACK) else assemble(w["record"], model)
    return {"window_id": w["window_id"], "llm_status": status, "memory": memory, "raw": json.dumps(raw) if raw is not None else None,
            "failures": failures, "first_attempt_ok": first_ok, "first_attempt_failures": first_failures}


async def process_batch(llm, tier: str, batch: list[dict], semaphore: asyncio.Semaphore) -> list[dict]:
    """A window that is still rejected after its one retry (or whose retry call fails) ends as 'code_only_fallback': the code-rendered
    entry with a code-made headline. No window ends with an empty memory. Early windows never reach the model."""
    results: dict[str, dict] = {}
    for w in batch:
        if is_early(w["record"]):
            results[w["window_id"]] = _result(w, STATUS_EARLY, None, None, [], None)
    order = [w["window_id"] for w in batch]
    batch = [w for w in batch if w["window_id"] not in results]
    by_id = {w["window_id"]: w for w in batch}
    if not batch:
        return [results[i] for i in order]
    ids = list(by_id)
    logger.info(f"memory_writer: calling LLM for {tier} batch {ids}")
    async with semaphore:
        try:
            raw_batch = await _attempt(llm, tier, batch)
        except Exception as exc:
            logger.warning(f"memory_writer: batch call failed ({tier}, {len(batch)} windows): {exc}")
            raw_batch = {}

    pending: list[tuple[str, list[str]]] = []
    for wid, w in by_id.items():
        if wid not in raw_batch:
            pending.append((wid, ["missing_from_batch_response"]))
            continue
        model, fails = validate_window(raw_batch[wid], w["record"], w.get("prior_record"), wid)
        if model is None:
            logger.info(f"memory_writer: {wid} failed validation, queuing individual retry: {fails}")
            pending.append((wid, fails))
        else:
            results[wid] = _result(w, "ok", model, raw_batch[wid], [], True)

    for wid, fails in pending:
        w = by_id[wid]
        extra = f"\n\nYour previous attempt for window_id {wid!r} failed validation for these specific reasons — fix them:\n{json.dumps(fails)}"
        async with semaphore:
            try:
                raw_retry = await _attempt(llm, tier, [w], extra)
            except Exception as exc:
                results[wid] = _result(w, STATUS_FALLBACK, None, None, [f"retry_call_failed:{exc}"], False, fails)
                continue
        if wid in raw_retry:
            model2, fails2 = validate_window(raw_retry[wid], w["record"], w.get("prior_record"), wid)
            if model2 is not None:
                results[wid] = _result(w, "ok", model2, raw_retry[wid], [], False, fails)
                continue
            logger.warning(f"memory_writer: {wid} rejected after retry: {fails2}")
            results[wid] = _result(w, STATUS_FALLBACK, None, raw_retry[wid], fails2, False, fails)
        else:
            results[wid] = _result(w, STATUS_FALLBACK, None, None, fails + ["missing_from_retry_response"], False, fails)
    return [results[i] for i in order]


async def run_llm_step(windows: list[dict]) -> list[dict]:
    """windows: [{'window_id','tier','record','prior_record'}]. Never raises: any LLM-side failure leaves the entry
    code-rendered (headline empty) with llm_status 'failed'/'rejected'."""
    try:
        llm = _llm()
    except Exception as exc:
        logger.error(f"memory_writer: could not start LLM client: {exc}")
        return [_result(w, STATUS_EARLY if is_early(w["record"]) else STATUS_FALLBACK, None, None, [str(exc)], None if is_early(w["record"]) else False) for w in windows]
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCH_CALLS)
    by_tier: dict[str, list[dict]] = {}
    for w in windows:
        by_tier.setdefault(w["tier"], []).append(w)
    batches = [(t, ws[i : i + BATCH_SIZE[t]]) for t, ws in by_tier.items() for i in range(0, len(ws), BATCH_SIZE[t])]
    out = await asyncio.gather(*(process_batch(llm, t, b, semaphore) for t, b in batches))
    return [r for batch in out for r in batch]
