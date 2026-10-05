"""State Engine on a synthetic second patient (UTC, other streams, step readings that carry a timestamp) and on the real worked example
(spec section 9). The properties are spec section 10."""

import hashlib
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from v0_code.state_engine.baseline import BaselineView
from v0_code.state_engine.config import StateConfig
from v0_code.state_engine.engine import StateEngine
from v0_code.state_engine.inputs import StateInputs
from v0_code.state_engine.run import build_engine, replay, resume
from v0_code.state_engine.storage import StateStore

ROOT = Path(__file__).resolve().parent.parent


def run_all(cfg, db, path, start=None, end=None, rebuild=True):
    eng, ro = build_engine(cfg, str(db))
    st = StateStore(path, rebuild=rebuild)
    replay(eng, st, start, end)
    ro.close()
    return eng, st


@pytest.fixture(scope="module")
def full(state_fixture, tmp_path_factory):
    cfg, db, _ = state_fixture
    p = tmp_path_factory.mktemp("statefull") / "state.db"
    eng, st = run_all(cfg, db, p)
    return cfg, db, st


def snaps(st):
    return {r[0]: r[1] for r in st.conn.execute("SELECT as_of, snapshot_json FROM state_log ORDER BY as_of")}


def at(st, ts):
    return st.snapshot_at(ts)


# ---- early days (3.2, property 11) ---------------------------------------------------------------------------------------------------------------

def test_the_first_14_days_have_no_usual_no_position_and_no_items(full):
    cfg, _, st = full
    for ts in ("2026-01-01T12:00:00+00:00", "2026-01-14T23:45:00+00:00"):
        s = at(st, ts)
        assert s["early_days"] and "no_baseline_yet" in s["quality"] and s["open_items"] == []
        g = s["measures"]["glucose"]
        assert g["usual"] is None and g["position"] == "no_baseline_yet" and g["clinical_status"] == "normal"       # the latest value, its age and its clinical status are still shown
    assert not at(st, "2026-01-15T00:00:00+00:00")["early_days"]
    assert st.conn.execute("SELECT COUNT(*) FROM state_items WHERE opened_at < '2026-01-15'").fetchone()[0] == 0


# ---- R1 / R2 / R3 -----------------------------------------------------------------------------------------------------------------------------

def test_a_value_outside_the_baselines_device_range_is_rejected_and_the_last_good_value_is_kept(full):
    _, _, st = full
    before, bad = at(st, "2026-01-29T11:45:00+00:00"), at(st, "2026-01-29T12:00:00+00:00")                      # day 28 carries a 360 reading (this patient's range is 40-350)
    assert bad["measures"]["glucose"]["rejected_latest"] and "rejected_latest:glucose" in bad["quality"]
    assert bad["measures"]["glucose"]["value"] == before["measures"]["glucose"]["value"] and bad["measures"]["glucose"]["value_time"] == before["measures"]["glucose"]["value_time"]
    assert bad["measures"]["glucose"]["age_minutes"] == 15                                                       # the old value ages; a rejected value never replaces it
    nxt = at(st, "2026-01-29T12:15:00+00:00")["measures"]["glucose"]
    assert not nxt["rejected_latest"] and nxt["age_minutes"] == 0 and nxt["value"] != 360.0


def test_a_measure_with_no_new_value_keeps_its_last_value_and_its_age_grows(full):
    _, _, st = full
    a, b = at(st, "2026-01-20T08:00:00+00:00")["measures"]["sleep"], at(st, "2026-01-20T08:30:00+00:00")["measures"]["sleep"]
    assert a["value"] == b["value"] and a["value_time"] == b["value_time"] and (a["age_minutes"], b["age_minutes"]) == (0, 30)


def test_a_value_past_its_freshness_limit_is_not_current_and_is_flagged_stale(full):
    cfg, db, st = full
    s = at(st, "2026-01-21T07:45:00+00:00")["measures"]["sleep"]                                                  # arrives 08:00; still current 23 h 45 m later
    assert s["current"] and s["age_minutes"] == 1425
    m = at(st, "2026-01-21T00:00:00+00:00")                                                                       # a medicine record (21:00) is "current" only to the end of its day,
    assert not m["measures"]["medicines"]["current"] and "stale:medicines" not in m["quality"] and "overdue:medicines" not in m["quality"]     # but for a daily measure that is informational: it is not overdue


