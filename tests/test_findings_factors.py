"""The factor table, mode, groups, positions, history note, repeat information and code line (findings_engine_spec.md 7 as amended), on hand-built event records and the
real Evidence library and phrase book. Nothing here needs a database or a model."""

import re
from pathlib import Path

import pytest

from v0_code.evidence_engine.library import load_library
from v0_code.findings_engine.codeline import build_code_line
from v0_code.findings_engine.factors import Item, NullPi, build_content
from v0_code.intel_common.phrasebook import Phrasebook

ROOT = Path(__file__).resolve().parent.parent
LIB = load_library(ROOT / "config/evidence_library_v0.yaml")
PB = Phrasebook.load(ROOT / "config/findings_phrasebook_v0.yaml")


def F(rank, cand, key=None, support="not_supported", flags=(), state="exposed", tail=None, check="group_comparison", reason=None, es=None, date="2026-09-17", tier="secondary"):
    f = {"rank": rank, "weight_tier": tier, "candidate": cand, "check_type": check, "relationship_evidence_id": f"rel|{key}|{date}|ev-v0" if key else None, "support": support, "flags": list(flags),
         "event_exposure": None if state is None else {"state": state, "anchor": "meal_start", **({"tail_percentile": tail} if tail is not None else {})}, "event_specific": es}
    if reason:
        f["reason"] = reason
    return f


def item(hid, opened, factors, measure="glucose", direction="above", size="clearly", overlap=(), date="2026-09-17", rule="r"):
    h = {"handoff_id": hid, "measure": measure, "direction": direction, "size": size, "opened_at": opened}
    ev = {"evidence_id": f"ev_{hid}", "handoff_id": hid, "rule_id": rule, "event_time": opened, "as_of_date": date, "factors": factors, "overlap": list(overlap), "not_tested": [], "counts": {}}
    return Item(h, ev)


def content(items, completions=None, pi=None):
    return build_content(items, completions or {}, LIB, PB, pi or NullPi())


SLEEP = "sleep_hours@prev_night->post_meal_peak:dinner"
MISS = "missed_dose@2d->post_meal_peak:dinner"
STRESS = "strained_period@1d->post_meal_peak:dinner"
STEPS = "steps_total@1d->post_meal_peak:dinner"
ILL = "symptom_entry@3d->post_meal_peak:dinner"
MEAL = dict(check="percentile_vs_history", support="supported", state="exposed", tier="primary",
            es={"elapsed_minutes": 62, "bucket_minutes": 60, "bucket_size": 15, "observed": 185.0, "history_n": 347, "history_median": 150.1, "history_p90": 167.4, "percentile": 99})


def example_a():
    glucose = item("handoff_glucose_2026-09-17T22:30", "2026-09-17T22:30:00+05:30", [
        F(1, "meal_composition", **MEAL),
        F(2, "medication_adherence", MISS, "supported", ["same_day_unverified"], "exposed"),
        F(3, "sleep", SLEEP, "supported", [], "exposed", tail=0.6),
        F(4, "stress_mood", STRESS, "not_supported", [], "exposed"),
        F(5, "activity", STEPS, "not_supported", ["same_day_unverified"], "not_yet_available"),
        F(6, "illness_symptoms", ILL, "not_supported", ["contrary", "placebo_fired"], "not_exposed"),
        F(10, "alcohol", "alcohol_entry@1d->post_meal_peak:dinner", "insufficient", ["small_group"], "not_exposed", reason="small_group", tier="tertiary")],
        overlap=[{"a": "sleep_hours@prev_night", "b": "missed_dose@2d", "a_view": "worst_quartile", "b_view": "binary", "share_given_a": 0.78, "share_overall": 0.71, "ratio": 1.1, "flag": False}])
    hr = item("handoff_heart_rate_2026-09-17T21:45", "2026-09-17T21:45:00+05:30", [], measure="heart_rate")
    return [hr, glucose]


