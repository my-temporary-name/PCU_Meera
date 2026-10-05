"""The reading-level usual (spec 4.2b): her typical READING for a context, as of the start of a date.

Two bases:
  clock_time     readings from earlier days within `band_minutes` of the time of day (a circular distance over midnight);
  meal_relative  readings from earlier days at the same number of minutes since a meal of the same kind (bucketed to the nearest `bucket_minutes`).
Reads only observations of earlier days (date index strictly below the as-of day), accepts only readings the baseline's cleaning kept, and writes nothing.
Spread is the population SD, like the Baseline Engine's profile.
"""

import statistics
from bisect import bisect_left

from v0_code.state_engine.inputs import Obs


def percentile(sorted_vals: list[float], q: float) -> float:
    """Linear interpolation between closest ranks (q in 0..100)."""
    if not sorted_vals:
        raise ValueError("no values")
    k = (len(sorted_vals) - 1) * q / 100
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def summarize(vals: list[float]) -> dict:
    s = sorted(vals)
    return {"n": len(s), "median": statistics.median(s), "sd": statistics.pstdev(s) if len(s) > 1 else 0.0, "p10": percentile(s, 10), "p90": percentile(s, 90)}


def bucket_of(minutes: float, bucket: int) -> int:
    """Nearest bucket (half rounds up): 77 -> 75 with 15-minute buckets, 82.5 -> 90."""
    return int((minutes / bucket) + 0.5) * bucket


class ReadingUsual:
    def __init__(self, stream: str, readings: list[tuple[int, int, float, object]], meals: list[tuple], meal_kinds: tuple[str, ...], meal_window: int, bucket: int):
        """readings: (day_index, minute_of_day, value, datetime) of ACCEPTED readings in time order. meals: (datetime, label) in time order."""
        self.stream = stream
        self.meal_kinds = meal_kinds
        self.bucket = bucket
        self.clock: dict[int, tuple[list[int], list[float]]] = {}
        for d, m, v, _ in readings:
            ds, vs = self.clock.setdefault(m, ([], []))
            ds.append(d)
            vs.append(v)
        self.meal: dict[tuple[str, int], tuple[list[int], list[float]]] = {}
        self._cache: dict = {}
        if self.meal_kinds:
            from bisect import bisect_left as bl
            times = [r[3] for r in readings]
            for mt, label in meals:
                kind = self.kind_of(label)
                if kind is None:
                    continue
                i = bl(times, mt)
                while i < len(readings):
                    d, m, v, rt = readings[i]
                    mins = (rt - mt).total_seconds() / 60
                    if mins > meal_window + bucket:
                        break
                    ds, vs = self.meal.setdefault((kind, bucket_of(mins, bucket)), ([], []))
                    ds.append(d)
                    vs.append(v)
                    i += 1
            for ds_vs in self.meal.values():                      # meals are visited in time order, so day indexes are non-decreasing; keep that explicit
                pairs = sorted(zip(*ds_vs))
                ds_vs[0][:] = [p[0] for p in pairs]
                ds_vs[1][:] = [p[1] for p in pairs]

    def kind_of(self, label: str) -> str | None:
        label = (label or "").lower()
        return next((k for k in self.meal_kinds if k in label), None)

    def clock_time(self, day_index: int, minute_of_day: int, band: int) -> dict | None:
        key = ("c", day_index, minute_of_day, band)
        if key in self._cache:
            return self._cache[key]
        vals: list[float] = []
        for m, (ds, vs) in self.clock.items():
            diff = abs(m - minute_of_day)
            if min(diff, 1440 - diff) <= band:
                vals.extend(vs[:bisect_left(ds, day_index)])
        out = {"basis": "clock_time", "context": {"time_of_day": f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}", "band_minutes": band}, **summarize(vals)} if vals else None
        self._cache[key] = out
        return out

    def meal_relative(self, day_index: int, kind: str, minutes_since_meal: float) -> dict | None:
        b = bucket_of(minutes_since_meal, self.bucket)
        key = ("m", day_index, kind, b)
        if key in self._cache:
            return self._cache[key]
        got = self.meal.get((kind, b))
        vals = got[1][:bisect_left(got[0], day_index)] if got else []
        out = {"basis": "meal_relative", "context": {"meal_kind": kind, "minutes_since_meal": b}, **summarize(vals)} if vals else None
        self._cache[key] = out
        return out
