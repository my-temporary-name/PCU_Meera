"""The Evidence Engine's own database (spec 9.3). No table holds a wall-clock timestamp, so a re-run produces identical rows. A relationship record is reused for the
same key, date, method version and inputs hash; a changed inputs hash marks the old record superseded and writes the new one."""

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS relationship_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id TEXT NOT NULL,                -- rel|<key>|<as-of date>|<method version>
    relationship_key TEXT, as_of_date TEXT, method_version TEXT, config_version TEXT,
    inputs_hash TEXT,
    status TEXT,                              -- current | superseded
    record_json TEXT,
    UNIQUE (evidence_id, inputs_hash)
);
CREATE INDEX IF NOT EXISTS idx_rel_date ON relationship_evidence (as_of_date, status);
CREATE INDEX IF NOT EXISTS idx_rel_id ON relationship_evidence (evidence_id, status);
CREATE TABLE IF NOT EXISTS event_evidence (
    evidence_id TEXT PRIMARY KEY,             -- ev_<handoff_id>
    packet_id TEXT, handoff_id TEXT, rule_id TEXT, event_time TEXT, as_of_date TEXT,
    record_json TEXT
);
CREATE TABLE IF NOT EXISTS event_completions (
    evidence_id TEXT NOT NULL,                -- the event record it completes
    candidate TEXT NOT NULL,
    support TEXT, result_json TEXT, evaluated_from TEXT,
    PRIMARY KEY (evidence_id, candidate)
);
CREATE TABLE IF NOT EXISTS evidence_runs (
    as_of_date TEXT NOT NULL, method_version TEXT NOT NULL,
    n_relationships INTEGER, n_tested INTEGER, family_size INTEGER, placebo_tested INTEGER, placebo_fired INTEGER,
    counts_json TEXT, summary_json TEXT,
    PRIMARY KEY (as_of_date, method_version)
);
"""

TABLES = ("relationship_evidence", "event_evidence", "event_completions", "evidence_runs")


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=False)


class EvidenceStore:
    def __init__(self, path: str | Path, rebuild: bool = False, readonly: bool = False):
        self.path = Path(path)
        if readonly:
            self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.path)
            if rebuild:
                for t in TABLES:
                    self.conn.execute(f"DROP TABLE IF EXISTS {t}")                    # only on an explicit request
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    # ---- relationship evidence ------------------------------------------------------------------------------------------------------------------------
    def put_relationship(self, rec: dict) -> str:
        """D4: nothing for the same id and inputs hash; a different hash supersedes the current record. Returns what happened."""
        with self.conn:
            if self.conn.execute("SELECT 1 FROM relationship_evidence WHERE evidence_id = ? AND inputs_hash = ?", (rec["evidence_id"], rec["inputs_hash"])).fetchone():
                return "reused"
            old = self.conn.execute("UPDATE relationship_evidence SET status = 'superseded' WHERE evidence_id = ? AND status = 'current'", (rec["evidence_id"],)).rowcount
            self.conn.execute(
                "INSERT INTO relationship_evidence (evidence_id, relationship_key, as_of_date, method_version, config_version, inputs_hash, status, record_json) VALUES (?, ?, ?, ?, ?, ?, 'current', ?)",
                (rec["evidence_id"], rec["relationship_key"], rec["as_of_date"], rec["method_version"], rec["config_version"], rec["inputs_hash"], _j({**rec, "status": "current"})))
            return "superseded" if old else "written"

    def get_relationship(self, evidence_id: str) -> dict | None:
        r = self.conn.execute("SELECT record_json FROM relationship_evidence WHERE evidence_id = ? AND status = 'current'", (evidence_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def relationships_on(self, as_of_date: str) -> list[dict]:
        return [json.loads(r[0]) for r in self.conn.execute("SELECT record_json FROM relationship_evidence WHERE as_of_date = ? AND status = 'current' ORDER BY id", (as_of_date,))]

    def has_date(self, as_of_date: str, method_version: str) -> bool:
        return self.conn.execute("SELECT 1 FROM evidence_runs WHERE as_of_date = ? AND method_version = ?", (as_of_date, method_version)).fetchone() is not None

    # ---- event evidence and completions ------------------------------------------------------------------------------------------------------------------
    def put_event(self, rec: dict) -> str:
        """An event record is never changed after it is written (spec 13.7). Returns written, same, or differs (the stored record stays)."""
        new = _j(rec)
        with self.conn:
            old = self.conn.execute("SELECT record_json FROM event_evidence WHERE evidence_id = ?", (rec["evidence_id"],)).fetchone()
            if old is None:
                self.conn.execute("INSERT INTO event_evidence (evidence_id, packet_id, handoff_id, rule_id, event_time, as_of_date, record_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (rec["evidence_id"], rec["packet_id"], rec["handoff_id"], rec["rule_id"], rec["event_time"], rec["as_of_date"], new))
                return "written"
        return "same" if old[0] == new else "differs"

    def get_event(self, evidence_id: str) -> dict | None:
        r = self.conn.execute("SELECT record_json FROM event_evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def events(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.conn.execute("SELECT record_json FROM event_evidence ORDER BY event_time, evidence_id")]

    def put_completion(self, evidence_id: str, candidate: str, support: str, result: dict, evaluated_from: dict) -> bool:
        with self.conn:
            return self.conn.execute("INSERT OR IGNORE INTO event_completions (evidence_id, candidate, support, result_json, evaluated_from) VALUES (?, ?, ?, ?, ?)",
                                     (evidence_id, candidate, support, _j(result), _j(evaluated_from))).rowcount == 1

    def completions(self) -> list[dict]:
        return [{"evidence_id": r[0], "candidate": r[1], "support": r[2], "result": json.loads(r[3]), "evaluated_from": json.loads(r[4])}
                for r in self.conn.execute("SELECT evidence_id, candidate, support, result_json, evaluated_from FROM event_completions ORDER BY evidence_id, candidate")]

    # ---- runs ---------------------------------------------------------------------------------------------------------------------------------------
    def put_run(self, as_of_date: str, method_version: str, summary: dict) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO evidence_runs (as_of_date, method_version, n_relationships, n_tested, family_size, placebo_tested, placebo_fired, counts_json, summary_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (as_of_date, method_version, summary["n_relationships"], summary["n_tested"], summary["family_size"], summary["placebo_tested"], summary["placebo_fired"],
                 _j(summary["counts"]), _j(summary)))

    def runs(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.conn.execute("SELECT summary_json FROM evidence_runs ORDER BY as_of_date")]
