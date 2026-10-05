"""The four output checks for a gist (spec section 7.4), and nothing else.

 1 direction_size       direction and size words agree with the tags, bound clause by clause
 2 causal               no causal language
 3 forbidden_content    no digits, dates, month names, quoted text (or 5+ words copied from a diary entry), no internal words
 4 structure            valid JSON, headline <= 15 words, 2 to 4 sentences, nothing else

Check 1 binds a direction word to the NEAREST PRECEDING measure in the SAME clause; a direction word with no measure before it in its clause
binds to nothing ("slightly higher blood pressure": nothing precedes "higher", so it is not read as a claim about any earlier measure).
Measures are matched longest phrase first, so "glucose variability", "average glucose" and "post-meal glucose peak" are separate measures.
Before check 1 matches anything, the text and the measure phrases are normalised the same way: lower case, possessives removed, plurals reduced
to a singular stem, hyphens read as spaces ("Post-meal glucose peaks" == "post meal glucose peak", "glucose's variability" == "glucose variability").
Every function returns failures as {"check": <name>, "detail": <text>}; an empty list is a pass.
"""

import json
import re

from v0_code.baseline_v2.config import Config

CHECKS = ("direction_size", "causal", "forbidden_content", "structure")

MAX_HEADLINE_WORDS = 15
MIN_SENTENCES, MAX_SENTENCES = 2, 4
COPY_RUN_WORDS = 5

UP_WORDS = ("up", "higher", "rose", "rise", "rises", "risen", "rising", "increase", "increased", "increases", "increasing", "more", "elevated", "greater", "climbed", "raised", "longer")
DOWN_WORDS = ("down", "lower", "fell", "fall", "falls", "fallen", "falling", "fewer", "less", "decrease", "decreased", "decreases", "decreasing", "dropped", "drop", "drops", "reduced", "declined", "shorter")
# intensity wording by size (spec 7.3: small = a little / slightly, moderate = clearly / noticeably, large = sharply / markedly / much); a few close synonyms are mapped to the same size
SIZE_WORDS = {"small": ("a little", "slightly", "somewhat", "marginally", "modestly"), "moderate": ("clearly", "noticeably", "moderately"),
              "large": ("sharply", "markedly", "much", "strongly", "dramatically", "substantially", "greatly", "considerably", "significantly")}

CAUSAL = re.compile(r"\b(caus\w*|trigger\w*|led to|resulted in|results in|as a result|due to|because|explains|attributable|driven by|responsible|thanks to|affected|impacted|influenced|contributed)\b", re.I)
TENTATIVE = re.compile(r"\b(tentative|tentatively|uncertain)\b", re.I)               # allowed only when the window is not reliable (the view says so)
# "fell below / rose above / was above / was below the reference range" describe a STATUS, not a trend: the verb is removed before direction words are read
STATUS_PHRASE = re.compile(r"\b(?:fell|dropped|declined|rose|climbed|went|was|were|is|are|remained|stayed)\s+(?:(?:slightly|a little|clearly|noticeably|well|just)\s+)?"
                           r"(?=(?:below|above)\s+(?:the\s+|its\s+)?(?:usual\s+)?(?:reference|normal)\s+range)")
HYPHENS = "\u2010\u2011\u2012\ufe63\uff0d"
INTERNAL = re.compile(r"\b(anchor|tag|stream|record|field|flag|window|tier|notable)s?\b|\bdirection table\b", re.I)
MONTHS = ("january", "february", "april", "june", "july", "august", "september", "october", "november", "december")
CLAUSE_SPLIT = re.compile(r"[,;:()—–]|\b(?:while|whereas|but|and|alongside|along with|together with|at the same time as|when|as|with|though|although|yet|then|so)\b", re.I)
SENTENCE_SPLIT = re.compile(r"[.!?]+")


def _f(check: str, detail: str, where: str | None = None) -> dict:
    return {"check": check, "detail": detail, **({"where": where} if where else {})}


def _stem(word: str) -> str:
    w = word.lower()
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def normalize_text(text: str) -> str:
    """Lower case, no possessive 's, plural words reduced to a singular stem, hyphens between letters read as spaces. Used on the text AND on every
    measure phrase / direction word / size word, so all of them are compared in the same form."""
    text = text.replace("\u00ad", "")                                                             # a soft hyphen is nothing at all
    text = re.sub(f"[{HYPHENS}]", "-", text)                                                       # non-breaking and look-alike hyphens are hyphens
    text = re.sub(r"(?<=[A-Za-z])-(?=[A-Za-z])", " ", text)
    return re.sub(r"[A-Za-z]+(?:['\u2019]s)?", lambda m: _stem(re.sub(r"['\u2019]s$", "", m.group(0))), text)


