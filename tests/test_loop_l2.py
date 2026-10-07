"""Stage L2, the loop with the models, on the real upstream databases with a FAKE model (no network): week barriers, text reuse, entry texts, structural identity with L1, resumability,
the stop rules and the call-ordering audit. Skipped when the upstream runs are absent."""

import dataclasses
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
F1 = ROOT / "output/findings_engine.db"
UPSTREAM = [ROOT / f"output/{n}.db" for n in ("findings_engine", "evidence_engine", "rulebook_lookup", "state_engine", "personal_data_store", "pi")]
pytestmark = pytest.mark.skipif(not all(p.exists() for p in UPSTREAM), reason="needs the real upstream runs")


class FakeModel:
    """Answers every Findings view with a valid two-sentence text about its first measure and every PI view with null."""

    def __init__(self, mode="valid"):
        self.mode, self.calls, self.lock = mode, 0, threading.Lock()
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        with self.lock:
            self.calls += 1
        if self.mode == "error":
            raise TimeoutError("slow")
        system, user = kw["messages"][0]["content"], kw["messages"][1]["content"]
        if system.startswith("You add one short line"):
            content = json.dumps({"situations": None})
        else:
            view = json.loads(user.split("VIEW:\n", 1)[1].split("\n\nYour previous")[0])
            m = view["situation"]["measures"][0]["id"]
            content = json.dumps({"headline": "A measure was off her usual that day.", "sentences": [{"text": "A measure was off her usual that day.", "refs": [m]},
                                                                                                       {"text": "Nothing more is stated here.", "refs": [m]}]})
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, completion_tokens_details=SimpleNamespace(reasoning_tokens=2))
        return SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def cfg_in(d: Path, f2=True, stop=None):
    from v0_code.loop_engine.config import LoopConfig
    cfg = LoopConfig.from_yaml(ROOT / "config/loop_meera_iyer_v1.yaml", ROOT)
    d.mkdir(parents=True, exist_ok=True)
    l2 = {**cfg.l2, "findings_db": str(d / "ff.db"), "pi_db": str(d / "pp.db"), "f2_db": cfg.l2["f2_db"] if f2 else None, "previous": None, **({"stop": stop} if stop else {})}
    return dataclasses.replace(cfg, findings_db=str(d / "l1_f.db"), pi_db=str(d / "l1_p.db"), l2=l2)


def dumps(cfg, f=None, p=None):
    from v0_code.findings_engine.storage import FindingsStore
    from v0_code.pi_engine.storage import PiStore
    fs, ps = FindingsStore(f or cfg.l2["findings_db"], readonly=True), PiStore(p or cfg.l2["pi_db"], readonly=True)
    d = {"findings": {k: v for k, v in fs.dump().items() if k != "meta"}, "texts": fs.texts(), "pi": ps.dump(), "pi_texts": ps.texts()}      # (the meta table holds this run's call log)
    fs.close()
    ps.close()
    return d


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    from v0_code.loop_engine.driver import run_loop
    from v0_code.loop_engine.l2 import run_l2
    base = tmp_path_factory.mktemp("l2")
    cfg = cfg_in(base / "a")
    run_loop(cfg)                                                                                   # L1 into the same temp dir, for the structural comparison
    model = FakeModel()
    res = run_l2(cfg, model)
    out = {"cfg": cfg, "res": res, "model": model, "dump_a": dumps(cfg)}
    again = FakeModel()
    out["again"] = run_l2(cfg, again)                                                                # a rerun over finished databases
    out["again_model"] = again
    out["dump_again"] = dumps(cfg)
    fresh = cfg_in(base / "b")                                                                       # a fresh rerun that reads the first run's answers: zero calls
    z = FakeModel()
    out["fresh"] = run_l2(fresh, z, seeds=(cfg.l2["findings_db"],), pi_seeds=(cfg.l2["pi_db"],), use_f2=False)
    out["fresh_model"] = z
    out["dump_fresh"] = dumps(fresh)
    return out


def test_every_version_has_a_text_and_the_week_barriers_ran_in_order(runs):
    from v0_code.findings_engine.storage import FindingsStore
    f = FindingsStore(runs["cfg"].l2["findings_db"], readonly=True)
    texts = f.texts()
    assert len(f.findings()) == 284 and len(texts) == 284 and runs["res"].notes["weeks_run"] == 51
    assert {t["status"] for t in texts.values()} == {"ok"} and runs["model"].calls > 0
    f.close()


