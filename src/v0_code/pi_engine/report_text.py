"""The P2 sample report (prompt pp-v3, checks pck-v4): each sampled version with the diary-only sentences used, the association (code text) and the situations line (or null, with the
reason); how many versions have a model call, a non-null line and a null line; first-attempt failures by check, retries and drops; scans of the stored lines (a word not in the used sentences,
a time-relative word, a word of the link's own phrase, a claim or causal word); the exact user message of three versions; the zero-call rerun; and the byte-identity of the structured layer
against P1."""

import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

from v0_code.findings_engine.factors import parse_key
from v0_code.findings_engine.textcheck import CAUSAL
from v0_code.pi_engine import text_check, text_layer
from v0_code.pi_engine.text_check import CLAIM_WORDS, TIME_WORDS, _content, _stem, unmatched_words

P1_TABLES = ("pi_mid_memories", "pi_mid_entries", "pi_entry_keys", "pi_long_memories", "pi_weekly_runs")


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path)]


def table_hash(db: str | Path) -> dict:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return {t: hashlib.sha256(json.dumps([list(r) for r in c.execute(f"SELECT * FROM {t} ORDER BY 1, 2")], sort_keys=True).encode()).hexdigest() for t in P1_TABLES}


def factor_stems(pb, lib, kinds: set) -> set:
    """Stems of every word in every exposure and outcome phrase of the library: a situations line that uses them is probably naming a factor or a measure, not a situation."""
    return {_stem(w) for ph in text_check.other_phrases(pb, lib, kinds) for w in _content(ph)}


def scans(rows: list[dict], pb, lib, kinds: set) -> dict:
    out = {"stray": [], "time": [], "own": [], "claim": [], "factor": []}
    fs = factor_stems(pb, lib, kinds)
    for r in rows:
        v, t = r["view"], r["result"]["text"]
        line = (t or {}).get("situations")
        if v is None or not line:
            continue
        body, low = line.replace(text_check.FRAME, ""), line.lower()
        stray = unmatched_words(line, v)
        if stray:
            out["stray"].append((r["uid"], stray))
        out["time"] += [(r["uid"], w) for w in TIME_WORDS if re.search(rf"\b{re.escape(w)}\b", low)]
        link = {_stem(w) for w in _content(v["link"]["present"] + " " + v["link"]["outcome"])}
        own = sorted({w for w in _content(body) if _stem(w) in link})
        if own:
            out["own"].append((r["uid"], own))
        out["claim"] += [(r["uid"], m.group(0)) for pat in CAUSAL + [rf"\b{w}\b" for w in CLAIM_WORDS] for m in [re.search(pat, low)] if m]
        hit = sorted({w for w in _content(body) if _stem(w) in fs})
        if hit:
            out["factor"].append((r["uid"], hit))
    return out


REASONS = {"ok": "model line, all checks passed", "null": "the model returned null", "dropped": "failed the checks twice: line dropped", "no_diary_sentences": "no diary-only sentence: no call, null",
           "kept_previous_line": "no diary sentence this week: the previous line stands, no call", "code_text_retracted": "retracted: code text only, no call"}


def reason(r: dict) -> str:
    """Why a version has the line it has (null or not)."""
    return REASONS.get(r["result"]["status"], r["result"]["status"])


def pick_messages(rows: list[dict]) -> list[dict]:
    """Three versions that went to the model: one with a previous line, one same-day-only, one other (as far as the sample has them)."""
    model = [r for r in rows if r["view"] is not None and r["result"]["llm_raw"]]
    picks = []
    for pred in (lambda r: r["view"]["previous_situations"], lambda r: r["why"].startswith("same-day"), lambda r: r["why"] in ("candidate", "regenerated", "back-filled supported"), lambda r: True, lambda r: True):
        for r in model:
            if pred(r) and r not in picks:
                picks.append(r)
                break
    return picks[:3]


