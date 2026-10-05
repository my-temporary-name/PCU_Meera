"""Baseline Engine v2: config, trust layer, profile, tags, co-movement, anchors, material changes (pure functions, synthetic inputs)."""

from datetime import datetime, timedelta, timezone

import pytest

from v0_code.baseline_v2 import anchors as A
from v0_code.baseline_v2.config import Config, resolve_threshold
from v0_code.baseline_v2.data import Reading
from v0_code.baseline_v2.material import MATERIAL_KINDS, build_material
from v0_code.baseline_v2.profile import build_profile, day_status
from v0_code.baseline_v2.tags import co_movement, make_tag
from v0_code.baseline_v2.trust import clean_series, confidence, is_reliable, with_questionable


# ---- config ----------------------------------------------------------------------------------------------------------------------

def test_config_loads_every_section_and_versions_itself(v2_cfg):
    assert v2_cfg.timezone == "Asia/Kolkata" and v2_cfg.pronoun == "she" and v2_cfg.min_days_for_compare == 14
    assert v2_cfg.device_range == (40.0, 400.0) and v2_cfg.max_step_change_per_15min == 75
    assert v2_cfg.sd_multiplier == 0.5 and (v2_cfg.small_below, v2_cfg.moderate_below) == (2, 4)
    assert v2_cfg.stream("mood_state").count_like and v2_cfg.stream("mood_state").label == "strained periods of the day"
    assert v2_cfg.version.startswith("meera_iyer_v1-") and len(v2_cfg.version.split("-")[1]) == 12
    assert v2_cfg.medicine_name("med_002_metformin") == "metformin" and v2_cfg.possessive == "her"


def test_threshold_expression_resolves_for_the_medication_count():
    assert resolve_threshold("min(2, n_meds)", 3) == 2 and resolve_threshold("min(2, n_meds)", 1) == 1 and resolve_threshold(1500, 3) == 1500
    with pytest.raises(ValueError):
        resolve_threshold("max(2, n_meds)", 3)


# ---- trust layer -----------------------------------------------------------------------------------------------------------------

def _series(values, start="2026-01-01T00:00:00+00:00", step_min=15):
    t0 = datetime.fromisoformat(start)
    return [Reading((t0 + timedelta(minutes=step_min * i)).isoformat(), t0 + timedelta(minutes=step_min * i), v) for i, v in enumerate(values)]


def test_readings_outside_the_device_range_are_removed(v2_cfg):
    kept, removed = clean_series(_series([120, 125, 450, 130, 20, 128]), v2_cfg)
    assert [r.value for r in kept] == [120, 125, 130, 128] and [x.value for x in removed] == [450, 20]


def test_a_jump_bigger_than_the_limit_is_removed_and_the_next_reading_is_judged_against_the_last_kept_one(v2_cfg):
    kept, removed = clean_series(_series([120, 124, 230, 126, 128]), v2_cfg)        # +106 in 15 minutes
    assert [x.value for x in removed] == [230] and [r.value for r in kept] == [120, 124, 126, 128]


def test_the_jump_limit_is_scaled_by_the_gap_so_a_legitimate_change_after_a_gap_is_kept(v2_cfg):
    s = _series([120, 124], step_min=15) + _series([210], start="2026-01-01T04:00:00+00:00")   # +86 after a 3.75 h gap
    kept, removed = clean_series(s, v2_cfg)
    assert not removed and len(kept) == 3


def test_a_spike_at_midnight_is_judged_against_the_previous_days_last_reading(v2_cfg):
    s = _series([120], start="2026-01-01T23:45:00+00:00") + _series([300], start="2026-01-02T00:00:00+00:00")
    kept, removed = clean_series(s, v2_cfg)
    assert [x.value for x in removed] == [300] and removed[0].date == "2026-01-02"


def test_an_isolated_65_between_close_neighbours_is_not_removed_a_known_upstream_limit(v2_cfg):
    kept, removed = clean_series(_series([100, 98, 65.0, 102, 104]), v2_cfg)         # -33: under the 75 limit, inside the device range
    assert not removed and 65.0 in [r.value for r in kept]