def test_the_structured_layer_equals_f1_and_l1_and_pi_statuses_equal_l1(runs):
    from v0_code.loop_engine import regress
    cfg = runs["cfg"]
    a, l1 = regress.records(cfg.l2["findings_db"]), regress.records(cfg.findings_db)
    assert a.keys() == l1.keys() == regress.records(F1).keys() and all(json.dumps(a[k], sort_keys=True) == json.dumps(l1[k], sort_keys=True) for k in a)
    r = regress.compare_findings(F1, cfg.l2["findings_db"])
    assert r["violations"] == []
    pi = regress.compare_pi(cfg.pi_db, cfg.l2["pi_db"])
    assert pi["pi_long_memories"]["identical"] and pi["pi_weekly_runs"]["identical"] and pi["pi_entry_keys"]["identical"] and pi["pi_mid_entries"]["different_rows"] > 0      # only the entry text differs
    assert regress.status_transitions(cfg.pi_db) == regress.status_transitions(cfg.l2["pi_db"]) and regress.final_statuses(cfg.pi_db) == regress.final_statuses(cfg.l2["pi_db"])


def test_the_pi_entries_carry_the_final_text_and_the_sealed_weeks_too(runs):
    from v0_code.loop_engine.l2_audit import audit_call_log
    bad, n = audit_call_log(runs["cfg"].l2["findings_db"], runs["cfg"].l2["pi_db"])
    assert bad == [] and n["entries"] == 284 and n["barriers"] == 51 and n["findings_texts"] == 284
    import sqlite3
    c = sqlite3.connect(f"file:{runs['cfg'].l2['pi_db']}?mode=ro", uri=True)
    sealed = [json.loads(r[0]) for r in c.execute("SELECT record_json FROM pi_mid_memories WHERE status = 'sealed'")]
    from v0_code.findings_engine.storage import FindingsStore
    f = FindingsStore(runs["cfg"].l2["findings_db"], readonly=True)
    texts = f.texts()
    f.close()
    assert sum(len(w["entries"]) for w in sealed) >= 116 and all(e["headline"] == texts[e["finding_id"]]["text"]["headline"] for w in sealed for e in w["entries"])
    assert any(e["headline"] == "A measure was off her usual that day." for w in sealed for e in w["entries"])


def test_the_full_audits_are_clean(runs):
    from v0_code.loop_engine import regress
    from v0_code.loop_engine.run import audits
    cfg = runs["cfg"]
    run_cfg = dataclasses.replace(cfg, findings_db=cfg.l2["findings_db"], pi_db=cfg.l2["pi_db"])
    bad, n = audits(run_cfg, list(regress.records(cfg.l2["findings_db"]).values()))
    assert bad == []


def test_an_f2_answer_is_kept_for_an_unchanged_view_and_only_changed_views_are_always_new(runs):
    log = runs["res"].log["calls"]
    texts = [c for c in log if c["phase"] == "findings_text"]
    reused = [c for c in texts if c["from_cache"]]
    assert len(texts) == 284 and reused and all(c["p_items"] == 0 for c in reused)                   # never for a view that carries an earlier conclusion
    assert all(c["from_prompt"] in ("p-v3", "p-v2", "p-v1", None) for c in reused)
    assert sum(c["p_items"] > 0 for c in texts) == 106 and all(not c["from_cache"] for c in texts if c["p_items"] > 0)


def test_a_rerun_makes_no_call_and_changes_nothing(runs):
    assert runs["again_model"].calls == 0 and runs["again"].notes["weeks_skipped"] == 51 and runs["again"].notes["weeks_run"] == 0
    assert runs["dump_again"] == runs["dump_a"]


def test_a_fresh_rerun_that_reads_the_first_runs_answers_makes_no_call_and_is_identical(runs):
    assert runs["fresh_model"].calls == 0
    a, b = runs["dump_a"], runs["dump_fresh"]
    assert a["findings"] == b["findings"] and a["pi"] == b["pi"]
    assert {k: v["text"] for k, v in a["texts"].items()} == {k: v["text"] for k, v in b["texts"].items()}
    assert {k: v["text"] for k, v in a["pi_texts"].items()} == {k: v["text"] for k, v in b["pi_texts"].items()}


def test_the_stop_rule_ends_the_run_and_a_later_run_continues_to_the_same_result(runs, tmp_path):
    from v0_code.loop_engine.l2 import StopLoop, run_l2
    cfg = cfg_in(tmp_path / "s", stop={"after_calls": 2, "max_first_failure": 0.45, "max_call_errors": 0.10})
    with pytest.raises(StopLoop) as e:
        run_l2(cfg, FakeModel("error"))
    assert "first attempt" in str(e.value) or "API error" in str(e.value)
    from v0_code.pi_engine.storage import PiStore
    p = PiStore(cfg.l2["pi_db"], readonly=True)
    assert p.get_progress("done") is None and p.get_progress("stopped")
    p.close()
    good = FakeModel()
    run_l2(cfg, good)                                                                                  # continue: call-error fallbacks are tried again
    d = dumps(cfg)
    assert {k: v["text"] for k, v in d["texts"].items()} == {k: v["text"] for k, v in runs["dump_a"]["texts"].items()}
    assert d["pi"] == runs["dump_a"]["pi"] and d["findings"] == runs["dump_a"]["findings"]


