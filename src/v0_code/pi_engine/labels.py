"""Week labels (pi_spec.md 6.3 as amended): from a relationship's daily labels in the Evidence store, by id and by date. The numbers in those records are never read: only
`support` and `flags`. A day with no record counts as `insufficient`; a partial week counts only the days that exist and scales the threshold (rounded up); a week with fewer
than `min_days` days is `insufficient`."""

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from v0_code.pi_engine.weeks import Week

DECISIVE = ("supported", "not_supported")


@dataclass(frozen=True)
class LabelCfg:
    days_needed: int
    of: int
    min_days: int
    scale: bool


@dataclass(frozen=True)
class WeekCounts:
    week: str
    days_in_week: int
    supported: int
    suggestive: int
    not_supported: int
    insufficient: int
    placebo_days: int
    contrary_days: int
    days_with_record: int


def needed_days(days: int, base: int, of: int, cfg: LabelCfg) -> int:
    """5 of 7 days; for a partial week the same share of the days that exist, rounded up (5 days: 4, 4 days: 3)."""
    return math.ceil(base * days / of) if cfg.scale else base


def week_label(c: WeekCounts, cfg: LabelCfg) -> str:
    if c.days_in_week < cfg.min_days:
        return "insufficient"
    need = needed_days(c.days_in_week, cfg.days_needed, cfg.of, cfg)
    if c.supported >= need:
        return "supported"
    if c.supported + c.suggestive >= need:
        return "suggestive"
    if c.insufficient >= need:
        return "insufficient"
    return "not_supported"


class EvidenceLabels:
    """Read-only view of the Evidence store's relationship records (`current` ones)."""

    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self._span = None
        self._daily: dict = {}

    def close(self) -> None:
        self.conn.close()

    def span(self) -> tuple[date, date]:
        """The data span: the first to the last day with an evidence record."""
        if self._span is None:
            lo, hi = self.conn.execute("SELECT MIN(as_of_date), MAX(as_of_date) FROM relationship_evidence WHERE status = 'current'").fetchone()
            self._span = (date.fromisoformat(lo), date.fromisoformat(hi))
        return self._span

    def first_day(self, key: str) -> date | None:
        r = self.conn.execute("SELECT MIN(as_of_date) FROM relationship_evidence WHERE relationship_key = ? AND status = 'current'", (key,)).fetchone()[0]
        return date.fromisoformat(r) if r else None

    def daily(self, key: str) -> dict:
        """date -> (support, flags) for one relationship, all days (cached)."""
        if key not in self._daily:
            rows = self.conn.execute("SELECT as_of_date, record_json FROM relationship_evidence WHERE relationship_key = ? AND status = 'current'", (key,)).fetchall()
            self._daily[key] = {date.fromisoformat(d): ((j := json.loads(rj)).get("support"), tuple(j.get("flags") or ())) for d, rj in rows}
        return self._daily[key]

    def week_counts(self, key: str, week: Week, span: tuple[date, date], until: date | None = None) -> WeekCounts:
        lo, hi = max(week.start, span[0]), min(week.end, span[1], until or week.end)
        days = self.daily(key)
        sup = sug = ns = ins = placebo = contrary = rec = 0
        d = lo
        while d <= hi:
            got = days.get(d)
            support, flags = got if got else ("insufficient", ())
            rec += got is not None
            sup += support == "supported"
            sug += support == "suggestive"
            ns += support == "not_supported"
            ins += support not in ("supported", "suggestive", "not_supported")
            placebo += "placebo_fired" in flags
            contrary += "contrary" in flags
            d += timedelta(days=1)
        n = max(0, (hi - lo).days + 1)
        return WeekCounts(week.iso, n, sup, sug, ns, ins, placebo, contrary, rec)

    def last_record_id(self, key: str, week: Week, until: date) -> str | None:
        """The id (`rel|<key>|<date>|<method>`) of the last day of the week, not after `until`, that has a record for the key."""
        hi = min(week.end, until)
        r = self.conn.execute("SELECT evidence_id FROM relationship_evidence WHERE relationship_key = ? AND status = 'current' AND as_of_date >= ? AND as_of_date <= ? "
                              "ORDER BY as_of_date DESC LIMIT 1", (key, week.start.isoformat(), hi.isoformat())).fetchone()
        return r[0] if r else None
