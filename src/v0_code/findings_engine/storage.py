"""The Findings Engine's own database (findings_engine_spec.md 9.2). Versions are append-only: a stored version is never changed, and writing a different record under an
existing finding_id is an error, not an update. No table holds a wall-clock time. Dropping the tables needs the explicit `rebuild`."""

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY, local_date TEXT, opened_at TEXT, last_handoff_at TEXT, closed_at TEXT, status TEXT,
    n_counted INTEGER, n_recorded INTEGER, n_versions INTEGER
);
CREATE TABLE IF NOT EXISTS case_handoffs (
    case_id TEXT NOT NULL, handoff_id TEXT NOT NULL, joined_at TEXT, counted INTEGER, packet_status TEXT,
    PRIMARY KEY (case_id, handoff_id)
);
CREATE TABLE IF NOT EXISTS unattached_handoffs (handoff_id TEXT PRIMARY KEY, opened_at TEXT, packet_status TEXT);
CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, version INTEGER NOT NULL, as_of TEXT, mode TEXT, provisional INTEGER, closed INTEGER, text_source TEXT, status TEXT,
    record_json TEXT NOT NULL, UNIQUE (case_id, version)
);
CREATE TABLE IF NOT EXISTS finding_llm (finding_id TEXT PRIMARY KEY, view_hash TEXT, llm_raw TEXT, usage_json TEXT, checks_json TEXT);    -- one JSON list per attempt
CREATE TABLE IF NOT EXISTS finding_text (                      -- the text layer's result for a version; the version itself (`findings`) is never touched
    finding_id TEXT PRIMARY KEY, cache_key TEXT NOT NULL, view_hash TEXT NOT NULL, text_source TEXT, status TEXT, text_json TEXT NOT NULL,
    prompt_version TEXT, checks_version TEXT, from_prompt TEXT, settings_key TEXT
);
CREATE INDEX IF NOT EXISTS idx_finding_text_key ON finding_text (cache_key);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""
TABLES = ("cases", "case_handoffs", "unattached_handoffs", "findings", "meta")                     # dropped by --rebuild; the text layer's cache survives it
TEXT_TABLES = ("finding_llm", "finding_text")


class ImmutableVersionError(RuntimeError):
    pass


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


