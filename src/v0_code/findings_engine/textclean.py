"""The cleanup step of the text layer: mechanical fixes to the model's wording, run BEFORE the checks (the checks see the cleaned text). It capitalises the start of the headline
and of every sentence, lower-cases the first letter of an earlier summary's content after "says", strips quotes around the view's own phrases, and finishes a sentence that has no final mark with a full stop (the headline is left as it is). Nothing else is touched: words,
refs and order stay. The raw object is never changed; the caller stores raw and cleaned."""

import copy
import re

QUOTES_OPEN, QUOTES_CLOSE = "\"“‘'", "\"”’'"
AFTER_SAYS = re.compile(r"(\bsays?\s+)([A-Z])(?=[a-z]+\b)")


def view_phrases(view: dict) -> list[str]:
    """Every phrase the view gives the model to use as it is."""
    out = [m["what"] for m in view["situation"]["measures"]]
    if view["situation"].get("meal_context"):
        out.append(view["situation"]["meal_context"])
    for p in view["things"]:
        out += [p[k] for k in ("name", "outcome", "statement", "position") if p.get(k)]
    out += (view.get("not_known_yet") or {}).get("items", [])
    return sorted({p for p in out if p}, key=len, reverse=True)


def _strip_quotes(text: str, phrases: list[str]) -> str:
    for ph in phrases:
        text = re.sub(rf"[{re.escape(QUOTES_OPEN)}](\s*)({re.escape(ph)})(\s*)[{re.escape(QUOTES_CLOSE)}]", lambda m: m.group(1) + m.group(2) + m.group(3), text, flags=re.IGNORECASE)
    return text


def _capitalise(text: str) -> str:
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
        if not ch.isspace():
            return text
    return text


def _fix(text: str, phrases: list[str], changes: set) -> str:
    t = _strip_quotes(text, phrases)
    if t != text:
        changes.add("quotes_stripped")
    if re.search(r"earlier summar", t, re.I):
        u = AFTER_SAYS.sub(lambda m: m.group(1) + m.group(2).lower(), t)
        if u != t:
            changes.add("lowercased_after_says")
        t = u
    u = _capitalise(t)
    if u != t:
        changes.add("capitalised")
    return u


def clean(obj: dict, view: dict) -> tuple[dict, list[str]]:
    """(cleaned copy, sorted list of the kinds of change made)."""
    out, changes, phrases = copy.deepcopy(obj), set(), view_phrases(view)
    if isinstance(out.get("headline"), str):
        out["headline"] = _fix(out["headline"], phrases, changes)
    for s in out.get("sentences") or []:
        if isinstance(s, dict) and isinstance(s.get("text"), str):
            s["text"] = _fix(s["text"], phrases, changes)
            if s["text"].strip() and s["text"].strip()[-1] not in ".!?":
                s["text"] = s["text"].strip() + "."
                changes.add("punctuation_added")
    return out, sorted(changes)
