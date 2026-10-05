"""The seven checks of the text layer (findings_engine_spec.md 8.3). Nothing else is checked. Each failure is {check, name, detail}; an empty list is a pass."""

import json
import re

from v0_code.findings_engine import textclean
from v0_code.findings_engine.view import INTERNAL_WORDING
from v0_code.findings_engine.wording import CLAIM
from v0_code.intel_common.phrasebook import Phrasebook

CAUSAL = [r"\bcaus\w*", r"\btrigger\w*", r"\bled to\b", r"\bresult\w*", r"\bdue to\b", r"\bbecause\b", r"\bexplains\b", r"\battributable\b", r"\bdriven by\b", r"\bresponsible\b", r"\baffect\w*",
          r"\bimpact\w*", r"\binfluenc\w*", r"\bcontribut\w*", r"\bas a result\b", r"\bthanks to\b"]
MONTHS = r"\b(january|february|march|april|june|july|august|september|october|november|december)\b"          # "may" is left out: it is a modal verb ("may be linked to"); a dated "May 5" has a digit
CLOCK = r"\b(o'clock|a\.?m\.?|p\.?m\.?)\b"
MOVE_TOGETHER, MAY_BE_LINKED = r"\bha(?:s|ve) tended to move together with\b", r"\bmay be linked to\b"
RECURRENCE = r"\b(come|comes|came) up before\b|\bhas come up\b|\bhave come up\b|\bearly observation\b"
CHECKS_VERSION = "ck-v5.2"                       # bump when a check changes: it is part of the cache key
VIEW_ID = r"\b[fgmdsphn]\d+\b"
NAMES = {1: "structure", 2: "refs_exist", 3: "no_digits_dates_counts", 4: "no_causal_wording", 5: "no_copied_diary_or_internal_words", 6: "claim_level", 7: "required_statements",
         8: "recurrence_wording", 9: "often_together_wording", 10: "one_summary_sentence", 11: "clinical_terms_in_view", 12: "object_of_a_claim", 13: "no_repeated_phrase", 14: "claim_followed_by_an_outcome"}


def fail(n: int, detail: str) -> dict:
    return {"check": n, "name": NAMES[n], "detail": detail}


def words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", s.lower().replace("’", "'"))


def normalise(s: str) -> str:
    return re.sub(r"[‐-―]", "-", s).replace("’", "'")


def parse(raw: str | None) -> tuple[dict | None, list[dict]]:
    """Check 1 begins here: the answer must be a JSON object."""
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError):
        return None, [fail(1, "the answer is not valid JSON")]
    if not isinstance(obj, dict):
        return None, [fail(1, "the answer is not a JSON object")]
    return obj, []


