"""The cleanup round after Stage D: pick the windows to redo, estimate the calls, redo them, and audit every stored gist (read-only).

    uv run python -m v0_code.baseline_v2.cleanup --estimate          # which windows, why, and how many calls (no model call)
    uv run python -m v0_code.baseline_v2.cleanup --run               # reset exactly those windows and regenerate them (Stage D machinery)
    uv run python -m v0_code.baseline_v2.cleanup --audit             # read-only audit of every stored gist -> output/baseline_v2_cleanup_audit.md

No new checks or rules live here: the selection re-validates stored gists under the (changed) existing checks; the audits only report.
"""

import argparse
import json
import math
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.gist import make_client
from v0_code.baseline_v2.gist_check import CLAUSE_SPLIT, DOWN_WORDS, STATUS_PHRASE, UP_WORDS, _term_regex, check_gist, normalize_text
from v0_code.baseline_v2.gist_view import diary_texts, wording_tags
from v0_code.baseline_v2.render import diary_severity_rank
from v0_code.baseline_v2.stage_d import TIERS, run_stage_d, stage_d_report
from v0_code.baseline_v2.storage import MemoryV2Store

ACCEPTED = ("gist_ok", "gist_retry_ok")
OBSERVED_FIRST_ATTEMPT_FAILURE = {"day": 0.081, "week": 0.145, "month": 0.364}          # Stage D, used only to estimate retry calls
BARE_GLUCOSE = re.compile(r"(?<!average )(?<!meal )(?<!estimated )\bglucose\b(?!-based| variability| peak)", re.I)
WATCHED = ("tentative", "affected", "impacted", "influenced", "contributed")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")
STOP = set("about after again being before could during first other still their there these those through where which while would family".split()) - {"family"}


def _text(r: dict) -> str:
    return " ".join([r["gist"]["headline"] or "", *r["gist"]["sentences"]])


def _all(rows: dict[str, list[dict]]):
    for t in TIERS:
        yield from rows.get(t, [])


# ---- selection and estimate -----------------------------------------------------------------------------------------------------------------

def affected_windows(cfg: Config, rows: dict[str, list[dict]]) -> dict[str, list[str]]:
    """Windows to redo, with the reasons: every fallback; every accepted gist that fails the existing checks as they are NOW (tentative wording, the longer causal
    list); every accepted headline that says a bare "glucose"."""
    out: dict[str, list[str]] = {}
    for r in _all(rows):
        st = r["gist"]["status"]
        if st == "code_line_fallback":
            out[r["window_id"]] = ["fallback"]
        elif st in ACCEPTED:
            why = sorted({f["check"] for f in check_gist(cfg, {"headline": r["gist"]["headline"], "sentences": r["gist"]["sentences"]}, wording_tags(cfg, r), diary_texts(r), reliable=bool(r["reliable"]))})
            if BARE_GLUCOSE.search(r["gist"]["headline"] or ""):
                why.append("bare glucose in the headline")
            if why:
                out[r["window_id"]] = why
    return out


def estimate_calls(cfg: Config, counts: dict[str, int]) -> dict:
    sizes = cfg.gist["batch_size"]
    first = {t: math.ceil(counts.get(t, 0) / int(sizes[t])) for t in TIERS}
    retries = math.ceil(sum(counts.get(t, 0) * OBSERVED_FIRST_ATTEMPT_FAILURE[t] for t in TIERS))
    return {"first_attempt_calls": first, "total_first": sum(first.values()), "retries_expected": retries, "total_expected": sum(first.values()) + retries, "windows": dict(counts)}


# ---- the read-only audit --------------------------------------------------------------------------------------------------------------------

def audit_missed_medicines(cfg: Config, rows: dict[str, list[dict]]) -> list[dict]:
    """(a) gists that do not name a medicine the window's facts list as missed."""
    out = []
    for r in _all(rows):
        if r["gist"]["status"] not in ACCEPTED:
            continue
        text = _text(r).lower()
        missed = sorted({cfg.medicine_name(i["medicine"]) for i in r["material_changes"] if i["kind"] == "missed_dose"})
        gone = [m for m in missed if not re.search(rf"\b{re.escape(m.lower())}\b", text)]
        if gone:
            out.append({"window_id": r["window_id"], "missing": gone})
    return out


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]{5,}", text.lower()) if w not in STOP}