def by_cand(c, name):
    return next(f for f in c["factors"] if f["candidate"] == name)


# ---- example A --------------------------------------------------------------------------------------------------------------------------------------------
def test_example_a_mode_classes_groups_and_positions():
    c = content(example_a())
    assert c["mode"] == "relationship"
    classes = {f["candidate"]: f["wording_class"] for f in c["factors"]}
    assert classes == {"meal_composition": "event_unusual", "medication_adherence": "asserted_same_day", "sleep": "asserted", "stress_mood": "exposure_only", "activity": "not_known_yet",
                       "illness_symptoms": "not_mentioned", "alcohol": "not_mentioned"}
    assert c["groups"] == [{"group_id": "g1", "reason": "co_exposed", "members": ["f2", "f3"]}] and by_cand(c, "sleep")["group"] == "g1" and by_cand(c, "meal_composition")["group"] is None
    assert by_cand(c, "sleep")["position"] == "among the very lowest she has had"
    assert by_cand(c, "meal_composition")["position"] == "among the very highest she has had within the hour or so after dinners"
    assert c["history_note"] == "enough"
    assert c["not_known_yet"] == ["the day's step total"]
    assert [f["factor_id"] for f in c["factors"]] == ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]
    assert c["repeat"] == [{"relationship_key": MISS, "pi_status": None, "seen_before": "none"}, {"relationship_key": SLEEP, "pi_status": None, "seen_before": "none"}]
    assert [m["measure_id"] for m in c["measures"]] == ["m1", "m2"] and c["measures"][1]["measure"] == "glucose"


def test_example_a_code_line_matches_the_spec_template_without_numbers():
    c = content(example_a())
    line = build_code_line(c, PB)
    assert line.startswith("Heart rate was clearly above her usual. Glucose was clearly above her usual.")
    assert "Present: missed doses on the same day or the day before, short sleep the night before (among the very lowest she has had)." in line
    assert "Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner in her history." in line
    assert "Short sleep the night before has tended to move together with higher glucose peaks after dinner in her history." in line
    assert "The size of this meal's rise was among the very highest she has had within the hour or so after dinners." in line
    assert "Also present, with no link claimed: a stressed or low-mood period on the same day." in line
    assert line.endswith("Not known yet: the day's step total.")
    assert not re.search(r"\d", line) and "alcohol" not in line.lower() and "symptom" not in line.lower()


# ---- merging ---------------------------------------------------------------------------------------------------------------------------------------------
def test_relationship_factors_merge_by_key_with_the_latest_outcome_date_and_exposure_precedence():
    a = item("h1", "2026-09-17T23:30:00+05:30", [F(3, "sleep", SLEEP, "suggestive", ["same_day_unverified"], "not_yet_available", date="2026-09-17")], date="2026-09-17")
    b = item("h2", "2026-09-18T01:00:00+05:30", [F(3, "sleep", SLEEP, "supported", [], "exposed", tail=3.0, date="2026-09-18")], date="2026-09-18")
    c = content([a, b])
    (f,) = c["factors"]
    assert f["label"] == "supported" and f["flags"] == [] and f["exposure"] == "exposed" and f["handoff_ids"] == ["h1", "h2"] and f["wording_class"] == "asserted"
    assert f["relationship_evidence_ids"] == [f"rel|{SLEEP}|2026-09-17|ev-v0", f"rel|{SLEEP}|2026-09-18|ev-v0"] and f["position"] == "among the very lowest she has had"
    assert content([b, a])["factors"][0]["label"] == "supported"                                      # the latest outcome date wins whatever the order
    same_day = item("h3", "2026-09-17T23:45:00+05:30", [F(3, "sleep", SLEEP, "suggestive", ["contrary"], "exposed", date="2026-09-17")])
    flags = content([a, same_day])["factors"][0]["flags"]
    assert sorted(flags) == ["contrary", "same_day_unverified"]                                       # flags are the union within the latest date


