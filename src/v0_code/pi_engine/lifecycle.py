"""The status lifecycle (pi_spec.md 6.3 as amended, items 35 and 37). Pure functions of the weekly labels, no database.

A count of consecutive weeks is the current run of equal DECISIVE labels (supported / not_supported); the opposite decisive label resets it; suggestive and insufficient weeks
neither extend nor reset it. One transition at most per week. A status is a pure function of the weekly labels from the first tested week, so stepping week by week and the
back-fill on creation give the same result."""

import copy
from dataclasses import dataclass, field

from v0_code.pi_engine.labels import DECISIVE, LabelCfg, needed_days


@dataclass(frozen=True)
class LifecycleCfg:
    promote_after: int
    weaken_after: int
    retract_after: int
    contrary_days: int
    contrary_of: int
    contrary_weeks: int
    repromote_after: int
    placebo_max_share: float
    min_days: int
    scale: bool


@dataclass(frozen=True)
class Wk:
    """One weekly label with the counts the rules read."""
    iso: str
    end: str                 # the last day of the week that exists in the data (status_since)
    label: str
    days_in_week: int
    placebo_days: int = 0
    contrary_days: int = 0
    days_with_record: int = 0
    days_supported: int = 0


@dataclass
class State:
    status: str = "candidate"
    since: str | None = None
    run_label: str | None = None
    run_len: int = 0
    run_weeks: list = field(default_factory=list)           # the weeks of the current run (Wk)
    ns_after: int = 0                                      # unbroken not_supported weeks after the week of weakening
    contrary_run: int = 0
    history: list = field(default_factory=list)


def initial() -> State:
    return State()


def _contrary_qualifies(w: Wk, cfg: LifecycleCfg) -> bool:
    if w.days_in_week < cfg.min_days:
        return False
    return w.contrary_days >= needed_days(w.days_in_week, cfg.contrary_days, cfg.contrary_of, LabelCfg(cfg.contrary_days, cfg.contrary_of, cfg.min_days, cfg.scale))


def _placebo_ok(weeks: list, n: int, cfg: LifecycleCfg) -> bool:
    last = weeks[-n:]
    days = sum(w.days_in_week for w in last)
    return days > 0 and sum(w.placebo_days for w in last) / days < cfg.placebo_max_share


def _move(s: State, to: str, w: Wk) -> None:
    s.history.append({"week": w.iso, "from": s.status, "to": to})
    s.status, s.since = to, w.end


def step(state: State, w: Wk, cfg: LifecycleCfg) -> State:
    """The state after one more week. The given state is not changed."""
    s = copy.deepcopy(state)
    if w.label in DECISIVE:
        if w.label == s.run_label:
            s.run_len += 1
            s.run_weeks.append(w)
        else:
            s.run_label, s.run_len, s.run_weeks = w.label, 1, [w]
    was = s.status
    if was == "weakened":
        s.contrary_run = s.contrary_run + 1 if _contrary_qualifies(w, cfg) else 0
        if w.label == "not_supported":
            s.ns_after += 1
        elif w.label == "supported":
            s.ns_after = 0
    if was == "candidate":
        if s.run_label == "supported" and s.run_len >= cfg.promote_after and _placebo_ok(s.run_weeks, cfg.promote_after, cfg):
            _move(s, "supported", w)
    elif was == "supported":
        if s.run_label == "not_supported" and s.run_len >= cfg.weaken_after:
            _move(s, "weakened", w)
            s.ns_after, s.contrary_run = 0, 0
    elif was == "weakened":
        if s.run_label == "supported" and s.run_len >= cfg.repromote_after:
            _move(s, "supported", w)
        elif s.ns_after >= cfg.retract_after or s.contrary_run >= cfg.contrary_weeks:
            _move(s, "retracted", w)
    elif was == "retracted":
        if s.run_label == "supported" and s.run_len >= cfg.repromote_after:
            _move(s, "candidate", w)
    return s


def run(weeks: list[Wk], cfg: LifecycleCfg) -> State:
    s = initial()
    for w in weeks:
        s = step(s, w, cfg)
    return s
