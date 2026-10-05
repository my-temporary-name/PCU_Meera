"""Validator-side tests: the annotated plain-English view, the sanitizer, grounding tolerance, caps, co-movement,
questionable-reading handling and the material-change checks.

None of these call the LLM — they feed a record and a hand-written entry straight to the code that decides
whether an entry is acceptable.
"""

import copy

from v0_code.logic.record_view import annotate, to_plain
from v0_code.nodes.memory_llm import (
    GROUNDING, CoMovement, MemoryEntry, Refs, Statement, _MISSING, caps_for, code_unremarkable,
    sanitize_text, validate_entry, DiaryStatement,
)

RANKED = [
    {"name": "steps", "direction": "down", "amount": 802.8, "unit": "steps", "relation": "opposite", "strength": 3.1},
    {"name": "sleep", "direction": "up", "amount": 0.5, "unit": "hours", "relation": "same", "strength": 2.0},
    {"name": "hydration", "direction": "down", "amount": 300.0, "unit": "mL", "relation": "opposite", "strength": 1.5},
]
RECORD = {
    "window_id": "day_2026-01-05", "tier": "day", "date": "2026-01-05",
    "glucose": {"mean": 142.5, "tir_pct": 88.4, "cv_pct": 24.1, "tbr_pct": 0.0, "completeness_pct": 97.0},
    "sleep": {"duration_hours": 6.4},
    "activity": {"total_steps": 1802.0},
    "deltas": {"glucose_tir_pct": -4.2, "sleep_hours": 0.5},
    "stream_direction_table": {"glucose": "up", "sleep": "up", "steps": "down"},
    "stream_change_table": {"glucose": 6.0, "sleep": 0.5, "steps": -802.8},
    "co_movement_candidates": {"glucose_direction": "up", "glucose_change": 6.0, "same_direction": ["sleep"], "opposite_direction": ["steps", "hydration"],
                               "flat": [], "moved_while_glucose_flat": [], "unavailable": [], "ranked": RANKED},
    "anchors_crossed": [], "anchors_questionable": [], "has_diary_event": False, "quiet": False,
    "material_changes": [], "data_quality_flags": [], "data_quality_details": [], "diary_events": [],
    "adherence": {"per_medication": {"med_002_metformin": "missed", "med_003_amlodipine": "taken"}},
    "reliable": True, "confidence": "high",
}


def _entry(**kw) -> MemoryEntry:
    base = dict(window_id="day_2026-01-05", tier="day", headline="A day.", is_notable=False)
    return MemoryEntry(**{**base, **kw})


def _resolver(record, prior=None):
    return Refs(annotate(record, caps_for(record)["co_movement"]), annotate(prior) if prior else None, record["window_id"])


def _validate(entry, record=RECORD):
    return validate_entry(entry, record, None, _resolver(record), record["window_id"])


def _comove(*items) -> list[CoMovement]:
    return list(items)


GOOD_COMOVE = _comove(
    CoMovement(statement="Her steps fell 802.8 steps, the opposite way to glucose, which rose.", streams=["steps"], evidence_refs=["co_movement_required[0].amount"]),
    CoMovement(statement="Her sleep rose 0.5 hours, the same way as glucose.", streams=["sleep"], evidence_refs=["co_movement_required[1].amount"]),
    CoMovement(statement="Her hydration fell 300 mL, the opposite way to glucose.", streams=["hydration"], evidence_refs=["co_movement_required[2].amount"]),
)


def _failures(entry, record=RECORD, kind=None):
    f = _validate(entry, record)
    return [x for x in f if kind is None or x.startswith(kind)]


def _good(**kw):
    """An entry that satisfies the co-movement and missed-dose requirements, plus whatever is under test."""
    base = dict(co_movement=GOOD_COMOVE, key_observations=[Statement(statement="Metformin was missed.", evidence_refs=[])])
    return _entry(**{**base, **kw})


# ---- plain view ----------------------------------------------------------------------------------------

def test_plain_view_renames_keys_and_paths_resolve_back():
    plain, path_map, labels = to_plain(annotate(RECORD))
    assert plain["glucose"]["time in range percent"] == 88.4
    assert plain["changes vs previous window"]["change in sleep hours"] == 0.5
    assert path_map["glucose.time in range percent"] == "glucose.tir_pct"
    assert labels["tir_pct"] == "time in range percent"


