"""Baseline Engine v2 invariants, run over EVERY day window of the real patient (spec section 10), plus the golden days."""

import json
import sqlite3
import shutil

import pytest

from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.data import StoreView
from v0_code.baseline_v2.engine import build_days
from v0_code.baseline_v2.trust import clean_series


def test_there_is_one_window_per_calendar_day_and_every_row_carries_the_config_version(v2_rows, v2_cfg):
    assert len(v2_rows) == 352
    assert all(r["config_version"] == v2_cfg.version and r["tier"] == "day" for r in v2_rows.values())


def test_a_window_never_has_an_empty_memory(v2_rows):
    for r in v2_rows.values():
        assert r["deviation_text"].strip() and r["facts"]["daily_values"] and r["tags"]
        assert r["gist_status"] in (None, "code_line_early", "code_line_quiet")


def test_every_missed_dose_appears_in_material_changes_and_in_the_deviation_text(v2_rows, v2_cfg):
    n = 0
    for r in v2_rows.values():
        missed = [m for m, s in r["facts"]["adherence"]["per_medication"].items() if s != "taken"]
        in_material = {i["medicine"] for i in r["material_changes"] if i["kind"] == "missed_dose"}
        assert set(missed) == in_material, r["window_id"]
        for m in missed:
            n += 1
            assert f"Missed dose: {v2_cfg.medicine_name(m)}" in r["deviation_text"], (r["window_id"], m)
    assert n > 150                                      # the loop was not vacuous: she misses many doses


def test_every_diary_event_appears_in_the_deviation_text_verbatim_and_dated(v2_rows):
    n = 0
    for r in v2_rows.values():
        for e in r["facts"]["diary_events"]:
            n += 1
            assert e["text"] in r["deviation_text"] and f"Diary, {r['facts']['date']}" in r["deviation_text"], (r["window_id"], e["text"])
            assert any(i["kind"] == "diary_event" and i["text"] == e["text"] and i["date"] == r["facts"]["date"] for i in r["material_changes"])
    assert n == 129


def test_is_notable_is_exactly_whether_an_anchor_crossed_and_false_when_none_did(v2_rows):
    for r in v2_rows.values():
        assert r["is_notable"] == bool(r["anchors_crossed"])
        if not r["anchors_crossed"]:
            assert r["is_notable"] is False and r["notable_reason"] is None
        else:
            assert r["notable_reason"] and r["notable_reason"].endswith(".")


def test_quiet_is_exactly_an_empty_material_list(v2_rows):
    for r in v2_rows.values():
        assert r["quiet"] == (not r["material_changes"])
        if r["quiet"] and r["gist_status"]:
            assert r["gist_status"] in ("code_line_quiet", "code_line_early")


def test_the_first_14_days_have_no_flat_band_or_direction_tag_and_get_the_early_code_line(v2_rows):
    days = sorted(v2_rows)
    for wid in days[:14]:
        r = v2_rows[wid]
        assert r["gist_status"] == "code_line_early" and r["gist_headline"].startswith("Not enough history yet to compare.")
        assert all(t["direction"] == "not_enough_data" for t in r["tags"]), wid
    assert v2_rows[days[14]]["gist_status"] != "code_line_early"
    assert any(t["direction"] != "not_enough_data" for t in v2_rows[days[14]]["tags"])


def test_reliability_is_false_for_the_first_13_days_and_true_after(v2_rows):
    days = sorted(v2_rows)
    assert not any(v2_rows[w]["reliable"] for w in days[:13]) and v2_rows[days[13]]["reliable"]


