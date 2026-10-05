"""State Engine's own tables (spec 7.2): `state_log` (append-only, one row per tick), `state_items` (one row per deviation item) and `state_handoffs`
(the hand-off record, written to a log only: nothing reads it yet). They live in the State Engine's own SQLite file; the Personal Data Store and the
Baseline Engine's tables are never written. Writes are upserts, so running the same tick again writes the same rows (idempotent)."""

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS state_log (
    as_of TEXT PRIMARY KEY,              -- the tick timestamp
    baseline_asof TEXT,
    config_version TEXT,
    n_open_items INTEGER,
    any_stale INTEGER,
    snapshot_json TEXT
);
CREATE TABLE IF NOT EXISTS state_items (
    item_id TEXT PRIMARY KEY,            -- <measure>_<opened_at>
    measure TEXT, direction TEXT, size_at_open TEXT, size_peak TEXT,
    opened_at TEXT, peak_at TEXT, closed_at TEXT, peak_value TEXT,
    trigger TEXT, status TEXT, handed_off_at TEXT, context_json TEXT,
    item_class TEXT,                     -- adverse | favourable (a favourable item is recorded but not handed off)
    close_reason TEXT,                   -- recovered | stale (continuous value past its freshness limit) | expired (daily / periodic measure overdue)
    peak_metric REAL                     -- internal: |z| (or 1 - share) at the peak, so a restart continues the same comparison
);
CREATE TABLE IF NOT EXISTS state_handoffs (
    handoff_id TEXT PRIMARY KEY,
    item_id TEXT, written_at TEXT, record_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_state_items_measure ON state_items (measure, opened_at);
"""


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False)


class StateStore:
    def __init__(self, path: str | Path, rebuild: bool = False, readonly: bool = False):
        self.path = Path(path)
        if readonly:
            self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.path)
            if rebuild:
                for t in ("state_log", "state_items", "state_handoffs"):
                    self.conn.execute(f"DROP TABLE IF EXISTS {t}")                    # only on an explicit request
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def write_tick(self, snapshot: dict, items: list[dict], handoffs: list[dict]) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO state_log (as_of, baseline_asof, config_version, n_open_items, any_stale, snapshot_json) VALUES (?, ?, ?, ?, ?, ?)",
                              (snapshot["as_of"], snapshot["baseline_asof"], snapshot["config_version"], len(snapshot["open_items"]),
                               int(any(q.startswith(("stale:", "overdue:")) for q in snapshot["quality"])), _j(snapshot)))      # any_stale: stale continuous or overdue daily / periodic only
            for it in items:
                self.conn.execute(
                    "INSERT OR REPLACE INTO state_items (item_id, measure, direction, size_at_open, size_peak, opened_at, peak_at, closed_at, peak_value, trigger, status, handed_off_at, "
                    "context_json, close_reason, peak_metric, item_class) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (it["item_id"], it["measure"], it["direction"], it["size_at_open"], it["size_peak"], it["opened_at"], it["peak_at"], it["closed_at"], _j(it["peak_value"]),
                     it["trigger"], it["status"], it["handed_off_at"], _j(it["context"]), it["close_reason"], it["peak_metric"], it["item_class"]))
            for h in handoffs:
                self.conn.execute("INSERT OR IGNORE INTO state_handoffs (handoff_id, item_id, written_at, record_json) VALUES (?, ?, ?, ?)",
                                  (h["handoff_id"], h["item_id"], h["written_at"], _j(h)))

    # ---- reads ------------------------------------------------------------------------------------------------------------------------------
    def latest_snapshot(self) -> dict | None:
        """The live state: the newest state_log row (there is no second copy)."""
        r = self.conn.execute("SELECT snapshot_json FROM state_log ORDER BY as_of DESC LIMIT 1").fetchone()
        return json.loads(r[0]) if r else None

    def snapshot_at(self, as_of: str) -> dict | None:
        r = self.conn.execute("SELECT snapshot_json FROM state_log WHERE as_of = ?", (as_of,)).fetchone()
        return json.loads(r[0]) if r else None

    def items(self, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM state_items" + (" WHERE status = ?" if status else "") + " ORDER BY opened_at, item_id"
        rows = self.conn.execute(q, (status,) if status else ()).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["peak_value"] = json.loads(d["peak_value"])
            d["context"] = json.loads(d.pop("context_json"))
            out.append(d)
        return out

    def handoffs(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.conn.execute("SELECT record_json FROM state_handoffs ORDER BY written_at, handoff_id")]
