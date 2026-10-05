"""The replay driver (pi_spec.md 11, amendment 40). It replays the STORED Findings versions in `as_of` order, runs the weekly job for every week end that lies strictly before the
next event, runs a final job at the last day of the data (23:59:59), and counts case closings. Idempotent and resumable: every step checks what is already written. The Findings
database is opened read-only; Findings is not asked to read PI (stage L)."""

import json
import sqlite3
from datetime import datetime, time
from pathlib import Path

from v0_code.pi_engine.config import PiConfig
from v0_code.pi_engine.engine import Pi
from v0_code.pi_engine.weeks import week_end_time, week_of_date, weeks_between


class FindingsSource:
    """The stored versions (with their final F2 text) and the case closings of a Findings database, read-only."""

    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

    def close(self) -> None:
        self.conn.close()

    def versions(self, mode: str) -> list[dict]:
        """Findings records as `record_finding` takes them. Mode `full`: the final text of each version (the model text, or the code line where that was kept); `code_only`:
        the code line stored with the version."""
        finals = {}
        if mode == "full":
            finals = {fid: json.loads(t) for fid, t in self.conn.execute("SELECT finding_id, text_json FROM finding_text")}
        out = []
        for (rj,) in self.conn.execute("SELECT record_json FROM findings"):
            r = json.loads(rj)
            if r["finding_id"] in finals:
                r = {**r, "text": finals[r["finding_id"]]}
            out.append(r)
        return sorted(out, key=lambda r: (datetime.fromisoformat(r["as_of"]), r["finding_id"]))

    def closings(self) -> list[dict]:
        cur = self.conn.execute("SELECT case_id, closed_at FROM cases ORDER BY closed_at, case_id")
        return [{"case_id": c, "closed_at": t} for c, t in cur]


def schedule(pi: Pi) -> list[tuple]:
    """(week, job time) for every week from the week of the first day of the data to the week of its last day; the last job is at the last day, 23:59:59."""
    first, last = pi.labels.span()
    weeks = weeks_between(week_of_date(first), week_of_date(last))
    out = [(w, week_end_time(w, pi.tz)) for w in weeks]
    w, _ = out[-1]
    out[-1] = (w, datetime.combine(last, time(23, 59, 59), tzinfo=pi.tz))
    return out


def replay(pi: Pi, source: FindingsSource, cfg: PiConfig, mode: str | None = None, max_events: int | None = None) -> dict:
    mode = mode or cfg.replay["mode"]
    jobs = schedule(pi)
    final_time = jobs[-1][1]
    events = [(datetime.fromisoformat(r["as_of"]), 0, r["finding_id"], r) for r in source.versions(mode)]
    events += [(datetime.fromisoformat(c["closed_at"]), 1, c["case_id"], c) for c in source.closings()]
    events.sort(key=lambda e: e[:3])
    rep = {"mode": mode, "versions_written": 0, "versions_same": 0, "weeks_run": 0, "weeks_new": 0, "cases_closed": 0, "cases_closed_after_the_data_end": 0, "stopped": False, "events": 0}
    nxt = 0

    def run_job(i: int) -> None:
        w, t = jobs[i]
        new = pi.store.get_run(w.iso) is None
        pi.weekly_job(w, t)
        rep["weeks_run"] += 1
        rep["weeks_new"] += new

    for t, order, ident, payload in events:
        if max_events is not None and rep["events"] >= max_events:
            rep["stopped"] = True
            pi.store.set_progress("last_event", f"{t.isoformat()}|{ident}")
            return rep
        while nxt < len(jobs) and jobs[nxt][1] < t:                                  # a week end lies before this event: its job runs first
            run_job(nxt)
            nxt += 1
        if order == 0:
            if t > final_time:
                raise ValueError(f"{ident} is later than the end of the data")
            rep["versions_written" if pi.record_finding(payload) == "written" else "versions_same"] += 1
        else:
            rep["cases_closed"] += 1
            rep["cases_closed_after_the_data_end"] += t > final_time
        rep["events"] += 1
        pi.store.set_progress("last_event", f"{t.isoformat()}|{ident}")
    while nxt < len(jobs):                                                            # the remaining weeks, the last one at the end of the data
        run_job(nxt)
        nxt += 1
    pi.store.set_progress("done", "1")
    return rep
