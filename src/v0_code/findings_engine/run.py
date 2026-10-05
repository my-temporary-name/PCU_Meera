"""Run the Findings Engine.

    uv run python -m v0_code.findings_engine.run --config config/findings_<patient>.yaml --stage F1       # replay every hand-off in order -> output/findings_engine.db
    uv run python -m v0_code.findings_engine.run --config ... --stage F1 --rebuild                         # drop and recreate the Findings tables first (explicit)
    uv run python -m v0_code.findings_engine.run --config ... --gaps 3 6 12                                # case counts at other gaps (nothing is written)

Stage F1 is the code layer only: cases, versions, factor tables, modes, wording classes, groups, repeat information (PI absent) and the code line. No model is called. The State
Engine, Rulebook Lookup, Evidence Engine and Personal Data Store databases are opened read-only; the only file written is the Findings database."""

import argparse
from pathlib import Path

from v0_code.evidence_engine.library import load_library
from v0_code.findings_engine.audit import audit_versions
from v0_code.findings_engine.config import FindingsConfig
from v0_code.findings_engine.context import Context
from v0_code.findings_engine.inputs import load_inputs
from v0_code.findings_engine.loop import Settings, replay
from v0_code.findings_engine.storage import FindingsStore
from v0_code.intel_common.phrasebook import Phrasebook

ROOT = Path(__file__).resolve().parents[3]


class MissingEvidence(RuntimeError):
    pass


def prepare(cfg: FindingsConfig):
    lib = load_library(cfg.paths["evidence_library"])
    pb = Phrasebook.load(cfg.paths["phrasebook"])
    pb.check(lib)
    data = load_inputs(cfg)
    missing = sorted(h for h, s in data["packet_status"].items() if s == "ok" and h not in data["evidence"])
    if missing:
        raise MissingEvidence(f"{len(missing)} counted hand-offs have no event evidence record (first: {missing[0]}); run the Evidence Engine first")
    return lib, pb, data


def run_replay(cfg: FindingsConfig, lib, pb, data, gap_hours: float | None = None, context=None):
    s = Settings(gap_hours if gap_hours is not None else cfg.gap_hours, cfg.max_span_hours, cfg.tz)
    return replay(data["handoffs"], data["packet_status"], data["evidence"], data["completions"], s, lib, pb, context=context)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--stage", choices=["F1"], default="F1")
    ap.add_argument("--db", help="Findings database path (default: from the config)")
    ap.add_argument("--rebuild", action="store_true", help="drop and recreate the Findings tables first")
    ap.add_argument("--gaps", nargs="+", type=float, help="print the case counts at these gaps (hours) and write nothing")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = FindingsConfig.from_yaml(Path(a.config) if Path(a.config).is_absolute() else root / a.config, root)
    lib, pb, data = prepare(cfg)
    if a.gaps:
        for g in a.gaps:
            r = run_replay(cfg, lib, pb, data, g)
            print(f"gap {g:g} h: {len(r.cases)} cases, {sum(c['n_counted'] for c in r.cases)} counted hand-offs, {len(r.versions)} versions, {len(r.unattached)} unattached")
        return 0
    ctx = Context(cfg)
    result = run_replay(cfg, lib, pb, data, context=ctx)
    ctx.close()
    bad, n = audit_versions(result.versions, cfg)
    if bad:
        print("AS-OF AUDIT FAILED:\n" + "\n".join(bad[:20]))
        return 1
    store = FindingsStore(a.db or cfg.paths["db_path"], rebuild=a.rebuild)
    counts = store.write_replay(result, {"method_version": cfg.method_version, "config_version": cfg.version, "phrasebook_version": pb.raw.get("version", ""), "library_version": lib.version})
    store.close()
    print(f"{len(result.cases)} cases, {len(result.versions)} versions ({counts['written']} written, {counts['same']} already stored), {len(result.unattached)} unattached; as-of audit clean {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
