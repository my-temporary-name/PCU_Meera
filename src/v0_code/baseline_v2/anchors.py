"""Anchors (spec section 6): config-driven thresholds, evaluated on CLEANED values.

`adherence_meds_changed` counts medicines that got WORSE (taken -> missed) and `adherence_pct_change` fires only on a DROP; a recovery is not a
crossing (it still shows in "what changed").

A crossing that exists only because of a removed reading is not counted; it is returned separately as `questionable`, found by evaluating
the same anchors on the raw (not cleaned) values and taking the difference. `is_notable = len(crossed) > 0`, decided here, never by the LLM.
These thresholds are starting heuristics, not clinical standards, and are not retuned here — only fire rates are reported.
"""

from v0_code.baseline_v2.config import Config, resolve_threshold

TIER_KEY = {"day": "day", "week": "week", "month": "month"}
ANCHOR_ORDER = ["glucose_TIR_change_points", "glucose_CV_change_points", "glucose_GMI_change", "severe_range_appeared_or_cleared", "sleep_hours_change",
                "resting_hr_change_bpm", "adherence_meds_changed", "adherence_pct_change", "steps_abs_change", "lab_cgm_discordance"]

# anchor -> the stream it measures (used to avoid listing the same measure twice among the material changes)
ANCHOR_STREAM = {"glucose_TIR_change_points": "time_in_range", "glucose_CV_change_points": "variability", "glucose_GMI_change": "cgm_glucose_reading",
                 "sleep_hours_change": "sleep_duration", "resting_hr_change_bpm": "resting_heart_rate", "adherence_pct_change": "medication_adherence",
                 "adherence_meds_changed": "medication_adherence", "steps_abs_change": "step_count"}

# anchors that fire on a change in ONE direction only (a drop); the other direction still shows in "what changed"
DROP_ONLY = {"adherence_pct_change"}

# anchor -> (key in the deltas dict, plain label, unit)
SOURCE = {
    "glucose_TIR_change_points": ("tir", "time in range", "percentage points"), "glucose_CV_change_points": ("cv", "variability", "percentage points"),
    "glucose_GMI_change": ("gmi", "GMI", "points"), "sleep_hours_change": ("sleep", "sleep", "hours"),
    "resting_hr_change_bpm": ("resting_hr", "resting heart rate", "bpm"), "adherence_pct_change": ("adherence_pct", "medication adherence", "percentage points"),
    "steps_abs_change": ("steps", "steps", "steps"),
}


def _threshold(cfg: Config, name: str, tier: str):
    a = cfg.anchors.get(name)
    if not a:
        return None
    key = "week_mean" if (name == "steps_abs_change" and tier == "week") else TIER_KEY[tier]
    return a.thresholds.get(key, a.thresholds.get("any"))


def configured_for(cfg: Config, tier: str) -> list[str]:
    return [n for n in ANCHOR_ORDER if _threshold(cfg, n, tier) not in (None, False)]


def evaluate(cfg: Config, tier: str, deltas: dict, n_meds: int) -> list[str]:
    """deltas: tir, cv, gmi, sleep, resting_hr, steps, adherence_pct, meds_changed, severe_curr, severe_prior, lab_gap — None when unknown.
    Strictly greater than the threshold fires (equal does not), except meds_changed (>= the resolved count) and the lab gap (>=, inclusive)."""
    crossed: list[str] = []
    for name in configured_for(cfg, tier):
        th = _threshold(cfg, name, tier)
        if name in SOURCE:
            v = deltas.get(SOURCE[name][0])
            if v is not None and (-v if name in DROP_ONLY else abs(v)) > float(th):
                crossed.append(name)
        elif name == "severe_range_appeared_or_cleared":
            c, p = deltas.get("severe_curr"), deltas.get("severe_prior")
            if c is not None and p is not None and (p > 0) != (c > 0):
                crossed.append(name)
        elif name == "adherence_meds_changed":
            k = deltas.get("meds_changed")
            if k is not None and k >= resolve_threshold(th, n_meds) and k > 0:
                crossed.append(name)
        elif name == "lab_cgm_discordance":
            g = deltas.get("lab_gap")
            if g is not None and abs(g) >= float(th):
                crossed.append(name)
    return crossed


def split_questionable(cfg: Config, tier: str, clean: dict, raw: dict, n_meds: int) -> tuple[list[str], list[str]]:
    """(anchors crossed on cleaned values, anchors that crossed ONLY on the raw values)."""
    crossed = evaluate(cfg, tier, clean, n_meds)
    return crossed, [a for a in evaluate(cfg, tier, raw, n_meds) if a not in crossed]