def test_category_and_status_values_and_medicine_ids_are_plain_words():
    rec = {**RECORD, "mood": {"morning": {"category": "calm_stable", "label": "x"}, "evening": {"category": "positive_uplifted", "label": "y"}},
           "sleep": {"duration_hours": 6.4, "status": "borderline_low"}}
    plain, _, _ = to_plain(annotate(rec))
    assert plain["mood"]["morning"]["category"] == "calm" and plain["mood"]["evening"]["category"] == "uplifted"
    assert plain["sleep"]["compared with the reference range"] == "slightly below the reference range"
    assert "metformin" in plain["medication adherence"]["each medicine"] and "med_002_metformin" not in str(plain)


def test_resolver_accepts_plain_internal_and_sloppy_paths():
    r = _resolver(RECORD)
    for ref in ("glucose.time in range percent", "glucose.tir_pct", "Glucose.Time In Range Percent", "record.glucose.time in range percent"):
        assert r.resolve(ref) == 88.4
    assert r.resolve("glucose.nothing_here") is _MISSING


def test_sanitizer_rewrites_leaked_keys_values_and_short_dates():
    _, _, labels = to_plain(annotate(RECORD))
    assert sanitize_text("total_steps fell on 01-05", labels, RECORD, "t") == "steps fell on 2026-01-05"
    assert sanitize_text("her mood was calm_stable", {"calm_stable": "calm"}, RECORD, "t") == "her mood was calm"
    assert sanitize_text("steps ran 1600-2000", labels, RECORD, "t") == "steps ran 1600-2000"  # a range is not a date


# ---- annotate: questionable readings, per-metric notes ---------------------------------------------------

def _artifact_record(flag="known_clip_artifact_reading:65.0", affects=("tbr_pct", "tbr_severe_pct", "min_value")):
    rec = copy.deepcopy(RECORD)
    rec["glucose"].update({"tbr_pct": 0.15, "min_value": 65.0, "tir_pct": 99.7, "cv_pct": 11.32})
    rec["glucose"]["questionable_excluded"] = {
        "n_excluded": 1, "excluded_values": [65.0],
        "metrics_without_them": {"tbr_pct": 0.0, "min_value": 70.1, "tir_pct": 99.85, "cv_pct": 11.15},
        "metrics_with_them": {"tbr_pct": 0.15, "min_value": 65.0, "tir_pct": 99.7, "cv_pct": 11.32},
    }
    rec["data_quality_flags"] = [flag]
    rec["data_quality_details"] = [{"flag": flag, "affects": list(affects), "window": "this window"}]
    return rec


def test_only_affected_metrics_are_cleaned_and_noted():
    a = annotate(_artifact_record())
    g = a["glucose"]
    assert g["tbr_pct"] == 0.0 and "tbr_pct__note" in g          # affected: cleaned value + note beside it
    assert g["tir_pct"] == 99.7 and "tir_pct__note" not in g      # NOT affected: raw value, no note
    assert g["cv_pct"] == 11.32 and "cv_pct__note" not in g
    assert "questionable_excluded" not in g                        # the twin is folded in, not shown beside it


def test_raw_flagged_values_live_only_in_the_questionable_readings_section():
    a = annotate(_artifact_record())
    section = a["questionable_readings"][0]
    assert section["questionable_values"] == [65.0] and section["values_if_included"] == {"tbr_pct": 0.15, "min_value": 65.0}
    assert 65.0 not in [v for k, v in a["glucose"].items() if not k.endswith("__note") and isinstance(v, float)]


def test_a_flagged_value_outside_caveats_is_rejected_but_allowed_in_caveats():
    rec = _artifact_record()
    bad = _good(key_observations=[Statement(statement="Metformin was missed. Her lowest glucose was 65.", evidence_refs=["glucose.lowest glucose mg/dL"])])
    assert _failures(bad, rec, "flagged_value_outside_caveats")
    ok = _good(data_quality_caveats=["known_clip_artifact_reading:65.0: one reading of 65.0 was a clipped value."])
    assert not _failures(ok, rec, "flagged_value_outside_caveats")


