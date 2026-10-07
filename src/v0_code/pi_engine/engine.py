"""PI, code layer (pi_spec.md 4 to 9, as amended): record_finding into the open week's mid-term memory, the weekly job that seals the week and writes the long-term memories, and
the as-of retrieval calls. Deterministic; no model; every write stamped with the replay clock; versions append-only."""

from datetime import date, datetime, time, timedelta

from v0_code.pi_engine.codetext import code_text, same_day_only
from v0_code.pi_engine.config import PiConfig
from v0_code.pi_engine.labels import DECISIVE, EvidenceLabels, week_label
from v0_code.pi_engine.lifecycle import Wk, initial, step
from v0_code.pi_engine.storage import PiStore, ts
from v0_code.pi_engine.weeks import Week, week_of, week_of_date, weeks_between

USABLE = ("supported", "suggestive")


class PiError(RuntimeError):
    pass


class PiConflict(PiError):
    pass


class SealedWeekError(PiError):
    pass


def _as_ts(as_of) -> int:
    return ts(as_of)


class PiReader:
    """The retrieval calls of section 9. Every one takes `as_of` and returns only what was written at or before it. With `strict` (the loop's reader) it returns only what was written
    strictly before it, so a read never depends on what happened to be written at the same instant (a rerun over a database that already holds it reads the same as the first run)."""

    def __init__(self, cfg: PiConfig, store: PiStore, strict: bool = False):
        self.cfg, self.store, self.tz, self.strict = cfg, store, cfg.tz, strict

    def _t(self, as_of) -> int:
        return _as_ts(as_of) - (1 if self.strict else 0)                                  # written_ts is whole seconds: "<= t - 1" is "< t"

    def _week_dict(self, w: Week) -> dict:
        return {"iso": w.iso, "start": w.start.isoformat(), "end": w.end.isoformat()}

    def _mid_record(self, week: Week, as_of_ts: int, status: str, sealed_at: str | None) -> dict:
        mid = f"pi_mid_{week.iso}"
        entries = self.store.latest_entries(mid, as_of_ts)
        keys: list[str] = []
        for e in entries:
            keys += [k for k in e["relationship_keys"] if k not in keys]
        return {"memory_id": mid, "tier": "mid_term", "week": self._week_dict(week), "status": status, "sealed_at": sealed_at,
                "entries": [{k: e[k] for k in ("case_id", "local_date", "finding_id", "entry_version", "mode", "relationship_keys", "relationships", "headline", "sentences")} for e in entries],
                "relationship_keys_touched": keys, "case_days": sorted({e["local_date"] for e in entries})}

    def get_long_term(self, relationship_key: str, as_of) -> dict | None:
        return self.store.latest_long(relationship_key, self._t(as_of))

    def get_long_term_many(self, keys, as_of) -> dict:
        t = self._t(as_of)
        out = {k: self.store.latest_long(k, t) for k in keys}
        return {k: v for k, v in out.items() if v is not None}

    def list_long_term(self, status: str | None, as_of) -> list[dict]:
        return [m for m in self.store.latest_long_all(self._t(as_of)) if status is None or m["status"] == status]

    def get_open_week(self, as_of) -> dict:
        """The entries received so far in the week that contains `as_of` (the latest version of each case)."""
        t = self._t(as_of)
        w = week_of(as_of, self.tz)
        mid = f"pi_mid_{w.iso}"
        sealed = self.store.has_mid(mid, "sealed", t)
        return self._mid_record(w, t, "sealed" if sealed else "open", self.store.sealed_at(mid) if sealed else None)

    def get_sealed_weeks(self, n: int, as_of) -> list[dict]:
        return self.store.sealed_weeks(n, self._t(as_of))

    def get_case_entry(self, case_id: str, as_of) -> dict | None:
        return self.store.case_entry(case_id, self._t(as_of))

    def get_seen_before(self, relationship_key: str, as_of, exclude_case: str | None = None) -> str:
        """none / this_week / recent_weeks / earlier, from the latest local_date of the relationship in any entry written by `as_of` and in its long-term dates, leaving out
        `exclude_case`."""
        t = self._t(as_of)
        dates = []
        d = self.store.latest_seen_date(relationship_key, t, exclude_case)
        if d:
            dates.append(d)
        m = self.store.latest_long(relationship_key, t)
        if m:
            for day, cases in m["dates"]["case_days"].items():
                if exclude_case and set(cases) == {exclude_case}:
                    continue
                dates.append(day)
        if not dates:
            return "none"
        today = (datetime.fromisoformat(as_of) if isinstance(as_of, str) else as_of).astimezone(self.tz).date()
        days = (today - date.fromisoformat(max(dates))).days
        b = self.cfg.seen_before_bands
        return "this_week" if days <= b["this_week_days"] else "recent_weeks" if days <= b["recent_weeks_days"] else "earlier"


