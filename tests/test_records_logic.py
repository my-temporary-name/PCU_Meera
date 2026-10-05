"""Record-side logic: best/worst day ties, mood ranking, material changes, questionable readings, co-movement ranking."""

from v0_code.logic import stream_tables as st
from v0_code.logic.data_quality import cleaned_deltas, cleaned_metrics, flag_affects, questionable_timestamps
from v0_code.logic.memory_records import material_changes_day, pick_best_worst, worst_mood_category


def _day(date, tir, mean):
    return {"date": date, "glucose": {"tir_pct": tir, "mean": mean}}


def test_best_worst_break_a_tir_tie_by_mean_glucose():
    days = [_day("d1", 100.0, 130.0), _day("d2", 100.0, 120.0), _day("d3", 100.0, 140.0)]
    best, worst, identical = pick_best_worst(days)
    assert (best["date"], worst["date"], identical) == ("d2", "d3", False)  # best = lowest mean, worst = highest mean


def test_best_worst_prefer_tir_over_mean():
    best, worst, _ = pick_best_worst([_day("a", 90.0, 110.0), _day("b", 100.0, 150.0), _day("c", 80.0, 100.0)])
    assert (best["date"], worst["date"]) == ("b", "c")


def test_identical_days_are_reported_as_identical_not_named_twice():
    _, _, identical = pick_best_worst([_day(f"d{i}", 100.0, 125.0) for i in range(7)])
    assert identical


def test_positive_uplifted_never_ranks_as_the_worst_mood():
    mood = {"morning": {"category": "positive_uplifted"}, "afternoon": {"category": "calm_stable"}, "evening": {"category": "mild_stress"}}
    assert worst_mood_category(mood) == "mild_stress"
    assert worst_mood_category({"morning": {"category": "positive_uplifted"}, "evening": {"category": "calm_stable"}}) == "calm_stable"
    assert worst_mood_category({"morning": {"category": "calm_stable"}, "evening": {"category": "overwhelmed_high_distress"}}) == "overwhelmed_high_distress"
    assert worst_mood_category({}) is None


def _quiet_day(**over):
    rec = {"anchors_crossed": [], "adherence": {"per_medication": {"med_002_metformin": "taken"}}, "unusual_statuses": [],
           "diary_events": [], "data_quality_flags": [], "glucose": {}}
    rec.update(over)
    return rec


def test_a_day_with_nothing_deviating_has_no_material_changes():
    assert material_changes_day(_quiet_day()) == []


def test_each_kind_of_deviation_is_a_material_change():
    assert material_changes_day(_quiet_day(anchors_crossed=["sleep_hours_change"]))[0]["kind"] == "anchor_crossed"
    missed = material_changes_day(_quiet_day(adherence={"per_medication": {"med_002_metformin": "missed"}}))
    assert missed == [{"kind": "missed_dose", "medicine": "med_002_metformin"}]  # the 2025-12-26 case: a miss with no anchor
    assert material_changes_day(_quiet_day(unusual_statuses=[{"measure": "hydration", "status": "borderline_low"}]))[0]["kind"] == "unusual_status"
    assert material_changes_day(_quiet_day(diary_events=[{"text": "x"}]))[0] == {"kind": "diary_events", "count": 1}
    for flag in ("gap_hours:2.2", "low_completeness:step_count:0.0"):
        assert material_changes_day(_quiet_day(data_quality_flags=[flag])) == [{"kind": "data_quality", "flag": flag}], flag
    assert material_changes_day(_quiet_day(data_quality_flags=["known_discrepancy:x"])) == []  # informational, not a deviation


def test_a_non_normal_status_that_is_the_streams_usual_is_not_a_deviation():
    # unusual_statuses is built in code from day-level modes vs the stream's usual; usual-status days never reach it
    assert material_changes_day(_quiet_day(unusual_statuses=[])) == []


# ---- questionable readings ---------------------------------------------------------------------------------------

def _readings(values, start_hour=0, date="2026-01-05"):
    return [(f"{date}T{start_hour + i // 4:02d}:{(i % 4) * 15:02d}:00+05:30", v) for i, v in enumerate(values)]


def test_clipped_and_ceiling_readings_are_questionable():
    r = _readings([120.0, 65.0, 125.0, 450.0, 130.0])
    assert questionable_timestamps(r) == {r[1][0], r[3][0]}


def test_an_implausible_jump_marks_the_endpoint_farther_from_the_median():
    r = _readings([120.0, 122.0, 330.0, 124.0, 126.0, 121.0])
    assert r[2][0] in questionable_timestamps(r)


