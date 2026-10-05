"""The as-of audit (findings_engine_spec.md 4 and 13): for every stored version, nothing it refers to is later than its `as_of`. Checked from the stored records against the source
databases, independently of the code that wrote them: event evidence must have an event time at or before `as_of` and an outcome date no later than the local date of `as_of`;
completions must have been evaluated at or before it; relationship evidence dates must not pass the local date; diary entries must be timestamped at or before it; state-memory
windows must have ended before the local date. Returns the violations (an empty list is a pass)."""

import json
import sqlite3
from datetime import datetime

from v0_code.findings_engine.config import FindingsConfig


def audit_versions(versions: list[dict], cfg: FindingsConfig) -> tuple[list[str], dict]:
    ev = sqlite3.connect(f"file:{cfg.paths['evidence_db']}?mode=ro", uri=True)
    store = sqlite3.connect(f"file:{cfg.paths['store_db']}?mode=ro", uri=True)
    events = {r[0]: (r[1], r[2]) for r in ev.execute("SELECT evidence_id, event_time, as_of_date FROM event_evidence")}
    completions = {f"{r[0]}#{r[1]}": json.loads(r[2])["end"] for r in ev.execute("SELECT evidence_id, candidate, evaluated_from FROM event_completions")}
    diary = {}
    for ts, meta, row_id in store.execute("SELECT timestamp, meta_json, id FROM context_events WHERE stream = ?", (cfg.diary["stream"],)):
        diary[(json.loads(meta) if meta else {}).get(cfg.diary["id_field"]) or f"event_{row_id}"] = ts
    windows = {r[0]: r[1] for r in store.execute("SELECT window_id, end_date FROM memory_v2")}
    tz, bad, n = cfg.tz, [], {"evidence": 0, "relationship": 0, "completions": 0, "diary": 0, "state_memory": 0}
    for v in versions:
        as_of = datetime.fromisoformat(v["as_of"])
        local = as_of.astimezone(tz).date().isoformat()
        for eid in v["evidence_ids"]:
            n["evidence"] += 1
            t, d = events[eid]
            if datetime.fromisoformat(t) > as_of or d > local:
                bad.append(f"{v['finding_id']}: evidence {eid} (event {t}, outcome date {d}) is after as_of {v['as_of']}")
        for f in v["factors"]:
            for rid in f.get("relationship_evidence_ids", []):
                n["relationship"] += 1
                if rid.split("|")[2] > local:
                    bad.append(f"{v['finding_id']}: relationship evidence {rid} is dated after {local}")
        for cid in v["completion_ids"]:
            n["completions"] += 1
            if datetime.fromisoformat(completions[cid]) > as_of:
                bad.append(f"{v['finding_id']}: completion {cid} was evaluated at {completions[cid]}, after as_of {v['as_of']}")
        for d in v["refs"]["diary"]:
            n["diary"] += 1
            if datetime.fromisoformat(diary[d["context_id"]]) > as_of:
                bad.append(f"{v['finding_id']}: diary entry {d['context_id']} ({diary[d['context_id']]}) is after as_of {v['as_of']}")
        for s in v["refs"]["state_memory"]:
            n["state_memory"] += 1
            if windows[s["window_id"]] >= local:
                bad.append(f"{v['finding_id']}: state-memory window {s['window_id']} ends {windows[s['window_id']]}, not before {local}")
    ev.close()
    store.close()
    return bad, n
