"""Code-rendered facts. The guarantee (by construction): whatever the code found worth reporting — missed doses, diary
events, statuses unusual for the stream, data gaps, removed questionable readings — appears in the rendered
material-changes section. Each invariant is checked on the real pipeline output (all 352 days / 346 weeks) and on
synthetic records, so a regression cannot hide in either."""

import pytest

from v0_code.logic.memory_records import MATERIAL_KINDS
from v0_code.logic.record_view import plain_value
from v0_code.logic.render import STATUS_WORDS, measure_name, move, phrase, render_material, render_window
from v0_code.nodes.memory_writer import is_notable_by_code


def material_text(rec: dict) -> str:
    return "\n".join(render_material(rec))


def days(recs):
    return [r for r in recs.values() if r["tier"] == "day"]


def weeks(recs):
    return [r for r in recs.values() if r["tier"] == "week"]


# ---- wording ------------------------------------------------------------------------------------------------------------

def test_change_wording_is_direction_amount_unit():
    assert phrase(-1.82, "hours") == "down 1.82 hours" and phrase(10.74, "bpm") == "up 10.74 bpm" and phrase(0, "bpm") == "no change"
    assert move("sleep", -1.82, "hours") == "Sleep: down 1.82 hours"


def test_mood_is_worded_as_fewer_or_more_strained_periods_never_up_or_down():
    assert move("mood", -3.0, "strained periods of the day", count_like=True) == "Mood: 3 fewer strained periods of the day"
    assert move("mood", 2.0, "strained periods of the day", count_like=True) == "Mood: 2 more strained periods of the day"


def test_only_strain_categories_count_toward_mood():
    from v0_code.logic import stream_tables as st
    from v0_code.logic.registry import get
    s = get("mood_state")
    uplifted = {"mood": {"morning": {"category": "positive_uplifted"}, "afternoon": {"category": "calm_stable"}, "evening": {"category": "calm_stable"}}}
    strained = {"mood": {"morning": {"category": "tired_low_energy"}, "afternoon": {"category": "anxious"}, "evening": {"category": "calm_stable"}}}
    assert st.day_value(s, uplifted) == 0.0       # uplifted does not count
    assert st.day_value(s, strained) == 2.0


# ---- every material kind has a renderer, and renders its identifying facts ----------------------------------------------

SYNTHETIC = {
    "anchor_crossed": ({"kind": "anchor_crossed", "detail": "sleep_hours_change"}, "sleep"),
    "missed_dose": ({"kind": "missed_dose", "medicine": "med_002_metformin"}, "metformin"),
    "missed_doses": ({"kind": "missed_doses", "medicine": "med_003_amlodipine", "missed": 2, "of": 7}, "amlodipine"),
    "unusual_status": ({"kind": "unusual_status", "measure": "hydration", "status": "borderline_low"}, STATUS_WORDS["borderline_low"]),
    "diary_events": ({"kind": "diary_events", "count": 1}, "Diary"),
    "data_quality": ({"kind": "data_quality", "flag": "gap_hours:2.2"}, "2.2"),
    "questionable_reading": ({"kind": "questionable_reading", "time": "2025-12-07T10:30:00+05:30", "value": 599.0}, "599"),
    "lab_result": ({"kind": "lab_result", "lab_date": "2025-12-18", "hba1c_pct": 7.6, "gap_hba1c_minus_gmi": 1.11}, "7.6"),
}


def test_every_material_kind_has_a_renderer_test():
    assert set(SYNTHETIC) == set(MATERIAL_KINDS)


@pytest.mark.parametrize("kind", sorted(SYNTHETIC))
def test_each_material_kind_renders_its_facts(kind):
    item, must_contain = SYNTHETIC[kind]
    rec = {"tier": "day", "material_changes": [item], "deltas": {"sleep_hours": -1.7}, "date": "2025-12-26",
           "diary_events": [{"category": "life_event", "text": "Visited parents", "severity_note": None}]}
    text = material_text(rec)
    assert text and must_contain.lower() in text.lower(), (kind, text)


# ---- invariants on the real data -----------------------------------------------------------------------------------------

def test_quiet_means_material_changes_is_empty(pipeline_records):
    for r in list(days(pipeline_records)) + list(weeks(pipeline_records)):
        assert r["quiet"] == (not r["material_changes"]), r["window_id"]
        assert {m["kind"] for m in r["material_changes"]} <= set(MATERIAL_KINDS)


def test_every_missed_dose_appears_in_the_rendered_section(pipeline_records):
    n = 0
    for r in days(pipeline_records):
        text = material_text(r).lower()
        for med, status in r["adherence"]["per_medication"].items():
            if status != "taken":
                n += 1
                assert measure_name(med).lower() in text and "missed" in text, (r["window_id"], med)
    for r in weeks(pipeline_records):
        text = material_text(r).lower()
        for med, v in r["aggregates"]["medication_adherence"]["per_medication"].items():
            if v["taken"] < v["expected"]:
                n += 1
                assert measure_name(med).lower() in text, (r["window_id"], med)
    assert n > 100  # the data really does contain many missed doses; the loop was not vacuous


def test_every_diary_event_appears_verbatim_with_its_date(pipeline_records):
    n = 0
    for r in days(pipeline_records):
        text = material_text(r)
        for e in r["diary_events"]:
            n += 1
            assert e["text"] in text and r["date"] in text, (r["window_id"], e["text"])
    for r in weeks(pipeline_records):
        text = material_text(r)
        for e in r["events_in_window"]:
            n += 1
            assert e["text"] in text and e["date"] in text, (r["window_id"], e["text"])
    assert n >= 129


