"""Run the Baseline Engine v2.

    uv run python -m v0_code.baseline_v2.run --stage A                 # day tier, no LLM; upserts memory_v2 (never wipes)
    uv run python -m v0_code.baseline_v2.run --stage A --rebuild       # drops and recreates memory_v2 only (v1 tables untouched)
"""

import argparse
import sqlite3
from pathlib import Path

from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.data import StoreView
from v0_code.baseline_v2.engine import build_days, build_windows
from v0_code.baseline_v2.report import md_report, sample_entries_md, stage_b_entries_md, stage_b_report
from v0_code.baseline_v2.storage import MemoryV2Store


def run_stage_a(cfg: Config, db: str, rebuild: bool = False) -> list[dict]:
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    view = StoreView(ro, cfg)
    rows = build_days(cfg, view)
    store = MemoryV2Store(db, rebuild=rebuild)
    store.upsert(rows)
    store.close()
    ro.close()
    return rows


def run_stage_b(cfg: Config, db: str, rebuild: bool = False) -> dict[str, list[dict]]:
    """Stage B: the week and month tiers (the day rows are rebuilt and upserted with them; the result is identical)."""
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    out = build_windows(cfg, StoreView(ro, cfg))
    store = MemoryV2Store(db, rebuild=rebuild)
    store.upsert([r for tier in ("day", "week", "month") for r in out[tier]])
    store.close()
    ro.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Baseline Engine v2")
    ap.add_argument("--config", default="config/patient_meera_iyer_v1.yaml")
    ap.add_argument("--db", default="output/personal_data_store.db")
    ap.add_argument("--stage", default="A", choices=["A", "B"])
    ap.add_argument("--rebuild", action="store_true", help="drop and recreate memory_v2 (the v1 tables are never touched)")
    ap.add_argument("--report-dir", default="output")
    args = ap.parse_args()
    cfg = Config.from_yaml(args.config)
    out = Path(args.report_dir)
    if args.stage == "B":
        by_tier = run_stage_b(cfg, args.db, args.rebuild)
        ro = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
        (out / "baseline_v2_stage_b_report.md").write_text(stage_b_report(cfg, by_tier, ro))
        (out / "baseline_v2_stage_b_entries.md").write_text(stage_b_entries_md(cfg, by_tier))
        print(f"Stage B: {len(by_tier['week'])} week and {len(by_tier['month'])} month windows written to memory_v2 ({cfg.version}); reports in {out}/baseline_v2_stage_b_*.md")
        return
    rows = run_stage_a(cfg, args.db, args.rebuild)
    ro = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    (out / "baseline_v2_stage_a_report.md").write_text(md_report(cfg, rows, ro, "A"))
    (out / "baseline_v2_stage_a_day_entries.md").write_text(sample_entries_md(rows))
    print(f"Stage A: {len(rows)} day windows written to memory_v2 ({cfg.version}); reports in {out}/baseline_v2_stage_a_*.md")


if __name__ == "__main__":
    main()