def finalize_headline(headline: str) -> str:
    """Code finishes the headline: first letter capitalised, a full stop at the end unless it already ends a sentence."""
    h = headline.strip()
    h = h[:1].upper() + h[1:]
    return h if not h or h.endswith((".", "!", "?")) else h + "."


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


# ---- check 4 ---------------------------------------------------------------------------------------------------------------------------------

def check_structure(obj) -> list[dict]:
    if not isinstance(obj, dict):
        return [_f("structure", "the answer is not a JSON object")]
    out = []
    if set(obj) != {"headline", "sentences"}:
        out.append(_f("structure", f"keys must be exactly headline and sentences, got {sorted(obj)}"))
    h, s = obj.get("headline"), obj.get("sentences")
    if not isinstance(h, str) or not h.strip():
        out.append(_f("structure", "headline is missing or empty"))
    elif len(h.split()) > MAX_HEADLINE_WORDS:
        out.append(_f("structure", f"headline has {len(h.split())} words (max {MAX_HEADLINE_WORDS})"))
    if not isinstance(s, list) or not all(isinstance(x, str) and x.strip() for x in s):
        out.append(_f("structure", "sentences must be a list of non-empty strings"))
    elif not MIN_SENTENCES <= len(s) <= MAX_SENTENCES:
        out.append(_f("structure", f"{len(s)} sentences (need {MIN_SENTENCES} to {MAX_SENTENCES})"))
    return out


def parse_json(raw: str) -> tuple[dict | None, list[dict]]:
    """Strict: the whole answer must be one JSON object (no prose around it, no code fence)."""
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError):
        return None, [_f("structure", "the answer is not valid JSON")]
    return obj, check_structure(obj)


def parse_batch(raw: str, keys: list[str]) -> dict[str, tuple[dict | None, list[dict]]]:
    """A batched answer is {"1": {...}, "2": {...}}. A key that is missing (or whose value is malformed) is that window's failure only."""
    try:
        whole = json.loads(raw)
    except (TypeError, ValueError):
        return {k: (None, [_f("structure", "the answer is not valid JSON")]) for k in keys}
    if not isinstance(whole, dict):
        return {k: (None, [_f("structure", "the answer is not a JSON object")]) for k in keys}
    out = {}
    for k in keys:
        if k not in whole:
            out[k] = (None, [_f("structure", f"key {k} is missing from the batched answer")])
        else:
            out[k] = (whole[k] if isinstance(whole[k], dict) else None, check_structure(whole[k]))
    return out


# ---- check 3 ---------------------------------------------------------------------------------------------------------------------------------

def _forbidden_content(texts: list[str], diary: list[str], reliable: bool = True) -> list[dict]:
    out = []
    for t in texts:
        if reliable:
            for m in TENTATIVE.finditer(t):
                out.append(_f("forbidden_content", f"{m.group(0)!r} in: {t!r} (the view does not say the window is unreliable)"))
        if re.search(r"\d", re.sub(r"hba1c", "", t, flags=re.I)):                  # the token "HbA1c" is the one allowed digit
            out.append(_f("forbidden_content", f"digit in: {t!r}"))
        if re.search(r"[\"“”]", t):
            out.append(_f("forbidden_content", f"quoted text in: {t!r}"))
        for m in re.finditer(r"\b(" + "|".join(MONTHS) + r")\b", t, re.I):
            out.append(_f("forbidden_content", f"month name {m.group(0)!r} in: {t!r}"))
        for m in re.finditer(r"\b(May|March)\b", t):          # also ordinary words (may, march): a month only when capitalised and not the first word
            if t[:m.start()].strip():
                out.append(_f("forbidden_content", f"month name {m.group(0)!r} in: {t!r}"))
        for m in INTERNAL.finditer(t):
            out.append(_f("forbidden_content", f"internal word {m.group(0)!r} in: {t!r}"))
    entries = [_words(d) for d in diary]
    for t in texts:
        w = _words(t)
        hit = next((" ".join(w[i:i + COPY_RUN_WORDS]) for i in range(len(w) - COPY_RUN_WORDS + 1)
                    for e in entries if any(e[j:j + COPY_RUN_WORDS] == w[i:i + COPY_RUN_WORDS] for j in range(len(e) - COPY_RUN_WORDS + 1))), None)
        if hit:
            out.append(_f("forbidden_content", f"{COPY_RUN_WORDS} or more words copied from a diary entry: {hit!r}"))
    return out


