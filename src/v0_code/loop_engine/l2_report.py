"""The L2 report (docs/loop_l2_report.md): totals, first-attempt failures by check, fallbacks with reasons, calls, tokens and time, the versions whose text changed from F2, the regression
and the scans, the audits, and the READ LIST (a to f) with, for each version, its text and refs, the view's earlier conclusions and the PI notes it drew on. Reads databases only."""

import json
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from v0_code.evidence_engine.library import load_library
from v0_code.findings_engine import run as frun
from v0_code.findings_engine import textcheck
from v0_code.findings_engine.report_text import SCAN_WORDS, audit_classes, clinical_term_hits
from v0_code.findings_engine.run_text import build_views
from v0_code.findings_engine.view import thing_index
from v0_code.findings_engine.storage import FindingsStore
from v0_code.loop_engine import regress
from v0_code.loop_engine.config import LoopConfig
from v0_code.loop_engine.l2_audit import audit_call_log
from v0_code.loop_engine.pi_live import earlier_conclusions
from v0_code.loop_engine.run import audits
from v0_code.pi_engine.engine import PiReader
from v0_code.pi_engine.storage import PiStore

ROOT = Path(__file__).resolve().parents[3]
CHECK_NAMES = {0: "call error", **textcheck.NAMES}


def _ro(path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def sentences(text: dict) -> list[dict]:
    return [s if isinstance(s, dict) else {"text": s, "refs": []} for s in text["sentences"]]


def load_texts(db) -> dict:
    c = _ro(db)
    out = {}
    for fid, status, source, tj, pv, cv, fp in c.execute("SELECT finding_id, status, text_source, text_json, prompt_version, checks_version, from_prompt FROM finding_text"):
        out[fid] = {"status": status, "source": source, "text": json.loads(tj), "prompt_version": pv, "checks_version": cv, "from_prompt": fp}
    for fid, usage, checks, raw in c.execute("SELECT finding_id, usage_json, checks_json, llm_raw FROM finding_llm"):
        if fid in out:
            out[fid].update({"usage": json.loads(usage or "[]"), "checks": json.loads(checks or "[]"), "raw": json.loads(raw or "[]")})
    c.close()
    return out


def render(fid: str, rec: dict, text: dict, view: dict, pi: PiStore, f2: dict | None) -> list[str]:
    o = [f"#### {fid}  (as_of {rec['as_of']}, mode {rec['mode']}, text `{text['source']}`" + (f", from prompt {text['from_prompt']}" if text.get("from_prompt") else "") + ")", ""]
    o.append(f"**{text['text']['headline']}**\n")
    o += [f"{i}. {s['text']}  `{s['refs']}`" for i, s in enumerate(sentences(text["text"]), 1)]
    items = view["earlier_conclusions"]
    o.append("")
    o.append("- view's earlier conclusions: " + ("none" if not items else ""))
    for it in items:
        o.append(f"  - `{it['id']}` about {it['about']}, state **{it['state']}**, seen before: {it['seen_before']}: \"{it['text']}\"" + (f" / situations: \"{it['situations']}\"" if it.get("situations") else ""))
    notes = [r for r in rec["refs"]["pi_memories"] if r.get("view_id")]
    if notes:
        o.append("- PI notes drawn on: " + "; ".join(f"`{r['memory_id']}` v{r['version']} ({r['status']}, written {r['written_at']})" for r in notes))
    if f2 is not None and fid in f2 and f2[fid]["text"]["headline"] != text["text"]["headline"]:
        o.append(f"- F2 headline was: {f2[fid]['text']['headline']}")
    return o + [""]


def week_of(as_of: str, tz) -> str:
    d = datetime.fromisoformat(as_of).astimezone(tz).date()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def make(cfg: LoopConfig, f1_db: str, l1_findings: str, l1_pi: str, out: Path, wall: str = "") -> str:
    fdb, pdb = cfg.l2["findings_db"], cfg.l2["pi_db"]
    run_cfg = __import__("dataclasses").replace(cfg, findings_db=fdb, pi_db=pdb)
    recs = regress.records(fdb)
    versions = sorted(recs.values(), key=lambda r: (r["as_of"], r["finding_id"]))
    texts, f2 = load_texts(fdb), load_texts(cfg.l2["f2_db"])
    pi = PiStore(pdb, readonly=True)
    reader = PiReader(cfg.pi, pi, strict=True)
    lib, pb, data = frun.prepare(cfg.findings)
    views = build_views(cfg.findings, pb, data, versions, lib, pi_items=lambda r: earlier_conclusions(r, reader, cfg.state_words, pi.situations_line))
    log_row = _ro(fdb).execute("SELECT value FROM meta WHERE key = 'l2_call_log'").fetchone()
    log = json.loads(log_row[0]) if log_row else {"barriers": [], "calls": []}
    new_ids = {c["id"] for c in log["calls"] if c["phase"] == "findings_text" and not c["from_cache"]}
    reused = [c for c in log["calls"] if c["phase"] == "findings_text" and c["from_cache"]]
    tz = cfg.findings.tz
    rows = [{"finding_id": r["finding_id"], "view": views[r["finding_id"]], "result": {"text_source": texts[r["finding_id"]]["source"], "text": texts[r["finding_id"]]["text"]}} for r in versions]
    n = len(versions)
    fallbacks = [fid for fid, t in texts.items() if t["source"] != "llm"]
    first = [fid for fid in new_ids if texts[fid].get("checks") and texts[fid]["checks"][0]]
    by_check = Counter(c for fid in first for c in {f["check"] for f in texts[fid]["checks"][0]})
    usage = [u for fid in new_ids for u in texts[fid].get("usage", [])]
    pc = _ro(pdb)
    plines = pc.execute("SELECT t.memory_id, t.version, t.status, t.text_json, l.usage_json, l.checks_json FROM pi_text t LEFT JOIN pi_llm l USING (memory_id, version) ORDER BY t.memory_id, t.version").fetchall()
    pl = [(m, v, st, json.loads(tj), json.loads(uj or "[]"), json.loads(cj or "[]")) for m, v, st, tj, uj, cj in plines]
    pusage = [u for *_, uj, _c in pl for u in uj]
    p_by_check = Counter(c for *_, ch in pl for c in ({f["check"] for f in ch[0]} if ch and ch[0] else set()))
    pc.close()
    p_called = [x for x in pl if x[4]]
    lines_stat = Counter(st for _, _, st, *_ in pl)
    wall_s = sum(max((b["lines_end"] for b in log["barriers"] if b.get("run") == r), default=0) for r in range(1, log.get("runs", 1) + 1)) if log["barriers"] else 0
    changed = [fid for fid in texts if fid in f2 and (texts[fid]["text"]["headline"] != f2[fid]["text"]["headline"] or [s["text"] for s in sentences(texts[fid]["text"])] != [s["text"] for s in sentences(f2[fid]["text"])])]
    p_cited = {fid: sum(1 for s in sentences(texts[fid]["text"]) for r in s["refs"] if re.fullmatch(r"p\d+", r)) for fid in texts}
    o = ["# Stage L2 report: the loop with the models\n",
         f"Loop config `{cfg.version}`. Findings texts `p-v4` / checks `ck-v6`, PI situations lines `pp-v4` / `pck-v6`; model `{cfg.findings.text['model']}` (reasoning {cfg.findings.text['reasoning_effort']}, retries {cfg.findings.text['retries']}). "
         "Databases `output/findings_loop_full.db` and `output/pi_loop_full.db`.\n", "## Totals\n",
         f"- versions: **{n}** in {len({r['case_id'] for r in versions})} cases; texts: {n - len(fallbacks)} written by a model or kept ({len(new_ids)} written in this run, {len(reused)} answers kept from F2 for unchanged views), "
         f"**{len(fallbacks)} code-line fallbacks ({100 * len(fallbacks) / n:.1f}%, acceptance: at most {int(0.04 * n)} = 4%)**",
         f"- first-attempt failures (texts written in this run): **{len(first)} of {len(new_ids)}**" + ("" if not by_check else " (" + ", ".join(f"{CHECK_NAMES[c]} {k}" for c, k in sorted(by_check.items())) + ")"),
         f"- PI situations lines: {len(pl)} memory versions; by status {dict(lines_stat)}; model calls for {len(p_called)} of them; first-attempt failures {sum(1 for *_, ch in p_called if ch and ch[0])}"
         + ("" if not p_by_check else " (" + ", ".join(f"check {c} {k}" for c, k in sorted(p_by_check.items())) + ")"),
         f"- model calls: Findings {sum(len(texts[f]['checks']) for f in new_ids)}, PI {sum(len(ch) for *_, ch in p_called)}; tokens in {sum(u.get('input_tokens') or 0 for u in usage + pusage):,}, "
         f"out {sum(u.get('output_tokens') or 0 for u in usage + pusage):,} (reasoning {sum(u.get('reasoning_tokens') or 0 for u in usage + pusage):,}); call seconds {sum(u['wall_seconds'] for u in usage + pusage):.0f}; "
         f"run time {wall_s / 60:.1f} min" + (f" (wall {wall})" if wall else ""), ""]
    o += ["## Fallbacks and their reasons\n"]
    for fid in sorted(fallbacks):
        t = texts[fid]
        why = []
        for k, att in enumerate(t.get("checks", []), 1):
            why.append(f"attempt {k}: " + ("; ".join(f"{CHECK_NAMES[f['check']]} ({f['detail']})" for f in att) if att else "no failure recorded"))
        o.append(f"- `{fid}`: " + " | ".join(why))
    if not fallbacks:
        o.append("- none")
    o += ["", "## Texts that changed from F2\n", f"- {len(changed)} of {n} versions have a different text from F2: {sum(1 for f in changed if views[f]['earlier_conclusions'])} of them have a view with earlier conclusions "
          f"({sum(1 for f in views if views[f]['earlier_conclusions'])} such views in all). Of the {len(changed)}, the p items in the view: " + ", ".join(f"{k} items: {c}" for k, c in sorted(Counter(len(views[f]['earlier_conclusions']) for f in changed).items()))
          + "; p items cited in the text: " + ", ".join(f"{k} cited: {c}" for k, c in sorted(Counter(p_cited[f] for f in changed).items())),
          f"- versions whose text cites at least one p item: {sum(1 for f in texts if p_cited[f])}; versions whose view has p items but whose text cites none: {sum(1 for f in texts if views[f]['earlier_conclusions'] and not p_cited[f])}", ""]
    # regression
    cmp_f1 = regress.compare_findings(f1_db, fdb)
    l1, l2 = regress.records(l1_findings), recs
    same_l1 = sum(json.dumps(l1[k], sort_keys=True) == json.dumps(l2[k], sort_keys=True) for k in l2) if l1.keys() == l2.keys() else -1
    cmp_pi = regress.compare_pi(l1_pi, pdb)
    o += ["## Regression\n", f"- against F1 (labels, flags, exposure states, wording classes, groups, factor ids, mode, measures, case and version ids): versions that differ outside `repeat` and `refs.pi_memories`: **{len(cmp_f1['violations'])} of {cmp_f1['f1']}**",
          f"- structured layer (`findings` rows) identical to L1: **{same_l1} of {len(l2)}**",
          "- PI against L1: " + "; ".join(f"`{t}` {'identical' if v['identical'] else str(v['different_rows']) + ' rows differ'}" for t, v in cmp_pi.items())
          + f"; final statuses identical: {regress.final_statuses(l1_pi) == regress.final_statuses(pdb)}; status transitions identical: {regress.status_transitions(l1_pi) == regress.status_transitions(pdb)}", ""]
    # scans
    llm_rows = [r for r in rows if r["result"]["text_source"] == "llm"]
    scan_rep = [(r["finding_id"], t) for r in llm_rows for t in [("headline", r["result"]["text"]["headline"])] + [(f"s{i}", s["text"]) for i, s in enumerate(sentences(r["result"]["text"]), 1)] if re.search(r"\brepeatedly\b|\bmoved together\b", t[1], re.I)]
    scan_rec = [(r["finding_id"], s["text"], s["refs"]) for r in llm_rows for s in sentences(r["result"]["text"]) if re.search(textcheck.RECURRENCE, s["text"].lower()) and not any(re.fullmatch(r"p\d+", x) for x in s["refs"])]
    scan_expl = [(r["finding_id"], s["text"]) for r in llm_rows for s in sentences(r["result"]["text"]) if SCAN_WORDS.search(s["text"])]
    scan_art = []
    for r in llm_rows:
        by_id = thing_index(r["view"])
        for s in sentences(r["result"]["text"]):
            if any(by_id.get(x, {}).get("wording") == "artifact_note" for x in s["refs"]) and (re.search(r"\b(tended|linked|together|come up before|early observation)\b", s["text"], re.I) or any(re.fullmatch(r"[sp]\d+", x) for x in s["refs"])):
                scan_art.append((r["finding_id"], s["text"]))
    stronger = audit_classes(rows)
    clin = clinical_term_hits(rows, pb)
    calls_bad, calls_n = audit_call_log(fdb, pdb)
    bad, n_aud = audits(run_cfg, versions)
    o += ["## Scans of the final Findings texts\n",
          f"- a headline or sentence containing \"repeatedly\" or \"moved together\": **{len(scan_rep)}**" + "".join(f"\n  - {f} {w}: {t}" for f, (w, t) in scan_rep),
          f"- sentences stronger than their class or with claim wording and no claim-class point (heuristic scan): **{len(stronger)}**" + "".join(f"\n  - {x}" for x in stronger),
          f"- \"this has come up before\" or \"an early observation\" without a p ref: **{len(scan_rec)}**" + "".join(f"\n  - {f}: {t} {r}" for f, t, r in scan_rec),
          f"- explanation or reason words: **{len(scan_expl)}**" + "".join(f"\n  - {f}: {t}" for f, t in scan_expl),
          f"- artifact sentences linked to a claim, an earlier summary or an earlier conclusion: **{len(scan_art)}**" + "".join(f"\n  - {f}: {t}" for f, t in scan_art),
          f"- clinical terms not in the view: **{len(clin)}**" + "".join(f"\n  - {c}" for c in clin), ""]
    o += ["## Audits\n", f"- as-of audits (evidence, diary, state memory, PI labels, strict PI reads): " + ("**clean**" if not bad else f"**{len(bad)} violations**") + f" {json.dumps(n_aud)}" + "".join(f"\n  - {b}" for b in bad[:10]),
          f"- model-call ordering (barriers in order, a text written after the memory it cites and after its situations line, lines built only from entries written by their barrier, entry text equals the Findings text): "
          + ("**clean**" if not calls_bad else f"**{len(calls_bad)} violations**") + f" {json.dumps(calls_n)}" + "".join(f"\n  - {b}" for b in calls_bad[:10]), ""]
    # read list
    o += ["## READ LIST\n"]
    by_case = defaultdict(list)
    for r in versions:
        by_case[r["case_id"]].append(r)
    show = lambda r: render(r["finding_id"], r, texts[r["finding_id"]], views[r["finding_id"]], pi, f2)
    rl = cfg.l2["read_list"]
    o += [f"### (a) The cases of {rl['first_cases'][0]} to {rl['first_cases'][1]} (the hospitalization week)\n"]
    for cid in sorted(by_case):
        if rl["first_cases"][0] <= cid[5:15] <= rl["first_cases"][1]:
            for r in by_case[cid]:
                o += show(r)
    o += [f"### (b) The cases of {rl['last_cases'][0]} to {rl['last_cases'][1]}\n"]
    for cid in sorted(by_case):
        if rl["last_cases"][0] <= cid[5:15] <= rl["last_cases"][1]:
            for r in by_case[cid]:
                o += show(r)
    key = rl["relationship"]
    for wk in rl["weeks"]:
        o += [f"### (c) Cases in {wk} that cite `{key}`\n"]
        cases = sorted({r["case_id"] for r in versions if week_of(r["as_of"], tz) == wk and any(f["kind"] == "relationship" and f["relationship_key"] == key and f.get("label") in ("supported", "suggestive") for f in r["factors"])})
        o.append(f"{len(cases)} cases: " + (", ".join(f"`{c}`" for c in cases) if cases else "none") + "\n")
        for cid in cases:
            for r in by_case[cid]:
                if week_of(r["as_of"], tz) == wk:
                    o += show(r)
        mem = [(m[0], m[1]) for m in pi.conn.execute("SELECT memory_id, version, relationship_key, status, written_at FROM pi_long_memories WHERE relationship_key = ? ORDER BY version", (key,)).fetchall()
               if week_of(m[4], tz) == wk]
        o.append(f"The long-term note of `{key}` written by the job of {wk}:\n")
        for mid, ver in mem:
            m = pi.long_version(mid, ver)
            line = pi.situations_line(mid, ver)
            o.append(f"- version {ver}, {m['written_at']}, **{m['status']}**: {' '.join(m['text']['sentences'])}" + (f" **Situations:** {line}" if line else " (no situations line)"))
        o.append("")
    # (d)
    runs = pi.runs()
    by_week = {r["week"]: r["counts"]["entries"] for r in runs}
    empty = [r for r in runs if r["counts"]["entries"] == 0]
    mid_year = [r for r in empty[2:] if by_week.get(next((x["week"] for x in runs if x["week"] > r["week"]), ""), 0) > 0]          # not the first weeks of the data; the next week has findings
    o += ["### (d) A week with no findings and the mid-term memory of the following week\n"]
    if empty:
        w = (mid_year or empty)[0]["week"]
        nxt = next((r["week"] for r in runs if r["week"] > w), None)
        o.append(f"Week {w} had no entries ({len(empty)} such weeks: {', '.join(r['week'] for r in empty)}). The mid-term memory of the following week, {nxt}:\n")
        mid = next(json.loads(x[0]) for x in pi.conn.execute("SELECT record_json FROM pi_mid_memories WHERE memory_id = ? AND status = 'sealed'", (f"pi_mid_{nxt}",)))
        o.append(f"`{mid['memory_id']}` sealed {mid['sealed_at']}, relationships touched: {mid['relationship_keys_touched']}, case days {mid['case_days']}\n")
        for e in mid["entries"]:
            o += [f"- `{e['finding_id']}` ({e['mode']}): **{e['headline']}** " + " ".join(e["sentences"]), ""]
    else:
        quiet = min(runs, key=lambda r: r["counts"]["entries"])
        o.append(f"No week of this year has zero entries. The quietest, {quiet['week']}, has {quiet['counts']['entries']}.\n")
    # (e)
    with_p = [r for r in versions if views[r["finding_id"]]["earlier_conclusions"]]
    rng = random.Random(int(rl["seed"]))
    months = defaultdict(list)
    for r in with_p:
        months[r["as_of"][:7]].append(r)
    for m in months.values():
        rng.shuffle(m)
    chosen = []
    while len(chosen) < 20 and any(months.values()):
        for mth in sorted(months):
            if months[mth] and len(chosen) < 20:
                chosen.append(months[mth].pop())
    o += [f"### (e) 20 versions with earlier conclusions, chosen by seed {rl['seed']} across months ({len({r['as_of'][:7] for r in chosen})} months)\n"]
    for r in sorted(chosen, key=lambda r: r["as_of"]):
        o += show(r)
    # (f)
    mems = defaultdict(list)
    for (mid, ver, key_, status, written) in [(x[0], x[1], x[2], x[3], x[4]) for x in pi.conn.execute("SELECT memory_id, version, relationship_key, status, written_at FROM pi_long_memories ORDER BY memory_id, version")]:
        mems[key_].append((mid, ver, status, written))
    pick = sorted((k for k, v in mems.items() if len(v) >= 3), key=lambda k: (-len(mems[k]), k))[:12]
    o += ["### (f) The long-term note of 12 relationships at three points in time\n"]
    for k in pick:
        v = mems[k]
        o.append(f"**`{k}`** ({len(v)} versions)\n")
        for mid, ver, status, written in (v[0], v[len(v) // 2], v[-1]):
            m = pi.long_version(mid, ver)
            line = pi.situations_line(mid, ver)
            o += [f"- version {ver}, {written}, {status}: {' '.join(m['text']['sentences'])}" + (f" **Situations:** {line}" if line else " (no situations line)")]
        o.append("")
    pi.close()
    out.write_text("\n".join(o))
    return "\n".join(o)


if __name__ == "__main__":
    # usage: l2_report <loop config> <F1 findings db> <L1 findings db> <L1 pi db> <report path> [wall]
    cfg = LoopConfig.from_yaml(ROOT / sys.argv[1] if not Path(sys.argv[1]).is_absolute() else sys.argv[1], ROOT)
    make(cfg, sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5]), sys.argv[6] if len(sys.argv) > 6 else "")
