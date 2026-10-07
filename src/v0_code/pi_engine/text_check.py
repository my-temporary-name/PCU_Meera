"""The checks of the situations line (checks version pck-v6): the Findings checks that apply, plus the time-relative words, no association or claim, one short sentence in the frame,
no other relationship's phrase, a content-word overlap with the diary sentences, no names and no item that is only a generic word. Each failure is {check, name, detail}; [] is a pass.

1 structure (one sentence in the frame, at most `max_words` words), 2 digits, dates, times and counting words, 3 causal and claim words, 4 internal words, banned words (unknown,
unspecified, unclear, and the feelings, states and habits: felt, feel, feeling, proud, relieved, tired, stressed, anxious, happy, sad, guilty, drained, exhausted, stayed up) and underscore tokens (the frame's own "cases" is exempt), 5 time-relative words, 6 the line repeats neither the link's phrases nor another relationship's, 7 clinical
terms only if the sentences have them, 8 no phrase repeated, 9 the situation words come from the sentences (not strict: a stray word or two is tolerated), 10 no names, 11 no item of the list that is only a generic word (change, evening, day, night, morning, afternoon, time, thing)."""

import json
import re

from v0_code.findings_engine.factors import parse_key
from v0_code.findings_engine.textcheck import CAUSAL, CLOCK, MONTHS, normalise, view_text

CHECKS_VERSION = "pck-v6"
FRAME = "In the cases noted, the situations included"
TIME_WORDS = ["this week", "last week", "recently", "recent", "today", "yesterday", "tonight", "now", "currently", "lately", "so far", "again", "earlier", "previous", "prior"]
GENERIC_WORDS = {"change", "evening", "day", "night", "morning", "afternoon", "time", "thing"}          # an item of the list that is only one of these says nothing
DETERMINERS = {"a", "an", "the", "her", "some", "this", "that"}
BANNED_WORDS = ["unknown", "unspecified", "unclear", "felt", "feel", "feeling", "proud", "relieved", "tired", "stressed", "anxious", "happy", "sad", "guilty", "drained", "exhausted", "stayed up"]
CLAIM_WORDS = ["moved together", "linked", "tended"]
NAMES = {1: "structure", 2: "digits_dates_counting", 3: "causal_or_claim_words", 4: "no_internal_or_banned_words", 5: "no_time_relative_words", 6: "no_association_or_other_relationship",
         7: "clinical_terms_in_view", 8: "no_repeated_word", 9: "words_from_the_sentences", 10: "no_names", 11: "no_generic_item"}
STOP = set("""and with from that this their during amid over plus also into onto about after before while than then them they were been have having those these there which what when where who whom whose
each both some such other more most very only noted included situations cases days""".split())


def internal_words(pb) -> list[str]:
    return list(pb.raw["internal_words"]) + list(pb.raw.get("pi_internal_extra") or [])


def fail(n: int, detail: str) -> dict:
    return {"check": n, "name": NAMES[n], "detail": detail}


def parse(raw: str | None) -> tuple[dict | None, list[dict]]:
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError):
        return None, [fail(1, "the answer is not valid JSON")]
    if not isinstance(obj, dict) or "situations" not in obj or not (obj["situations"] is None or isinstance(obj["situations"], str)):
        return None, [fail(1, 'the answer must be a JSON object {"situations": "one sentence"} or {"situations": null}')]
    return obj, []


def other_phrases(pb, lib, kinds: set) -> list[str]:
    """Every exposure and outcome phrase of the library (lower case), with each meal kind of the memories filled in, longest first."""
    out = set()
    for p in lib.runnable():
        e, tag, o, _ = parse_key(p["key"].replace("{meal_kind}", "x"))
        out.add(pb.exposure(e, tag).lower())
        tpl = pb.raw["outcomes"][o]["phrase"]
        for k in (kinds if "{kind}" in tpl else [None]):
            out.add(pb.outcome(o, k).lower())
    return sorted(out, key=len, reverse=True)


def _stem(w: str) -> str:
    """A rough stem: plural, -ing, -ed and a final e are dropped, then the first five letters ("dose" and "doses", "stayed" and "staying" meet)."""
    w = w.lower()
    for suf, new in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)] + new
            break
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    return w[:5]


def list_items(line: str) -> list[str]:
    """The items of the list after the frame: split at commas, semicolons, "and" and "or" ("a work trip, a festival and a picnic" -> three items)."""
    body = line.replace(FRAME, "").strip().rstrip(".!?")
    return [x.strip() for x in re.split(r",|;|\band\b|\bor\b", body.lower()) if x.strip()]


def _is_generic(item: str) -> bool:
    words = [w for w in re.findall(r"[a-z']+", item) if w not in DETERMINERS]
    stems = [w[:-1] if w.endswith("s") and w[:-1] in GENERIC_WORDS else w for w in words]
    return bool(stems) and all(w in GENERIC_WORDS for w in stems)


