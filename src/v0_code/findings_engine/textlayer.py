"""The text layer (findings_engine_spec.md 8 and Appendix B): view -> one model call -> seven checks -> one retry with the failed checks appended -> the code line. The
structured layer is an input only. The result of a view is cached by a key made of the view hash, the model settings and the prompt, so a second run with the same views makes
no call; `refresh` recomputes."""

import hashlib
import json
from dataclasses import dataclass

from v0_code.findings_engine import llm, textcheck, textclean
from v0_code.findings_engine.textcheck import check_text, failure_text, parse
from v0_code.findings_engine.view import canonical, view_hash, view_ids
from v0_code.intel_common.phrasebook import Phrasebook, join_list

SYSTEM_PROMPT = """You write a short plain-language account of one situation in a person's health record.

You receive a VIEW: what happened (measures that were off her usual), the things that were present with the kind of statement each allows, sets of things that must be described together, what is not known yet, whether there is enough history, diary entries, earlier summaries of her numbers, and earlier conclusions about her. All numbers were removed on purpose.

Write:
1. headline: one sentence, at most 20 words.
2. sentences: two to eight short sentences. Each sentence lists the ids of the view items it relies on. A set id counts as citing all the things in that set.

RULES. Follow all of them.
1. Write no digits, dates or times, and do not count ("once", "twice", "first", "second", "one", "two"). Use "that day".
2. Use only what is in the VIEW. Do not invent causes, places, settings or details.
3. Each thing has a wording. Say only what its wording allows:
   - asserted: "has tended to move together with"
   - asserted_same_day: the same, and the sentence must contain "same day", "same-day", "that day" or "on the day"
   - hedged, hedged_same_day: "may be linked to" (and one of those same-day phrases for the second)
   - present_only, present_only_history: say it was present, with no link. Say nothing about history in these sentences: the history note (rule 6) is stated once.
   - event_unusual: say how unusual this event was, using the position words given
   - artifact_note: "may be a sensor artifact"
   - contrary_note: say that on days with that thing the outcome has tended to be lower
4. Never write that something caused, triggered, explains, affects or led to anything.
5. Things in the same set must be described together in one sentence and cite the set id. For an often_together set, say they often occur together and their separate roles cannot be told apart.
6. If the history note says there is not enough history, say so once, in one sentence that cites "h1" and claims no link; that one sentence covers every present_only_history thing. If the history note says there is enough history, say nothing about history and do not cite "h1". If something is not known yet, say so and cite "n1".
7. Describe a diary entry only as it describes itself. Paraphrase; do not copy five or more words. Do not repeat numbers from it. If its note says it concerns someone else, say so, and do not describe her as unwell or as having a symptom because of it. An entry with "backs" is the entry behind the things it lists.
8. Earlier conclusions (the p items) may be mentioned as "this has come up before" or "an early observation", only in the same sentence as the thing it is about: a sentence that cites a p item must also cite the thing(s) that item is about, and a p item never stands alone in a sentence. They never supply claim wording: a claim uses only the thing's own wording from rule 3, and a phrase such as "has repeatedly moved together with" is never copied from an earlier conclusion. They never make a statement stronger than the thing's wording. Earlier summaries (the s items) are described as "an earlier summary says ..."; never say "this has come up before" or "an early observation" about them, never combine one with a claim about a thing in the same sentence, never cite one in a sentence about an artifact_note thing, and cite earlier summaries in at most one sentence.
9. Do not give advice, diagnoses or predictions. Do not use the words: evidence, label, relationship, factor, supported, suggestive, statistic, case, engine, memory, hand-off, group, class, exposure, exposures, entangled, bundle, pair, points.
10. Refer to the person with "she" and "her".
11. Never write view ids (f1, g1, m1, d1, s1, p1, h1, n1) in the text of a sentence or the headline; they go only in refs.
12. Use each thing's phrase exactly as given, including its window phrase; do not shorten or merge phrases.
13. Do not use "drink", "drank" or "drinking" for fluid intake.
14. When one sentence cites things of different strengths, use "may be linked to" for the whole sentence, or put them in separate sentences.
15. Use no clinical term (for example insulin, hypoglycemia, infection, diagnosis) unless the VIEW itself uses it.
16. Do not write the same phrase of a thing twice in one sentence.
17. A claim phrase ("has tended to move together with", "may be linked to") must be followed by the outcome given for that thing; never by another thing, "each other", a comma, "same day", "and" or "or", and never at the end of the sentence.
18. Write no word with an underscore.
19. A thing that lists several "ids" stands for all of them: cite its "id".

Return only JSON: {"headline": "...", "sentences": [{"text": "...", "refs": ["f1"]}]}"""

