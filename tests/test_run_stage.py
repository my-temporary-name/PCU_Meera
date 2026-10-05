"""The Stage runner: saves after every batch, resumes, skips early windows, falls back to code-only entries, chains the tiers
and stops on its two rules. A stub model stands in for the LLM."""

import asyncio
import json
import re
import shutil

import pytest

from v0_code import run_memory_stage as rms
from v0_code.data.store import PersonalDataStore

GOOD = {"headline": "A day.", "what_stood_out": ["Glucose stayed within range.", "Activity was low.", "A dose was missed."], "notable_reason": "Something changed."}
BAD = {**GOOD, "what_stood_out": ["Glucose rose because of dinner.", "Activity was low.", "A dose was missed."]}   # causal language: fails the first attempt AND the retry
EARLY_DAYS = 14


class Stub:
    def __init__(self, reply):
        self.reply, self.calls, self.ids = reply, 0, []

    async def ainvoke(self, messages):
        self.calls += 1
        ids = re.findall(r"=== WINDOW (\S+) \(", messages[-1][1])
        self.ids += ids
        return type("R", (), {"content": json.dumps({i: self.reply for i in ids})})()


@pytest.fixture()
def db(pipeline_run, tmp_path):
    _, src = pipeline_run
    dst = tmp_path / "stage.db"
    shutil.copy(src, dst)
    return str(dst)


def _rows(db_path, tier="day"):
    s = PersonalDataStore(db_path)
    return {r["window_id"]: r for r in s.conn.execute("SELECT * FROM memory_records WHERE tier=?", (tier,))}


