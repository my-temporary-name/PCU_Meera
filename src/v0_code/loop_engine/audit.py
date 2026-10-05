"""The as-of audit of the loop's PI reads (stage L1, independent of the writer). It reads only the stored Findings records and PI's database with its own SQL (not PI's retrieval code) and
checks, for every stored version (`strict`: against what was written strictly before `as_of`, as the loop reads; otherwise at or before):

- `repeat`: `pi_status` is the status of the latest long-term version written at or before the version's `as_of` (null if none); `seen_before` is the band recomputed from the entries
  written at or before `as_of` (other cases only) and the long-term memory's case days;
- `refs.pi_memories`, long-term: the version named exists, was written at or before `as_of`, is the latest such version, and has the status named;
- the open week: it is the week of `as_of`; every entry listed was written at or before `as_of` and belongs to that week; exactly the latest entry of each case written by then is listed;
- the sealed weeks: sealed at or before `as_of`, and they are the latest `recent_weeks` sealed weeks by then.

Returns the violations (an empty list is a pass) and the counts of what was checked. The evidence and diary reads of the same versions are checked by the Findings audit
(`findings_engine.audit.audit_versions`)."""

import json
import sqlite3
from datetime import date, datetime


def _ro(path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _band(days: int, bands: dict) -> str:
    return "this_week" if days <= bands["this_week_days"] else "recent_weeks" if days <= bands["recent_weeks_days"] else "earlier"


def audit_pi_reads(findings_db, pi_db, tz, bands: dict, recent_weeks: int, include_open_week: bool = True, strict: bool = True) -> tuple[list[str], dict]:
    f, p = _ro(findings_db), _ro(pi_db)
    bad: list[str] = []
    n = {"versions": 0, "repeat": 0, "long_term": 0, "open_week": 0, "sealed": 0}
    for finding_id, case_id, as_of, rj in f.execute("SELECT finding_id, case_id, as_of, record_json FROM findings ORDER BY as_of, finding_id"):
        v = json.loads(rj)
        when = datetime.fromisoformat(as_of)
        t, local = int(when.timestamp()) - (1 if strict else 0), when.astimezone(tz).date()          # strict: only what was written strictly before as_of (whole seconds)
        year, week, _ = local.isocalendar()
        week_id = f"pi_mid_{year}-W{week:02d}"
        n["versions"] += 1
        for r in v["repeat"]:
            n["repeat"] += 1
            key = r["relationship_key"]
            row = p.execute("SELECT status FROM pi_long_memories WHERE relationship_key = ? AND written_ts <= ? ORDER BY version DESC LIMIT 1", (key, t)).fetchone()
            if r["pi_status"] != (row[0] if row else None):
                bad.append(f"{finding_id}: pi_status of {key} is {r['pi_status']!r}, the latest memory written by {as_of} says {row[0] if row else None!r}")
            dates = []
            d = p.execute("SELECT MAX(e.local_date) FROM pi_entry_keys k JOIN pi_mid_entries e ON e.finding_id = k.finding_id WHERE k.relationship_key = ? AND e.written_ts <= ? AND e.case_id != ?",
                          (key, t, case_id)).fetchone()[0]
            if d:
                dates.append(d)
            last = p.execute("SELECT record_json FROM pi_long_memories WHERE relationship_key = ? AND written_ts <= ? ORDER BY version DESC LIMIT 1", (key, t)).fetchone()
            if last:
                dates += [day for day, cases in json.loads(last[0])["dates"]["case_days"].items() if set(cases) != {case_id}]
            expected = _band((local - date.fromisoformat(max(dates))).days, bands) if dates else "none"
            if r["seen_before"] != expected:
                bad.append(f"{finding_id}: seen_before of {key} is {r['seen_before']!r}, recomputed from what was written by {as_of}: {expected!r}")
        listed_open = False
        sealed_ids = []
        for ref in v["refs"]["pi_memories"]:
            if ref["tier"] == "long_term":
                n["long_term"] += 1
                row = p.execute("SELECT written_ts, status FROM pi_long_memories WHERE memory_id = ? AND version = ?", (ref["memory_id"], ref["version"])).fetchone()
                if row is None:
                    bad.append(f"{finding_id}: memory {ref['memory_id']} version {ref['version']} does not exist")
                    continue
                if row[0] > t:
                    bad.append(f"{finding_id}: memory {ref['memory_id']} version {ref['version']} was written after as_of {as_of}")
                newest = p.execute("SELECT MAX(version) FROM pi_long_memories WHERE memory_id = ? AND written_ts <= ?", (ref["memory_id"], t)).fetchone()[0]
                if newest != ref["version"]:
                    bad.append(f"{finding_id}: memory {ref['memory_id']} version {ref['version']} is not the latest version written by {as_of} ({newest})")
                if row[1] != ref["status"]:
                    bad.append(f"{finding_id}: memory {ref['memory_id']} version {ref['version']} has status {row[1]!r}, the ref says {ref['status']!r}")
            elif ref["status"] == "open":
                n["open_week"] += 1
                listed_open = True
                if ref["memory_id"] != week_id:
                    bad.append(f"{finding_id}: the open week read is {ref['memory_id']}, the week of {as_of} is {week_id}")
                for fid in ref["finding_ids"]:
                    row = p.execute("SELECT written_ts, memory_id FROM pi_mid_entries WHERE finding_id = ?", (fid,)).fetchone()
                    if row is None or row[0] > t or row[1] != week_id:
                        bad.append(f"{finding_id}: open week entry {fid} was not written by {as_of} in {week_id}")
                expected = [r[0] for r in p.execute("SELECT finding_id FROM pi_mid_entries e WHERE memory_id = ? AND written_ts <= ? AND entry_version = (SELECT MAX(entry_version) FROM pi_mid_entries "
                                                    "WHERE memory_id = e.memory_id AND case_id = e.case_id AND written_ts <= ?)", (week_id, t, t))]
                if sorted(ref["finding_ids"]) != sorted(expected):
                    bad.append(f"{finding_id}: the open week entries listed differ from the latest entry of each case written by {as_of} (missing {sorted(set(expected) - set(ref['finding_ids']))}, "
                               f"not allowed {sorted(set(ref['finding_ids']) - set(expected))})")
            else:
                n["sealed"] += 1
                sealed_ids.append(ref["memory_id"])
                row = p.execute("SELECT written_ts, sealed_at FROM pi_mid_memories WHERE memory_id = ? AND status = 'sealed'", (ref["memory_id"],)).fetchone()
                if row is None or row[0] > t:
                    bad.append(f"{finding_id}: sealed week {ref['memory_id']} was not sealed by {as_of}")
        expected_open = p.execute("SELECT COUNT(*) FROM pi_mid_entries WHERE memory_id = ? AND written_ts <= ?", (week_id, t)).fetchone()[0]
        if include_open_week and expected_open and not listed_open:
            bad.append(f"{finding_id}: the open week {week_id} has entries written by {as_of} but the version lists none")
        latest = [r[0] for r in p.execute("SELECT memory_id FROM pi_mid_memories WHERE status = 'sealed' AND written_ts <= ? ORDER BY week_start DESC LIMIT ?", (t, recent_weeks))]
        if sorted(sealed_ids) != sorted(latest):
            bad.append(f"{finding_id}: the sealed weeks listed {sorted(sealed_ids)} are not the latest {recent_weeks} sealed by {as_of}: {sorted(latest)}")
        ids = [r["view_id"] for r in v["refs"]["pi_memories"] if "view_id" in r]
        if ids != [f"p{i}" for i in range(1, len(ids) + 1)]:
            bad.append(f"{finding_id}: view ids {ids} are not p1, p2, ... in order")
    f.close()
    p.close()
    return bad, n