def test_questionable_language_on_an_unaffected_metric_is_rejected():
    rec = _artifact_record()
    bad = _good(key_observations=[Statement(statement="Metformin was missed. Time in range was 99.7%, which may reflect a questionable reading.",
                                           evidence_refs=["glucose.time in range percent"])])
    assert _failures(bad, rec, "caveat_on_unaffected_metric")
    ok = _good(key_observations=[Statement(statement="Metformin was missed. Time below range was 0%, excluding a questionable reading.",
                                          evidence_refs=["glucose.time below range percent"])])
    assert not _failures(ok, rec, "caveat_on_unaffected_metric")


def test_changes_that_cannot_be_cleaned_get_a_note_when_a_flag_affects_them():
    rec = _artifact_record("max_reading_above_400", ("cv_pct", "glucose_cv_pct"))
    rec["deltas"]["glucose_cv_pct"] = 6.35
    assert annotate(rec)["deltas"]["glucose_cv_pct__note"] == "may reflect a questionable reading"
    assert "glucose_tir_pct__note" not in annotate(rec)["deltas"]


# ---- grounding tolerance, directions, voice ----------------------------------------------------------------

def test_rounded_number_is_grounded_but_counted():
    before = GROUNDING["tolerance_only"]
    e = _good(key_observations=[Statement(statement="Metformin was missed. Her average glucose was about 145.", evidence_refs=["glucose.average glucose mg/dL"])])
    assert not _failures(e, kind="ungrounded_number")
    assert GROUNDING["tolerance_only"] == before + 1


def test_range_is_grounded_when_a_value_falls_inside():
    e = _good(key_observations=[Statement(statement="Metformin was missed. Steps ran 1600-2000.", evidence_refs=["activity.steps"])])
    assert not _failures(e, kind="ungrounded_number")


def test_number_with_no_near_match_is_rejected():
    e = _good(key_observations=[Statement(statement="Metformin was missed. Her average glucose was 55555.", evidence_refs=["glucose.average glucose mg/dL"])])
    assert _failures(e, kind="ungrounded_number")


def test_wrong_direction_is_rejected():
    e = _good(changes_vs_prior=[Statement(statement="Metformin was missed. Time in range rose 4.2 points.", evidence_refs=["changes vs previous window.change in time in range points"])])
    assert _failures(e, kind="wrong_direction")


def test_system_voice_and_machine_fragments_are_rejected():
    for text in ("The steps stream was flat in the record.", "Her glucose was up (direction: down).", "See the direction table.", "The time in range percent note says so."):
        e = _good(key_observations=[Statement(statement=f"Metformin was missed. {text}", evidence_refs=["activity.steps"])])
        assert _failures(e, kind="system_voice"), text


def test_status_echo_is_counted_not_rejected_and_reference_range_wording_is_clean():
    from v0_code.nodes.memory_llm import STATUS_ECHOES
    before = len(STATUS_ECHOES)
    echo = _good(key_observations=[Statement(statement="Metformin was missed. Her steps was low.", evidence_refs=["activity.steps"])])
    assert not _failures(echo)                      # soft: a paraphrase of the status is reported, not a rejection
    assert len(STATUS_ECHOES) == before + 1
    ok = _good(key_observations=[Statement(statement="Metformin was missed. Her steps were below the reference range.", evidence_refs=["activity.steps"])])
    _failures(ok)
    assert len(STATUS_ECHOES) == before + 1         # the reference-range wording is not an echo


def test_the_word_note_is_fine_in_prose_but_a_note_key_echo_is_not():
    diary = _good(key_observations=[Statement(statement="Metformin was missed. A diary note mentions exam stress.", evidence_refs=[])])
    assert not _failures(diary, kind="system_voice")


def test_flag_names_in_statements_are_rewritten_to_plain_phrases_and_logged():
    from v0_code.nodes.memory_llm import SANITIZED
    before = len(SANITIZED)
    out = sanitize_text("Step completeness was flagged (low_completeness:steps:0.0).", {}, RECORD, "t")
    assert out == "Step completeness was flagged (incomplete data)." and len(SANITIZED) == before + 1
    assert sanitize_text("low_completeness:step_count:0.0", {}, RECORD, "t", flags=False) == "low_completeness:step_count:0.0"


def test_flag_names_outside_caveats_are_rejected_inside_caveats_allowed():
    bad = _good(key_observations=[Statement(statement="Metformin was missed. See known_clip_artifact_reading.", evidence_refs=[])])
    assert _failures(bad, kind="flag_name_outside_caveats")
    ok = _good(data_quality_caveats=["known_clip_artifact_reading:65.0"])
    assert not _failures(ok, kind="flag_name_outside_caveats")


