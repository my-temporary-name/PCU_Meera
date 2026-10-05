"""Model-facing copy of a record: the same numbers under plain-English keys with units.

Why this exists: the stored record uses internal key names (`mean_per_day`, `n_days`,
`tir_pct`). Those names are the strongest wording signal in the prompt, so the model echoed
them into prose and the voice check rejected the entry. Instead of asking the model to avoid
words we put in front of it, we rename them: the prompt gets "average per day", "number of
days", "time in range percent", and an echo now reads like ordinary English.

The stored `record_json` is untouched — only the prompt copy is renamed. `to_plain` also
returns a path map (plain dotted path -> internal dotted path) so evidence_refs the model
writes against the plain copy resolve back into the real record in code.

`annotate` is the step before `to_plain`: it applies the questionable-reading handling (cleaned values in
place, a note beside each affected metric, raw values only in a separate section) and swaps the code-side
co-movement tables for what the model needs. The validator checks against the annotated record too, so what
the model was shown and what it is checked against can never drift apart.

Labels depend on where a key sits: `mean` is a glucose mean in the glucose section but a
per-day average inside `aggregates`, and every key under `deltas` is a change. CONTEXT_MAPS
switches the label map for a whole subtree.
"""

import copy
import re
from typing import Any

from v0_code.logic.data_quality import flag_affects
from v0_code.logic.registry import REGISTRY

# Default labels: internal key -> plain English (with unit where there is one).
LABELS: dict[str, str] = {
    # structure
    "window_id": "window id", "tier": "tier", "date": "date", "start_date": "start date", "end_date": "end date",
    "glucose_by_period": "glucose by time of day", "post_meal": "after meals", "blood_pressure": "blood pressure",
    "heart_rate": "heart rate", "adherence": "medication adherence", "lifestyle": "lifestyle",
    "diary_events": "diary events", "events_in_window": "diary events", "recurring_in_window": "repeating patterns",
    "other_threshold_crossings": "other measures out of range", "completeness_by_stream": "data completeness percent",
    "deltas": "changes vs previous window", "stream_direction_table": "direction vs previous window",
    "deltas_vs_cumulative": "difference from her own history", "co_movement_candidates": "moved together with glucose",
    "daily_trajectory": "day by day", "best_day": "best day", "worst_day": "worst day",
    "weekday_vs_weekend": "weekdays vs weekends", "aggregates": "weekly totals",
    # "whole record so far" would be a fine label, but it put the word "record" in the model's mouth
    # and the voice check then rejected the sentence. Labels must not contain system words.
    "cumulative": "whole history so far", "last_30_days": "last 30 days", "monthly_trajectory": "month by month",
    "lab_link": "lab comparison", "domain_trends": "long run trends",
    "has_diary_event": "has diary event", "data_quality_flags": "data quality flags",
    "material_changes": "things that deviated",
    # The model never sees the word "anchor": a crossing is "a large change found", and the artifact subset is named for what it is.
    "anchors_crossed": "large changes found", "anchors_questionable": "large changes that may be sensor artifacts", "questionable_readings": "questionable readings (mention only in data_quality_caveats)",
    "stream_movement": "movement vs previous window", "co_movement_required": "co_movement_required",
    "glucose_movement": "glucose movement vs previous window",
    "best_and_worst_day_note": "best and worst day note", "post_meal_peak_mean": "average peak glucose after meals mg/dL",
    "post_meal_peak_max": "highest peak glucose after meals mg/dL",
    "where": "where", "questionable_values": "questionable values", "values_if_included": "values if they were included",
    "kind": "type", "detail": "detail", "medicine": "medicine", "measures": "measures", "measure": "measure",
    "days": "number of days", "missed": "missed", "of": "out of", "count": "count", "flag": "flag",
    "status": "compared with the reference range", "direction": "moved", "change": "change", "unit": "unit",
    "amount": "amount", "relation": "relation", "lab_date": "lab date", "hba1c_pct": "HbA1c percent",
    "gap_hba1c_minus_gmi": "HbA1c minus GMI points",
    # glucose metrics
    "mean": "average glucose mg/dL", "gmi_pct": "GMI percent", "tir_pct": "time in range percent",
    "tar_pct": "time above range percent", "tar_severe_pct": "time above 250 percent",
    "tbr_pct": "time below range percent", "tbr_severe_pct": "time below 54 percent",
    "cv_pct": "variability percent", "min_value": "lowest glucose mg/dL", "max_value": "highest glucose mg/dL",
    "min_timestamp": "time of lowest glucose", "max_timestamp": "time of highest glucose",
    "max": "highest glucose mg/dL", "n_readings": "number of glucose readings",
    "completeness_pct": "glucose data completeness percent", "glucose_mean": "average glucose mg/dL",
    # sleep / activity / heart rate / lifestyle
    "duration_hours": "sleep hours", "quality": "sleep quality", "sleep_hours": "sleep hours",
    "total_steps": "steps", "steps": "steps", "peak_step_hour": "busiest step hour",
    "sedentary_minutes": "sedentary minutes", "continuous_mean": "average heart rate bpm",
    "continuous_min": "lowest heart rate bpm", "continuous_max": "highest heart rate bpm",
    "resting_period_mean": "average heart rate at rest bpm", "resting_hr": "average heart rate at rest bpm",
    "resting_heart_rate_daily": "daily resting heart rate bpm",
    "resting_heart_rate_status": "daily resting heart rate compared with the reference range",
    "hydration_ml": "hydration mL", "screen_time_hours": "screen time hours", "location": "location",
    "systolic": "systolic blood pressure", "diastolic": "diastolic blood pressure",
    "systolic_status": "systolic compared with the reference range", "diastolic_status": "diastolic compared with the reference range",
    # medication / mood / meals
    "per_medication": "each medicine", "overall_pct": "medication adherence percent",
    "adherence_pct": "medication adherence percent", "worst_mood_category": "worst mood",
    "meal_label": "meal", "meal_time": "meal time", "food_description": "food",
    "pre_meal_glucose": "glucose before the meal mg/dL", "peak_glucose": "peak glucose after the meal mg/dL",
    "rise": "rise in glucose mg/dL", "minutes_to_peak": "minutes to peak",
    "severity_note": "severity note", "of_days": "out of days",
}