def make(log: Path, zero_log: Path | None, db: str, p1_db: str, out: Path, pb, lib, kinds: set, wall: str = "", entries_this_week: dict | None = None, old_log: Path | None = None) -> str:
    rows = load(log)
    model = [r for r in rows if r["view"] is not None]
    res = lambda r: r["result"]
    called = [r for r in model if res(r)["llm_raw"]]
    first = [r for r in called if res(r)["checks"] and res(r)["checks"][0]]
    by_check = Counter(c for r in first for c in {f["check"] for f in res(r)["checks"][0]})
    all_fail = Counter(f["check"] for r in called for att in res(r)["checks"] for f in att)
    usage = [u for r in called for u in res(r)["usage"]]
    retried = [r for r in called if len(res(r)["checks"]) > 1]
    dropped = [r for r in rows if res(r)["status"] == "dropped"]
    line = lambda r: (res(r)["text"] or {}).get("situations")
    nonnull = [r for r in rows if line(r)]
    null = [r for r in rows if not line(r)]
    sc = scans(rows, pb, lib, kinds)
    o = ["# PI, stage P2 report: situations line from diary-only sentences (pp-v3, pck-v4)\n",
         f"{len(rows)} long-term versions from `{log.name}`. Model `openai/gpt-5-mini`, reasoning low, 90 s timeout, no SDK retries, one retry; prompt `pp-v3`, checks `{text_check.CHECKS_VERSION}`. "
         "The view is built only from sentences of the mid-term entries whose refs (read from the Findings database) cite diary items only.\n", "## Totals\n",
         f"- versions with a model call: **{len(called)}** of {len(rows)}; without a call: {len(rows) - len(called)} (" + ", ".join(f"{n} {w}" for w, n in Counter(reason(r) for r in rows if r not in called).items()) + ")",
         f"- versions with a non-null situations line: **{len(nonnull)}**; with a null line: **{len(null)}** (" + "; ".join(f"{n}: {w}" for w, n in Counter(reason(r) for r in null).items()) + ")",
         f"- first-attempt failures: **{len(first)} of {len(called)}**" + ("" if not by_check else " (" + ", ".join(f"check {c} ({text_check.NAMES[c]}) {n}" for c, n in sorted(by_check.items())) + ")"),
         f"- retried: {len(retried)}; dropped to a null line after two failures: **{len(dropped)}**" + "".join(f"\n  - {r['uid'][0]} version {r['uid'][1]}" for r in dropped),
         "- every failure, both attempts, by check: " + (", ".join(f"check {c} {n}" for c, n in sorted(all_fail.items())) or "none"),
         f"- model calls {len(usage)}; tokens in {sum(u.get('input_tokens') or 0 for u in usage):,}, out {sum(u.get('output_tokens') or 0 for u in usage):,} (reasoning {sum(u.get('reasoning_tokens') or 0 for u in usage):,}); "
         f"call seconds {sum(u['wall_seconds'] for u in usage):.0f}" + (f"; wall {wall}" if wall else ""),
         f"- every version's association is the P1 code text unchanged: {all((res(r)['text'] or {}).get('sentences') == r['assoc']['sentences'] for r in rows)}\n"]
    if entries_this_week is not None:
        none = [r for r in rows if r["view"] is None and res(r)["status"] == "no_diary_sentences"]
        o.insert(-1, f"- of the {len(none)} versions with no diary-only sentence: {sum(entries_this_week[tuple(r['uid'])] == 0 for r in none)} had no entry citing the relationship that week, "
                     f"{sum(entries_this_week[tuple(r['uid'])] > 0 for r in none)} had entries but none with a diary-only sentence")
    if zero_log:
        z = load(zero_log)
        o.append(f"## Zero-call rerun\n\n`{zero_log.name}`: from cache {sum(r['from_cache'] for r in z if r['view'] is not None and res(r)['llm_raw'])} of {len(called)} versions that had a call, model calls "
                 f"{sum(len(r['result']['llm_raw']) for r in z if not r['from_cache'])}; texts identical to the first run: {[r['result']['text'] for r in z] == [r['result']['text'] for r in rows]}.\n")
    now, was = table_hash(db), table_hash(p1_db)
    o.append("## Structured layer against P1\n\n" + "\n".join(f"- `{t}`: {'identical' if now[t] == was[t] else 'DIFFERENT'}" for t in P1_TABLES) + "\n")
    o += ["## Scans of the stored situations lines\n",
          f"- words in a line that are not in the used sentences or the previous line (strict: any word; the check tolerates a stray word or two): **{len(sc['stray'])}** lines"
          + "".join(f"\n  - {u[0]} v{u[1]}: {', '.join(w)}" for u, w in sc["stray"]),
          f"- time-relative words (the check list): **{len(sc['time'])}**" + "".join(f"\n  - {u[0]} v{u[1]}: {w}" for u, w in sc["time"]),
          f"- words of the link's own phrase (stem match): **{len(sc['own'])}** lines" + "".join(f"\n  - {u[0]} v{u[1]}: {', '.join(w)}" for u, w in sc["own"]),
          f"- claim or causal words: **{len(sc['claim'])}**" + "".join(f"\n  - {u[0]} v{u[1]}: {w}" for u, w in sc["claim"]),
          f"- lines that use a word from any relationship's phrase (heuristic, read by eye): {len(sc['factor'])}" + "".join(f"\n  - {u[0]} v{u[1]}: {', '.join(h)}" for u, h in sc["factor"]), ""]
    if old_log:
        old = {tuple(r["uid"]): r for r in load(old_log)}
        o.append(f"## Old lines (`{old_log.name}`) next to the new ones, for the versions that have a line\n")
        for r in rows:
            if res(r)["llm_raw"] or line(r) or tuple(r["uid"]) in old and (old[tuple(r["uid"])]["result"]["text"] or {}).get("situations"):
                u = tuple(r["uid"])
                was = (old[u]["result"]["text"] or {}).get("situations") if u in old else None
                o += [f"### {u[0]} version {u[1]}", f"- old: {was or 'null'}", f"- new: {line(r) or 'null'}", ""]
    o.append("## The exact user message sent for three versions\n")
    for r in pick_messages(rows):
        o += [f"### {r['uid'][0]} version {r['uid'][1]} ({r['why']})", "", "```", text_layer.USER_TEMPLATE.format(view_json=json.dumps(r["view"], indent=2, ensure_ascii=False)), "```", ""]
    o.append("## Every sampled version: diary-only sentences, association and situations line\n")
    for r in rows:
        v, t = r["view"], res(r)["text"] or {}
        o += [f"### {r['why']}: `{r['relationship_key']}` version {r['uid'][1]}, {r['week']}, status {r['status']}", ""]
        if v:
            o.append(f"link: {v['link']['present']} -> {v['link']['outcome']}; previous line: {v['previous_situations'] or 'none'}; diary-only sentences used: {len(v['sentences'])}\n")
            o += [f"- sentence {i}: {x}" for i, x in enumerate(v["sentences"], 1)]
        else:
            o.append("- retracted: no view" if res(r)["status"] == "code_text_retracted" else "- no view: no diary-only sentence")
        o += [f"- **association (code text):** {' '.join(t.get('sentences') or [])}", f"- **situations line** (`{res(r)['status']}`; {reason(r)}): {t.get('situations') or 'null'}"]
        if t.get("cleaned") and t.get("raw") and t["raw"].get("situations") != t.get("situations"):
            o.append(f"- raw: {t['raw'].get('situations')} (cleanup: {', '.join(t['cleaned'])})")
        for i, f in enumerate(res(r)["checks"], 1):
            o.append(f"- attempt {i}: " + ("all checks pass" if not f else "; ".join(f"check {x['check']}: {x['detail']}" for x in f)))
        o.append("")
    out.write_text("\n".join(o))
    return "\n".join(o)


