"""Command-line entry point and verification report."""

import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

from v0_code.graph.executor import run_pipeline
from v0_code.graph.state import UMCState


def print_report(state: UMCState) -> None:
    total = sum(state.filter_counts.values())
    print(f"Plausibility Filter: {total} readings -> {state.filter_counts}")

    errors = [r for r in state.filter_results if r.filter_result != "PASS"]
    by_month = Counter((r.biomarker, r.timestamp[:7], r.filter_result) for r in errors)
    print("Rejected readings by (biomarker, month, result):")
    for key, n in sorted(by_month.items()):
        print(f"  {key}: {n}")

    print(f"Threshold Evaluator: {len(state.threshold_results)} readings -> {state.status_counts}")
    print(f"  no threshold row (not evaluated): {state.no_threshold_row}")
    print(f"  reference not applicable (not evaluated): {state.not_applicable}")

    for label, day, biomarker in (
        ("Sep 17 2026 fasting glucose", "2026-09-17", "fasting_glucose"),
        ("Aug 22 2026 lowest CGM reading", "2026-08-22", "cgm_glucose_reading"),
    ):
        rows = [
            r
            for r in state.threshold_results
            if r.biomarker == biomarker and r.timestamp.startswith(day)
        ]
        if biomarker == "cgm_glucose_reading":
            rows = sorted(rows, key=lambda r: r.value)[:1]
        print(f"Spot-check {label}:")
        for r in rows:
            print(f"  {r.model_dump()}")

    print(
        f"Short-Range Event Linker: {state.qualifying_glucose_events} qualifying glucose readings "
        f"(high/low), {state.glucose_events_with_pairings} with >=1 pairing, "
        f"{len(state.pairings)} pairings total -> {state.linker_counts}"
    )

    print(f"Personal Data Store: {state.store_counts}")

    print(f"Baseline Engine (glucose): {state.baseline_counts}")
    if state.baseline_llm_failures:
        print(f"  LLM failures (numeric metrics still stored for these): {state.baseline_llm_failures}")
    notable = [w for w in state.glucose_windows if w.is_notable]
    print(f"  Example notable windows (showing up to 3 of {len(notable)}):")
    for w in notable[:3]:
        print(f"    [{w.window_type} {w.window_start}->{w.window_end}] {w.interpretive_note}")

    print(f"Memory Records (cross-domain, numeric only — LLM step not yet run): {state.memory_counts}")
    for tier, r in state.anchor_report.items():
        fired = ", ".join(f"{k} {v['windows']} ({v['pct']}%)" for k, v in r["fired"].items() if v["windows"])
        print(f"  anchors[{tier}]: {r['any_crossed']}/{r['windows']} windows with a crossing ({r['any_crossed_pct']}%) | {fired}")
        if r["dead"]:
            print(f"    DEAD (configured but never fired): {', '.join(r['dead'])}")

    print(f"Outputs: {state.filter_output}, {state.threshold_output}, {state.linker_output}, {state.store_output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the UMC plausibility + threshold pipeline")
    parser.add_argument("--data-dir", default="final")
    parser.add_argument("--ranges-dir", default="ranges")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--glucose-caption", action="store_true", help="also run the legacy per-window glucose caption LLM (off by default; ~5 min)")
    parser.add_argument("--rebuild", action="store_true",
                        help="rebuild output/personal_data_store.db from scratch. REQUIRED when the database already exists: it wipes every stored memory entry (memory_json, llm_status)")
    args = parser.parse_args()

    db = Path(args.output_dir) / "personal_data_store.db"
    if db.exists() and not args.rebuild:
        print(f"{db} already exists and may hold model-written memory entries. Rebuilding wipes it.\n"
              "Re-run with --rebuild to rebuild it on purpose (back the file up first); nothing was touched.", file=sys.stderr)
        sys.exit(2)

    state = asyncio.run(run_pipeline(args.data_dir, args.ranges_dir, args.output_dir, args.glucose_caption))
    print_report(state)
