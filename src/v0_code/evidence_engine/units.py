"""Outcome units (spec 6.1): one value per meal, day, hour or reading, built by generic primitives the library selects. Also the detrending of the outcome
(spec 7.1): the difference from a baseline built only from earlier values."""

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from statistics import median

from v0_code.evidence_engine.data import EvidenceData


@dataclass
class Unit:
    start: datetime               # the unit's start (the ordering rule compares exposures with this)
    end: datetime                 # when the whole unit, forward window included, has ended (it enters the history only after this)
    date: date                    # the outcome date of the unit
    value: float
    scope: str | None = None
    hour: int | None = None
    resid: float = math.nan       # the detrended outcome; nan when too few earlier values


def _mid(d: date, tz) -> datetime:
    return datetime.combine(d, time(0), tzinfo=tz)


def _day_unit(d: date, v: float, tz) -> Unit:
    return Unit(_mid(d, tz), _mid(d + timedelta(days=1), tz), d, v)


def _by_date(readings):
    out = defaultdict(list)
    for t, v in readings:
        out[t.date()].append((t, v))
    return out


def _max_after_event(od, data: EvidenceData, cfg):
    p, minutes = od["value"], int(od["value"]["window_minutes"])
    tz = data.tz
    out: dict = defaultdict(list)
    for m in data.records(od["unit_source"]):
        kind = data.event_kind(od["unit_source"], m) if m.ts else None
        if m.ts is None or kind is None:
            continue
        vals = data.readings_between(p["source"], m.ts, m.ts + timedelta(minutes=minutes))
        if vals:
            out[kind].append(Unit(m.ts, m.ts + timedelta(minutes=int(od["forward_minutes"])), m.date, max(vals), kind))
    return out


def _mean_outside_event_windows(od, data, cfg):
    p = od["value"]
    starts = sorted(m.ts for m in data.records(p["event_source"]) if m.ts)
    gap = timedelta(minutes=int(p["gap_minutes"]))
    from bisect import bisect_right
    out = []
    for d, rs in sorted(_by_date(data.readings(p["source"])).items()):
        keep = []
        for t, v in rs:
            i = bisect_right(starts, t)
            if i == 0 or t - starts[i - 1] > gap:
                keep.append(v)
        if keep:
            out.append(_day_unit(d, sum(keep) / len(keep), data.tz))
    return {None: out}


def _day_stat(fn):
    def run(od, data, cfg):
        return {None: [_day_unit(d, fn([v for _, v in rs]), data.tz) for d, rs in sorted(_by_date(data.readings(od["value"]["source"])).items())]}
    return run


def _mean_of_hour(od, data, cfg):
    groups = defaultdict(list)
    for t, v in data.readings(od["value"]["source"]):
        groups[t.replace(minute=0, second=0, microsecond=0)].append(v)
    return {None: [Unit(h, h + timedelta(hours=1), h.date(), sum(v) / len(v), None, h.hour) for h, v in sorted(groups.items())]}


def _dated_record(od, data, cfg):
    p = od["value"]
    pick = cfg.picks.get(p["pick_from_config"], "last") if p.get("pick_from_config") else p.get("pick", "last")
    out = []
    for d, rs in sorted(data.by_date(p["source"]).items()):
        rs = [r for r in rs if r.value is not None]
        if rs:
            out.append(_day_unit(d, (rs[-1] if pick == "last" else rs[0]).value, data.tz))
    return {None: out}


def _count_matching_by_day(od, data, cfg):
    p = od["value"]
    field = "text" if p["match"]["field"] == "text" else "category"
    out = []
    for d, rs in sorted(data.by_date(p["source"]).items()):
        out.append(_day_unit(d, float(sum(1 for r in rs if getattr(r, field) == p["match"]["equals"])), data.tz))
    return {None: out}


def _record_value(od, data, cfg):
    return {None: [Unit(r.ts, r.ts, r.date, r.value) for r in data.records(od["value"]["source"]) if r.ts is not None and r.value is not None]}


OUTCOME_FUNCS = {"max_after_event": _max_after_event, "mean_outside_event_windows": _mean_outside_event_windows, "min_of_day": _day_stat(min), "mean_of_day": _day_stat(lambda v: sum(v) / len(v)),
                 "mean_of_hour": _mean_of_hour, "dated_record": _dated_record, "count_matching_by_day": _count_matching_by_day, "record_value": _record_value}


def build_units(od: dict, data: EvidenceData, cfg) -> dict:
    """scope -> units in time order, each with its detrended outcome. A relationship whose stream the patient lacks has no units."""
    if not data.has(od["value"]["source"]):
        return {}
    by_scope = OUTCOME_FUNCS[od["value"]["primitive"]](od, data, cfg)
    for units in by_scope.values():
        units.sort(key=lambda u: u.start)
        detrend(units, od["unit"], cfg.detrend_window_days, cfg.detrend_min_prior)
    return {k: v for k, v in by_scope.items() if v}


def detrend(units: list[Unit], unit_kind: str, window_days: int, min_prior: int) -> None:
    """spec 7.1: day units against the median of the previous window_days days; meal units against her earlier meals of the same kind in those days (units are already
    split by kind); hour units against the same clock hour over those days; reading units against the readings in those days. Only earlier values; at least min_prior."""
    if unit_kind == "hour":
        index = {(u.date, u.hour): u.value for u in units}
        for u in units:
            prior = [index[(u.date - timedelta(days=k), u.hour)] for k in range(1, window_days + 1) if (u.date - timedelta(days=k), u.hour) in index]
            u.resid = u.value - median(prior) if len(prior) >= min_prior else math.nan
        return
    from bisect import bisect_left
    if unit_kind == "reading":
        times = [u.start for u in units]
        for i, u in enumerate(units):
            lo = bisect_left(times, u.start - timedelta(days=window_days))
            prior = [units[k].value for k in range(lo, i) if units[k].start < u.start]
            u.resid = u.value - median(prior) if len(prior) >= min_prior else math.nan
        return
    dates = [u.date for u in units]                                  # day and meal units: previous window_days calendar days, strictly earlier dates
    for i, u in enumerate(units):
        lo = bisect_left(dates, u.date - timedelta(days=window_days))
        hi = bisect_left(dates, u.date)
        prior = [units[k].value for k in range(lo, hi)]
        u.resid = u.value - median(prior) if len(prior) >= min_prior else math.nan
