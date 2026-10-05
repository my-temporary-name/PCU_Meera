"""Stage D: the full gist run (day, then week, then month), resumable and idempotent.

    uv run python -m v0_code.baseline_v2.stage_d [--reset-gists] [--seed 4817]

Windows are processed in waves (config `gist.wave_windows`); every window is saved as soon as it is decided, so a stopped run resumes with the
windows that are still pending, and a finished run does nothing. Between waves the stop rules are evaluated:
  * first-attempt failure above 25% in a tier (once the tier has `min_sample` windows attempted, or all of them if fewer)  -> STOP
  * an accepted entry that contains a digit or a date (an audit independent of check 3)                                       -> STOP
  * fallbacks above 10% of attempted windows while the sentence-level direction check is strict                              -> switch that check to
    warn mode (headline stays strict) and continue (the pre-agreed rule; it is logged loudly)
After the first `checkpoint_after` day windows five entries are printed as a checkpoint, and the run continues.
The old v1 tables are never touched; only memory_v2 gist columns are written.
"""

import argparse
import json
import random
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.gist import make_client, run_gist
from v0_code.baseline_v2.gist_view import build_gist_view, usual_places
from v0_code.baseline_v2.report import anchor_report
from v0_code.baseline_v2.storage import MemoryV2Store

TIERS = ("day", "week", "month")
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")


def audit_entry(obj: dict) -> list[str]:
    """Independent audit of an ACCEPTED entry: any digit (other than the allowed token HbA1c), ISO-style date or month name. Empty = clean."""
    out = []
    for t in [obj["headline"], *obj["sentences"]]:
        text = re.sub(r"hba1c", "", t, flags=re.I)
        if re.search(r"\d", text):
            out.append(f"digit in {t!r}")
        if re.search(r"\b(" + "|".join(MONTHS) + r")\b", text, re.I):
            out.append(f"month name in {t!r}")
    return out


def _stats() -> dict:
    return {"pending": 0, "attempted": 0, "first_fail": 0, "ok": 0, "retry_ok": 0, "fallbacks": 0, "warnings": 0, "first_fail_reasons": Counter(), "final_fail_reasons": Counter()}


def run_stage_d(cfg: Config, store: MemoryV2Store, rows: dict[str, list[dict]], client, *, batch_size: dict | None = None, wave: dict | None = None, min_sample: int = 20,
                stop_first_attempt_rate: float = 0.25, fallback_switch_rate: float = 0.10, checkpoint_after: int = 40, seed: int = 4817, log=None, say=print,
                stop_after_windows: int | None = None, mode: str | None = None) -> dict:
    sizes = batch_size or cfg.gist["batch_size"]
    waves = wave or cfg.gist["wave_windows"]
    mode = mode or cfg.gist.get("sentence_direction", "strict")
    day_locations = [(r["end_date"], (r["facts"].get("lifestyle") or {}).get("location")) for r in rows.get("day", [])]
    places = lambda r: usual_places(cfg, day_locations, r["start_date"])
    tiers = {t: _stats() for t in TIERS}
    summary = {"tiers": tiers, "stopped": None, "mode": mode, "mode_switched_at": None, "checkpoint": None, "processed": 0}
    day_done: list[dict] = []
    t0 = time.monotonic()

    for tier in TIERS:
        todo = [r for r in rows.get(tier, []) if r["gist"]["status"] is None]
        st = tiers[tier]
        st["pending"] = len(todo)
        for i in range(0, len(todo), int(waves[tier])):
            chunk = todo[i:i + int(waves[tier])]
            if stop_after_windows is not None:
                chunk = chunk[:max(0, stop_after_windows - summary["processed"])]
                if not chunk:
                    summary["seconds"] = round(time.monotonic() - t0, 1)
                    return summary
            results = run_gist(cfg, chunk, client, store=store, log=log, batch_size=sizes, sentence_mode=mode, usual_places_for=places)
            summary["processed"] += len(chunk)
            for res in results:
                st["attempted"] += 1
                a1 = res.attempts[0]
                st["warnings"] += sum(len(a.get("warnings", [])) for a in res.attempts)
                if not a1["passed"]:
                    st["first_fail"] += 1
                    st["first_fail_reasons"].update(f["check"] for f in a1["failures"])
                if res.status == "gist_ok":
                    st["ok"] += 1
                elif res.status == "gist_retry_ok":
                    st["retry_ok"] += 1
                else:
                    st["fallbacks"] += 1
                    st["final_fail_reasons"].update(f["check"] for f in res.attempts[-1]["failures"])
                if res.status in ("gist_ok", "gist_retry_ok"):
                    bad = audit_entry({"headline": res.headline, "sentences": res.sentences})
                    if bad:
                        summary["stopped"] = f"digit or date in an accepted entry ({res.window_id}): {bad[0]}"
                if tier == "day":
                    day_done.append({"window_id": res.window_id, "status": res.status, "headline": res.headline, "sentences": res.sentences})
            say(f"[{tier}] {st['attempted']}/{st['pending']} done | first-attempt failures {st['first_fail']} ({100 * st['first_fail'] / st['attempted']:.0f}%) | "
                f"fallbacks {st['fallbacks']} | warnings {st['warnings']} | mode {mode} | {time.monotonic() - t0:.0f}s")
            if tier == "day" and summary["checkpoint"] is None and len(day_done) >= checkpoint_after:
                pick = random.Random(seed).sample(day_done[:checkpoint_after], 5)
                block = f"CHECKPOINT after {checkpoint_after} day windows (5 of the first {checkpoint_after}):\n" + "\n".join(
                    f"- {e['window_id']} [{e['status']}]\n  headline: {e['headline']}\n  sentences: {' '.join(e['sentences']) or '(none)'}" for e in pick)
                summary["checkpoint"] = block
                say(block)
            if summary["stopped"]:
                break
            enough = st["attempted"] >= min(min_sample, st["pending"])
            if enough and st["first_fail"] / st["attempted"] > stop_first_attempt_rate:
                summary["stopped"] = f"first-attempt failure above {int(stop_first_attempt_rate * 100)}% in the {tier} tier ({st['first_fail']} of {st['attempted']})"
                break
            if enough and mode == "strict" and st["fallbacks"] / st["attempted"] > fallback_switch_rate:
                mode = "warn"
                summary["mode_switched_at"] = f"{tier}:{st['attempted']}"
                say(f"SWITCH: fallbacks above {int(fallback_switch_rate * 100)}% ({st['fallbacks']} of {st['attempted']} in the {tier} tier): the sentence-level direction check is now a counted WARNING "
                    f"(the headline stays strict); the run continues")
        if summary["stopped"]:
            say(f"STOP: {summary['stopped']}")
            break
    summary["mode_final"] = mode
    summary["seconds"] = round(time.monotonic() - t0, 1)
    return summary


