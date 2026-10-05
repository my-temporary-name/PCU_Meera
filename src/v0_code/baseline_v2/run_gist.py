"""Stage C: run the gist on a small named sample and write a report. Never touches the old v1 tables; writes only memory_v2 gist columns.

    uv run python -m v0_code.baseline_v2.run_gist --stage C [--seed 4817] [--part sample|batch|both] [--sentence-direction strict|warn]

The sample is sent one window per call (batch size 1) so tokens and wall time belong to one window. The batch test sends 16 day windows 4 per call
and 6 week windows 2 per call (the configured batch sizes) to exercise batching for real. The default command never wipes anything.
"""

import argparse
import json
import random
import sqlite3
import time
from pathlib import Path

from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.gist import SYSTEM_PROMPT, make_client, run_gist
from v0_code.baseline_v2.storage import MemoryV2Store

FIXED = {"week_ENDING_2025-11-22": "golden week", "week_ENDING_2026-03-20": "golden week", "month_ENDING_2025-12-29": "golden month",
         "day_2025-12-26": "golden day (missed metformin)", "day_2026-04-23": "golden day (removed 590 reading)"}


NO_LLM = ("code_line_early", "code_line_quiet", "code_line_week_skipped")


def llm_eligible(row: dict) -> bool:
    """Would this window get a model gist? Independent of whether it already has one, so a re-run picks the same windows as the first run."""
    return row["gist"]["status"] not in NO_LLM


def choose_sample(rows: dict[str, list[dict]], seed: int) -> list[dict]:
    """The named windows plus a seeded random rest: one diary-heavy day (2+ diary entries), one quiet day, one early day with material, two more weeks and one more month."""
    rng = random.Random(seed)
    day, week, month = rows["day"], rows["week"], rows["month"]
    n_diary = lambda r: sum(1 for i in r["material_changes"] if i["kind"] == "diary_event")
    taken = set(FIXED)
    pick = lambda pool: rng.choice(sorted((r["window_id"] for r in pool if r["window_id"] not in taken)))
    out = [{"role": role, "window_id": wid} for wid, role in FIXED.items()]
    for role, pool in (("diary-heavy day", [r for r in day if llm_eligible(r) and n_diary(r) >= 2]),
                       ("quiet day", [r for r in day if r["gist"]["status"] == "code_line_quiet"]),
                       ("early day", [r for r in day if r["gist"]["status"] == "code_line_early" and r["material_changes"]]),
                       ("random week 1", [r for r in week if llm_eligible(r)]), ("random week 2", [r for r in week if llm_eligible(r)]),
                       ("random month", [r for r in month if llm_eligible(r)])):
        wid = pick(pool)
        taken.add(wid)
        out.append({"role": role, "window_id": wid})
    return out


def choose_batch_test(rows: dict[str, list[dict]], seed: int, n_days: int = 16, n_weeks: int = 6) -> list[dict]:
    """Seeded random windows for the batching test: eligible day and week windows that are not in the named sample."""
    rng = random.Random(seed + 1)
    taken = {x["window_id"] for x in choose_sample(rows, seed)}
    days = sorted(r["window_id"] for r in rows["day"] if llm_eligible(r) and r["window_id"] not in taken)
    weeks = sorted(r["window_id"] for r in rows["week"] if llm_eligible(r) and r["window_id"] not in taken)
    ids = rng.sample(days, n_days) + rng.sample(weeks, n_weeks)
    by_id = {r["window_id"]: r for rs in rows.values() for r in rs}
    return [by_id[i] for i in ids]


def _unique_calls(results) -> list[dict]:
    """One usage record per model call (a batched call serves several windows, so it must be counted once)."""
    seen, out = set(), []
    for r in results:
        for a in r.attempts:
            if a["call_id"] not in seen:
                seen.add(a["call_id"])
                out.append(a["usage"])
    return out


