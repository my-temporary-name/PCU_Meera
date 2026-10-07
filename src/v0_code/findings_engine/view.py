"""The numberless view of one case version (findings_engine_spec.md 8.1 as amended): what the text layer is allowed to see. Built from the stored structured record, the
hand-offs' meal context, the as-of context (diary, earlier summaries) and the phrase book. No digit, date, time of day, count, internal id or statistic appears in the code-built
parts; diary text, the diary note and earlier-summary headlines are passed as written (the model must not repeat their digits). Static presence facts are not in the view.

No key and no code-built value of the view is a banned (internal) word: the structured layer's own names are translated here (`VIEW_WORDING`, `MODE_WORDS`, the key names).
Ids are the record's own: `f<n>` for things, `g<n>` for sets, `m<n>` for measures; diary `d<n>` and earlier summaries `s<n>` as stored in `refs` (diary entries added because
they back a point continue the numbering); `h1` the history note, `n1` the not-known-yet list, `p<k>` the earlier conclusions."""

import hashlib
import json
import re
from datetime import datetime

from v0_code.evidence_engine.windows import window_for
from v0_code.findings_engine.factors import parse_key
from v0_code.findings_engine.wording import CLAIM
from v0_code.intel_common.phrasebook import Phrasebook
from v0_code.intel_common.timeutil import part_of_day, to_local

VIEW_WORDING = {"asserted": "asserted", "asserted_same_day": "asserted_same_day", "hedged": "hedged", "hedged_same_day": "hedged_same_day", "exposure_only": "present_only",
                "exposure_only_history": "present_only_history", "contrary_note": "contrary_note", "event_unusual": "event_unusual", "artifact_note": "artifact_note"}
INTERNAL_WORDING = {v: k for k, v in VIEW_WORDING.items()}
VIEW_REASON = {"entangled": "often_together", "co_exposed": "present_together"}
MODE_WORDS = {"relationship": "may_discuss_links", "descriptive": "describe_only"}
HISTORY_WORDS = {"enough": "enough history", "enough_for_some": "enough history for some of these, not for others", "not_enough_history_yet": "not enough history yet"}
WINDOW_WORDS = {"yesterday_day": "yesterday", "last_week": "the last week", "latest_month": "the latest month"}


def meal_context(handoffs: list[dict], pb: Phrasebook) -> str | None:
    """'<a kind of meal> <how long earlier>', from the latest hand-off of the case that carries a last meal."""
    for h in reversed(handoffs):
        m = (h.get("context") or {}).get("last_meal")
        if m:
            return f"{pb.meal_label(m['label'])} {pb.meal_ago(m['minutes_ago'])}"
    return None


DEFAULT_SUMMARIES = {"use": ["yesterday_day"], "notable_only": True}


def merge_things(things: list[dict]) -> tuple[list[dict], dict]:
    """Things with identical content (name, wording, position, outcome, statement, set: everything but the id) become one thing, the first, carrying every factor id as `ids`. Returns the
    things and a map from every factor id to the id of the thing that stands for it. The record is never touched: this only shapes the view."""
    members: dict[str, list[str]] = {}
    first: dict[str, dict] = {}
    order: list[str] = []
    primary: dict[str, str] = {}
    for t in things:
        sig = json.dumps({k: v for k, v in t.items() if k != "id"}, sort_keys=True)
        if sig not in first:
            first[sig], members[sig] = t, []
            order.append(sig)
        members[sig].append(t["id"])
        primary[t["id"]] = first[sig]["id"]
    out = []
    for sig in order:
        t = first[sig]
        out.append({"id": t["id"], "ids": members[sig], **{k: v for k, v in t.items() if k != "id"}} if len(members[sig]) > 1 else t)
    return out, primary


def thing_index(view: dict) -> dict:
    """Every id a sentence may cite for a thing (the thing's own id and every merged id) -> the thing."""
    return {i: t for t in view["things"] for i in t.get("ids", [t["id"]])}


def _dedupe(ids: list[str], primary: dict) -> list[str]:
    return list(dict.fromkeys(primary.get(i, i) for i in ids))


