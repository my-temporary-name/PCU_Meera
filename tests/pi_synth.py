"""A second synthetic patient for PI (UTC+9, other library ids, other phrases, other relationship keys): everything PI needs is written from config and data, nothing in the engine."""

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import yaml

import evidence_synth as syn
import findings_synth as fsyn
from pi_helpers import finding, make_findings_db

KEY_A = "pill_skip@2d->meal_peak:supper"
KEY_B = "rest_hours@prev_night->day_level"
D0 = date(2026, 5, 4)                                   # a Monday
N_DAYS = 6 * 7 + 4


def make_pi_patient(d) -> Path:
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "baseline.yaml").write_text(syn.BASELINE)
    (d / "library.yaml").write_text(syn.LIBRARY)
    (d / "phrasebook.yaml").write_text(yaml.safe_dump(fsyn.phrasebook(), sort_keys=False))
    c = sqlite3.connect(d / "evidence.db")
    c.execute("CREATE TABLE relationship_evidence (id INTEGER PRIMARY KEY AUTOINCREMENT, evidence_id TEXT, relationship_key TEXT, as_of_date TEXT, method_version TEXT, config_version TEXT, inputs_hash TEXT, "
              "status TEXT, record_json TEXT)")
    rows = []
    for key, pattern in ((KEY_A, ["supported"] * 3 + ["not_supported"] * 3 + ["suggestive"]), (KEY_B, ["supported", "supported", "suggestive", "suggestive", "supported", "supported", "supported"])):
        for i in range(N_DAYS):
            day = D0 + timedelta(days=i)
            lab = pattern[min(i // 7, len(pattern) - 1)]
            rows.append((f"rel|{key}|{day.isoformat()}|ev-v0", key, day.isoformat(), "ev-v0", "c", f"h{i}", "current", json.dumps({"support": lab, "flags": ["same_day_unverified"] if key == KEY_A else [], "as_of_date": day.isoformat()})))
    c.executemany("INSERT INTO relationship_evidence (evidence_id, relationship_key, as_of_date, method_version, config_version, inputs_hash, status, record_json) VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()
    at = lambda off, hh=12, mm=0: f"{(D0 + timedelta(days=off)).isoformat()}T{hh:02d}:{mm:02d}:00+09:00"
    vs = [finding("case_one", 1, at(2), (D0 + timedelta(days=2)).isoformat(), [(KEY_A, "supported", "exposed", ["same_day_unverified"]), (KEY_B, "suggestive", "not_exposed", [])]),
          finding("case_two", 1, at(9), (D0 + timedelta(days=9)).isoformat(), [(KEY_B, "supported", "exposed", [])]),
          finding("case_three", 1, at(6, 23, 40), (D0 + timedelta(days=6)).isoformat(), [(KEY_A, "supported", "exposed", [])]),
          finding("case_three", 2, at(7, 0, 20), (D0 + timedelta(days=6)).isoformat(), [(KEY_A, "supported", "exposed", [])]),
          finding("case_four", 1, at(N_DAYS - 2), (D0 + timedelta(days=N_DAYS - 2)).isoformat(), [(KEY_A, "supported", "exposed", [])])]
    make_findings_db(d, [(r, None) for r in vs])
    (d / "pi.yaml").write_text(f"""
pi:
  method_version: pi-v0
  baseline_config: {d / 'baseline.yaml'}
  evidence_library: {d / 'library.yaml'}
  phrasebook: {d / 'phrasebook.yaml'}
  paths: {{findings_db: {d / 'f.db'}, evidence_db: {d / 'evidence.db'}, db_path: {d / 'pi.db'}}}
  week: {{start_day: monday, close_at: "23:59:59", partial_week: {{min_days: 4, scale_threshold: true}}}}
  week_label: {{days_needed: 5, of: 7}}
  lifecycle: {{promote_after_weeks: 2, weaken_after_weeks: 2, retract_after_weeks: 6, retract_on_contrary: {{days_per_week: 5, weeks: 4}}, repromote_after_weeks: 2, placebo_fired_max_share: 0.5, backfill_on_create: true}}
  seen_before_bands: {{this_week_days: 7, recent_weeks_days: 28}}
  text: {{enabled: false, regenerate_every_weeks: 4}}
  replay: {{mode: code_only}}
""")
    return d / "pi.yaml"
