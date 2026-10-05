"""The code layer of one case version (findings_engine_spec.md 7 as amended): merges the factors of the case's hand-offs into one factor table, then gives each factor its
wording class and position words, forms the groups, decides the mode, the history note, "not known yet" and the repeat information.

Pure functions of their arguments: no database, no clock, no model. Rank and weight tier are copied through for display and never enter a rule. Labels, flags and
exposure states of the Evidence Engine are used unchanged."""

import re
from dataclasses import dataclass

from v0_code.findings_engine.wording import CLAIM, classify_event, classify_relationship
from v0_code.intel_common.phrasebook import Phrasebook

REL_KEY = re.compile(r"^(\w+)@(\w+)->(\w+)(?::(\w+))?$")
EVENT_TYPES = ("percentile_vs_history", "shape_check", "pattern_repeat", "presence_check")
EXPOSURE_ORDER = ("exposed", "not_yet_available", "not_exposed", "no_data")          # amendment 7: earlier wins


@dataclass(frozen=True)
class Item:
    """One counted hand-off with its event-evidence record."""
    handoff: dict
    evidence: dict

    @property
    def handoff_id(self) -> str:
        return self.handoff["handoff_id"]

    @property
    def date(self) -> str:
        return self.evidence.get("as_of_date") or ""


class NullPi:
    """PI is absent (stage F1): nothing has been seen before and no relationship has a status."""

    def seen_before(self, key: str, exclude_case: str | None = None) -> str:
        return "none"

    def status(self, key: str) -> str | None:
        return None


def key_of(factor: dict) -> str | None:
    """`rel|<relationship_key>|<date>|<method version>` -> the relationship key."""
    rid = factor.get("relationship_evidence_id")
    return rid.split("|")[1] if rid else None


def parse_key(key: str) -> tuple[str, str, str, str | None]:
    m = REL_KEY.match(key)
    if not m:
        raise ValueError(f"the relationship key {key!r} is not <exposure>@<tag>-><outcome>[:<kind>]")
    return m.groups()


def item_kind(item: Item) -> str | None:
    """The meal kind the hand-off's relationships are scoped to (the `:kind` part of any key), if any."""
    for f in item.evidence.get("factors") or []:
        k = key_of(f)
        if k and parse_key(k)[3]:
            return parse_key(k)[3]
    return None


def _kind_of_factor(f: dict) -> str:
    if key_of(f):
        return "relationship"
    return "event" if f.get("check_type") in EVENT_TYPES else "unavailable"


class _Acc:
    """The parts (one per hand-off) of one merged factor."""

    def __init__(self, kind: str, candidate: str, key: str | None, ident):
        self.kind, self.candidate, self.key, self.ident = kind, candidate, key, ident
        self.parts: list[tuple[Item, dict]] = []


def _identity(f: dict, item: Item):
    kind = _kind_of_factor(f)
    if kind == "relationship":
        return kind, ("rel", f["candidate"], key_of(f))
    if kind == "unavailable":
        return kind, ("none", f["candidate"], f.get("reason"))
    if f.get("check_type") == "presence_check":
        return kind, ("presence", f["candidate"])
    return kind, ("event", f["candidate"], item.handoff_id)


def _merge(items: list[Item]) -> list[_Acc]:
    accs: dict = {}
    for it in items:
        for f in sorted(it.evidence.get("factors") or [], key=lambda x: x.get("rank", 0)):
            kind, ident = _identity(f, it)
            acc = accs.get(ident)
            if acc is None:
                acc = accs[ident] = _Acc(kind, f["candidate"], key_of(f), ident)
            acc.parts.append((it, f))
    return list(accs.values())


def _exposure(parts) -> str | None:
    states = [(f.get("event_exposure") or {}).get("state") for _, f in parts]
    for s in EXPOSURE_ORDER:
        if s in states:
            return s
    return None