def test_the_with_them_twin_lists_only_the_metrics_that_differ():
    twin = with_questionable([120.0] * 95, [599.0], 96)
    assert twin["max_value"] == 599.0 and twin["cv_pct"] > 0 and "tbr_pct" not in twin and "tir_pct" in twin
    assert with_questionable([120.0] * 95, [], 96) == {}


def test_reliability_needs_completeness_and_enough_days(v2_cfg):
    assert is_reliable(70.0, 14, v2_cfg) and not is_reliable(69.9, 14, v2_cfg) and not is_reliable(100.0, 13, v2_cfg)
    assert confidence(True, 100.0) == "high" and confidence(True, 80.0) == "moderate" and confidence(False, 100.0) == "low"


# ---- profile ---------------------------------------------------------------------------------------------------------------------

def test_profile_has_no_flat_band_or_usual_status_before_the_minimum_history(v2_cfg):
    p = build_profile([100.0 + i for i in range(13)], ["normal"] * 13, v2_cfg)
    assert p["flat_band"] is None and p["usual_status"] is None and p["n_days"] == 13
    q = build_profile([100.0 + (i % 2) * 10 for i in range(14)], ["low"] * 10 + ["normal"] * 4, v2_cfg)
    assert q["flat_band"] == pytest.approx(0.5 * 5.0, abs=1e-3) and q["usual_status"] == "low" and q["share_non_normal"] == pytest.approx(10 / 14, abs=1e-3)


def test_day_status_is_the_most_common_reading_status_with_a_deterministic_tie_break():
    assert day_status(["normal", "low", "low", None]) == "low" and day_status([None, None]) is None and day_status(["high", "low"]) == "low"


# ---- tags ------------------------------------------------------------------------------------------------------------------------

def _tag(delta, band, cfg, count_like=False):
    sc = type("S", (), {"name": "x", "domain": "d", "display": "x", "unit": "u", "count_like": count_like})()
    return make_tag(sc, 100.0 + delta, 100.0, {"flat_band": band}, cfg)


@pytest.mark.parametrize("delta,direction,size", [(0.9, "flat", "none"), (-0.9, "flat", "none"), (1.0, "up", "small"), (1.99, "up", "small"), (2.0, "up", "moderate"),
                                                  (3.99, "up", "moderate"), (4.0, "up", "large"), (-8.0, "down", "large"), (-1.5, "down", "small")])
def test_direction_and_size_label_boundaries(v2_cfg, delta, direction, size):
    t = _tag(delta, 1.0, v2_cfg)
    assert (t["direction"], t["size"]) == (direction, size)


def test_no_band_or_no_previous_value_is_not_enough_data_but_the_delta_is_kept_when_it_exists(v2_cfg):
    t = _tag(5.0, None, v2_cfg)
    assert t["direction"] == "not_enough_data" and t["size"] == "none" and t["delta"] == 5.0
    sc = type("S", (), {"name": "x", "domain": "d", "display": "x", "unit": "u", "count_like": False})()
    assert make_tag(sc, None, 1.0, {"flat_band": 1.0}, v2_cfg)["direction"] == "not_enough_data"


def test_a_zero_spread_stream_calls_any_change_large_and_no_change_flat(v2_cfg):
    t = _tag(0.1, 0.0, v2_cfg)
    assert (t["direction"], t["size"]) == ("up", "large")
    z = _tag(0.0, 0.0, v2_cfg)
    assert (z["direction"], z["size"]) == ("flat", "none")        # a zero change is never "down"


def _t(measure, domain, direction, size="moderate", ratio=3.0):
    return {"measure": measure, "label": measure, "domain": domain, "direction": direction, "direction_word": direction, "size": size, "ratio": ratio}


def test_co_movement_is_only_reported_when_glucose_itself_moved():
    tags = [_t("glucose", "glucose", "flat", "none"), _t("sleep", "sleep", "down"), _t("steps", "activity", "up")]
    cm = co_movement(tags, "glucose")
    assert cm["same_direction"] == [] and cm["opposite_direction"] == [] and cm["glucose_direction"] == "flat"


