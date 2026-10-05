"""As-of context for a case version (findings_engine_spec.md 4, 6 and Amendments 16, 19): which diary entries and which state-memory windows the text layer may be shown. Only
references are kept in the finding record (`refs.diary`, `refs.state_memory`); the text itself is read again when a view is built. Every read goes through this class, which
only returns rows at or before `as_of` and logs what it returned, so the as-of audit can check the log and the stored records independently."""

import json
import re
import sqlite3
from datetime import datetime, timedelta

from v0_code.findings_engine.config import FindingsConfig


class Context:
    def __init__(self, cfg: FindingsConfig, store_path: str | None = None):
        self.cfg = cfg
        self.tz = cfg.tz
        self.conn = sqlite3.connect(f"file:{store_path or cfg.paths['store_db']}?mode=ro", uri=True)
        self.reads: list[dict] = []
        self._diary = self._load_diary()

    def close(self) -> None:
        self.conn.close()

    # ---- diary ----------------------------------------------------------------------------------------------------------------------------------------
    def _load_diary(self) -> list[dict]:
        d = self.cfg.diary
        rows = self.conn.execute("SELECT timestamp, category, value_text, meta_json, id FROM context_events WHERE stream = ? ORDER BY timestamp, id", (d["stream"],)).fetchall()
        out = []
        for ts, cat, text, meta, row_id in rows:
            m = json.loads(meta) if meta else {}
            out.append({"context_id": m.get(d["id_field"]) or f"event_{row_id}", "timestamp": ts, "at": datetime.fromisoformat(ts), "category": cat, "description": text, "severity_or_note": m.get(d["note_field"]) or None})
        return out

    @property
    def all_diary(self) -> list[dict]:
        """Every diary row (aware `at`); used to find the entries that back a point, wherever they fall. The caller applies the as-of cut."""
        return self._diary

    def severity_rank(self, note: str | None) -> int:
        """0 = most severe keyword present in the note; entries with none sort after every ranked one."""
        order = self.cfg.diary_severity_order
        text = (note or "").lower()
        hits = [i for i, kw in enumerate(order) if re.search(rf"\b{re.escape(kw.lower())}\b", text)]
        return min(hits) if hits else len(order)

    def diary(self, as_of: datetime, local_date: str) -> list[dict]:
        """Entries from the start of the previous local day up to `as_of`; at most `max_entries`, moderate or worse first, then the most recent."""
        d = self.cfg.diary
        start = datetime.fromisoformat(local_date).replace(tzinfo=self.tz) - timedelta(days=1)
        cutoff = self.severity_rank(d["priority_up_to"])
        pool = [e for e in self._diary if start <= e["at"] <= as_of]
        pool.sort(key=lambda e: (self.severity_rank(e["severity_or_note"]) > cutoff, -e["at"].timestamp(), str(e["context_id"])))
        chosen = pool[: int(d["max_entries"])]
        for n, e in enumerate(chosen, 1):
            e["view_id"] = f"d{n}"
            self.reads.append({"as_of": as_of.isoformat(), "kind": "diary", "id": e["context_id"], "at": e["timestamp"]})
        return chosen

    # ---- state memory ---------------------------------------------------------------------------------------------------------------------------------
    def state_memory(self, as_of: datetime, local_date: str) -> list[dict]:
        sm = self.cfg.state_memory
        yesterday = (datetime.fromisoformat(local_date) - timedelta(days=1)).date().isoformat()
        out = []
        for name in sm["use"]:
            spec = sm["windows"][name]
            if isinstance(spec, str):
                row = self.conn.execute("SELECT window_id, end_date, gist_status, gist_headline, is_notable FROM memory_v2 WHERE window_id = ? AND end_date < ?", (spec.format(date=yesterday), local_date)).fetchone()
            else:
                row = self.conn.execute("SELECT window_id, end_date, gist_status, gist_headline, is_notable FROM memory_v2 WHERE tier = ? AND end_date < ? ORDER BY end_date DESC LIMIT 1",
                                        (spec["tier"], local_date)).fetchone()
            if row is None or not row[3] or row[2] is None or row[2] in sm["skip_statuses"]:
                continue
            e = {"window_id": row[0], "end_date": row[1], "gist_status": row[2], "gist_headline": row[3], "is_notable": row[4], "view_id": f"s{len(out) + 1}", "use": name}
            out.append(e)
            self.reads.append({"as_of": as_of.isoformat(), "kind": "state_memory", "id": row[0], "at": row[1]})
        return out

    # ---- what a version stores ------------------------------------------------------------------------------------------------------------------------
    def refs(self, as_of: datetime, local_date: str) -> dict:
        return {"diary": [{"view_id": e["view_id"], "context_id": e["context_id"]} for e in self.diary(as_of, local_date)],
                "state_memory": [{"view_id": e["view_id"], "window_id": e["window_id"]} for e in self.state_memory(as_of, local_date)], "pi_memories": []}
