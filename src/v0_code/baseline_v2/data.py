"""Read side of the engine: the Personal Data Store, grouped by local calendar day.

The engine reads ONLY `raw_events` (readings) and `context_events` from the store — no source CSVs (spec section 2). "A day" is a
calendar day in the config timezone, so a UTC+0 patient and an IST patient both work from the same timestamps.
"""

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as _date, datetime, timedelta

from v0_code.baseline_v2.config import Config


@dataclass(frozen=True)
class Reading:
    ts: str            # the stored timestamp string (shown to humans)
    dt: datetime       # timezone-aware, in the config timezone
    value: float


@dataclass(frozen=True)
class CtxRow:
    stream: str
    timestamp: str | None
    date: str
    value_text: str | None
    value_num: float | None
    category: str | None
    meta: dict


class StoreView:
    def __init__(self, conn: sqlite3.Connection, cfg: Config):
        self.cfg = cfg
        tz = cfg.tz

        def local_date(ts: str) -> str:
            return datetime.fromisoformat(ts).astimezone(tz).date().isoformat()

        self.raw: dict[tuple[str, str], list[tuple[str, float, str | None]]] = defaultdict(list)   # (biomarker, date) -> [(ts, value, status)]
        for ts, bio, value, status in conn.execute("SELECT timestamp, biomarker, value, status FROM raw_events WHERE source_type = 'reading' ORDER BY timestamp"):
            self.raw[(bio, local_date(ts))].append((ts, value, status))

        self.ctx: dict[tuple[str, str], list[CtxRow]] = defaultdict(list)                          # (stream, date) -> rows
        for stream, ts, d, vt, vn, cat, meta in conn.execute("SELECT stream, timestamp, date, value_text, value_num, category, meta_json FROM context_events ORDER BY id"):
            day = local_date(ts) if ts else d
            self.ctx[(stream, day)].append(CtxRow(stream, ts, day, vt, vn, cat, json.loads(meta) if meta else {}))

        gname = next((s.name for s in cfg.streams if s.agg == "glucose_mean"), "cgm_glucose_reading")
        self.glucose_stream = gname
        series = sorted((datetime.fromisoformat(ts).astimezone(tz), ts, v) for (b, _d), rows in self.raw.items() if b == gname for ts, v, _s in rows)
        self.glucose_series: list[Reading] = [Reading(ts, dt, v) for dt, ts, v in series]
        gdates = sorted({r.dt.date().isoformat() for r in self.glucose_series})
        # every calendar day between the first and last glucose day is a window (a day with no readings is a window with 0% completeness)
        self.dates: list[str] = []
        if gdates:
            d0, d1 = _date.fromisoformat(gdates[0]), _date.fromisoformat(gdates[-1])
            self.dates = [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days + 1)]

        # medicines seen up to and including each date (as-of: a medicine that first appears later does not exist yet)
        self.meds_by_date: dict[str, set[str]] = {}
        seen: set[str] = set()
        for d in self.dates:
            seen |= {r.category for r in self.ctx.get(("medication_adherence", d), []) if r.category}
            self.meds_by_date[d] = set(seen)

    def labs(self, biomarker: str) -> list[tuple[datetime, float, str | None]]:
        """Lab readings (timezone-aware), oldest first."""
        out = [(datetime.fromisoformat(ts).astimezone(self.cfg.tz), v, st) for (b, _d), rows in self.raw.items() if b == biomarker for ts, v, st in rows]
        return sorted(out, key=lambda x: x[0])

    def raw_rows(self, biomarker: str, date: str) -> list[tuple[str, float, str | None]]:
        return self.raw.get((biomarker, date), [])

    def ctx_rows(self, stream: str, date: str) -> list[CtxRow]:
        return self.ctx.get((stream, date), [])
