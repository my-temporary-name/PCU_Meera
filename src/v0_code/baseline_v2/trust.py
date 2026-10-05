"""Trust layer (spec section 5): clean first, then compute.

A questionable reading is removed BEFORE any metric, delta, anchor or tag is computed. The raw values are recorded, and a caveat shows
what the metrics would have been with them included. The detector is generic — device range and a maximum jump from config, no
hard-coded values. (Known upstream limit, reported not patched: five isolated readings of exactly 65.0 mg/dL pass both rules.)
"""

from dataclasses import dataclass

from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.data import Reading
from v0_code.logic.baseline_glucose import _metrics  # the verified ADA formulas (mean, GMI, TIR 70-180, TAR >180/>250, TBR <70/<54, %CV)

# NOTE (by design, not a bug): these glucose bands are ADA *management* bands (70/180/250/54). They are allowed to disagree with the
# Threshold Evaluator's fasting-glucose status bands (70/99/125, diagnostic); one reading can be 'high' there and in range here.

METRIC_KEYS = ("mean", "gmi_pct", "tir_pct", "tar_pct", "tar_severe_pct", "tbr_pct", "tbr_severe_pct", "cv_pct")


@dataclass(frozen=True)
class Removed:
    ts: str
    value: float
    reason: str
    date: str = ""     # local calendar day of the reading


def clean_series(series: list[Reading], cfg: Config) -> tuple[list[Reading], list[Removed]]:
    """Walk the whole timeline once (so a spike at midnight is judged against the previous day's last reading). A reading is removed when
    it is outside the device range, or it differs from the last KEPT reading by more than max_step_change_per_15min, scaled by the gap in
    15-minute units. Only earlier readings are looked at, so the result for a day never depends on later data."""
    lo, hi = cfg.device_range
    kept: list[Reading] = []
    removed: list[Removed] = []
    for r in series:
        if not lo <= r.value <= hi:
            removed.append(Removed(r.ts, r.value, f"outside the device range ({lo:g}-{hi:g})", r.dt.date().isoformat()))
            continue
        if kept:
            gap_units = max(1.0, (r.dt - kept[-1].dt).total_seconds() / 900)
            if abs(r.value - kept[-1].value) > cfg.max_step_change_per_15min * gap_units:
                removed.append(Removed(r.ts, r.value, f"a jump of more than {cfg.max_step_change_per_15min:g} mg/dL per 15 minutes", r.dt.date().isoformat()))
                continue
        kept.append(r)
    return kept, removed


def glucose_metrics(values: list[float], expected: int) -> dict | None:
    if not values:
        return None
    m = _metrics(values, expected)
    m["min_value"], m["max_value"] = min(values), max(values)
    return m


def with_questionable(kept_vals: list[float], removed_vals: list[float], expected: int) -> dict:
    """What the metrics would have been had the removed readings been kept — only the metrics that actually differ."""
    if not removed_vals or not kept_vals:
        return {}
    clean, raw = glucose_metrics(kept_vals, expected), glucose_metrics(kept_vals + removed_vals, expected)
    return {k: raw[k] for k in (*METRIC_KEYS, "min_value", "max_value") if raw[k] != clean[k]}


def max_gap_hours(kept: list[Reading]) -> float:
    return max(((b.dt - a.dt).total_seconds() / 3600 for a, b in zip(kept, kept[1:])), default=0.0)


def is_reliable(completeness_pct: float, days_of_data_so_far: int, cfg: Config) -> bool:
    """Reliable = enough completeness AND enough days of data so far. This adapts the ADA 14-day / 70% AGP-reliability guidance to
    window level; it is not a verbatim restatement of it."""
    return completeness_pct >= cfg.reliable_completeness_pct and days_of_data_so_far >= cfg.min_days_for_compare


def confidence(reliable: bool, completeness_pct: float) -> str:
    """high = reliable and completeness >= 90; moderate = reliable (so >= the reliability threshold); low otherwise."""
    if reliable and completeness_pct >= 90:
        return "high"
    return "moderate" if reliable else "low"
