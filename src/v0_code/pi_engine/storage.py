"""PI's own database (pi_spec.md 12.4 and amendments 37, 38). Every table is append-only: a row is inserted once and never changed; a sealed week is a second row. No table holds a
wall-clock time: `written_at` is the replay clock, `written_ts` the same moment as epoch seconds for as-of comparisons."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS pi_mid_memories (
    memory_id TEXT NOT NULL, status TEXT NOT NULL, week_iso TEXT, week_start TEXT, week_end TEXT, written_at TEXT, written_ts INTEGER, sealed_at TEXT, record_json TEXT,
    PRIMARY KEY (memory_id, status)
);
CREATE TABLE IF NOT EXISTS pi_mid_entries (
    finding_id TEXT PRIMARY KEY, memory_id TEXT NOT NULL, case_id TEXT NOT NULL, entry_version INTEGER NOT NULL, local_date TEXT, written_at TEXT, written_ts INTEGER, entry_json TEXT NOT NULL,
    UNIQUE (memory_id, case_id, entry_version)
);
CREATE TABLE IF NOT EXISTS pi_entry_keys (finding_id TEXT NOT NULL, relationship_key TEXT NOT NULL, exposed INTEGER, PRIMARY KEY (finding_id, relationship_key));
CREATE INDEX IF NOT EXISTS idx_pi_entry_keys ON pi_entry_keys (relationship_key);
CREATE TABLE IF NOT EXISTS pi_long_memories (
    memory_id TEXT NOT NULL, version INTEGER NOT NULL, relationship_key TEXT, status TEXT, written_at TEXT, written_ts INTEGER, record_json TEXT, PRIMARY KEY (memory_id, version)
);
CREATE INDEX IF NOT EXISTS idx_pi_long_key ON pi_long_memories (relationship_key, written_ts);
CREATE TABLE IF NOT EXISTS pi_weekly_runs (week TEXT PRIMARY KEY, written_at TEXT, written_ts INTEGER, record_json TEXT);
CREATE TABLE IF NOT EXISTS pi_llm (memory_id TEXT NOT NULL, version INTEGER NOT NULL, view_hash TEXT, llm_raw TEXT, usage_json TEXT, checks_json TEXT, PRIMARY KEY (memory_id, version));
CREATE TABLE IF NOT EXISTS pi_text (          -- the text layer's result for a long-term version; the version itself (`pi_long_memories`) is never touched
    memory_id TEXT NOT NULL, version INTEGER NOT NULL, cache_key TEXT NOT NULL, view_hash TEXT NOT NULL, text_source TEXT, status TEXT, text_json TEXT NOT NULL, prompt_version TEXT, checks_version TEXT,
    PRIMARY KEY (memory_id, version)
);
CREATE INDEX IF NOT EXISTS idx_pi_text_key ON pi_text (cache_key);
CREATE TABLE IF NOT EXISTS pi_progress (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS pi_meta (key TEXT PRIMARY KEY, value TEXT);
"""
TABLES = ("pi_mid_memories", "pi_mid_entries", "pi_entry_keys", "pi_long_memories", "pi_weekly_runs", "pi_progress", "pi_meta")        # dropped by --rebuild; the text layer's tables survive it
TEXT_TABLES = ("pi_llm", "pi_text")


def ts(iso: str | datetime) -> int:
    return int((datetime.fromisoformat(iso) if isinstance(iso, str) else iso).timestamp())


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


