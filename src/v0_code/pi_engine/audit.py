"""The as-of audit of a PI database, written independently of the engine (pi_spec.md 14, properties 3, 9, 10 and 14): it re-derives from the source databases and compares. It does
not import the engine's lifecycle or label code. It checks that every entry sits in the week of its as_of, that no weekly label or evidence ref reads a day later than the week it
belongs to (and so later than the job that wrote it), that the labels, statuses and counters re-derived here equal the stored ones, and that every week has exactly one run.
Returns (violations, counts); an empty list is a pass."""

import json
import math
import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path

DEC = ("supported", "not_supported")


def _week(d: date) -> tuple[str, date, date]:
    y, n, _ = d.isocalendar()
    mon = d - timedelta(days=d.weekday())
    return f"{y}-W{n:02d}", mon, mon + timedelta(days=6)


def _need(days: int, cfg) -> int:
    return math.ceil(cfg.label.days_needed * days / cfg.label.of) if cfg.label.scale else cfg.label.days_needed


def _label(c: dict, cfg) -> str:
    if c["days"] < cfg.label.min_days:
        return "insufficient"
    need = _need(c["days"], cfg)
    return "supported" if c["sup"] >= need else "suggestive" if c["sup"] + c["sug"] >= need else "insufficient" if c["ins"] >= need else "not_supported"


def _status(labels: list[dict], cfg) -> tuple[str, str | None, list]:
    """A second, compact implementation of the lifecycle over stored weekly labels."""
    L = cfg.lifecycle
    status, since, hist, run_label, run, ns, contrary, runweeks = "candidate", None, [], None, 0, 0, 0, []
    for w in labels:
        lab = w["label"]
        if lab in DEC:
            if lab == run_label:
                run += 1
                runweeks.append(w)
            else:
                run_label, run, runweeks = lab, 1, [w]
        was = status
        if was == "weakened":
            ok = w["days_in_week"] >= L.min_days and w["contrary_days"] >= (math.ceil(L.contrary_days * w["days_in_week"] / L.contrary_of) if L.scale else L.contrary_days)
            contrary = contrary + 1 if ok else 0
            ns = ns + 1 if lab == "not_supported" else 0 if lab == "supported" else ns
        move = None
        if was == "candidate":
            last = runweeks[-L.promote_after:]
            days = sum(x["days_in_week"] for x in last)
            if run_label == "supported" and run >= L.promote_after and days and sum(x["placebo_days"] for x in last) / days < L.placebo_max_share:
                move = "supported"
        elif was == "supported":
            if run_label == "not_supported" and run >= L.weaken_after:
                move = "weakened"
        elif was == "weakened":
            if run_label == "supported" and run >= L.repromote_after:
                move = "supported"
            elif ns >= L.retract_after or contrary >= L.contrary_weeks:
                move = "retracted"
        elif was == "retracted":
            if run_label == "supported" and run >= L.repromote_after:
                move = "candidate"
        if move:
            hist.append({"week": w["week"], "from": was, "to": move})
            status, since = move, w["_end"]
            if move == "weakened":
                ns = contrary = 0
    return status, since, hist