def build_content(items: list[Item], completions: dict, lib, pb: Phrasebook, pi, case_id: str | None = None) -> dict:
    """The structured layer of a case version. `completions` maps (evidence_id, candidate) to {support, completion_id} for the completions that have arrived."""
    measures = _measures(items, pb)
    accs = _merge(items)
    factors, used_completions = [], []
    for n, acc in enumerate(accs, 1):
        rec = _factor_record(acc, f"f{n}", completions, lib, pb, used_completions)
        factors.append(rec)
    entangled = _entangled_groups(accs, factors)
    groups = _assign_groups(factors, entangled)
    return {"mode": "relationship" if any(f["kind"] == "relationship" and f["wording_class"] in CLAIM for f in factors) else "descriptive", "measures": measures,
            "factors": factors, "groups": groups, "history_note": _history_note(factors), "not_known_yet": _not_known_yet(factors, pb),
            "repeat": _repeat(factors, pi, case_id), "completion_ids": used_completions}


# ---- measures ---------------------------------------------------------------------------------------------------------------------------------------------
def _measures(items: list[Item], pb: Phrasebook) -> list[dict]:
    order = list(pb.raw["strength_words"])
    out: dict = {}
    for it in items:
        h = it.handoff
        k = (h["measure"], h["direction"])
        if k not in out:
            out[k] = {"measure_id": f"m{len(out) + 1}", "measure": h["measure"], "direction": h["direction"], "strength": h["size"], "opened_at": h["opened_at"]}
        elif order.index(h["size"]) > order.index(out[k]["strength"]):
            out[k]["strength"] = h["size"]
    return list(out.values())


# ---- one factor -------------------------------------------------------------------------------------------------------------------------------------------
def _factor_record(acc: _Acc, fid: str, completions: dict, lib, pb: Phrasebook, used: list) -> dict:
    latest = max(it.date for it, _ in acc.parts)
    newest = [(it, f) for it, f in acc.parts if it.date == latest]
    first_it, first_f = acc.parts[0]
    label = newest[0][1].get("support")
    flags = sorted({fl for _, f in newest for fl in f.get("flags") or []})
    reason = newest[0][1].get("reason")
    exposure = _exposure(acc.parts)
    handoff_ids = list(dict.fromkeys(it.handoff_id for it, _ in acc.parts))
    rec = {"factor_id": fid, "candidate": acc.candidate, "kind": acc.kind, "relationship_key": acc.key, "label": label, "flags": flags, "exposure": exposure, "position": None,
           "wording_class": "not_mentioned", "group": None, "handoff_ids": handoff_ids, "rank": first_f.get("rank"), "weight_tier": first_f.get("weight_tier")}
    if acc.kind == "relationship":
        rec["relationship_evidence_ids"] = list(dict.fromkeys(f["relationship_evidence_id"] for _, f in acc.parts))
        rec["wording_class"] = classify_relationship(label, flags, exposure, reason)
        rec["position"] = _relationship_position(acc, newest, exposure, lib, pb)
    elif acc.kind == "event":
        _event(rec, acc, first_it, first_f, completions, pb, used)
    if label == "insufficient" or (reason and acc.kind == "unavailable"):
        rec["insufficient_reason"] = reason
    return rec


def _relationship_position(acc: _Acc, newest, exposure: str | None, lib, pb: Phrasebook) -> str | None:
    """Position words from the exposure's tail percentile; the risk side is the Evidence library's. Binarized exposures carry no percentile."""
    if exposure != "exposed":
        return None
    side = lib.exposures[parse_key(acc.key)[0]].get("risk_side")
    if side not in ("low", "high"):
        return None
    for parts in (newest, acc.parts):
        for _, f in parts:
            ee = f.get("event_exposure") or {}
            if ee.get("state") == "exposed" and ee.get("tail_percentile") is not None:
                return pb.position(ee["tail_percentile"], side)
    return None