def build_view(record: dict, handoffs: list[dict], diary: list[dict], memory: list[dict], pb: Phrasebook, tz, bands: dict, pi_items: list[dict] | None = None,
               summaries: dict | None = None) -> dict:
    """`handoffs`: the case's hand-off records in order; `diary` / `memory`: the as-of context rows (`merge_diary(...)` / `Context.state_memory`)."""
    local_date = record["local_date"]
    things, listed = [], set()
    for f in record["factors"]:
        cls = f["wording_class"]
        if cls in ("not_mentioned", "not_known_yet"):
            continue
        if f["kind"] == "event" and pb.is_static(f["candidate"]):
            continue
        item = {"id": f["factor_id"], "wording": VIEW_WORDING[cls]}
        if f["kind"] == "relationship":
            exposure, tag, outcome, kind = parse_key(f["relationship_key"])
            item["name"] = pb.exposure(exposure, tag)
            if cls in CLAIM:
                item["outcome"] = pb.outcome(outcome, kind)
            elif cls == "contrary_note":
                item["statement"] = pb.contrary(outcome, kind)
        else:
            item["name"] = pb.event_phrase(f["candidate"])
        if f.get("position"):
            item["position"] = f["position"]
        if f.get("group"):
            item["set"] = f["group"]
        things.append(item)
        listed.add(f["factor_id"])
    things, primary = merge_things(things)
    sets = [{"id": g["group_id"], "reason": VIEW_REASON[g["reason"]], "members": _dedupe(g["members"], primary)} for g in record["groups"] if all(m in listed for m in g["members"])]
    sets = [g for g in sets if len(g["members"]) > 1]
    situation = {"mode": MODE_WORDS[record["mode"]],
                 "measures": [{"id": m["measure_id"], "what": pb.measure_clause(m["measure"], m["direction"], m["strength"]), "part_of_day": part_of_day(to_local(m["opened_at"], tz), bands)}
                              for m in record["measures"]]}
    meal = meal_context(handoffs, pb)
    if meal:
        situation["meal_context"] = meal
    view = {"situation": situation, "things": things, "sets": sets, "history": {"id": "h1", "note": HISTORY_WORDS[record["history_note"]]}}
    view["not_known_yet"] = {"id": "n1", "items": record["not_known_yet"]} if record["not_known_yet"] else None
    if view["not_known_yet"] is None:
        del view["not_known_yet"]
    view["diary"] = [_diary_item(e, tz, local_date, bands) for e in diary]
    for d in view["diary"]:
        if d.get("backs"):
            d["backs"] = _dedupe(d["backs"], primary)
    view["earlier_summaries"] = [{"id": e["view_id"], "window": WINDOW_WORDS.get(e["use"], e["use"]), "headline": e["gist_headline"]} for e in select_summaries(memory, record, summaries)]
    view["earlier_conclusions"] = [{**p, "about": _dedupe(p["about"], primary)} for p in (pi_items or [])]
    return view


def select_summaries(memory: list[dict], record: dict, rules: dict | None) -> list[dict]:
    """Which earlier summaries the text layer sees: only the windows in `rules["use"]` (V0: yesterday's day window), only a notable one when `notable_only`, and none at all in a
    version that has an artifact point. The other windows stay available in the code layer (and in the stored `refs`)."""
    rules = rules or DEFAULT_SUMMARIES
    if any(f["wording_class"] == "artifact_note" for f in record["factors"]):
        return []
    return [e for e in memory if e["use"] in rules["use"] and (not rules.get("notable_only") or e.get("is_notable"))]


def _diary_item(e: dict, tz, local_date: str, bands: dict) -> dict:
    days_back = (datetime.fromisoformat(local_date).date() - to_local(e["timestamp"], tz).date()).days
    item = {"id": e["view_id"], "category": e["category"], "when": "that day" if days_back <= 0 else "the day before" if days_back == 1 else "in the days before",
            "part_of_day": part_of_day(to_local(e["timestamp"], tz), bands), "text": e["description"], "severity_or_note": e["severity_or_note"]}
    if e.get("backs"):
        item["backs"] = e["backs"]
    return item


