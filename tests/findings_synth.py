"""A second synthetic patient for the Findings Engine tests (UTC+9, other stream, exposure, outcome, measure and event-check names, its own phrase book). Event evidence comes from
the real Evidence Engine run on tests/evidence_synth.py's patient, so the records have the true shape; the hand-off, packet, diary and memory databases are written here."""

import copy
import json
import sqlite3
from datetime import datetime, time, timedelta
from pathlib import Path

import yaml

import evidence_synth as syn
from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.events import EventEngine
from v0_code.evidence_engine.loader import load_data
from v0_code.evidence_engine.refresh import DailyRefresh
from v0_code.evidence_engine.storage import EvidenceStore
from v0_code.rulebook_lookup.storage import PacketStore
from v0_code.state_engine.storage import StateStore

ROOT = Path(__file__).resolve().parent.parent
D = syn.START + timedelta(days=200)

MEMORY_V2 = """CREATE TABLE IF NOT EXISTS memory_v2 (id INTEGER PRIMARY KEY AUTOINCREMENT, window_id TEXT UNIQUE, tier TEXT, start_date TEXT, end_date TEXT, gist_headline TEXT, gist_status TEXT, is_notable INTEGER)"""


def phrasebook() -> dict:
    """The real phrase book with this patient's library ids and different words, so nothing of the first patient can leak through."""
    raw = copy.deepcopy(yaml.safe_load((ROOT / "config/findings_phrasebook_v0.yaml").read_text()))
    raw["exposures"] = {
        "pill_skip": {"phrase": "skipped pills {window}", "number": "plural", "pending": "the pill record"},
        "rest_hours": {"phrase": "a short night {window}", "number": "singular", "pending": "last night's rest"},
        "stress_block": {"phrase": "a tense spell {window}", "number": "singular", "pending": "the mood log"},
        "unwell_note": {"phrase": "an unwell note {window}", "number": "singular", "pending": "the day's notes"},
        "steps_before": {"phrase": "a burst of walking in the hour before", "number": "singular", "pending": "the last hour's steps"},
        "late_start": {"phrase": "a late start to the meal", "number": "singular", "pending": "the meal time"}}
    raw["outcomes"] = {
        "meal_peak": {"phrase": "bigger sugar swings after {kind}", "contrary": "her sugar swings after {kind} have tended to be smaller"},
        "day_level": {"phrase": "a higher sugar level over the day", "contrary": "her sugar level over the day has tended to be lower"},
        "night_len": {"phrase": "a shorter night", "contrary": "her night has tended to be longer"},
        "hour_level": {"phrase": "a higher sugar level in that hour", "contrary": "her sugar level in that hour has tended to be lower"}}
    raw["event_checks"] = {
        "anything": {"phrase": "a standing fact", "static": True}, "peak_check": {"phrase": "the height of this swing", "position_suffix": "among {kind}s at this point"},
        "gap_check": {"phrase": "the wait since the last meal", "position_suffix": "at this time of day"}, "artifact": {"phrase": "a stray reading", "pending": "the readings that follow"},
        "rise": {"phrase": "a rise in the morning"}, "rates": {"phrase": "which pill is skipped"}}
    raw["measures"] = {"sugar": {"above": "sugar was {strength} above her usual", "below": "sugar was {strength} below her usual"}, "rest": {"above": "rest was {strength} above her usual", "below": "rest was {strength} below her usual"}}
    return raw