def test_the_audit_names_a_text_written_before_the_memory_it_cites(runs):
    from v0_code.loop_engine.l2_audit import audit_call_log
    cfg = runs["cfg"]
    log = json.loads(json.dumps(runs["res"].log))
    cited = next(c for c in log["calls"] if c["phase"] == "findings_text" and c["p_items"] > 0)
    cited["barrier"] = 0
    bad, _ = audit_call_log(cfg.l2["findings_db"], cfg.l2["pi_db"], log)
    assert any(cited["id"] in b and "cites memory" in b for b in bad)
    log2 = json.loads(json.dumps(runs["res"].log))
    log2["barriers"][3]["texts_start"] = log2["barriers"][2]["lines_end"] - 1
    assert any("started before" in b or "out of order" in b for b in audit_call_log(cfg.l2["findings_db"], cfg.l2["pi_db"], log2)[0])


def test_l2_wrote_nothing_that_belongs_to_an_earlier_stage(runs):
    from v0_code.loop_engine.config import LoopConfig, LoopConfigError
    import hashlib
    assert hashlib.md5(F1.read_bytes()).hexdigest() == "b86721280366e76ea524a63535d28e39"
    real = LoopConfig.from_yaml(ROOT / "config/loop_meera_iyer_v1.yaml", ROOT)
    assert real.l2["findings_db"].endswith("findings_loop_polish.db") and real.l2["pi_db"].endswith("pi_loop_polish.db") and real.l2["findings_db"] != real.findings_db
    assert real.l2["previous"]["findings_db"].endswith("findings_loop_full.db") and real.l2["previous"]["findings_db"] != real.l2["findings_db"]
    assert LoopConfigError


def test_a_kept_f2_text_is_the_versions_own_f2_text_never_a_twins(runs):
    from v0_code.findings_engine.storage import FindingsStore
    f2, f = FindingsStore(F1, readonly=True), FindingsStore(runs["cfg"].l2["findings_db"], readonly=True)
    t2, t = f2.texts(), f.texts()
    flat = lambda x: [x["headline"].rstrip(".")] + [(s["text"] if isinstance(s, dict) else s).rstrip(".") for s in x["sentences"]]          # (the cleanup now finishes a sentence with a full stop)
    kept = [c["id"] for c in runs["res"].log["calls"] if c["phase"] == "findings_text" and c.get("cause") == "f2"]               # (an F2 text that now fails a check may be replaced by an identical-view twin's, cause "twin")
    assert kept and all(flat(t[fid]["text"]) == flat(t2[fid]["text"]) for fid in kept)
    f2.close()
    f.close()


# ---- the polish round: reuse a previous run's texts where the view is unchanged and they still pass --------------------------------------------------------------------------------
def prev_cfg(d: Path, prev: dict):
    cfg = cfg_in(d, f2=False)
    return dataclasses.replace(cfg, l2={**cfg.l2, "previous": prev})


@pytest.fixture(scope="module")
def polish(runs, tmp_path_factory):
    from v0_code.loop_engine.l2 import run_l2
    base = tmp_path_factory.mktemp("polish")
    prev = {"findings_db": runs["cfg"].l2["findings_db"], "pi_db": runs["cfg"].l2["pi_db"]}
    cfg = prev_cfg(base / "c", prev)
    m = FakeModel()
    res = run_l2(cfg, m)
    return {"cfg": cfg, "res": res, "model": m, "prev": prev}


def test_with_nothing_changed_the_previous_texts_are_kept_and_no_call_is_made(polish, runs):
    assert polish["model"].calls == 0
    causes = {c["cause"] for c in polish["res"].log["calls"] if c["phase"] == "findings_text"}
    assert causes <= {"kept", "kept_recleaned"} and "kept" in causes
    a, b = dumps(runs["cfg"]), dumps(polish["cfg"])
    assert {k: v["text"]["headline"] for k, v in a["texts"].items()} == {k: v["text"]["headline"] for k, v in b["texts"].items()}
    assert a["pi"]["pi_long_memories"] == b["pi"]["pi_long_memories"]


def tamper(db, fid, fn):
    import sqlite3
    c = sqlite3.connect(db)
    row = c.execute("SELECT text_json, view_hash, text_source, status FROM finding_text WHERE finding_id = ?", (fid,)).fetchone()
    new = fn({"text": json.loads(row[0]), "view_hash": row[1], "source": row[2], "status": row[3]})
    c.execute("UPDATE finding_text SET text_json = ?, view_hash = ?, text_source = ?, status = ? WHERE finding_id = ?", (json.dumps(new["text"]), new["view_hash"], new["source"], new["status"], fid))
    c.commit()
    c.close()


