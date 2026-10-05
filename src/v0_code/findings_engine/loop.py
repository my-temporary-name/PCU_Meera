"""The minimal ordered event loop and the case rules (findings_engine_spec.md 5 and 4 as amended). Replay over the hand-offs and completions in time order: a counted hand-off
(packet `ok`) opens or joins a case and writes a version; a completion writes a version at its own time; a deferred or unmatched hand-off is recorded and never opens a case
or moves the gap clock. A case closes when `gap_hours` pass after its last counted hand-off; closing is recorded on the case and writes no version.

Pure: no database, no clock. The same inputs and settings give identical cases, versions, ids and records.

Stage L1 (the loop) drives this same function with optional `hooks` (`before_event(t)` runs before each event is handled, `after_version(version)` after each version is built) and a PI
that is bound to each version's time: `pi.at(as_of)` is called first, then `pi.status`, `pi.seen_before` and, if present, `pi.memory_refs(factors, case_id)` (which fills `refs.pi_memories`).
Without hooks, `max_events` or such a PI the result is exactly what it was before."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from v0_code.findings_engine.codeline import code_sentences
from v0_code.findings_engine.factors import Item, NullPi, build_content
from v0_code.intel_common.phrasebook import Phrasebook
from v0_code.intel_common.timeutil import to_local

COUNTED = "ok"


@dataclass(frozen=True)
class Settings:
    gap_hours: float
    max_span_hours: float
    tz: ZoneInfo


@dataclass
class Replay:
    cases: list = field(default_factory=list)
    case_handoffs: list = field(default_factory=list)
    unattached: list = field(default_factory=list)
    versions: list = field(default_factory=list)


class _NoContext:
    def refs(self, as_of: datetime, local_date: str) -> dict:
        return {"diary": [], "state_memory": [], "pi_memories": []}


class _Case:
    def __init__(self, hand: dict, local_date: str):
        self.id = f"case_{hand['opened_at']}"
        self.first = datetime.fromisoformat(hand["opened_at"])
        self.last = self.first
        self.local_date = local_date
        self.items: list[Item] = []
        self.recorded: list[dict] = []
        self.version = 0
        self.row = {"case_id": self.id, "local_date": local_date, "opened_at": hand["opened_at"], "last_handoff_at": hand["opened_at"], "closed_at": None, "status": "open",
                    "n_counted": 0, "n_recorded": 0, "n_versions": 0}

    def can_take(self, t: datetime, s: Settings) -> bool:
        return t - self.last <= timedelta(hours=s.gap_hours) and t - self.first <= timedelta(hours=s.max_span_hours)


def replay(handoffs: list[dict], packet_status: dict, evidence: dict, completions: list[dict], settings: Settings, lib, pb: Phrasebook, pi=None, context=None, hooks=None,
           max_events: int | None = None) -> Replay:
    pi, context = pi or NullPi(), context or _NoContext()
    events = [(datetime.fromisoformat(h["opened_at"]), 0, h["handoff_id"], h) for h in handoffs]
    events += [(datetime.fromisoformat(c["evaluated_from"]["end"]), 1, f"{c['evidence_id']}#{c['candidate']}", c) for c in completions]
    events.sort(key=lambda e: e[:3])
    out, cur, case_of_handoff, arrived = Replay(), None, {}, {}
    gap = timedelta(hours=settings.gap_hours)

    def close(case):
        case.row["closed_at"] = (case.last + gap).isoformat()
        case.row["status"] = "closed"

    stopped = False
    for n, (t, kind, key, rec) in enumerate(events):
        if max_events is not None and n >= max_events:                    # a stop for the loop's resumability: the open case stays open, nothing is closed
            stopped = True
            break
        if hooks is not None:
            hooks.before_event(t)
        if cur is not None and t - cur.last > gap:
            close(cur)
            cur = None
        if kind == 0:
            status = packet_status.get(rec["handoff_id"])
            if status != COUNTED:
                if cur is not None and cur.can_take(t, settings):
                    cur.recorded.append(rec)
                    cur.row["n_recorded"] += 1
                    out.case_handoffs.append({"case_id": cur.id, "handoff_id": rec["handoff_id"], "joined_at": rec["opened_at"], "counted": False, "packet_status": status})
                else:
                    out.unattached.append({"handoff_id": rec["handoff_id"], "opened_at": rec["opened_at"], "packet_status": status})
                continue
            if cur is None or not cur.can_take(t, settings):
                if cur is not None:
                    close(cur)
                cur = _Case(rec, to_local(rec["opened_at"], settings.tz).date().isoformat())
                out.cases.append(cur.row)
            cur.items.append(Item(rec, evidence[rec["handoff_id"]]))
            cur.last = t
            cur.row["last_handoff_at"] = rec["opened_at"]
            cur.row["n_counted"] += 1
            case_of_handoff[rec["handoff_id"]] = cur
            out.case_handoffs.append({"case_id": cur.id, "handoff_id": rec["handoff_id"], "joined_at": rec["opened_at"], "counted": True, "packet_status": status})
            case = cur
        else:
            case = next((c for c in case_of_handoff.values() if any(i.evidence["evidence_id"] == rec["evidence_id"] for i in c.items)), None)
            if case is None:
                continue
            arrived[(rec["evidence_id"], rec["candidate"])] = {"support": rec["support"], "completion_id": key}
        out.versions.append(_version(case, t, lib, pb, pi, context, arrived))
        case.row["n_versions"] = case.version
        if hooks is not None:
            hooks.after_version(out.versions[-1])
    if cur is not None and not stopped:
        close(cur)
    return out


def _version(case: _Case, as_of: datetime, lib, pb: Phrasebook, pi, context, arrived: dict) -> dict:
    case.version += 1
    if hasattr(pi, "at"):
        pi.at(as_of)
    content = build_content(case.items, arrived, lib, pb, pi, case_id=case.id)
    sentences = code_sentences(content, pb)
    refs = context.refs(as_of, case.local_date)
    if hasattr(pi, "memory_refs"):
        refs = {**refs, "pi_memories": pi.memory_refs(content["factors"], case.id)}
    return {"finding_id": f"fnd_{case.id}_v{case.version}", "case_id": case.id, "version": case.version, "provisional": True, "closed": False, "as_of": as_of.isoformat(),
            "local_date": case.local_date, "handoff_ids": [i.handoff_id for i in case.items], "evidence_ids": [i.evidence["evidence_id"] for i in case.items],
            "completion_ids": content.pop("completion_ids"), **content, "refs": refs,
            "text": {"headline": sentences[0], "sentences": [{"text": s, "refs": []} for s in sentences[1:]], "source": "code_line"}, "checks": {"passed": True, "failed": []}, "status": "ok"}
