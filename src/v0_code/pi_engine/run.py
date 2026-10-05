"""Run PI.

    uv run python -m v0_code.pi_engine.run --config config/pi_<patient>.yaml                    # replay the stored Findings versions -> output/pi.db (idempotent, resumable)
    uv run python -m v0_code.pi_engine.run --config ... --mode code_only                        # the Findings code line instead of the final text
    uv run python -m v0_code.pi_engine.run --config ... --rebuild                               # drop and recreate PI's own tables first (explicit)
    uv run python -m v0_code.pi_engine.run --config ... --max-events 50                         # stop after 50 events (a later run continues)

Stage P1 is the code layer only: no model is called. The Findings, Evidence and Personal Data Store databases are opened read-only; the only file written is PI's own."""

import argparse
from pathlib import Path

from v0_code.evidence_engine.library import load_library
from v0_code.intel_common.phrasebook import Phrasebook
from v0_code.pi_engine.audit import audit_pi
from v0_code.pi_engine.config import PiConfig
from v0_code.pi_engine.driver import FindingsSource, replay
from v0_code.pi_engine.engine import Pi
from v0_code.pi_engine.labels import EvidenceLabels
from v0_code.pi_engine.storage import PiStore

ROOT = Path(__file__).resolve().parents[3]


def build(cfg: PiConfig, rebuild: bool = False, db: str | None = None) -> Pi:
    lib = load_library(cfg.paths["evidence_library"])
    pb = Phrasebook.load(cfg.paths["phrasebook"])
    pb.check(lib)                                                                    # property 17: every relationship has a phrase, every status a wording rule
    return Pi(cfg, PiStore(db or cfg.paths["db_path"], rebuild=rebuild), EvidenceLabels(cfg.paths["evidence_db"]), lib, pb)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--mode", choices=["full", "code_only"])
    ap.add_argument("--db", help="PI database path (default: from the config)")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--max-events", type=int)
    ap.add_argument("--no-audit", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = PiConfig.from_yaml(Path(a.config) if Path(a.config).is_absolute() else root / a.config, root)
    pi = build(cfg, a.rebuild, a.db)
    rep = replay(pi, FindingsSource(cfg.paths["findings_db"]), cfg, mode=a.mode, max_events=a.max_events)
    print(" ".join(f"{k} {v}" for k, v in rep.items()))
    if rep["stopped"] or a.no_audit:
        return 0
    bad, n = audit_pi(a.db or cfg.paths["db_path"], cfg.paths["evidence_db"], cfg.paths["findings_db"], cfg)
    print("as-of audit:", "clean" if not bad else f"{len(bad)} VIOLATIONS", n)
    for b in bad[:20]:
        print("  ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