def test_saves_every_window_and_skips_the_early_days_without_a_call(db):
    stub = Stub(GOOD)
    state = asyncio.run(rms.run_stage("day", 4, db, llm=stub))
    rows = _rows(db)
    assert state["stopped"] is None and state["remaining"] == 0
    assert stub.calls == -(-(352 - EARLY_DAYS) // 4) == 85 and state["early_saved"] == EARLY_DAYS
    assert sum(r["llm_status"] == "code_only_early" for r in rows.values()) == EARLY_DAYS and sum(r["llm_status"] == "ok" for r in rows.values()) == 352 - EARLY_DAYS
    r = rows["day_2025-12-26"]
    memory = json.loads(r["memory_json"])
    assert memory["headline"] == "A day." and memory["rendered"]["material_changes"] and memory["is_notable"] == bool(r["is_notable"])
    blob = json.loads(r["llm_raw"])
    assert blob["first_attempt_ok"] is True and json.loads(blob["raw"])["headline"] == "A day."
    early = rows["day_2025-10-03"]
    e = json.loads(early["memory_json"])
    assert early["llm_status"] == "code_only_early" and "Not enough history" in e["headline"] and e["confidence"] == "low"
    assert json.loads(early["llm_raw"])["first_attempt_ok"] is None


def test_resume_keeps_ok_windows_and_reruns_old_rejected_ones(db):
    s = PersonalDataStore(db)
    ids = [r["window_id"] for r in s.conn.execute("SELECT window_id FROM memory_records WHERE tier='day' ORDER BY start_date LIMIT 100")]
    ok, rejected = ids[20:60], ids[60:70]
    for w in ok:
        s.update_memory_llm_result(w, "{}", False, "ok", "{}")
    for w in rejected:
        s.update_memory_llm_result(w, "{}", False, "rejected", "{}")   # the old status from the first Stage 1 run
    stub = Stub(GOOD)
    asyncio.run(rms.run_stage("day", 4, db, llm=stub))
    assert not set(ok) & set(stub.ids) and set(rejected) <= set(stub.ids)
    assert _rows(db)[ok[0]]["memory_json"] == "{}"


def test_a_fallback_window_is_final_and_is_not_rerun(db):
    stub = Stub(BAD)
    asyncio.run(rms.run_stage("day", 4, db, llm=stub))        # stops, leaving fallbacks
    fb = [w for w, r in _rows(db).items() if r["llm_status"] == "code_only_fallback"]
    assert fb
    stub2 = Stub(GOOD)
    asyncio.run(rms.run_stage("day", 4, db, llm=stub2))
    assert not set(fb) & set(stub2.ids)


def test_stops_when_first_attempt_failures_exceed_25_percent_counting_model_windows_only(db):
    state = asyncio.run(rms.run_stage("day", 4, db, llm=Stub(BAD)))
    assert state["stopped"] and "first-attempt failure rate" in state["stopped"]
    assert 20 <= state["attempted"] < 352 - EARLY_DAYS and state["remaining"] > 0
    rows = _rows(db)
    fb = [r for r in rows.values() if r["llm_status"] == "code_only_fallback"]
    assert fb and all(json.loads(r["memory_json"])["headline"] for r in fb)                     # no empty memory
    assert sum(r["llm_status"] == "code_only_early" for r in rows.values()) == EARLY_DAYS      # early windows are not counted as failures


def test_does_not_stop_below_the_minimum_window_count(db):
    class OneBad(Stub):
        async def ainvoke(self, messages):
            self.calls += 1
            ids = re.findall(r"=== WINDOW (\S+) \(", messages[-1][1])
            return type("R", (), {"content": json.dumps({i: (BAD if (self.calls == 1 and i == ids[0]) else GOOD) for i in ids})})()
    state = asyncio.run(rms.run_stage("day", 4, db, llm=OneBad(GOOD)))
    assert state["stopped"] is None and state["first_failed"] == 1


def test_stops_when_a_number_is_grounded_nowhere(db):
    invented = {**GOOD, "what_stood_out": ["Glucose averaged 987654 mg/dL.", "Activity was low.", "A dose was missed."]}
    state = asyncio.run(rms.run_stage("day", 4, db, llm=Stub(invented)))
    assert state["stopped"] and "grounded nowhere" in state["stopped"] and state["ungrounded"]
    assert state["attempted"] < 352 - EARLY_DAYS


def test_the_chain_runs_day_then_week_then_month_with_the_batch_sizes(db):
    stub = Stub(GOOD)
    states = asyncio.run(rms.run_all(rms.TIERS, db, rms.BATCH_SIZE, llm=stub))
    assert [s["tier"] for s in states] == ["day", "week", "month"] and not any(s["stopped"] for s in states)
    for tier in rms.TIERS:
        rows = _rows(db, tier)
        assert all(r["llm_status"] in rms.DONE for r in rows.values())
    month_rows = _rows(db, "month")
    assert sum(r["llm_status"] == "code_only_early" for r in month_rows.values()) == 1          # the first checkpoint has no previous one


def test_a_stopped_tier_ends_the_chain(db):
    states = asyncio.run(rms.run_all(rms.TIERS, db, rms.BATCH_SIZE, llm=Stub(BAD)))
    assert [s["tier"] for s in states] == ["day"] and states[0]["stopped"]
    assert not _rows(db, "week") or all(r["llm_status"] != "ok" for r in _rows(db, "week").values())


def test_summary_reports_counts_rates_reasons_and_quiet_fraction(db):
    asyncio.run(rms.run_stage("day", 4, db, llm=Stub(BAD)))
    s = rms.summarize("day", db)
    assert s["status"]["code_only_early"] == EARLY_DAYS and s["status"].get("code_only_fallback")
    assert s["first_attempt_failure_rate"] > 0.9 and s["final_failure_rate"] > 0.9
    assert s["first_attempt_failure_kinds"].get("forbidden_language") and s["final_failure_kinds"].get("forbidden_language")
    assert 0 < s["quiet_fraction"] < 1


def test_random_entries_come_from_the_ok_windows(db):
    asyncio.run(rms.run_stage("day", 4, db, llm=Stub(GOOD)))
    entries = rms.random_entries("day", 5, db)
    assert len(entries) == 5 and all(e["headline"] == "A day." and e["rendered"] for e in entries)


# ---- the default command must not wipe the database -------------------------------------------------------------------------------

def test_the_pipeline_command_refuses_to_touch_an_existing_database_without_rebuild(tmp_path, monkeypatch, capsys):
    from v0_code import cli
    out = tmp_path / "out"
    out.mkdir()
    db = out / "personal_data_store.db"
    db.write_text("precious model-written entries")
    calls = []

    async def fake_run(*a, **k):
        calls.append(a)
        raise AssertionError("the pipeline must not run")

    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    monkeypatch.setattr("sys.argv", ["v0-code", "--output-dir", str(out)])
    with pytest.raises(SystemExit) as e:
        cli.main()
    assert e.value.code == 2 and not calls and db.read_text() == "precious model-written entries"
    assert "--rebuild" in capsys.readouterr().err


def test_rebuild_flag_and_a_missing_database_both_allow_the_run(tmp_path, monkeypatch):
    from v0_code import cli
    out = tmp_path / "out"
    out.mkdir()
    calls = []

    async def fake_run(*a, **k):
        calls.append(a)
        return object()

    monkeypatch.setattr(cli, "run_pipeline", fake_run)
    monkeypatch.setattr(cli, "print_report", lambda state: None)
    monkeypatch.setattr("sys.argv", ["v0-code", "--output-dir", str(out)])
    cli.main()                                   # no database yet: first build is allowed
    (out / "personal_data_store.db").write_text("x")
    monkeypatch.setattr("sys.argv", ["v0-code", "--output-dir", str(out), "--rebuild"])
    cli.main()                                   # explicit rebuild
    assert len(calls) == 2