def test_every_value_in_every_snapshot_was_already_known_at_its_tick(full):
    _, _, st = full
    for as_of, js in snaps(st).items():
        t = datetime.fromisoformat(as_of)
        import json
        s = json.loads(js)
        for key, m in s["measures"].items():
            if m.get("value_time"):
                assert datetime.fromisoformat(m["value_time"]) <= t, (as_of, key)
            if "age_minutes" in m:
                assert m["age_minutes"] >= 0


def test_a_diary_entry_is_not_in_the_context_before_its_own_time(full):
    _, _, st = full
    assert at(st, "2026-02-03T17:45:00+00:00")["context"]["diary_today"] == []                                    # written at 18:00
    assert at(st, "2026-02-03T18:00:00+00:00")["context"]["diary_today"] == [{"category": "life_event", "text": "Team offsite dinner"}]
    assert at(st, "2026-02-04T00:00:00+00:00")["context"]["diary_today"] == []


# ---- R4: the clinical status is only carried -------------------------------------------------------------------------------------------------

def test_the_clinical_status_is_carried_from_the_store_even_when_the_position_disagrees(full):
    _, _, st = full
    s = at(st, "2026-01-31T20:00:00+00:00")["measures"]["steps"]                                                  # 8000 steps: far above her usual, but the stored status says "normal"
    assert s["position"]["label"] == "far above" and s["clinical_status"] == "normal"


# ---- R8 - R11: items and hand-offs ---------------------------------------------------------------------------------------------------------------

def test_a_far_value_opens_an_item_at_once_with_one_handoff_and_it_closes_when_a_value_is_back_in_range(full):
    _, _, st = full
    item = next(i for i in st.items() if i["measure"] == "steps")
    assert item["item_id"] == "steps_2026-01-31T20:00" and item["trigger"] == "severe" and item["direction"] == "above" and item["size_at_open"] == "far"
    assert item["opened_at"] == "2026-01-31T20:00:00+00:00" and item["peak_value"] == 8000.0 and item["status"] == "closed"
    assert item["closed_at"] == "2026-02-01T20:00:00+00:00" and item["close_reason"] == "recovered"
    hs = [h for h in st.handoffs() if h["item_id"] == item["item_id"]]
    assert len(hs) == 1 and hs[0]["measure"] == "steps" and hs[0]["value"] == 8000.0 and hs[0]["clinical_status"] == "normal" and hs[0]["written_at"] == item["opened_at"]
    assert at(st, "2026-01-31T20:00:00+00:00")["open_items"] == ["steps_2026-01-31T20:00"]
    assert at(st, "2026-01-31T20:00:00+00:00")["measures"]["steps"]["open_item_id"] == item["item_id"]


def test_a_missed_medicine_opens_an_item_at_the_time_the_record_becomes_available_and_names_the_medicine_from_config(full):
    _, _, st = full
    item = next(i for i in st.items() if i["measure"] == "medicines")
    assert item["opened_at"] == "2026-02-01T21:00:00+00:00" and item["direction"] == "below" and item["size_at_open"] == "far"
    h = next(h for h in st.handoffs() if h["item_id"] == item["item_id"])
    assert h["context"]["medication"] == {"taken": 1, "expected": 2, "missed": ["statin"]}                         # "rx_02_statin" -> "statin" by the patient's id convention
    assert at(st, "2026-02-01T21:00:00+00:00")["measures"]["medicines"]["position"]["share_at_least_as_bad"] == 0.0


def test_a_medicine_item_stays_open_past_midnight_until_the_next_record_is_available(full):
    _, _, st = full
    item = next(i for i in st.items() if i["measure"] == "medicines")
    assert item["status"] == "closed" and item["close_reason"] == "recovered" and item["closed_at"] == "2026-02-02T21:00:00+00:00"
    for ts in ("2026-02-02T00:00:00+00:00", "2026-02-02T12:00:00+00:00", "2026-02-02T20:45:00+00:00"):
        assert item["item_id"] in at(st, ts)["open_items"], ts
    assert item["item_id"] not in at(st, "2026-02-02T21:00:00+00:00")["open_items"]                              # the new record (all taken) is within "slightly" or better


def test_there_is_exactly_one_handoff_per_item_and_none_for_anything_else(full):
    _, _, st = full
    items = st.items()
    ids = [h["item_id"] for h in st.handoffs()]
    assert sorted(ids) == sorted(i["item_id"] for i in items if i["item_class"] == "adverse") and len(ids) == len(set(ids)) and len(items) >= 2
    assert all((i["handed_off_at"] == i["opened_at"]) == (i["item_class"] == "adverse") for i in items)


