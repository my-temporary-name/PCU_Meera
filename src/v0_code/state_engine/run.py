"""Run the State Engine.

    uv run python -m v0_code.state_engine.run --replay                       # every tick of the record, into output/state_engine.db
    uv run python -m v0_code.state_engine.run --replay --from 2026-09-17 --to 2026-09-17
    uv run python -m v0_code.state_engine.run --replay --rebuild             # drop and recreate the state tables first (explicit)

The Personal Data Store is opened read-only. A replay steps tick by tick with the same rules as live; "now" is the tick being evaluated."""

import argparse
import sqlite3
from datetime import date as _date, datetime, timedelta
from pathlib import Path

from v0_code.state_engine.baseline import BaselineView
from v0_code.state_engine.config import StateConfig
from v0_code.state_engine.engine import StateEngine
from v0_code.state_engine.inputs import StateInputs
from v0_code.state_engine.storage import StateStore


def build_engine(cfg: StateConfig, db: str) -> tuple[StateEngine, sqlite3.Connection]:
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    return StateEngine(cfg, StateInputs(ro, cfg), BaselineView(ro)), ro


def resume(engine: StateEngine, store: StateStore) -> datetime | None:
    """Restore the engine's memory (last values, runs, open items) from the newest state_log row so a later run continues exactly where the last one stopped.
    Returns the as_of of that snapshot (the next tick to run is one tick later), or None for an empty log."""
    from bisect import bisect_right
    snap = store.latest_snapshot()
    if snap is None:
        return None
    as_of = datetime.fromisoformat(snap["as_of"])
    items = {i["item_id"]: i for i in store.items("open")}
    handed = {h["handoff_id"] for h in store.handoffs()}
    engine._handed = set(handed)
    for name, st in engine.states.items():
        s = st.cfg
        st.seen_idx = bisect_right(engine.inputs._avail[name], as_of) - 1
        m = snap["measures"].get(s.key, {})
        if m.get("value_time"):
            vt = datetime.fromisoformat(m["value_time"])
            st.value = next((o for o in reversed(engine.inputs.obs[name][:st.seen_idx + 1]) if o.value_time == vt and not o.rejected), None)
        st.rejected_latest = bool(m.get("rejected_latest"))
        st.stale_handled = bool(st.value and (m.get("overdue") if s.tracks_overdue else (s.kind == "continuous" and not m.get("current", True))))
        run = m.get("run")
        if run:
            st.tracker.run_direction, st.tracker.run_count, st.tracker.close_count = run["direction"], run["count"], run["close_count"]
        oid = m.get("open_item_id")
        if oid and oid in items:
            it = items[oid]
            st.item = {**it, "peak_metric": it["peak_metric"]}
            st.tracker.open, st.tracker.open_direction = True, it["direction"]
    return as_of


def replay(engine: StateEngine, store: StateStore, start: _date | datetime | None = None, end: _date | None = None, say=print) -> dict:
    n = 0
    n_items = n_hand = 0
    first = last = None
    for as_of in engine.ticks(start, end):
        snap = engine.tick(as_of)
        store.write_tick(snap, engine.items_changed, engine.handoffs)
        n += 1
        n_items += len(engine.items_changed)
        n_hand += len(engine.handoffs)
        first = first or snap["as_of"]
        last = snap["as_of"]
    return {"ticks": n, "first": first, "last": last, "items_written": n_items, "handoffs": n_hand}


def main() -> None:
    ap = argparse.ArgumentParser(description="State Engine")
    ap.add_argument("--config", default="config/state_meera_iyer_v1.yaml")
    ap.add_argument("--db", default="output/personal_data_store.db", help="the Personal Data Store (opened read-only)")
    ap.add_argument("--state-db", default=None, help="the State Engine's own database (default: state.db_path from the config)")
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--from", dest="start", default=None)
    ap.add_argument("--to", dest="end", default=None)
    ap.add_argument("--rebuild", action="store_true", help="drop and recreate the state tables (explicit; the store is never touched)")
    args = ap.parse_args()
    cfg = StateConfig.from_yaml(args.config, root=Path.cwd())
    engine, ro = build_engine(cfg, args.db)
    store = StateStore(args.state_db or cfg.db_path, rebuild=args.rebuild)
    start = _date.fromisoformat(args.start) if args.start else None
    end = _date.fromisoformat(args.end) if args.end else None
    if not args.replay:
        ap.error("nothing to do: pass --replay")
    last = resume(engine, store)                           # an existing log is continued, never rewritten: the next tick is the one after the last logged tick
    begin = datetime.combine(start, datetime.min.time(), tzinfo=cfg.tz) if start else None
    if last is not None:
        nxt = last + timedelta(minutes=cfg.tick_minutes)
        if begin is not None and begin < nxt:
            ap.error(f"the log already runs to {last.isoformat()}; replaying earlier ticks needs --rebuild")
        begin = begin or nxt
    print(replay(engine, store, begin, end))
    store.close()
    ro.close()


if __name__ == "__main__":
    main()