class PiStore:
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

    def close(self) -> None:
        self.conn.close()

    # ---- mid-term memories ---------------------------------------------------------------------------------------------------------------------------
    def has_mid(self, memory_id: str, status: str, as_of_ts: int | None = None) -> bool:
        q, a = "SELECT 1 FROM pi_mid_memories WHERE memory_id = ? AND status = ?", [memory_id, status]
        if as_of_ts is not None:
            q, a = q + " AND written_ts <= ?", a + [as_of_ts]
        return self.conn.execute(q, a).fetchone() is not None

    def put_mid(self, memory_id: str, status: str, week, written_at: str, sealed_at: str | None = None, record: dict | None = None) -> None:
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO pi_mid_memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (memory_id, status, week.iso, week.start.isoformat(), week.end.isoformat(), written_at, ts(written_at),
                                                                                                       sealed_at, _j(record) if record is not None else None))

    def sealed_weeks(self, n: int, as_of_ts: int) -> list[dict]:
        rows = self.conn.execute("SELECT record_json FROM pi_mid_memories WHERE status = 'sealed' AND written_ts <= ? ORDER BY week_start DESC LIMIT ?", (as_of_ts, n)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def sealed_at(self, memory_id: str) -> str | None:
        r = self.conn.execute("SELECT sealed_at FROM pi_mid_memories WHERE memory_id = ? AND status = 'sealed'", (memory_id,)).fetchone()
        return r[0] if r else None

    # ---- entries -------------------------------------------------------------------------------------------------------------------------------------
    def entry_by_finding(self, finding_id: str) -> dict | None:
        r = self.conn.execute("SELECT entry_json FROM pi_mid_entries WHERE finding_id = ?", (finding_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def entry_exists(self, memory_id: str, case_id: str, version: int) -> bool:
        return self.conn.execute("SELECT 1 FROM pi_mid_entries WHERE memory_id = ? AND case_id = ? AND entry_version = ?", (memory_id, case_id, version)).fetchone() is not None

    def put_entry(self, memory_id: str, entry: dict, written_at: str) -> None:
        with self.conn:
            self.conn.execute("INSERT INTO pi_mid_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (entry["finding_id"], memory_id, entry["case_id"], entry["entry_version"], entry["local_date"], written_at,
                                                                                               ts(written_at), _j(entry)))
            for r in entry["relationships"]:
                self.conn.execute("INSERT OR IGNORE INTO pi_entry_keys VALUES (?, ?, ?)", (entry["finding_id"], r["relationship_key"], int(r["exposed"])))

    def latest_entries(self, memory_id: str, as_of_ts: int) -> list[dict]:
        """For each case of the week, its latest entry written at or before `as_of_ts`, ordered by when it was written."""
        rows = self.conn.execute("SELECT entry_json FROM pi_mid_entries e WHERE memory_id = ? AND written_ts <= ? AND entry_version = "
                                 "(SELECT MAX(entry_version) FROM pi_mid_entries WHERE memory_id = e.memory_id AND case_id = e.case_id AND written_ts <= ?) "
                                 "ORDER BY written_ts, case_id", (memory_id, as_of_ts, as_of_ts)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def case_entry(self, case_id: str, as_of_ts: int) -> dict | None:
        r = self.conn.execute("SELECT entry_json FROM pi_mid_entries WHERE case_id = ? AND written_ts <= ? ORDER BY written_ts DESC, entry_version DESC LIMIT 1", (case_id, as_of_ts)).fetchone()
        return json.loads(r[0]) if r else None

    def latest_seen_date(self, key: str, as_of_ts: int, exclude_case: str | None) -> str | None:
        q = ("SELECT MAX(e.local_date) FROM pi_entry_keys k JOIN pi_mid_entries e ON e.finding_id = k.finding_id WHERE k.relationship_key = ? AND e.written_ts <= ?"
             + (" AND e.case_id != ?" if exclude_case else ""))
        return self.conn.execute(q, (key, as_of_ts, exclude_case) if exclude_case else (key, as_of_ts)).fetchone()[0]

    # ---- long-term memories ---------------------------------------------------------------------------------------------------------------------------
    def put_long(self, rec: dict) -> None:
        with self.conn:
            self.conn.execute("INSERT INTO pi_long_memories VALUES (?, ?, ?, ?, ?, ?, ?)", (rec["memory_id"], rec["version"], rec["relationship_key"], rec["status"], rec["written_at"], ts(rec["written_at"]), _j(rec)))

    def latest_long(self, key: str, as_of_ts: int) -> dict | None:
        r = self.conn.execute("SELECT record_json FROM pi_long_memories WHERE relationship_key = ? AND written_ts <= ? ORDER BY version DESC LIMIT 1", (key, as_of_ts)).fetchone()
        return json.loads(r[0]) if r else None

    def long_version(self, memory_id: str, version: int) -> dict | None:
        """One stored version of a long-term memory by id (a version a Findings record names in its refs)."""
        r = self.conn.execute("SELECT record_json FROM pi_long_memories WHERE memory_id = ? AND version = ?", (memory_id, version)).fetchone()
        return json.loads(r[0]) if r else None

    def latest_long_all(self, as_of_ts: int) -> list[dict]:
        rows = self.conn.execute("SELECT record_json FROM pi_long_memories m WHERE written_ts <= ? AND version = (SELECT MAX(version) FROM pi_long_memories WHERE memory_id = m.memory_id AND written_ts <= ?) "
                                 "ORDER BY relationship_key", (as_of_ts, as_of_ts)).fetchall()
        return [json.loads(r[0]) for r in rows]

    # ---- runs, progress ---------------------------------------------------------------------------------------------------------------------------------
    def get_run(self, week: str) -> dict | None:
        r = self.conn.execute("SELECT record_json FROM pi_weekly_runs WHERE week = ?", (week,)).fetchone()
        return json.loads(r[0]) if r else None

    def put_run(self, rec: dict) -> None:
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO pi_weekly_runs VALUES (?, ?, ?, ?)", (rec["week"], rec["written_at"], ts(rec["written_at"]), _j(rec)))

    def runs(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.conn.execute("SELECT record_json FROM pi_weekly_runs ORDER BY week")]

    def set_progress(self, key: str, value) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO pi_progress VALUES (?, ?)", (key, str(value)))

    def clear_progress(self, key: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM pi_progress WHERE key = ?", (key,))

    def get_progress(self, key: str) -> str | None:
        r = self.conn.execute("SELECT value FROM pi_progress WHERE key = ?", (key,)).fetchone()
        return r[0] if r else None

    # ---- the text layer (stage P2) ---------------------------------------------------------------------------------------------------------------------
    def put_text(self, memory_id: str, version: int, cache_key: str, view_hash: str, result: dict) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO pi_text VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (memory_id, version, cache_key, view_hash, result["text_source"], result["status"], _j(result["text"]),
                                                                                                     result.get("prompt_version"), result.get("checks_version")))
            self.conn.execute("INSERT OR REPLACE INTO pi_llm VALUES (?, ?, ?, ?, ?, ?)", (memory_id, version, view_hash, _j(result["llm_raw"]), _j(result["usage"]), _j(result["checks"])))

    def text_rows(self) -> dict:
        """Every stored text result keyed by cache key: {cache_key: [((memory_id, version), row), ...]}, read once in the main thread so worker threads need no connection."""
        out: dict = {}
        for m, v, k, tj, st, pv, cv, lr, uj, cj in self.conn.execute("SELECT t.memory_id, t.version, t.cache_key, t.text_json, t.status, t.prompt_version, t.checks_version, l.llm_raw, l.usage_json, l.checks_json "
                                                                     "FROM pi_text t LEFT JOIN pi_llm l USING (memory_id, version) ORDER BY t.memory_id, t.version"):
            out.setdefault(k, []).append(((m, v), {"text": json.loads(tj), "status": st, "prompt_version": pv, "checks_version": cv, "llm_raw": json.loads(lr or "[]"), "usage": json.loads(uj or "[]"),
                                                   "checks": json.loads(cj or "[]")}))
        return out

    def drop_text_rows(self, keep_prompt_version: str) -> int:
        """Explicit clean-up: delete stored text results made under another prompt version (they have another shape). Returns the number of rows deleted."""
        with self.conn:
            n = self.conn.execute("DELETE FROM pi_text WHERE prompt_version IS NOT ?", (keep_prompt_version,)).rowcount
            self.conn.execute("DELETE FROM pi_llm WHERE (memory_id, version) NOT IN (SELECT memory_id, version FROM pi_text)")
        return n

    def texts(self) -> dict:
        return {(m, v): {"cache_key": k, "view_hash": h, "text_source": src, "status": st, "text": json.loads(tj), "prompt_version": pv, "checks_version": cv}
                for m, v, k, h, src, st, tj, pv, cv in self.conn.execute("SELECT * FROM pi_text ORDER BY memory_id, version")}

    def dump(self) -> dict:
        return {t: [list(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")] for t in TABLES}
