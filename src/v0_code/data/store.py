"""Personal Data Store: pure write-in/read-out SQLite layer — no computation.

Holds everything that reached this point in the chain: every Threshold Evaluator
output row (every status, including 'normal') and every Short-Range Linker pairing.
Rejected readings and untouched source files never reach here.

`event_id` is reused across the year in the source data (see CLAUDE.md), so it
cannot be a primary key, and a pairing lookup needs `timestamp` alongside
`glucose_event_id` to be unambiguous. `raw_events` therefore uses a surrogate
`id`, and `insert_pairing`/`get_pairings` take the extra fields needed to make
each pairing row self-contained and each glucose reading unambiguous.
"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    timestamp TEXT,
    biomarker TEXT,
    value REAL,
    status TEXT,
    source_type TEXT,      -- 'reading' or 'pairing'
    paired_to TEXT,        -- nullable: the candidate's id, only for pairings
    candidate_type TEXT,   -- nullable: e.g. 'meal', 'medication', 'sleep'
    lag_minutes REAL       -- nullable: only for pairings
);
CREATE INDEX IF NOT EXISTS idx_raw_events_biomarker_ts ON raw_events (biomarker, timestamp);
CREATE INDEX IF NOT EXISTS idx_raw_events_pairing_lookup ON raw_events (source_type, event_id, timestamp);

CREATE TABLE IF NOT EXISTS numeric_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    biomarker TEXT,
    window_type TEXT,          -- 'day' or 'week'
    window_start TEXT,
    window_end TEXT,
    n_readings INTEGER,
    completeness_pct REAL,
    reliable INTEGER,          -- 0/1
    mean REAL,
    gmi_pct REAL,
    tir_pct REAL,
    tar_pct REAL,
    tar_severe_pct REAL,
    tbr_pct REAL,
    tbr_severe_pct REAL,
    cv_pct REAL,
    delta_mean REAL,
    delta_tir_pct REAL,
    delta_cv_pct REAL,
    delta_gmi_pct REAL,
    is_notable INTEGER,        -- nullable 0/1: null if the LLM step didn't run/failed for this window
    interpretive_note TEXT,    -- nullable
    UNIQUE (biomarker, window_type, window_start)
);
CREATE INDEX IF NOT EXISTS idx_numeric_summary_lookup ON numeric_summary (biomarker, window_type, window_start);

CREATE TABLE IF NOT EXISTS context_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT, timestamp TEXT, date TEXT,
    value_text TEXT, value_num REAL, category TEXT, meta_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_context_events_stream_date ON context_events (stream, date);

CREATE TABLE IF NOT EXISTS memory_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id TEXT UNIQUE,
    tier TEXT,                 -- day | week | month
    start_date TEXT, end_date TEXT,
    reliable INTEGER,
    record_json TEXT,          -- code-computed, always written first
    prior_window_id TEXT,
    data_quality_flags TEXT,
    memory_json TEXT,          -- validated LLM output, nullable
    is_notable INTEGER,        -- nullable
    llm_status TEXT,           -- ok | rejected | failed | skipped
    llm_raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_memory_records_tier_date ON memory_records (tier, start_date, end_date);
"""