def test_every_unusual_status_appears_and_a_usual_one_does_not(pipeline_records):
    for r in days(pipeline_records):
        text = material_text(r).lower()
        for u in r["unusual_statuses"]:
            assert measure_name(u["measure"]).lower() in text and STATUS_WORDS[u["status"]] in text, (r["window_id"], u)
    # steps are "low" on ~95% of her days: that is her usual, so it must almost never be reported as a deviation
    low_steps = sum(1 for r in days(pipeline_records) if any(u["measure"] == "step_count" for u in r["unusual_statuses"]))
    assert low_steps < 0.1 * len(days(pipeline_records))


def test_every_data_gap_and_low_completeness_flag_appears(pipeline_records):
    n = 0
    for r in list(days(pipeline_records)) + list(weeks(pipeline_records)):
        text = material_text(r).lower()
        for f in r["data_quality_flags"]:
            if f.startswith("gap_hours"):
                n += 1
                assert f.split(":")[1] in text and "gap" in text, (r["window_id"], f)
            if f.startswith("low_completeness"):
                n += 1
                assert "incomplete" in text, (r["window_id"], f)
    assert n > 10


def test_every_removed_questionable_reading_appears(pipeline_records):
    n = 0
    for r in list(days(pipeline_records)) + list(weeks(pipeline_records)):
        q = r["glucose"].get("questionable_excluded")
        if q:
            text = material_text(r)
            for rd in q["excluded_readings"]:
                n += 1
                assert f"{rd['value']:g}" in text and rd["time"][:10] in text, (r["window_id"], rd)
    assert n >= 5


def test_every_anchor_crossing_is_rendered_with_its_numbers(pipeline_records):
    for r in list(days(pipeline_records)) + list(weeks(pipeline_records)):
        lines = [x for x in render_material(r) if x.startswith("Large change")]
        assert len(lines) == len(r["anchors_crossed"]), r["window_id"]


# ---- golden windows ---------------------------------------------------------------------------------------------------------

def test_golden_crisis_week_shows_sleep_down_adherence_down_resting_hr_up_glucose_up(pipeline_records):
    r = pipeline_records["week_ENDING_2025-11-22"]
    rendered = render_window(r)
    changed = "\n".join(rendered["what_changed"])
    assert "Sleep: down" in changed
    assert "Medication adherence: down" in changed
    assert "Resting heart rate: up" in changed
    assert "Average glucose: up" in changed
    material = "\n".join(rendered["material_changes"])
    assert "sleep down" in material and "medication adherence down" in material and "heart rate at rest up" in material
    assert is_notable_by_code(r)


def test_golden_artifact_week_is_not_notable(pipeline_records):
    r = pipeline_records["week_ENDING_2025-12-09"]
    assert r["anchors_crossed"] == []                              # the 599 reading is removed before the alarm is checked
    assert "severe_range_appeared_or_cleared" in r["anchors_suppressed"]   # ...and the raw crossing is recorded as suppressed
    assert not is_notable_by_code(r)
    assert any("599" in x and "removed" in x.lower() for x in render_window(r)["material_changes"])


def test_clipped_reading_week_puts_no_questionable_note_on_unaffected_metrics(pipeline_records):
    rendered = "\n".join(sum(render_window(pipeline_records["week_ENDING_2026-01-23"]).values(), []))
    assert "65" in rendered and "removed" in rendered.lower()


# ---- nothing in a window's entry depends on data after its end date ---------------------------------------------------------------

def test_no_window_depends_on_data_after_its_end_date(pipeline_run, tmp_path):
    """Rebuild every record from the store truncated at a cutoff date; every window that ends on or before the cutoff must be
    identical (record, hence every rendered fact) to the one built from the full year. A "usual status" computed over the whole
    dataset, a baseline that peeks at later days, or an anchor that reads a later reading would all fail here."""
    import json
    from v0_code.data.store import PersonalDataStore
    from v0_code.logic.memory_records import build_all_records

    state, db = pipeline_run
    cutoff = "2026-03-15"
    with PersonalDataStore(tmp_path / "truncated.db") as trunc:
        trunc.conn.execute("ATTACH DATABASE ? AS src", (str(db),))
        trunc.conn.execute("INSERT INTO raw_events SELECT * FROM src.raw_events WHERE substr(timestamp, 1, 10) <= ?", (cutoff,))
        trunc.conn.execute("INSERT INTO context_events SELECT * FROM src.context_events WHERE date <= ?", (cutoff,))
        trunc.conn.commit()
        short = build_all_records(trunc, state.steps_by_hour)
    with PersonalDataStore(db) as full_store:
        full = build_all_records(full_store, state.steps_by_hour)

    def norm(x):
        return json.loads(json.dumps(x))

    compared = 0
    for tier, key in (("day", None), ("week", None)):
        for date, rec in short[tier].items():
            assert date <= cutoff
            assert norm(rec["record"]) == norm(full[tier][date]["record"]), (tier, date)
            compared += 1
    full_months = {m["record"]["window_id"]: m for m in full["month"]}
    for m in short["month"]:
        wid = m["record"]["window_id"]
        if wid in full_months and m["end_date"] <= cutoff:
            assert norm(m["record"]) == norm(full_months[wid]["record"]), wid
            compared += 1
    assert compared > 150
