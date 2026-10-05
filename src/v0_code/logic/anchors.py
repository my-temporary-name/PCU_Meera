"""Anchor thresholds and code-side evaluation (spec change A: anchors_crossed is computed by
code, not the LLM — the LLM only explains an already-determined crossing list).

These are engineering defaults, not clinical standards, and are deliberately config, not
buried in logic, so they can be tuned per patient/stream without touching code.
"""

ANCHORS: dict[str, dict] = {
    "day": {
        "glucose_TIR_change_points": 10,
        "glucose_CV_change_points": 8,
        "severe_range_appeared_or_cleared": True,
        "sleep_hours_change": 1.5,
        "resting_hr_change_bpm": 8,
        "steps_change_abs": 3000,
        # resolved per-record as min(2, n_meds), so it still works for a 1-medication patient
        "adherence_meds_changed_base": 2,
    },
    "week": {
        "glucose_TIR_change_points": 10,
        "glucose_CV_change_points": 8,
        "glucose_GMI_change": 0.3,
        "severe_range_appeared_or_cleared": True,
        "sleep_hours_change": 1.5,
        "resting_hr_change_bpm": 8,
        "steps_mean_change_abs": 1500,
        "adherence_pct_change": 15,
    },
    "month": {
        "glucose_TIR_change_points": 10,
        "glucose_CV_change_points": 8,
        "glucose_GMI_change": 0.2,
        "severe_range_appeared_or_cleared": True,
        "sleep_hours_change": 1.5,
        "resting_hr_change_bpm": 8,
        "adherence_pct_change": 10,
        # |lab HbA1c - GMI over the 90 days before the lab| >= this (inclusive), for a lab drawn within the checkpoint's 30 days.
        "lab_cgm_discordance": 0.5,
    },
}


def _severe_appeared_or_cleared(curr_severe_total: float, prior_severe_total: float | None) -> bool:
    if prior_severe_total is None:
        return False
    was_present, now_present = prior_severe_total > 0, curr_severe_total > 0
    return was_present != now_present


def evaluate_anchors(tier: str, deltas: dict, n_meds: int) -> list[str]:
    """deltas: the record's flat 'deltas' dict (see logic/memory_records.py for its shape).
    Returns the list of anchor names crossed — empty list means is_notable MUST be false."""
    a = ANCHORS[tier]
    crossed: list[str] = []

    def crossed_if(name: str, value: float | None, threshold: float) -> None:
        if value is not None and abs(value) > threshold:
            crossed.append(name)

    crossed_if("glucose_TIR_change_points", deltas.get("glucose_tir_pct"), a["glucose_TIR_change_points"])
    crossed_if("glucose_CV_change_points", deltas.get("glucose_cv_pct"), a["glucose_CV_change_points"])
    if "glucose_GMI_change" in a:
        crossed_if("glucose_GMI_change", deltas.get("glucose_gmi_pct"), a["glucose_GMI_change"])
    if _severe_appeared_or_cleared(deltas.get("glucose_severe_total_curr", 0.0), deltas.get("glucose_severe_total_prior")):
        crossed.append("severe_range_appeared_or_cleared")
    crossed_if("sleep_hours_change", deltas.get("sleep_hours"), a["sleep_hours_change"])
    crossed_if("resting_hr_change_bpm", deltas.get("resting_hr_mean"), a["resting_hr_change_bpm"])
    if "lab_cgm_discordance" in a:  # month tier only; the one inclusive (>=) threshold, as specified
        gap = deltas.get("lab_cgm_gap")
        if gap is not None and abs(gap) >= a["lab_cgm_discordance"]:
            crossed.append("lab_cgm_discordance")

    if tier == "day":
        crossed_if("steps_change_abs", deltas.get("activity_steps"), a["steps_change_abs"])
        threshold = min(a["adherence_meds_changed_base"], n_meds) if n_meds else a["adherence_meds_changed_base"]
        meds_changed = deltas.get("adherence_meds_changed_count")
        if meds_changed is not None and meds_changed >= threshold:
            crossed.append("adherence_meds_changed")
    else:
        if tier == "week":
            crossed_if("steps_mean_change_abs", deltas.get("activity_steps_mean"), a["steps_mean_change_abs"])
        crossed_if("adherence_pct_change", deltas.get("adherence_overall_pct"), a["adherence_pct_change"])

    return crossed


# An anchor crossing is "questionable" when it is driven by a reading code already flagged as a
# probable sensor artifact. The window's data_quality_flags decide that, never the LLM.
QUESTIONABLE_WHEN_ARTIFACT = {"severe_range_appeared_or_cleared"}
ARTIFACT_FLAG_PREFIXES = ("max_reading_above_400", "known_clip_artifact_reading", "implausible_rate_of_change")


def questionable_anchors(crossed: list[str], scope_flags: list[str]) -> list[str]:
    """scope_flags: flags of the window AND its prior window (a 'cleared' crossing is the prior
    window's artifact leaving, so the prior window's flags matter too)."""
    if not any(f.startswith(ARTIFACT_FLAG_PREFIXES) for f in scope_flags):
        return []
    return [a for a in crossed if a in QUESTIONABLE_WHEN_ARTIFACT]


# Every anchor name evaluate_anchors can emit, per tier. The unit tests assert this list matches reality
# (each fires on a synthetic trigger, stays silent on a quiet window), and the final report lists any
# configured anchor that never fired across the real data ("dead anchors").
ANCHOR_NAMES: dict[str, list[str]] = {
    "day": ["glucose_TIR_change_points", "glucose_CV_change_points", "severe_range_appeared_or_cleared",
            "sleep_hours_change", "resting_hr_change_bpm", "steps_change_abs", "adherence_meds_changed"],
    "week": ["glucose_TIR_change_points", "glucose_CV_change_points", "glucose_GMI_change", "severe_range_appeared_or_cleared",
             "sleep_hours_change", "resting_hr_change_bpm", "steps_mean_change_abs", "adherence_pct_change"],
    "month": ["glucose_TIR_change_points", "glucose_CV_change_points", "glucose_GMI_change", "severe_range_appeared_or_cleared",
              "sleep_hours_change", "resting_hr_change_bpm", "adherence_pct_change", "lab_cgm_discordance"],
}


def anchor_fire_report(crossed_by_tier: dict[str, list[list[str]]]) -> dict[str, dict]:
    """crossed_by_tier: tier -> one anchors_crossed list per window. Returns per-tier fire counts/rates,
    the share of windows with any crossing, and the configured anchors that never fired."""
    out: dict[str, dict] = {}
    for tier, windows in crossed_by_tier.items():
        n = len(windows)
        counts = {name: sum(1 for w in windows if name in w) for name in ANCHOR_NAMES[tier]}
        any_crossed = sum(1 for w in windows if w)
        out[tier] = {
            "windows": n,
            "any_crossed": any_crossed,
            "any_crossed_pct": round(100 * any_crossed / n, 1) if n else 0.0,
            "fired": {k: {"windows": v, "pct": round(100 * v / n, 1) if n else 0.0} for k, v in counts.items()},
            "dead": [k for k, v in counts.items() if v == 0],
        }
    return out