class PersonalDataStore:
    """Insert and select only — no aggregation, no filtering logic beyond plain WHERE clauses."""

    def __init__(self, db_path: str | Path, reset: bool = False):
        """reset=True rebuilds the table from scratch (what the pipeline node does on each
        run, same as the CSV outputs); reset=False (default) opens the existing store as-is,
        for any later reader — a plain open must never silently wipe prior data."""
        self.path = Path(db_path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        if reset:
            for table in ("raw_events", "numeric_summary", "context_events", "memory_records"):
                self.conn.execute(f"DROP TABLE IF EXISTS {table}")
        self.conn.executescript(SCHEMA)  # IF NOT EXISTS everywhere: a plain open never wipes, and adds any missing newer table
        self.conn.commit()

    def _table_exists(self, name: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "PersonalDataStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- writes -------------------------------------------------------------------------

    def insert_reading(self, event_id: str, timestamp: str, biomarker: str, value: float, status: str) -> None:
        self.insert_readings([(event_id, timestamp, biomarker, value, status)])

    def insert_readings(self, rows: list[tuple[str, str, str, float, str]]) -> None:
        """rows: (event_id, timestamp, biomarker, value, status) — one per Threshold Evaluator row."""
        with self.conn:
            self.conn.executemany(
                "INSERT INTO raw_events (event_id, timestamp, biomarker, value, status, source_type) "
                "VALUES (?, ?, ?, ?, ?, 'reading')",
                rows,
            )

    def insert_pairing(
        self,
        glucose_event_id: str,
        candidate_type: str,
        candidate_event_id: str | None,
        lag_minutes: float | None,
        *,
        timestamp: str,
        biomarker: str,
        value: float,
        status: str,
    ) -> None:
        """timestamp/biomarker/value/status make the row self-contained and disambiguate
        glucose_event_id, which (like candidate ids such as adherence_id) repeats across months."""
        self.insert_pairings([(glucose_event_id, timestamp, biomarker, value, status, candidate_event_id, candidate_type, lag_minutes)])

    def insert_pairings(self, rows: list[tuple[str, str, str, float, str, str | None, str, float | None]]) -> None:
        """rows: (glucose_event_id, timestamp, biomarker, value, status, paired_to, candidate_type, lag_minutes)."""
        with self.conn:
            self.conn.executemany(
                "INSERT INTO raw_events "
                "(event_id, timestamp, biomarker, value, status, source_type, paired_to, candidate_type, lag_minutes) "
                "VALUES (?, ?, ?, ?, ?, 'pairing', ?, ?, ?)",
                rows,
            )

    # ---- reads --------------------------------------------------------------------------

    def get_events(self, biomarker: str, start_date: str, end_date: str) -> list[sqlite3.Row]:
        """Reading rows (not pairings) for one biomarker, timestamp between start_date and
        end_date inclusive (end_date treated as covering the whole day)."""
        return self.conn.execute(
            "SELECT * FROM raw_events WHERE source_type = 'reading' AND biomarker = ? "
            "AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
            (biomarker, start_date, end_date + "T23:59:59"),
        ).fetchall()

    def get_pairings(self, glucose_event_id: str, timestamp: str) -> list[sqlite3.Row]:
        """All pairings for one specific glucose reading, identified by (event_id, timestamp) —
        event_id alone is not unique across the year."""
        return self.conn.execute(
            "SELECT * FROM raw_events WHERE source_type = 'pairing' AND event_id = ? AND timestamp = ?",
            (glucose_event_id, timestamp),
        ).fetchall()

    # ---- numeric_summary (Baseline Engine) -----------------------------------------------

    def insert_numeric_summaries(self, rows: list[tuple]) -> None:
        """rows match numeric_summary's column order (see SCHEMA), minus the surrogate id."""
        with self.conn:
            self.conn.executemany(
                "INSERT INTO numeric_summary "
                "(biomarker, window_type, window_start, window_end, n_readings, completeness_pct, "
                "reliable, mean, gmi_pct, tir_pct, tar_pct, tar_severe_pct, tbr_pct, tbr_severe_pct, "
                "cv_pct, delta_mean, delta_tir_pct, delta_cv_pct, delta_gmi_pct, is_notable, interpretive_note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )

    def get_numeric_summary(self, biomarker: str, window_type: str, start_date: str, end_date: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM numeric_summary WHERE biomarker = ? AND window_type = ? "
            "AND window_start >= ? AND window_end <= ? ORDER BY window_start",
            (biomarker, window_type, start_date, end_date),
        ).fetchall()

    # ---- context_events (verbatim ingest of non-Threshold-Evaluated streams) -------------

    def insert_context_events(self, rows: list[tuple]) -> None:
        """rows: (stream, timestamp, date, value_text, value_num, category, meta_json)."""
        with self.conn:
            self.conn.executemany(
                "INSERT INTO context_events (stream, timestamp, date, value_text, value_num, category, meta_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                rows,
            )

    def get_context_events(self, stream: str, start_date: str, end_date: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM context_events WHERE stream = ? AND date >= ? AND date <= ? ORDER BY date, timestamp",
            (stream, start_date, end_date),
        ).fetchall()

    # ---- memory_records (Baseline Engine memory) ------------------------------------------

    def insert_memory_record(
        self,
        window_id: str,
        tier: str,
        start_date: str,
        end_date: str,
        reliable: bool,
        record_json: str,
        prior_window_id: str | None,
        data_quality_flags: str,
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO memory_records "
                "(window_id, tier, start_date, end_date, reliable, record_json, prior_window_id, "
                "data_quality_flags, llm_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'skipped')",
                (window_id, tier, start_date, end_date, int(reliable), record_json, prior_window_id, data_quality_flags),
            )

    def update_memory_llm_result(
        self, window_id: str, memory_json: str | None, is_notable: bool | None, llm_status: str, llm_raw: str | None
    ) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE memory_records SET memory_json = ?, is_notable = ?, llm_status = ?, llm_raw = ? WHERE window_id = ?",
                (memory_json, None if is_notable is None else int(is_notable), llm_status, llm_raw, window_id),
            )

    def get_memory(self, tier: str, date: str) -> sqlite3.Row | None:
        """Record + memory for the window of this tier ending on `date`."""
        return self.conn.execute(
            "SELECT * FROM memory_records WHERE tier = ? AND end_date = ? ORDER BY start_date DESC LIMIT 1",
            (tier, date),
        ).fetchone()

    def get_memories_overlapping(self, start_date: str, end_date: str, tier: str | None = None) -> list[sqlite3.Row]:
        if tier:
            return self.conn.execute(
                "SELECT * FROM memory_records WHERE tier = ? AND end_date >= ? AND start_date <= ? ORDER BY start_date",
                (tier, start_date, end_date),
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM memory_records WHERE end_date >= ? AND start_date <= ? ORDER BY tier, start_date",
            (start_date, end_date),
        ).fetchall()

    def get_notable_memories(self, tier: str, since_date: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM memory_records WHERE tier = ? AND is_notable = 1 AND start_date >= ? ORDER BY start_date",
            (tier, since_date),
        ).fetchall()
