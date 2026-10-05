"""PI: the independent as-of audit, on a clean run and on planted violations."""

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from test_pi_driver import build
from v0_code.pi_engine.audit import audit_pi
from v0_code.pi_engine.driver import replay


@pytest.fixture()
def run(tmp_path):
    pi, src, cfg = build(tmp_path, "aud")
    replay(pi, src, cfg, mode="full")
    pi.store.close()
    return cfg


def audit(cfg, db=None):
    return audit_pi(db or cfg.paths["db_path"], cfg.paths["evidence_db"], cfg.paths["findings_db"], cfg)


def planted(cfg, tmp_path, sql, args=()):
    copy = tmp_path / "planted.db"
    shutil.copy(cfg.paths["db_path"], copy)
    c = sqlite3.connect(copy)
    c.execute(sql, args)
    c.commit()
    c.close()
    return copy


def test_a_clean_run_passes_and_the_audit_counts_what_it_checked(run):
    bad, n = audit(run)
    assert bad == [] and n["entries"] == 6 and n["versions"] >= 1 and n["labels"] > 0 and n["evidence_days_read"] > 0 and n["runs"] == 9 and n["evidence_refs"] > 0


def test_a_label_that_the_evidence_does_not_give_is_caught(run, tmp_path):
    db = tmp_path / "p1.db"
    shutil.copy(run.paths["db_path"], db)
    c = sqlite3.connect(db)
    rj, key, ver = c.execute("SELECT record_json, relationship_key, version FROM pi_long_memories ORDER BY version DESC LIMIT 1").fetchone(), None, None
    rec = json.loads(rj[0])
    rec["weekly_labels"][0]["label"] = "not_supported"
    c.execute("UPDATE pi_long_memories SET record_json = ? WHERE memory_id = ? AND version = ?", (json.dumps(rec), rec["memory_id"], rec["version"]))
    c.commit()
    c.close()
    bad, _ = audit(run, db)
    assert any("weekly label" in b for b in bad) and any("status" in b for b in bad)


def test_an_entry_in_the_wrong_week_or_written_at_the_wrong_time_is_caught(run, tmp_path):
    db = planted(run, tmp_path, "UPDATE pi_mid_entries SET memory_id = 'pi_mid_2026-W12', written_ts = written_ts + 5 WHERE case_id = 'case_a' AND entry_version = 1")
    bad, _ = audit(run, db)
    assert any("is in pi_mid_2026-W12" in b for b in bad) and any("written at" in b for b in bad)


def test_a_label_for_a_week_after_the_job_and_a_missing_run_are_caught(run, tmp_path):
    db = tmp_path / "p3.db"
    shutil.copy(run.paths["db_path"], db)
    c = sqlite3.connect(db)
    rj = c.execute("SELECT record_json FROM pi_long_memories ORDER BY version LIMIT 1").fetchone()[0]
    rec = json.loads(rj)
    rec["weekly_labels"].append({**rec["weekly_labels"][-1], "week": "2026-W30"})
    c.execute("UPDATE pi_long_memories SET record_json = ? WHERE memory_id = ? AND version = ?", (json.dumps(rec), rec["memory_id"], rec["version"]))
    c.execute("DELETE FROM pi_weekly_runs WHERE week = '2026-W12'")
    c.commit()
    c.close()
    bad, _ = audit(run, db)
    assert any("after the job that wrote it" in b for b in bad) and any("weekly runs" in b for b in bad)


def test_counters_that_do_not_follow_from_the_entries_are_caught(run, tmp_path):
    db = tmp_path / "p4.db"
    shutil.copy(run.paths["db_path"], db)
    c = sqlite3.connect(db)
    rj = c.execute("SELECT record_json FROM pi_long_memories ORDER BY version DESC LIMIT 1").fetchone()[0]
    rec = json.loads(rj)
    rec["counters"]["case_days"] += 3
    c.execute("UPDATE pi_long_memories SET record_json = ? WHERE memory_id = ? AND version = ?", (json.dumps(rec), rec["memory_id"], rec["version"]))
    c.commit()
    c.close()
    bad, _ = audit(run, db)
    assert any("counters" in b for b in bad)