def make_findings_patient(d) -> Path:
    """Write every database and config the Findings Engine reads for the synthetic patient into `d`; return the findings config path."""
    d = Path(d)
    ev_cfg_path = syn.make_patient(d, n_days=240)
    cfg = EvidenceConfig.from_yaml(ev_cfg_path, d)
    lib, data, _ = load_data(cfg, d)
    st = EvidenceStore(d / "evidence.db")
    eng = EventEngine(data, lib, cfg, st, DailyRefresh(data, lib, cfg, st))

    def sel(rule, ranks):
        return [{"rank": r, "weight_tier": lib.pair(rule, r)["tier"], "candidate": lib.pair(rule, r)["candidate"], "check_type": lib.pair(rule, r)["check_type"], "lookback": {"kind": "x", "value": None}}
                for r in ranks]

    def tz(day, h, m=0):
        return datetime.combine(day, time(h, m), tzinfo=syn.TZ)

    supper = next(r for r in data.records("meals") if r.date == D and r.category.startswith("supper"))
    brunch = next(r for r in data.records("meals") if r.date == D + timedelta(days=1) and r.category.startswith("brunch"))
    plan = [("h_a", "r_meal", [1, 2, 3, 4, 7], supper.ts + timedelta(minutes=62), ("supper_x", supper.ts), "sugar", "ok"),
            ("h_b", "r_day", [1, 2, 3], supper.ts + timedelta(minutes=140), None, "rest", "ok"),
            ("h_c", "r_day", [], supper.ts + timedelta(minutes=170), None, "rest", "deferred"),
            ("h_d", "r_meal", [1, 2, 3, 4, 7], brunch.ts + timedelta(minutes=45), ("brunch_x", brunch.ts), "sugar", "ok"),
            ("h_e", "r_day", [1, 2], tz(D + timedelta(days=3), 23, 30), None, "rest", "ok")]
    state, rb = StateStore(d / "state.db"), PacketStore(d / "rulebook.db")
    for hid, rule, ranks, t, meal, measure, status in plan:
        pk = {"packet_id": f"packet_{hid}", "handoff_id": hid, "matched_rule": {"rule_id": rule, "status": "active"}, "selected": sel(rule, ranks), "skipped": [], "not_selected": [], "status": status,
              "rulebook_version": "x", "counts": {"selected": len(ranks), "skipped": 0, "not_selected": 0}}
        last = None if meal is None else {"label": meal[0], "time": meal[1].isoformat(), "minutes_ago": int((t - meal[1]).total_seconds() // 60)}
        ho = {"handoff_id": hid, "item_id": f"i_{hid}", "written_at": t.isoformat(), "measure": measure, "direction": "above", "size": "clearly", "opened_at": t.isoformat(), "context": {"last_meal": last}}
        eng.process(pk, ho)
        state.conn.execute("INSERT INTO state_handoffs (handoff_id, item_id, written_at, record_json) VALUES (?, ?, ?, ?)", (hid, ho["item_id"], ho["written_at"], json.dumps(ho)))
        rb.write(pk)
    state.conn.commit()
    for s in (state, rb, st):
        s.close()
    conn = sqlite3.connect(d / "store.db")
    conn.execute(MEMORY_V2)
    conn.executemany("INSERT INTO memory_v2 (window_id, tier, start_date, end_date, gist_headline, gist_status, is_notable) VALUES (?, ?, ?, ?, ?, ?, ?)", [
        (f"day_{(D + timedelta(days=-1)).isoformat()}", "day", "x", (D + timedelta(days=-1)).isoformat(), "A quiet day.", "gist_ok", 1),
        (f"week_ENDING_{(D + timedelta(days=-1)).isoformat()}", "week", "x", (D + timedelta(days=-1)).isoformat(), "Early weeks.", "code_line_early", 0),
        (f"month_ENDING_{(D + timedelta(days=-20)).isoformat()}", "month", "x", (D + timedelta(days=-20)).isoformat(), "A steady month.", "gist_ok", 0)])
    conn.commit()
    conn.close()
    (d / "phrasebook.yaml").write_text(yaml.safe_dump(phrasebook(), sort_keys=False))
    (d / "findings.yaml").write_text(f"""
findings:
  method_version: fe-v0
  baseline_config: {d / 'baseline.yaml'}
  evidence_library: {d / 'library.yaml'}
  phrasebook: {d / 'phrasebook.yaml'}
  paths: {{state_db: {d / 'state.db'}, rulebook_db: {d / 'rulebook.db'}, evidence_db: {d / 'evidence.db'}, store_db: {d / 'store.db'}, db_path: {d / 'findings.db'}}}
  case: {{gap_hours: 6, max_span_hours: 36}}
  diary: {{stream: notes, max_entries: 3, start: previous_local_day, id_field: id, note_field: note, priority_up_to: moderate, library_source: diary, backing_per_point: 3}}
  state_memory: {{use: [yesterday_day, last_week, latest_month], windows: {{yesterday_day: "day_{{date}}", last_week: "week_ENDING_{{date}}", latest_month: {{tier: month}}}}, skip_statuses: [code_line_early], view: {{use: [yesterday_day], notable_only: true}}}}
  part_of_day: {{night: [0, 5], morning: [5, 12], afternoon: [12, 18], evening: [18, 24]}}
  text: {{enabled: true, model: "m", reasoning_effort: low, timeout_seconds: 90, sdk_retries: 0, retries: 1, concurrency: 2, headline_max_words: 20, sentences: {{min: 2, max: 8}}, copy_words: 7, cache: true}}
""")
    return d / "findings.yaml"
