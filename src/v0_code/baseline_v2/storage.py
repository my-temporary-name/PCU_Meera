"""memory_v2: the engine's own table (spec section 8). The v1 tables (raw_events, numeric_summary, context_events, memory_records) are never
touched. Writing is an upsert keyed by window_id, so a run is resumable and idempotent; the default NEVER drops anything — dropping memory_v2
needs an explicit rebuild=True (the CLI's --rebuild).

Retrieval returns parsed objects, not raw rows. `facts` (the big blob) is left out unless full=True; the gist text lives in its own columns so
it can be embedded later (no embeddings are built here).
"""

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id TEXT UNIQUE,
    tier TEXT, start_date TEXT, end_date TEXT,
    reliable INTEGER, confidence TEXT,          -- computed in code from reliability and completeness
    facts_json TEXT,                            -- all code-computed facts
    tags_json TEXT,                             -- direction tags with size labels (+ co-movement)
    material_changes_json TEXT,
    anchors_crossed TEXT, anchors_questionable TEXT,
    is_notable INTEGER, notable_reason TEXT,    -- code only
    deviation_text TEXT,                        -- code-rendered, human-readable
    data_quality_json TEXT,
    gist_headline TEXT, gist_sentences TEXT,    -- LLM or code line
    gist_status TEXT,                           -- gist_ok | gist_retry_ok | code_line_early | code_line_quiet | code_line_week_skipped | code_line_fallback (NULL = gist not run yet)
    llm_raw TEXT, usage_json TEXT,
    config_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_memory_v2_tier_end ON memory_v2 (tier, end_date);
