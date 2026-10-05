"""Run the loop, stage L1 (code layer only, no model).

    uv run python -m v0_code.loop_engine.run --config config/loop_<patient>.yaml                    # Findings live with PI -> output/findings_loop.db + output/pi_loop.db, then the audits
    uv run python -m v0_code.loop_engine.run --config ... --max-events 120                          # stop after 120 events; running again continues
    uv run python -m v0_code.loop_engine.run --config ... --rebuild                                 # drop and recreate the loop's own tables first (explicit)

Writes only the loop's two databases. The F1 / F2 / P1 outputs, Evidence, Rulebook, State and Store databases are never written."""

import argparse
from pathlib import Path

from v0_code.findings_engine.audit import audit_versions
from v0_code.loop_engine import audit as laudit
from v0_code.loop_engine.config import LoopConfig
from v0_code.loop_engine.driver import run_loop
from v0_code.pi_engine.audit import audit_pi

ROOT = Path(__file__).resolve().parents[3]


def audits(cfg: LoopConfig, versions: list[dict]) -> tuple[list[str], dict]:
    """The Findings as-of audit (evidence and diary), PI's own as-of audit (labels), and the audit of PI reads made by Findings."""
    bad, n = audit_versions(versions, cfg.findings)
    pbad, pn = audit_pi(cfg.pi_db, cfg.pi.paths["evidence_db"], cfg.findings_db, cfg.pi)
    rbad, rn = laudit.audit_pi_reads(cfg.findings_db, cfg.pi_db, cfg.findings.tz, cfg.findings.seen_before_bands, int(cfg.findings.pi.get("mid_term_recent_weeks", 2)),
                                     bool(cfg.findings.pi.get("include_open_week", True)), strict=True)
    return bad + pbad + rbad, {"findings": n, "pi": pn, "pi_reads": rn}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--max-events", type=int)
    ap.add_argument("--no-audit", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = LoopConfig.from_yaml(Path(a.config) if Path(a.config).is_absolute() else root / a.config, root)
    res = run_loop(cfg, rebuild=a.rebuild, max_events=a.max_events)
    r = res.replay
    print(f"{len(r.cases)} cases, {len(r.versions)} versions ({res.counts['written']} written, {res.counts['same']} already stored); PI: {res.counts['weeks_run']} weekly jobs "
          f"({res.counts['weeks_new']} new), {res.counts['entries_written']} entries written, {res.counts['entries_same']} already recorded; {len(res.live.reads)} PI reads" + ("; STOPPED early" if res.stopped else ""))
    if res.stopped or a.no_audit:
        return 0
    bad, n = audits(cfg, r.versions)
    print("as-of audits:", "clean" if not bad else f"{len(bad)} VIOLATIONS", n)
    for b in bad[:20]:
        print("  ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
