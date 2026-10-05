"""Read-only access to the Personal Data Store through the patient's stream map (spec 4.3). Every record is normalised to one shape, a series is cleaned with the
Baseline Engine's own rule, and the State Engine's availability rules (block ends, end of day, hourly rows) are applied here, in one place."""

import json
import sqlite3
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from v0_code.baseline_v2.data import Reading
from v0_code.baseline_v2.trust import clean_series
from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.library import Library


@dataclass(frozen=True)
class Rec:
    ts: datetime | None            # None for a date-only record
    date: date                     # local date
    value: float | None
    text: str | None
    category: str | None
    meta: dict = field(default_factory=dict, compare=False)
    block: str | None = None


class DataError(ValueError):
    pass


class EvidenceData:
    def __init__(self, conn: sqlite3.Connection, cfg: EvidenceConfig, lib: Library):
        self.conn, self.cfg, self.lib, self.tz = conn, cfg, lib, cfg.tz
        self._raw_names = {r[0] for r in conn.execute("SELECT DISTINCT biomarker FROM raw_events WHERE source_type = 'reading'")}
        self._ctx_names = {r[0] for r in conn.execute("SELECT DISTINCT stream FROM context_events")}
        self._recs: dict[str, list[Rec]] = {}
        self._by_date: dict[str, dict[date, list[Rec]]] = {}
        self._clean: dict[str, list[tuple[datetime, float]]] = {}
        self.kinds = tuple(cfg.state.meal_kinds)
        self.meal_bucket = cfg.state.meal_bucket_minutes

    # ---- streams ----------------------------------------------------------------------------------------------------------------------------------
    def store_ref(self, token: str) -> tuple[str, str] | None:
        """(table, name) of a generic token, or None when the patient has no such stream (the factor is `insufficient`, reason `no_stream`)."""
        v = self.cfg.stream_map.get(token)
        if v is None:
            return None
        if isinstance(v, dict):
            table, name = v["table"], v["name"]
        else:
            name, hits = v, [t for t, names in (("raw", self._raw_names), ("context", self._ctx_names)) if v in names]
            if len(hits) > 1:
                raise DataError(f"stream {v!r} exists in both tables; name the table in the stream map")
            if not hits:
                return None
            table = hits[0]
        return (table, name) if name in (self._raw_names if table == "raw" else self._ctx_names) else None

    def has(self, token: str) -> bool:
        return self.store_ref(token) is not None

    def state_stream(self, token: str):
        """The State Engine's config row for the token's store stream (None when it is not a State Engine stream)."""
        ref = self.store_ref(token)
        if ref is None:
            return None
        return next((s for s in self.cfg.state.streams if s.source.get("name") == ref[1] or ref[1] in (s.source.get("names") or ())), None)

    def _local_date(self, ts: datetime) -> date:
        return ts.astimezone(self.tz).date()

    def _parse(self, ts: str | None):
        if not ts:
            return None
        if len(ts) == 10:
            return None
        return datetime.fromisoformat(ts).astimezone(self.tz)

    def records(self, token: str) -> list[Rec]:
        if token in self._recs:
            return self._recs[token]
        ref = self.store_ref(token)
        out: list[Rec] = []
        if ref is not None:
            table, name = ref
            block_key = (self.state_stream(token).source.get("block_key") if self.state_stream(token) else None)
            if table == "raw":
                for ts, v in self.conn.execute("SELECT timestamp, value FROM raw_events WHERE biomarker = ? AND source_type = 'reading' ORDER BY timestamp, id", (name,)):
                    t = self._parse(ts)
                    out.append(Rec(t, t.date() if t else date.fromisoformat(ts[:10]), v, None, None))
            else:
                for ts, d, vt, vn, cat, meta in self.conn.execute("SELECT timestamp, date, value_text, value_num, category, meta_json FROM context_events WHERE stream = ? ORDER BY id", (name,)):
                    t = self._parse(ts)
                    m = json.loads(meta) if meta else {}
                    out.append(Rec(t, t.date() if t else date.fromisoformat(d), vn, vt, cat, m, m.get(block_key) if block_key else None))
            out.sort(key=lambda r: (r.ts or datetime.combine(r.date, time(0), tzinfo=self.tz), r.date))
        self._recs[token] = out
        return out

    def by_date(self, token: str) -> dict[date, list[Rec]]:
        if token not in self._by_date:
            d: dict[date, list[Rec]] = {}
            for r in self.records(token):
                d.setdefault(r.date, []).append(r)
            self._by_date[token] = d
        return self._by_date[token]

    def readings(self, token: str) -> list[tuple[datetime, float]]:
        """The token's timestamped numeric readings; cleaned with the Baseline Engine's rule when the library says so (device range and jump rule)."""
        if token in self._clean:
            return self._clean[token]
        raw = [(r.ts, r.value) for r in self.records(token) if r.ts is not None and r.value is not None]
        if self.lib.sources.get(token, {}).get("clean") == "baseline":
            kept, _ = clean_series([Reading(t.isoformat(), t, v) for t, v in raw], self.cfg.baseline)
            raw = [(r.dt, r.value) for r in kept]
        self._clean[token] = raw
        return raw

    # ---- kinds and availability -----------------------------------------------------------------------------------------------------------------------
    def kind_of(self, label: str | None) -> str | None:
        """The State Engine's meal-kind matching: the first configured kind contained in the label text."""
        low = (label or "").lower()
        return next((k for k in self.kinds if k in low), None)

    def event_kind(self, token: str, rec: Rec) -> str | None:
        """The kind of an event record (a meal): the State Engine's label matching on the field the library names for this source."""
        field_ = self.lib.sources.get(token, {}).get("label_field", "category")
        return self.kind_of(getattr(rec, field_))

    def block_end(self, token: str, rec: Rec) -> datetime | None:
        """The end of a block record: the State Engine's `available_at` for that block on its date."""
        s = self.state_stream(token)
        if s is None or not isinstance(s.available_at, dict) or rec.block not in s.available_at:
            return None
        h, m = (int(x) for x in s.available_at[rec.block].split(":"))
        return datetime.combine(rec.date, time(h, m), tzinfo=self.tz)

    def avail_rule(self, token: str, rec: Rec | None = None) -> str:
        """The availability rule of a token's records: the library's own (a stream the State Engine does not know), else the State Engine's `available_at`."""
        src = self.lib.sources.get(token, {})
        if "available_at" in src:
            return src["available_at"]
        s = self.state_stream(token)
        if s is not None:
            return "block_end" if isinstance(s.available_at, dict) else str(s.available_at)
        ref = self.store_ref(token)
        for c in self.cfg.state.context_streams.values():
            if ref and c.get("name") == ref[1]:
                return "timestamp" if rec is not None and rec.ts is not None else str(c.get("available_at", "end_of_day"))
        return "timestamp" if rec is None or rec.ts is not None else "end_of_day"

    def available_at(self, token: str, rec: Rec) -> datetime:
        """When a record becomes available to the system (spec 3.1 rule 3): its timestamp, the end of its day, a clock time on its date, the end of its block or the end of its hour."""
        rule = self.avail_rule(token, rec)
        mid = datetime.combine(rec.date, time(0), tzinfo=self.tz)
        if rule == "block_end":
            return self.block_end(token, rec) or mid + timedelta(days=1)
        if rule == "timestamp":
            return rec.ts or mid
        if rule == "end_of_day":
            return mid + timedelta(days=1)
        if rule == "end_of_hour":
            return (rec.ts or mid) + (self.span(token) or timedelta(hours=1))
        h, m = (int(x) for x in rule.split(":"))
        return datetime.combine(rec.date, time(h, m), tzinfo=self.tz)

    def span(self, token: str) -> timedelta:
        return timedelta(minutes=int(self.lib.sources.get(token, {}).get("span_minutes", 0)))

    def ts_index(self, token: str) -> tuple[list[datetime], list[Rec]]:
        """The token's timestamped records that carry a value, with their times, for bisecting."""
        key = "_ts_" + token
        if key not in self.__dict__:
            recs = [r for r in self.records(token) if r.ts is not None and r.value is not None]
            self.__dict__[key] = ([r.ts for r in recs], recs)
        return self.__dict__[key]

    def readings_between(self, token: str, lo: datetime, hi: datetime) -> list[float]:
        r = self.readings(token)
        times = self._times(token)
        i, j = bisect_left(times, lo), bisect_right(times, hi)
        return [v for _, v in r[i:j]]

    def _times(self, token: str) -> list[datetime]:
        key = "_t_" + token
        if key not in self.__dict__:
            self.__dict__[key] = [t for t, _ in self.readings(token)]
        return self.__dict__[key]
