"""Exposure values for one outcome unit (spec 6.2 and 3.1 rules 5 to 8), computed by generic primitives the library selects. An exposure value counts for a meal,
hour or reading unit only if it was recorded at or before the unit's start; on a day-level unit everything inside the window counts as date-resolution."""

from bisect import bisect_left, bisect_right
from datetime import datetime

from v0_code.evidence_engine.data import DataError, EvidenceData, Rec
from v0_code.evidence_engine.library import Library
from v0_code.evidence_engine.units import Unit
from v0_code.evidence_engine.windows import Window, window_for

MISSING, UNORDERED = "missing", "unordered"


class ExposureEvaluator:
    def __init__(self, lib: Library, cfg, data: EvidenceData):
        self.lib, self.cfg, self.data = lib, cfg, data
        self._now: datetime | None = None          # set only while an event-time state is evaluated
        self._pending: str | None = None           # the availability rule of a record that exists but is not available yet

    def window(self, tag: str, outcome: dict, unit: Unit, excludes: bool) -> Window:
        shift = int(outcome.get("exposure_shift_days", 0))
        return window_for(tag, outcome["unit"], unit.start, unit.date, shift, tag in self.lib.shifted_tags and shift != 0, excludes, self.lib.evening)

    def value(self, exposure: dict, tag: str, outcome: dict, unit: Unit, excludes: bool) -> tuple[float | None, str | None]:
        """(raw value, None) or (None, reason). The raw value is a 0/1 for a binary exposure and the measured value for a continuous one (the library may binarize it
        at a quantile afterwards, as-of)."""
        p = exposure["value"]
        w = self.window(tag, outcome, unit, excludes)
        return PRIMITIVES[p["primitive"]](self, exposure, p, w, outcome, unit)

    def event_value(self, exposure: dict, tag: str, outcome: dict, unit: Unit, excludes: bool, now: datetime):
        """The same value as `value`, from the records that are available at `now` (spec 3.1 rule 3). Returns (value, reason, pending): `pending` is the availability rule of a
        record in the window that exists but is not available yet (a daily total at the end of its day, a record at a clock time, a block that has not ended)."""
        self._now, self._pending = now, None
        try:
            v, why = self.value(exposure, tag, outcome, unit, excludes)
            return v, why, self._pending
        finally:
            self._now = None

    def _split(self, token: str, recs: list[Rec]) -> list[Rec]:
        """Event time: the records available now; the rest set `_pending`. Without an event time every record is visible."""
        if self._now is None:
            return recs
        vis = []
        for r in recs:
            if self.data.available_at(token, r) <= self._now:
                vis.append(r)
            elif self._pending is None:
                self._pending = self.data.avail_rule(token, r)
        return vis

    # ---- helpers ----------------------------------------------------------------------------------------------------------------------------------
    def _ref(self, name: str):
        if name.startswith("baseline."):
            return tuple(getattr(self.cfg.baseline, name.split(".", 1)[1]))
        if name.startswith("config."):
            _, group, item = name.split(".")
            return tuple(self.cfg.sets[group][item])
        raise DataError(f"unknown reference {name!r}")

    def _matcher(self, match: dict):
        field = match["field"]
        if "equals" in match:
            return lambda r: getattr(r, field) == match["equals"]
        if "in_ref" in match:
            vals = self._ref(match["in_ref"])
            return lambda r: getattr(r, field) in vals
        vals = self._ref(match["not_in_ref"])
        return lambda r: getattr(r, field) not in vals

    @staticmethod
    def _in_time(r: Rec, w: Window) -> bool:
        return r.ts is not None and w.lo <= r.ts <= w.hi


def _any_in_window(ev: ExposureEvaluator, exposure, p, w: Window, outcome, unit: Unit):
    token, data = p["source"], ev.data
    if not data.has(token):
        return None, MISSING
    hit = ev._matcher(p["match"])
    day_unit = outcome["unit"] == "day"
    res = exposure["resolution"]
    if res == "date":
        recs = ev._split(token, [r for d in w.dates for r in data.by_date(token).get(d, [])])
        return (None, MISSING) if not recs else (float(any(hit(r) for r in recs)), None)
    if res == "timestamp":
        recs = [r for r in data.records(token) if r.ts is not None and ((r.date in w.dates) if (day_unit and not w.bounded) else ev._in_time(r, w)) and (ev._now is None or r.ts <= ev._now)]
        return float(any(hit(r) for r in recs)), None
    blocks = [r for d in w.dates for r in data.by_date(token).get(d, [])]                    # block resolution
    if day_unit:
        blocks = ev._split(token, blocks)
        return (None, MISSING) if not blocks else (float(any(hit(r) for r in blocks)), None)
    ended = [r for r in blocks if (data.block_end(token, r) or unit.start) <= unit.start]
    if not ended:
        return None, (UNORDERED if blocks else MISSING)
    return float(any(hit(r) for r in ended)), None


def _value_in_window(ev: ExposureEvaluator, exposure, p, w: Window, outcome, unit: Unit):
    token, data = p["source"], ev.data
    if not data.has(token):
        return None, MISSING
    if w.kind == "prev_night":
        if outcome["unit"] == "day":                                      # the record dated the outcome date (spec 3.1 rule 7)
            hit = ev._split(token, [r for r in data.by_date(token).get(unit.date, []) if r.value is not None])
            return (hit[-1].value, None) if hit else (None, MISSING)
        times, recs = data.ts_index(token)                                # the latest record stamped at or before the unit's start
        i = bisect_right(times, unit.start)
        return (recs[i - 1].value, None) if i else (None, MISSING)
    if exposure["resolution"] == "date":
        hit = ev._split(token, [r for d in w.dates for r in data.by_date(token).get(d, []) if r.value is not None])
        return (hit[-1].value, None) if hit else (None, MISSING)
    span = data.span(token)
    times, recs = data.ts_index(token)
    i, j = bisect_left(times, w.lo), bisect_right(times, w.hi - span)         # a row counts only when its whole span has ended by the window's end
    return (recs[j - 1].value, None) if j > i else (None, MISSING)


def _mean_in_window(ev: ExposureEvaluator, exposure, p, w: Window, outcome, unit: Unit):
    token, data = p["source"], ev.data
    if not data.has(token):
        return None, MISSING
    vals = [v for t, v in data.readings(token) if t.date() in w.dates and w.lo <= t <= w.hi] if w.dates else data.readings_between(token, w.lo, w.hi)
    return (sum(vals) / len(vals), None) if vals else (None, MISSING)


def _event_start_minute(ev: ExposureEvaluator, exposure, p, w: Window, outcome, unit: Unit):
    token, data = p["source"], ev.data
    if not data.has(token):
        return None, MISSING
    kind = unit.scope if p["kind"] == "same_as_unit" else p["kind"]
    hit = [r for r in data.records(token) if r.ts is not None and data.event_kind(token, r) == kind and w.lo <= r.ts <= w.hi]
    return ((hit[-1].ts.hour * 60 + hit[-1].ts.minute) * 1.0, None) if hit else (None, MISSING)


PRIMITIVES = {"any_in_window": _any_in_window, "value_in_window": _value_in_window, "mean_in_window": _mean_in_window, "event_start_minute": _event_start_minute}