USER_TEMPLATE = "VIEW:\n{view_json}"
RETRY_ADDENDUM = ("Your previous answer failed these checks: {failed_checks}. Rewrite it using only the VIEW, with no digits or dates, no causal words, and no statement stronger "
                  "than the wording allows.")
PROMPT_VERSION = "p-v5"
COMPATIBLE_PROMPTS = {"p-v5": ("p-v4", "p-v3", "p-v2", "p-v1")}   # answers made under an earlier prompt are judged under the current checks and kept if they pass (`from_prompt` records which prompt made them)


def settings_key(text_cfg: dict) -> str:
    """What decides which answers a model can have given: the model and its effort."""
    return hashlib.sha256(json.dumps([text_cfg["model"], text_cfg["reasoning_effort"]]).encode()).hexdigest()


def cache_key(view: dict, text_cfg: dict) -> str:
    """The view hash plus everything else that decides the answer: the model and every setting that changes what is accepted (effort, retries, length limits, the copy
    window), the prompt version and texts and the version of the checks. Timeout and concurrency do not change an answer and are not part of it."""
    settings = [text_cfg[k] for k in ("model", "reasoning_effort", "retries", "headline_max_words", "sentences", "copy_words")]
    basis = json.dumps([view_hash(view), settings, PROMPT_VERSION, SYSTEM_PROMPT, USER_TEMPLATE, RETRY_ADDENDUM, textcheck.CHECKS_VERSION], sort_keys=True)
    return hashlib.sha256(basis.encode()).hexdigest()


def user_prompt(view: dict) -> str:
    return USER_TEMPLATE.format(view_json=json.dumps(view, indent=2, ensure_ascii=False))


@dataclass
class TextResult:
    text: dict
    text_source: str                       # llm | code_line
    status: str                            # ok | code_line_fallback
    llm_raw: list                          # one entry per attempt
    usage: list
    checks: list                           # one list of failures per attempt ([] = passed)
    from_cache: bool = False
    prompt_version: str = PROMPT_VERSION   # the prompt the stored answer was made under
    checks_version: str = textcheck.CHECKS_VERSION
    from_prompt: str | None = None         # set when an answer made under an earlier compatible prompt was accepted by the current checks
    settings_key: str = ""
    needs_model: bool = False              # a stored answer that fails the current checks and was made under another prompt (only set when no model call was allowed)

    def as_dict(self) -> dict:
        return {"text": self.text, "text_source": self.text_source, "status": self.status, "llm_raw": self.llm_raw, "usage": self.usage, "checks": self.checks,
                "prompt_version": self.prompt_version, "checks_version": self.checks_version, "from_prompt": self.from_prompt, "settings_key": self.settings_key}


def code_line_text(code_sentences: list[str]) -> dict:
    return {"headline": code_sentences[0], "sentences": [{"text": s, "refs": []} for s in code_sentences[1:]], "source": "code_line"}


def _from_row(hit: dict, text_cfg: dict) -> "TextResult":
    return TextResult(hit["text"], hit["text_source"], hit["status"], hit["llm_raw"], hit["usage"], hit["checks"], from_cache=True, prompt_version=hit.get("prompt_version") or PROMPT_VERSION,
                      checks_version=hit.get("checks_version") or textcheck.CHECKS_VERSION, from_prompt=hit.get("from_prompt"), settings_key=hit.get("settings_key") or settings_key(text_cfg))


def cached(view: dict, text_cfg: dict, store, finding_id: str | None = None) -> "TextResult | None":
    """The stored result for exactly this view, prompt, settings and checks, if any (a database connection belongs to one thread, so the caller looks up before it fans out)."""
    hit = store.get_cached(cache_key(view, text_cfg), finding_id) if store is not None and text_cfg.get("cache", True) else None
    if hit is not None and finding_id and hit["finding_id"] != finding_id and store.has_text(finding_id):
        return None                                                     # a twin's row: the version's own stored answer is judged first (see `lookup`)
    return None if hit is None else _from_row(hit, text_cfg)


def evaluate(raw: str | None, view: dict, record: dict, pb: Phrasebook, text_cfg: dict, ids: set) -> tuple[dict | None, list[dict]]:
    """One answer through parse, cleanup, the checks and the completion by code. Returns (the text, []) or (None, the failures). The checks see the cleaned text."""
    obj, failures = parse(raw)
    if obj is None:
        return None, failures
    cleaned, changes = textclean.clean(obj, view)
    failures = check_text(cleaned, view, record, pb, text_cfg, ids)
    if failures:
        return None, failures
    sentences = [{"text": x["text"], "refs": x["refs"]} for x in cleaned["sentences"]]
    appended = []
    cl = pb.raw["code_line"]
    for ref in textcheck.missing_required(cleaned, view, record):                       # check 7: completed by code with the phrase book's own sentence
        text = cl["not_known_yet"].format(list=join_list(view["not_known_yet"]["items"])) if ref == "n1" else cl["history_short"]
        sentences.append({"text": text, "refs": [ref], "appended": True})
        appended.append(ref)
    return {"headline": cleaned["headline"], "sentences": sentences, "source": "llm", "raw": {"headline": obj.get("headline"), "sentences": obj.get("sentences")},
            "cleaned": changes, "appended": appended}, []


