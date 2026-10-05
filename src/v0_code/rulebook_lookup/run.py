"""Run Rulebook Lookup.

    uv run python -m v0_code.rulebook_lookup.run --config config/rulebook_<patient>.yaml                          # one packet per hand-off in output/state_engine.db -> output/rulebook_lookup.db (replaces by packet_id)
    uv run python -m v0_code.rulebook_lookup.run --print <handoff_id>
    uv run python -m v0_code.rulebook_lookup.run --rebuild                # drop and recreate the packet table first (explicit)

The State Engine database is opened read-only; the Personal Data Store is not opened."""

import argparse
import json
from collections import Counter
from pathlib import Path

from v0_code.rulebook_lookup.config import RulebookConfig
from v0_code.rulebook_lookup.lookup import build_packet
from v0_code.rulebook_lookup.report import render
from v0_code.rulebook_lookup.rulebook import load_rulebook
from v0_code.rulebook_lookup.storage import PacketStore
from v0_code.state_engine.storage import StateStore

ROOT = Path(__file__).resolve().parents[3]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="the patient's rulebook config, e.g. config/rulebook_<patient>.yaml")
    ap.add_argument("--root", default=str(ROOT), help="directory the relative paths in the config are resolved against")
    ap.add_argument("--db", help="packet log path (default: from the config)")
    ap.add_argument("--rebuild", action="store_true", help="drop and recreate the packet table first")
    ap.add_argument("--no-report", action="store_true", help="do not write the markdown report")
    ap.add_argument("--print", dest="show", metavar="HANDOFF_ID", help="print the packet of one hand-off (as JSON) after the run")
    a = ap.parse_args(argv)

    root = Path(a.root)
    cfg_path = Path(a.config) if Path(a.config).is_absolute() else root / a.config
    cfg = RulebookConfig.from_yaml(cfg_path, root)
    book = load_rulebook(cfg.rulebook_path(root), cfg)
    state = StateStore(root / cfg.state_db if not Path(cfg.state_db).is_absolute() else cfg.state_db, readonly=True)
    handoffs = state.handoffs()
    state.close()

    packets = [build_packet(h, book, cfg) for h in handoffs]
    db = Path(a.db) if a.db else (root / cfg.db_path if not Path(cfg.db_path).is_absolute() else Path(cfg.db_path))
    store = PacketStore(db, rebuild=a.rebuild)
    for p in packets:
        store.write(p)
    store.close()

    status = Counter(p.get("status", "ok") for p in packets)
    print(f"rulebook {book.version} ({book.review_status}): {len(packets)} packets -> {db}; " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())))
    if not a.no_report:
        rp = root / cfg.report_path if not Path(cfg.report_path).is_absolute() else Path(cfg.report_path)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(render(packets, book))
        print(f"report -> {rp}")
    if a.show:
        p = next((p for p in packets if p["handoff_id"] == a.show), None)
        print(json.dumps(p, indent=2, ensure_ascii=False) if p else f"no hand-off {a.show}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
