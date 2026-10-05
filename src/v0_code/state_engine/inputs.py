"""Read side of the State Engine (spec 4): the Personal Data Store, read-only, turned into observations that each know WHEN they became available.

An observation has `value_time` (the moment it is known, which is what its age counts from) and `available_at` (the same moment: nothing here is ever
visible earlier, spec 3.1). A value with its own timestamp is available from it; a date-only record follows its stream's `available_at` rule: a clock
time, a time per block, or `end_of_day` (the next midnight). A timestamped stream whose row is date-only is treated as `end_of_day`.
Nothing is written to the store.
"""

import json
import sqlite3
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date as _date, datetime, time, timedelta

from v0_code.baseline_v2.data import Reading
from v0_code.baseline_v2.profile import STATUS_RANK
from v0_code.baseline_v2.trust import clean_series
from v0_code.state_engine.config import StateConfig, StreamCfg, parse_hhmm


@dataclass(frozen=True)
class Obs:
    value_time: datetime
    available_at: datetime
    value: object                    # float, or a dict for blood pressure / medicines / mood
    status: str | None = None
    meta: dict = field(default_factory=dict, compare=False, hash=False)
    rejected: bool = False
    reject_reason: str | None = None
    record_date: _date | None = None   # the date the RECORD belongs to (an end-of-day value of 17 Sept is known at midnight of the 18th, but its record date is the 17th)


def parse_ts(ts: str, tz) -> tuple[datetime, bool]:
    """(timezone-aware datetime in the patient's timezone, has_time). A date-only string is midnight of that date in the patient's timezone."""
    if len(ts) == 10:
        d = _date.fromisoformat(ts)
        return datetime.combine(d, time(0, 0), tzinfo=tz), False
    return datetime.fromisoformat(ts).astimezone(tz), True


def end_of_day(dt: datetime) -> datetime:
    return datetime.combine(dt.date() + timedelta(days=1), time(0, 0), tzinfo=dt.tzinfo)


def availability(rule, ts: str, tz, block: str | None = None) -> tuple[datetime, datetime]:
    """(value_time, available_at) of a record under a stream's `available_at` rule."""
    dt, has_time = parse_ts(ts, tz)
    if has_time and rule == "timestamp":
        return dt, dt
    day = datetime.combine(dt.date(), time(0, 0), tzinfo=tz)
    if isinstance(rule, dict):
        h, m = parse_hhmm(rule[block])
        t = day.replace(hour=h, minute=m)
        return t, t
    if rule in ("timestamp", "end_of_day"):
        eod = end_of_day(day)
        return eod, eod
    h, m = parse_hhmm(rule)
    if has_time:
        return dt, dt                                    # a timed record is known from its own time even when the stream has a clock-time fallback
    t = day.replace(hour=h, minute=m)
    return t, t


def worse_status(a: str | None, b: str | None) -> str | None:
    if a is None or b is None:
        return a or b
    return a if STATUS_RANK.get(a, 0) >= STATUS_RANK.get(b, 0) else b