def reevaluate(row: dict, view: dict, record: dict, code_sentences: list[str], pb: Phrasebook, text_cfg: dict, ids: set) -> "TextResult":
    """A stored result judged again under the current checks: its saved answers, in order, until one passes."""
    raws, checks = row["llm_raw"], []
    for k, raw in enumerate(raws):
        if str(raw).startswith("ERROR"):
            text, failures = None, [{"check": 0, "name": "call_error", "detail": str(raw)[6:]}]
        else:
            text, failures = evaluate(raw, view, record, pb, text_cfg, ids)
        checks.append(failures)
        if text is not None:
            prompt = row.get("prompt_version") or PROMPT_VERSION
            return TextResult(text, "llm", "ok", raws[:k + 1], row["usage"][:k + 1], checks, from_cache=True, prompt_version=prompt, from_prompt=prompt if prompt != PROMPT_VERSION else None,
                              settings_key=settings_key(text_cfg))
    return TextResult(code_line_text(code_sentences), "code_line", "code_line_fallback", raws, row["usage"], checks, from_cache=True, prompt_version=row.get("prompt_version") or PROMPT_VERSION,
                      settings_key=settings_key(text_cfg), needs_model=(row.get("prompt_version") or PROMPT_VERSION) != PROMPT_VERSION)


def lookup(view: dict, record: dict, code_sentences: list[str], text_cfg: dict, pb: Phrasebook, store) -> "TextResult | None":
    """Stored results for the same view and model settings made under this prompt or a compatible earlier one, judged again under the current checks: the first that passes, else
    the first one as a fallback (flagged `needs_model` when it was made under another prompt), else None."""
    if store is None or not text_cfg.get("cache", True):
        return None
    ids, stale = None, None
    for row in store.find_texts(view_hash(view), settings_key(text_cfg), [PROMPT_VERSION, *COMPATIBLE_PROMPTS.get(PROMPT_VERSION, ())], record.get("finding_id")):
        ids = ids or view_ids(view)
        r = reevaluate(row, view, record, code_sentences, pb, text_cfg, ids)
        if r.status == "ok":
            return r
        stale = stale or r
    return stale


def generate(view: dict, record: dict, code_sentences: list[str], client, text_cfg: dict, pb: Phrasebook, store=None, refresh: bool = False, allow_model: bool = True) -> TextResult:
    """One version. An exact stored result is reused. A result stored under an earlier compatible prompt is judged again under the current checks and accepted if it passes
    (`from_prompt` says which prompt made it). Otherwise attempt, clean, check, complete, retry once with the failures appended, then the code line. With `allow_model` False no
    call is ever made: the best stored result is returned (a fallback that needs the model is flagged)."""
    stale = None
    if not refresh:
        hit = cached(view, text_cfg, store, record.get("finding_id"))
        if hit is not None:
            return hit
        stale = lookup(view, record, code_sentences, text_cfg, pb, store)
        if stale is not None and stale.status == "ok":
            return stale
    if not allow_model:
        return stale or TextResult(code_line_text(code_sentences), "code_line", "code_line_fallback", [], [], [], from_cache=True, settings_key=settings_key(text_cfg), needs_model=True)
    ids = view_ids(view)
    base = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt(view)}]
    raws, usages, checks = [], [], []
    failures: list[dict] = []
    for attempt in range(1 + int(text_cfg["retries"])):
        user = base[1]["content"] if attempt == 0 else base[1]["content"] + "\n\n" + RETRY_ADDENDUM.format(failed_checks=failure_text(failures))
        raw, usage, error = llm.call(client, text_cfg, [base[0], {"role": "user", "content": user}])
        raws.append(raw if error is None else f"ERROR {error}")
        usages.append(usage)
        if error is not None:
            text, failures = None, [{"check": 0, "name": "call_error", "detail": error}]
        else:
            text, failures = evaluate(raw, view, record, pb, text_cfg, ids)
        checks.append(failures)
        if text is not None:
            return TextResult(text, "llm", "ok", raws, usages, checks, settings_key=settings_key(text_cfg))
    return TextResult(code_line_text(code_sentences), "code_line", "code_line_fallback", raws, usages, checks, settings_key=settings_key(text_cfg))
