"""A second, tiny patient must run through the engine with CONFIG CHANGES ONLY (spec section 10): 2 medications, no mood stream, no heart
rate, UTC+0 timestamps, pronoun "he", a different device range and step floor. No engine edit was needed to make this pass."""

import dataclasses
import sqlite3

from v0_code.baseline_v2.data import StoreView
from v0_code.baseline_v2.engine import build_days
from v0_code.baseline_v2.render import code_line


def test_the_engine_runs_on_the_fixture_patient_with_config_alone(v2_fixture):
    cfg, rows, _ = v2_fixture
    assert len(rows) == 40 and cfg.timezone == "UTC" and cfg.pronoun == "he"
    assert sorted(rows)[0] == "day_2026-01-01" and sorted(rows)[-1] == "day_2026-02-09"


def test_streams_the_fixture_patient_does_not_have_simply_do_not_appear(v2_fixture):
    _, rows, _ = v2_fixture
    measures = {t["measure"] for t in rows["day_2026-01-20"]["tags"]}
    assert "mood_state" not in measures and "continuous_heart_rate" not in measures and "resting_heart_rate" not in measures
    assert {"cgm_glucose_reading", "sleep_duration", "step_count", "medication_adherence"} <= measures
    assert rows["day_2026-01-20"]["facts"]["mood"]["strained_count"] is None


def test_the_first_14_days_are_early_and_pronoun_comes_from_config(v2_fixture):
    cfg, rows, _ = v2_fixture
    assert [rows[f"day_2026-01-{d:02d}"]["gist_status"] for d in (1, 14)] == ["code_line_early", "code_line_early"]
    assert rows["day_2026-01-15"]["gist_status"] != "code_line_early"
    assert code_line(cfg, "code_line_quiet") == "Nothing deviated from his usual."


def test_the_device_range_and_medicine_names_come_from_the_patients_config(v2_fixture):
    cfg, rows, db = v2_fixture
    day = rows["day_2026-01-29"]                                   # carries a 360 mg/dL reading
    assert [x["value"] for x in day["data_quality"]["questionable_readings"]] == [360.0]       # outside THIS patient's 40-350 range
    assert day["facts"]["glucose"]["max_value"] < 350 and "Reading removed: 360" in day["deviation_text"]
    assert "outside the device range (40-350)" in day["data_quality"]["questionable_readings"][0]["reason"]
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    # the same data under a wider range AND a looser jump limit (the jump rule would still remove a 105 -> 360 jump): nothing is removed
    wide = build_days(dataclasses.replace(cfg, device_range=(40.0, 400.0), max_step_change_per_15min=500.0), StoreView(ro, cfg))
    ro.close()
    assert next(r for r in wide if r["window_id"] == "day_2026-01-29")["data_quality"]["questionable_readings"] == []
    missed = rows["day_2026-02-01"]
    assert {"kind": "missed_dose", "medicine": "rx_02_statin", "days": 1} in missed["material_changes"] and "Missed dose: statin." in missed["deviation_text"]


def test_the_step_floor_in_config_decides_the_steps_anchor(v2_fixture):
    _, rows, _ = v2_fixture
    jump = rows["day_2026-01-31"]                                  # 5100 -> 8000 steps: over THIS patient's 1000 floor (Meera's is 3000)
    assert "steps_abs_change" in jump["anchors_crossed"] and jump["is_notable"] and "steps" in jump["notable_reason"]
    assert "steps_abs_change" in rows["day_2026-02-01"]["anchors_crossed"]       # and back down
    assert "adherence_meds_changed" not in rows["day_2026-02-01"]["anchors_crossed"]   # one of two medicines changed: below min(2, n_meds=2)


def test_the_diary_entry_appears_dated_and_verbatim(v2_fixture):
    _, rows, _ = v2_fixture
    r = rows["day_2026-02-03"]
    assert 'Diary, 2026-02-03 [life event]: "Team offsite dinner" (mild)' in r["deviation_text"]


def test_utc_dates_are_used_for_windowing(v2_fixture):
    _, rows, _ = v2_fixture
    assert rows["day_2026-01-10"]["facts"]["glucose"]["n_readings"] == 96            # all 96 readings of the UTC day, none leaking into a neighbour