@pytest.mark.parametrize("states,expected", [(["not_exposed", "exposed"], "exposed"), (["not_exposed", "not_yet_available"], "not_yet_available"), (["no_data", "not_exposed"], "not_exposed"),
                                             (["no_data", "no_data"], "no_data"), (["not_yet_available", "exposed", "not_exposed"], "exposed")])
def test_exposure_precedence(states, expected):
    items = [item(f"h{i}", f"2026-09-17T2{i}:00:00+05:30", [F(3, "sleep", SLEEP, "supported", [], s)]) for i, s in enumerate(states)]
    assert content(items)["factors"][0]["exposure"] == expected


def test_event_level_factors_merge_only_for_presence_checks():
    pk = dict(check="percentile_vs_history", support="supported", state="exposed", es={"elapsed_minutes": 62, "bucket_minutes": 60, "percentile": 96})
    pres = dict(check="presence_check", support="not_applicable", state=None, es={"present": True})
    a = item("h1", "2026-09-17T10:00:00+05:30", [F(1, "meal_composition", **pk), F(8, "thyroid_status", **pres)])
    b = item("h2", "2026-09-17T15:00:00+05:30", [F(1, "meal_composition", **pk), F(8, "thyroid_status", **pres)])
    c = content([a, b])
    assert [f["candidate"] for f in c["factors"]] == ["meal_composition", "thyroid_status", "meal_composition"]
    assert by_cand(c, "thyroid_status")["handoff_ids"] == ["h1", "h2"] and c["factors"][0]["handoff_ids"] == ["h1"] and c["factors"][2]["handoff_ids"] == ["h2"]
    assert by_cand(c, "thyroid_status")["wording_class"] == "exposure_only"
    assert c["factors"][0]["position"] == "among the very highest she has had within the hour or so after meals"


def test_factors_without_a_key_merge_by_candidate_and_reason_and_are_never_mentioned():
    a = item("h1", "2026-09-17T10:00:00+05:30", [F(9, "cycle_phase", None, "insufficient", [], None, reason="no_definition")])
    b = item("h2", "2026-09-17T11:00:00+05:30", [F(9, "cycle_phase", None, "insufficient", [], None, reason="no_definition"), F(2, "sleep", None, "insufficient", [], None, reason="no_meal_kind")])
    c = content([a, b])
    assert [(f["candidate"], f["kind"], f["wording_class"], f["handoff_ids"]) for f in c["factors"]] == [("cycle_phase", "unavailable", "not_mentioned", ["h1", "h2"]), ("sleep", "unavailable", "not_mentioned", ["h2"])]
    assert c["factors"][0]["insufficient_reason"] == "no_definition" and c["history_note"] == "enough"


def test_a_completion_fills_the_shape_label_of_its_factor():
    shape = dict(check="shape_check", support="not_yet_available", state=None, es={"earliest_evaluation_time": "2026-09-17T12:00:00+05:30"})
    it = item("h1", "2026-09-17T11:00:00+05:30", [F(1, "sensor_artifact", **shape)])
    f0 = content([it])["factors"][0]
    assert f0["label"] == "not_yet_available" and f0["wording_class"] == "not_known_yet"
    done = content([it], {("ev_h1", "sensor_artifact"): {"support": "supported", "completion_id": "ev_h1#sensor_artifact"}})
    assert done["factors"][0]["label"] == "supported" and done["factors"][0]["wording_class"] == "artifact_note" and done["completion_ids"] == ["ev_h1#sensor_artifact"]
    assert "may be a sensor artifact" in build_code_line(done, PB) and done["not_known_yet"] == []