class StateInputs:
    def __init__(self, conn: sqlite3.Connection, cfg: StateConfig):
        self.cfg = cfg
        tz = cfg.tz
        raw: dict[str, list[tuple[str, float, str | None]]] = {}
        for ts, bio, value, status in conn.execute("SELECT timestamp, biomarker, value, status FROM raw_events WHERE source_type = 'reading' ORDER BY timestamp, id"):
            raw.setdefault(bio, []).append((ts, value, status))
        ctx: dict[str, list[tuple]] = {}
        for stream, ts, d, vt, vn, cat, meta in conn.execute("SELECT stream, timestamp, date, value_text, value_num, category, meta_json FROM context_events ORDER BY id"):
            ctx.setdefault(stream, []).append((ts, d, vt, vn, cat, json.loads(meta) if meta else {}))
        self.obs: dict[str, list[Obs]] = {}
        self._avail: dict[str, list[datetime]] = {}
        for s in cfg.streams:
            items = self._build(s, raw, ctx, tz)
            items.sort(key=lambda o: (o.available_at, o.value_time))
            self.obs[s.name] = items
            self._avail[s.name] = [o.available_at for o in items]
        # label-only context
        meal_name = cfg.context_streams.get("meals", {}).get("name")
        self.meals = sorted(((parse_ts(ts, tz)[0], cat or "meal", meta.get("meal_id")) for ts, d, vt, vn, cat, meta in ctx.get(meal_name, []) if ts), key=lambda m: m[0])
        self._meal_times = [m[0] for m in self.meals]
        diary_cfg = cfg.context_streams.get("diary", {})
        diary_rule = diary_cfg.get("available_at", "21:00")
        diary = []
        for ts, d, vt, vn, cat, meta in ctx.get(diary_cfg.get("name"), []):
            vtime, avail = availability(diary_rule, ts or d, tz)
            diary.append((avail, vtime, {"category": cat, "text": vt}))
        self.diary = sorted(diary, key=lambda x: (x[0], x[1]))
        self._diary_times = [x[0] for x in self.diary]
        # first date of the record = first date of the primary (first configured continuous) stream
        primary = next(s for s in cfg.streams if s.kind == "continuous")
        self.primary = primary.name
        first = min((o.value_time for o in self.obs[primary.name]), default=None)
        self.first_date = first.date() if first else None
        self.last_date = max((o.value_time for o in self.obs[primary.name]), default=None)
        self.last_date = self.last_date.date() if self.last_date else None

    # ---- observations ------------------------------------------------------------------------------------------------------------------------
    def _build(self, s: StreamCfg, raw, ctx, tz) -> list[Obs]:
        src = s.source
        rule = s.available_at
        if s.kind == "continuous":
            rows = raw.get(src["name"], []) if src["table"] == "raw" else [(ts, vn, None) for ts, d, vt, vn, cat, meta in ctx.get(src["name"], []) if vn is not None]
            status_of = {}
            if s.status_from:
                status_of = {ts: st for ts, v, st in raw.get(s.status_from["name"], [])}
            rejected: dict[str, str] = {}
            if s.cleaning == "baseline_glucose":                                     # the Baseline Engine's own cleaning of questionable readings
                series = []
                for ts, v, st in rows:
                    dt = parse_ts(ts, tz)[0]
                    series.append(Reading(ts, dt, v))
                series.sort(key=lambda r: r.dt)
                _, removed = clean_series(series, self.cfg.baseline)
                rejected = {x.ts: x.reason for x in removed}
            out = []
            for ts, v, st in rows:
                vt, av = availability(rule, ts, tz)
                out.append(Obs(vt, av, float(v), st if st is not None else status_of.get(ts), {}, ts in rejected, rejected.get(ts), vt.date()))
            return out
        if s.kind in ("daily", "lab"):
            out = []
            for ts, v, st in raw.get(src["name"], []):
                vt, av = availability(rule, ts, tz)
                out.append(Obs(vt, av, float(v), st, record_date=parse_ts(ts, tz)[0].date()))
            return out
        if s.kind == "periodic":
            names = src["names"]
            by = [{ts: (v, st) for ts, v, st in raw.get(n, [])} for n in names]
            out = []
            for ts in sorted(set.intersection(*(set(d) for d in by))):
                vt, av = availability(rule, ts, tz)
                comps = {n.rsplit("_", 1)[-1]: d[ts][0] for n, d in zip(names, by)}
                st = None
                for d in by:
                    st = worse_status(st, d[ts][1])
                out.append(Obs(vt, av, comps, st, {"component_status": {n.rsplit("_", 1)[-1]: d[ts][1] for n, d in zip(names, by)}}, record_date=parse_ts(ts, tz)[0].date()))
            return out
        if s.kind == "count":
            by_date: dict[str, list] = {}
            for ts, d, vt, vn, cat, meta in ctx.get(src["name"], []):
                by_date.setdefault(d, []).append((cat, vt))
            out = []
            for d, rows in by_date.items():
                vtm, av = availability(rule, d, tz)
                missed = sorted(c for c, v in rows if v != "taken")
                out.append(Obs(vtm, av, {"taken": len(rows) - len(missed), "expected": len(rows), "missed": missed}, record_date=parse_ts(d, tz)[0].date()))
            return out
        if s.kind == "label":
            out = []
            for ts, d, vt, vn, cat, meta in ctx.get(src["name"], []):
                block = meta.get(src.get("block_key", ""))
                vtm, av = availability(rule, ts or d, tz, block)
                out.append(Obs(vtm, av, {"label": vt, "category": cat, "block": block}, record_date=parse_ts(ts or d, tz)[0].date()))
            return out
        raise ValueError(f"unknown stream kind {s.kind!r}")

    def latest(self, stream: str, as_of: datetime) -> Obs | None:
        """The newest observation available at `as_of`."""
        i = bisect_right(self._avail[stream], as_of)
        return self.obs[stream][i - 1] if i else None

    def history(self, stream: str, before: datetime) -> list[Obs]:
        """Observations whose own moment is strictly before `before` (used for percentile / profile-like usuals)."""
        return [o for o in self.obs[stream] if o.value_time < before]

    # ---- context -----------------------------------------------------------------------------------------------------------------------------
    def last_meal(self, as_of: datetime, window_minutes: int):
        i = bisect_right(self._meal_times, as_of)
        if not i:
            return None
        t, label, mid = self.meals[i - 1]
        mins = (as_of - t).total_seconds() / 60
        return {"label": label, "time": t, "minutes_ago": round(mins)} if mins <= window_minutes else None

    def diary_today(self, as_of: datetime) -> list[dict]:
        i = bisect_right(self._diary_times, as_of)
        day = as_of.date()
        return [e for avail, vt, e in self.diary[:i] if vt.date() == day]

    # ---- time helpers ------------------------------------------------------------------------------------------------------------------------
    def day_index(self, d: _date) -> int:
        return (d - self.first_date).days