def test_co_movement_splits_same_and_opposite_and_never_reports_flat_flat():
    tags = [_t("glucose", "glucose", "up", "large"), _t("sleep", "sleep", "down"), _t("steps", "activity", "up"), _t("hydration", "lifestyle", "flat", "none"), _t("mood", "mood", "not_enough_data", "none")]
    cm = co_movement(tags, "glucose")
    assert [e["measure"] for e in cm["same_direction"]] == ["steps"] and [e["measure"] for e in cm["opposite_direction"]] == ["sleep"]
    assert cm["flat"] == ["hydration"] and cm["not_enough_data"] == ["mood"]


def test_co_movement_gives_one_entry_per_domain_the_strongest(  ):
    tags = [_t("glucose", "glucose", "up"), _t("heart rate", "heart_rate", "up", ratio=2.5), _t("resting heart rate", "heart_rate", "up", ratio=6.0), _t("daily", "heart_rate", "down", ratio=3.0)]
    cm = co_movement(tags, "glucose")
    assert len(cm["same_direction"]) + len(cm["opposite_direction"]) == 1 and cm["same_direction"][0]["measure"] == "resting heart rate"


def test_the_glucose_domain_is_the_reference_not_a_co_mover():
    tags = [_t("glucose", "glucose", "up"), _t("time in range", "glucose", "down"), _t("variability", "glucose", "up")]
    cm = co_movement(tags, "glucose")
    assert cm["same_direction"] == [] and cm["opposite_direction"] == []


# ---- anchors: one test per configured anchor (fires on a trigger, silent on a quiet window) ----------------------------------------

QUIET = {"tir": 0.0, "cv": 0.0, "gmi": 0.0, "sleep": 0.0, "resting_hr": 0.0, "steps": 0.0, "adherence_pct": 0.0, "meds_changed": 0, "severe_curr": 0.0, "severe_prior": 0.0, "lab_gap": 0.0}
TRIGGERS = {
    "glucose_TIR_change_points": ("day", {"tir": -10.01}), "glucose_CV_change_points": ("day", {"cv": 8.01}), "glucose_GMI_change": ("week", {"gmi": 0.31}),
    "severe_range_appeared_or_cleared": ("day", {"severe_curr": 1.04, "severe_prior": 0.0}), "sleep_hours_change": ("day", {"sleep": -1.51}),
    "resting_hr_change_bpm": ("day", {"resting_hr": 8.01}), "adherence_meds_changed": ("day", {"meds_changed": 2}), "adherence_pct_change": ("week", {"adherence_pct": -15.01}),
    "steps_abs_change": ("day", {"steps": 3000.5}), "lab_cgm_discordance": ("month", {"lab_gap": 0.5}),
}


def test_every_configured_anchor_has_a_trigger_test(v2_cfg):
    assert set(TRIGGERS) == set(A.ANCHOR_ORDER) == set(v2_cfg.anchors)


@pytest.mark.parametrize("name", sorted(TRIGGERS))
def test_each_anchor_fires_alone_on_its_trigger_and_is_silent_on_a_quiet_window(v2_cfg, name):
    tier, delta = TRIGGERS[name]
    assert A.evaluate(v2_cfg, tier, {**QUIET, **delta}, n_meds=3) == [name]
    assert A.evaluate(v2_cfg, tier, QUIET, n_meds=3) == []


def test_equal_to_the_threshold_is_not_a_crossing_except_the_two_inclusive_anchors(v2_cfg):
    assert A.evaluate(v2_cfg, "day", {**QUIET, "tir": 10.0, "cv": 8.0, "sleep": 1.5, "resting_hr": 8.0, "steps": 3000.0}, 3) == []
    assert A.evaluate(v2_cfg, "month", {**QUIET, "lab_gap": -0.5}, 3) == ["lab_cgm_discordance"]         # inclusive, either direction
    assert A.evaluate(v2_cfg, "day", {**QUIET, "meds_changed": 2}, 3) == ["adherence_meds_changed"]       # >= the resolved count