class Pi(PiReader):
    def __init__(self, cfg: PiConfig, store: PiStore, labels: EvidenceLabels, lib, pb):
        super().__init__(cfg, store)
        self.labels, self.lib, self.pb = labels, lib, pb

    # ---- record_finding ---------------------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _entry(finding: dict) -> dict:
        rels, seen = [], set()
        for f in finding["factors"]:
            k = f.get("relationship_key")
            if f.get("kind") == "relationship" and k and f.get("label") in USABLE and k not in seen:
                seen.add(k)
                rels.append({"relationship_key": k, "exposed": f.get("exposure") == "exposed", "label": f["label"], "flags": list(f.get("flags") or [])})
        t = finding["text"]
        return {"case_id": finding["case_id"], "local_date": finding["local_date"], "finding_id": finding["finding_id"], "entry_version": finding["version"], "mode": finding["mode"],
                "relationship_keys": [r["relationship_key"] for r in rels], "relationships": rels, "headline": t["headline"],
                "sentences": [s["text"] if isinstance(s, dict) else s for s in t["sentences"]], "as_of": finding["as_of"]}

    def _ensure_open(self, week: Week) -> None:
        opened = datetime.combine(week.start, time(0, 0), tzinfo=self.tz).isoformat()
        self.store.put_mid(f"pi_mid_{week.iso}", "open", week, opened)

    def record_finding(self, finding: dict) -> str:
        """Idempotent by `finding_id`. The entry lands in the week of the version's `as_of`. Returns "written" or "same"."""
        entry = self._entry(finding)
        week = week_of(finding["as_of"], self.tz)
        mid = f"pi_mid_{week.iso}"
        old = self.store.entry_by_finding(finding["finding_id"])
        if old is not None:
            if old != entry:
                raise PiConflict(f"{finding['finding_id']} is already recorded with different content")
            return "same"
        if self.store.has_mid(mid, "sealed"):
            raise SealedWeekError(f"{finding['finding_id']} (as_of {finding['as_of']}) belongs to {week.iso}, which is sealed")
        if self.store.entry_exists(mid, entry["case_id"], entry["entry_version"]):
            raise PiConflict(f"{entry['case_id']} version {entry['entry_version']} is already recorded under another finding id")
        self._ensure_open(week)
        self.store.put_entry(mid, entry, finding["as_of"])
        return "written"

    def replace_entry_text(self, finding_id: str, headline: str, sentences: list[str]) -> bool:
        """The loop's barrier (stage L2): put the final text into an entry of a week that is not sealed yet. Nothing but the text changes."""
        entry = self.store.entry_by_finding(finding_id)
        if entry is None:
            raise KeyError(finding_id)
        week = week_of(entry["as_of"], self.tz)
        if self.store.has_mid(f"pi_mid_{week.iso}", "sealed"):
            raise SealedWeekError(f"{finding_id} belongs to {week.iso}, which is sealed")
        return self.store.update_entry_text(finding_id, headline, sentences)

    # ---- the weekly job ---------------------------------------------------------------------------------------------------------------------------------
    def _through(self, key: str, week: Week, span, until: date) -> tuple:
        """The lifecycle state and the weekly labels of a relationship from the first week it was tested to `week` (a pure function of the Evidence store's daily labels, read up
        to `until`)."""
        first = self.labels.first_day(key)
        if first is None or first > min(week.end, until):
            return initial(), [], []
        state, labels, weeks = initial(), [], weeks_between(week_of_date(first), week)
        for w in weeks:
            c = self.labels.week_counts(key, w, span, until=until if w == week else None)
            label = week_label(c, self.cfg.label)
            labels.append({"week": w.iso, "label": label, "days_supported": c.supported, "days_in_week": c.days_in_week, "placebo_days": c.placebo_days, "contrary_days": c.contrary_days,
                           "days_with_record": c.days_with_record})
            state = step(state, Wk(w.iso, min(w.end, span[1]).isoformat(), label, c.days_in_week, c.placebo_days, c.contrary_days, c.days_with_record, c.supported), self.cfg.lifecycle)
        return state, labels, weeks

    def weekly_job(self, week: Week, job_time: datetime) -> dict:
        existing = self.store.get_run(week.iso)
        if existing is not None:
            return existing
        span, until, job_ts, job_iso = self.labels.span(), job_time.astimezone(self.tz).date(), int(job_time.timestamp()), job_time.isoformat()
        mid = f"pi_mid_{week.iso}"
        self._ensure_open(week)
        # 1. seal
        record = self._mid_record(week, job_ts, "sealed", job_iso)
        self.store.put_mid(mid, "sealed", week, job_iso, sealed_at=job_iso, record=record)
        entries = self.store.latest_entries(mid, job_ts)
        usage: dict = {}
        for e in entries:
            for r in e["relationships"]:
                usage.setdefault(r["relationship_key"], []).append((e, r))
        known = {m["relationship_key"] for m in self.store.latest_long_all(job_ts)}
        created, changes, texts_updated, written, due = [], [], 0, 0, []
        for key in sorted(known | set(usage)):
            prev = self.store.latest_long(key, job_ts)
            state, labels, weeks = self._through(key, week, span, until)           # 2 and 3: week labels, and the back-fill on creation
            dates = {"case_days": {}, "exposed_case_days": {}, "weeks": []} if prev is None else {k: (dict(v) if isinstance(v, dict) else list(v)) for k, v in prev["dates"].items()}
            flags, fids = set(prev["flags_seen"]) if prev else set(), list(prev["finding_ids"]) if prev else []
            for e, r in usage.get(key, []):                                         # 4. counters, from the latest entry of each case
                for bucket, on in (("case_days", True), ("exposed_case_days", r["exposed"])):
                    if on:
                        dates[bucket][e["local_date"]] = sorted(set(dates[bucket].get(e["local_date"], [])) | {e["case_id"]})
                flags |= set(r["flags"])
                if e["finding_id"] not in fids:
                    fids.append(e["finding_id"])
            if key in usage and week.iso not in dates["weeks"]:
                dates["weeks"].append(week.iso)
            days = sorted(dates["case_days"])
            counters = {"case_days": len(days), "exposed_case_days": len(dates["exposed_case_days"]), "first_seen": days[0] if days else None, "last_seen": days[-1] if days else None,
                        "weeks_seen": len(dates["weeks"])}
            same_day = same_day_only(self.lib, key)                                 # 5/6. status (the lifecycle) and the code text
            text = code_text(key, state.status, same_day, self.pb)
            created_week = prev["created_week"] if prev else week.iso
            n_since = (week.start - week_of_date(date.fromisoformat(created_week_start(created_week))).start).days // 7
            if n_since > 0 and n_since % self.cfg.regenerate_every_weeks == 0:
                due.append(key)
            refs = [r for w, lab in zip(weeks, labels) if lab["label"] in DECISIVE and (r := self.labels.last_record_id(key, w, until))]
            rec = {"memory_id": f"pi_long_{key}", "tier": "long_term", "relationship_key": key, "version": (prev["version"] + 1) if prev else 1, "written_at": job_iso, "status": state.status,
                   "status_since": state.since, "same_day_only": same_day, "story_coupling": "unknown", "weekly_labels": labels, "counters": counters, "flags_seen": sorted(flags),
                   "evidence_refs": refs, "finding_ids": fids, "text": text, "text_version": (prev["text_version"] + (prev["text"] != text)) if prev else 1,
                   "status_history": state.history, "dates": dates, "created_week": created_week}
            for t in state.history:
                if t["week"] == week.iso:
                    changes.append({"relationship_key": key, "from": t["from"], "to": t["to"]})
            if prev is None:
                created.append(key)
            changed = prev is None or any(prev[k] != rec[k] for k in ("status", "counters", "flags_seen", "finding_ids", "text"))
            if prev is None or prev["text"] != text:
                texts_updated += 1
            if changed:                                                             # 7. a version only when something changed
                self.store.put_long(rec)
                written += 1
        run = {"week": week.iso, "written_at": job_iso, "memories_created": created, "statuses_changed": changes, "texts_updated": texts_updated, "texts_kept": 0, "usage_json": {},
               "counts": {"entries": len(entries), "case_days": len({e["local_date"] for e in entries}), "memories_total": len(known | set(usage)), "memories_written": written,
                          "touched": len(usage), "regeneration_due": due}, "mid_memory": mid}
        self.store.put_run(run)                                                     # 8. the run record
        return run


def created_week_start(iso: str) -> str:
    """The Monday of an ISO week name like 2026-W10."""
    year, week = iso.split("-W")
    return date.fromisocalendar(int(year), int(week), 1).isoformat()