"""
LLM_STATUSES = ("gist_ok", "gist_retry_ok")
FACT_COLUMNS = ("tier", "start_date", "end_date", "reliable", "confidence", "facts_json", "tags_json", "material_changes_json", "anchors_crossed",
                "anchors_questionable", "is_notable", "notable_reason", "deviation_text", "data_quality_json", "config_version")
GIST_COLUMNS = ("gist_headline", "gist_sentences", "gist_status", "llm_raw", "usage_json")


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False)


class MemoryV2Store:
    def __init__(self, db_path: str | Path, rebuild: bool = False, readonly: bool = False):
        self.path = Path(db_path)
        if readonly:
            self.conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        else:
            self.conn = sqlite3.connect(self.path, check_same_thread=False)      # the gist runner saves from worker threads, one at a time (it holds a lock)
            if rebuild:
                self.conn.execute("DROP TABLE IF EXISTS memory_v2")   # the ONLY destructive statement in this module, and only on request
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    # ---- write -------------------------------------------------------------------------------------------------------------
    def upsert(self, rows: list[dict]) -> None:
        """Insert or update by window_id. A window whose gist was written by the LLM keeps it; code lines are recomputed with the facts."""
        existing = {r["window_id"]: r["gist_status"] for r in self.conn.execute("SELECT window_id, gist_status FROM memory_v2")}
        with self.conn:
            for r in rows:
                values = {
                    "window_id": r["window_id"], "tier": r["tier"], "start_date": r["start_date"], "end_date": r["end_date"], "reliable": int(r["reliable"]),
                    "confidence": r["confidence"], "facts_json": _j(r["facts"]), "tags_json": _j({"tags": r["tags"], "co_movement": r["co_movement"]}),
                    "material_changes_json": _j(r["material_changes"]), "anchors_crossed": _j(r["anchors_crossed"]), "anchors_questionable": _j(r["anchors_questionable"]),
                    "is_notable": int(r["is_notable"]), "notable_reason": r["notable_reason"], "deviation_text": r["deviation_text"],
                    "data_quality_json": _j(r["data_quality"]), "config_version": r["config_version"],
                    "gist_headline": r.get("gist_headline"), "gist_sentences": _j(r["gist_sentences"]) if r.get("gist_sentences") is not None else None,
                    "gist_status": r.get("gist_status"), "llm_raw": None, "usage_json": None,
                }
                cols = list(FACT_COLUMNS) + ([] if existing.get(r["window_id"]) in LLM_STATUSES else list(GIST_COLUMNS))
                self.conn.execute(
                    f"INSERT INTO memory_v2 (window_id, {', '.join(values_cols(values))}) VALUES ({', '.join('?' * (1 + len(values_cols(values))))}) "
                    f"ON CONFLICT(window_id) DO UPDATE SET {', '.join(f'{c} = excluded.{c}' for c in cols)}",
                    [values["window_id"], *[values[c] for c in values_cols(values)]])

    def save_gist(self, window_id: str, headline: str, sentences: list[str], status: str, llm_raw: str | None = None, usage: list | dict | None = None) -> None:
        """Write one window's gist (LLM text or a code line) and its audit trail. Touches only the gist columns."""
        with self.conn:
            cur = self.conn.execute("UPDATE memory_v2 SET gist_headline = ?, gist_sentences = ?, gist_status = ?, llm_raw = ?, usage_json = ? WHERE window_id = ?",
                                    (headline, _j(sentences), status, llm_raw, _j(usage) if usage is not None else None, window_id))
        if cur.rowcount != 1:
            raise KeyError(window_id)

    def reset_gists(self, window_ids: list[str] | None = None) -> int:
        """Return windows whose gist came from the model (gist_ok, gist_retry_ok, code_line_fallback) to pending: all of them, or only `window_ids`.
        Touches only the gist columns of those windows; early and quiet code lines and every fact are untouched. Used explicitly, to regenerate."""
        sql = ("UPDATE memory_v2 SET gist_headline = NULL, gist_sentences = NULL, gist_status = NULL, llm_raw = NULL, usage_json = NULL "
               "WHERE gist_status IN ('gist_ok', 'gist_retry_ok', 'code_line_fallback')")
        with self.conn:
            if window_ids is None:
                return self.conn.execute(sql).rowcount
            return sum(self.conn.execute(sql + " AND window_id = ?", (w,)).rowcount for w in window_ids)

    # ---- read: parsed objects -------------------------------------------------------------------------------------------------
    @staticmethod
    def _parse(row: sqlite3.Row, full: bool) -> dict:
        tags = json.loads(row["tags_json"])
        out = {
            "window_id": row["window_id"], "tier": row["tier"], "start_date": row["start_date"], "end_date": row["end_date"], "reliable": bool(row["reliable"]),
            "confidence": row["confidence"], "tags": tags["tags"], "co_movement": tags["co_movement"], "material_changes": json.loads(row["material_changes_json"]),
            "anchors_crossed": json.loads(row["anchors_crossed"]), "anchors_questionable": json.loads(row["anchors_questionable"]), "is_notable": bool(row["is_notable"]),
            "notable_reason": row["notable_reason"], "deviation_text": row["deviation_text"], "data_quality": json.loads(row["data_quality_json"]),
            "gist": {"headline": row["gist_headline"], "sentences": json.loads(row["gist_sentences"]) if row["gist_sentences"] else [], "status": row["gist_status"]},
            "config_version": row["config_version"],
        }
        out["quiet"] = not out["material_changes"]
        if full:
            out["facts"] = json.loads(row["facts_json"])
            out["deltas_clean"] = out["facts"]["deltas"]["clean"]          # what the code lines need to word an anchor crossing
        return out

    def get_memory(self, tier: str, date: str, full: bool = False) -> dict | None:
        row = self.conn.execute("SELECT * FROM memory_v2 WHERE tier = ? AND end_date = ?", (tier, date)).fetchone()
        return self._parse(row, full) if row else None

    def get_memories_between(self, start_date: str, end_date: str, tier: str, full: bool = False) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM memory_v2 WHERE tier = ? AND end_date >= ? AND end_date <= ? ORDER BY end_date", (tier, start_date, end_date)).fetchall()
        return [self._parse(r, full) for r in rows]

    def get_notable(self, tier: str, since_date: str, full: bool = False) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM memory_v2 WHERE tier = ? AND is_notable = 1 AND end_date >= ? ORDER BY end_date", (tier, since_date)).fetchall()
        return [self._parse(r, full) for r in rows]

    def get_profile_asof(self, stream: str, date: str) -> dict | None:
        """The stream's normal profile as it stood at the START of `date` (history strictly before it)."""
        row = self.conn.execute("SELECT facts_json FROM memory_v2 WHERE tier = 'day' AND end_date = ?", (date,)).fetchone()
        return json.loads(row["facts_json"])["profile_asof"].get(stream) if row else None


def values_cols(values: dict) -> list[str]:
    return [c for c in values if c != "window_id"]
