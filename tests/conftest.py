"""Shared fixtures. `pipeline_run` runs the real pipeline once per session into a temp dir (no LLM: the glucose caption
step is off by default); `pipeline_records` returns every window's stored record, so the golden and invariant tests check
the actual output of the actual code on the actual patient data."""

import asyncio
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def pipeline_run(tmp_path_factory):
    """(final UMCState, path to the pipeline's SQLite store)."""
    if not (ROOT / "final").exists():
        pytest.skip("source data folder 'final/' is not present")
    from v0_code.graph.executor import run_pipeline

    out = tmp_path_factory.mktemp("pipeline_output")
    state = asyncio.run(run_pipeline(str(ROOT / "final"), str(ROOT / "ranges"), str(out)))
    return state, out / "personal_data_store.db"


@pytest.fixture(scope="session")
def pipeline_records(pipeline_run) -> dict[str, dict]:
    from v0_code.data.store import PersonalDataStore

    _, db = pipeline_run
    with PersonalDataStore(db) as store:
        return {r["window_id"]: json.loads(r["record_json"]) for r in store.conn.execute("SELECT window_id, record_json FROM memory_records")}


# ---- Baseline Engine v2 fixtures --------------------------------------------------------------------------------------------------

V2_CONFIG = ROOT / "config" / "patient_meera_iyer_v1.yaml"


@pytest.fixture(scope="session")
def v2_cfg():
    from v0_code.baseline_v2.config import Config
    return Config.from_yaml(V2_CONFIG)


@pytest.fixture(scope="session")
def v2_rows(pipeline_run, v2_cfg):
    """Every day window the engine builds from the real pipeline's store (read-only)."""
    import sqlite3
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_days

    _, db = pipeline_run
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = build_days(v2_cfg, StoreView(conn, v2_cfg))
    conn.close()
    return {r["window_id"]: r for r in rows}


FIXTURE_YAML = """
patient:
  id: fixture_he
  timezone: "UTC"
  pronoun: "he"
  strain_mood_categories: []
  medication_id_regex: "^rx_\\\\d+_"
history: {min_days_for_compare: 14, reliable_completeness_pct: 70}
glucose: {device_range: [40, 350], max_step_change_per_15min: 75, expected_per_day: 96, gap_hours_flag: 1.0}
streams:
  - {name: cgm_glucose_reading, domain: glucose,   kind: continuous, label: glucose,    unit: mg/dL,            agg: glucose_mean,   source: raw, expected_per_day: 96}
  - {name: time_in_range,       domain: glucose,   kind: derived,    label: time in range, unit: percentage points, agg: glucose_tir_pct}
  - {name: variability,         domain: glucose,   kind: derived,    label: variability, unit: percentage points, agg: glucose_cv_pct}
  - {name: sleep_duration,      domain: sleep,     kind: daily,      label: sleep,      unit: hours,            agg: value, source: raw, expected_per_day: 1}
  - {name: step_count,          domain: activity,  kind: hourly,     label: steps,      unit: steps,            agg: value, source: raw, expected_per_day: 1}
  - {name: medication_adherence, domain: adherence, kind: event,     label: medication adherence, unit: percentage points, agg: adherence_pct, source: context}
flat_band: {sd_multiplier: 0.5}
size_labels: {small_below: 2, moderate_below: 4}
anchors:
  glucose_TIR_change_points: {day: 10}
  glucose_CV_change_points: {day: 8}
  severe_range_appeared_or_cleared: true
  sleep_hours_change: {day: 2.0}
  adherence_meds_changed: {day: "min(2, n_meds)"}
  steps_abs_change: {day: 1000}
gist: {}
"""


