"""The wording classes (findings_engine_spec.md 7.3 as amended): the precedence, row by row."""

import pytest

from v0_code.findings_engine.wording import CLAIM, CLASSES, classify_event, classify_relationship


def r(label, flags=(), exposure="exposed", reason=None):
    return classify_relationship(label, list(flags), exposure, reason)


def test_there_are_eleven_classes():
    assert len(CLASSES) == 11 and set(CLAIM) <= set(CLASSES)


@pytest.mark.parametrize("label,flags,exposure,reason,expected", [
    ("supported", [], "exposed", None, "asserted"),
    ("supported", ["same_day_unverified"], "exposed", None, "asserted_same_day"),
    ("suggestive", [], "exposed", None, "hedged"),
    ("suggestive", ["same_day_unverified"], "exposed", None, "hedged_same_day"),
    ("suggestive", ["placebo_fired"], "exposed", None, "exposure_only"),
    ("suggestive", ["placebo_fired", "same_day_unverified"], "exposed", None, "exposure_only"),
    ("not_supported", ["contrary"], "exposed", None, "contrary_note"),
    ("not_supported", ["contrary", "same_day_unverified"], "exposed", None, "contrary_note"),
    ("not_supported", ["contrary", "placebo_fired"], "exposed", None, "exposure_only"),
    ("not_supported", [], "exposed", None, "exposure_only"),
    ("not_supported", ["placebo_fired"], "exposed", None, "exposure_only"),
    ("supported", [], "not_exposed", None, "not_mentioned"),
    ("suggestive", ["placebo_fired"], "not_exposed", None, "not_mentioned"),
    ("not_supported", ["contrary"], "not_exposed", None, "not_mentioned"),
    ("not_supported", [], "not_exposed", None, "not_mentioned"),
    ("supported", [], "no_data", None, "not_mentioned"),
    ("supported", [], "not_yet_available", None, "not_known_yet"),
    ("not_supported", ["contrary"], "not_yet_available", None, "not_known_yet"),
    ("suggestive", ["placebo_fired"], "not_yet_available", None, "not_known_yet"),
    ("insufficient", [], "not_yet_available", "history", "not_known_yet"),
    ("insufficient", [], "exposed", "history", "exposure_only_history"),
    ("insufficient", ["small_group"], "exposed", "small_group", "exposure_only_history"),
    ("insufficient", [], "not_exposed", "history", "not_mentioned"),
    ("insufficient", [], "exposed", "no_ordered_exposure", "not_mentioned"),
    ("insufficient", [], "exposed", "no_stream", "not_mentioned"),
    ("insufficient", [], "exposed", "no_variation", "not_mentioned"),
    ("insufficient", [], "exposed", "no_definition", "not_mentioned"),
    ("insufficient", [], "exposed", "no_meal_kind", "not_mentioned"),
    ("insufficient", [], "no_data", "no_ordered_exposure", "not_mentioned"),
])
def test_relationship_rows(label, flags, exposure, reason, expected):
    assert r(label, flags, exposure, reason) == expected


@pytest.mark.parametrize("check,label,exposure,present,expected", [
    ("percentile_vs_history", "supported", "exposed", None, "event_unusual"),
    ("percentile_vs_history", "supported", "not_exposed", None, "not_mentioned"),
    ("percentile_vs_history", "not_supported", "not_exposed", None, "not_mentioned"),
    ("percentile_vs_history", "insufficient", None, None, "not_mentioned"),
    ("shape_check", "supported", None, None, "artifact_note"),
    ("shape_check", "not_supported", None, None, "not_mentioned"),
    ("shape_check", "not_yet_available", None, None, "not_known_yet"),
    ("shape_check", "insufficient", None, None, "not_mentioned"),
    ("presence_check", "not_applicable", None, True, "exposure_only"),
    ("presence_check", "not_applicable", None, False, "not_mentioned"),
    ("pattern_repeat", "supported", None, None, "exposure_only"),
    ("pattern_repeat", "not_supported", None, None, "not_mentioned"),
    ("pattern_repeat", "insufficient", None, None, "not_mentioned"),
    ("pattern_repeat", "not_applicable", None, None, "not_mentioned"),
])
def test_event_level_rows(check, label, exposure, present, expected):
    assert classify_event(check, label, exposure, present) == expected


def test_tier_and_rank_never_matter():
    assert r("supported") == classify_relationship("supported", [], "exposed", None)
    import inspect
    assert "tier" not in inspect.signature(classify_relationship).parameters and "rank" not in inspect.signature(classify_relationship).parameters