class FindingsStore:
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
            have = {r[1] for r in self.conn.execute("PRAGMA table_info(finding_text)")}
            for col in ("prompt_version", "checks_version", "from_prompt", "settings_key"):          # a database written before the prompt versions existed
                if col not in have:
                    self.conn.execute(f"ALTER TABLE finding_text ADD COLUMN {col} TEXT")
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def put_finding(self, rec: dict) -> str:
        """written | same. A different record under an existing id raises: stored versions are never changed."""
        new = _j(rec)
        with self.conn:
            old = self.conn.execute("SELECT record_json FROM findings WHERE finding_id = ?", (rec["finding_id"],)).fetchone()
            if old is not None:
                if old[0] != new:
                    raise ImmutableVersionError(f"{rec['finding_id']} is already stored with a different record; versions are never changed (use an explicit rebuild to start again)")
                return "same"
            self.conn.execute("INSERT INTO findings (finding_id, case_id, version, as_of, mode, provisional, closed, text_source, status, record_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                              (rec["finding_id"], rec["case_id"], rec["version"], rec["as_of"], rec["mode"], int(rec["provisional"]), int(rec["closed"]), rec["text"]["source"], rec["status"], new))
            return "written"

    def write_replay(self, result, meta: dict) -> dict:
        counts = {"written": 0, "same": 0}
        for v in result.versions:
            counts[self.put_finding(v)] += 1
        with self.conn:
            for c in result.cases:
                self.conn.execute("INSERT OR REPLACE INTO cases VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (c["case_id"], c["local_date"], c["opened_at"], c["last_handoff_at"], c["closed_at"],
                                                                                                         c["status"], c["n_counted"], c["n_recorded"], c["n_versions"]))
            for h in result.case_handoffs:
                self.conn.execute("INSERT OR REPLACE INTO case_handoffs VALUES (?, ?, ?, ?, ?)", (h["case_id"], h["handoff_id"], h["joined_at"], int(h["counted"]), h["packet_status"]))
            for u in result.unattached:
                self.conn.execute("INSERT OR REPLACE INTO unattached_handoffs VALUES (?, ?, ?)", (u["handoff_id"], u["opened_at"], u["packet_status"]))
            for k, v in meta.items():
                self.conn.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (k, str(v)))
        return counts

    # ---- reads ----------------------------------------------------------------------------------------------------------------------------------------
    def findings(self, case_id: str | None = None) -> list[dict]:
        q, args = "SELECT record_json FROM findings" + (" WHERE case_id = ?" if case_id else "") + " ORDER BY case_id, version", ((case_id,) if case_id else ())
        return [json.loads(r[0]) for r in self.conn.execute(q, args)]

    def get_finding(self, finding_id: str) -> dict | None:
        r = self.conn.execute("SELECT record_json FROM findings WHERE finding_id = ?", (finding_id,)).fetchone()
        return json.loads(r[0]) if r else None

    def cases(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM cases ORDER BY opened_at")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur]

    def is_last_version(self, finding_id: str) -> bool:
        r = self.conn.execute("SELECT version, case_id FROM findings WHERE finding_id = ?", (finding_id,)).fetchone()
        return r is not None and r[0] == self.conn.execute("SELECT MAX(version) FROM findings WHERE case_id = ?", (r[1],)).fetchone()[0]

    def dump(self) -> dict:
        """Every table's rows, for the determinism check."""
        return {t: [list(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")] for t in TABLES}

    # ---- the text layer (stage F2) ---------------------------------------------------------------------------------------------------------------------
    def get_cached(self, cache_key: str, finding_id: str | None = None) -> dict | None:
        """The stored result for a view with this cache key: the version's own row if it has one, else any version that had the same view; None if there is none."""
        r = self.conn.execute("SELECT t.finding_id, t.view_hash, t.text_source, t.status, t.text_json, l.llm_raw, l.usage_json, l.checks_json, t.prompt_version, t.checks_version, t.from_prompt, t.settings_key FROM finding_text t LEFT JOIN finding_llm l USING (finding_id) "
                              "WHERE t.cache_key = ? ORDER BY (t.finding_id = ?) DESC, t.finding_id LIMIT 1", (cache_key, finding_id)).fetchone()
        if r is None:
            return None
        return {"finding_id": r[0], "view_hash": r[1], "text_source": r[2], "status": r[3], "text": json.loads(r[4]), "llm_raw": json.loads(r[5] or "[]"), "usage": json.loads(r[6] or "[]"),
                "checks": json.loads(r[7] or "[]"), "prompt_version": r[8], "checks_version": r[9], "from_prompt": r[10], "settings_key": r[11]}

    def own_row(self, finding_id: str) -> dict | None:
        """The stored result of a version, whatever view it was made against (with the view hash it was made against), or None."""
        r = self.conn.execute("SELECT t.finding_id, t.view_hash, t.text_source, t.status, t.text_json, l.llm_raw, l.usage_json, l.checks_json, t.prompt_version, t.checks_version, t.from_prompt "
                              "FROM finding_text t LEFT JOIN finding_llm l USING (finding_id) WHERE t.finding_id = ?", (finding_id,)).fetchone()
        if r is None:
            return None
        return {"finding_id": r[0], "view_hash": r[1], "text_source": r[2], "status": r[3], "text": json.loads(r[4]), "llm_raw": json.loads(r[5] or "[]"), "usage": json.loads(r[6] or "[]"),
                "checks": json.loads(r[7] or "[]"), "prompt_version": r[8], "checks_version": r[9], "from_prompt": r[10]}

    def has_text(self, finding_id: str) -> bool:
        return self.conn.execute("SELECT 1 FROM finding_text WHERE finding_id = ?", (finding_id,)).fetchone() is not None

    def put_text(self, finding_id: str, cache_key: str, view_hash: str, result: dict) -> None:
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO finding_text (finding_id, cache_key, view_hash, text_source, status, text_json, prompt_version, checks_version, from_prompt, settings_key) "
                              "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (finding_id, cache_key, view_hash, result["text_source"], result["status"], _j(result["text"]), result.get("prompt_version"),
                                                                        result.get("checks_version"), result.get("from_prompt"), result.get("settings_key")))
            self.conn.execute("INSERT OR REPLACE INTO finding_llm VALUES (?, ?, ?, ?, ?)", (finding_id, view_hash, _j(result["llm_raw"]), _j(result["usage"]), _j(result["checks"])))

    def find_texts(self, view_hash: str, settings_key: str, prompt_versions: list[str], finding_id: str | None = None) -> list[dict]:
        """Stored results for the same model settings made under one of the given prompt versions: this version's own row first (whatever view it was made against: the checks
        judge it against today's), then any other version's row for an identical view."""
        marks = ",".join("?" * len(prompt_versions))
        rows = self.conn.execute("SELECT t.finding_id, t.cache_key, t.prompt_version, t.checks_version, t.from_prompt, t.text_source, t.status, t.text_json, l.llm_raw, l.usage_json, l.checks_json "
                                 f"FROM finding_text t LEFT JOIN finding_llm l USING (finding_id) WHERE (t.view_hash = ? OR t.finding_id = ?) AND t.settings_key = ? AND t.prompt_version IN ({marks}) "
                                 "ORDER BY (t.finding_id = ?) DESC, t.finding_id", (view_hash, finding_id, settings_key, *prompt_versions, finding_id)).fetchall()
        return [{"finding_id": r[0], "cache_key": r[1], "prompt_version": r[2], "checks_version": r[3], "from_prompt": r[4], "text_source": r[5], "status": r[6], "text": json.loads(r[7]),
                 "llm_raw": json.loads(r[8] or "[]"), "usage": json.loads(r[9] or "[]"), "checks": json.loads(r[10] or "[]")} for r in rows]

    def adopt_legacy(self, settings_key: str, prompt_version: str, checks_version: str) -> int:
        """Rows written before prompt versions were recorded are given the version they were made under. Returns how many rows were changed."""
        with self.conn:
            return self.conn.execute("UPDATE finding_text SET prompt_version = ?, checks_version = ?, settings_key = ? WHERE prompt_version IS NULL",
                                     (prompt_version, checks_version, settings_key)).rowcount

    def texts_ids(self) -> set:
        return {r[0] for r in self.conn.execute("SELECT finding_id FROM finding_text")}

    def texts(self) -> dict:
        return {r[0]: {"cache_key": r[1], "view_hash": r[2], "text_source": r[3], "status": r[4], "text": json.loads(r[5])}
                for r in self.conn.execute("SELECT finding_id, cache_key, view_hash, text_source, status, text_json FROM finding_text ORDER BY finding_id")}