# ---- mode ---------------------------------------------------------------------------------------------------------------------------------------------
def test_mode_needs_an_exposed_usable_relationship_factor_with_a_claim_class():
    only_event = item("h1", "2026-09-18T15:15:00+05:30", [F(1, "meal_composition", **MEAL), F(2, "sleep", SLEEP, "insufficient", [], "exposed", reason="history")])
    assert content([only_event])["mode"] == "descriptive"
    placebo = item("h2", "2026-09-18T15:15:00+05:30", [F(2, "sleep", SLEEP, "suggestive", ["placebo_fired"], "exposed")])
    assert content([placebo])["mode"] == "descriptive"
    not_exposed = item("h3", "2026-09-18T15:15:00+05:30", [F(2, "sleep", SLEEP, "supported", [], "not_exposed")])
    assert content([not_exposed])["mode"] == "descriptive"
    usable = item("h4", "2026-09-18T15:15:00+05:30", [F(2, "sleep", SLEEP, "suggestive", [], "exposed")])
    assert content([usable])["mode"] == "relationship"


def test_event_statements_are_added_in_descriptive_mode_and_the_meal_line_is_in_example_b():
    lunch = lambda k: k.replace(":dinner", ":lunch")
    it = item("h1", "2025-11-18T15:15:00+05:30", [F(1, "meal_composition", **{**MEAL, "es": {**MEAL["es"], "percentile": 97}}), F(3, "sleep", lunch(SLEEP), "insufficient", [], "exposed", tail=0.0, reason="history"),
                                                  F(2, "medication_adherence", lunch(MISS), "insufficient", ["same_day_unverified"], "exposed", reason="history")], date="2025-11-18")
    c = content([it])
    assert c["mode"] == "descriptive" and c["history_note"] == "not_enough_history_yet"
    line = build_code_line(c, PB)
    assert "The size of this meal's rise was among the very highest she has had within the hour or so after lunches." in line
    assert "Present: missed doses on the same day or the day before, short sleep the night before (among the very lowest she has had)." in line
    assert line.endswith("There is not enough history yet to say what usually goes with this.") and not re.search(r"\d", line)


# ---- groups ---------------------------------------------------------------------------------------------------------------------------------------------
def test_entangled_groups_are_connected_components_among_claim_class_factors_only():
    keys = {"a": "sleep_hours@prev_night->hr_day_mean", "b": "missed_dose@2d->hr_day_mean", "c": "hydration_total@prev_day->hr_day_mean", "d": "strained_period@same_day->hr_day_mean", "e": "symptom_entry@3d->hr_day_mean"}
    fs = [F(1, "sleep", keys["a"], "supported", [], "exposed", tail=1.0), F(2, "x", keys["b"], "supported", ["same_day_unverified"], "exposed"), F(3, "y", keys["c"], "suggestive", [], "exposed", tail=10.0),
          F(4, "z", keys["d"], "supported", [], "exposed"), F(5, "w", keys["e"], "suggestive", ["placebo_fired"], "exposed")]
    ov = [{"a": "sleep_hours@prev_night", "b": "missed_dose@2d", "a_view": "x", "b_view": "y", "share_given_a": 0.9, "share_overall": 0.3, "ratio": 3.0, "flag": True},
          {"a": "hydration_total@prev_day", "b": "strained_period@same_day", "a_view": "x", "b_view": "y", "share_given_a": 0.9, "share_overall": 0.3, "ratio": 3.0, "flag": True},
          {"a": "symptom_entry@3d", "b": "sleep_hours@prev_night", "a_view": "x", "b_view": "y", "share_given_a": 0.9, "share_overall": 0.3, "ratio": 3.0, "flag": True}]
    c = content([item("h1", "2026-09-17T10:00:00+05:30", fs, measure="heart_rate", overlap=ov)])
    assert c["groups"] == [{"group_id": "g1", "reason": "entangled", "members": ["f1", "f2"]}, {"group_id": "g2", "reason": "entangled", "members": ["f3", "f4"]}]      # f5 is exposure_only: no member
    line = build_code_line(c, PB)
    assert line.count("often occur together") == 2 and "separate roles cannot be told apart" in line