# Subtree-specific labels: entering one of these keys switches the map for everything below it.
CONTEXT_MAPS: dict[str, dict[str, str]] = {
    "deltas": {
        "glucose_tir_pct": "change in time in range points", "glucose_cv_pct": "change in variability points",
        "glucose_gmi_pct": "change in GMI points", "glucose_mean": "change in average glucose mg/dL",
        "adherence_overall_pct": "change in medication adherence points",
        "glucose_severe_total_curr": "severe time this window percent",
        "glucose_severe_total_prior": "severe time previous window percent",
        "sleep_hours": "change in sleep hours", "resting_hr_mean": "change in average heart rate at rest bpm",
        "activity_steps": "change in steps", "activity_steps_mean": "change in average steps per day",
        "adherence_meds_changed_count": "number of medicines whose status changed",
        "cumulative_mean": "change in cumulative average glucose mg/dL",
    },
    "aggregates": {
        "mean": "average per day", "sum": "total", "mean_per_day": "average per day",
        "n_days": "number of days", "n_readings": "number of readings", "counts": "counts",
        "readings": "readings", "per_medication": "each medicine",
        "overall_pct": "medication adherence percent", "meals_by_label": "meals by type",
        "post_meal_peak_mean": "average peak glucose after meals mg/dL",
        "post_meal_peak_max": "highest peak glucose after meals mg/dL",
        "foods_best_day": "foods on the best day", "foods_worst_day": "foods on the worst day",
        "completeness_pct": "data completeness percent", "taken": "taken", "expected": "expected",
    },
    "monthly_trajectory": {
        "month": "month", "partial": "partial month", "mean_sleep_hours": "average sleep hours",
        "mean_steps": "average steps per day", "mean_adherence_pct": "medication adherence percent",
        "diary_event_counts_by_category": "diary events by category",
    },
    "domain_trends": {
        "first_month": "first month", "latest_month": "latest month",
        "delta_latest_minus_first": "change latest minus first", "direction": "moved",
        "resting_hr": "resting heart rate",
    },
    "lab_link": {
        "lab_date": "lab date", "hba1c_pct": "HbA1c percent", "hba1c_status": "HbA1c compared with the reference range",
        "cgm_gmi_pct_90d_prior": "GMI percent over the 90 days before the lab",
        "gap_hba1c_minus_gmi": "HbA1c minus GMI points",
    },
}