# ---- the diary entries that back a point ---------------------------------------------------------------------------------------------------------------------
def backing_entries(record: dict, lib, entries: list[dict], source_token: str, tz, per_point: int) -> list[dict]:
    """For every exposed point whose exposure the Evidence library defines on diary entries of one category, the most recent such entries (at most `per_point`) inside the
    exposure's own window and at or before `as_of`. Each entry is returned once with `backs` = the factor ids it backs. `entries`: all diary rows (`at` = aware datetime)."""
    as_of = datetime.fromisoformat(record["as_of"])
    found: dict = {}
    for f in record["factors"]:
        if f["kind"] != "relationship" or f["exposure"] != "exposed" or f["wording_class"] in ("not_mentioned", "not_known_yet"):
            continue
        exposure, tag, outcome, kind = parse_key(f["relationship_key"])
        value = lib.exposures[exposure]["value"]
        match = value.get("match") or {}
        if value.get("source") != source_token or match.get("field") != "category" or "equals" not in match or tag == "prev_night":
            continue
        out = lib.outcomes[outcome]
        unit_date = datetime.fromisoformat(f["relationship_evidence_ids"][-1].split("|")[2]).date()
        pair_key = f["relationship_key"].rsplit(":", 1)[0] + (":{meal_kind}" if kind else "")
        pair = next((p for p in lib.pairs if p.get("key") == pair_key), {})
        w = window_for(tag, out["unit"], as_of, unit_date, int(out.get("exposure_shift_days", 0)), tag in lib.shifted_tags, pair.get("ordering") == "excludes_outcome_day", lib.evening)
        lo, hi = (w.lo, min(w.hi, as_of) if w.hi else as_of)
        mine = [e for e in entries if e["category"] == match["equals"] and (lo is None or e["at"] >= lo) and e["at"] <= hi]
        for e in sorted(mine, key=lambda e: (e["at"], str(e["context_id"])), reverse=True)[:per_point]:
            found.setdefault(e["context_id"], {**e, "backs": []})["backs"].append(f["factor_id"])
    return sorted(found.values(), key=lambda e: (e["at"], str(e["context_id"])), reverse=True)


def merge_diary(window: list[dict], backing: list[dict]) -> list[dict]:
    """Entries that back a point first (they do not count against the window's size), then the rest of the window. An entry already in the window keeps its id; the others
    continue the numbering."""
    by_ctx = {e["context_id"]: e for e in window}
    n = len(window)
    out = []
    for b in backing:
        base = by_ctx.get(b["context_id"])
        if base is None:
            n += 1
            base = {**b, "view_id": f"d{n}"}
        out.append({**base, "backs": b["backs"]})
    backed = {b["context_id"] for b in backing}
    return out + [e for e in window if e["context_id"] not in backed]


AS_WRITTEN = ("text", "severity_or_note", "headline")        # diary text, notes and earlier-summary headlines are passed on as written


def banned_words_in_view(view: dict, banned: set[str]) -> list:
    """Banned words (a set of lower-case words; plurals are added) among every key and every value of the view, except the text passed on as written. [] = clean."""
    words = {w.lower() for w in banned}
    words |= {w + "s" for w in words}
    hits = []

    def tokens(t: str) -> set:
        return set(re.findall(r"[a-z]+", t.lower())) | ({"hand-off"} if "hand-off" in t.lower() else set())

    def walk(node, path):
        if isinstance(node, dict):
            for k, x in node.items():
                bad = tokens(str(k)) & words
                if bad:
                    hits.append((path + [k], sorted(bad)))
                walk(x, path + [k])
        elif isinstance(node, list):
            for x in node:
                walk(x, path)
        elif isinstance(node, str) and path and path[-1] not in AS_WRITTEN:
            bad = tokens(node) & words
            if bad:
                hits.append((path, sorted(bad)))
    walk(view, [])
    return hits


def canonical(view: dict) -> str:
    return json.dumps(view, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def view_hash(view: dict) -> str:
    return hashlib.sha256(canonical(view).encode()).hexdigest()


def view_ids(view: dict) -> set[str]:
    """Every id a sentence may cite."""
    ids = {m["id"] for m in view["situation"]["measures"]} | set(thing_index(view)) | {g["id"] for g in view["sets"]} | {d["id"] for d in view["diary"]}
    ids |= {s["id"] for s in view["earlier_summaries"]} | {p["id"] for p in view["earlier_conclusions"]} | {view["history"]["id"]}
    if "not_known_yet" in view:
        ids.add(view["not_known_yet"]["id"])
    return ids
