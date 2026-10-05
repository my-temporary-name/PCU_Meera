"""Regression checks of the loop against the stored F1 / P1 results (stage L1, spec item 3). Everything here reads databases read-only.

- `compare_findings(f1_db, loop_db)`: version by version, the loop's record against F1's. Only `repeat` and `refs.pi_memories` may differ; any other difference is returned as a violation.
  Also counts what changed, by field.
- `before_first_memory(...)`: the versions written before the first long-term memory existed: everything but `refs.pi_memories` equals F1, `pi_status` is null, and each changed
  `seen_before` is explained by an entry of another case with that relationship in the open week (spec 13 counts the open week).
- `compare_pi(p1_db, loop_pi_db)`: PI's tables of the loop against a P1 (code-only) run, table by table.
- `final_statuses(db)`: the last status of every long-term memory."""

import json
import sqlite3
from datetime import datetime

P1_TABLES = ("pi_mid_memories", "pi_mid_entries", "pi_entry_keys", "pi_long_memories", "pi_weekly_runs")


def _ro(path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def records(db) -> dict:
    c = _ro(db)
    out = {r[0]: json.loads(r[1]) for r in c.execute("SELECT finding_id, record_json FROM findings ORDER BY finding_id")}
    c.close()
    return out


def _structured(r: dict) -> dict:
    """A record without the fields the loop may change."""
    return {**{k: v for k, v in r.items() if k not in ("repeat", "refs")}, "refs": {k: v for k, v in r["refs"].items() if k != "pi_memories"}}


def compare_findings(f1_db, loop_db) -> dict:
    a, b = records(f1_db), records(loop_db)
    out = {"f1": len(a), "loop": len(b), "same_ids": set(a) == set(b), "violations": [], "changed": {"repeat.pi_status": 0, "repeat.seen_before": 0, "refs.pi_memories": 0, "any": 0}, "versions_changed": set()}
    for fid in sorted(set(a) & set(b)):
        x, y = a[fid], b[fid]
        if json.dumps(_structured(x), sort_keys=True) != json.dumps(_structured(y), sort_keys=True):
            out["violations"].append(fid)
        if [r["relationship_key"] for r in x["repeat"]] != [r["relationship_key"] for r in y["repeat"]]:
            out["violations"].append(fid)
            continue
        ch = False
        for rx, ry in zip(x["repeat"], y["repeat"]):
            for f in ("pi_status", "seen_before"):
                if rx[f] != ry[f]:
                    out["changed"][f"repeat.{f}"] += 1
                    ch = True
        if x["refs"]["pi_memories"] != y["refs"]["pi_memories"]:
            out["changed"]["refs.pi_memories"] += 1
            ch = True
        if ch:
            out["versions_changed"].add(fid)
    out["changed"]["any"] = len(out["versions_changed"])
    out["violations"] = sorted(set(out["violations"]))
    return out


def first_memory_time(pi_db) -> str | None:
    c = _ro(pi_db)
    r = c.execute("SELECT MIN(written_at) FROM pi_long_memories").fetchone()[0]
    c.close()
    return r


def before_first_memory(f1_db, loop_db, pi_db) -> dict:
    """The versions written before the first long-term memory existed."""
    a, b = records(f1_db), records(loop_db)
    first = datetime.fromisoformat(first_memory_time(pi_db))
    pi = _ro(pi_db)
    out = {"first_memory": first.isoformat(), "versions": 0, "identical_but_pi_memories": 0, "pi_status_not_null": [], "other_difference": [], "seen_before_changed": [], "unexplained": [], "long_term_refs": 0}
    for fid, x in sorted(a.items()):
        if datetime.fromisoformat(x["as_of"]) >= first:
            continue
        y = b[fid]
        out["versions"] += 1
        out["long_term_refs"] += sum(r["tier"] == "long_term" for r in y["refs"]["pi_memories"])
        out["pi_status_not_null"] += [fid] * sum(r["pi_status"] is not None for r in y["repeat"])
        if json.dumps(_structured(x), sort_keys=True) != json.dumps(_structured(y), sort_keys=True):
            out["other_difference"].append(fid)
        if x["repeat"] == y["repeat"]:
            out["identical_but_pi_memories"] += 1
            continue
        out["seen_before_changed"].append(fid)
        t = int(datetime.fromisoformat(x["as_of"]).timestamp())
        for rx, ry in zip(x["repeat"], y["repeat"]):
            if rx["seen_before"] != ry["seen_before"]:
                n = pi.execute("SELECT COUNT(*) FROM pi_entry_keys k JOIN pi_mid_entries e ON e.finding_id = k.finding_id WHERE k.relationship_key = ? AND e.written_ts <= ? AND e.case_id != ?",
                               (ry["relationship_key"], t, x["case_id"])).fetchone()[0]
                if n == 0:
                    out["unexplained"].append(fid)
    pi.close()
    return out


def compare_pi(p1_db, loop_pi_db) -> dict:
    a, b = _ro(p1_db), _ro(loop_pi_db)
    out = {}
    for t in P1_TABLES:
        ra, rb = a.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall(), b.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall()
        out[t] = {"p1": len(ra), "loop": len(rb), "identical": ra == rb, "different_rows": sum(1 for x, y in zip(ra, rb) if x != y) + abs(len(ra) - len(rb))}
    a.close()
    b.close()
    return out


def final_statuses(pi_db) -> dict:
    c = _ro(pi_db)
    rows = c.execute("SELECT relationship_key, status FROM pi_long_memories m WHERE version = (SELECT MAX(version) FROM pi_long_memories WHERE memory_id = m.memory_id) ORDER BY relationship_key").fetchall()
    c.close()
    return dict(rows)


def status_transitions(pi_db) -> list:
    c = _ro(pi_db)
    rows = c.execute("SELECT relationship_key, version, status, written_at FROM pi_long_memories ORDER BY relationship_key, version").fetchall()
    c.close()
    return rows