def audit_diary_theme(cfg: Config, rows: dict[str, list[dict]]) -> list[dict]:
    """(b) windows with a moderate-or-worse diary entry where the gist mentions none of the entries' content words. Heuristic: the words of five or more letters in
    the entries' text (a small stop-word list removed), compared with the gist's words by their first five letters ("hospitalized" ~ "hospital")."""
    cutoff = diary_severity_rank(cfg, cfg.month_min_severity)
    out = []
    for r in _all(rows):
        if r["gist"]["status"] not in ACCEPTED:
            continue
        ents = [i for i in r["material_changes"] if i["kind"] == "diary_event" and diary_severity_rank(cfg, i.get("severity_note")) <= cutoff]
        if ents and not (set().union(*(_stems(e["text"]) for e in ents)) & _stems(_text(r))):
            out.append({"window_id": r["window_id"], "entries": [e["text"] for e in ents]})
    return out


def audit_words(rows: dict[str, list[dict]]) -> dict:
    """(c) accepted gists containing the watched words (counted by window)."""
    counts, wins = Counter({w: 0 for w in WATCHED}), set()
    for r in _all(rows):
        if r["gist"]["status"] not in ACCEPTED:
            continue
        text = _text(r)
        for w in WATCHED:
            if re.search(rf"\b{w}(ly)?\b" if w == "tentative" else rf"\b{w}\b", text, re.I):
                counts[w] += 1
                wins.add(r["window_id"])
    return {"counts": {w: counts[w] for w in WATCHED}, "windows": sorted(wins)}


def audit_wrong_facts(cfg: Config, rows: dict[str, list[dict]]) -> list[dict]:
    """A wrong medicine (named but not missed in that window), a wrong date (a weekday or month name) or a wrong direction the checker cannot see (a direction
    word placed up to three words BEFORE a measure phrase and disagreeing with that measure's tag)."""
    meds = {cfg.medicine_name(i["medicine"]) for r in _all(rows) for i in r["material_changes"] if i["kind"] == "missed_dose"}
    rx, terms = _term_regex(cfg)
    up = re.compile(r"\b(" + "|".join(sorted({normalize_text(w) for w in UP_WORDS})) + r")\b")
    down = re.compile(r"\b(" + "|".join(sorted({normalize_text(w) for w in DOWN_WORDS})) + r")\b")
    out = []
    for r in _all(rows):
        if r["gist"]["status"] not in ACCEPTED:
            continue
        text, low = _text(r), _text(r).lower()
        missed = {cfg.medicine_name(i["medicine"]) for i in r["material_changes"] if i["kind"] == "missed_dose"}
        for m in sorted(meds - missed):
            if re.search(rf"\b{re.escape(m.lower())}\b", low):
                out.append({"window_id": r["window_id"], "kind": "wrong medicine", "detail": f"names {m}, which was not missed in this window"})
        for w in WEEKDAYS + MONTHS:
            if re.search(rf"\b{w}\b", low) and not (w == "may" and "may" in text and "May" not in text):
                out.append({"window_id": r["window_id"], "kind": "wrong date", "detail": f"names {w}"})
        by_stream = {t["measure"]: t for t in r["tags"]}
        for sentence in re.split(r"[.!?]+", STATUS_PHRASE.sub("", normalize_text(text))):
            for clause in CLAUSE_SPLIT.split(sentence):
                for m in rx.finditer(clause):
                    tag = by_stream.get(terms[m.group(1)])
                    before = clause[:m.start()].split()[-3:]
                    words = " ".join(before)
                    d = [("up", x.group(0)) for x in up.finditer(words)] + [("down", x.group(0)) for x in down.finditer(words)]
                    if tag and d and not (up.search(clause[m.end():]) or down.search(clause[m.end():])):
                        bad = tag["direction"] in ("flat", "not_enough_data") or any(dd != tag["direction"] for dd, _ in d)
                        if bad:
                            out.append({"window_id": r["window_id"], "kind": "wrong direction", "detail": f"{d[0][1]!r} before {m.group(1)!r}, tag is {tag['direction']}: {clause.strip()!r}"})
    return out


# ---- CLI --------------------------------------------------------------------------------------------------------------------------------------

