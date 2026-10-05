"""The three small grammars of the rulebook files (spec 5.1 to 5.3, with the Amendments) and the lookback kinds (spec 3). Parsing only: whether a stream, flag or
class is true for a patient is decided by the config."""

import re
from dataclasses import dataclass

LOOKBACK_KINDS_WITH_VALUE = ("minutes_before_open", "days_ending_at_open", "minutes_around_open")
LOOKBACK_KINDS_WITHOUT_VALUE = ("same_calendar_day", "previous_calendar_day", "previous_night", "previous_evening", "at_open")
LOOKBACK_KINDS = LOOKBACK_KINDS_WITH_VALUE + LOOKBACK_KINDS_WITHOUT_VALUE


class GrammarError(ValueError):
    pass


# ---- 5.1 context_match ----------------------------------------------------------------------------------------------------------------------------
_CMP = re.compile(r"^last_meal_minutes_ago\s*(<=|>=|==|<|>)\s*(\d+)$")
_PRES = re.compile(r"^last_meal\s+(absent|present)$")


@dataclass(frozen=True)
class ContextMatch:
    """`or` of `and`s of conditions on the minutes since the last logged meal (None = no meal logged). Empty = no extra condition."""
    clauses: tuple
    numbers: tuple

    def matches(self, last_meal_minutes: int | None) -> bool:
        if not self.clauses:
            return True
        return any(all(_holds(c, last_meal_minutes) for c in clause) for clause in self.clauses)


def _holds(cond, minutes) -> bool:
    kind = cond[0]
    if kind == "absent":
        return minutes is None
    if kind == "present":
        return minutes is not None
    if minutes is None:
        return False                      # a comparison needs a logged meal
    op, n = cond[1], cond[2]
    return {"<=": minutes <= n, ">=": minutes >= n, "==": minutes == n, "<": minutes < n, ">": minutes > n}[op]


def parse_context_match(text: str) -> ContextMatch:
    text = (text or "").strip()
    if not text:
        return ContextMatch((), ())
    clauses, numbers = [], []
    for part in re.split(r"\s+or\s+", text):
        clause = []
        for term in re.split(r"\s+and\s+", part.strip()):
            term = term.strip()
            if m := _CMP.match(term):
                clause.append(("cmp", m.group(1), int(m.group(2))))
                numbers.append(int(m.group(2)))
            elif m := _PRES.match(term):
                clause.append((m.group(1),))
            else:
                raise GrammarError(f"cannot parse context_match term {term!r} in {text!r}")
        clauses.append(tuple(clause))
    return ContextMatch(tuple(clauses), tuple(numbers))


# ---- 5.2 requires_streams -------------------------------------------------------------------------------------------------------------------------
_TOKEN = re.compile(r"^([A-Za-z0-9_]+)(?:\[([A-Za-z0-9_]+)\])?$")


@dataclass(frozen=True)
class Token:
    name: str
    category: str | None
    generic: str          # the token as written, e.g. "some_stream[some_category]"


def parse_requires(text: str) -> tuple[tuple[Token, ...], ...]:
    """`;` splits groups, `|` splits the alternatives (fallbacks, in order) of a group."""
    text = (text or "").strip()
    if not text:
        raise GrammarError("requires_streams is empty")
    groups = []
    for grp in text.split(";"):
        alts = []
        for raw in grp.split("|"):
            raw = raw.strip()
            m = _TOKEN.match(raw)
            if not m:
                raise GrammarError(f"cannot parse stream token {raw!r} in {text!r}")
            alts.append(Token(m.group(1), m.group(2), raw))
        groups.append(tuple(alts))
    return tuple(groups)


# ---- 5.3 applies_if_rule --------------------------------------------------------------------------------------------------------------------------
_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")
_NAME = re.compile(r"^[A-Za-z0-9_]+$")
APPLIES_KINDS = ("patient_flag", "medication_class_present", "stream_present", "open_time_between")


@dataclass(frozen=True)
class Atom:
    kind: str
    arg: str
    window: tuple | None = None      # open_time_between: (start minute, end minute)


@dataclass(frozen=True)
class Term:
    text: str                        # the term as written (what a skip names)
    atoms: tuple                     # any of (OR)


def _minutes(hhmm: str) -> int:
    m = _HHMM.match(hhmm.strip())
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise GrammarError(f"not a clock time: {hhmm!r}")
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_applies(text: str) -> tuple[Term, ...]:
    """Terms separated by `;` are all required; inside a term `|` means any of."""
    text = (text or "").strip()
    if not text:
        return ()
    terms = []
    for raw_term in text.split(";"):
        atoms = []
        for raw in raw_term.split("|"):
            kind, sep, arg = raw.strip().partition(":")
            if not sep or kind not in APPLIES_KINDS:
                raise GrammarError(f"cannot parse applicability term {raw.strip()!r} in {text!r}")
            if kind == "open_time_between":
                a, dash, b = arg.partition("-")
                if not dash:
                    raise GrammarError(f"open_time_between needs HH:MM-HH:MM, got {arg!r}")
                atoms.append(Atom(kind, arg, (_minutes(a), _minutes(b))))
            else:
                if not _NAME.match(arg):
                    raise GrammarError(f"cannot parse applicability term {raw.strip()!r} in {text!r}")
                atoms.append(Atom(kind, arg))
        terms.append(Term(raw_term.strip(), tuple(atoms)))
    return tuple(terms)


# ---- 3 lookback -----------------------------------------------------------------------------------------------------------------------------------
def parse_lookback(kind: str, value: str | int | None) -> int | None:
    kind = (kind or "").strip()
    if kind not in LOOKBACK_KINDS:
        raise GrammarError(f"unknown lookback_kind {kind!r}")
    raw = "" if value is None else str(value).strip()
    if kind in LOOKBACK_KINDS_WITH_VALUE:
        if not raw.isdigit() or int(raw) <= 0:
            raise GrammarError(f"lookback_value must be a positive whole number for lookback_kind {kind!r}, got {raw!r}")
        return int(raw)
    if raw:
        raise GrammarError(f"lookback_value must be empty for lookback_kind {kind!r}, got {raw!r}")
    return None
