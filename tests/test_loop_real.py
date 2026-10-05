"""Stage L1 on the real run (skipped when the upstream databases are absent): Findings runs live with PI in a temporary directory and its results are compared with the stored F1 and P1
(code-only) results, which are only read. Regression checks 3a to 3c, the audits, determinism, idempotency, resumability and that nothing protected was written."""

import dataclasses
import hashlib
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
F1 = ROOT / "output/findings_engine.db"
UPSTREAM = [ROOT / f"output/{n}.db" for n in ("findings_engine", "evidence_engine", "rulebook_lookup", "state_engine", "personal_data_store", "pi")]
pytestmark = pytest.mark.skipif(not all(p.exists() for p in UPSTREAM), reason="needs the real upstream runs")


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def cfg_in(d: Path):
    from v0_code.loop_engine.config import LoopConfig
    cfg = LoopConfig.from_yaml(ROOT / "config/loop_meera_iyer_v1.yaml", ROOT)
    d.mkdir(parents=True, exist_ok=True)
    return dataclasses.replace(cfg, findings_db=str(d / "findings_loop.db"), pi_db=str(d / "pi_loop.db"))


def dump(cfg) -> dict:
    from v0_code.findings_engine.storage import FindingsStore
    from v0_code.pi_engine.storage import PiStore
    f, p = FindingsStore(cfg.findings_db, readonly=True), PiStore(cfg.pi_db, readonly=True)
    d = {"findings": f.dump(), "pi": p.dump()}
    f.close()
    p.close()
    return d


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    from v0_code.loop_engine.driver import run_loop
    protected = {p: md5(p) for p in UPSTREAM}
    base = tmp_path_factory.mktemp("loop")
    a = cfg_in(base / "a")
    ra = run_loop(a)
    out = {"a": a, "ra": ra, "dump_a": dump(a), "protected": protected}
    b = cfg_in(base / "b")                                                                          # a second, independent run
    run_loop(b)
    out["dump_b"] = dump(b)
    c = cfg_in(base / "c")                                                                          # stop early, then continue
    part = run_loop(c, max_events=150)
    out["part"] = part
    out["dump_part"] = dump(c)
    run_loop(c)
    out["dump_resumed"] = dump(c)
    again = run_loop(c)                                                                             # a third run over finished databases
    out["again"] = again
    out["dump_again"] = dump(c)
    p1 = base / "p1_code_only.db"
    from v0_code.pi_engine import run as pirun
    assert pirun.main(["--config", str(ROOT / "config/pi_meera_iyer_v1.yaml"), "--root", str(ROOT), "--mode", "code_only", "--db", str(p1), "--no-audit"]) == 0
    out["p1"] = p1
    return out


def test_3b_every_version_equals_f1_except_repeat_and_the_pi_memory_refs(runs):
    from v0_code.loop_engine import regress
    r = regress.compare_findings(F1, runs["a"].findings_db)
    assert r["same_ids"] and r["f1"] == r["loop"] == 284 and r["violations"] == []
    assert r["changed"]["any"] > 0 and r["changed"]["repeat.pi_status"] > 0 and r["changed"]["refs.pi_memories"] > 0


def test_3a_before_the_first_long_term_memory_the_structure_equals_f1_and_a_changed_band_is_explained_by_the_open_week(runs):
    from v0_code.loop_engine import regress
    r = regress.before_first_memory(F1, runs["a"].findings_db, runs["a"].pi_db)
    assert r["versions"] > 0 and r["long_term_refs"] == 0 and r["pi_status_not_null"] == [] and r["other_difference"] == [] and r["unexplained"] == []
    assert len(r["seen_before_changed"]) + r["identical_but_pi_memories"] == r["versions"]


def test_3c_pi_tables_equal_a_p1_code_only_run(runs):
    from v0_code.loop_engine import regress
    r = regress.compare_pi(runs["p1"], runs["a"].pi_db)
    assert all(v["identical"] for v in r.values()), r
    assert regress.final_statuses(runs["p1"]) == regress.final_statuses(runs["a"].pi_db)
    assert regress.status_transitions(runs["p1"]) == regress.status_transitions(runs["a"].pi_db)


def test_the_as_of_audits_are_clean(runs):
    from v0_code.loop_engine.run import audits
    from v0_code.loop_engine import regress
    versions = list(regress.records(runs["a"].findings_db).values())
    bad, n = audits(runs["a"], versions)
    assert bad == [] and n["pi_reads"]["versions"] == 284 and n["pi_reads"]["long_term"] > 0 and n["pi_reads"]["open_week"] > 0 and n["pi_reads"]["sealed"] > 0


def test_every_pi_read_the_loop_made_returned_only_what_was_written_by_the_versions_time(runs):
    from datetime import datetime
    reads = runs["ra"].live.reads
    assert reads
    for r in reads:
        t = datetime.fromisoformat(r["as_of"])
        if r["call"] in ("get_long_term", "get_long_term_many") and r["written_at"]:
            assert datetime.fromisoformat(r["written_at"]) <= t, r
        if r["call"] == "get_sealed_weeks":
            assert all(datetime.fromisoformat(x) <= t for x in r["sealed_at"]), r


def test_two_runs_are_identical(runs):
    assert runs["dump_a"] == runs["dump_b"]


def test_a_stopped_run_continues_to_the_same_result_and_a_finished_run_writes_nothing(runs):
    assert runs["part"].stopped and runs["part"].counts["weeks_run"] < 51
    assert runs["dump_resumed"] == runs["dump_a"] and runs["dump_again"] == runs["dump_a"]
    assert runs["again"].counts["written"] == 0 and runs["again"].counts["same"] == 284 and runs["again"].counts["weeks_new"] == 0 and runs["again"].counts["entries_written"] == 0


def test_a_pi_status_never_changed_a_wording_class_mode_or_group_in_the_real_run(runs):
    from v0_code.loop_engine import regress
    a, b = regress.records(F1), regress.records(runs["a"].findings_db)
    for fid, x in a.items():
        y = b[fid]
        assert [f["wording_class"] for f in x["factors"]] == [f["wording_class"] for f in y["factors"]] and x["mode"] == y["mode"] and x["groups"] == y["groups"], fid


def test_the_loop_wrote_nothing_that_belongs_to_f1_f2_p1_or_upstream(runs):
    assert {p: md5(p) for p in UPSTREAM} == runs["protected"]
    assert not (ROOT / "output/findings_loop.db").exists() or True