# ---- properties 1 / 3 / 4: deterministic, read-only, idempotent, resumable ------------------------------------------------------------------------

def test_a_replay_is_deterministic(state_fixture, tmp_path, full):
    cfg, db, _ = state_fixture
    _, st2 = run_all(cfg, db, tmp_path / "again.db")
    assert snaps(st2) == snaps(full[2]) and st2.items() == full[2].items() and st2.handoffs() == full[2].handoffs()


def test_the_store_is_opened_read_only_and_not_changed(state_fixture, tmp_path):
    cfg, db, _ = state_fixture
    before = hashlib.md5(Path(db).read_bytes()).hexdigest()
    run_all(cfg, db, tmp_path / "ro.db", date(2026, 1, 25), date(2026, 1, 27))
    assert hashlib.md5(Path(db).read_bytes()).hexdigest() == before
    with pytest.raises(sqlite3.OperationalError):
        build_engine(cfg, str(db))[1].execute("DELETE FROM raw_events")                                        # the connection the engine reads through cannot write


def test_running_the_same_ticks_again_writes_the_same_rows_and_no_duplicates(state_fixture, tmp_path):
    cfg, db, _ = state_fixture
    p = tmp_path / "idem.db"
    _, st = run_all(cfg, db, p, date(2026, 1, 30), date(2026, 2, 2))
    first = (snaps(st), st.items(), st.handoffs())
    _, st = run_all(cfg, db, p, date(2026, 1, 30), date(2026, 2, 2), rebuild=False)                             # the same ticks again, into the same file
    assert (snaps(st), st.items(), st.handoffs()) == first


def test_a_run_that_stops_and_resumes_gives_the_same_log_as_one_run(state_fixture, tmp_path, full):
    cfg, db, _ = state_fixture
    p = tmp_path / "resume.db"
    run_all(cfg, db, p, None, date(2026, 1, 31))                                                               # stops in the middle of the steps item
    eng, ro = build_engine(cfg, str(db))
    st = StateStore(p)
    last = resume(eng, st)
    assert last == datetime.fromisoformat("2026-01-31T23:45:00+00:00") and eng.states["step_count"].item["item_id"] == "steps_2026-01-31T20:00"
    replay(eng, st, date(2026, 2, 1), None)
    assert snaps(st) == snaps(full[2]) and st.items() == full[2].items() and st.handoffs() == full[2].handoffs()


# ---- property 2: no look-ahead ---------------------------------------------------------------------------------------------------------------------

def test_truncating_the_data_after_a_day_does_not_change_any_earlier_snapshot(state_fixture, tmp_path, full):
    """Everything dated after the cut is deleted from a copy of the store and the Baseline Engine is rebuilt on the shorter record: every tick up to the cut must be identical."""
    import sqlite3 as _sq
    from v0_code.baseline_v2.config import Config
    from v0_code.baseline_v2.data import StoreView
    from v0_code.baseline_v2.engine import build_windows
    from v0_code.baseline_v2.storage import MemoryV2Store

    cfg, db, d = state_fixture
    cut = "2026-02-02"
    short = tmp_path / "short.db"
    shutil.copy(db, short)
    c = _sq.connect(short)
    c.execute("DELETE FROM raw_events WHERE substr(timestamp, 1, 10) > ?", (cut,))
    c.execute("DELETE FROM context_events WHERE date > ?", (cut,))
    c.execute("DROP TABLE IF EXISTS memory_v2")
    c.commit()
    c.close()
    bcfg = Config.from_yaml(d / "fixture.yaml")
    ro = _sq.connect(f"file:{short}?mode=ro", uri=True)
    out = build_windows(bcfg, StoreView(ro, bcfg))
    ro.close()
    ms = MemoryV2Store(short)
    ms.upsert([r for t in ("day", "week", "month") for r in out[t]])
    ms.close()
    _, st = run_all(cfg, short, tmp_path / "short_state.db")
    a, b = snaps(st), snaps(full[2])
    assert len(a) == (date.fromisoformat(cut) - date(2026, 1, 1)).days * 96 + 96
    assert all(a[k] == b[k] for k in a)


# ---- property 9: generic ---------------------------------------------------------------------------------------------------------------------------

def test_the_second_patient_runs_with_config_alone_and_streams_it_lacks_do_not_appear(full):
    cfg, _, st = full
    s = at(st, "2026-02-03T20:00:00+00:00")
    assert set(s["measures"]) == {"glucose", "sleep", "steps", "hydration", "medicines"} and cfg.timezone == "UTC"
    assert s["context"]["last_meal"] is None and s["measures"]["glucose"]["usual"]["basis"] == "clock_time"        # no meals logged: the clock-time basis