def test_a_single_claim_factor_has_no_group_and_event_factors_are_never_members():
    c = content([item("h1", "2026-09-17T10:00:00+05:30", [F(1, "meal_composition", **MEAL), F(3, "sleep", SLEEP, "supported", [], "exposed", tail=1.0)])])
    assert c["groups"] == [] and all(f["group"] is None for f in c["factors"])


def test_overlap_entries_are_matched_inside_their_own_record():
    k1, k2 = "sleep_hours@prev_night->post_meal_peak:dinner", "missed_dose@2d->post_meal_peak:dinner"
    ov = [{"a": "sleep_hours@prev_night", "b": "missed_dose@2d", "a_view": "x", "b_view": "y", "share_given_a": 0.9, "share_overall": 0.3, "ratio": 3.0, "flag": True}]
    one = item("h1", "2026-09-17T20:00:00+05:30", [F(3, "sleep", k1, "supported", [], "exposed", tail=1.0)])
    two = item("h2", "2026-09-17T21:00:00+05:30", [F(2, "medication_adherence", k2, "supported", ["same_day_unverified"], "exposed")], overlap=ov)
    assert content([one, two])["groups"][0]["reason"] == "co_exposed"            # the entry sits in h2's record, where the sleep factor is absent: not entangled
    both = item("h2", "2026-09-17T21:00:00+05:30", [F(3, "sleep", k1, "supported", [], "exposed", tail=1.0), F(2, "medication_adherence", k2, "supported", ["same_day_unverified"], "exposed")], overlap=ov)
    assert content([both])["groups"][0]["reason"] == "entangled"


# ---- history note ---------------------------------------------------------------------------------------------------------------------------------------
def test_history_note_partition():
    def mk(reasons):
        fs = [F(i + 1, "c", f"sleep_hours@prev_night->post_meal_peak:{k}", "insufficient" if r else "not_supported", [], "not_exposed", reason=r) for i, (r, k) in enumerate(zip(reasons, ["breakfast", "lunch", "dinner", "kindx"]))]
        return content([item("h1", "2026-09-17T10:00:00+05:30", fs)])["history_note"]
    assert mk(["history", "history", "history"]) == "not_enough_history_yet"
    assert mk(["history", None, None]) == "enough_for_some"
    assert mk([None, None, None]) == "enough"
    assert mk(["history", "history", None, None]) == "enough_for_some"          # exactly half is not "more than half"
    assert mk(["history", "history", "history", None]) == "not_enough_history_yet"
    assert content([item("h1", "2026-09-17T10:00:00+05:30", [])])["history_note"] == "enough"


# ---- positions, repeat, measures --------------------------------------------------------------------------------------------------------------------------
def test_positions_use_the_exposures_risk_side_and_skip_binarized_exposures():
    hi = item("h1", "2026-09-17T10:00:00+05:30", [F(1, "screen_time", "screen_hours@prev_evening->sleep_hours_night", "supported", [], "exposed", tail=97.0),
                                               F(2, "unusual_activity", "high_steps_day@1d->day_min_glucose", "supported", ["same_day_unverified"], "exposed"),
                                               F(3, "hydration", "hydration_total@prev_day->hr_day_mean", "supported", [], "exposed", tail=20.0)])
    c = content([hi])
    assert [f["position"] for f in c["factors"]] == ["among the very highest she has had", None, "low for her"]


class FakePi:
    def seen_before(self, key, exclude_case=None):
        return {"missed_dose@2d->post_meal_peak:dinner": "this_week"}.get(key, "earlier")

    def status(self, key):
        return "candidate" if key.startswith("missed") else None


def test_repeat_information_comes_from_pi_and_never_changes_a_class():
    c = content(example_a(), pi=FakePi())
    assert c["repeat"] == [{"relationship_key": MISS, "pi_status": "candidate", "seen_before": "this_week"}, {"relationship_key": SLEEP, "pi_status": None, "seen_before": "earlier"}]
    assert [f["wording_class"] for f in c["factors"]] == [f["wording_class"] for f in content(example_a())["factors"]]


