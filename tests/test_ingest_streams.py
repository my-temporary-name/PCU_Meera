"""Ingest-only streams (config/ingest_streams.yaml): readings already parsed from the data dir are written to context_events by a config row, and are used by
nothing but the engines that name them in `used_by`. The Baseline and State Engines never see them: not in their registry, not in their configs."""

import sqlite3
from pathlib import Path

import pytest
import yaml

from v0_code.data.context_ingest import build_context_rows
from v0_code.data.ingest_config import IngestConfigError, load_ingest_streams
from v0_code.graph.state import Reading, UMCState
from v0_code.logic.registry import REGISTRY

ROOT = Path(__file__).resolve().parent.parent
INGEST_CFG = ROOT / "config/ingest_streams.yaml"


def write(tmp_path, body):
    p = tmp_path / "ingest.yaml"
    p.write_text(yaml.safe_dump(body))
    return p


GOOD = {"ingest_streams": {"hourly_thing": {"kind": "hourly", "source": {"biomarker": "thing_per_hour"}, "used_by": ["some_engine"]}}}


def make_state(readings):
    return UMCState(data_dir="d", ranges_dir="r", output_dir="o", passed_readings=readings)


def reading(bio, ts, v):
    return Reading(event_id="e", biomarker=bio, timestamp=ts, value=v, source_file="f.csv")


def test_loader_parses_a_stream(tmp_path):
    (s,) = load_ingest_streams(write(tmp_path, GOOD))
    assert (s.name, s.kind, s.biomarker, s.used_by) == ("hourly_thing", "hourly", "thing_per_hour", ("some_engine",))


@pytest.mark.parametrize("mutate,word", [
    (lambda d: d["ingest_streams"]["hourly_thing"].pop("used_by"), "used_by"),
    (lambda d: d["ingest_streams"]["hourly_thing"].update(used_by=[]), "used_by"),
    (lambda d: d["ingest_streams"]["hourly_thing"].pop("source"), "biomarker"),
    (lambda d: d["ingest_streams"]["hourly_thing"].update(source={}), "biomarker"),
    (lambda d: d["ingest_streams"]["hourly_thing"].pop("kind"), "kind"),
    (lambda d: d["ingest_streams"].update(meal_events=dict(d["ingest_streams"]["hourly_thing"])), "registry"),          # a name the Baseline registry already owns
    (lambda d: d["ingest_streams"].update(raw_events=dict(d["ingest_streams"]["hourly_thing"])), "table"),              # not a stream name that clashes with the store tables
])
def test_loader_rejects_bad_rows(tmp_path, mutate, word):
    import copy
    d = copy.deepcopy(GOOD)
    mutate(d)
    with pytest.raises(IngestConfigError) as e:
        load_ingest_streams(write(tmp_path, d))
    assert word in str(e.value)


def test_ingest_rows_for_a_configured_stream(tmp_path):
    state = make_state([reading("thing_per_hour", "2030-01-01T00:00:00+05:30", 0.0), reading("other", "2030-01-01T00:00:00+05:30", 9.0),
                                      reading("thing_per_hour", "2030-01-01T01:00:00+05:30", 12.0), reading("thing_per_hour", "2030-01-02T00:00:00+05:30", 5.0)])
    streams = load_ingest_streams(write(tmp_path, GOOD))
    base = build_context_rows(state)
    with_cfg = build_context_rows(state, streams)
    assert with_cfg[:len(base)] == base                                         # existing rows and their order are untouched; new rows come after
    assert with_cfg[len(base):] == [("hourly_thing", "2030-01-01T00:00:00+05:30", "2030-01-01", None, 0.0, None, None),
                                    ("hourly_thing", "2030-01-01T01:00:00+05:30", "2030-01-01", None, 12.0, None, None),
                                    ("hourly_thing", "2030-01-02T00:00:00+05:30", "2030-01-02", None, 5.0, None, None)]


def test_no_configured_streams_changes_nothing():
    state = make_state([reading("thing_per_hour", "2030-01-01T00:00:00+05:30", 1.0)])
    assert build_context_rows(state) == build_context_rows(state, ()) == []


def test_only_plausibility_passed_readings_are_ingested(tmp_path):
    state = make_state([reading("thing_per_hour", "2030-01-01T00:00:00+05:30", 1.0)])           # a failed reading is never in passed_readings
    assert len(build_context_rows(state, load_ingest_streams(write(tmp_path, GOOD)))) == 1


# ---- the real config: ingest-only means only the named engine references it ------------------------------------------------------------------
def real_streams():
    return load_ingest_streams(INGEST_CFG)


def test_real_config_names_the_hourly_steps_stream_for_the_rulebook_only():
    (s,) = real_streams()
    assert s.name == "step_count_hourly" and s.kind == "hourly" and s.used_by == ("rulebook",) and s.biomarker == "steps_hourly"


def test_ingest_only_streams_are_not_in_the_baseline_registry_or_either_engine_config():
    names = {s.name for s in real_streams()}
    assert {s.name for s in REGISTRY}.isdisjoint(names)
    for cfg in ("config/patient_meera_iyer_v1.yaml", "config/state_meera_iyer_v1.yaml"):
        text = (ROOT / cfg).read_text()
        for n in names:
            assert n not in text, f"{n} appears in {cfg}"


def test_only_the_rulebook_config_maps_the_stream():
    raw = yaml.safe_load((ROOT / "config/rulebook_meera_iyer_v1.yaml").read_text())["rulebook"]
    assert raw["stream_map"]["step_count_hourly"] == "step_count_hourly"
    for s in real_streams():
        assert s.used_by == ("rulebook",)


def test_the_stream_and_file_names_are_not_hard_coded_in_the_engines():
    for f in (ROOT / "src/v0_code").rglob("*.py"):
        if f.name == "ingest_config.py":
            continue
        assert "step_count_hourly" not in f.read_text(), f"step_count_hourly is hard-coded in {f}"
    assert "steps_hourly_yearly" not in (ROOT / "src/v0_code/data/context_ingest.py").read_text()


# ---- the real store ----------------------------------------------------------------------------------------------------------------------------
DB = ROOT / "output/personal_data_store.db"
needs_db = pytest.mark.skipif(not DB.exists(), reason="needs output/personal_data_store.db")


@needs_db
def test_real_store_has_the_hourly_rows_after_the_other_streams():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    n, mn, mx = c.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM context_events WHERE stream = 'step_count_hourly'").fetchone()
    assert n > 8000
    assert c.execute("SELECT MAX(id) FROM context_events WHERE stream != 'step_count_hourly'").fetchone()[0] < mn          # appended: no existing row moved
    assert c.execute("SELECT COUNT(*) FROM context_events WHERE stream = 'step_count_hourly' AND (value_num IS NULL OR timestamp IS NULL)").fetchone()[0] == 0
    days = c.execute("SELECT COUNT(DISTINCT date) FROM context_events WHERE stream = 'step_count_hourly'").fetchone()[0]
    daily = c.execute("SELECT COUNT(*) FROM raw_events WHERE biomarker = 'step_count' AND source_type = 'reading'").fetchone()[0]
    assert days == daily                                                                                                     # the same days as the daily step_count rows