# `aggregates` is keyed by internal stream name; show the registry's plain label instead.
STREAM_LABELS: dict[str, str] = {s.name: s.label for s in REGISTRY if s.label}

# Keys left exactly as-is: the model needs them to reason about notability, and the voice scan
# is supposed to catch an echo of these (they are system words, not measurements).
KEEP = {"reliable", "confidence", "label",
        "category", "text", "time", "timestamp", "biomarker", "value", "pattern",
        "glucose", "sleep", "activity", "mood", "meals", "weekday", "weekend"}

# String VALUES (and category keys inside count dicts) shown in plain words. A category such as
# "calm_stable" or a status such as "borderline_low" is data, not wording — left as is, the model repeats it
# ("steps was low", "mood calm_stable"). Anything snake_case not listed gets its underscores turned into spaces.
VALUE_LABELS: dict[str, str] = {
    "calm_stable": "calm", "positive_uplifted": "uplifted", "mild_stress": "mild stress", "tired_low_energy": "tired",
    "anxious": "anxious", "overwhelmed_high_distress": "overwhelmed",
    "normal": "within the reference range", "high": "above the reference range", "low": "below the reference range",
    "borderline_high": "slightly above the reference range", "borderline_low": "slightly below the reference range",
    "insufficient_data": "not enough data",
    # directions as sentence fragments, so the model writes "steps went down", not "direction: down"
    "up": "went up", "down": "went down", "flat": "stayed about the same",
    "step_count": "steps", "sedentary_time": "sedentary time", "sleep_duration": "sleep",
    "continuous_heart_rate": "heart rate at rest", "resting_heart_rate": "daily resting heart rate",
    "screen_time": "screen time", "waist_hip_ratio": "waist-to-hip ratio", "bmi": "BMI", "ggt": "GGT", "hba1c": "HbA1c",
    "blood_pressure_systolic": "systolic blood pressure", "blood_pressure_diastolic": "diastolic blood pressure",
    "home_wfh": "home (working from home)", "airport_travel": "airport or travel", "other_city": "another city",
    "family_home": "family home", "wedding_venue": "wedding venue", "public_event": "public event",
    "light_dinner": "light dinner", "late_dinner": "late dinner", "light_breakfast": "light breakfast",
    "pre_dawn_meal": "pre-dawn meal", "moonrise_meal": "moonrise meal", "late_night_function_meal": "late-night function meal",
    "snack_lunch": "snack lunch", "festive_lunch": "festive lunch", "festive_dinner": "festive dinner",
    # what a material_changes item is
    "anchor_crossed": "large change", "missed_dose": "missed dose", "missed_doses": "missed doses",
    "outside_reference_range": "outside the reference range", "diary_events": "diary events", "data_quality": "data quality",
    "lab_result": "lab result",
    # the anchors, in plain words (a crossing is described by what changed, never by the anchor's name)
    "glucose_TIR_change_points": "time in range changed by more than the usual amount",
    "glucose_CV_change_points": "variability changed by more than the usual amount",
    "glucose_GMI_change": "GMI changed by more than the usual amount",
    "severe_range_appeared_or_cleared": "severe high or low glucose time appeared or cleared",
    "sleep_hours_change": "sleep changed by more than the usual amount",
    "resting_hr_change_bpm": "heart rate at rest changed by more than the usual amount",
    "steps_change_abs": "steps changed by more than the usual amount",
    "steps_mean_change_abs": "average steps changed by more than the usual amount",
    "adherence_meds_changed": "several medicines changed from taken to missed or back",
    "adherence_pct_change": "medication adherence changed by more than the usual amount",
    "lab_cgm_discordance": "lab HbA1c and the sensor-estimated GMI disagree",
}
_SNAKE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)+$")


_MED_ID = re.compile(r"^med_\d+_(.+)$")