def test_measures_are_unique_per_measure_and_direction_with_the_strongest_strength():
    items = [item("h1", "2026-09-17T08:00:00+05:30", [], measure="heart_rate", size="clearly"), item("h2", "2026-09-17T09:00:00+05:30", [], measure="heart_rate", size="far"),
             item("h3", "2026-09-17T10:00:00+05:30", [], measure="sleep_duration", direction="below")]
    m = content(items)["measures"]
    assert [(x["measure_id"], x["measure"], x["direction"], x["strength"], x["opened_at"]) for x in m] == [
        ("m1", "heart_rate", "above", "far", "2026-09-17T08:00:00+05:30"), ("m2", "sleep_duration", "below", "clearly", "2026-09-17T10:00:00+05:30")]
    line = build_code_line(content(items), PB)
    assert line.startswith("Heart rate was far above her usual. She slept clearly less than usual.")


def test_every_class_that_can_appear_renders_without_digits_or_internal_words():
    for c in (content(example_a()), content([item("h1", "2026-09-17T10:00:00+05:30", [F(3, "sleep", SLEEP, "not_supported", ["contrary"], "exposed")])])):
        line = build_code_line(c, PB)
        assert not re.search(r"\d", line) and not any(re.search(r"\b" + w + r"\b", line.lower()) for w in PB.raw["internal_words"])
    assert "On days with short sleep the night before, her glucose peaks after dinner have tended to be lower." in build_code_line(content([item("h1", "2026-09-17T10:00:00+05:30", [F(3, "sleep", SLEEP, "not_supported", ["contrary"], "exposed")])]), PB)


def test_the_same_exposure_tested_against_several_outcomes_is_listed_once_in_the_code_line():
    hr = item("h1", "2026-09-17T21:45:00+05:30", [F(2, "sleep", "sleep_hours@prev_night->hr_day_mean", "supported", ["same_day_unverified"], "exposed", tail=1.0)], measure="heart_rate")
    gl = item("h2", "2026-09-17T22:30:00+05:30", [F(3, "sleep", SLEEP, "supported", [], "exposed", tail=1.0), F(4, "stress_mood", STRESS, "not_supported", [], "exposed")])
    c = content([hr, gl])
    assert [f["candidate"] for f in c["factors"]] == ["sleep", "sleep", "stress_mood"] and [f["wording_class"] for f in c["factors"]] == ["asserted_same_day", "asserted", "exposure_only"]
    line = build_code_line(c, PB)
    assert line.count("short sleep the night before (among the very lowest she has had)") == 1 and "Present: short sleep the night before (among the very lowest she has had)." in line
    assert "higher heart rate over the day" in line and "higher glucose peaks after dinner" in line                  # one claim sentence per relationship
    assert "Also present, with no link claimed: a stressed or low-mood period on the same day." in line
    shown = content([hr, item("h3", "2026-09-17T23:00:00+05:30", [F(4, "stress_mood", "strained_period@1d->hr_day_mean", "supported", [], "exposed")])])
    assert "Also present" not in build_code_line(shown, PB)                                                          # an exposure already claimed is not repeated as "no link"


