"""Which readings are questionable, which metrics each data-quality flag touches, and the metrics
recomputed without those readings.

Why: a sensor artifact (a clipped 65.0, a 599 spike) distorts only some metrics. The earlier
entries applied "may reflect a questionable reading" to whatever the model felt like (TIR and
variability for a clipped low reading that only touches time below range). So every flag now
carries an `affects` list in code, the model-facing copy attaches the caveat next to those metrics
only, and the entry is built on values recomputed *without* the questionable readings.

Everything here is deterministic; the LLM only sees the result.
"""

from datetime import datetime

from v0_code.logic.baseline_glucose import _deltas, _metrics

KNOWN_CLIP_ARTIFACT_VALUE = 65.0
MAX_READING_FLAG_THRESHOLD = 400
IMPLAUSIBLE_RATE_MG_DL_PER_15MIN = 100.0  # config; optional sensor-artifact signal

# Internal metric keys each flag touches. "Glucose metrics" use the keys of the window metrics dict
# (cv_pct, tar_pct, ...); the delta/post-meal keys let the note ride on the changes and meal peaks too.
_SPIKE_AFFECTS = ["max_value", "tar_pct", "tar_severe_pct", "cv_pct", "glucose_cv_pct",
                  "glucose_severe_total_curr", "glucose_severe_total_prior",
                  "peak_glucose", "post_meal_peak_mean", "post_meal_peak_max"]
FLAG_AFFECTS: dict[str, list[str]] = {
    "known_clip_artifact_reading": ["tbr_pct", "tbr_severe_pct", "min_value"],  # 65.0 is above 54, so severe totals are untouched
    "max_reading_above_400": _SPIKE_AFFECTS,
    "implausible_rate_of_change": _SPIKE_AFFECTS + ["tbr_pct", "tbr_severe_pct", "min_value"],
    "gap_hours": ["completeness_pct", "n_readings"],
    "known_discrepancy": [],  # informational (spec vs data); touches no metric
}
# low_completeness:<stream>:<pct> -> the stream's own metric keys
LOW_COMPLETENESS_AFFECTS: dict[str, list[str]] = {
    "cgm_glucose_reading": ["completeness_pct", "n_readings"],
    "step_count": ["total_steps", "activity_steps", "activity_steps_mean"],
    "sleep_duration": ["duration_hours", "sleep_hours"],
    "continuous_heart_rate": ["continuous_mean", "resting_period_mean", "resting_hr_mean"],
    "resting_heart_rate": ["resting_heart_rate_daily"],
}
ARTIFACT_FLAGS = ("known_clip_artifact_reading", "max_reading_above_400", "implausible_rate_of_change")


def flag_affects(flag: str) -> list[str]:
    name = flag.split(":")[0]
    if name == "low_completeness":
        parts = flag.split(":")
        return LOW_COMPLETENESS_AFFECTS.get(parts[1], [parts[1]]) if len(parts) > 1 else []
    return FLAG_AFFECTS.get(name, [])


def flag_details(flags: list[str], window: str = "this window") -> list[dict]:
    """[{flag, affects, window}] — what each flag touches. `window` is 'this window' or 'previous window'."""
    return [{"flag": f, "affects": flag_affects(f), "window": window} for f in flags]


