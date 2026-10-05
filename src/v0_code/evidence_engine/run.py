"""Run the Evidence Engine.

    uv run python -m v0_code.evidence_engine.run --config config/evidence_<patient>.yaml --stage A      # the daily refresh for every day of the record -> relationship_evidence
    uv run python -m v0_code.evidence_engine.run --config ... --stage B                                  # event evidence for every packet (replay in time order) + completions
    uv run python -m v0_code.evidence_engine.run --config ... --stage A --from 2026-09-17 --to 2026-09-17
    uv run python -m v0_code.evidence_engine.run --config ... --stage A --rebuild                       # drop and recreate the Evidence Engine's own tables first (explicit)

The Personal Data Store, the State Engine and Rulebook Lookup databases are opened read-only; only the Evidence Engine's own database is written."""

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.loader import load_data, resolve
from v0_code.evidence_engine.refresh import DailyRefresh
from v0_code.evidence_engine.storage import EvidenceStore

ROOT = Path(__file__).resolve().parents[3]


def date_range(refresh: DailyRefresh) -> tuple[date, date]:
    ds = [u.date for o in refresh.lib.outcomes for us in refresh.units(o).values() for u in us]
    return min(ds), max(ds)


def stage_b(cfg, lib, data, store, refresh, root, conn) -> int:
    """Event evidence for every packet, in the order the hand-offs opened. After each record the completion step runs (in a replay the data already exists)."""
    from datetime import datetime
    from v0_code.evidence_engine.events import EventEngine
    from v0_code.rulebook_lookup.storage import PacketStore
    from v0_code.state_engine.storage import StateStore
    packets = PacketStore(resolve(root, cfg.paths["packets_db"]), readonly=True)
    handoffs = StateStore(resolve(root, cfg.paths["handoffs_db"]), readonly=True)
    by_id = {h["handoff_id"]: h for h in handoffs.handoffs()}
    todo = sorted(packets.packets(), key=lambda p: (datetime.fromisoformat(by_id[p["handoff_id"]]["opened_at"]), p["handoff_id"]))
    eng = EventEngine(data, lib, cfg, store, refresh)
    t0, how, done = time.perf_counter(), {}, 0
    for p in todo:
        _, h = eng.process(p, by_id[p["handoff_id"]])
        how[h] = how.get(h, 0) + 1
        done += len(eng.complete(f"ev_{p['handoff_id']}"))
    store.close()
    packets.close()
    handoffs.close()
    conn.close()
    print(f"event evidence: {len(todo)} packets {how}, {done} completions, {time.perf_counter() - t0:.1f} s")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--stage", default="A", choices=["A", "B"])
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--db", help="the Evidence Engine's own database (default: from the config)")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = EvidenceConfig.from_yaml(resolve(root, a.config), root)
    lib, data, conn = load_data(cfg, root)
    store = EvidenceStore(Path(a.db) if a.db else resolve(root, cfg.paths["db_path"]), rebuild=a.rebuild)
    refresh = DailyRefresh(data, lib, cfg, store)
    if a.stage == "B":
        return stage_b(cfg, lib, data, store, refresh, root, conn)
    first, last = date_range(refresh)
    first = date.fromisoformat(a.start) if a.start else first
    last = date.fromisoformat(a.end) if a.end else last
    t0, n, records = time.perf_counter(), 0, 0
    d = first
    while d <= last:
        s = refresh.refresh(d)
        n += 1
        records += s["n_relationships"]
        d += timedelta(days=1)
    store.close()
    conn.close()
    print(f"daily refresh {first} to {last}: {n} days, {records} relationship records, {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