def test_a_removed_reading_never_moves_any_metric_delta_anchor_or_tag(v2_rows, v2_cfg, pipeline_run, tmp_path):
    """Delete the removed readings from the store entirely and rebuild: every computed value must be identical. If a questionable reading
    leaked into a metric, a delta, an anchor or a tag, the two builds would differ."""
    _, db = pipeline_run
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    _, removed = clean_series(StoreView(ro, v2_cfg).glucose_series, v2_cfg)
    ro.close()
    assert len(removed) >= 3
    copy = tmp_path / "without_removed.db"
    shutil.copy(db, copy)
    c = sqlite3.connect(copy)
    for rm in removed:
        c.execute("DELETE FROM raw_events WHERE biomarker = 'cgm_glucose_reading' AND timestamp = ? AND value = ?", (rm.ts, rm.value))
    c.commit()
    c.close()
    ro = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    rebuilt = {r["window_id"]: r for r in build_days(v2_cfg, StoreView(ro, v2_cfg))}
    ro.close()
    for wid, r in v2_rows.items():
        b = rebuilt[wid]
        for key in ("tags", "co_movement", "anchors_crossed", "is_notable", "notable_reason", "reliable", "confidence", "deltas_clean"):
            assert r[key] == b[key], (wid, key)
        assert r["facts"]["glucose"] == b["facts"]["glucose"] and r["facts"]["daily_values"] == b["facts"]["daily_values"] and r["facts"]["profile_asof"] == b["facts"]["profile_asof"]
        assert r["facts"]["post_meal"] == b["facts"]["post_meal"]


def test_no_window_depends_on_data_after_its_end_date(v2_rows, v2_cfg, pipeline_run, tmp_path):
    """Rebuild from a store truncated at a cutoff date: every window ending on or before it must be identical to the full build."""
    _, db = pipeline_run
    cutoff = "2026-03-15"
    copy = tmp_path / "truncated.db"
    shutil.copy(db, copy)
    c = sqlite3.connect(copy)
    c.execute("DELETE FROM raw_events WHERE substr(timestamp, 1, 10) > ?", (cutoff,))
    c.execute("DELETE FROM context_events WHERE date > ?", (cutoff,))
    c.commit()
    c.close()
    ro = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    short = {r["window_id"]: r for r in build_days(v2_cfg, StoreView(ro, v2_cfg))}
    ro.close()
    assert max(r["end_date"] for r in short.values()) == cutoff and len(short) > 150
    for wid, r in short.items():
        assert json.dumps(r, sort_keys=True, default=str) == json.dumps(v2_rows[wid], sort_keys=True, default=str), wid


def test_an_unusual_status_is_only_ever_worse_than_the_streams_usual(v2_rows):
    from v0_code.baseline_v2.profile import STATUS_RANK
    for r in v2_rows.values():
        for i in r["material_changes"]:
            if i["kind"] == "status_worse_than_usual":
                assert STATUS_RANK[i["status"]] > STATUS_RANK[i["usual"]]
                assert r["facts"]["profile_asof"][i["measure"]]["usual_status"] == i["usual"]


# ---- golden days -----------------------------------------------------------------------------------------------------------------

def test_golden_2025_12_26_lists_the_missed_metformin_dose(v2_rows):
    r = v2_rows["day_2025-12-26"]
    assert {"kind": "missed_dose", "medicine": "med_002_metformin", "days": 1} in r["material_changes"] and "Missed dose: metformin" in r["deviation_text"]


def test_golden_2026_04_23_lists_the_removed_590_reading_and_is_not_notable_from_it(v2_rows):
    r = v2_rows["day_2026-04-23"]
    assert [x["value"] for x in r["data_quality"]["questionable_readings"]] == [590.0]
    assert any(i["kind"] == "questionable_reading_removed" and i["value"] == 590.0 for i in r["material_changes"]) and "Reading removed: 590" in r["deviation_text"]
    assert r["facts"]["glucose"]["max_value"] < 400 and r["facts"]["glucose"]["cv_pct"] < 15       # the 590 is in no metric
    assert not r["is_notable"] and r["anchors_crossed"] == [] and "glucose_CV_change_points" in r["anchors_questionable"] and "severe_range_appeared_or_cleared" in r["anchors_questionable"]
    assert "variability 41.63" in r["deviation_text"]                                              # ...only in the caveat, with the metrics as they would have been


def test_golden_2025_12_09_599_is_removed_and_not_counted(v2_rows):
    r = v2_rows["day_2025-12-09"]
    assert [x["value"] for x in r["data_quality"]["questionable_readings"]] == [599.0] and not r["is_notable"]