def test_the_medication_threshold_is_min_of_two_and_the_number_of_medicines(v2_cfg):
    assert A.evaluate(v2_cfg, "day", {**QUIET, "meds_changed": 1}, 3) == [] and A.evaluate(v2_cfg, "day", {**QUIET, "meds_changed": 1}, 1) == ["adherence_meds_changed"]


def test_unknown_values_never_fire(v2_cfg):
    assert A.evaluate(v2_cfg, "day", {k: None for k in QUIET}, 3) == []


def test_week_tier_uses_the_week_mean_step_threshold(v2_cfg):
    assert A.evaluate(v2_cfg, "week", {**QUIET, "steps": 1500.5}, 3) == ["steps_abs_change"] and A.evaluate(v2_cfg, "week", {**QUIET, "steps": 1499.0}, 3) == []


def test_a_crossing_that_exists_only_on_the_raw_values_is_questionable_not_counted(v2_cfg):
    clean = {**QUIET}
    raw = {**QUIET, "cv": 32.0, "severe_curr": 1.04}
    crossed, questionable = A.split_questionable(v2_cfg, "day", clean, raw, 3)
    assert crossed == [] and set(questionable) == {"glucose_CV_change_points", "severe_range_appeared_or_cleared"}


# ---- material changes -------------------------------------------------------------------------------------------------------------

def _mat(**over):
    kw = dict(anchors_crossed=[], per_medication={"med_1": "taken"}, diary_events=[], statuses={}, usual={}, tags=[], gap_hours=None, low_completeness=[], removed=[], date="2026-01-05")
    kw.update(over)
    return build_material(**kw)


def test_a_day_with_nothing_deviating_has_no_material_changes():
    assert _mat() == []


def test_every_kind_is_built_in_the_specified_order():
    items = _mat(anchors_crossed=["sleep_hours_change"], per_medication={"m": "missed"}, diary_events=[{"category": "c", "text": "t", "severity_note": None}],
                 statuses={"sleep": "low"}, usual={"sleep": "normal"}, tags=[{"measure": "x", "label": "x", "domain": "d", "direction": "up", "direction_word": "up", "size": "large"}],
                 gap_hours=2.2, low_completeness=[{"stream": "s", "label": "s", "pct": 0.0}], removed=[{"time": "t", "value": 599.0, "reason": "r"}])
    assert [i["kind"] for i in items] == ["anchor_crossed", "missed_dose", "diary_event", "status_worse_than_usual", "large_change", "data_gap", "low_completeness", "questionable_reading_removed"]
    assert set(i["kind"] for i in items) | {"diary_summary"} == set(MATERIAL_KINDS)          # diary_summary: the month tier only (tests/test_v2_review2.py)


def test_a_status_is_material_only_when_worse_than_the_streams_usual():
    assert _mat(statuses={"steps": "low"}, usual={"steps": "low"}) == []                              # chronic: her usual
    assert _mat(statuses={"steps": "normal"}, usual={"steps": "low"}) == []                           # better than usual
    assert _mat(statuses={"sleep": "borderline_low"}, usual={"sleep": "normal"}, min_status_rank=1)[0]["kind"] == "status_worse_than_usual"
    assert _mat(statuses={"sleep": "low"}, usual={"sleep": None}) == []                                # no usual yet -> nothing to compare against


def test_missed_doses_and_diary_events_are_always_material():
    assert _mat(per_medication={"m": "missed"})[0] == {"kind": "missed_dose", "medicine": "m", "days": 1}
    assert _mat(diary_events=[{"category": "c", "text": "x", "severity_note": "mild"}])[0]["kind"] == "diary_event"


def test_only_large_tags_are_large_changes():
    tags = [{"measure": "a", "label": "a", "domain": "d", "direction": "up", "direction_word": "up", "size": "moderate"}, {"measure": "b", "label": "b", "domain": "d", "direction": "down", "direction_word": "down", "size": "large"}]
    assert [i["measure"] for i in _mat(tags=tags) if i["kind"] == "large_change"] == ["b"]