# ---- report ---------------------------------------------------------------------------------------------------------------------------------

def _read_logs(report_dir: str) -> list[dict]:
    out = []
    for f in sorted(Path(report_dir).glob("gist_stage_d_[0-9]*.jsonl")):
        out += [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
    return out


def stage_d_report(cfg: Config, store: MemoryV2Store, report_dir: str, seed: int, runs: list[dict]) -> str:
    log = _read_logs(report_dir)
    tier_of = lambda wid: wid.split("_")[0]
    L = ["# Baseline Engine v2: Stage D report (full gist run)\n", f"Config `{cfg.version}` | model `{cfg.gist['model']}` | reasoning `{cfg.gist['reasoning_effort']}` | batch sizes {cfg.gist['batch_size']}\n"]
    rows = {t: [store.get_memory(t, d, full=True) for (d,) in store.conn.execute("SELECT end_date FROM memory_v2 WHERE tier = ? ORDER BY end_date", (t,))] for t in TIERS}
    L += ["## Counts by tier and status\n", "| tier | status | windows |", "|---|---|---:|"]
    for t in TIERS:
        for st, n in sorted(Counter(r["gist"]["status"] or "pending" for r in rows[t]).items()):
            L.append(f"| {t} | {st} | {n} |")
    L += ["\n## First-attempt and final failures by tier\n", "| tier | sent | first-attempt failures | rate | final fallbacks | rate | accepted after retry |", "|---|---:|---:|---:|---:|---:|---:|"]
    first = {}
    for e in log:
        if e["attempt"] == 1:
            first.setdefault(e["window_id"], e)
    reasons = {t: Counter() for t in TIERS}
    details: list[tuple[str, str, str]] = []
    for wid, e in first.items():
        for f in e["failures"]:
            reasons[tier_of(wid)][f["check"]] += 1
            details.append((wid, f["check"], f["detail"]))
    for t in TIERS:
        w = [wid for wid in first if tier_of(wid) == t]
        ff = sum(1 for wid in w if not first[wid]["passed"])
        fb = sum(1 for r in rows[t] if r["gist"]["status"] == "code_line_fallback" and r["window_id"] in first)
        rt = sum(1 for r in rows[t] if r["gist"]["status"] == "gist_retry_ok" and r["window_id"] in first)
        L.append(f"| {t} | {len(w)} | {ff} | {100 * ff / max(1, len(w)):.1f}% | {fb} | {100 * fb / max(1, len(w)):.1f}% | {rt} |")
    L += ["\n## First-attempt rejection reasons (failure counts by check)\n"] + [f"- {t}: {dict(reasons[t]) or 'none'}" for t in TIERS]
    warn = [(e["window_id"], w) for e in log for w in e.get("warnings", [])]
    L.append(f"\nSentence-level direction warnings (counted, not rejected): {len(warn)}\n")
    seen, calls = set(), []
    for e in log:
        if e["call_id"] not in seen:
            seen.add(e["call_id"])
            calls.append(e["usage"])
    L += ["## Tokens and time\n", f"- model calls: {len(calls)} (first attempts {len(set(e['call_id'] for e in log if e['attempt'] == 1))}, retries {sum(1 for e in log if e['attempt'] == 2)})",
          f"- tokens in {sum(c.get('input_tokens') or 0 for c in calls):,} / out {sum(c.get('output_tokens') or 0 for c in calls):,} (includes reasoning) / reasoning {sum(c.get('reasoning_tokens') or 0 for c in calls):,}",
          f"- sum of call times {sum(c['wall_seconds'] for c in calls) / 60:.1f} min; elapsed run time {sum(r['seconds'] for r in runs) / 60:.1f} min over {len(runs)} invocation(s)\n"]
    L += ["## Dead anchors (configured, never fired)\n"]
    for t in TIERS:
        a = anchor_report(cfg, t, rows[t])
        L.append(f"- {t}: dead = {a['dead'] or 'none'}; notable {a['notable']} of {a['windows']} ({100 * a['notable_rate']:.1f}%)")
    L += ["\n## Every first-attempt failure (for the check-or-model review)\n"] + [f"- `{w}` {c}: {d}" for w, c, d in details] + [""]
    rng = random.Random(seed)
    L.append("## Entries\n")
    named = ["week_ENDING_2025-11-22", "month_ENDING_2025-12-29", "day_2025-12-25"]
    picks = [(f"random {t}", r) for t in TIERS for r in rng.sample([x for x in rows[t] if x["gist"]["status"] in ("gist_ok", "gist_retry_ok", "code_line_fallback")], 5)]
    by_id = {r["window_id"]: r for t in TIERS for r in rows[t]}
    picks += [("named", by_id[w]) for w in named]
    day_locations = [(r["end_date"], (r["facts"].get("lifestyle") or {}).get("location")) for r in rows["day"]]
    for label, r in picks:
        view = build_gist_view(cfg, r, usual_places(cfg, day_locations, r["start_date"]))
        L += [f"### {label}: `{r['window_id']}` [{r['gist']['status']}]\n", f"- top_items: {view.get('top_items', '(none)')}", f"- headline: {r['gist']['headline']}"]
        L += [f"- {x}" for x in r["gist"]["sentences"]] + [f"- is_notable (code): {r['is_notable']}; notable_reason (code): {r['notable_reason']}\n"]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Baseline Engine v2, Stage D: the full gist run")
    ap.add_argument("--config", default="config/patient_meera_iyer_v1.yaml")
    ap.add_argument("--db", default="output/personal_data_store.db")
    ap.add_argument("--seed", type=int, default=4817)
    ap.add_argument("--reset-gists", action="store_true", help="return model-written gists (and fallbacks) to pending first, to regenerate them under the final prompt/view")
    ap.add_argument("--report-dir", default="output")
    args = ap.parse_args()
    cfg = Config.from_yaml(args.config)
    store = MemoryV2Store(args.db)
    if args.reset_gists:
        print(f"reset: {store.reset_gists()} model-written gists returned to pending", flush=True)
    ro = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    rows = {t: [store.get_memory(t, d, full=True) for (d,) in ro.execute("SELECT end_date FROM memory_v2 WHERE tier = ? ORDER BY end_date", (t,))] for t in TIERS}
    ro.close()
    stamp = int(time.time())
    log_path = f"{args.report_dir}/gist_stage_d_{stamp}.jsonl"
    with open(log_path, "a") as fh:
        summary = run_stage_d(cfg, store, rows, make_client(cfg), seed=args.seed, say=lambda s: print(s, flush=True),
                              log=lambda e: (fh.write(json.dumps(e, ensure_ascii=False) + "\n"), fh.flush()))
    runs_path = Path(args.report_dir) / "gist_stage_d_runs.jsonl"
    with open(runs_path, "a") as fh:
        fh.write(json.dumps({"stamp": stamp, "seconds": summary["seconds"], "stopped": summary["stopped"], "mode_final": summary.get("mode_final"), "mode_switched_at": summary["mode_switched_at"]}) + "\n")
    runs = [json.loads(x) for x in runs_path.read_text().splitlines() if x.strip()]
    out = Path(args.report_dir) / "baseline_v2_stage_d_report.md"
    out.write_text(stage_d_report(cfg, store, args.report_dir, args.seed, runs))
    store.close()
    print(f"Stage D finished: stopped={summary['stopped']!r} mode_switched_at={summary['mode_switched_at']}; report in {out}", flush=True)


if __name__ == "__main__":
    main()