def batch_report(cfg: Config, store: MemoryV2Store, rows: list[dict], results: dict, log_path: str, mode: str) -> str:
    from collections import Counter
    res = [results[r["window_id"]] for r in rows]
    first_fail = [r for r in res if not r.attempts[0]["passed"]]
    calls = _unique_calls(res)
    L = ["# Baseline Engine v2: Stage C batching test\n", f"Config `{cfg.version}` | sentence-level direction check: **{mode}** | batch sizes day 4, week 2 | raw log `{log_path}`\n",
         f"- windows: {len(res)} ({sum(r.tier == 'day' for r in res)} day, {sum(r.tier == 'week' for r in res)} week)\n",
         f"- first-attempt failures: {len(first_fail)} of {len(res)} ({100 * len(first_fail) / len(res):.0f}%)\n",
         f"- first-attempt reasons: {dict(Counter(f['check'] for r in first_fail for f in r.attempts[0]['failures'])) or 'none'}\n",
         f"- final statuses: {dict(Counter(r.status for r in res))}\n", f"- warnings (sentence-level direction): {sum(len(a.get('warnings', [])) for r in res for a in r.attempts)}\n",
         f"- model calls: {len(calls)}; tokens in {sum(c.get('input_tokens') or 0 for c in calls)}, out {sum(c.get('output_tokens') or 0 for c in calls)}, reasoning {sum(c.get('reasoning_tokens') or 0 for c in calls)}; "
         f"wall time (sum) {sum(c['wall_seconds'] for c in calls):.1f} s, longest call {max(c['wall_seconds'] for c in calls):.1f} s\n", "\n## Windows\n"]
    for r in res:
        a0 = r.attempts[0]
        L.append(f"### `{r.window_id}`: {r.status} ({a0['mode']})\n")
        L.append(f"- first-attempt: {'PASS' if a0['passed'] else 'FAIL'}" + "".join(f"\n  - `{f['check']}`: {f['detail']}" for f in a0["failures"]) + "".join(f"\n  - warning `{w['check']}`: {w['detail']}" for w in a0.get("warnings", [])) + "\n")
        for a in r.attempts[1:]:
            L.append(f"- retry: {'PASS' if a['passed'] else 'FAIL'}" + "".join(f"\n  - `{f['check']}`: {f['detail']}" for f in a["failures"]) + "\n")
        stored = store.get_memory(r.tier, r.window_id.split("_")[-1], full=False)
        L.append(f"- headline: {stored['gist']['headline']}\n" + "".join(f"- {x}\n" for x in stored["gist"]["sentences"]))
    return "\n".join(L)


