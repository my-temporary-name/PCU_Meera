"""The view of the situations line (pi_spec.md 8.1 as amended, item 44): the link in words (context only), the previous situations line, and the DIARY-ONLY sentences of the mid-term
entries that cite the relationship (this week's, plus the earlier entries the previous line was built from). A sentence counts only if every ref it cites (read from the Findings database
by finding id) is a diary item; a sentence that cites a factor, a measure, a history or not-known-yet note, an earlier summary or conclusion, or any mix, is skipped. At most six sentences,
most recent first, none twice. No state, no association sentence, no counts, no dates. Retracted memories have no view. The association sentence of a memory is the P1 code text: the
model neither sees nor edits it."""

import json
import re
import sqlite3
from datetime import date

from v0_code.findings_engine.factors import parse_key
from v0_code.pi_engine.weeks import week_of

CAP = 6


def regeneration_due(created_week: str, week: str, every: int) -> bool:
    """Every `every` weeks counted from the memory's creation week (amendment 25)."""
    mon = lambda iso: date.fromisocalendar(int(iso.split("-W")[0]), int(iso.split("-W")[1]), 1)
    n = (mon(week) - mon(created_week)).days // 7
    return n > 0 and n % every == 0


class FindingsSentences:
    """finding id -> [(sentence text, refs)] from a Findings database, opened read-only. A sentence stored without refs (a code line) has none."""

    def __init__(self, path):
        self.conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

    def __call__(self, finding_id: str) -> list[tuple[str, list[str]]]:
        row = self.conn.execute("SELECT text_json FROM finding_text WHERE finding_id = ?", (finding_id,)).fetchone()
        if row is None:
            return []
        return [(x["text"], list(x.get("refs") or [])) if isinstance(x, dict) else (x, []) for x in json.loads(row[0])["sentences"]]

    def close(self) -> None:
        self.conn.close()


def diary_sentences(entry: dict, refs, prefix: str) -> list[str]:
    """The sentences of an entry that cite only diary items (refs such as d1, d12), in the entry's own order."""
    own = set(entry["sentences"])
    return [t for t, rs in refs(entry["finding_id"]) if t in own and rs and all(re.fullmatch(rf"{re.escape(prefix)}\d+", r) for r in rs)]


def build_view(pi, m: dict, previous: dict | None, regenerated: bool, pb, lib, kinds: set, refs=None, prefix: str = "d") -> tuple[dict | None, list[str]]:
    """`m`: a long-term memory version; `previous`: {"line", "entry_ids"} of the previous situations line or None; `regenerated`: rewrite without the previous line; `refs`: finding id ->
    [(sentence, refs)] (`FindingsSentences`); `prefix`: the diary items' id prefix. Returns (view, the finding ids of the entries whose sentences are in it); (None, []) when there is no
    diary-only sentence."""
    if m["status"] == "retracted":
        raise ValueError("a retracted memory has no view: it takes the code text")
    exposure, tag, outcome, kind = parse_key(m["relationship_key"])
    this = [e for e in pi.get_open_week(m["written_at"])["entries"] if m["relationship_key"] in e["relationship_keys"]]
    keep_previous = previous is not None and previous.get("line") and not regenerated
    earlier = []
    if keep_previous:
        for fid in [x for x in previous["entry_ids"] if x not in {e["finding_id"] for e in this}]:
            e = pi.store.entry_by_finding(fid)
            if e is not None:
                earlier.append(e)
    sentences, ids = [], []
    # most recent first: this week's entries are stored oldest to newest (and are all newer than the earlier weeks' entries, which are ordered by their own time)
    for e in this[::-1] + sorted(earlier, key=lambda e: (e.get("as_of", ""), e["finding_id"]), reverse=True):
        take = [t for t in diary_sentences(e, refs, prefix) if t not in sentences][: CAP - len(sentences)] if refs is not None else []
        if take:
            sentences += take
            ids.append(e["finding_id"])
        if len(sentences) >= CAP:
            break
    if not sentences:
        return None, []
    view = {"link": {"present": pb.exposure(exposure, tag), "outcome": pb.outcome(outcome, kind)}, "previous_situations": previous["line"] if keep_previous else None, "sentences": sentences}
    return view, ids[::-1]


def clean(line: str, view: dict) -> tuple[str, list[str]]:
    """Strip wrapping quotes, capitalise the start and add a final full stop. The raw line is not changed."""
    changes, t = set(), line.strip()
    u = t.strip("\"'“”‘’ ")
    if u != t and t[:1] in "\"'“‘":
        changes.add("quotes_stripped")
        t = u
    if t[:1].isalpha() and t[:1] != t[:1].upper():
        t = t[:1].upper() + t[1:]
        changes.add("capitalised")
    if t and t[-1] not in ".!?":
        t += "."
        changes.add("full_stop_added")
    return t, sorted(changes)
