"""One test per configured anchor: fires on a synthetic trigger window, silent on a quiet one."""

import pytest

from v0_code.logic.anchors import ANCHOR_NAMES, ANCHORS, anchor_fire_report, evaluate_anchors, questionable_anchors

QUIET = {"glucose_tir_pct": 0.0, "glucose_cv_pct": 0.0, "glucose_gmi_pct": 0.0, "glucose_severe_total_curr": 0.0,
         "glucose_severe_total_prior": 0.0, "sleep_hours": 0.0, "resting_hr_mean": 0.0, "activity_steps": 0.0,
         "activity_steps_mean": 0.0, "adherence_meds_changed_count": 0, "adherence_overall_pct": 0.0, "lab_cgm_gap": 0.0}


def _over(x: float) -> float:
    return x + 0.01


def triggers(tier: str) -> dict[str, dict]:
    a = ANCHORS[tier]
    t = {
        "glucose_TIR_change_points": {"glucose_tir_pct": -_over(a["glucose_TIR_change_points"])},
        "glucose_CV_change_points": {"glucose_cv_pct": _over(a["glucose_CV_change_points"])},
        "severe_range_appeared_or_cleared": {"glucose_severe_total_curr": 1.04, "glucose_severe_total_prior": 0.0},
        "sleep_hours_change": {"sleep_hours": -_over(a["sleep_hours_change"])},
        "resting_hr_change_bpm": {"resting_hr_mean": _over(a["resting_hr_change_bpm"])},
    }
    if "glucose_GMI_change" in a:
        t["glucose_GMI_change"] = {"glucose_gmi_pct": _over(a["glucose_GMI_change"])}
    if tier == "day":
        t["steps_change_abs"] = {"activity_steps": -_over(a["steps_change_abs"])}
        t["adherence_meds_changed"] = {"adherence_meds_changed_count": a["adherence_meds_changed_base"]}
    else:
        t["adherence_pct_change"] = {"adherence_overall_pct": -_over(a["adherence_pct_change"])}
        if tier == "week":
            t["steps_mean_change_abs"] = {"activity_steps_mean": _over(a["steps_mean_change_abs"])}
    if "lab_cgm_discordance" in a:
        t["lab_cgm_discordance"] = {"lab_cgm_gap": a["lab_cgm_discordance"]}  # inclusive: exactly the threshold fires
    return t


@pytest.mark.parametrize("tier", ["day", "week", "month"])
def test_quiet_window_fires_nothing(tier):
    assert evaluate_anchors(tier, QUIET, n_meds=3) == []


@pytest.mark.parametrize("tier", ["day", "week", "month"])
def test_every_configured_anchor_fires_alone_on_its_trigger(tier):
    t = triggers(tier)
    assert set(t) == set(ANCHOR_NAMES[tier]), "ANCHOR_NAMES and the test triggers must list the same anchors"
    for name, delta in t.items():
        assert evaluate_anchors(tier, {**QUIET, **delta}, n_meds=3) == [name], name


@pytest.mark.parametrize("tier", ["day", "week", "month"])
def test_just_below_threshold_stays_silent(tier):
    a = ANCHORS[tier]
    below = {"glucose_tir_pct": a["glucose_TIR_change_points"], "glucose_cv_pct": a["glucose_CV_change_points"],
             "sleep_hours": a["sleep_hours_change"], "resting_hr_mean": a["resting_hr_change_bpm"]}
    if "glucose_GMI_change" in a:
        below["glucose_gmi_pct"] = a["glucose_GMI_change"]
    assert evaluate_anchors(tier, {**QUIET, **below}, n_meds=3) == []  # equal to the threshold is not "more than"


def test_severe_range_fires_when_it_clears_too():
    d = {**QUIET, "glucose_severe_total_curr": 0.0, "glucose_severe_total_prior": 1.04}
    assert evaluate_anchors("day", d, n_meds=3) == ["severe_range_appeared_or_cleared"]


def test_severe_range_silent_with_no_prior_window():
    assert evaluate_anchors("day", {**QUIET, "glucose_severe_total_curr": 1.04, "glucose_severe_total_prior": None}, 3) == []


def test_day_adherence_threshold_is_min_of_two_and_medication_count():
    one = {**QUIET, "adherence_meds_changed_count": 1}
    assert evaluate_anchors("day", one, n_meds=3) == []  # 3 medicines: needs 2 changes
    assert evaluate_anchors("day", one, n_meds=1) == ["adherence_meds_changed"]  # 1 medicine: min(2,1)=1


def test_null_deltas_never_fire():
    assert evaluate_anchors("week", {k: None for k in QUIET}, n_meds=3) == []


def test_questionable_only_for_severe_range_and_only_with_an_artifact_flag():
    assert questionable_anchors(["severe_range_appeared_or_cleared", "glucose_CV_change_points"], ["max_reading_above_400"]) == ["severe_range_appeared_or_cleared"]
    assert questionable_anchors(["severe_range_appeared_or_cleared"], ["low_completeness:step_count:0.0"]) == []
    assert questionable_anchors(["severe_range_appeared_or_cleared"], ["implausible_rate_of_change:485.2"]) == ["severe_range_appeared_or_cleared"]


def test_dead_anchor_report_lists_never_fired_anchors():
    rep = anchor_fire_report({"day": [["sleep_hours_change"], [], ["sleep_hours_change", "steps_change_abs"]], "week": [[]], "month": [[]]})
    assert rep["day"]["fired"]["sleep_hours_change"]["windows"] == 2
    assert "sleep_hours_change" not in rep["day"]["dead"] and "glucose_TIR_change_points" in rep["day"]["dead"]
    assert rep["day"]["any_crossed"] == 2


def test_lab_cgm_discordance_is_month_only_and_inclusive():
    assert "lab_cgm_discordance" in ANCHOR_NAMES["month"]
    assert "lab_cgm_discordance" not in ANCHOR_NAMES["day"] and "lab_cgm_discordance" not in ANCHOR_NAMES["week"]
    t = ANCHORS["month"]["lab_cgm_discordance"]
    assert t == 0.5
    assert evaluate_anchors("month", {**QUIET, "lab_cgm_gap": 0.5}, 3) == ["lab_cgm_discordance"]  # >= , not >
    assert evaluate_anchors("month", {**QUIET, "lab_cgm_gap": -0.5}, 3) == ["lab_cgm_discordance"]  # either direction
    assert evaluate_anchors("month", {**QUIET, "lab_cgm_gap": 0.49}, 3) == []
    assert evaluate_anchors("month", {**QUIET, "lab_cgm_gap": None}, 3) == []  # no lab in the window
    # a lab_cgm_gap on a day/week record is ignored: the anchor is not configured there
    assert evaluate_anchors("week", {**QUIET, "lab_cgm_gap": 5.0}, 3) == []


def test_lab_cgm_discordance_is_in_the_dead_anchor_report():
    rep = anchor_fire_report({"day": [[]], "week": [[]], "month": [["lab_cgm_discordance"], []]})
    assert rep["month"]["fired"]["lab_cgm_discordance"]["windows"] == 1
    rep = anchor_fire_report({"day": [[]], "week": [[]], "month": [[], []]})
    assert "lab_cgm_discordance" in rep["month"]["dead"]
