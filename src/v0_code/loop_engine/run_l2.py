"""Run the loop with the models, stage L2.

    uv run python -m v0_code.loop_engine.run_l2 --config config/loop_<patient>.yaml                 # Findings + PI LIVE with the models -> output/findings_loop_full.db + output/pi_loop_full.db
    uv run python -m v0_code.loop_engine.run_l2 --config ... --no-network                           # no model call at all (a rerun: every text comes from the stored answers)
    uv run python -m v0_code.loop_engine.run_l2 --config ... --findings-db A --pi-db B --cache-from F P --no-network    # a rerun into fresh databases, answers read from the first run's (zero calls)

Writes only the L2 databases (and nothing of F1 / F2 / P1 / L1 or upstream). A stop rule ends the run with everything saved; running again continues."""

import argparse
from pathlib import Path

from v0_code.findings_engine import llm
from v0_code.loop_engine import regress
from v0_code.loop_engine.config import LoopConfig
from v0_code.loop_engine.l2 import StopLoop, run_l2
from v0_code.loop_engine.run import audits
from v0_code.pi_engine.run_text import NoNetwork

ROOT = Path(__file__).resolve().parents[3]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--findings-db")
    ap.add_argument("--pi-db")
    ap.add_argument("--cache-from", nargs=2, metavar=("FINDINGS_DB", "PI_DB"), help="read-only databases of an earlier L2 run whose answers may be reused for any view")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--no-f2", action="store_true", help="do not reuse answers from the F2 database")
    ap.add_argument("--rebuild", action="store_true", help="drop and recreate the L2 tables first (explicit)")
    ap.add_argument("--no-audit", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = LoopConfig.from_yaml(Path(a.config) if Path(a.config).is_absolute() else root / a.config, root)
    client = NoNetwork() if a.no_network else llm.make_client(cfg.findings.text)
    seeds, pi_seeds = ((a.cache_from[0],), (a.cache_from[1],)) if a.cache_from else ((), ())
    try:
        res = run_l2(cfg, client, rebuild=a.rebuild, findings_db=a.findings_db, pi_db=a.pi_db, seeds=seeds, pi_seeds=pi_seeds, use_f2=not a.no_f2)
    except StopLoop as e:
        print("STOPPED:", e)
        return 2
    c = res.counters
    calls = [x for x in res.log["calls"] if not x["from_cache"]]
    print(f"{len(res.replay.cases)} cases, {len(res.replay.versions)} versions; weeks run {res.notes['weeks_run']} (skipped {res.notes['weeks_skipped']}); model calls {c.calls} "
          f"({sum(x['phase'] == 'findings_text' for x in calls)} Findings texts, {sum(x['phase'] == 'pi_line' for x in calls)} PI lines); first-attempt failures {c.first_fail} of {c.versions}; "
          f"call errors {c.call_errors}; reused answers {sum(x['from_cache'] for x in res.log['calls'])}")
    if a.no_audit:
        return 0
    import dataclasses
    run_cfg = dataclasses.replace(cfg, findings_db=res.findings_db, pi_db=res.pi_db)
    bad, n = audits(run_cfg, list(regress.records(res.findings_db).values()))
    print("as-of audits:", "clean" if not bad else f"{len(bad)} VIOLATIONS", n)
    for b in bad[:20]:
        print("  ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