def _event(rec: dict, acc: _Acc, item: Item, f: dict, completions: dict, pb: Phrasebook, used: list) -> None:
    check, label = f.get("check_type"), f.get("support")
    es = f.get("event_specific") or {}
    done = completions.get((item.evidence["evidence_id"], acc.candidate)) if check == "shape_check" else None
    if done is not None and label == "not_yet_available":
        label = rec["label"] = done["support"]
        used.append(done["completion_id"])
    present = es.get("present") if check == "presence_check" else None
    cls = classify_event(check, label, rec["exposure"], present)
    if check == "percentile_vs_history" and cls == "event_unusual" and es.get("percentile") is not None:
        words = pb.position(es["percentile"], "high")
        if words is None:
            cls = "not_mentioned"
        else:
            suffix = pb.position_suffix(acc.candidate, es.get("bucket_minutes", 0), item_kind(item))
            rec["position"] = f"{words} {suffix}".strip()
    elif cls == "event_unusual":
        cls = "not_mentioned"
    rec["wording_class"] = cls


# ---- groups -----------------------------------------------------------------------------------------------------------------------------------------------
def _entangled_groups(accs: list[_Acc], factors: list[dict]) -> list[list[int]]:
    """Connected components of the `entangled` overlap flags among claim-class factors. An entry's a and b are matched to factors by the key's part before `->`,
    inside the record of the hand-off the entry sits in."""
    eligible = {i for i, f in enumerate(factors) if f["kind"] == "relationship" and f["wording_class"] in CLAIM}
    parent = {i: i for i in eligible}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    seen = set()
    by_record: dict = {}
    for i, acc in enumerate(accs):
        if i not in eligible:
            continue
        for it, _ in acc.parts:
            by_record.setdefault(it.handoff_id, {}).setdefault(acc.key.split("->")[0], []).append(i)
    items = {it.handoff_id: it for acc in accs for it, _ in acc.parts}
    for hid, it in items.items():
        for o in it.evidence.get("overlap") or []:
            if not o.get("flag"):
                continue
            a, b = by_record.get(hid, {}).get(o["a"], []), by_record.get(hid, {}).get(o["b"], [])
            for x in a:
                for y in b:
                    rx, ry = find(x), find(y)
                    if rx != ry:
                        parent[max(rx, ry)] = min(rx, ry)
                    seen.update((x, y))
    comps: dict = {}
    for i in sorted(seen):
        comps.setdefault(find(i), []).append(i)
    return sorted(comps.values(), key=lambda c: c[0])


def _assign_groups(factors: list[dict], entangled: list[list[int]]) -> list[dict]:
    groups = []
    for comp in entangled:
        gid = f"g{len(groups) + 1}"
        groups.append({"group_id": gid, "reason": "entangled", "members": [factors[i]["factor_id"] for i in comp]})
        for i in comp:
            factors[i]["group"] = gid
    rest = [f for f in factors if f["kind"] == "relationship" and f["wording_class"] in CLAIM and f["group"] is None]
    if len(rest) >= 2:
        gid = f"g{len(groups) + 1}"
        groups.append({"group_id": gid, "reason": "co_exposed", "members": [f["factor_id"] for f in rest]})
        for f in rest:
            f["group"] = gid
    return groups


# ---- history note, not known yet, repeat ------------------------------------------------------------------------------------------------------------------
def _history_note(factors: list[dict]) -> str:
    keyed = [f for f in factors if f["kind"] == "relationship"]
    short = [f for f in keyed if f["label"] == "insufficient" and f.get("insufficient_reason") == "history"]
    if not short:
        return "enough"
    return "not_enough_history_yet" if len(short) * 2 > len(keyed) else "enough_for_some"


def _not_known_yet(factors: list[dict], pb: Phrasebook) -> list[str]:
    out = []
    for f in factors:
        if f["wording_class"] != "not_known_yet":
            continue
        out.append(pb.pending(parse_key(f["relationship_key"])[0]) if f["kind"] == "relationship" else pb.event_pending(f["candidate"]))
    return list(dict.fromkeys(out))


def _repeat(factors: list[dict], pi, case_id: str | None) -> list[dict]:
    return [{"relationship_key": f["relationship_key"], "pi_status": pi.status(f["relationship_key"]), "seen_before": pi.seen_before(f["relationship_key"], exclude_case=case_id)}
            for f in factors if f["kind"] == "relationship" and f["wording_class"] in CLAIM]
