"""Baseline Engine, glucose slice: deterministic CGM window metrics (ADA consensus set).

No LLM here — this module only computes numbers. The LLM step (nodes/baseline_engine.py)
takes its output and adds a judgment layer on top; it never recomputes anything below.

Windows: one 'day' window per calendar date, and one rolling 'week' window (trailing 7
calendar days) ending on every date. Both compare against the adjacent prior window of the
same type (day vs day-1; week vs the preceding non-overlapping 7-day window) wherever one
exists. A window is 'reliable' when it has >=70% of its expected 15-min readings AND falls on
or after the 14th calendar day of the whole dataset — an adaptation of the ADA's 14-day/70%
AGP-reliability rule to per-window granularity, not a verbatim restatement of it.
"""

import statistics
from collections import defaultdict

from v0_code.graph.state import GlucoseWindow

# NOTE (by design, not a bug): these TIR/TAR/TBR bands (70/180/250/54, ADA management metrics) differ from
# the Threshold Evaluator's fasting-glucose status cut-offs (70/99/125, diagnostic). Don't "reconcile" them.
EXPECTED_PER_DAY = 96  # 15-minute cadence over 24 hours
MIN_RELIABLE_DAY_INDEX = 13  # 0-based: the 14th calendar day of the dataset


def _metrics(values: list[float], expected: int) -> dict[str, float | int]:
    n = len(values)
    mean = statistics.fmean(values)
    cv = round(100 * statistics.pstdev(values) / mean, 2) if mean else 0.0

    def pct(pred) -> float:
        return round(100 * sum(1 for v in values if pred(v)) / n, 2)

    return {
        "n_readings": n,
        "completeness_pct": round(100 * n / expected, 2),
        "mean": round(mean, 2),
        "gmi_pct": round(3.31 + 0.02392 * mean, 2),
        "tir_pct": pct(lambda v: 70 <= v <= 180),
        "tar_pct": pct(lambda v: v > 180),
        "tar_severe_pct": pct(lambda v: v > 250),
        "tbr_pct": pct(lambda v: v < 70),
        "tbr_severe_pct": pct(lambda v: v < 54),
        "cv_pct": cv,
    }


def _deltas(curr: dict, prior: dict | None) -> dict[str, float | None]:
    if prior is None:
        return {"delta_mean": None, "delta_tir_pct": None, "delta_cv_pct": None, "delta_gmi_pct": None}
    return {
        "delta_mean": round(curr["mean"] - prior["mean"], 2),
        "delta_tir_pct": round(curr["tir_pct"] - prior["tir_pct"], 2),
        "delta_cv_pct": round(curr["cv_pct"] - prior["cv_pct"], 2),
        "delta_gmi_pct": round(curr["gmi_pct"] - prior["gmi_pct"], 2),
    }


def compute_glucose_windows(readings: list[tuple[str, float]]) -> list[GlucoseWindow]:
    """readings: (timestamp, value) pairs for cgm_glucose_reading, any order."""
    by_date: dict[str, list[float]] = defaultdict(list)
    for ts, value in readings:
        by_date[ts[:10]].append(value)
    dates = sorted(by_date)

    windows: list[GlucoseWindow] = []

    # Day windows
    day_metrics: dict[str, dict] = {}
    for i, date in enumerate(dates):
        values = by_date[date]
        if not values:
            continue
        m = _metrics(values, EXPECTED_PER_DAY)
        day_metrics[date] = m
        prior = day_metrics.get(dates[i - 1]) if i > 0 else None
        windows.append(
            GlucoseWindow(
                window_type="day",
                window_start=date,
                window_end=date,
                reliable=m["completeness_pct"] >= 70 and i >= MIN_RELIABLE_DAY_INDEX,
                **m,
                **_deltas(m, prior),
            )
        )

    # Week windows: rolling trailing 7 calendar days, ending on every date from the 7th onward.
    week_metrics: dict[int, dict] = {}  # keyed by the index of the window's end date
    for i, date in enumerate(dates):
        if i < 6:
            continue
        values = [v for d in dates[i - 6 : i + 1] for v in by_date[d]]
        m = _metrics(values, EXPECTED_PER_DAY * 7)
        week_metrics[i] = m
        prior = week_metrics.get(i - 7)  # the immediately preceding, non-overlapping 7-day window
        windows.append(
            GlucoseWindow(
                window_type="week",
                window_start=dates[i - 6],
                window_end=date,
                reliable=m["completeness_pct"] >= 70 and i >= MIN_RELIABLE_DAY_INDEX,
                **m,
                **_deltas(m, prior),
            )
        )

    return windows