def plain_value(v: str) -> str:
    if v in VALUE_LABELS:
        return VALUE_LABELS[v]
    if m := _MED_ID.match(v):  # "med_002_metformin" -> "metformin": the entry names medicines, never ids
        return m.group(1).replace("_", " ")
    return v.replace("_", " ") if _SNAKE.match(v) else v


def plain_key(key: str, ctx: dict[str, str]) -> str:
    if key.endswith("__note"):  # a note attached beside a metric by annotate()
        return plain_key(key[: -len("__note")], ctx) + " note"
    if _MED_ID.match(key):
        return plain_value(key)
    if key in KEEP:
        return key
    return ctx.get(key) or LABELS.get(key) or STREAM_LABELS.get(key) or VALUE_LABELS.get(key) or key


def to_plain(record: Any, ctx: dict[str, str] | None = None, path: str = "", plain_path: str = "",
             path_map: dict[str, str] | None = None, label_pairs: dict[str, str] | None = None) -> tuple[Any, dict[str, str], dict[str, str]]:
    """Returns (plain_record, {plain path: internal path}, {internal key: plain label}).

    The label pairs feed the sanitizer: if an internal key still leaks into the model's prose,
    it is swapped for the plain label rather than rejected."""
    path_map = {} if path_map is None else path_map
    label_pairs = {} if label_pairs is None else label_pairs
    ctx = LABELS if ctx is None else ctx

    if isinstance(record, dict):
        out = {}
        for k, v in record.items():
            pk = plain_key(k, ctx)
            if pk != k:
                label_pairs.setdefault(k, pk)
            sub_ctx = {**LABELS, **CONTEXT_MAPS[k]} if k in CONTEXT_MAPS else ctx
            p, pp = f"{path}.{k}".lstrip("."), f"{plain_path}.{pk}".lstrip(".")
            path_map[pp] = p
            out[pk], _, _ = to_plain(v, sub_ctx, p, pp, path_map, label_pairs)
        return out, path_map, label_pairs
    if isinstance(record, list):
        out_l = []
        for i, v in enumerate(record):
            p, pp = f"{path}[{i}]", f"{plain_path}[{i}]"
            path_map[pp] = p
            sub, _, _ = to_plain(v, ctx, p, pp, path_map, label_pairs)
            out_l.append(sub)
        return out_l, path_map, label_pairs
    if isinstance(record, str) and path.split(".")[-1].split("[")[0] not in ("text", "quoted_text", "food_description", "food", "window_id"):
        return plain_value(record), path_map, label_pairs
    return record, path_map, label_pairs


# ---- annotate: what the model sees and what the validator checks against -----------------------------------

DROP_FROM_MODEL = {"quiet", "data_quality_details", "stream_direction_table", "stream_change_table", "co_movement_candidates"}
_ARTIFACT_PREFIXES = ("known_clip_artifact_reading", "max_reading_above_400", "implausible_rate_of_change")
_QUESTIONABLE_NOTE = "may reflect a questionable reading"
_REASON_BY_FLAG = {"gap_hours": "there was a gap in the readings", "low_completeness": "data was incomplete"}


def _where(path: str) -> str:
    parts = [p for p in re.findall(r"[^.\[\]]+", path)] or ["whole window"]
    return " > ".join(LABELS.get(p) or STREAM_LABELS.get(p) or p for p in parts)


