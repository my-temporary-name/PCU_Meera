"""The P1 report (markdown) from a PI database: weeks, mid-term memories, long-term memories and their statuses, transitions, the partial weeks and sample texts. Reads only."""

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load(db: str | Path) -> dict:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    runs = [json.loads(r[0]) for r in c.execute("SELECT record_json FROM pi_weekly_runs ORDER BY week")]
    versions = defaultdict(list)
    for key, ts, rj in c.execute("SELECT relationship_key, written_ts, record_json FROM pi_long_memories ORDER BY relationship_key, version"):
        versions[key].append((ts, json.loads(rj)))
    sealed = {w: json.loads(j) for w, j in c.execute("SELECT week_iso, record_json FROM pi_mid_memories WHERE status = 'sealed'")}
    run_ts = {w: t for w, t in c.execute("SELECT week, written_ts FROM pi_weekly_runs")}
    return {"runs": runs, "versions": versions, "sealed": sealed, "run_ts": run_ts}


def status_at(versions: list, ts: int) -> str | None:
    cur = None
    for t, v in versions:
        if t <= ts:
            cur = v["status"]
    return cur


def make(db: str | Path, out: Path, picks: dict | None = None) -> str:
    d = load(db)
    runs, versions, sealed, run_ts = d["runs"], d["versions"], d["sealed"], d["run_ts"]
    final = {k: v[-1][1] for k, v in versions.items()}
    spec = Path(__file__).resolve().parents[3] / "task/pi_spec.md"
    amend = spec.read_text().split("## Amendments")[1].split("\n---")[0] if spec.exists() else ""
    o = ["# PI, stage P1 report (code layer and replay driver)\n", "## Amendments section of task/pi_spec.md (as printed at this stage)\n" + amend + "\n", f"Weeks run: **{len(runs)}** ({runs[0]['week']} to {runs[-1]['week']}); last job at `{runs[-1]['written_at']}`. "
         f"Long-term memories: **{len(final)}**, versions written: {sum(len(v) for v in versions.values())}.\n"]
    o += ["## Mid-term memories per week\n", "| week | entries (latest per case) | case-days | long-term created |", "|---|---:|---:|---|"]
    for r in runs:
        s = sealed[r["week"]]
        o.append(f"| {r['week']} | {len(s['entries'])} | {len(s['case_days'])} | {len(r['memories_created']) or ''} |")
    o.append(f"\nTotals: {sum(len(sealed[r['week']]['entries']) for r in runs)} entries, {sum(len(sealed[r['week']]['case_days']) for r in runs)} case-days, "
             f"{sum(len(r['memories_created']) for r in runs)} long-term memories created.\n")
    o += ["## Status counts at the end of each week (weeks with a memory)\n", "| week | candidate | supported | weakened | retracted |", "|---|---:|---:|---:|---:|"]
    for r in runs:
        cnt = Counter(status_at(v, run_ts[r["week"]]) for v in versions.values())
        if sum(cnt.get(s, 0) for s in ("candidate", "supported", "weakened", "retracted")):
            o.append(f"| {r['week']} | {cnt.get('candidate', 0)} | {cnt.get('supported', 0)} | {cnt.get('weakened', 0)} | {cnt.get('retracted', 0)} |")
    o += ["\n## Every status transition (from each memory's stored history; back-filled ones were found when the memory was created)\n", "| week | relationship | from | to | found |", "|---|---|---|---|---|"]
    rows = []
    for k, m in final.items():
        for t in m["status_history"]:
            rows.append((t["week"] if not t["week"].startswith("2026-W0") else t["week"], t, k, "back-filled" if t["week"] < m["created_week"] else "live"))
    for _, t, k, how in sorted(rows, key=lambda x: (x[0] if x[0][:4] == "2025" else x[0], x[2])):
        o.append(f"| {t['week']} | `{k}` | {t['from']} | {t['to']} | {how} |")
    sup = [(m["status_history"][0]["week"], k, m) for k, m in final.items() if any(t["to"] == "supported" for t in m["status_history"])]
    never = [k for k, m in final.items() if not m["status_history"]]
    o += [f"\n## Which relationships reach supported, and when\n", f"{len(sup)} of {len(final)} reach `supported` at some point; **{len(never)} stay `candidate` all year**: " + ", ".join(f"`{k}`" for k in never) + ".\n",
          "| first supported in week | relationship | created in week | created as |", "|---|---|---|---|"]
    for k, m in sorted(final.items(), key=lambda x: next((t["week"] for t in x[1]["status_history"] if t["to"] == "supported"), "9")):
        w = next((t["week"] for t in m["status_history"] if t["to"] == "supported"), None)
        if w:
            first_version = versions[k][0][1]
            o.append(f"| {w} | `{k}` | {m['created_week']} | {first_version['status']} |")
    weak = [(k, m) for k, m in final.items() if any(t["to"] == "weakened" for t in m["status_history"])]
    o.append(f"\nWeakened at some point: **{len(weak)}**; retracted at some point: **{sum(any(t['to'] == 'retracted' for t in m['status_history']) for m in final.values())}**; "
             f"status at the end: " + ", ".join(f"{s} {n}" for s, n in Counter(m['status'] for m in final.values()).items()) + ".\n")
    first, last = runs[0], runs[-1]
    o += ["## The first and the last partial weeks\n"]
    for lab, r in (("first", first), ("last", last)):
        labs = Counter()
        for m in final.values():
            for w in m["weekly_labels"]:
                if w["week"] == r["week"]:
                    labs[(w["days_in_week"], w["label"])] += 1
        o.append(f"- **{lab} week {r['week']}**: job at `{r['written_at']}`; weekly labels of the memories whose latest stored version reaches this week: " + (", ".join(f"{n} x {l} on {d} days" for (d, l), n in sorted(labs.items())) or "none (no memory existed yet)") + ".")
    o.append("")
    o += ["## Code text of 12 long-term memories (final version unless stated)\n"]
    chosen = []
    def add(why, k, ver=None):
        if k and k not in [c[1] for c in chosen] or ver is not None:
            chosen.append((why, k, ver))
    sd = [k for k, m in final.items() if m["same_day_only"] and m["status"] == "supported"]
    contrary = [k for k, m in final.items() if "contrary" in m["flags_seen"]]
    back = [k for k, m in final.items() if versions[k][0][1]["status"] == "supported"]
    cand = [k for k, m in final.items() if m["status"] == "candidate"]
    retr = [k for k, m in final.items() if m["status"] == "retracted"]
    if sd: add("same-day only, supported", sd[0])
    if len(sd) > 1: add("same-day only, supported", sd[-1])
    if contrary:
        add("contrary flag seen", contrary[0])
    else:                                                                              # no memory has the flag (contrary-flagged factors are not usable): the closest one
        close = max(final, key=lambda k: max((w["contrary_days"] for w in final[k]["weekly_labels"]), default=0))
        add(f"closest to a contrary relationship: no memory has the flag in flags_seen; most contrary days in a week: {max((w['contrary_days'] for w in final[close]['weekly_labels']), default=0)}", close)
    if back: add("back-filled: created as supported", back[0])
    if len(back) > 3: add("back-filled: created as supported", back[3])
    for k in cand[:2]: add("candidate all year", k)
    for k, m in weak[:1]:
        wv = next((v for _, v in versions[k] if v["status"] == "weakened"), None)
        if wv: chosen.append(("weakened (the version written at the week of weakening)", k, wv["version"]))
    for k in retr[:1]: add("retracted", k)
    for k in sorted(final):
        if len(chosen) >= 12: break
        if k not in [c[1] for c in chosen] and final[k]["status"] == "supported": add("supported", k)
    for why, k, ver in chosen[:12]:
        m = next(v for _, v in versions[k] if ver is None or v["version"] == ver) if ver else final[k]
        o.append(f"- **{why}** `{k}` (version {m['version']}, status {m['status']} since {m['status_since']}, flags {m['flags_seen']}, created {m['created_week']}):\n  > {' '.join(m['text']['sentences'])}")
    for wk in (picks or {}).get("sealed", ["2026-W38", "2025-W47"]):
        s = sealed[wk]
        o += [f"\n## Sealed mid-term memory {wk}\n", "```json", json.dumps(s, indent=1, ensure_ascii=False), "```"]
    out.write_text("\n".join(o))
    return "\n".join(o)


if __name__ == "__main__":
    make(sys.argv[1], Path(sys.argv[2]))
