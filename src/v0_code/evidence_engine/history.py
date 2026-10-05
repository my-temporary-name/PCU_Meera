"""The history table (spec 7.1) of one relationship. The per-unit exposure and detrended outcome do not depend on the as-of date (they use only earlier values and
the ordering rule), so they are computed once; `at(D)` then selects the units whose whole window ended before the start of D, applies the quantile binarization
as-of D, orients both sides and hashes the rows used."""

import hashlib
import math
from dataclasses import dataclass
from datetime import date, datetime, time

import numpy as np

from v0_code.evidence_engine.exposures import MISSING, UNORDERED, ExposureEvaluator
from v0_code.evidence_engine.units import Unit


@dataclass
class Hist:
    x: np.ndarray                  # oriented exposure (higher = riskier); 0/1 when binary
    y: np.ndarray                  # oriented, detrended outcome (higher = worse)
    first_day: date | None
    last_day: date | None
    dates: np.ndarray              # ordinal of the outcome date of every row used
    n_complete: int                # units whose whole window ended before the as-of start
    n_dropped_by_detrend: int      # complete units with an exposure and an outcome but too few earlier values for the baseline
    n_unordered: int               # complete units dropped because nothing had been recorded before the unit's start (ordering rule)
    n_missing: int                 # complete units dropped for a missing exposure
    inputs_hash: str
    threshold: float | None = None


class Series:
    def __init__(self, ev: ExposureEvaluator, outcome: dict, exposure: dict, tag: str, excludes: bool, units: list[Unit]):
        self.outcome, self.exposure, self.units = outcome, exposure, units
        n = len(units)
        self.end = np.array([u.end.timestamp() for u in units])
        self.start = np.array([u.start.timestamp() for u in units])
        self.dates = [u.date for u in units]
        self.y = np.array([u.resid for u in units])
        self.x_raw = np.full(n, math.nan)
        self.reason = np.zeros(n, dtype=np.int8)                                  # 0 ok, 1 missing, 2 unordered
        for i, u in enumerate(units):
            v, r = ev.value(exposure, tag, outcome, u, excludes)
            if v is None:
                self.reason[i] = 2 if r == UNORDERED else 1
            else:
                self.x_raw[i] = v
        self.binary = exposure["form"] == "binary"
        self.binarize = exposure.get("binarize")
        self.sign_y = -1.0 if outcome["worse_is"] == "lower" else 1.0
        self.sign_x = -1.0 if (exposure["form"] == "continuous" and exposure["risk_side"] == "low") else 1.0

    def n_complete_before(self, D: date, tz) -> int:
        return int(np.searchsorted(self.end, datetime.combine(D, time(0), tzinfo=tz).timestamp(), side="right"))

    def at(self, D: date, tz) -> Hist:
        k = self.n_complete_before(D, tz)
        xr, y = self.x_raw[:k], self.y[:k]
        has_x = ~np.isnan(xr)
        used = has_x & ~np.isnan(y)
        threshold = None
        if self.binarize:
            ref = xr[has_x]
            threshold = float(np.quantile(ref, self.binarize["quantile"])) if len(ref) else None
            x = (xr >= threshold).astype(float) if threshold is not None else xr
        else:
            x = xr
        xs = x[used] * (self.sign_x if not self.binary else 1.0)
        ys = y[used] * self.sign_y
        idx = np.flatnonzero(used)
        h = hashlib.sha256()
        h.update(np.round(self.start[:k][used], 0).tobytes())
        h.update(np.round(xs, 9).tobytes())
        h.update(np.round(ys, 9).tobytes())
        h.update(repr(threshold).encode())
        ords = np.array([self.dates[i].toordinal() for i in idx], dtype=np.int64)
        return Hist(x=xs, y=ys, dates=ords, first_day=self.dates[idx[0]] if len(idx) else None, last_day=self.dates[idx[-1]] if len(idx) else None, n_complete=k,
                    n_dropped_by_detrend=int((has_x & np.isnan(y)).sum()), n_unordered=int((self.reason[:k] == 2).sum()), n_missing=int((self.reason[:k] == 1).sum()),
                    inputs_hash=h.hexdigest()[:16], threshold=threshold)

    def reference(self, D: date, tz) -> np.ndarray:
        """The raw exposure values of every complete unit as of D (the distribution an event value is placed in)."""
        xr = self.x_raw[:self.n_complete_before(D, tz)]
        return xr[~np.isnan(xr)]

    def exposed_dates(self, D: date, tz, tail_quantile: float) -> tuple[set, set]:
        """(all dates with a used row, the dates on which the factor was exposed): a binary exposure as it is, a continuous one in its worse quartile. A date counts as
        exposed if any of its units is (spec 7.2, overlap)."""
        h = self.at(D, tz)
        if len(h.x) == 0:
            return set(), set()
        flag = (h.x == 1) if self.binary else (h.x >= np.quantile(h.x, 1 - tail_quantile))
        return set(h.dates.tolist()), set(h.dates[flag].tolist())