def build_fixture_store(path, days: int = 40):
    """A tiny synthetic patient: UTC+0 timestamps, 2 medications (rx_ ids), NO mood stream, NO heart rate, a different step floor.
    Day 28 carries a 360 mg/dL reading (inside the default 40-400 range, outside this patient's 40-350); day 30 a big step jump;
    day 31 a missed dose; day 33 a diary entry."""
    import json
    import math
    from datetime import date, timedelta
    from v0_code.data.store import PersonalDataStore

    store = PersonalDataStore(path, reset=True)
    readings, ctx = [], []
    base = date(2026, 1, 1)
    for i in range(days):
        ds = (base + timedelta(days=i)).isoformat()
        for k in range(96):
            v = 105 + 12 * math.sin(2 * math.pi * k / 96) + (i % 3)
            if i == 28 and k == 48:
                v = 360.0
            readings.append((f"g{i}_{k}", f"{ds}T{k // 4:02d}:{(k % 4) * 15:02d}:00+00:00", "cgm_glucose_reading", round(v, 1), "normal"))
        readings.append((f"s{i}", f"{ds}T08:00:00+00:00", "sleep_duration", 7.0 + 0.1 * (i % 5), "normal"))
        readings.append((f"t{i}", f"{ds}T20:00:00+00:00", "step_count", 8000.0 if i == 30 else 5000.0 + 50 * (i % 4), "normal"))
        for med in ("rx_01_metformin", "rx_02_statin"):
            taken = not (i == 31 and med == "rx_02_statin")
            ctx.append(("medication_adherence", None, ds, "taken" if taken else "missed", float(taken), med, json.dumps({})))
        if i == 33:
            ctx.append(("diary_context", f"{ds}T18:00:00+00:00", ds, "Team offsite dinner", None, "life_event", json.dumps({"note": "mild"})))
    store.insert_readings(readings)
    store.insert_context_events(ctx)
    store.conn.close()
    return path


@pytest.fixture(scope="session")
def v2_fixture(tmp_path_factory):
    import sqlite3
    from v0_code.baseline_v2.config import Config
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_days

    d = tmp_path_factory.mktemp("v2fixture")
    (d / "fixture.yaml").write_text(FIXTURE_YAML)
    cfg = Config.from_yaml(d / "fixture.yaml")
    db = build_fixture_store(d / "fixture.db")
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = {r["window_id"]: r for r in build_days(cfg, StoreView(conn, cfg))}
    conn.close()
    return cfg, rows, db


@pytest.fixture(scope="session")
def v2_all(pipeline_run, v2_cfg):
    """All three tiers the engine builds from the real pipeline's store: {"day": {id: row}, "week": {...}, "month": {...}}."""
    import sqlite3
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_windows

    _, db = pipeline_run
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = build_windows(v2_cfg, StoreView(conn, v2_cfg))
    conn.close()
    return {tier: {r["window_id"]: r for r in rows} for tier, rows in out.items()}


@pytest.fixture(scope="session")
def v2_weeks_with_weekday_rule(pipeline_run, v2_cfg):
    """Week rows built with a weekday rule configured (Sunday): the optional rule that the shipped config turns off with `none`."""
    import dataclasses
    import sqlite3
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_windows

    _, db = pipeline_run
    cfg = dataclasses.replace(v2_cfg, gist={**v2_cfg.gist, "week_gist_weekday": "Sunday"})
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = build_windows(cfg, StoreView(conn, cfg))
    conn.close()
    return cfg, {r["window_id"]: r for r in out["week"]}


@pytest.fixture(scope="session")
def v2_fixture_all(v2_fixture):
    import sqlite3
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_windows

    cfg, _, db = v2_fixture
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = build_windows(cfg, StoreView(conn, cfg))
    conn.close()
    return cfg, {tier: {r["window_id"]: r for r in rows} for tier, rows in out.items()}


@pytest.fixture(scope="session")
def v2_stored(pipeline_run, v2_cfg, tmp_path_factory):
    """(rows, db): the real run's v2 windows written to memory_v2 (in a COPY of the run's store, so other tests' store is untouched) and read back
    parsed with facts, {tier: [row]} in date order."""
    import shutil
    import sqlite3
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_windows
    from v0_code.baseline_v2.storage import MemoryV2Store

    _, src = pipeline_run
    db = str(tmp_path_factory.mktemp("v2_stored") / "store.db")
    shutil.copy(src, db)
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = build_windows(v2_cfg, StoreView(ro, v2_cfg))
    ro.close()
    store = MemoryV2Store(db)
    store.upsert([r for t in ("day", "week", "month") for r in out[t]])
    rows = {t: [store.get_memory(t, r["end_date"], full=True) for r in out[t]] for t in out}
    store.close()
    return rows, db