def annotate(record: dict | None, k_co_movement: int = 4) -> dict | None:
    """Internal-key copy of a record, prepared for the model and the validator.

    1. Questionable readings. Where a metrics dict carries `questionable_excluded`, the cleaned value takes the
       metric's place (so key observations rest on cleaned values) and a `<metric>__note` says so. The raw
       numbers survive only in the top-level `questionable_readings` section, which is for data_quality_caveats.
    2. Per-metric caveats. A flag's `affects` list decides which metrics get a note — changes (`deltas`) that
       cannot be cleaned, and gap / low-completeness metrics. No other metric is annotated.
    3. Movement. The code-side direction / change tables and co-movement candidates are replaced by
       `stream_movement` (direction, signed change, unit per measure) and `co_movement_required`: the top K
       same/opposite co-movers, each with direction and the unsigned amount to state.
    """
    if record is None:
        return None
    details = record.get("data_quality_details") or []
    this_reason: dict[str, str] = {}   # affected key -> why (this window)
    prev_keys: set[str] = set()        # affected keys of the previous window (only matter for changes)
    for d in details:
        kind = d["flag"].split(":")[0]
        reason = _QUESTIONABLE_NOTE if kind in _ARTIFACT_PREFIXES else _REASON_BY_FLAG.get(kind, "data was incomplete")
        for key in d["affects"]:
            if d["window"] == "this window":
                this_reason.setdefault(key, reason)
            else:
                prev_keys.add(key)
    raw_section: list[dict] = []
    # Only the metrics a flag affects are cleaned and annotated. A clipped 65.0 reading moves time below range
    # (and the lowest value); it must not put a "questionable" note on time in range or variability, even though
    # recomputing without it nudges those numbers too.
    affected = {key for f in record.get("data_quality_flags", []) if f.split(":")[0] in _ARTIFACT_PREFIXES for key in flag_affects(f)}
    # A change is also distorted when the PREVIOUS window held the artifact (it "leaving" looks like a change).
    affected_for_changes = affected | {k for d in details if d["window"] == "previous window" and d["flag"].split(":")[0] in _ARTIFACT_PREFIXES for k in d["affects"]}

    def walk(node: Any, path: str) -> Any:
        if isinstance(node, dict):
            q = node.get("questionable_excluded")
            aff = affected_for_changes if path == "deltas" else affected
            clean = {k: v for k, v in q["metrics_without_them"].items() if k in aff} if q else {}
            out: dict[str, Any] = {}
            for key, v in node.items():
                if key == "questionable_excluded":
                    continue
                if key in clean:
                    out[key] = clean[key]
                    out[f"{key}__note"] = f"excludes {q['n_excluded']} questionable reading(s)"
                else:
                    out[key] = walk(v, f"{path}.{key}" if path else key)
            if clean:
                raw_section.append({"where": _where(path), "questionable_values": q["excluded_values"],
                                    "values_if_included": {k: q["metrics_with_them"][k] for k in clean}})
            return out
        if isinstance(node, list):
            return [walk(x, f"{path}[{i}]") for i, x in enumerate(node)]
        return node

    ann = {k: walk(v, k) for k, v in record.items() if k not in DROP_FROM_MODEL}

    deltas = ann.get("deltas")
    if isinstance(deltas, dict):
        for key in list(deltas):
            if key.endswith("__note") or f"{key}__note" in deltas:
                continue  # already cleaned and noted
            if key in this_reason:
                deltas[f"{key}__note"] = this_reason[key]
            elif key in prev_keys:
                deltas[f"{key}__note"] = "the previous window had questionable data, so this change " + _QUESTIONABLE_NOTE.removeprefix("may ")
    for section in ("glucose", "activity", "sleep", "heart_rate"):  # gap / low-completeness notes sit beside the metric itself
        sec = ann.get(section)
        if isinstance(sec, dict):
            for key in list(sec):
                if key in this_reason and this_reason[key] != _QUESTIONABLE_NOTE and f"{key}__note" not in sec:
                    sec[f"{key}__note"] = this_reason[key]

    sd, ch = record.get("stream_direction_table"), record.get("stream_change_table")
    if sd is not None and ch is not None:
        from v0_code.logic.stream_tables import UNIT_BY_LABEL  # local: stream_tables imports registry only, but keep this module import-light
        ann["stream_movement"] = {lab: {"direction": sd[lab], "change": ch.get(lab), "unit": UNIT_BY_LABEL.get(lab, "")} for lab in sd}
    cand = record.get("co_movement_candidates")
    if cand is not None:
        ann["co_movement_required"] = [
            {"name": r["name"], "direction": r["direction"], "amount": r["amount"], "unit": r["unit"],
             "relation": "moved the same way as glucose" if r["relation"] == "same" else "moved the opposite way to glucose"}
            for r in cand["ranked"][:k_co_movement]
        ]
        ann["glucose_movement"] = {"direction": cand["glucose_direction"], "change": cand["glucose_change"], "unit": "mg/dL"}
    if raw_section:
        ann["questionable_readings"] = raw_section
    return ann