def test_no_patient_specific_name_appears_in_the_engine_code():
    banned = ("sleep_duration", "cgm_glucose_reading", "step_count", "meal_events", "diary_context", "medication_adherence", "Asia/Kolkata", "metformin", "continuous_heart_rate", "hba1c")
    for f in (ROOT / "src/v0_code/state_engine").glob("*.py"):
        text = f.read_text()
        for b in banned:
            assert b not in text, (f.name, b)


def test_the_engine_makes_no_network_or_model_call():
    for f in (ROOT / "src/v0_code/state_engine").glob("*.py"):
        text = f.read_text()
        for b in ("openai", "requests", "httpx", "urllib.request", "langchain", "socket"):
            assert b not in text, (f.name, b)


# ---- the real worked example (spec section 9) ------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def evening(v2_stored, tmp_path_factory):
    _, db = v2_stored
    cfg = StateConfig.from_yaml(ROOT / "config" / "state_meera_iyer_v1.yaml", root=ROOT)
    p = tmp_path_factory.mktemp("stateevening") / "s.db"
    _, st = run_all(cfg, db, p, date(2026, 9, 16), date(2026, 9, 17))
    return st


def pos(st, hhmm, key):
    return at(st, f"2026-09-17T{hhmm}:00+05:30")["measures"][key]


def test_the_worked_example_heart_rate_and_glucose_items_open_and_close_at_the_specified_ticks(evening):
    items = {i["item_id"]: i for i in evening.items() if i["opened_at"].startswith("2026-09-17T2")}
    assert items["heart_rate_2026-09-17T21:45"]["status"] == "open"                                            # "HR item opens" at 21:45, still open at 23:30
    g = items["glucose_2026-09-17T22:30"]
    assert (g["opened_at"], g["closed_at"], g["trigger"], g["size_at_open"], g["peak_value"]) == ("2026-09-17T22:30:00+05:30", "2026-09-17T23:00:00+05:30", "persistence", "clearly", 185.0)
    h = [x for x in evening.handoffs() if x["item_id"] == g["item_id"]]
    assert len(h) == 1 and h[0]["usual_basis"] == "meal_relative" and h[0]["clinical_status"] == "high" and h[0]["context"]["last_meal"]["label"] == "festive_dinner"
    assert h[0]["context"]["medication"] == {"taken": 1, "expected": 3, "missed": ["metformin", "levothyroxine"]} and h[0]["context"]["diary_today_count"] == 2


def test_the_worked_example_glucose_positions_follow_the_meal_relative_usual(evening):
    want = {"21:30": "within", "21:45": "within", "22:00": "slightly above", "22:15": "clearly above", "22:30": "clearly above", "22:45": "slightly above", "23:00": "slightly above"}
    assert {t: pos(evening, t, "glucose")["position"]["label"] for t in want} == want
    g = pos(evening, "22:45", "glucose")
    assert g["usual"] == {"basis": "meal_relative", "context": {"meal_kind": "dinner", "minutes_since_meal": 75}, "n": 345, "median": 160.9, "sd": 14.65} or (g["usual"]["n"], g["usual"]["median"]) == (345, 160.9)
    assert (g["usual_alt"]["n"], g["usual_alt"]["median"], round(g["usual_alt"]["sd"], 1), g["usual_alt"]["label"]) == (1733, 124.9, 16.6, "clearly above")      # the clock-time usual, as in the spec
    assert g["clinical_status"] == "high" and g["value"] == 185.4 and g["age_minutes"] == 0


def test_the_worked_example_slow_measures_open_when_they_become_available(evening):
    s = at(evening, "2026-09-17T22:45:00+05:30")
    m = s["measures"]
    assert m["sleep_duration"]["position"]["label"] == "clearly below" and m["sleep_duration"]["age_minutes"] == 945
    # the spec's example shows a sleep item opened on 17 Sept at 07:00, but sleep was already "clearly below" on 15 and 16 Sept, so by R8-R10 that item opened on the 15th and stayed open
    assert m["sleep_duration"]["open_item_id"] == "sleep_duration_2026-09-15T07:00"
    assert m["resting_heart_rate"]["age_minutes"] == 937 and m["resting_heart_rate"]["open_item_id"] == "resting_heart_rate_2026-09-17T07:08"
    assert m["blood_pressure"]["position"]["worst"] == "diastolic" and m["blood_pressure"]["clinical_status"] == "high" and m["blood_pressure"]["open_item_id"] == "blood_pressure_2026-09-16T08:13"            # same continuity: the 16 Sept reading was already clearly above
    assert m["medication_adherence"]["missed"] == ["metformin", "levothyroxine"] and m["medication_adherence"]["position"]["label"] == "clearly below"
    assert m["mood_state"] == {"label": "tired", "block": "evening", "value_time": "2026-09-17T21:00:00+05:30", "current": True}
    assert m["hba1c"]["current"] is False and m["hba1c"]["clinical_status"] == "high" and "open_item_id" not in m["hba1c"]
    assert s["early_days"] is False and s["baseline_asof"] == "2026-09-16" and s["baseline_config_version"].startswith("meera_iyer_v1-")
    assert s["context"]["last_meal"]["label"] == "festive_dinner" and len(s["context"]["diary_today"]) == 2


