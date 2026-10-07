"""Storage (append-only versions, no wall clock), as-of context and audit, and a second synthetic patient run through the whole code layer on config alone."""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import findings_synth as fs
from v0_code.findings_engine import run as frun
from v0_code.findings_engine.audit import audit_versions
from v0_code.findings_engine.config import FindingsConfig
from v0_code.findings_engine.context import Context
from v0_code.findings_engine.storage import FindingsStore, ImmutableVersionError

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def patient(tmp_path_factory):
    d = tmp_path_factory.mktemp("findings_synth")
    return d, fs.make_findings_patient(d)


def go(cfgp, root, name="out.db", rebuild=True):
    return frun.main(["--config", str(cfgp), "--root", str(root), "--db", str(Path(root) / name)] + (["--rebuild"] if rebuild else []))


# ---- the second patient, end to end -----------------------------------------------------------------------------------------------------------------------
def test_second_patient_runs_on_config_alone(patient, capsys):
    d, cfgp = patient
    assert go(cfgp, d) == 0
    out = capsys.readouterr().out
    assert "3 cases" in out and "4 versions" in out and "as-of audit clean" in out                       # h_a + h_b (joined), h_d (next brunch, past the gap), h_e (counted); h_c deferred
    s = FindingsStore(d / "out.db", readonly=True)
    cases = s.cases()
    assert [(c["n_counted"], c["n_recorded"], c["status"]) for c in cases] == [(2, 1, "closed"), (1, 0, "closed"), (1, 0, "closed")]
    recs = s.findings()
    assert all(r["text"]["source"] == "code_line" and r["provisional"] and not r["closed"] for r in recs)
    line = " ".join([recs[1]["text"]["headline"]] + [x["text"] for x in recs[1]["text"]["sentences"]])
    assert line.startswith("Sugar was clearly above her usual. Rest was clearly above her usual.")
    assert not re.search(r"\d", line)
    for real in ("glucose", "heart rate", "dinner", "missed doses", "short sleep"):
        assert real not in line.lower(), real
    assert recs[0]["local_date"] == (fs.D).isoformat()                                                   # the zone is the synthetic patient's, from its own baseline config
    s.close()


def test_the_synthetic_run_is_deterministic_and_rerunning_without_rebuild_is_the_same(patient, capsys):
    d, cfgp = patient
    go(cfgp, d, "a.db")
    go(cfgp, d, "b.db")
    a, b = FindingsStore(d / "a.db", readonly=True), FindingsStore(d / "b.db", readonly=True)
    assert a.dump() == b.dump()
    assert go(cfgp, d, "a.db", rebuild=False) == 0 and "0 written" in capsys.readouterr().out.splitlines()[-1]
    assert a.dump() == FindingsStore(d / "a.db", readonly=True).dump()


def test_the_upstream_databases_are_untouched(patient):
    d, cfgp = patient
    before = {n: (d / n).read_bytes() for n in ("state.db", "rulebook.db", "evidence.db", "store.db")}
    go(cfgp, d, "c.db")
    assert before == {n: (d / n).read_bytes() for n in before}


def test_as_of_audit_is_clean_and_catches_a_planted_late_read(patient):
    d, cfgp = patient
    cfg = FindingsConfig.from_yaml(cfgp, d)
    lib, pb, data = frun.prepare(cfg)
    ctx = Context(cfg)
    result = frun.run_replay(cfg, lib, pb, data, context=ctx)
    ctx.close()
    bad, n = audit_versions(result.versions, cfg)
    assert bad == [] and n["evidence"] >= 4 and n["relationship"] > 0
    forged = json.loads(json.dumps(result.versions))
    forged[0]["evidence_ids"].append("ev_h_e")                                    # an event from three days later
    assert any("ev_h_e" in b for b in audit_versions(forged, cfg)[0])


def test_the_context_reads_the_previous_day_up_to_as_of_and_skips_early_windows(patient):
    d, cfgp = patient
    cfg = FindingsConfig.from_yaml(cfgp, d)
    ctx = Context(cfg)
    as_of = datetime.fromisoformat(f"{fs.D.isoformat()}T21:00:00+09:00")
    diary = ctx.diary(as_of, fs.D.isoformat())
    assert diary and all(datetime.fromisoformat(e["timestamp"]) <= as_of for e in diary) and len(diary) <= 3
    assert all(e["context_id"].startswith("event_") for e in diary)                                    # no id in this patient's notes: the row id stands in
    mem = ctx.state_memory(as_of, fs.D.isoformat())
    assert [m["use"] for m in mem] == ["yesterday_day", "latest_month"] and [m["view_id"] for m in mem] == ["s1", "s2"]      # the early week window is skipped
    assert all(m["end_date"] < fs.D.isoformat() for m in mem)
    assert ctx.state_memory(as_of, (fs.D - timedelta(days=60)).isoformat()) == []                       # nothing had ended yet 60 days earlier
    ctx.close()


