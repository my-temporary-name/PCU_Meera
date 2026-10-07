"""The L2 audit of model-call ordering (independent of the writer): it reads the run's call log (`meta.l2_call_log` of the L2 Findings database) and the two databases, and checks that

- the barriers ran in order and each in the order texts, entry texts, weekly job, situations lines (monotonic times);
- every weekly job time is later than every version of its week;
- a Findings text that cites an earlier conclusion was written in a barrier AFTER the barrier whose job wrote the memory version it cites, and after that version's situations line was resolved;
- a PI situations line was built only from entries whose Findings texts were written in its own barrier or an earlier one, and whose time is not after the job;
- the final text of every PI entry is the Findings text stored for its version.

Barriers finished in an earlier run are not in the log; a version that cites such a memory is counted as `unlogged`, not as a violation."""

import json
import sqlite3
from datetime import datetime


def _ro(path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def audit_call_log(findings_db, pi_db, log: dict | None = None) -> tuple[list[str], dict]:
    f, p = _ro(findings_db), _ro(pi_db)
    if log is None:
        row = f.execute("SELECT value FROM meta WHERE key = 'l2_call_log'").fetchone()
        log = json.loads(row[0]) if row else {"barriers": [], "calls": []}
    bad: list[str] = []
    n = {"barriers": len(log["barriers"]), "findings_texts": 0, "pi_lines": 0, "p_refs": 0, "unlogged": 0, "entries": 0}
    records = {r[0]: json.loads(r[1]) for r in f.execute("SELECT finding_id, record_json FROM findings")}
    barriers = {b["barrier"]: b for b in log["barriers"]}
    by_job = {b["job_time"]: b for b in log["barriers"]}
    prev = None
    for b in sorted(log["barriers"], key=lambda x: x["barrier"]):
        t = [b["texts_start"], b["texts_end"], b["job_at"], b["lines_start"], b["lines_end"]]
        if t != sorted(t):
            bad.append(f"barrier {b['barrier']} ({b['week']}): the phases are out of order {t}")
        if prev is not None and b.get("run") == prev.get("run") and b["texts_start"] < prev["lines_end"]:             # times are only comparable within one run
            bad.append(f"barrier {b['barrier']} ({b['week']}) started before barrier {prev['barrier']} had finished")
        for fid in b["versions"]:
            if datetime.fromisoformat(records[fid]["as_of"]) > datetime.fromisoformat(b["job_time"]):
                bad.append(f"{fid} (as_of {records[fid]['as_of']}) is later than the job time {b['job_time']} of its barrier")
        prev = b
    text_barrier = {}
    for c in log["calls"]:
        if c["phase"] == "findings_text":
            n["findings_texts"] += 1
            text_barrier[c["id"]] = c["barrier"]
        else:
            n["pi_lines"] += 1
    lines_done = {c["id"]: c["barrier"] for c in log["calls"] if c["phase"] == "pi_line"}
    for c in log["calls"]:
        if c["phase"] == "findings_text":
            for ref in records[c["id"]]["refs"]["pi_memories"]:
                if ref["tier"] != "long_term" or "view_id" not in ref:
                    continue
                n["p_refs"] += 1
                b = by_job.get(ref["written_at"])
                if b is None:
                    n["unlogged"] += 1
                    continue
                if b["barrier"] >= c["barrier"]:
                    bad.append(f"{c['id']}: text written in barrier {c['barrier']} cites memory {ref['memory_id']} version {ref['version']} written by the job of barrier {b['barrier']}")
                key = f"{ref['memory_id']}#{ref['version']}"
                if key not in lines_done or lines_done[key] >= c["barrier"]:
                    bad.append(f"{c['id']}: the situations line of {key} was not resolved before barrier {c['barrier']}")
        else:
            b = barriers.get(c["barrier"])
            for fid in c["entry_ids"]:
                if fid in text_barrier and text_barrier[fid] > c["barrier"]:
                    bad.append(f"{c['id']}: built from entry {fid}, whose text was written in a later barrier")
                if b and datetime.fromisoformat(records[fid]["as_of"]) > datetime.fromisoformat(b["job_time"]):
                    bad.append(f"{c['id']}: built from entry {fid}, which is later than the job time")
    texts = {r[0]: json.loads(r[1]) for r in f.execute("SELECT finding_id, text_json FROM finding_text")}
    for fid, entry_json in p.execute("SELECT finding_id, entry_json FROM pi_mid_entries"):
        n["entries"] += 1
        e, t = json.loads(entry_json), texts.get(fid)
        if t is None:
            bad.append(f"{fid}: a PI entry has no Findings text")
        elif e["headline"] != t["headline"] or e["sentences"] != [s["text"] if isinstance(s, dict) else s for s in t["sentences"]]:
            bad.append(f"{fid}: the PI entry text is not the Findings text")
    f.close()
    p.close()
    return bad, n
