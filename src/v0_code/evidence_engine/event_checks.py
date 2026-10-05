"""Event-level checks (spec 7.3): a percentile against her history like for like, a shape check, descriptive pattern frequencies and a presence fact. They are about this
event only and have no relationship record. Each returns {support, event_specific, event_exposure} (and `reason` when the label is `insufficient`)."""

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import numpy as np

from v0_code.evidence_engine.data import EvidenceData


@dataclass
class EventCtx:
    data: EvidenceData
    cfg: object
    T: datetime                  # the hand-off's opened_at (local)
    D: date                      # the outcome date; history is the days strictly before it
    meal: dict | None            # {"label", "time" (datetime), "kind"} of the hand-off's last meal, or None
    check: dict                  # the library's event check


def _mid(d: date, tz) -> datetime:
    return datetime.combine(d, time(0), tzinfo=tz)


def _percentile(history: list[float], observed: float, worse: str) -> int:
    h = np.asarray(history, float)
    return int(round(100 * float(np.mean(h <= observed + 1e-9) if worse == "higher" else np.mean(h >= observed - 1e-9))))


def _percentile_result(ctx: EventCtx, history: list[float], observed: float, extra: dict) -> dict:
    pc = ctx.cfg.percentile_check
    es = dict(extra)
    es.update(observed=observed, history_n=len(history))
    if history:
        es.update(history_median=round(float(np.median(history)), 1), history_p90=round(float(np.percentile(history, 90)), 1),
                  percentile=_percentile(history, observed, ctx.check.get("worse", "higher")))
    if len(history) < pc["history_min"]:
        return {"support": "insufficient", "reason": "history", "event_specific": es, "event_exposure": None}
    pct = es["percentile"]
    return {"support": "supported" if pct >= pc["supported_min_percentile"] else "not_supported", "event_specific": es,
            "event_exposure": {"state": "exposed" if pct >= 100 * (1 - ctx.cfg.event_exposure["tail_quantile"]) else "not_exposed"}}


def peak_at_elapsed(ctx: EventCtx) -> dict:
    """The highest value so far after the event meal, over the minutes elapsed (rounded to the meal bucket), against the same elapsed-minutes peak after her earlier meals of
    the same kind (all her meals when the event meal has no kind)."""
    if ctx.meal is None:
        return {"support": "insufficient", "reason": "no_meal", "event_specific": {}, "event_exposure": None}
    d, c = ctx.data, ctx.check
    size = d.meal_bucket
    elapsed = int(round((ctx.T - ctx.meal["time"]).total_seconds() / 60))
    bucket = int(math.floor(elapsed / size + 0.5)) * size
    so_far = d.readings_between(c["source"], ctx.meal["time"], ctx.T)
    if not so_far:
        return {"support": "insufficient", "reason": "no_readings", "event_specific": {"elapsed_minutes": elapsed}, "event_exposure": None}
    hist = []
    for r in d.records(c["unit_source"]):
        if r.ts is None or r.ts >= ctx.meal["time"] or (ctx.meal["kind"] is not None and d.event_kind(c["unit_source"], r) != ctx.meal["kind"]):
            continue
        vals = d.readings_between(c["source"], r.ts, r.ts + timedelta(minutes=bucket))
        if vals:
            hist.append(max(vals))
    return _percentile_result(ctx, hist, max(so_far), {"elapsed_minutes": elapsed, "bucket_minutes": bucket, "bucket_size": size})


