"""memory_v2 storage and retrieval, the no-wipe rule, and the report helpers."""

import json
import shutil
import sqlite3

import pytest

from v0_code.baseline_v2.render import phrase
from v0_code.baseline_v2.report import known_upstream_issues
from v0_code.baseline_v2.run import run_stage_a
from v0_code.baseline_v2.storage import MemoryV2Store

V1_TABLES = ("raw_events", "numeric_summary", "context_events", "memory_records")


def _counts(db):
    c = sqlite3.connect(db)
    out = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in V1_TABLES}
    c.close()
    return out


@pytest.fixture()
def db(pipeline_run, tmp_path):
    _, src = pipeline_run
    dst = tmp_path / "store.db"
    shutil.copy(src, dst)
    return str(dst)


def test_a_run_writes_memory_v2_and_never_touches_the_v1_tables(db, v2_cfg):
    before = _counts(db)
    c = sqlite3.connect(db)
    snap = c.execute("SELECT group_concat(window_id || coalesce(record_json,'')) FROM memory_records").fetchone()[0]
    c.close()
    run_stage_a(v2_cfg, db)
    assert _counts(db) == before
    c = sqlite3.connect(db)
    assert c.execute("SELECT group_concat(window_id || coalesce(record_json,'')) FROM memory_records").fetchone()[0] == snap
    assert c.execute("SELECT COUNT(*) FROM memory_v2").fetchone()[0] == 352
    c.close()


def test_the_default_run_is_idempotent_and_never_wipes(db, v2_cfg):
    run_stage_a(v2_cfg, db)
    c = sqlite3.connect(db)
    c.execute("INSERT INTO memory_v2 (window_id, tier, end_date, config_version) VALUES ('week_ENDING_2026-01-01', 'week', '2026-01-01', 'x')")
    c.commit()
    c.close()
    run_stage_a(v2_cfg, db)
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM memory_v2").fetchone()[0] == 353          # rerun: no duplicates, and the other tier's row survives
    c.close()


def test_a_gist_written_by_the_llm_survives_a_rerun_of_the_facts(db, v2_cfg):
    run_stage_a(v2_cfg, db)
    c = sqlite3.connect(db)
    c.execute("UPDATE memory_v2 SET gist_headline = 'LLM headline', gist_sentences = '[\"one\", \"two\"]', gist_status = 'gist_ok', llm_raw = '{}' WHERE window_id = 'day_2025-12-26'")
    c.commit()
    c.close()
    run_stage_a(v2_cfg, db)
    s = MemoryV2Store(db, readonly=True)
    g = s.get_memory("day", "2025-12-26")["gist"]
    assert g == {"headline": "LLM headline", "sentences": ["one", "two"], "status": "gist_ok"}


def test_rebuild_needs_the_flag_and_drops_only_memory_v2(db, v2_cfg):
    run_stage_a(v2_cfg, db)
    c = sqlite3.connect(db)
    c.execute("INSERT INTO memory_v2 (window_id, tier, end_date, config_version) VALUES ('extra', 'week', '2026-01-01', 'x')")
    c.commit()
    c.close()
    before = _counts(db)
    run_stage_a(v2_cfg, db, rebuild=True)
    c = sqlite3.connect(db)
    assert c.execute("SELECT COUNT(*) FROM memory_v2").fetchone()[0] == 352 and c.execute("SELECT COUNT(*) FROM memory_v2 WHERE window_id = 'extra'").fetchone()[0] == 0
    c.close()
    assert _counts(db) == before


@pytest.fixture()
def store(db, v2_cfg):
    run_stage_a(v2_cfg, db)
    s = MemoryV2Store(db, readonly=True)
    yield s
    s.close()


def test_get_memory_returns_a_parsed_object_without_the_facts_blob(store):
    m = store.get_memory("day", "2025-12-26")
    assert isinstance(m, dict) and isinstance(m["tags"], list) and isinstance(m["material_changes"], list) and isinstance(m["anchors_crossed"], list)
    assert "facts" not in m and m["window_id"] == "day_2025-12-26" and m["quiet"] is False and m["is_notable"] is False
    assert m["gist"]["status"] is None and m["config_version"].startswith("meera_iyer_v1-")
    assert store.get_memory("day", "1999-01-01") is None


def test_full_adds_the_facts(store):
    f = store.get_memory("day", "2025-12-26", full=True)["facts"]
    assert f["date"] == "2025-12-26" and f["adherence"]["per_medication"]["med_002_metformin"] == "missed"


def test_get_memories_between_is_inclusive_ordered_and_tiered(store):
    ms = store.get_memories_between("2025-12-24", "2025-12-27", "day")
    assert [m["end_date"] for m in ms] == ["2025-12-24", "2025-12-25", "2025-12-26", "2025-12-27"]
    assert store.get_memories_between("2025-12-24", "2025-12-27", "week") == []


def test_get_notable_returns_only_notable_windows_since_the_date(store):
    ms = store.get_notable("day", "2026-01-01")
    assert ms and all(m["is_notable"] and m["end_date"] >= "2026-01-01" and m["anchors_crossed"] for m in ms)
    assert ms == sorted(ms, key=lambda m: m["end_date"])


def test_get_profile_asof_uses_only_history_before_the_date(store, v2_rows):
    p = store.get_profile_asof("sleep_duration", "2025-12-26")
    earlier = [r["facts"]["daily_values"]["sleep_duration"] for w, r in v2_rows.items() if w < "day_2025-12-26" and r["facts"]["daily_values"]["sleep_duration"] is not None]
    assert p["n_days"] == len(earlier) and p["flat_band"] is not None
    assert store.get_profile_asof("sleep_duration", "2025-10-05")["flat_band"] is None            # before 14 days: no band yet
    assert store.get_profile_asof("sleep_duration", "1999-01-01") is None


def test_a_count_of_periods_is_worded_more_or_fewer(v2_rows):
    assert phrase(-1.0, "", True) == "1 fewer" and phrase(2.0, "", True) == "2 more"
    assert "Strained periods of the day: 1 fewer" in v2_rows["day_2025-11-22"]["deviation_text"]


def test_the_upstream_issue_report_says_which_65_readings_the_rules_removed_and_which_remain(pipeline_run, v2_cfg):
    _, db = pipeline_run
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    up = known_upstream_issues(v2_cfg, c)
    c.close()
    assert len(up["isolated_65_readings"]) == 5
    assert [t[:10] for t, _ in up["removed_by_rules"]] == ["2026-05-20"] and len(up["still_in_the_data"]) == 4
    assert [l["date"] for l in up["labs_vs_gmi"]][0] == "2025-09-15" and up["labs_vs_gmi"][0]["gmi_90d_prior"] is None