if __name__ == "__main__":
    # usage: report_text <config> <sample log> <zero-call log> <pi db> <P1 snapshot db> <report path> [wall]
    from v0_code.evidence_engine.library import load_library
    from v0_code.intel_common.phrasebook import Phrasebook
    from v0_code.pi_engine.config import PiConfig
    root = Path(__file__).resolve().parents[3]
    cfg = PiConfig.from_yaml(Path(sys.argv[1]) if Path(sys.argv[1]).is_absolute() else root / sys.argv[1], root)
    lib, pb = load_library(cfg.paths["evidence_library"]), Phrasebook.load(cfg.paths["phrasebook"])
    rows = load(Path(sys.argv[2]))
    kinds = {parse_key(r["relationship_key"])[3] for r in rows} - {None}
    from v0_code.pi_engine import run_text
    from v0_code.pi_engine.engine import PiReader
    from v0_code.pi_engine.storage import PiStore
    store = PiStore(sys.argv[4], readonly=True)
    entries = {(v["memory_id"], v["version"]): v["entries_this_week"] for v in run_text.load_versions(store, cfg, PiReader(cfg, store))}
    make(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], sys.argv[5], Path(sys.argv[6]), pb, lib, kinds, sys.argv[7] if len(sys.argv) > 7 else "", entries, Path(sys.argv[8]) if len(sys.argv) > 8 else None)