def check_text(obj: dict, view: dict, record: dict, pb: Phrasebook, text_cfg: dict, ids: set[str]) -> list[dict]:
    out: list[dict] = []
    head, sents = obj.get("headline"), obj.get("sentences")
    # 1. structure
    ok_struct = True
    if not isinstance(head, str) or not head.strip():
        out.append(fail(1, "no headline"))
        ok_struct = False
    elif len(head.split()) > int(text_cfg["headline_max_words"]):
        out.append(fail(1, f"the headline has {len(head.split())} words (at most {text_cfg['headline_max_words']})"))
    lo, hi = int(text_cfg["sentences"]["min"]), int(text_cfg["sentences"]["max"])
    if not isinstance(sents, list) or not (lo <= len(sents) <= hi):
        out.append(fail(1, f"there must be {lo} to {hi} sentences"))
        return out
    for i, s in enumerate(sents, 1):
        if not (isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip() and isinstance(s.get("refs"), list) and s["refs"] and all(isinstance(r, str) for r in s["refs"])):
            out.append(fail(1, f"sentence {i} needs text and at least one ref"))
            ok_struct = False
    if not ok_struct:
        return out
    texts = [(0, head)] + [(i, s["text"]) for i, s in enumerate(sents, 1)]
    # 2. refs exist
    for i, s in enumerate(sents, 1):
        for r in s["refs"]:
            if r not in ids:
                out.append(fail(2, f"sentence {i} cites {r!r}, which is not in the view"))
    # 3. no digits, dates, times, counting words
    banned_counts = [w.lower() for w in pb.raw["counting_words"]]
    for i, t in texts:
        n = normalise(t)
        low = n.lower()
        where = "the headline" if i == 0 else f"sentence {i}"
        if re.search(VIEW_ID, low):
            out.append(fail(3, f"{where} contains a view id ({re.search(VIEW_ID, low).group(0)}); ids belong only in refs"))
        if re.search(r"\d", re.sub(VIEW_ID, " ", n)):
            out.append(fail(3, f"{where} contains a digit"))
        if re.search(MONTHS, low) or re.search(CLOCK, low):
            out.append(fail(3, f"{where} contains a date or time word"))
        for w in banned_counts:
            if re.search(rf"\b{re.escape(w)}\b", low):
                out.append(fail(3, f"{where} uses the counting word {w!r}"))
    # 4. no causal wording
    for i, t in texts:
        low = normalise(t).lower()
        for pat in CAUSAL:
            m = re.search(pat, low)
            if m:
                out.append(fail(4, f"{'the headline' if i == 0 else f'sentence {i}'} uses the causal word {m.group(0)!r}"))
    # 5. no copied diary text, no internal words
    k = int(text_cfg["copy_words"])
    diary_words = [words(normalise(f"{d['text']} {d.get('severity_or_note') or ''}")) for d in view["diary"]]
    internal = [w.lower() for w in pb.raw["internal_words"]]
    for i, t in texts:
        where = "the headline" if i == 0 else f"sentence {i}"
        tw = words(normalise(t))
        grams = {" ".join(tw[j:j + k]) for j in range(len(tw) - k + 1)}
        for dw in diary_words:
            if grams & {" ".join(dw[j:j + k]) for j in range(len(dw) - k + 1)}:
                out.append(fail(5, f"{where} copies {k} or more words of a diary entry"))
                break
        low = normalise(t).lower()
        tok = re.search(r"\w*_\w*", low)
        if tok:
            out.append(fail(5, f"{where} uses a token with an underscore ({tok.group(0)})"))
        for w in internal:
            if re.search(rf"\b{re.escape(w)}{'' if w.endswith('s') else 's?'}\b", low):
                out.append(fail(5, f"{where} uses the internal word {w!r}"))
    # 6. claim level matches the refs; a cited bundle id counts as citing all its members
    by_id = {f["id"]: f for f in view["things"]}
    bundles = {g["id"]: g["members"] for g in view["sets"]}
    allowed_tt, allowed_ml = set(CLAIM[:2]), set(CLAIM)
    expanded = []
    for s in sents:
        refs = list(dict.fromkeys(x for r in s["refs"] for x in [r] + bundles.get(r, [])))
        expanded.append(refs)
    for i, s in enumerate(sents, 1):
        low = re.sub(r"\s+", " ", normalise(s["text"]).lower().replace("same-day", "same day"))
        classes = {INTERNAL_WORDING[by_id[r]["wording"]] for r in expanded[i - 1] if r in by_id}
        tt, ml = bool(re.search(MOVE_TOGETHER, low)), bool(re.search(MAY_BE_LINKED, low))
        if tt and not (classes and classes <= allowed_tt):
            out.append(fail(6, f"sentence {i} says 'has tended to move together with' but cites " + (", ".join(sorted(classes)) if classes else "no point")))
        if ml and not (classes and classes <= allowed_ml):
            out.append(fail(6, f"sentence {i} says 'may be linked to' but cites " + (", ".join(sorted(classes)) if classes else "no point")))
        if any(c.endswith("_same_day") for c in classes) and "same day" not in low:
            out.append(fail(6, f"sentence {i} cites a same-day point but does not say 'same day'"))
    # 8. recurrence wording and earlier summaries
    summaries = {x["id"] for x in view["earlier_summaries"]}
    conclusions = {x["id"] for x in view["earlier_conclusions"]}
    for i, s in enumerate(sents, 1):
        low = normalise(s["text"]).lower()
        refs = expanded[i - 1]
        if re.search(RECURRENCE, low) and not (set(refs) & conclusions):
            out.append(fail(8, f"sentence {i} says it has come up before or is an early observation but cites no earlier conclusion"))
        if set(refs) & summaries:
            kinds = {INTERNAL_WORDING[by_id[r]["wording"]] for r in refs if r in by_id}
            if kinds & set(CLAIM) or re.search(MOVE_TOGETHER, low) or re.search(MAY_BE_LINKED, low):
                out.append(fail(8, f"sentence {i} combines an earlier summary with a claim about a point"))
            if "artifact_note" in kinds:
                out.append(fail(8, f"sentence {i} cites an earlier summary together with a possible sensor artifact"))
    # 9. a set whose members often occur together is described that way
    entangled = {g["id"] for g in view["sets"] if g["reason"] == "often_together"}
    for i, s in enumerate(sents, 1):
        if set(s["refs"]) & entangled:
            low = normalise(s["text"]).lower()
            if not (re.search(r"\boften occur together\b", low) and re.search(r"\b(separate|individual) roles (cannot|can't|can not|could not) be told apart\b", low)):
                out.append(fail(9, f"sentence {i} cites a set whose members often occur together but does not say the items often occur together and their separate roles cannot be told apart"))
    # 10. at most one sentence cites an earlier summary
    n_summary = sum(bool(set(s["refs"]) & summaries) for s in sents)
    if n_summary > 1:
        out.append(fail(10, f"{n_summary} sentences cite an earlier summary (at most one)"))
    # 11. a clinical term only if the view's own text has it
    vt = view_text(view)
    for term in pb.raw["clinical_terms"]:
        pat = rf"\b{re.escape(term.lower())}(?:s|es)?\b"
        if re.search(pat, vt):
            continue
        for i, t in texts:
            if re.search(pat, normalise(t).lower()):
                out.append(fail(11, f"{'the headline' if i == 0 else f'sentence {i}'} uses the clinical term {term!r}, which is not in the view"))
    # 12. the object of a claim is an outcome, never another thing
    names_ = sorted({p["name"].lower() for p in view["things"] if p.get("name")}, key=len, reverse=True)
    for i, t in texts:
        low = normalise(t).lower()
        for m in re.finditer(MOVE_TOGETHER + "|" + MAY_BE_LINKED, low):
            after = low[m.end():].lstrip(" '\"“‘")
            hit = next((n for n in names_ if after.startswith(n) or after.startswith(" ".join(n.split()[:3]))), None) or ("each other" if re.match(r"(each other|one another)\b", after) else None)
            if hit:
                out.append(fail(12, f"{'the headline' if i == 0 else f'sentence {i}'} links something to another thing ({hit!r}); the object of a claim must be an outcome"))
    # 13. no phrase of the view twice in one sentence
    phrases = textclean.view_phrases(view)
    positions = {p["position"].lower() for p in view["things"] if p.get("position")} | {b[2].lower() for band in pb.raw["position_bands"].values() for b in band}
    for i, t in texts:
        low = normalise(t).lower()
        for ph in phrases:                                                      # longest first: a phrase inside a longer one is counted once
            pat = rf"(?<!\w){re.escape(ph.lower())}(?!\w)"
            if len(re.findall(pat, low)) > 1 and ph.lower() not in positions:                  # position phrases ("among the very lowest she has had") may repeat
                out.append(fail(13, f"{'the headline' if i == 0 else f'sentence {i}'} uses the phrase {ph!r} more than once"))
            low = re.sub(pat, "§", low)
    # 14. a claim phrase is followed by an outcome: not a comma, "same day", "and" or "or", and not the end of the sentence
    for i, t in texts:
        low = normalise(t).lower()
        for m in re.finditer(MOVE_TOGETHER + "|" + MAY_BE_LINKED, low):
            after = low[m.end():].lstrip()
            if after == "" or after[0] in ",;.:" or re.match(r"(same[- ]day|and|or)\b", after):
                out.append(fail(14, f"{'the headline' if i == 0 else f'sentence {i}'} has a claim phrase that is not followed by an outcome"))
    return out


def missing_required(obj: dict, view: dict, record: dict) -> list[str]:
    """Check 7 is completed by code, not enforced on the model: the ids ("n1", "h1") whose required sentence is missing. A required sentence is one that says it and cites its id:
    "not enough history" with h1 when the history note says so, "not known yet" with n1 when something is not known yet."""
    sents = obj.get("sentences") or []

    def says(pattern: str, ref: str) -> bool:
        return any(ref in s.get("refs", []) and re.search(pattern, normalise(s.get("text", "")).lower()) for s in sents)

    out = []
    if "not_known_yet" in view and not says(r"not (yet )?known|not known yet|not yet known", "n1"):
        out.append("n1")
    if record["history_note"] == "not_enough_history_yet" and not says(r"not enough history", "h1"):
        out.append("h1")
    return out


def view_text(view: dict) -> str:
    """Every string value of the view (not the keys), lower case: the words the model was given."""
    out: list[str] = []

    def walk(n):
        if isinstance(n, dict):
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
        elif isinstance(n, str):
            out.append(n.lower())
    walk(view)
    return " ".join(out)


def failure_text(failures: list[dict]) -> str:
    return "; ".join(f"check {f['check']} ({f['name']}): {f['detail']}" for f in failures)
