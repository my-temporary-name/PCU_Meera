"""The shared phrase book (config/findings_phrasebook_v0.yaml): its load check against the Evidence library, and the wording helpers both components use."""

import copy
import re
from pathlib import Path

import pytest
import yaml

from v0_code.evidence_engine.library import KEY, load_library
from v0_code.intel_common.phrasebook import Phrasebook, PhrasebookError

ROOT = Path(__file__).resolve().parent.parent
PB = ROOT / "config/findings_phrasebook_v0.yaml"
LIB = load_library(ROOT / "config/evidence_library_v0.yaml")


def raw():
    return copy.deepcopy(yaml.safe_load(PB.read_text()))


def test_the_real_phrase_book_covers_the_whole_evidence_library():
    pb = Phrasebook.load(PB)
    pb.check(LIB)
    assert len(pb.raw["classes"]) == 11 and len(pb.raw["exposures"]) == 16 and len(pb.raw["outcomes"]) == 10 and len(pb.raw["windows"]) == 11


@pytest.mark.parametrize("path,word", [
    (("exposures", "sleep_hours"), "sleep_hours"), (("outcomes", "post_meal_peak"), "post_meal_peak"), (("windows", "prev_night"), "prev_night"),
    (("event_checks", "sensor_artifact"), "sensor_artifact"), (("classes", "hedged"), "hedged"), (("elapsed_words",), "elapsed_words"), (("position_bands",), "position_bands")])
def test_a_missing_entry_fails_the_load_check_with_a_plain_message(path, word):
    r = raw()
    node = r
    for p in path[:-1]:
        node = node[p]
    del node[path[-1]]
    with pytest.raises(PhrasebookError) as e:
        Phrasebook(r).check(LIB)
    assert word in str(e.value)


def test_phrases_have_no_digits_internal_words_or_counting_words():
    pb = Phrasebook.load(PB)
    for text in pb.all_phrases():
        low = text.lower()
        assert not re.search(r"\d", text), text
        for w in pb.raw["internal_words"] + pb.raw["counting_words"]:
            assert not re.search(r"\b" + re.escape(w) + r"\b", low), (w, text)


def test_a_bad_phrase_fails_the_load_check():
    r = raw()
    r["windows"]["3d"] = "in the first days before"
    with pytest.raises(PhrasebookError) as e:
        Phrasebook(r).check(LIB)
    assert "first" in str(e.value)
    r = raw()
    r["exposures"]["sleep_hours"]["phrase"] = "short sleep {window} in 2 nights"
    with pytest.raises(PhrasebookError):
        Phrasebook(r).check(LIB)


def test_exposure_phrases_with_windows_and_agreement():
    pb = Phrasebook.load(PB)
    assert pb.exposure("missed_dose", "2d") == "missed doses on the same day or the day before"
    assert pb.exposure("sleep_hours", "prev_night") == "short sleep the night before"
    assert pb.exposure("late_meal", "same_day") == "a late meal"
    assert pb.is_plural("missed_dose") and not pb.is_plural("sleep_hours")
    assert pb.outcome("post_meal_peak", "dinner") == "higher glucose peaks after dinner"
    assert pb.contrary("post_meal_peak", "dinner") == "her glucose peaks after dinner have tended to be lower"
    assert pb.outcome("systolic_reading", None) == "higher blood pressure readings"


def test_every_pair_of_the_library_renders_a_claim_sentence_with_same_day_where_required():
    pb = Phrasebook.load(PB)
    for p in LIB.runnable():
        e, tag, o, scoped = KEY.match(p["key"]).groups()
        s = pb.claim_sentence("asserted_same_day" if p["ordering"] == "same_day_unverified" else "asserted", e, tag, o, "dinner" if scoped else None)
        assert s[0].isupper() and s.endswith(".") and not re.search(r"\d", s)
        assert ("same day" in s) == (p["ordering"] == "same_day_unverified" or "same day" in pb.exposure(e, tag)), s
        h = pb.claim_sentence("hedged", e, tag, o, "dinner" if scoped else None)
        assert " may be linked to " in h


def test_has_and_have_and_the_same_day_tail():
    pb = Phrasebook.load(PB)
    assert pb.claim_sentence("asserted", "missed_dose", "2d", "post_meal_peak", "dinner") == "Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner in her history."
    assert pb.claim_sentence("asserted_same_day", "high_steps_day", "1d", "day_min_glucose", None) == "A very active day has tended to move together with a lower lowest glucose that day in her history, on the same day."
    assert pb.claim_sentence("asserted_same_day", "strained_period", "1d", "non_meal_mean", None).count("same day") == 1          # not repeated when the window phrase has it