def _load(db: str) -> tuple[MemoryV2Store, dict[str, list[dict]]]:
    store = MemoryV2Store(db)
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = {t: [store.get_memory(t, d, full=True) for (d,) in ro.execute("SELECT end_date FROM memory_v2 WHERE tier = ? ORDER BY end_date", (t,))] for t in TIERS}
    ro.close()
    return store, rows


def audit_report(cfg: Config, rows: dict[str, list[dict]]) -> str:
    accepted = sum(1 for r in _all(rows) if r["gist"]["status"] in ACCEPTED)
    a, b, c, f = audit_missed_medicines(cfg, rows), audit_diary_theme(cfg, rows), audit_words(rows), audit_wrong_facts(cfg, rows)
    L = [f"# Baseline cleanup: read-only audit of all stored gists\n", f"Gists audited: {accepted} accepted (gist_ok / gist_retry_ok) of {sum(1 for r in _all(rows) if r['gist']['status'] and r['gist']['status'].startswith(('gist', 'code_line_fallback')))} model-attempted windows; "
         f"fallback code lines in the store: {sum(1 for r in _all(rows) if r['gist']['status'] == 'code_line_fallback')}\n",
         "## (a) A missed medicine in the facts that the gist does not name\n", f"Count: **{len(a)}** windows.\n"] + [f"- `{x['window_id']}` does not name: {', '.join(x['missing'])}" for x in a]
    L += ["\n## (b) A moderate-or-worse diary entry whose theme the gist does not mention\n",
          "Method: content words of five or more letters from the entries' text (small stop-word list removed) are compared with the gist's words by their first five letters; a window is a miss when no entry shares any.\n",
          f"Count: **{len(b)}** windows.\n"] + [f"- `{x['window_id']}`: " + " | ".join(x["entries"]) for x in b]
    L += ["\n## (c) Accepted gists containing the watched words\n", f"Counts by word: {c['counts']}; windows: {c['windows'] or 'none'}\n"]
    L += ["\n## Wrong facts (wrong medicine, wrong date, wrong direction the checker cannot see)\n", f"Count: **{len(f)}**.\n"] + [f"- `{x['window_id']}` {x['kind']}: {x['detail']}" for x in f]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Baseline cleanup round")
    ap.add_argument("--config", default="config/patient_meera_iyer_v1.yaml")
    ap.add_argument("--db", default="output/personal_data_store.db")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--only", help="comma-separated window ids to redo instead of the computed set (used for wrong facts)")
    ap.add_argument("--report-dir", default="output")
    args = ap.parse_args()
    cfg = Config.from_yaml(args.config)
    store, rows = _load(args.db)
    if args.estimate or args.run:
        sel = {w: ["requested"] for w in args.only.split(",")} if args.only else affected_windows(cfg, rows)
        counts = Counter(w.split("_")[0] for w in sel)
        est = estimate_calls(cfg, {"day": counts["day"], "week": counts["week"], "month": counts["month"]})
        print(json.dumps({"windows": len(sel), "by_tier": est["windows"], "reasons": dict(Counter(r for v in sel.values() for r in v)), "estimate": est}, indent=2), flush=True)
    if args.run:
        n = store.reset_gists(sorted(sel))
        print(f"reset {n} windows to pending", flush=True)
        _, rows = _load(args.db)
        stamp = int(time.time())
        with open(f"{args.report_dir}/gist_cleanup_{stamp}.jsonl", "a") as fh:
            summary = run_stage_d(cfg, store, rows, make_client(cfg), stop_first_attempt_rate=1.0, say=lambda s: print(s, flush=True),
                                  log=lambda e: (fh.write(json.dumps(e, ensure_ascii=False) + "\n"), fh.flush()))
        print(json.dumps({k: (v if k != "tiers" else {t: {kk: (dict(vv) if isinstance(vv, Counter) else vv) for kk, vv in s.items()} for t, s in v.items()}) for k, v in summary.items() if k != "checkpoint"}, indent=2), flush=True)
    if args.audit:
        _, rows = _load(args.db)
        out = Path(args.report_dir) / "baseline_v2_cleanup_audit.md"
        out.write_text(audit_report(cfg, rows))
        print(f"audit written to {out}", flush=True)
    store.close()


if __name__ == "__main__":
    main()