# ---- storage ------------------------------------------------------------------------------------------------------------------------------------------------
def rec(n=1, mode="relationship"):
    return {"finding_id": f"fnd_c_v{n}", "case_id": "c", "version": n, "as_of": "t", "mode": mode, "provisional": True, "closed": False, "text": {"source": "code_line"}, "status": "ok"}


def test_versions_are_append_only(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    assert s.put_finding(rec()) == "written" and s.put_finding(rec()) == "same"
    with pytest.raises(ImmutableVersionError):
        s.put_finding(rec(mode="descriptive"))
    assert s.get_finding("fnd_c_v1")["mode"] == "relationship"
    s.put_finding(rec(2))
    assert s.is_last_version("fnd_c_v2") and not s.is_last_version("fnd_c_v1")


def test_rebuild_is_explicit_and_no_column_holds_a_wall_clock(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    s.put_finding(rec())
    s.close()
    assert FindingsStore(tmp_path / "f.db").findings() != []                       # opening again keeps the rows
    assert FindingsStore(tmp_path / "f.db", rebuild=True).findings() == []
    conn = sqlite3.connect(tmp_path / "f.db")
    cols = [r[1] for t in ("cases", "case_handoffs", "unattached_handoffs", "findings", "finding_llm", "meta") for r in conn.execute(f"PRAGMA table_info({t})")]
    assert not any(w in c for c in cols for w in ("written_at", "created", "updated", "wall"))


def test_the_engine_names_no_stream_measure_medicine_or_patient():
    banned = ["glucose", "heart_rate", "sleep_duration", "metformin", "amlodipine", "levothyroxine", "meal_events", "diary_context", "step_count", "hydration", "screen_time", "blood_pressure",
              "mood_state", "medication_adherence", "thyroid", "meera", "iyer", "cgm", "dinner", "lunch", "breakfast", "memory_v2_day"]
    for f in list((ROOT / "src/v0_code/findings_engine").glob("*.py")) + list((ROOT / "src/v0_code/intel_common").glob("*.py")):
        text = f.read_text().lower()
        for w in banned:
            assert w not in text, f"{w} appears in {f.name}"


def test_second_patient_text_layer_runs_on_config_alone(patient):
    """The view, the checks and the retry/fallback work with this patient's phrase book, zone and library; nothing of the first patient is in the view."""
    from v0_code.findings_engine.codeline import code_sentences
    from v0_code.findings_engine.run_text import build_views
    from v0_code.findings_engine import textlayer
    from test_findings_text import FakeClient
    d, cfgp = patient
    cfg = FindingsConfig.from_yaml(cfgp, d)
    lib, pb, data = frun.prepare(cfg)
    go(cfgp, d, "t.db")
    store = FindingsStore(d / "t.db")
    recs = store.findings()
    views = build_views(cfg, pb, data, recs, lib)
    text = json.dumps(views)
    for real in ("glucose", "heart rate", "dinner", "missed doses", "short sleep", "thyroid"):
        assert real not in text.lower(), real
    assert "sugar" in text and cfg.text["model"] == "m" and all(m["part_of_day"] in ("night", "morning", "afternoon", "evening") for v in views.values() for m in v["situation"]["measures"])
    rec = recs[1]
    v = views[rec["finding_id"]]
    ids = sorted(textlayer.view_ids(v))
    answer = {"headline": "Sugar and rest were above her usual.", "sentences": [{"text": "Her sugar was clearly above her usual.", "refs": [v["situation"]["measures"][0]["id"]]},
                                                                            {"text": "There is not enough history yet to say what usually goes with this.", "refs": ["h1"]}]}
    if rec["history_note"] == "enough":                                                           # check 16: nothing about history when there is enough
        answer["sentences"][1] = {"text": "It is nothing more than a plain account.", "refs": [v["situation"]["measures"][0]["id"]]}
    if "not_known_yet" in v:
        answer["sentences"].append({"text": "It is not known yet what the rest of the day held.", "refs": ["n1"]})
    r = textlayer.generate(v, rec, code_sentences(rec, pb), FakeClient([answer]), cfg.text, pb, None)
    assert r.status == "ok" and r.text_source == "llm", r.checks
    bad = textlayer.generate(v, rec, code_sentences(rec, pb), FakeClient(["nope", "nope"]), cfg.text, pb, None)
    assert bad.status == "code_line_fallback" and bad.text["headline"].startswith("Sugar")
    store.close()