# ---- check 2 ---------------------------------------------------------------------------------------------------------------------------------

def _causal(texts: list[str]) -> list[dict]:
    return [_f("causal", f"causal wording {m.group(0)!r} in: {t!r}") for t in texts for m in CAUSAL.finditer(t)]


# ---- check 1 ---------------------------------------------------------------------------------------------------------------------------------

def _term_regex(cfg: Config) -> tuple[re.Pattern, dict[str, str]]:
    terms = {normalize_text(t): s for t, s in cfg.measure_terms().items()}
    ordered = sorted(terms, key=lambda t: (-len(t), t))                       # longest phrase first, in every form
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(t) for t in ordered) + r")(?!\w)"), terms


def _direction_size(cfg: Config, texts: list[str], tags: list[dict], where: str = "sentence") -> list[dict]:
    rx, terms = _term_regex(cfg)
    by_stream = {t["measure"]: t for t in tags}
    up = re.compile(r"\b(" + "|".join(sorted({normalize_text(w) for w in UP_WORDS})) + r")\b")
    down = re.compile(r"\b(" + "|".join(sorted({normalize_text(w) for w in DOWN_WORDS})) + r")\b")
    size_rx = {sz: re.compile(r"(?<!\w)(" + "|".join(re.escape(normalize_text(w)) for w in ws) + r")(?!\w)") for sz, ws in SIZE_WORDS.items()}
    out = []
    for raw_text in texts:
        text = STATUS_PHRASE.sub("", normalize_text(raw_text))
        for sentence in SENTENCE_SPLIT.split(text):
            for clause in CLAUSE_SPLIT.split(sentence):
                if not clause or not clause.strip():
                    continue
                mentions = [(m.start(), m.end(), terms[m.group(1)], m.group(1)) for m in rx.finditer(clause)]
                if not mentions:
                    continue
                spans = [(mentions[i][0], mentions[i + 1][0] if i + 1 < len(mentions) else len(clause), mentions[i]) for i in range(len(mentions))]
                for start, end, (_, mend, stream, phrase) in spans:
                    tag = by_stream.get(stream)
                    seg = clause[mend:end]                                       # words after the measure and before the next one: its direction words bind here
                    claims = [("up", m.group(0)) for m in up.finditer(seg)] + [("down", m.group(0)) for m in down.finditer(seg)]
                    if not claims or tag is None:
                        continue                                                 # no claim, or a measure with no direction tag (blood pressure): nothing to compare
                    if tag["direction"] in ("flat", "not_enough_data"):
                        out.append(_f("direction_size", f"claims {claims[0][1]!r} for {phrase!r} whose tag is {tag['direction']}: {clause.strip()!r}", where))
                        continue
                    for d, word in claims:
                        if d != tag["direction"]:
                            out.append(_f("direction_size", f"{word!r} says {d} for {phrase!r}, but its tag is {tag['direction']}: {clause.strip()!r}", where))
                    for sz, srx in size_rx.items():
                        if sz != tag["size"] and (m := srx.search(seg)):
                            out.append(_f("direction_size", f"{m.group(0)!r} is a {sz}-size word for {phrase!r}, but its size is {tag['size']}: {clause.strip()!r}", where))
    return out


# ---- all four --------------------------------------------------------------------------------------------------------------------------------

def check_gist(cfg: Config, obj, tags: list[dict], diary: list[str], sentence_mode: str = "strict", warnings: list | None = None, reliable: bool = True) -> list[dict]:
    """Run all four checks on a parsed gist. The structure check goes first; if it fails the wording checks are skipped (there is nothing to read).

    sentence_mode "strict" (default): every direction/size failure rejects the gist. "warn": a direction/size failure in a SENTENCE is appended to
    `warnings` (counted by the caller) instead of rejecting; the headline stays strict and the other three checks are never softened."""
    bad = check_structure(obj)
    if bad:
        return bad
    texts = [obj["headline"], *obj["sentences"]]
    head = _direction_size(cfg, [obj["headline"]], tags, "headline")
    body = _direction_size(cfg, obj["sentences"], tags, "sentence")
    if sentence_mode == "warn":
        if warnings is not None:
            warnings.extend(body)
        body = []
    return head + body + _causal(texts) + _forbidden_content(texts, diary, reliable)