def copy_prev(runs, tmp_path):
    import shutil
    d = tmp_path / "prev"
    d.mkdir()
    for k in ("findings_db", "pi_db"):
        shutil.copy(runs["cfg"].l2[k], d / Path(runs["cfg"].l2[k]).name)
    return {"findings_db": str(d / Path(runs["cfg"].l2["findings_db"]).name), "pi_db": str(d / Path(runs["cfg"].l2["pi_db"]).name)}


def test_a_previous_text_that_now_fails_a_check_or_whose_view_changed_goes_back_to_the_model_only_for_that_version(runs, tmp_path):
    from v0_code.loop_engine.l2 import run_l2
    prev = copy_prev(runs, tmp_path)
    ids = [c["id"] for c in runs["res"].log["calls"] if c["phase"] == "findings_text" and not c["from_cache"]][:3]
    fails, changed, fallback = ids

    def now_fails(r):                               # the saved answer cites the history note although there is enough history (check 16)
        r["text"]["raw"]["sentences"][0]["refs"] = ["h1"]
        return r

    def new_hash(r):
        r["view_hash"] = "0" * 64
        return r

    def as_fallback(r):                             # a fallback whose saved answer is gone: nothing to re-judge
        r["source"], r["status"] = "code_line", "code_line_fallback"
        r["text"] = {"headline": "H", "sentences": [], "source": "code_line"}
        return r
    for fid, fn in ((fails, now_fails), (changed, new_hash), (fallback, as_fallback)):
        tamper(prev["findings_db"], fid, fn)
    import sqlite3
    c = sqlite3.connect(prev["findings_db"])
    c.execute("UPDATE finding_llm SET llm_raw = '[\"nope\"]' WHERE finding_id = ?", (fallback,))
    c.commit()
    c.close()
    cfg = prev_cfg(tmp_path / "t", prev)
    m = FakeModel()
    res = run_l2(cfg, m)
    by = {c["id"]: c for c in res.log["calls"] if c["phase"] == "findings_text"}
    assert by[fails]["cause"] == "fails_now" and by[changed]["cause"].startswith("view_changed") and by[fallback]["cause"] == "fallback_before"
    assert sum(not c["from_cache"] for c in by.values()) == 3 and m.calls >= 3


def test_a_fallback_whose_saved_answers_now_pass_is_kept_without_a_call(runs, tmp_path):
    from v0_code.loop_engine.l2 import run_l2
    prev = copy_prev(runs, tmp_path)
    fid = next(c["id"] for c in runs["res"].log["calls"] if c["phase"] == "findings_text" and not c["from_cache"])
    import sqlite3
    c = sqlite3.connect(prev["findings_db"])
    good_raw = json.dumps(json.loads(c.execute("SELECT text_json FROM finding_text WHERE finding_id = ?", (fid,)).fetchone()[0])["raw"])
    c.execute("UPDATE finding_llm SET llm_raw = ? WHERE finding_id = ?", (json.dumps(["not json", good_raw]), fid))
    c.commit()
    c.close()
    tamper(prev["findings_db"], fid, lambda r: {**r, "source": "code_line", "status": "code_line_fallback", "text": {"headline": "H", "sentences": [], "source": "code_line"}})
    m = FakeModel()
    res = run_l2(prev_cfg(tmp_path / "t", prev), m)
    assert m.calls == 0 and next(c for c in res.log["calls"] if c["id"] == fid)["cause"] in ("kept", "kept_recleaned")


def test_cleanup_punctuation_changes_a_kept_text_and_is_recorded_as_such(runs, tmp_path):
    from v0_code.loop_engine.l2 import run_l2
    prev = copy_prev(runs, tmp_path)
    fid = next(c["id"] for c in runs["res"].log["calls"] if c["phase"] == "findings_text" and not c["from_cache"])

    def drop_stop(r):
        r["text"]["raw"]["sentences"][1]["text"] = "Nothing more is stated here"
        r["text"]["sentences"][1]["text"] = "Nothing more is stated here"                           # an old text, saved before the cleanup finished sentences
        return r
    tamper(prev["findings_db"], fid, drop_stop)
    m = FakeModel()
    res = run_l2(prev_cfg(tmp_path / "t", prev), m)
    assert m.calls == 0 and next(c for c in res.log["calls"] if c["id"] == fid)["cause"] == "kept_recleaned"
    from v0_code.findings_engine.storage import FindingsStore
    f = FindingsStore(res.findings_db, readonly=True)
    assert [s["text"] for s in f.texts()[fid]["text"]["sentences"]][1] == "Nothing more is stated here."
    f.close()