def sample_report(cfg: Config, store: MemoryV2Store, sample: list[dict], results: dict, seed: int, log_path: str) -> str:
    L = [f"# Baseline Engine v2: Stage C sample (gist)\n", f"Config `{cfg.version}` | model `{cfg.gist['model']}` reasoning `{cfg.gist['reasoning_effort']}` timeout {cfg.gist['timeout_seconds']}s SDK retries {cfg.gist['sdk_retries']} | "
         f"sample seed {seed} | one window per call | raw log `{log_path}`\n", "## System prompt (identical for every call; verbatim from the spec)\n", "```\n" + SYSTEM_PROMPT + "\n```\n"]
    for s in sample:
        wid = s["window_id"]
        stored = store.get_memory(wid.split("_")[0], wid.rsplit("_", 1)[1] if not wid.startswith("day") else wid[4:])
        L.append(f"\n---\n\n## {s['role']}: `{wid}`\n")
        res = results.get(wid)
        if res is None:
            L.append(f"No call (code line, status `{stored['gist']['status']}`).\n\nStored entry: headline = {stored['gist']['headline']!r}; sentences = {stored['gist']['sentences']}; gist_status = `{stored['gist']['status']}`; is_notable = {stored['is_notable']}; notable_reason = {stored['notable_reason']!r}\n")
            continue
        first = res.attempts[0]
        L += ["### Gist view, exactly as sent (user message of attempt 1)\n", "```\n" + first["prompt_sent"] + "\n```\n"]
        for a in res.attempts:
            u = a["usage"]
            L.append(f"### Attempt {a['n']}\n")
            if a["n"] == 2:
                L += ["Retry message appended (after the system prompt, the original user message and the model's previous answer):\n", "```\n" + a["prompt_sent"] + "\n```\n"]
            L.append("Model output:\n\n```\n" + (a["raw"] if a["raw"] is not None else f"(no answer: {a['error']})") + "\n```\n")
            L.append("Validation: " + ("**PASS** (all four checks)" if a["passed"] else "**FAIL**\n" + "\n".join(f"- `{f['check']}`: {f['detail']}" for f in a["failures"])) + "\n")
            if a.get("warnings"):
                L.append("Warnings (sentence-level direction, counted not rejected):\n" + "\n".join(f"- `{w['check']}`: {w['detail']}" for w in a["warnings"]) + "\n")
            L.append(f"Tokens in {u.get('input_tokens')} / out {u.get('output_tokens')} / reasoning {u.get('reasoning_tokens')}; wall time {u['wall_seconds']} s\n")
        L.append(f"### Stored entry\n\nstatus `{stored['gist']['status']}`\n\n- headline: {stored['gist']['headline']}\n" + "".join(f"- {x}\n" for x in stored['gist']['sentences'])
                 + f"- is_notable (code): {stored['is_notable']}; notable_reason (code): {stored['notable_reason']}\n")
    # summary
    llm = [r for r in results.values()]
    first_fail = [r for r in llm if not r.attempts[0]["passed"]]
    from collections import Counter
    reasons = Counter(f["check"] for r in first_fail for f in r.attempts[0]["failures"])
    final = Counter(r.status for r in llm)
    calls = _unique_calls(llm)
    toks = lambda k: sum((c.get(k) or 0) for c in calls)
    L += ["\n---\n\n## Summary\n", f"- windows sent to the model: {len(llm)} (plus {len(sample) - len(llm)} code-line windows, no call)\n",
          f"- first-attempt failures: {len(first_fail)} of {len(llm)} ({100 * len(first_fail) / max(1, len(llm)):.0f}%)\n",
          f"- first-attempt rejection reasons (count of failures by check): {dict(reasons) or 'none'}\n", f"- final statuses: {dict(final)}\n",
          f"- calls: {len(calls)}; tokens in {toks('input_tokens')}, out {toks('output_tokens')}, reasoning {toks('reasoning_tokens')}; "
          f"wall time (sum of calls) {sum(c['wall_seconds'] for c in calls):.1f} s\n",
          f"- sentence-level direction warnings: {sum(len(a.get('warnings', [])) for r in llm for a in r.attempts)}\n"]
    for r in first_fail:
        L.append(f"- first-attempt failure `{r.window_id}`: " + "; ".join(f"{f['check']}: {f['detail']}" for f in r.attempts[0]["failures"]) + "\n")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description="Baseline Engine v2, Stage C: gist sample and batching test")
    ap.add_argument("--config", default="config/patient_meera_iyer_v1.yaml")
    ap.add_argument("--db", default="output/personal_data_store.db")
    ap.add_argument("--stage", default="C", choices=["C"])
    ap.add_argument("--seed", type=int, default=4817)
    ap.add_argument("--part", default="both", choices=["sample", "batch", "both"])
    ap.add_argument("--sentence-direction", default=None, choices=["strict", "warn"], help="override gist.sentence_direction for this run")
    ap.add_argument("--report-dir", default="output")
    args = ap.parse_args()
    cfg = Config.from_yaml(args.config)
    mode = args.sentence_direction or cfg.gist.get("sentence_direction", "strict")
    store = MemoryV2Store(args.db)
    ro = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    rows = {t: [store.get_memory(t, d, full=True) for (d,) in ro.execute("SELECT end_date FROM memory_v2 WHERE tier = ? ORDER BY end_date", (t,))] for t in ("day", "week", "month")}
    ro.close()
    by_id = {r["window_id"]: r for rs in rows.values() for r in rs}
    client = make_client(cfg)
    stamp = int(time.time())                                                           # a unique log file per run
    if args.part in ("sample", "both"):
        sample = choose_sample(rows, args.seed)
        to_run = [by_id[s["window_id"]] for s in sample if llm_eligible(by_id[s["window_id"]]) and by_id[s["window_id"]]["gist"]["status"] not in ("code_line_early", "code_line_quiet")]
        log_path = f"{args.report_dir}/gist_stage_c_sample_{stamp}.jsonl"
        with open(log_path, "a") as fh:
            results = {r.window_id: r for r in run_gist(cfg, to_run, client, store=store, log=lambda e: (fh.write(json.dumps(e, ensure_ascii=False) + "\n"), fh.flush()),
                                                          batch_size={t: 1 for t in ("day", "week", "month")}, sentence_mode=mode)}
        out = Path(args.report_dir) / "baseline_v2_stage_c_sample.md"
        out.write_text(sample_report(cfg, store, sample, results, args.seed, log_path))
        print(f"sample: {len(results)} windows sent, report in {out}")
    if args.part in ("batch", "both"):
        batch_rows = choose_batch_test(rows, args.seed)
        log_path = f"{args.report_dir}/gist_stage_c_batch_{stamp}.jsonl"
        with open(log_path, "a") as fh:
            results = {r.window_id: r for r in run_gist(cfg, batch_rows, client, store=store, log=lambda e: (fh.write(json.dumps(e, ensure_ascii=False) + "\n"), fh.flush()),
                                                          batch_size={"day": 4, "week": 2, "month": 1}, sentence_mode=mode)}
        out = Path(args.report_dir) / "baseline_v2_stage_c_batch.md"
        out.write_text(batch_report(cfg, store, batch_rows, results, log_path, mode))
        print(f"batch: {len(results)} windows sent, report in {out}")
    store.close()


if __name__ == "__main__":
    main()