def audit_pi(pi_db: str | Path, evidence_db: str | Path, findings_db: str | Path, cfg) -> tuple[list[str], dict]:
    pi = sqlite3.connect(f"file:{pi_db}?mode=ro", uri=True)
    ev = sqlite3.connect(f"file:{evidence_db}?mode=ro", uri=True)
    fd = sqlite3.connect(f"file:{findings_db}?mode=ro", uri=True)
    tz, bad = cfg.tz, []
    n = {"entries": 0, "versions": 0, "labels": 0, "evidence_days_read": 0, "evidence_refs": 0, "runs": 0, "statuses": 0, "counters": 0}
    lo, hi = ev.execute("SELECT MIN(as_of_date), MAX(as_of_date) FROM relationship_evidence WHERE status='current'").fetchone()
    first, last = date.fromisoformat(lo), date.fromisoformat(hi)
    # ---- entries: the week of the as_of; written at the as_of; the same finding as in the Findings database
    fin = {r[0]: (r[1], r[2], r[3]) for r in fd.execute("SELECT finding_id, case_id, version, as_of FROM findings")}
    entries = []
    for fid, mid, case, ver, ld, wat, wts, ej in pi.execute("SELECT finding_id, memory_id, case_id, entry_version, local_date, written_at, written_ts, entry_json FROM pi_mid_entries"):
        n["entries"] += 1
        e = json.loads(ej)
        as_of = datetime.fromisoformat(e["as_of"])
        wk = _week(as_of.astimezone(tz).date())[0]
        if mid != f"pi_mid_{wk}":
            bad.append(f"entry {fid} is in {mid} but its as_of {e['as_of']} is in {wk}")
        if int(as_of.timestamp()) != wts or wat != e["as_of"]:
            bad.append(f"entry {fid} was written at {wat}, not at its as_of {e['as_of']}")
        if fid not in fin or fin[fid][0] != case or fin[fid][1] != ver or fin[fid][2] != e["as_of"]:
            bad.append(f"entry {fid} does not match the Findings version")
        entries.append((mid, case, ver, wts, e))
    # ---- runs: one per week from the first to the last week of the data; the last at the end of the data
    runs = {w: (t, json.loads(j)) for w, t, j in pi.execute("SELECT week, written_ts, record_json FROM pi_weekly_runs")}
    n["runs"] = len(runs)
    expected, d = [], _week(first)[1]
    while d <= last:
        expected.append(_week(d)[0])
        d += timedelta(days=7)
    if sorted(runs) != sorted(expected):
        bad.append(f"weekly runs {len(runs)} do not match the weeks of the data {len(expected)}")
    ends = {}
    for w in expected:
        _, mon, sun = _week(mon_of(w))
        end_day = min(sun, last)
        ends[w] = end_day
        if w in runs and runs[w][1]["written_at"] != datetime.combine(end_day, time(23, 59, 59), tzinfo=tz).isoformat():
            bad.append(f"run {w} was written at {runs[w][1]['written_at']}, not at the end of {end_day}")
    sealed = {mid: (ts_, sa) for mid, ts_, sa in pi.execute("SELECT memory_id, written_ts, sealed_at FROM pi_mid_memories WHERE status = 'sealed'")}
    for mid, case, ver, wts, e in entries:
        if mid in sealed and wts > sealed[mid][0]:
            bad.append(f"entry {e['finding_id']} was written after its week was sealed")
    # ---- long-term versions
    daily = {}

    def days(key):
        if key not in daily:
            daily[key] = {date.fromisoformat(a): (json.loads(j).get("support"), json.loads(j).get("flags") or []) for a, j in
                          ev.execute("SELECT as_of_date, record_json FROM relationship_evidence WHERE relationship_key = ? AND status='current'", (key,))}
        return daily[key]

    by_key = {}
    for key, ver, wts, wat, rj in pi.execute("SELECT relationship_key, version, written_ts, written_at, record_json FROM pi_long_memories ORDER BY relationship_key, version"):
        by_key.setdefault(key, []).append((ver, wts, wat, json.loads(rj)))
    for key, versions in by_key.items():
        for ver, wts, wat, m in versions:
            n["versions"] += 1
            wdate = datetime.fromisoformat(wat).astimezone(tz).date()
            if m["version"] != ver or m["written_at"] != wat:
                bad.append(f"{key} version {ver}: record and row disagree")
            labels = []
            for lab in m["weekly_labels"]:
                n["labels"] += 1
                y, wn = lab["week"].split("-W")
                mon = date.fromisocalendar(int(y), int(wn), 1)
                sun = mon + timedelta(days=6)
                lo_d, hi_d = max(mon, first), min(sun, last, wdate)
                if mon > wdate:
                    bad.append(f"{key} version {ver}: weekly label {lab['week']} reads days after the job that wrote it ({wat})")
                c = {"days": 0, "sup": 0, "sug": 0, "ns": 0, "ins": 0, "placebo": 0, "contrary": 0, "rec": 0}
                dd = lo_d
                while dd <= hi_d:
                    got = days(key).get(dd)
                    s, f = got if got else ("insufficient", [])
                    c["days"] += 1
                    c["rec"] += got is not None
                    c["sup"] += s == "supported"
                    c["sug"] += s == "suggestive"
                    c["ns"] += s == "not_supported"
                    c["ins"] += s not in ("supported", "suggestive", "not_supported")
                    c["placebo"] += "placebo_fired" in f
                    c["contrary"] += "contrary" in f
                    dd += timedelta(days=1)
                n["evidence_days_read"] += c["days"]
                if (lab["label"], lab["days_in_week"], lab["days_supported"], lab["placebo_days"], lab["contrary_days"], lab["days_with_record"]) != (_label(c, cfg), c["days"], c["sup"], c["placebo"], c["contrary"], c["rec"]):
                    bad.append(f"{key} version {ver}: weekly label {lab['week']} is not what the Evidence daily labels give")
                labels.append({**lab, "_end": min(sun, last).isoformat()})
            st, since, hist = _status(labels, cfg)
            n["statuses"] += 1
            if (m["status"], m["status_since"], m["status_history"]) != (st, since, hist):
                bad.append(f"{key} version {ver}: status {m['status']} / {m['status_since']} does not follow from its weekly labels ({st} / {since})")
            # evidence refs: one per decisive week, the last day with a record, never after the job
            want = []
            for lab in m["weekly_labels"]:
                if lab["label"] in DEC:
                    y, wn = lab["week"].split("-W")
                    mon = date.fromisocalendar(int(y), int(wn), 1)
                    cand = [dd for dd in days(key) if mon <= dd <= min(mon + timedelta(days=6), wdate)]
                    if cand:
                        want.append(f"rel|{key}|{max(cand).isoformat()}|ev-v0")
            n["evidence_refs"] += len(m["evidence_refs"])
            if m["evidence_refs"] != want:
                bad.append(f"{key} version {ver}: evidence_refs differ from the last record of each decisive week")
            for r in m["evidence_refs"]:
                if date.fromisoformat(r.split("|")[2]) > wdate:
                    bad.append(f"{key} version {ver}: evidence ref {r} is after the job that wrote it")
            # counters from the latest entry of each case of each week, written at or before this version
            cd, ed, wks = {}, {}, set()
            latest = {}
            for mid, case, ev_ver, ets, e in entries:
                if ets <= wts and mid in sealed and sealed[mid][0] <= wts:                      # only weeks whose job had run by then
                    k2 = (mid, case)
                    if k2 not in latest or ev_ver > latest[k2][0]:
                        latest[k2] = (ev_ver, e)
            for (mid, case), (_, e) in latest.items():
                for r in e["relationships"]:
                    if r["relationship_key"] == key:
                        cd.setdefault(e["local_date"], set()).add(case)
                        if r["exposed"]:
                            ed.setdefault(e["local_date"], set()).add(case)
                        wks.add(mid)
            n["counters"] += 1
            got = m["counters"]
            ds = sorted(cd)
            if (got["case_days"], got["exposed_case_days"], got["first_seen"], got["last_seen"], got["weeks_seen"]) != (len(cd), len(ed), ds[0] if ds else None, ds[-1] if ds else None, len(wks)):
                bad.append(f"{key} version {ver}: counters {got} do not follow from the entries")
    for k, v in by_key.items():
        if [x[0] for x in v] != list(range(1, len(v) + 1)):
            bad.append(f"{k}: versions are not 1..n")
    return bad, n


def mon_of(iso_week: str) -> date:
    y, w = iso_week.split("-W")
    return date.fromisocalendar(int(y), int(w), 1)