def test_a_ref_that_drops_its_leading_section_resolves_only_when_unique():
    rec = {**RECORD, "aggregates": {"meal_events": {"post_meal_peak_mean": 170.2}}, "sleep": {"duration_hours": 6.4}}
    r = _resolver(rec)
    assert r.resolve("post-meal glucose peak.average peak glucose after meals mg/dL") == 170.2   # unique suffix
    assert r.resolve("weekly totals.post-meal glucose peak.average peak glucose after meals mg/dL") == 170.2
    assert r.resolve("nothing.at.all") is _MISSING


def test_the_model_never_sees_the_word_anchor_for_crossings():
    rec = {**RECORD, "anchors_crossed": ["sleep_hours_change"], "anchors_questionable": []}
    plain, _, _ = to_plain(annotate(rec))
    assert plain["large changes found"] == ["sleep changed by more than the usual amount"]
    assert "anchors_crossed" not in plain and "anchors_questionable" not in plain


# ---- caps and quiet ------------------------------------------------------------------------------------------

def test_quiet_means_no_material_changes_and_uses_the_short_caps():
    quiet = {**RECORD, "quiet": True}
    assert caps_for(quiet) == {"trajectory": 0, "changes_vs_prior": 0, "co_movement": 2, "recurring_patterns": 0, "key_observations": 2}
    assert caps_for(RECORD)["key_observations"] == 5
    e = _entry(key_observations=[Statement(statement="Quiet.", evidence_refs=[])] * 3)
    assert any(f.startswith("too_many_items:key_observations") for f in _validate(e, quiet))


def test_quiet_day_co_movement_is_capped_at_two_domains():
    quiet = {**RECORD, "quiet": True, "adherence": {"per_medication": {}}}
    two = _entry(co_movement=GOOD_COMOVE[:2])
    assert not [f for f in _validate(two, quiet) if f.startswith("co_movement")]
    assert any(f.startswith("co_movement_streams_not_in_candidates") for f in _validate(_entry(co_movement=GOOD_COMOVE), quiet))


def test_unremarkable_streams_excludes_what_the_entry_mentions():
    rec = {**RECORD, "stream_direction_table": {"glucose": "up", "sleep": "flat", "steps": "down"}}
    e = _entry(key_observations=[Statement(statement="Her sleep held steady.", evidence_refs=["sleep.sleep hours"])])
    assert code_unremarkable(rec, e) == []
    assert code_unremarkable(rec, _entry()) == ["sleep"]


# ---- co-movement -----------------------------------------------------------------------------------------------

def test_co_movement_with_direction_and_amount_passes():
    assert not [f for f in _validate(_good()) if f.startswith("co_movement")]


def test_co_movement_must_name_direction_and_amount_one_measure_per_item():
    no_dir = CoMovement(statement="Her steps changed by 802.8 steps.", streams=["steps"], evidence_refs=[])
    no_amount = CoMovement(statement="Her steps fell, the opposite way to glucose.", streams=["steps"], evidence_refs=[])
    two = CoMovement(statement="Her steps and sleep moved.", streams=["steps", "sleep"], evidence_refs=[])
    rest = GOOD_COMOVE[1:]
    assert any(f.startswith("co_movement_direction_missing") for f in _validate(_good(co_movement=[no_dir, *rest])))
    assert any(f.startswith("co_movement_magnitude_missing") for f in _validate(_good(co_movement=[no_amount, *rest])))
    assert any(f.startswith("co_movement_one_measure_per_item") for f in _validate(_good(co_movement=[two, *rest])))


def test_co_movement_requires_every_chosen_measure_and_nothing_else():
    assert any(f.startswith("co_movement_missing_candidates") for f in _validate(_good(co_movement=GOOD_COMOVE[:2])))
    extra = CoMovement(statement="Her mood fell 1 blocks.", streams=["mood"], evidence_refs=[])
    assert any(f.startswith("co_movement_streams_not_in_candidates") for f in _validate(_good(co_movement=[*GOOD_COMOVE, extra])))