def _phrases(text: str) -> list[str]:
    """The runs of content words between other words and punctuation ("a work trip, a festival" -> "work trip", "festival")."""
    runs, cur = [], []
    for tok in re.findall(r"[a-z']+|[^\sa-z']", text.lower()):
        if re.fullmatch(r"[a-z']+", tok) and len(tok) >= 4 and tok not in STOP:
            cur.append(tok)
        else:
            if cur:
                runs.append(" ".join(cur))
            cur = []
    return runs + ([" ".join(cur)] if cur else [])


def _content(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) >= 4 and w not in STOP]


def unmatched_words(line: str, view: dict) -> list[str]:
    """Content words of the line (the frame left out) that no entry or previous line uses (stem match)."""
    body = line.replace(FRAME, "").replace(FRAME.lower(), "")
    source = " ".join([view.get("previous_situations") or ""] + view["sentences"])
    have = {_stem(w) for w in re.findall(r"[a-z']+", source.lower())}
    return sorted({w for w in _content(body) if _stem(w) not in have})


def check(line: str, view: dict, pb, tcfg: dict, lib, kinds: set) -> list[dict]:
    out: list[dict] = []
    text = normalise(line)
    low = text.lower()
    body = text.replace(FRAME, "")
    # 1. structure
    if not text.strip() or not text.startswith(FRAME):
        out.append(fail(1, f"the line must start with the frame {FRAME!r}"))
    if len([s for s in re.split(r"[.!?](?:\s|$)", text.strip()) if s.strip()]) != 1 or "\n" in text:
        out.append(fail(1, "the line must be one sentence"))
    if len(text.split()) > int(tcfg["max_words"]):
        out.append(fail(1, f"the line has {len(text.split())} words (at most {tcfg['max_words']})"))
    # 2. digits, dates, times, counting words
    if re.search(r"\d", text) or re.search(MONTHS, low) or re.search(CLOCK, low):
        out.append(fail(2, "the line contains a digit, a date or a time"))
    for w in pb.raw["counting_words"]:
        if re.search(rf"\b{re.escape(w.lower())}\b", low):
            out.append(fail(2, f"the line uses the counting word {w!r}"))
    # 3. causal and claim words
    for pat in CAUSAL + [rf"\b{w}\b" for w in CLAIM_WORDS]:
        m = re.search(pat, low)
        if m:
            out.append(fail(3, f"the line uses the causal or claim word {m.group(0)!r}"))
    # 4. internal words and underscore tokens (the frame is exempt)
    tok = re.search(r"\w*_\w*", body.lower())
    if tok:
        out.append(fail(4, f"the line uses a token with an underscore ({tok.group(0)})"))
    for w in internal_words(pb):
        if re.search(rf"\b{re.escape(w.lower())}{'' if w.endswith('s') else 's?'}\b", body.lower()):
            out.append(fail(4, f"the line uses the internal word {w!r}"))
    for w in BANNED_WORDS:
        if re.search(rf"\b{w}\b", body.lower()):
            out.append(fail(4, f"the line uses the banned word {w!r}"))
    # 5. time-relative words
    for w in TIME_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", low):
            out.append(fail(5, f"the line uses the time-relative word {w!r}"))
    # 6. no association, no other relationship
    own = [view["link"]["present"].lower(), view["link"]["outcome"].lower()]
    for ph in own + other_phrases(pb, lib, kinds):
        if re.search(rf"(?<!\w){re.escape(ph)}(?!\w)", low):
            out.append(fail(6, f"the line repeats the association or names a relationship ({ph!r})"))
            break
    # 7. clinical terms
    vt = view_text(view)
    for term in pb.raw["clinical_terms"]:
        pat = rf"\b{re.escape(term.lower())}(?:s|es)?\b"
        if not re.search(pat, vt) and re.search(pat, low):
            out.append(fail(7, f"the line uses the clinical term {term!r}, which is not in the sentences"))
    # 8. no phrase repeated (a word may come back inside another phrase)
    runs = _phrases(body)
    rep = sorted({r for r in runs if runs.count(r) > 1})
    if rep:
        out.append(fail(8, f"the line repeats {', '.join(rep)}"))
    # 9. the situation words come from the entries (a stray word or two is tolerated: at least two and a quarter of the line's content words)
    stray = unmatched_words(text, view)
    if len(stray) >= 2 and len(stray) * 4 >= len(_content(body)):
        out.append(fail(9, f"these words are not in the sentences: {', '.join(stray)}"))
    # 10. no names: a capitalised word other than the start of the sentence
    caps = [w for w in re.findall(r"\b[A-Z][a-z]+\b", body) if w != "In"]
    if caps:
        out.append(fail(10, f"the line contains a name or capitalised word ({', '.join(caps)})"))
    # 11. an item of the list that is only a generic word (change, evening, day, ...)
    for item in list_items(text):
        if _is_generic(item):
            out.append(fail(11, f"the item {item!r} is only a generic word: name the situation"))
    return out


def failure_text(failures: list[dict]) -> str:
    return "; ".join(f"check {f['check']} ({f['name']}): {f['detail']}" for f in failures)