@pytest.mark.parametrize("p,side,words", [(0.0, "low", "among the very lowest she has had"), (4.99, "low", "among the very lowest she has had"), (5.0, "low", "low for her"), (24.9, "low", "low for her"),
                                        (25.0, "low", None), (75.0, "high", "high for her"), (94.9, "high", "high for her"), (95.0, "high", "among the very highest she has had"), (100.0, "high", "among the very highest she has had"),
                                        (50.0, "high", None)])
def test_position_bands_are_closed_below_and_open_above(p, side, words):
    assert Phrasebook.load(PB).position(p, side) == words


def test_elapsed_and_meal_words():
    pb = Phrasebook.load(PB)
    assert [pb.elapsed(m) for m in (15, 45, 46, 90, 91, 200)] == ["half hour or so", "half hour or so", "hour or so", "hour or so", "couple of hours", "couple of hours"]
    assert [pb.meal_ago(m) for m in (5, 30, 62, 90, 120, 400)] == ["a short while earlier", "a short while earlier", "about an hour earlier", "about an hour earlier", "a couple of hours earlier", "a few hours earlier"]
    assert pb.meal_label("festive_dinner") == "a festive dinner" and pb.meal_label("early_snack") == "an early snack"
    assert pb.position_suffix("meal_composition", 60, "dinner") == "within the hour or so after dinners"
    assert pb.position_suffix("meal_composition", 60, None) == "within the hour or so after meals"
    assert pb.position_suffix("meal_skipped_or_delayed", 0, None) == "at this time of day"


MEASURES = ["glucose", "heart_rate", "resting_heart_rate", "sleep_duration", "medication_adherence", "blood_pressure", "hydration", "screen_time"]


def test_each_measure_has_a_phrase_per_direction_with_the_strength_slot():
    pb = Phrasebook.load(PB)
    for m in MEASURES:
        for d in ("above", "below"):
            assert "{strength}" in pb.raw["measures"][m][d], (m, d)
    assert pb.measure_clause("medication_adherence", "below", "clearly") == "clearly fewer doses were taken than usual"
    assert pb.measure_clause("medication_adherence", "above", "far") == "far more doses were taken than usual"
    assert pb.measure_clause("glucose", "above", "far") == "glucose was far above her usual"
    assert pb.measure_clause("sleep_duration", "below", "clearly") == "she slept clearly less than usual"


def test_measure_sentences_are_one_per_measure_in_order():
    pb = Phrasebook.load(PB)
    ms = [{"measure": "heart_rate", "direction": "above", "strength": "clearly"}, {"measure": "glucose", "direction": "above", "strength": "clearly"}]
    assert pb.measures_sentence(ms) == "Heart rate was clearly above her usual. Glucose was clearly above her usual."
    assert pb.measures_sentence(ms[:1]) == "Heart rate was clearly above her usual."
    mixed = ms + [{"measure": "sleep_duration", "direction": "below", "strength": "far"}, {"measure": "medication_adherence", "direction": "below", "strength": "far"}]
    assert pb.measures_sentence(mixed) == ("Heart rate was clearly above her usual. Glucose was clearly above her usual. She slept far less than usual. Far fewer doses were taken than usual.")
    with pytest.raises(PhrasebookError):
        pb.measures_sentence([{"measure": "no_such_measure", "direction": "above", "strength": "clearly"}])


def test_a_measure_without_a_direction_phrase_fails_the_load_check():
    r = raw()
    del r["measures"]["glucose"]["below"]
    with pytest.raises(PhrasebookError) as e:
        Phrasebook(r).check(LIB)
    assert "glucose" in str(e.value) and "below" in str(e.value)
    r = raw()
    r["measures"]["glucose"]["above"] = "glucose was above her usual"
    with pytest.raises(PhrasebookError):
        Phrasebook(r).check(LIB)                                                                   # the strength slot is required


def test_exposure_and_exposures_are_internal_words():
    pb = Phrasebook.load(PB)
    assert {"exposure", "exposures"} <= set(pb.raw["internal_words"])
    r = raw()
    r["windows"]["3d"] = "in the days of exposure before"
    with pytest.raises(PhrasebookError):
        Phrasebook(r).check(LIB)


def test_a_meal_label_with_a_number_in_it_is_worded_without_the_number():
    pb = Phrasebook.load(PB)
    assert pb.meal_label("festive_snack_1") == "a festive snack" and pb.meal_label("light_dinner") == "a light dinner" and pb.meal_label("early_evening_snack_2") == "an early evening snack"


def test_fluid_intake_is_worded_without_drinking():
    pb = Phrasebook.load(PB)
    assert pb.measure_clause("hydration", "below", "clearly") == "clearly less fluid was taken than usual"
    assert pb.measure_clause("hydration", "above", "far") == "far more fluid was taken than usual"
    assert not any(re.search(r"drink|drank", t) for t in pb.all_phrases())
