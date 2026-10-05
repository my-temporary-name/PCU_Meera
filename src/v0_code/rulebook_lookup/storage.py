"""The packet log (spec 7.2, Amendments 11): its own SQLite file, one table, no timestamp (a re-run gives identical rows). A write replaces the row of the same
packet_id; the table is dropped only by an explicit rebuild."""

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS rulebook_packets (
    packet_id TEXT PRIMARY KEY,
    handoff_id TEXT,
    rule_id TEXT,                         -- null when unmatched
    status TEXT,                          -- ok | deferred | unmatched | ambiguous
    rulebook_version TEXT,
    n_selected INTEGER, n_skipped INTEGER, n_not_selected INTEGER,
    packet_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_rulebook_packets_rule ON rulebook_packets (rule_id);
"""


class PacketStore:
    def __init__(self, path: str | Path, rebuild: bool = False, readonly: bool = False):
        self.path = Path(path)
        if readonly:
            self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.path)
            if rebuild:
                self.conn.execute("DROP TABLE IF EXISTS rulebook_packets")           # only on an explicit request
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def write(self, packet: dict) -> None:
        rule = packet["matched_rule"]["rule_id"] if packet["matched_rule"] else None
        c = packet["counts"]
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO rulebook_packets (packet_id, handoff_id, rule_id, status, rulebook_version, n_selected, n_skipped, n_not_selected, packet_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (packet["packet_id"], packet["handoff_id"], rule, packet.get("status", "ok"), packet["rulebook_version"], c["selected"], c["skipped"], c["not_selected"],
                 json.dumps(packet, ensure_ascii=False)))

    def packets(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.conn.execute("SELECT packet_json FROM rulebook_packets ORDER BY handoff_id")]

    def get(self, packet_id: str) -> dict | None:
        r = self.conn.execute("SELECT packet_json FROM rulebook_packets WHERE packet_id = ?", (packet_id,)).fetchone()
        return json.loads(r[0]) if r else None