def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def questionable_timestamps(readings: list[tuple[str, float]]) -> set[str]:
    """Timestamps of readings code treats as questionable: the known clipped value, anything above
    the 400 ceiling, and the endpoint of an implausible jump that sits farther from the day's median.
    readings: one day's (timestamp, value) pairs, any order."""
    r = sorted(readings)
    out = {ts for ts, v in r if v == KNOWN_CLIP_ARTIFACT_VALUE or v > MAX_READING_FLAG_THRESHOLD}
    if len(r) > 1:
        vals = sorted(v for _, v in r)
        median = vals[len(vals) // 2]
        for (t0, v0), (t1, v1) in zip(r, r[1:]):
            steps = max((_dt(t1) - _dt(t0)).total_seconds() / 900, 1e-9)
            if abs(v1 - v0) / steps > IMPLAUSIBLE_RATE_MG_DL_PER_15MIN:
                out.add(t0 if abs(v0 - median) > abs(v1 - median) else t1)
    return out


# Metrics worth a "without the questionable readings" twin. Everything _metrics returns, so a caller
# can substitute whichever it needs; only the ones that actually differ are kept.
def cleaned_metrics(readings: list[tuple[str, float]], questionable: set[str], expected: int) -> dict | None:
    """Window metrics recomputed without the questionable readings, as a dict holding only the metrics
    that differ from the raw ones, plus how many readings were excluded. None when nothing was excluded
    (or nothing would remain)."""
    drop = [(ts, v) for ts, v in readings if ts in questionable]
    keep = [v for ts, v in readings if ts not in questionable]
    if not drop or not keep:
        return None
    raw_vals = [v for _, v in readings]
    raw = {**_metrics(raw_vals, expected), "min_value": min(raw_vals), "max_value": max(raw_vals)}
    clean = {**_metrics(keep, expected), "min_value": min(keep), "max_value": max(keep)}
    differing = {k: clean[k] for k in clean if clean[k] != raw[k] and k not in ("n_readings", "completeness_pct")}
    return {
        "n_excluded": len(drop),
        "excluded_values": sorted(v for _, v in drop),
        "excluded_readings": [{"time": ts, "value": v} for ts, v in sorted(drop)][:20],  # when, for the code-written caveat
        "metrics_without_them": differing,
        "metrics_with_them": {k: raw[k] for k in differing},
    }


def cleaned_deltas(curr: list[tuple[str, float]], prior: list[tuple[str, float]] | None, questionable: set[str],
                   curr_expected: int, prior_expected: int, keys: set[str]) -> dict | None:
    """The window-over-window glucose changes recomputed without questionable readings in EITHER window (a
    spike in the prior window leaving is as misleading as one arriving). Same shape as cleaned_metrics:
    only the changes that differ from the raw ones, `keys` limiting which record delta keys are considered
    (the record's own `deltas` keys). None when neither window holds a questionable reading."""
    excluded = [v for ts, v in (curr + (prior or [])) if ts in questionable]
    keep_c = [v for ts, v in curr if ts not in questionable]
    keep_p = [v for ts, v in (prior or []) if ts not in questionable]
    if not excluded or not keep_c or (prior and not keep_p):
        return None

    def both(readings_vals: list[float], expected: int) -> dict:
        return _metrics(readings_vals, expected)

    raw_c, clean_c = both([v for _, v in curr], curr_expected), both(keep_c, curr_expected)
    raw_p = both([v for _, v in prior], prior_expected) if prior else None
    clean_p = both(keep_p, prior_expected) if prior else None
    raw_d, clean_d = _deltas(raw_c, raw_p), _deltas(clean_c, clean_p)
    sev = lambda m: round(m["tar_severe_pct"] + m["tbr_severe_pct"], 2)
    raw = {"glucose_tir_pct": raw_d["delta_tir_pct"], "glucose_cv_pct": raw_d["delta_cv_pct"], "glucose_gmi_pct": raw_d["delta_gmi_pct"],
           "glucose_mean": raw_d["delta_mean"], "glucose_severe_total_curr": sev(raw_c), "glucose_severe_total_prior": sev(raw_p) if raw_p else None}
    clean = {"glucose_tir_pct": clean_d["delta_tir_pct"], "glucose_cv_pct": clean_d["delta_cv_pct"], "glucose_gmi_pct": clean_d["delta_gmi_pct"],
             "glucose_mean": clean_d["delta_mean"], "glucose_severe_total_curr": sev(clean_c), "glucose_severe_total_prior": sev(clean_p) if clean_p else None}
    differing = [k for k in raw if k in keys and clean[k] is not None and clean[k] != raw[k]]
    if not differing:
        return None
    return {"n_excluded": len(excluded), "excluded_values": sorted(excluded),
            "metrics_without_them": {k: clean[k] for k in differing}, "metrics_with_them": {k: raw[k] for k in differing}}


def effective_deltas(deltas: dict) -> dict:
    """The window-over-window changes with questionable readings removed: every change that
    `questionable_excluded` recomputed takes its cleaned value. Anchors, the rendered "what changed" section and
    the model all read this, never the raw values — an alarm that exists only because of a sensor artifact is not
    an alarm. The raw changes stay in the record's `deltas` untouched."""
    out = {k: v for k, v in deltas.items() if k != "questionable_excluded"}
    q = deltas.get("questionable_excluded")
    if q:
        out.update(q["metrics_without_them"])
    return out
