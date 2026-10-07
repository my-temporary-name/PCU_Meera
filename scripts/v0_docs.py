"""Read-only export of the V0 year in numbers and the showcase, computed from the databases (output/*.db, opened read-only). Writes docs/V0_year_in_numbers.md and docs/V0_showcase.md.
    uv run python scripts/v0_docs.py"""

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
O = ROOT / "output"
F, P = O / "findings_loop_polish.db", O / "pi_loop_polish.db"


def ro(p):
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


f, p, st = ro(F), ro(P), ro(O / "state_engine.db")
norm = lambda t: t.strip().lower().rstrip(".!?")


def table(rows, head):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def sents(t):
    return [s["text"] if isinstance(s, dict) else s for s in t["sentences"]]


# ---- year in numbers -------------------------------------------------------------------------------------------------------------------------------
hand = [json.loads(r[0]) for r in st.execute("SELECT record_json FROM state_handoffs")]
months = sorted({h["opened_at"][:7] for h in hand} | {r[0][:7] for r in f.execute("SELECT local_date FROM cases")})
by_type = Counter((h["measure"], h["direction"]) for h in hand)
by_tm = Counter((h["measure"], h["direction"], h["opened_at"][:7]) for h in hand)
cases = Counter(r[0][:7] for r in f.execute("SELECT local_date FROM cases"))
vers = Counter(r[0][:7] for r in f.execute("SELECT as_of FROM findings"))
tx = {r[0]: (r[1], json.loads(r[2]), r[3], r[4], r[5]) for r in f.execute("SELECT finding_id, text_source, text_json, from_prompt, prompt_version, status FROM finding_text")}
llm = {r[0]: json.loads(r[1] or "[]") for r in f.execute("SELECT finding_id, checks_json FROM finding_llm")}
kept = [k for k, v in tx.items() if v[0] == "llm" and v[2]]
new = [k for k, v in tx.items() if v[0] == "llm" and not v[2]]
fb = sorted(k for k, v in tx.items() if v[0] != "llm")
reasons = Counter()
for k in fb:
    last = llm[k][-1] if llm.get(k) else []
    reasons[", ".join(sorted({x["name"] for x in last})) or "no failure recorded"] += 1
mems = [json.loads(r[0]) for r in p.execute("SELECT record_json FROM pi_long_memories ORDER BY memory_id, version")]
last = {}
for m in mems:
    last[m["relationship_key"]] = m
trans = Counter()
for m in last.values():
    for t in m["status_history"]:
        trans[(t["from"], t["to"])] += 1
dup_h = dup_s = 0
dup_ids = []
for k, v in tx.items():
    if v[0] != "llm":
        continue
    ss = [norm(s) for s in sents(v[1])]
    h = norm(v[1]["headline"]) in ss
    s = len(set(ss)) < len(ss)
    dup_h += h
    dup_s += s
    if h or s:
        dup_ids.append(k)
o = ["# V0, the year in numbers\n", "Computed on " + str(Path(F).name) + ", " + str(Path(P).name) + " and state_engine.db (read-only; `scripts/v0_docs.py`). Data: 1 Oct 2025 to 17 Sep 2026, one patient.\n",
     "## Alerts (State Engine hand-offs) by type and month\n", f"{len(hand)} alerts in all (a hand-off is an alert handed to the pipeline).\n"]
tm = sorted({k[2] for k in by_tm})
o += table([(f"{m} {d}", by_type[(m, d)], *[by_tm.get((m, d, x), 0) for x in tm]) for (m, d) in sorted(by_type)], ["measure and direction", "total", *tm]) + [""]
o += ["## Cases and versions by month\n"] + table([(m, cases.get(m, 0), vers.get(m, 0)) for m in sorted(set(cases) | set(vers))], ["month", "cases", "versions"])
o += [f"\nTotal: {sum(cases.values())} cases, {sum(vers.values())} versions (a version is a case's text as of each new alert or completion).\n"]
o += ["## Texts\n", f"- written by the model in the last run (prompt p-v5): {len(new)}", f"- kept from earlier prompts (re-checked under the final checks): {len(kept)}",
      f"- code-line fallbacks: {len(fb)} ({100 * len(fb) / len(tx):.1f}%)", f"- all: {len(tx)}", "", "Fallback reasons (the checks that failed on the last attempt):", ""]
o += table(sorted(reasons.items(), key=lambda x: -x[1]), ["failed check(s)", "versions"])
o += ["", "## PI\n", f"- weekly jobs: {p.execute('SELECT COUNT(*) FROM pi_weekly_runs').fetchone()[0]} (calendar weeks, Monday to Sunday)", f"- long-term memories (relationships): {len(last)}; versions written: {len(mems)}",
      f"- mid-term weekly memories sealed: {p.execute(chr(83)+'ELECT COUNT(*) FROM pi_mid_memories WHERE status = '+chr(39)+'sealed'+chr(39)).fetchone()[0]}", "", "Status at the end:", ""]