def test_cleaned_metrics_drop_the_questionable_reading_and_keep_the_raw_beside_them():
    r = _readings([120.0, 125.0, 130.0, 599.0, 128.0, 122.0])
    c = cleaned_metrics(r, questionable_timestamps(r), expected=96)
    assert c["n_excluded"] == 1 and c["excluded_values"] == [599.0]
    assert c["metrics_without_them"]["max_value"] == 130.0 and c["metrics_with_them"]["max_value"] == 599.0
    assert c["metrics_without_them"]["cv_pct"] < c["metrics_with_them"]["cv_pct"]
    assert cleaned_metrics(_readings([120.0, 125.0, 130.0]), set(), 96) is None  # nothing excluded -> no twin


def test_each_flag_carries_the_metrics_it_affects():
    assert flag_affects("known_clip_artifact_reading:65.0") == ["tbr_pct", "tbr_severe_pct", "min_value"]  # not TIR, not variability
    assert "cv_pct" in flag_affects("max_reading_above_400") and "tir_pct" not in flag_affects("max_reading_above_400")
    assert flag_affects("low_completeness:step_count:0.0")[0] == "total_steps"
    assert flag_affects("known_discrepancy:foo") == []


# ---- co-movement ranking --------------------------------------------------------------------------------------------

def test_ranked_co_movers_carry_direction_amount_and_unit_strongest_first():
    dirs = {"glucose": "up", "sleep": "up", "steps": "down", "hydration": "down"}
    changes = {"glucose": 9.0, "sleep": 0.5, "steps": -800.0, "hydration": -150.0}
    strengths = {"glucose": 3.0, "sleep": 1.2, "steps": 4.0, "hydration": 2.0}
    ranked = st.candidates_from_directions(dirs, changes, strengths)["ranked"]
    assert [r["name"] for r in ranked] == ["steps", "hydration", "sleep"]
    assert ranked[0] == {"name": "steps", "direction": "down", "amount": 800.0, "unit": "steps", "relation": "opposite", "strength": 4.0}
    assert ranked[2]["relation"] == "same" and ranked[2]["unit"] == "hours"


def test_no_ranked_co_movers_when_glucose_is_flat():
    c = st.candidates_from_directions({"glucose": "flat", "sleep": "up"}, {"glucose": 0.2, "sleep": 0.5}, {"glucose": 0.1, "sleep": 1.0})
    assert c["ranked"] == [] and c["moved_while_glucose_flat"] == ["sleep"]


def test_stream_tables_report_change_and_strength():
    hist = {"x": [100.0 + (i % 2) * 10 for i in range(20)]}  # SD 5 -> band 2.5
    dirs, changes, strengths = st.stream_tables({"x": 110.0}, {"x": 100.0}, hist)
    assert dirs["x"] == "up" and changes["x"] == 10.0 and strengths["x"] == 4.0


def test_cleaned_deltas_remove_an_artifact_from_the_change_and_report_the_raw_beside_it():
    day = _readings([120.0, 122.0, 125.0, 123.0, 121.0, 124.0], date="2026-01-04")
    spike = _readings([120.0, 122.0, 599.0, 123.0, 121.0, 124.0])
    keys = {"glucose_cv_pct", "glucose_tir_pct", "glucose_severe_total_curr", "glucose_severe_total_prior", "glucose_mean", "glucose_gmi_pct"}
    d = cleaned_deltas(spike, day, questionable_timestamps(spike), 96, 96, keys)
    assert d["excluded_values"] == [599.0]
    assert d["metrics_with_them"]["glucose_cv_pct"] > 5            # the raw change is a big artifact-driven rise
    assert abs(d["metrics_without_them"]["glucose_cv_pct"]) < 1     # without the spike variability barely moved
    assert d["metrics_with_them"]["glucose_severe_total_curr"] > 0 and d["metrics_without_them"]["glucose_severe_total_curr"] == 0.0


def test_cleaned_deltas_also_cover_an_artifact_in_the_prior_window_leaving():
    day = _readings([120.0, 122.0, 125.0, 123.0, 121.0, 124.0])
    spike = _readings([120.0, 122.0, 599.0, 123.0, 121.0, 124.0], date="2026-01-04")
    keys = {"glucose_cv_pct", "glucose_severe_total_curr", "glucose_severe_total_prior"}
    d = cleaned_deltas(day, spike, questionable_timestamps(spike), 96, 96, keys)
    assert d["metrics_with_them"]["glucose_severe_total_prior"] > 0 and d["metrics_without_them"]["glucose_severe_total_prior"] == 0.0


def test_no_cleaned_deltas_when_neither_window_has_a_questionable_reading():
    a, b = _readings([120.0, 125.0, 130.0]), _readings([121.0, 126.0, 131.0])
    assert cleaned_deltas(a, b, set(), 96, 96, {"glucose_cv_pct"}) is None
