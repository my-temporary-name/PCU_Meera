"""Findings reading PI as-of (stage L1; findings_engine_spec.md 6, 7.6 and 8.1, pi_spec.md 9). `PiLive` is the interface the Findings loop uses (`at`, `status`, `seen_before`,
`memory_refs`); every read goes through PI's retrieval calls with the version's own `as_of`, so only memories and entries written at or before it are seen, and is logged.

- `status(key)` / `seen_before(key, exclude_case)` fill each `repeat` entry of a version (`pi_status`, `seen_before`). They are context only: they never change a wording class.
- `memory_refs(factors, case_id)` fills `refs.pi_memories`: the long-term memory (by id and version) of every usable relationship factor of the version, the open week's entries (finding
  ids; the case's own earlier versions are among them) and the last `recent_weeks` sealed weeks. A long-term memory whose relationship the view shows, and whose status has a state word
  (config), gets a view id `p<n>`; a retracted memory has no state word, so it is listed but has no view id and no earlier conclusion.
- `earlier_conclusions(record, reader, state_words)` builds the view's `earlier_conclusions` from a stored record: it reads the exact PI versions the record names."""

from datetime import datetime

from v0_code.pi_engine.engine import USABLE, PiReader
from v0_code.pi_engine.text_check import FRAME

HIDDEN = ("not_mentioned", "not_known_yet")                     # wording classes the view does not show as a thing (so nothing to attach an earlier conclusion to)


def _iso(as_of) -> str:
    return as_of.isoformat() if isinstance(as_of, datetime) else str(as_of)


class PiLive:
    def __init__(self, reader: PiReader, state_words: dict, recent_weeks: int, include_open_week: bool = True):
        self.reader, self.state_words, self.recent_weeks, self.include_open_week = reader, dict(state_words), int(recent_weeks), include_open_week
        self.as_of = None
        self.reads: list[dict] = []

    def at(self, as_of) -> None:
        self.as_of = as_of

    def _log(self, call: str, **kw) -> None:
        self.reads.append({"call": call, "as_of": _iso(self.as_of), **kw})

    # ---- repeat ------------------------------------------------------------------------------------------------------------------------------------------
    def status(self, key: str) -> str | None:
        m = self.reader.get_long_term(key, self.as_of)
        self._log("get_long_term", key=key, version=m["version"] if m else None, written_at=m["written_at"] if m else None)
        return m["status"] if m else None

    def seen_before(self, key: str, exclude_case: str | None = None) -> str:
        band = self.reader.get_seen_before(key, self.as_of, exclude_case)
        self._log("get_seen_before", key=key, exclude_case=exclude_case, band=band)
        return band

    # ---- refs.pi_memories -------------------------------------------------------------------------------------------------------------------------------
    def memory_refs(self, factors: list[dict], case_id: str) -> list[dict]:
        keys = list(dict.fromkeys(f["relationship_key"] for f in factors if f["kind"] == "relationship" and f.get("label") in USABLE))
        shown = {f["relationship_key"] for f in factors if f["kind"] == "relationship" and f["wording_class"] not in HIDDEN}
        memories = self.reader.get_long_term_many(keys, self.as_of)
        for k in keys:
            m = memories.get(k)
            self._log("get_long_term_many", key=k, version=m["version"] if m else None, written_at=m["written_at"] if m else None)
        refs, n = [], 0
        for k in keys:
            m = memories.get(k)
            if m is None:
                continue
            ref = {"tier": "long_term", "memory_id": m["memory_id"], "relationship_key": k, "version": m["version"], "status": m["status"], "written_at": m["written_at"]}
            if k in shown and m["status"] in self.state_words:
                n += 1
                ref["view_id"] = f"p{n}"
            refs.append(ref)
        if self.include_open_week:
            week = self.reader.get_open_week(self.as_of)
            ids = [e["finding_id"] for e in week["entries"]]
            self._log("get_open_week", memory_id=week["memory_id"], finding_ids=ids)
            if ids:
                refs.append({"tier": "mid_term", "memory_id": week["memory_id"], "status": "open", "finding_ids": ids})
        sealed = self.reader.get_sealed_weeks(self.recent_weeks, self.as_of)
        self._log("get_sealed_weeks", memory_ids=[w["memory_id"] for w in sealed], sealed_at=[w["sealed_at"] for w in sealed])
        refs += [{"tier": "mid_term", "memory_id": w["memory_id"], "status": "sealed", "sealed_at": w["sealed_at"]} for w in sealed]
        return refs


def earlier_conclusions(record: dict, reader: PiReader, state_words: dict, situations=None) -> list[dict]:
    """The view's `earlier_conclusions` for a stored record: for each long-term ref that has a view id, `about` (the ids of the things in the view that carry the relationship), the state word,
    the association text and the `seen_before` band, plus the situations line when the memory version has one (`situations(memory_id, version)`, the text overlay; none in L1 or when
    the line is null, so the key is left out)."""
    band = {r["relationship_key"]: r["seen_before"] for r in record["repeat"]}
    shown = [f for f in record["factors"] if f["kind"] == "relationship" and f["wording_class"] not in HIDDEN]
    items = []
    for ref in record["refs"]["pi_memories"]:
        if ref.get("tier") != "long_term" or "view_id" not in ref:
            continue
        m = reader.store.long_version(ref["memory_id"], ref["version"])
        key = ref["relationship_key"]
        item = {"id": ref["view_id"], "about": [f["factor_id"] for f in shown if f["relationship_key"] == key], "state": state_words[m["status"]], "text": " ".join(m["text"]["sentences"]),
                "seen_before": band.get(key) or reader.get_seen_before(key, record["as_of"], record["case_id"])}
        line = situations(ref["memory_id"], ref["version"]) if situations else None
        if line:
            item["situations"] = line.replace(FRAME, "").strip(" .,")                           # the list only: the frame's word "cases" is an internal word no view may carry
        items.append(item)
    return items
