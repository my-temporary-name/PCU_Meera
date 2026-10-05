"""Read-only access to the Baseline Engine's profile (spec 4.2a, 4.2c). Never writes, never reads a baseline window as an event.

`baseline_asof` for a tick on date D is D - 1: the profile as it stood at the START of D (history strictly before D), which is exactly
`MemoryV2Store.get_profile_asof(stream, D)`. If the baseline has no day row for D yet, the newest earlier one is used and the tick is marked `baseline_late`.
"""

import json
import sqlite3
from datetime import date as _date, timedelta


class BaselineView:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._rows: dict[str, tuple[str, dict] | None] = {}
        self._dates = [r[0] for r in conn.execute("SELECT end_date FROM memory_v2 WHERE tier = 'day' ORDER BY end_date")]
        self._cache: dict = {}

    def day_for(self, d: _date) -> tuple[str | None, bool]:
        """(the baseline day whose as-of profile applies to date d, late?)"""
        s = d.isoformat()
        if s in self._dates:
            return s, False
        earlier = [x for x in self._dates if x < s]
        return (earlier[-1], True) if earlier else (None, True)

    def _facts(self, day: str) -> dict:
        if day not in self._cache:
            row = self.conn.execute("SELECT facts_json, config_version FROM memory_v2 WHERE tier = 'day' AND end_date = ?", (day,)).fetchone()
            self._cache[day] = {"facts": json.loads(row[0]), "config_version": row[1]} if row else None
        return self._cache[day]

    def profile(self, stream: str, d: _date) -> tuple[dict | None, bool]:
        """(profile of `stream` as of the start of d, baseline_late)"""
        day, late = self.day_for(d)
        if day is None:
            return None, True
        f = self._facts(day)
        return f["facts"]["profile_asof"].get(stream), late

    def config_version(self, d: _date) -> str | None:
        day, _ = self.day_for(d)
        return self._facts(day)["config_version"] if day else None

    def yesterday_headline(self, d: _date) -> str | None:
        """Context only (4.2c): the headline of yesterday's day memory (a gist or a code line), if it exists."""
        row = self.conn.execute("SELECT gist_headline FROM memory_v2 WHERE tier = 'day' AND end_date = ?", ((d - timedelta(days=1)).isoformat(),)).fetchone()
        return row[0] if row else None