def test_co_movement_is_omitted_when_glucose_did_not_move_past_its_flat_band():
    flat = {**RECORD, "co_movement_candidates": {**RECORD["co_movement_candidates"], "glucose_direction": "flat", "ranked": []}}
    assert not [f for f in _validate(_entry(key_observations=[Statement(statement="Metformin was missed.", evidence_refs=[])]), flat) if f.startswith("co_movement")]
    assert any(f.startswith("co_movement_streams_not_in_candidates") for f in _validate(_good(), flat))


# ---- material changes ----------------------------------------------------------------------------------------------

def test_a_missed_dose_must_be_named():
    rec = {**RECORD, "material_changes": [{"kind": "missed_dose", "medicine": "med_002_metformin"}]}
    silent = _entry(co_movement=GOOD_COMOVE, key_observations=[Statement(statement="Her glucose was steady.", evidence_refs=[])])
    named = _entry(co_movement=GOOD_COMOVE, key_observations=[Statement(statement="She missed her metformin.", evidence_refs=[])])
    assert any(f.startswith("material_change_omitted") and "metformin" in f for f in _validate(silent, rec))
    assert not [f for f in _validate(named, rec) if f.startswith("material_change_omitted")]


def test_a_caveat_citing_both_affected_and_unaffected_metrics_is_only_a_warning():
    from v0_code.nodes.memory_llm import WARNINGS
    rec = _artifact_record()
    before = len(WARNINGS)
    mixed = _good(key_observations=[Statement(statement="Metformin was missed. Time in range was 99.7% and time below range 0%; the latter excludes a questionable reading.",
                                             evidence_refs=["glucose.time in range percent", "glucose.time below range percent"])])
    assert not _failures(mixed, rec, "caveat_on_unaffected_metric")
    assert any("caveat_on_unaffected_metric" in w for w in WARNINGS[before:])


def test_refs_into_the_things_that_deviated_checklist_are_dropped_not_failed():
    from v0_code.nodes.memory_llm import IGNORED_REFS
    before = len(IGNORED_REFS)
    e = _good(key_observations=[Statement(statement="Metformin was missed.", evidence_refs=["things that deviated[1].measures[7].number of days"])])
    assert not _failures(e, kind="evidence_ref_not_found")
    assert len(IGNORED_REFS) == before + 1


def test_numbers_inside_month_labelled_values_are_not_mistaken_for_dates():
    from v0_code.nodes.memory_llm import _strip_non_metric_numbers
    import re
    stripped = _strip_non_metric_numbers("Jan 98.51% and Feb 98.25%, Dec 18 2025, Dec 18, 2025")
    nums = re.findall(r"(?<!\d)-?\d+\.?\d*", stripped)
    assert nums == ["98.51", "98.25"]


def test_band_edges_shown_in_labels_are_grounded():
    e = _good(data_quality_caveats=["Time above 250 percent would be 0.01 with the reading."])
    assert not _failures(e, kind="ungrounded_number")


def test_the_verb_records_is_fine_but_the_noun_record_is_system_voice():
    ok = _good(key_observations=[Statement(statement="Metformin was missed. On 2026-01-18 the diary records the skin reaction was better.", evidence_refs=[])])
    bad = _good(key_observations=[Statement(statement="Metformin was missed. The record shows steady glucose.", evidence_refs=[])])
    assert not _failures(ok, kind="system_voice") and _failures(bad, kind="system_voice")


def test_annotate_replaces_an_artifact_driven_change_with_the_cleaned_one():
    rec = _artifact_record("max_reading_above_400", ("cv_pct", "glucose_cv_pct"))
    rec["deltas"] = {"glucose_cv_pct": 6.35, "sleep_hours": 0.5,
                     "questionable_excluded": {"n_excluded": 1, "excluded_values": [599.0],
                                               "metrics_without_them": {"glucose_cv_pct": 0.12}, "metrics_with_them": {"glucose_cv_pct": 6.35}}}
    a = annotate(rec)
    assert a["deltas"]["glucose_cv_pct"] == 0.12 and "glucose_cv_pct__note" in a["deltas"] and a["deltas"]["sleep_hours"] == 0.5
    assert a["questionable_readings"][-1]["values_if_included"] == {"glucose_cv_pct": 6.35}
    leaked = _good(changes_vs_prior=[Statement(statement="Metformin was missed. Variability rose 6.35 points.", evidence_refs=["changes vs previous window.change in variability points"])])
    assert _failures(leaked, rec, "flagged_value_outside_caveats")
