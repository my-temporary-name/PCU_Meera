"""PI's text layer (pi_spec.md 8 and Appendix A as amended, prompt pp-v4). A memory's note has two parts: the association sentence(s), the P1 code text, which the model never writes or
edits; and an optional situations line, written by the model from the diary-only sentences of the mid-term entries. view -> one call -> parse -> cleanup -> checks -> one retry with the
failed checks -> if it fails twice the line is dropped (null) and the association stays. A retracted memory takes the code text and never reaches the model; a memory with no diary-only
sentence makes no call. Results are stored beside the memory version, never in it."""

import hashlib
import json
from dataclasses import dataclass

from v0_code.findings_engine import llm
from v0_code.pi_engine import text_check, text_view

SYSTEM_PROMPT = """You add one short line to a note in a person's health record. The note (which you do not write or change) says how two things have moved together in her history. Your line says what was going on in her life in the cases where it was recorded.

You receive a VIEW: the two things in words (for context only), the previous line (or null), and sentences taken from her diary context. All numbers were removed on purpose.

Write {"situations": "one sentence"} or {"situations": null}.

A situation is something that happened or was going on in her life: an event, an activity, an outing, a social occasion, a piece of news. Readings, doses, sleep, activity levels, fluid intake, moods, meals and anything about her numbers are NOT situations.

RULES. Follow all of them.
1. One sentence of at most 25 words, starting with "In the cases noted, the situations included" followed by a plain list of at most four situations.
2. Name only situations that the sentences state, in plain words, with no names of people, places or events. Use no words that are not in the sentences, except plain grammar words.
3. List noun phrases only (an event, outing, occasion, activity or piece of news), with no verbs and no past tense; never list feelings, states or habits.
4. If the sentences state no situation, return {"situations": null}. Null is a good answer.
5. Do not link anything and do not explain: no "moved together", "linked", "tended", "because", "led to", no advice, no prediction. Do not mention the two things of the note.
6. No words about time relative to now: this week, last week, recently, today, yesterday, tonight, currently, lately, so far, again, earlier, previous, prior, recent.
7. No digits, dates or times, and no counting words (once, twice, first, second, one, two, several).
8. If a previous line is given, keep the situations the sentences still state and add new ones, up to four in all.
9. Do not use the words: evidence, label, relationship, factor, supported, suggestive, statistic, engine, memory, hand-off, group, class, exposure, entangled, bundle, pair, points, status. The word "cases" is allowed only in the opening phrase.
10. Do not write view field names or any word with an underscore, and use no capital letters except at the start of the sentence.
11. Use only what is in the sentences. Do not invent.
Return only JSON."""

USER_TEMPLATE = "VIEW:\n{view_json}"
RETRY_ADDENDUM = "Your previous answer failed these checks: {failed_checks}. Rewrite it using only the sentences, in the frame, as one short sentence, or return null."
PROMPT_VERSION = "pp-v4"