def hours_since_last_event(ctx: EventCtx) -> dict:
    """Hours since the last meal at the event time against her history of hours since the last meal at the same clock time (nearest 15-minute bucket)."""
    if ctx.meal is None:
        return {"support": "insufficient", "reason": "no_meal", "event_specific": {}, "event_exposure": None}
    d, c = ctx.data, ctx.check
    observed = round((ctx.T - ctx.meal["time"]).total_seconds() / 3600, 2)
    mins = ctx.T.hour * 60 + ctx.T.minute
    b = int(math.floor(mins / 15 + 0.5)) * 15 % 1440
    starts = sorted(r.ts for r in d.records(c["source"]) if r.ts is not None)
    hist = []
    if starts:
        day = starts[0].date()
        while day < ctx.D:
            t = datetime.combine(day, time(b // 60, b % 60), tzinfo=d.tz)
            prev = [s for s in starts if s <= t]
            if prev:
                hist.append((t - prev[-1]).total_seconds() / 3600)
            day += timedelta(days=1)
    return _percentile_result(ctx, hist, observed, {"clock_bucket": f"{b // 60:02d}:{b % 60:02d}"})


def isolated_reading_pending(ctx: EventCtx) -> dict:
    """Written at the event: the check needs readings after it (spec 7.3), so the label waits for a completion."""
    end = ctx.T + timedelta(minutes=int(ctx.check["window_minutes"]))
    return {"support": "not_yet_available", "event_specific": {"earliest_evaluation_time": end.isoformat()}, "event_exposure": None}


def isolated_reading_features(data: EvidenceData, cfg, check: dict, T: datetime, data_until: datetime | None = None) -> dict:
    """Features of the readings around the event reading: isolated (differs from both neighbours), rebound (the next reading returns to the earlier level), a steep drop and the
    overnight window. The neighbours are cleaned readings; the event reading itself is looked up in the raw stream and reported if the cleaning rule removed it."""
    sc, source = cfg.shape_check, check["source"]
    raw = [(r.ts, r.value) for r in data.records(source) if r.ts is not None and r.value is not None and (data_until is None or r.ts <= data_until)]
    cleaned = [(t, v) for t, v in data.readings(source) if data_until is None or t <= data_until]
    target = next((v for t, v in raw if t == T), None)
    prev = next((v for t, v in reversed(cleaned) if t < T), None)
    nxt = next((v for t, v in cleaned if t > T), None)
    out = {"target": target, "previous": prev, "next": nxt, "target_removed_by_cleaning": target is not None and all(t != T for t, _ in cleaned), "overnight": 0 <= T.hour < 6}
    if target is None or prev is None or nxt is None:
        out.update(isolated=None, rebound=None, steep_drop=None)
        return out
    out.update(isolated=abs(target - prev) >= sc["isolated_min_step"] and abs(target - nxt) >= sc["isolated_min_step"],
               rebound=abs(nxt - prev) <= sc["rebound_tolerance"], steep_drop=prev - target >= sc["steep_drop_min"])
    return out


def shape_support(features: dict) -> str:
    if features["isolated"] is None:
        return "insufficient"
    return "supported" if features["isolated"] and features["rebound"] else "not_supported"


def rise_in_window(ctx: EventCtx) -> dict:
    """The share of earlier mornings with a rise (the highest reading minus the lowest reading before it) of at least the configured size within the configured window."""
    pr = ctx.cfg.pattern_repeat
    a, b = pr["dawn_window"].split("-")
    (h0, m0), (h1, m1) = (int(x) for x in a.split(":")), (int(x) for x in b.split(":"))
    d = ctx.data
    by_day: dict[date, list[float]] = {}
    for t, v in d.readings(ctx.check["source"]):
        if t.date() < ctx.D and time(h0, m0) <= t.time() <= time(h1, m1):
            by_day.setdefault(t.date(), []).append(v)
    days = rises = 0
    for vals in by_day.values():
        if len(vals) < 2:
            continue
        days += 1
        low, best = vals[0], 0.0
        for v in vals[1:]:
            best, low = max(best, v - low), min(low, v)
        rises += best >= pr["dawn_min_rise"]
    es = {"window": pr["dawn_window"], "n_days": days, "n_rise_days": rises, "share": round(rises / days, 4) if days else None}
    if days < pr["min_days"]:
        return {"support": "insufficient", "reason": "history", "event_specific": es, "event_exposure": None}
    return {"support": "supported" if rises / days >= pr["min_share"] else "not_supported", "event_specific": es, "event_exposure": None}


def rate_by_group(ctx: EventCtx) -> dict:
    """Descriptive: the rate of matching records (for example misses) per group over her earlier days."""
    c, d = ctx.check, ctx.data
    strip = getattr(ctx.cfg.baseline, c["strip_regex_ref"].split(".", 1)[1]) if c.get("strip_regex_ref") else ""
    field, m = c["group_field"], c["match"]
    groups: dict[str, list[int]] = {}
    for r in d.records(c["source"]):
        if r.date >= ctx.D:
            continue
        name = re.sub(strip, "", getattr(r, field) or "") if strip else (getattr(r, field) or "")
        g = groups.setdefault(name, [0, 0])
        g[1] += 1
        g[0] += getattr(r, m["field"]) == m["equals"]
    rates = {k: {"n_match": v[0], "total": v[1], "rate": round(v[0] / v[1], 4)} for k, v in sorted(groups.items())}
    return {"support": "not_applicable", "event_specific": {"rates": rates}, "event_exposure": None}


def presence(ctx: EventCtx) -> dict:
    flags = ctx.cfg.presence_flags.get(ctx.check["facts"], {})
    return {"support": "not_applicable", "event_specific": {"present": any(bool(v) for v in flags.values())}, "event_exposure": None}


CHECKS = {"peak_at_elapsed": peak_at_elapsed, "hours_since_last_event": hours_since_last_event, "isolated_reading": isolated_reading_pending, "rise_in_window": rise_in_window,
          "rate_by_group": rate_by_group, None: presence}