o += table(sorted(Counter(m["status"] for m in last.values()).items()), ["status", "memories"])
o += ["", "Status transitions over the year (every move, all memories):", ""] + table(sorted(trans.items(), key=lambda x: -x[1]) and [(a + " to " + b, n) for (a, b), n in sorted(trans.items(), key=lambda x: -x[1])], ["transition", "count"])
o += ["", "Situations lines: " + str(sum(1 for r in p.execute("SELECT text_json FROM pi_text") if json.loads(r[0]).get("situations"))) + " of " + str(len(mems)) + " memory versions carry one.", "",
      "## Known limit: repeated headline or sentence\n", f"- versions whose headline is repeated as one of their sentences: **{dup_h}**", f"- versions with a sentence written twice: **{dup_s}**",
      f"- versions affected in all: **{len(dup_ids)}** of {len(tx)}", ""]
(ROOT / "docs/V0_year_in_numbers.md").write_text("\n".join(o))

# ---- showcase -------------------------------------------------------------------------------------------------------------------------------------
recs = {r[0]: json.loads(r[1]) for r in f.execute("SELECT finding_id, record_json FROM findings ORDER BY as_of, finding_id")}
assoc = {}
for r in p.execute("SELECT memory_id, version, record_json FROM pi_long_memories"):
    assoc[(r[0], r[1])] = json.loads(r[2])
sit = {(r[0], r[1]): json.loads(r[2]).get("situations") for r in p.execute("SELECT memory_id, version, text_json FROM pi_text")}


def note(m, v):
    rec = assoc[(m, v)]
    s = sit.get((m, v))
    return f"`{m}` v{v} ({rec['status']}, written {rec['written_at']}): {' '.join(rec['text']['sentences'])}" + (f" Situations line: {s}" if s else " (no situations line)")


def case_block(fid):
    r = recs[fid]
    t = tx[fid][1]
    out = [f"#### {fid}", f"as_of {r['as_of']}, mode {r['mode']}, text source `{tx[fid][0]}`" + (f" (kept from {tx[fid][3]})" if tx[fid][3] else ""), "", f"**{t['headline']}**", ""]
    out += [f"{i}. {s['text']}  `{s['refs']}`" for i, s in enumerate(t["sentences"], 1)]
    notes = [x for x in r["refs"]["pi_memories"] if x.get("view_id")]
    out += ["", "PI notes drawn on: " + ("none" if not notes else ""), *[f"- `{x['view_id']}` {note(x['memory_id'], x['version'])}" for x in notes], ""]
    return out


def case_ids(lo, hi):
    return sorted({r["case_id"] for r in recs.values() if lo <= r["case_id"][5:15] <= hi})


s = ["# V0 showcase\n", "Exported without edits from `findings_loop_polish.db` and `pi_loop_polish.db` (read-only, `scripts/v0_docs.py`): the text of each version (headline, sentences, refs) and the PI notes it drew on.\n",
     "## (a) The hospitalization week, 17 to 20 November 2025\n"]
for c in case_ids("2025-11-17", "2025-11-20"):
    for r in sorted((x for x in recs.values() if x["case_id"] == c), key=lambda x: x["version"]):
        s += case_block(r["finding_id"])
s += ["## (b) The evening case of 17 September 2026 (all versions)\n"]
ev = [c for c in case_ids("2026-09-17", "2026-09-17") if c.endswith("21:45:00+05:30")]
for c in ev:
    for r in sorted((x for x in recs.values() if x["case_id"] == c), key=lambda x: x["version"]):
        s += case_block(r["finding_id"])
s += ["## (c) The sensor-artifact case of 8 November 2025\n"]
art = sorted({r["case_id"] for r in recs.values() if r["case_id"][5:15] == "2025-11-08" and any(x["wording_class"] == "artifact_note" for x in r["factors"])})
for c in art:
    for r in sorted((x for x in recs.values() if x["case_id"] == c), key=lambda x: x["version"]):
        s += case_block(r["finding_id"])
s += ["## (d) Long-term notes at every version\n"]
for key in ("sleep_hours@prev_night->hr_day_mean", "steps_window_hourly@60m->hr_hour_mean"):
    s += [f"### `{key}`\n"]
    for (m, v), rec in sorted(assoc.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if rec["relationship_key"] == key:
            s += [f"- v{v}, {rec['written_at']}, **{rec['status']}**: {' '.join(rec['text']['sentences'])}" + (f" **Situations:** {sit[(m, v)]}" if sit.get((m, v)) else " (no situations line)")]
    s += [""]
(ROOT / "docs/V0_showcase.md").write_text("\n".join(s))
print("cases (a):", len(case_ids("2025-11-17", "2025-11-20")), "(b):", ev, "(c):", art)