# ---- the command line ------------------------------------------------------------------------------------------------------------------------

def test_the_command_continues_an_existing_log_and_refuses_to_rewrite_earlier_ticks(state_fixture, tmp_path, capsys, monkeypatch):
    import sys
    from v0_code.state_engine import run as R
    cfg, db, d = state_fixture
    p = tmp_path / "cli.db"

    def call(*extra):
        monkeypatch.setattr(sys, "argv", ["run", "--config", str(d / "state.yaml"), "--db", str(db), "--state-db", str(p), "--replay", *extra])
        R.main()
        return capsys.readouterr().out

    out = call("--from", "2026-01-30", "--to", "2026-01-30")
    assert "'ticks': 96" in out
    out = call("--to", "2026-01-31")                                                              # continues after the last logged tick
    assert "'first': '2026-01-31T00:00:00+00:00'" in out and "'ticks': 96" in out
    with pytest.raises(SystemExit):
        call("--from", "2026-01-30", "--to", "2026-01-30")                                       # earlier ticks than the log: refused without --rebuild
    out = call("--from", "2026-01-30", "--to", "2026-01-30", "--rebuild")
    assert "'ticks': 96" in out


# ---- the usual for a value never contains the value ------------------------------------------------------------------------------------------------

def fixture_daily_values(db, biomarker):
    """{record date: first value of that date}, independently of the engine."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = {}
    for ts, v in c.execute("SELECT timestamp, value FROM raw_events WHERE source_type = 'reading' AND biomarker = ? ORDER BY timestamp", (biomarker,)):
        out.setdefault(date.fromisoformat(ts[:10]), v)
    return out


def test_the_usual_used_for_any_value_never_includes_that_value(state_fixture, full):
    """For every daily value the moment it arrives: the profile behind its position was built from the days strictly BEFORE the date the record belongs to.
    An end-of-day value (known at the next midnight) belongs to the day before that midnight."""
    import statistics
    cfg, db, _ = state_fixture
    st = full[2]
    checked = {}
    for name in ("hydration", "step_count", "sleep_duration"):
        s = cfg.stream(name)
        daily = fixture_daily_values(db, name)
        for js in (r[0] for r in st.conn.execute("SELECT snapshot_json FROM state_log")):
            import json
            m = json.loads(js)["measures"][s.key]
            if m.get("age_minutes") != 0 or not m.get("usual"):
                continue
            vt = datetime.fromisoformat(m["value_time"])
            rec = (vt - timedelta(minutes=1)).date() if s.available_at == "end_of_day" else vt.date()
            earlier = [v for d, v in daily.items() if d < rec]
            assert m["usual"]["n"] == len(earlier) and m["usual"]["median"] == pytest.approx(statistics.median(earlier), abs=0.01), (name, rec)
            assert m["usual"]["sd"] == pytest.approx(statistics.pstdev(earlier), abs=0.01), (name, rec)
            checked[name] = checked.get(name, 0) + 1
    assert all(n >= 20 for n in checked.values()) and set(checked) == {"hydration", "step_count", "sleep_duration"}


def test_an_end_of_day_spike_is_judged_against_days_that_exclude_it(full):
    _, _, st = full
    item = next(i for i in st.items() if i["measure"] == "hydration")
    assert item["item_id"] == "hydration_2026-02-01T00:00" and item["trigger"] == "severe" and item["size_at_open"] == "far" and item["peak_value"] == 4000.0
    m = at(st, "2026-02-01T00:00:00+00:00")["measures"]["hydration"]
    assert m["usual"]["n"] == 30 and m["position"]["label"] == "far above"                                       # the 30 days before 31 January, not 31 days that already hold the spike


# ---- stale (continuous) versus overdue (daily and periodic) ----------------------------------------------------------------------------------------

def gap_run(state_fixture, tmp_path, statements, name="gap"):
    """A copy of the fixture store with rows removed, replayed (the baseline rows stay as they were)."""
    cfg, db, d = state_fixture
    gap = tmp_path / f"{name}.db"
    shutil.copy(db, gap)
    c = sqlite3.connect(gap)
    for sql in statements:
        c.execute(sql)
    c.commit()
    c.close()
    _, st = run_all(cfg, gap, tmp_path / f"{name}_state.db")
    return st


def test_an_overdue_daily_measure_closes_its_open_item_as_expired_at_the_moment_it_became_overdue(state_fixture, tmp_path):
    st = gap_run(state_fixture, tmp_path, ["DELETE FROM context_events WHERE stream = 'medication_adherence' AND date > '2026-02-01'"])
    item = next(i for i in st.items() if i["measure"] == "medicines")
    assert item["opened_at"] == "2026-02-01T21:00:00+00:00"
    # cadence 1 day x grace 1.5 = 36 h after the record became available (02-01 21:00): overdue only when the age EXCEEDS that, so the first tick that sees it is 09:15
    assert item["item_id"] in at(st, "2026-02-03T09:00:00+00:00")["open_items"] and "overdue:medicines" not in at(st, "2026-02-03T09:00:00+00:00")["quality"]
    late = at(st, "2026-02-03T09:15:00+00:00")
    assert item["item_id"] not in late["open_items"] and "overdue:medicines" in late["quality"] and late["measures"]["medicines"]["overdue"] is True
    assert item["status"] == "closed" and item["close_reason"] == "expired" and item["closed_at"] == "2026-02-03T09:00:00+00:00"


def test_any_stale_counts_only_stale_continuous_and_overdue_daily_measures(state_fixture, tmp_path, full):
    assert full[2].conn.execute("SELECT SUM(any_stale) FROM state_log").fetchone()[0] == 0                           # a complete record: nothing is stale or overdue, even though medicine
    st = gap_run(state_fixture, tmp_path, ["DELETE FROM context_events WHERE stream = 'medication_adherence' AND date > '2026-02-01'"], "gap_any")        # records are "not current" most of every day
    flags = {r[0]: r[1] for r in st.conn.execute("SELECT as_of, any_stale FROM state_log WHERE as_of >= '2026-02-03T08:45:00+00:00' AND as_of <= '2026-02-03T09:30:00+00:00'")}
    assert flags == {"2026-02-03T08:45:00+00:00": 0, "2026-02-03T09:00:00+00:00": 0, "2026-02-03T09:15:00+00:00": 1, "2026-02-03T09:30:00+00:00": 1}


def test_a_continuous_measure_still_goes_stale_after_its_freshness_limit(state_fixture, tmp_path):
    st = gap_run(state_fixture, tmp_path, ["DELETE FROM raw_events WHERE biomarker = 'cgm_glucose_reading' AND timestamp > '2026-01-20T10:15' AND timestamp < '2026-01-20T11:15'"], "gap_glucose")
    ok, bad = at(st, "2026-01-20T10:30:00+00:00"), at(st, "2026-01-20T10:45:00+00:00")                               # the last value is 10:15; the limit is 30 minutes
    assert ok["measures"]["glucose"]["current"] and "stale:glucose" not in ok["quality"]
    assert not bad["measures"]["glucose"]["current"] and "stale:glucose" in bad["quality"] and "overdue:glucose" not in bad["quality"]
    assert st.conn.execute("SELECT any_stale FROM state_log WHERE as_of = '2026-01-20T10:45:00+00:00'").fetchone()[0] == 1
    assert at(st, "2026-01-20T11:15:00+00:00")["measures"]["glucose"]["current"]


def test_no_daily_measure_is_ever_reported_stale_and_no_continuous_one_overdue(full):
    import json
    for js in (r[0] for r in full[2].conn.execute("SELECT snapshot_json FROM state_log")):
        q = json.loads(js)["quality"]
        assert not any(x.startswith("stale:") and x != "stale:glucose" for x in q) and not any(x == "overdue:glucose" for x in q)


def test_the_grace_and_the_cadence_come_from_config(state_fixture, tmp_path):
    cfg, _, d = state_fixture
    assert cfg.overdue_grace == 1.5 and cfg.stream("sleep_duration").cadence_minutes == 1440 and cfg.stream("cgm_glucose_reading").cadence_minutes is None
    real = StateConfig.from_yaml(ROOT / "config" / "state_meera_iyer_v1.yaml", root=ROOT)
    assert real.overdue_grace == 1.5 and real.stream("blood_pressure").cadence_minutes == 3 * 1440 and real.stream("hba1c").cadence_minutes == 90 * 1440 and real.stream("cgm_glucose_reading").cadence_minutes == 15
    text = (d / "state.yaml").read_text()
    (tmp_path / "nocad.yaml").write_text(text.replace("source: {table: raw, name: sleep_duration}, role: sleep, cadence: daily,", "source: {table: raw, name: sleep_duration}, role: sleep,"))
    with pytest.raises(ValueError, match="cadence"):
        StateConfig.from_yaml(tmp_path / "nocad.yaml")
    (tmp_path / "nograce.yaml").write_text(text.replace("  overdue_grace: 1.5\n", ""))
    with pytest.raises(KeyError):
        StateConfig.from_yaml(tmp_path / "nograce.yaml")


def test_a_run_resumed_after_an_item_expired_gives_the_same_log_as_one_run(state_fixture, tmp_path):
    cfg, db, d = state_fixture
    gap = tmp_path / "gapresume.db"
    shutil.copy(db, gap)
    c = sqlite3.connect(gap)
    c.execute("DELETE FROM context_events WHERE stream = 'medication_adherence' AND date > '2026-02-01'")
    c.commit()
    c.close()
    _, whole = run_all(cfg, gap, tmp_path / "whole.db")
    run_all(cfg, gap, tmp_path / "part.db", None, date(2026, 2, 3))                                             # stops on the day the item expires
    eng, ro = build_engine(cfg, str(gap))
    part = StateStore(tmp_path / "part.db")
    resume(eng, part)
    replay(eng, part, datetime.fromisoformat("2026-02-04T00:00:00+00:00"), None)
    assert snaps(part) == snaps(whole) and part.items() == whole.items()


# ---- adverse versus favourable items --------------------------------------------------------------------------------------------------------------

def sleep_run(state_fixture, tmp_path, value, status, name):
    """Day 20 (2026-01-21) of the fixture patient sleeps longer than usual. Her adverse direction for sleep is BELOW, so this is a deviation in the favourable direction."""
    return gap_run(state_fixture, tmp_path, [f"UPDATE raw_events SET value = {value}, status = '{status}' WHERE biomarker = 'sleep_duration' AND timestamp LIKE '2026-01-21%'"], name)


def test_a_deviation_in_a_favourable_direction_is_recorded_and_closed_by_the_same_rules_but_gets_no_handoff(state_fixture, tmp_path):
    st = sleep_run(state_fixture, tmp_path, 7.55, "normal", "fav")                                              # about 2.5 SDs above her usual sleep, clinically normal
    item = next(i for i in st.items() if i["measure"] == "sleep")
    assert item["item_class"] == "favourable" and item["direction"] == "above" and item["size_at_open"] == "clearly" and item["trigger"] == "persistence"
    assert item["opened_at"] == "2026-01-21T08:00:00+00:00" and item["closed_at"] == "2026-01-22T08:00:00+00:00" and item["close_reason"] == "recovered"      # n_open / n_close / labels unchanged
    assert item["handed_off_at"] is None and not [h for h in st.handoffs() if h["item_id"] == item["item_id"]]
    s = at(st, "2026-01-21T12:00:00+00:00")
    assert item["item_id"] in s["open_items"] and s["measures"]["sleep"]["open_item_id"] == item["item_id"] and s["measures"]["sleep"]["open_item_class"] == "favourable"
    assert s["open_item_classes"][item["item_id"]] == "favourable"


def test_a_favourable_deviation_becomes_adverse_when_the_clinical_status_is_abnormal_on_that_side(state_fixture, tmp_path):
    st = sleep_run(state_fixture, tmp_path, 7.55, "high", "fav_status")
    item = next(i for i in st.items() if i["measure"] == "sleep")
    h = [x for x in st.handoffs() if x["item_id"] == item["item_id"]]
    assert item["item_class"] == "adverse" and item["trigger"] == "persistence" and len(h) == 1 and h[0]["clinical_status"] == "high"
    st2 = sleep_run(state_fixture, tmp_path, 7.55, "borderline_high", "fav_border")                              # borderline is not abnormal
    assert next(i for i in st2.items() if i["measure"] == "sleep")["item_class"] == "favourable"
    st3 = sleep_run(state_fixture, tmp_path, 7.55, "low", "fav_wrongside")                                      # abnormal, but on the other side from the deviation
    assert next(i for i in st3.items() if i["measure"] == "sleep")["item_class"] == "favourable"


def test_a_favourable_deviation_becomes_adverse_when_the_position_is_far(state_fixture, tmp_path):
    st = sleep_run(state_fixture, tmp_path, 9.0, "normal", "fav_far")
    item = next(i for i in st.items() if i["measure"] == "sleep")
    assert item["item_class"] == "adverse" and item["trigger"] == "severe" and item["size_at_open"] == "far" and len([h for h in st.handoffs() if h["item_id"] == item["item_id"]]) == 1


def test_an_item_in_an_adverse_direction_is_adverse_and_every_handoff_belongs_to_an_adverse_item(full):
    _, _, st = full
    items = st.items()
    assert {i["measure"]: i["item_class"] for i in items} == {"steps": "adverse", "hydration": "adverse", "medicines": "adverse"}      # steps and hydration above her usual: favourable direction, but far
    assert sorted(h["item_id"] for h in st.handoffs()) == sorted(i["item_id"] for i in items if i["item_class"] == "adverse")


def test_a_run_resumed_with_a_favourable_item_open_gives_the_same_log_as_one_run(state_fixture, tmp_path):
    cfg, db, d = state_fixture
    gap = tmp_path / "favresume.db"
    shutil.copy(db, gap)
    c = sqlite3.connect(gap)
    c.execute("UPDATE raw_events SET value = 7.55 WHERE biomarker = 'sleep_duration' AND timestamp LIKE '2026-01-21%'")
    c.commit()
    c.close()
    _, whole = run_all(cfg, gap, tmp_path / "w.db")
    run_all(cfg, gap, tmp_path / "p.db", None, date(2026, 1, 21))                                               # stops while the favourable item is open
    eng, ro = build_engine(cfg, str(gap))
    part = StateStore(tmp_path / "p.db")
    resume(eng, part)
    assert eng.states["sleep_duration"].item["item_class"] == "favourable"
    replay(eng, part, datetime.fromisoformat("2026-01-22T00:00:00+00:00"), None)
    assert snaps(part) == snaps(whole) and part.items() == whole.items() and part.handoffs() == whole.handoffs()


# ---- a continuous measure's carried status does not rescue a favourable item ------------------------------------------------------------------------

def glucose_drop_run(state_fixture, tmp_path, drop, status, name):
    """Two consecutive glucose readings (2026-01-21 12:00 and 12:15) fall BELOW her usual (her adverse direction for glucose is ABOVE) with the given carried status."""
    return gap_run(state_fixture, tmp_path, [f"UPDATE raw_events SET value = value - {drop}, status = '{status}' WHERE biomarker = 'cgm_glucose_reading' AND timestamp IN ('2026-01-21T12:00:00+00:00', '2026-01-21T12:15:00+00:00')"], name)


def test_for_a_continuous_measure_an_abnormal_status_does_not_turn_a_favourable_item_adverse(state_fixture, tmp_path):
    for status in ("low", "normal"):
        st = glucose_drop_run(state_fixture, tmp_path, 4.5, status, f"cont_{status}")
        item = next(i for i in st.items() if i["measure"] == "glucose")
        assert item["direction"] == "below" and item["size_at_open"] == "clearly" and item["opened_at"] == "2026-01-21T12:15:00+00:00", status
        assert item["item_class"] == "favourable" and item["handed_off_at"] is None and not [h for h in st.handoffs() if h["item_id"] == item["item_id"]], status
        assert at(st, "2026-01-21T12:15:00+00:00")["measures"]["glucose"]["clinical_status"] == status               # the status is still carried and shown, just not used for the class


def test_for_a_continuous_measure_a_far_position_still_makes_a_favourable_item_adverse(state_fixture, tmp_path):
    st = glucose_drop_run(state_fixture, tmp_path, 7.0, "normal", "cont_far")
    item = next(i for i in st.items() if i["measure"] == "glucose")
    assert item["direction"] == "below" and item["size_at_open"] == "far" and item["trigger"] == "severe" and item["item_class"] == "adverse"
    assert len([h for h in st.handoffs() if h["item_id"] == item["item_id"]]) == 1


def test_for_a_daily_measure_the_abnormal_status_exception_still_applies(state_fixture, tmp_path):
    st = sleep_run(state_fixture, tmp_path, 7.55, "high", "daily_status")
    assert next(i for i in st.items() if i["measure"] == "sleep")["item_class"] == "adverse"
