"""Shared test builders for the PI tests: a small Evidence store with chosen daily labels, a PI config built in code, and finding records."""

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from v0_code.evidence_engine.library import load_library
from v0_code.intel_common.phrasebook import Phrasebook
from v0_code.pi_engine.config import PiConfig
from v0_code.pi_engine.labels import EvidenceLabels, LabelCfg
from v0_code.pi_engine.lifecycle import LifecycleCfg

ROOT = Path(__file__).resolve().parent.parent
LIB = load_library(ROOT / "config/evidence_library_v0.yaml")
PB = Phrasebook.load(ROOT / "config/findings_phrasebook_v0.yaml")
SLEEP = "sleep_hours@prev_night->post_meal_peak:dinner"
MISSED = "missed_dose@2d->post_meal_peak:dinner"
STRESS = "strained_period@1d->post_meal_peak:dinner"
START = date(2026, 3, 2)                       # a Monday
DAYS = 8 * 7 + 3                                # eight full weeks and a three-day tail (Mon 2 Mar to Wed 29 Apr)


def make_cfg(tmp_path, timezone="Asia/Kolkata", **over):
    life = dict(promote_after=2, weaken_after=2, retract_after=6, contrary_days=5, contrary_of=7, contrary_weeks=4, repromote_after=2, placebo_max_share=0.5, min_days=4, scale=True)
    life.update(over.pop("lifecycle", {}))
    return PiConfig(method_version="pi-v0", patient_id="t", timezone=timezone, label=LabelCfg(5, 7, 4, True), lifecycle=LifecycleCfg(**life), seen_before_bands={"this_week_days": 7, "recent_weeks_days": 28},
                    regenerate_every_weeks=4, text={"enabled": False}, replay={"mode": "full"}, version="test",
                    paths={"findings_db": str(tmp_path / "f.db"), "evidence_db": str(tmp_path / "ev.db"), "evidence_library": str(ROOT / "config/evidence_library_v0.yaml"),
                           "phrasebook": str(ROOT / "config/findings_phrasebook_v0.yaml"), "baseline_config": "", "db_path": str(tmp_path / "pi.db")}, **over)


def make_evidence(tmp_path, keys: dict, start=START, n_days=DAYS):
    """keys: relationship_key -> function(day_index) -> (support, flags); plus a key that gives every day a record so the data span is the whole range."""
    p = tmp_path / "ev.db"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE relationship_evidence (id INTEGER PRIMARY KEY AUTOINCREMENT, evidence_id TEXT, relationship_key TEXT, as_of_date TEXT, method_version TEXT, config_version TEXT, inputs_hash TEXT, "
              "status TEXT, record_json TEXT)")
    rows = []
    allkeys = {"span_key@1d->x": lambda i: ("insufficient", []), **keys}
    for key, fn in allkeys.items():
        for i in range(n_days):
            d = start + timedelta(days=i)
            got = fn(i)
            if got is None:
                continue
            sup, flags = got
            rows.append((f"rel|{key}|{d.isoformat()}|ev-v0", key, d.isoformat(), "ev-v0", "c", f"h{i}", "current", json.dumps({"support": sup, "flags": flags, "as_of_date": d.isoformat()})))
    c.executemany("INSERT INTO relationship_evidence (evidence_id, relationship_key, as_of_date, method_version, config_version, inputs_hash, status, record_json) VALUES (?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()
    return EvidenceLabels(p)


def weekly(pattern, **kw):
    """A day-label function from one label per week (days 0-6 week one, ...); the last pattern entry repeats."""
    def fn(i):
        label = pattern[min(i // 7, len(pattern) - 1)]
        return (label, kw.get("flags", []))
    return fn


def finding(case_id, version, as_of, local_date, relationships, mode="relationship", headline="A headline.", sentences=("One sentence.",), source="llm"):
    """relationships: list of (key, label, exposure_state, flags)."""
    factors = []
    for n, (key, label, exposure, flags) in enumerate(relationships, 1):
        factors.append({"factor_id": f"f{n}", "candidate": "c", "kind": "relationship", "relationship_key": key, "label": label, "flags": list(flags), "exposure": exposure, "wording_class": "asserted"})
    factors.append({"factor_id": f"f{len(factors) + 1}", "candidate": "meal_composition", "kind": "event", "relationship_key": None, "label": "supported", "flags": [], "exposure": "exposed", "wording_class": "event_unusual"})
    factors.append({"factor_id": f"f{len(factors) + 1}", "candidate": "c", "kind": "relationship", "relationship_key": "not_usable@1d->x", "label": "not_supported", "flags": [], "exposure": "exposed", "wording_class": "exposure_only"})
    return {"finding_id": f"fnd_{case_id}_v{version}", "case_id": case_id, "version": version, "as_of": as_of, "local_date": local_date, "mode": mode, "factors": factors,
            "text": {"headline": headline, "sentences": [{"text": s, "refs": []} for s in sentences], "source": source}}


def make_findings_db(tmp_path, versions, cases=()):
    """A Findings-shaped database: `versions` = list of (finding record, final text dict or None); `cases` = list of dicts for the cases table."""
    from v0_code.findings_engine.storage import FindingsStore
    s = FindingsStore(tmp_path / "f.db")
    for rec, final in versions:
        full = {**rec, "provisional": True, "closed": False, "status": "ok"}
        full["text"] = {**rec["text"], "source": "code_line"}
        s.put_finding(full)
        if final is not None:
            s.put_text(rec["finding_id"], f"key_{rec['finding_id']}", "vh", {"text": final, "text_source": final["source"], "status": "ok", "llm_raw": [], "usage": [], "checks": [],
                                                                                "prompt_version": "p-v3", "checks_version": "ck-v5.2", "settings_key": "s"})
    for c in cases:
        s.conn.execute("INSERT INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (c["case_id"], c["local_date"], c["opened_at"], c["last_handoff_at"], c["closed_at"], "closed", 1, 0, 1))
    s.conn.commit()
    s.close()