def view_hash(view) -> str:
    return hashlib.sha256(json.dumps(view, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def cache_key(view: dict, tcfg: dict) -> str:
    """The view hash plus everything else that decides the answer: the model and the settings that change what is accepted, the prompt version and texts, the checks version."""
    settings = [tcfg[k] for k in ("model", "reasoning_effort", "retries", "max_words")]
    return hashlib.sha256(json.dumps([view_hash(view), settings, PROMPT_VERSION, SYSTEM_PROMPT, USER_TEMPLATE, RETRY_ADDENDUM, text_check.CHECKS_VERSION], sort_keys=True).encode()).hexdigest()


@dataclass
class TextResult:
    text: dict                  # {sentences (the association, P1 code text), source "code_text", situations, entry_ids, raw, cleaned}
    status: str                 # ok | null | dropped | no_diary_sentences | kept_previous_line | code_text_retracted
    llm_raw: list
    usage: list
    checks: list
    from_cache: bool = False
    prompt_version: str = PROMPT_VERSION
    checks_version: str = text_check.CHECKS_VERSION

    @property
    def text_source(self) -> str:
        return self.text["source"]

    def as_dict(self) -> dict:
        return {"text": self.text, "text_source": self.text_source, "status": self.status, "llm_raw": self.llm_raw, "usage": self.usage, "checks": self.checks,
                "prompt_version": self.prompt_version, "checks_version": self.checks_version}


def note_sentences(text: dict) -> list[str]:
    """The whole note: the association sentences, then the situations line if there is one."""
    return list(text["sentences"]) + ([text["situations"]] if text.get("situations") else [])


def _note(assoc: dict, situations, entry_ids: list, raw=None, cleaned=None) -> dict:
    return {"sentences": list(assoc["sentences"]), "source": "code_text", "situations": situations, "entry_ids": list(entry_ids), "raw": raw, "cleaned": cleaned or []}


def cached(view: dict, tcfg: dict, rows: dict | None, uid: tuple) -> "TextResult | None":
    """The stored result for exactly this view, prompt, settings and checks: this version's own row first, else a twin's. `rows` is `PiStore.text_rows()` (read in the main thread)."""
    if not rows or not tcfg.get("cache", True):
        return None
    cands = rows.get(cache_key(view, tcfg))
    if not cands:
        return None
    own = [r for u, r in cands if u == uid]
    hit = (own or [cands[0][1]])[0]
    return TextResult(hit["text"], hit["status"], hit["llm_raw"], hit["usage"], hit["checks"], from_cache=True, prompt_version=hit.get("prompt_version") or PROMPT_VERSION,
                      checks_version=hit.get("checks_version") or text_check.CHECKS_VERSION)


def generate(view: dict | None, entry_ids: list, assoc: dict, previous: dict | None, retracted: bool, client, tcfg: dict, pb, lib, kinds: set, rows: dict | None = None,
             uid: tuple = ("", 0), refresh: bool = False, allow_model: bool = True) -> TextResult:
    """One memory version. `assoc` is the P1 code text (kept as it is); `previous` the previous situations line ({line, entry_ids}) or None."""
    if retracted:
        return TextResult(_note(assoc, None, []), "code_text_retracted", [], [], [])
    if view is None:                                                      # no diary-only sentence: nothing to ask, no call; a previous line stands
        if previous and previous.get("line"):
            return TextResult(_note(assoc, previous["line"], previous["entry_ids"]), "kept_previous_line", [], [], [])
        return TextResult(_note(assoc, None, []), "no_diary_sentences", [], [], [])
    if not refresh:
        hit = cached(view, tcfg, rows, uid)
        if hit is not None:
            return hit
    if not allow_model:
        return TextResult(_note(assoc, None, []), "dropped", [], [], [], from_cache=True)
    base = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": USER_TEMPLATE.format(view_json=json.dumps(view, indent=2, ensure_ascii=False))}]
    raws, usages, checks, failures = [], [], [], []
    for attempt in range(1 + int(tcfg["retries"])):
        user = base[1]["content"] if attempt == 0 else base[1]["content"] + "\n\n" + RETRY_ADDENDUM.format(failed_checks=text_check.failure_text(failures))
        raw, usage, error = llm.call(client, tcfg, [base[0], {"role": "user", "content": user}])
        raws.append(raw if error is None else f"ERROR {error}")
        usages.append(usage)
        if error is not None:
            line, failures = None, [{"check": 0, "name": "call_error", "detail": error}]
            done = False
        else:
            obj, failures = text_check.parse(raw)
            done = obj is not None
            line = None
            if done and obj["situations"] is not None:
                cleaned, changes = text_view.clean(obj["situations"], view)
                failures = text_check.check(cleaned, view, pb, tcfg, lib, kinds)
                done = not failures
                line = cleaned
            elif done:
                changes = []
        checks.append(failures)
        if done:
            if obj["situations"] is None:
                return TextResult(_note(assoc, None, entry_ids, {"situations": None}), "null", raws, usages, checks)
            return TextResult(_note(assoc, line, entry_ids, {"situations": obj["situations"]}, changes), "ok", raws, usages, checks)
    return TextResult(_note(assoc, None, entry_ids), "dropped", raws, usages, checks)
