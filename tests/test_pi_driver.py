"""PI: the replay driver (pi_spec.md 11 as amended, item 40): stored Findings versions in as_of order, weekly jobs between events, a final job at the end of the data."""

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from pi_helpers import LIB, PB, SLEEP, START, finding, make_cfg, make_evidence, make_findings_db, weekly
from v0_code.pi_engine.driver import FindingsSource, replay
from v0_code.pi_engine.engine import Pi
from v0_code.pi_engine.storage import PiStore

IST = ZoneInfo("Asia/Kolkata")
S, SUG = "supported", "suggestive"


def at(off, hh=12, mm=0):
    d = date.fromordinal(START.toordinal() + off)
    return f"{d.isoformat()}T{hh:02d}:{mm:02d}:00+05:30"


def build(tmp_path, name="a", mode="full", extra_cases=()):
    d = tmp_path / name
    d.mkdir()
    labels = make_evidence(d, {SLEEP: weekly([S] * 9)})
    cfg = make_cfg(d)
    vs = [finding("case_a", 1, at(1), "2026-03-03", [(SLEEP, S, "exposed", [])], headline="code a1"),
          finding("case_a", 2, at(1, 14), "2026-03-03", [(SLEEP, S, "exposed", [])], headline="code a2"),
          finding("case_b", 1, at(17), "2026-03-19", [(SLEEP, S, "not_exposed", [])], headline="code b1"),
          finding("case_c", 1, at(6, 23, 0), "2026-03-08", [(SLEEP, S, "exposed", [])], headline="code c1"),
          finding("case_c", 2, at(7, 0, 30), "2026-03-08", [(SLEEP, S, "exposed", [])], headline="code c2"),
          finding("case_d", 1, at(8 * 7 + 1), "2026-04-28", [(SLEEP, S, "exposed", [])], headline="code d1")]
    final = lambda r: {"headline": "final " + r["text"]["headline"], "sentences": [{"text": "Model sentence.", "refs": ["f1"]}], "source": "llm"}
    make_findings_db(d, [(r, final(r) if r["case_id"] != "case_d" else None) for r in vs],
                     [{"case_id": "case_a", "local_date": "2026-03-03", "opened_at": at(1), "last_handoff_at": at(1, 14), "closed_at": at(1, 20)},
                      {"case_id": "case_d", "local_date": "2026-04-28", "opened_at": at(57), "last_handoff_at": at(57), "closed_at": "2026-04-29T18:00:00+05:30"},
                      {"case_id": "case_late", "local_date": "2026-04-29", "opened_at": at(58), "last_handoff_at": at(58), "closed_at": "2026-04-30T04:00:00+05:30"}])
    pi = Pi(cfg, PiStore(cfg.paths["db_path"]), labels, LIB, PB)
    return pi, FindingsSource(cfg.paths["findings_db"]), cfg


def test_weekly_jobs_run_before_the_next_event_and_a_final_job_closes_the_data(tmp_path):
    pi, src, cfg = build(tmp_path)
    rep = replay(pi, src, cfg, mode="full")
    weeks = [r["week"] for r in pi.store.runs()]
    assert weeks == [f"2026-W{n}" for n in range(10, 19)] and rep["weeks_run"] == 9
    last = pi.store.runs()[-1]
    assert last["written_at"] == "2026-04-29T23:59:59+05:30"                                         # the data end on Wednesday: the final job runs then, not on Sunday
    assert pi.store.runs()[0]["written_at"] == "2026-03-08T23:59:59+05:30"
    assert rep["versions_written"] == 6 and rep["versions_same"] == 0


def test_an_event_after_a_week_end_is_recorded_after_that_weeks_job(tmp_path):
    pi, src, cfg = build(tmp_path)
    replay(pi, src, cfg, mode="full")
    w10 = pi.get_sealed_weeks(20, "2026-04-30T00:00:00+05:30")
    first = [w for w in w10 if w["week"]["iso"] == "2026-W10"][0]
    assert sorted({e["case_id"] for e in first["entries"]}) == ["case_a", "case_c"] and [e["entry_version"] for e in first["entries"] if e["case_id"] == "case_c"] == [1]   # c2 is Monday
    second = [w for w in w10 if w["week"]["iso"] == "2026-W11"][0]
    assert [e["entry_version"] for e in second["entries"] if e["case_id"] == "case_c"] == [2]
    assert second["entries"][0]["local_date"] in ("2026-03-08", "2026-03-19")


def test_full_mode_carries_the_final_text_and_code_only_the_code_line(tmp_path):
    pi, src, cfg = build(tmp_path, "full")
    replay(pi, src, cfg, mode="full")
    assert pi.get_case_entry("case_a", "2026-04-30T00:00:00+05:30")["headline"] == "final code a2" and pi.get_case_entry("case_a", "2026-04-30T00:00:00+05:30")["sentences"] == ["Model sentence."]
    assert pi.get_case_entry("case_d", "2026-04-30T00:00:00+05:30")["headline"] == "code d1"            # no stored final text: the code line
    pi2, src2, cfg2 = build(tmp_path, "code")
    replay(pi2, src2, cfg2, mode="code_only")
    assert pi2.get_case_entry("case_a", "2026-04-30T00:00:00+05:30")["headline"] == "code a2" and pi2.get_case_entry("case_a", "2026-04-30T00:00:00+05:30")["sentences"] == ["One sentence."]


def test_a_second_run_writes_nothing_new(tmp_path):
    pi, src, cfg = build(tmp_path)
    replay(pi, src, cfg, mode="full")
    before = json.dumps(pi.store.dump(), sort_keys=True)
    rep = replay(pi, src, cfg, mode="full")
    assert json.dumps(pi.store.dump(), sort_keys=True) == before and rep["versions_written"] == 0 and rep["versions_same"] == 6 and rep["weeks_new"] == 0


@pytest.mark.parametrize("stop", [1, 2, 3, 5])
def test_a_stopped_run_resumes_to_the_same_result(tmp_path, stop):
    one, src1, cfg1 = build(tmp_path, "one")
    replay(one, src1, cfg1, mode="full")
    two, src2, cfg2 = build(tmp_path, "two")
    partial = replay(two, src2, cfg2, mode="full", max_events=stop)
    assert partial["stopped"] is True
    replay(two, src2, cfg2, mode="full")
    assert json.dumps(two.store.dump(), sort_keys=True) == json.dumps(one.store.dump(), sort_keys=True)


def test_two_fresh_runs_are_identical(tmp_path):
    a, sa, ca = build(tmp_path, "x")
    b, sb, cb = build(tmp_path, "y")
    replay(a, sa, ca, mode="full")
    replay(b, sb, cb, mode="full")
    assert json.dumps(a.store.dump(), sort_keys=True) == json.dumps(b.store.dump(), sort_keys=True)


def test_case_closings_are_counted_and_those_after_the_data_end_close_at_the_end(tmp_path):
    pi, src, cfg = build(tmp_path)
    rep = replay(pi, src, cfg, mode="full")
    assert rep["cases_closed"] == 3 and rep["cases_closed_after_the_data_end"] == 1


def test_the_driver_never_changes_the_findings_database(tmp_path):
    pi, src, cfg = build(tmp_path)
    import hashlib
    h = lambda: hashlib.sha256(open(cfg.paths["findings_db"], "rb").read()).hexdigest()
    before = h()
    replay(pi, src, cfg, mode="full")
    assert h() == before