def test_a_contrary_note_names_the_exposure_it_refers_to():
    """A contrary note names its exposure in the sentence ("On days with <exposure>, ...") and the exposure is listed under Present, in both modes, not repeated as "no link"."""
    rel = content([item("h1", "2026-09-17T10:00:00+05:30", [F(2, "sleep", SLEEP, "supported", [], "exposed", tail=1.0), F(3, "illness_symptoms", ILL, "not_supported", ["contrary"], "exposed")]),
                   item("h2", "2026-09-17T11:00:00+05:30", [F(3, "illness_symptoms", "symptom_entry@3d->hr_day_mean", "not_supported", [], "exposed")])])
    line = build_code_line(rel, PB)
    assert rel["mode"] == "relationship" and "Present: short sleep the night before (among the very lowest she has had), a symptom noted in the diary on the same day or in the days before." in line
    assert "On days with a symptom noted in the diary on the same day or in the days before, her glucose peaks after dinner have tended to be lower." in line and "Also present" not in line
    assert "On days like this" not in line
    desc = content([item("h1", "2026-09-17T10:00:00+05:30", [F(3, "illness_symptoms", ILL, "not_supported", ["contrary"], "exposed")])])
    assert desc["mode"] == "descriptive" and build_code_line(desc, PB).split(". ", 2)[1].startswith("Present: a symptom noted in the diary on the same day or in the days before")


# ---- the four small changes after F1 ---------------------------------------------------------------------------------------------------------------------
def test_presence_check_facts_stay_in_the_structured_layer_but_not_in_the_code_line():
    pres = dict(check="presence_check", support="not_applicable", state=None, es={"present": True})
    patt = dict(check="pattern_repeat", support="supported", state=None, es={})
    c = content([item("h1", "2026-09-17T10:00:00+05:30", [F(2, "sleep", SLEEP, "supported", [], "exposed", tail=1.0), F(8, "thyroid_status", **pres), F(9, "dawn_effect", **patt)])])
    kept = {f["candidate"]: f["wording_class"] for f in c["factors"]}
    assert kept["thyroid_status"] == "exposure_only" and kept["dawn_effect"] == "exposure_only"            # the structured layer is unchanged
    line = build_code_line(c, PB)
    assert "thyroid" not in line and "an early-morning rise" in line                                    # a pattern is not a static fact
    only = content([item("h1", "2026-09-17T10:00:00+05:30", [F(8, "thyroid_status", **pres)], measure="heart_rate")])
    assert build_code_line(only, PB) == "Heart rate was clearly above her usual." and only["factors"][0]["wording_class"] == "exposure_only"


def test_the_phrase_book_marks_exactly_the_presence_checks_as_static():
    for name, c in LIB.event_checks.items():
        assert bool(PB.raw["event_checks"][name].get("static")) == (c["type"] == "presence_check"), name
    assert PB.is_static("thyroid_status") and not PB.is_static("dawn_effect") and not PB.is_static("meal_composition")


def test_the_co_exposed_sentence_says_they_were_both_present():
    c = content(example_a())
    line = build_code_line(c, PB)
    assert "Missed doses on the same day or the day before and short sleep the night before were both present." in line
    assert "explanation" not in line and "stands alone" not in line
    three = content([item("h1", "2026-09-17T10:00:00+05:30", [F(2, "missed", MISS, "supported", ["same_day_unverified"], "exposed"), F(3, "sleep", SLEEP, "supported", [], "exposed", tail=1.0),
                                                           F(4, "symptoms", ILL, "supported", [], "exposed")])])
    assert "Missed doses on the same day or the day before, short sleep the night before and a symptom noted in the diary on the same day or in the days before were all present." in build_code_line(three, PB)


def test_the_entangled_sentence_is_unchanged():
    ov = [{"a": "sleep_hours@prev_night", "b": "missed_dose@2d", "a_view": "x", "b_view": "y", "share_given_a": 0.9, "share_overall": 0.3, "ratio": 3.0, "flag": True}]
    c = content([item("h1", "2026-09-17T10:00:00+05:30", [F(2, "sleep", "sleep_hours@prev_night->hr_day_mean", "supported", [], "exposed", tail=1.0),
                                                       F(3, "missed", "missed_dose@2d->hr_day_mean", "supported", ["same_day_unverified"], "exposed")], overlap=ov)])
    assert "Short sleep the night before and missed doses on the same day or the day before often occur together, so their separate roles cannot be told apart." in build_code_line(c, PB)