# ---- State Engine fixtures ------------------------------------------------------------------------------------------------------------

STATE_FIXTURE_YAML = """
state:
  baseline_config: {baseline}
  db_path: state.db
  tick_minutes: 15
  min_history_days: 14
  min_samples_usual: 30
  overdue_grace: 1.5
  last_meal_window_minutes: 1440
  position: {{method_default: sd, thresholds_sd: [1, 2, 4], thresholds_percentile: [0.35, 0.15, 0.05]}}
  persistence: {{open_label: clearly, close_label: slightly, n_open: 2, n_close: 2}}
  severe: {{position: far, statuses: [critical_high, critical_low]}}
  glucose: {{usual_basis: meal_relative_with_clock_fallback, meal_window_minutes: 180, meal_bucket_minutes: 15, clock_band_minutes: 30, meal_kinds: [dinner]}}
  streams:
    cgm_glucose_reading: {{key: glucose, kind: continuous, source: {{table: raw, name: cgm_glucose_reading}}, freshness_minutes: 30, available_at: timestamp, usual_basis: glucose, adverse_directions: [above], cleaning: baseline_glucose}}
    sleep_duration:      {{key: sleep, kind: daily, source: {{table: raw, name: sleep_duration}}, role: sleep, cadence: daily, freshness_minutes: 1440, available_at: timestamp, usual_basis: profile, adverse_directions: [below], n_open: 1, n_close: 1}}
    step_count:          {{key: steps, kind: daily, source: {{table: raw, name: step_count}}, cadence: daily, freshness_minutes: 1440, available_at: timestamp, usual_basis: profile, adverse_directions: [below], n_open: 1, n_close: 1}}
    hydration:           {{key: hydration, kind: daily, source: {{table: raw, name: hydration}}, cadence: daily, freshness_minutes: 1440, available_at: end_of_day, usual_basis: profile, adverse_directions: [below], n_open: 1, n_close: 1}}
    medication_adherence: {{key: medicines, kind: count, source: {{table: context, name: medication_adherence}}, cadence: daily, freshness: end_of_day, available_at: "21:00", usual_basis: history_percentile, adverse_directions: [below], n_open: 1, n_close: 1}}
  context_streams:
    diary: {{name: diary_context, available_at: "21:00"}}
"""


@pytest.fixture(scope="session")
def state_fixture(tmp_path_factory):
    """The synthetic second patient (UTC, 2 medicines, no mood / heart rate / blood pressure / meals) with its baseline written to memory_v2, and a state config that
    names only the streams it has. Returns (state cfg, store db path, directory)."""
    import sqlite3
    from v0_code.baseline_v2.config import Config
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_windows
    from v0_code.baseline_v2.storage import MemoryV2Store
    from v0_code.state_engine.config import StateConfig

    from datetime import date, timedelta
    from v0_code.data.store import PersonalDataStore

    d = tmp_path_factory.mktemp("statefixture")
    (d / "fixture.yaml").write_text(FIXTURE_YAML.replace("  - {name: medication_adherence", "  - {name: hydration, domain: lifestyle, kind: daily, label: hydration, unit: mL, agg: value, source: raw, expected_per_day: 1}\n  - {name: medication_adherence", 1))
    (d / "state.yaml").write_text(STATE_FIXTURE_YAML.format(baseline=str(d / "fixture.yaml")))
    db = build_fixture_store(d / "fixture.db")
    with PersonalDataStore(db) as store:                  # an END-OF-DAY stream (written at 23:00, available at the next midnight) with one spike on day 30
        store.insert_readings([(f"h{i}", f"{(date(2026, 1, 1) + timedelta(days=i)).isoformat()}T23:00:00+00:00", "hydration", 4000.0 if i == 30 else 2000.0 + 10 * (i % 3), "normal") for i in range(40)])
    bcfg = Config.from_yaml(d / "fixture.yaml")
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = build_windows(bcfg, StoreView(ro, bcfg))
    ro.close()
    ms = MemoryV2Store(db)
    ms.upsert([r for t in ("day", "week", "month") for r in out[t]])
    ms.close()
    return StateConfig.from_yaml(d / "state.yaml"), db, d
