"""The gist view (spec section 7.2): what the model is allowed to see of a stored window. Built by code from the stored facts with every
number, count, date and field name removed; frequencies become words, measures take their configured gist name.

Only moved measures appear (a steady measure is not mentioned: rule 7 of the prompt; a measure with `not_enough_data` is left out so the model
has nothing to describe). Diary text and severity notes are passed through as written (they may contain digits; the output check forbids the
model from repeating them). Nothing here calls a model.
"""

from v0_code.baseline_v2.anchors import ANCHOR_STREAM
from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.render import STATUS_WORDS, diary_severity_rank

SIZE_RANK = {"large": 0, "moderate": 1, "small": 2}


def freq_word(k: int, n: int, unit: str = "days") -> str:
    """A frequency as words: k of n -> 'on one day', 'on a few days', 'on most days' (more than half), 'every day'. Units: days or readings."""
    one = unit[:-1] if unit.endswith("s") else unit
    if n == 1:
        return "on this day" if one == "day" else f"on the one {one}"
    if k >= n:
        return f"every {one}"
    if k == 1:
        return f"on one {one}"
    return f"on most {unit}" if k / n > 0.5 else f"on a few {unit}"


def wording_tags(cfg_or_row, row: dict | None = None) -> list[dict]:
    """The tags as the gist is WORDED and CHECKED: a measure that crossed an anchor is called at least `gist.anchor_size_floor` (moderate) so it is
    never described as only "a little" or "slightly". The stored tags are not changed; this returns copies. Call as wording_tags(row) or
    wording_tags(cfg, row)."""
    if row is None:
        cfg, row = None, cfg_or_row
    else:
        cfg = cfg_or_row
    floor = cfg.anchor_size_floor if cfg is not None else "moderate"
    crossed = {ANCHOR_STREAM[a] for a in row["anchors_crossed"] if a in ANCHOR_STREAM}
    out = []
    for t in row["tags"]:
        if t["measure"] in crossed and t["direction"] in ("up", "down") and SIZE_RANK.get(t["size"], 3) > SIZE_RANK[floor]:
            t = {**t, "size": floor}
        out.append(t)
    return out


def usual_places(cfg: Config, day_locations: list[tuple[str, str]], before_date: str) -> set[str]:
    """Her `gist.usual_place_count` most frequent places over the days strictly BEFORE the window (as-of; ties by name). No history: none."""
    from collections import Counter
    c = Counter(loc for d, loc in day_locations if d < before_date and loc)
    return {loc for loc, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:cfg.usual_place_count]}


def _status(s: str | None) -> str:
    return STATUS_WORDS.get(s, (s or "").replace("_", " "))


def _count_word(n: int) -> str:
    return "one" if n == 1 else "a few"


def diary_texts(row: dict) -> list[str]:
    return [i["text"] for i in row["material_changes"] if i["kind"] == "diary_event" and i.get("text")]


ANCHOR_WORDS = {"severe_range_appeared_or_cleared": "time at severe high or low glucose appeared or disappeared",
                "adherence_meds_changed": "medicines went from taken to missed"}


def _top_items(cfg: Config, row: dict, view: dict, tags: list[dict]) -> list[str]:
    """Up to three material items in words, in this priority order: the diary theme (moderate or worse), missed doses, anchors crossed and large
    changes TOGETHER (ordered by size, large first), status deviations. One item per kind, so the first item is the most important kind present."""
    mats, by_measure = row["material_changes"], {t["measure"]: t for t in tags}
    name = cfg.measure_name
    items: list[str] = []

    cutoff = diary_severity_rank(cfg, cfg.month_min_severity)
    theme = [(diary_severity_rank(cfg, i.get("severity_note")), k, i) for k, i in enumerate(mats) if i["kind"] == "diary_event" and diary_severity_rank(cfg, i.get("severity_note")) <= cutoff]
    if theme:
        _, _, e = min(theme, key=lambda x: (x[0], x[1]))
        items.append(f"diary entry ({e['severity_note']}): {e['text']}")

    if view.get("missed_medicines"):
        items.append("missed medicines: " + "; ".join(f"{m['medicine']} {m['how_often']}" for m in view["missed_medicines"]))

    members: list[tuple[int, str, str | None]] = []              # (size rank, text, measure)
    for i in mats:
        if i["kind"] != "anchor_crossed":
            continue
        a = i["anchor"]
        if a == "lab_cgm_discordance":
            members.append((-1, f"{cfg.unchecked_name('lab_test')} and the glucose-based estimate differ", None))
        elif a in ANCHOR_WORDS and a != "adherence_meds_changed":
            members.append((-1, ANCHOR_WORDS[a], None))
        else:
            stream = ANCHOR_STREAM.get(a)
            t = by_measure.get(stream) if stream else None
            if t and t["direction"] in ("up", "down"):
                members.append((SIZE_RANK.get(t["size"], 3), f"{name(stream)} {t.get('direction_word', t['direction'])} ({t['size']})", stream))
            else:
                members.append((3, name(stream) if stream else a.replace("_", " "), stream))
    for i in mats:
        if i["kind"] == "large_change":
            members.append((SIZE_RANK["large"], f"{name(i['measure'])} {i.get('direction_word', i['direction'])} (large)", i["measure"]))
    seen, ordered = set(), []
    for rank, text, measure in sorted(members, key=lambda m: m[0]):                  # stable: anchors before large changes among equals
        key = measure or text
        if key not in seen:
            seen.add(key)
            ordered.append(text)
    if ordered:
        items.append("notable or large changes: " + "; ".join(ordered))

    if view.get("unusual_statuses"):
        items.append("unusual statuses: " + "; ".join(f"{u['measure']} {u['status']} {u['how_often']}" for u in view["unusual_statuses"]))
    return items[:3]


def build_gist_view(cfg: Config, row: dict, usual_places: set[str] | None = None) -> dict:
    """row: a stored window as MemoryV2Store.get_memory(..., full=True) returns it. usual_places: her most frequent places before the window (not named
    in the view); None names every place. Sizes are the WORDING sizes (see wording_tags)."""
    mats = row["material_changes"]
    tags = wording_tags(cfg, row)
    name = lambda stream: cfg.measure_name(stream)
    view: dict = {"tier": row["tier"]}
    if not row["reliable"]:
        view["reliable"] = "no"                                                           # reliability is mentioned only when the answer is no

    moved = sorted((t for t in tags if t["direction"] in ("up", "down")), key=lambda t: SIZE_RANK.get(t["size"], 3))
    view["measures"] = [{"measure": name(t["measure"]), "direction": t.get("direction_word", t["direction"]), "size": t["size"]} for t in moved]

    cm = row["co_movement"]
    by_label = {t["label"]: t["measure"] for t in tags}
    if cm.get("glucose_direction") in ("up", "down"):
        view["moved_the_same_way_as_glucose"] = [name(by_label[e["measure"]]) for e in cm["same_direction"] if e["measure"] in by_label]
        view["moved_the_opposite_way_to_glucose"] = [name(by_label[e["measure"]]) for e in cm["opposite_direction"] if e["measure"] in by_label]

    missed = [{"medicine": cfg.medicine_name(i["medicine"]), "how_often": freq_word(i.get("days", 1), i.get("of", 1), "days")} for i in mats if i["kind"] == "missed_dose"]
    if missed:
        view["missed_medicines"] = missed

    unusual = []
    for i in mats:
        if i["kind"] == "status_worse_than_usual":
            unusual.append({"measure": name(i["measure"]), "status": _status(i["status"]), "usually": _status(i["usual"]),
                            "how_often": freq_word(i.get("days", 1), i.get("of", 1), i.get("unit", "days"))})
    if unusual:
        view["unusual_statuses"] = unusual

    diary = [{"category": (i.get("category") or "event").replace("_", " "), "text": i["text"], **({"severity": i["severity_note"]} if i.get("severity_note") else {})}
             for i in mats if i["kind"] == "diary_event"]
    if diary:
        view["diary"] = diary
    summary = next((i for i in mats if i["kind"] == "diary_summary"), None)
    if summary:
        view["other_diary_entries"] = "less serious entries exist in these categories: " + ", ".join(sorted(c.replace("_", " ") for c in summary["by_category"]))

    f = row["facts"]
    places = []
    if row["tier"] == "day":
        loc = (f.get("lifestyle") or {}).get("location")
        places = [(loc, 1, 1)] if loc else []
    elif row["tier"] == "week":
        places = [(k, v, f["n_days"]) for k, v in sorted(f["aggregates"]["location_days"].items())]
    shown = [{"place": k.replace("_", " "), "how_often": freq_word(v, n, "days")} for k, v, n in places if k not in (usual_places or ())]
    if shown:
        view["places"] = shown

    if row["tier"] == "month":
        long_standing = [{"measure": name(c["measure"]), "status": _status(c["usual_status"]), "how_often": "on most days"}
                         for c in f.get("chronic_findings", []) if c["share_pct"] > 50 and c["usual_status"] != "normal"]
        if long_standing:
            view["long_standing_patterns"] = long_standing
            covered = {p["measure"] for p in long_standing}                       # a long-standing pattern already says it: drop the duplicate unusual-status item
            kept = [u for u in view.get("unusual_statuses", []) if u["measure"] not in covered]
            if kept:
                view["unusual_statuses"] = kept
            else:
                view.pop("unusual_statuses", None)
        if "lab_cgm_discordance" in row["anchors_crossed"]:
            gap = (f.get("deltas", {}).get("clean") or {}).get("lab_gap") or 0
            view["lab_vs_glucose_estimate"] = f"{cfg.unchecked_name('lab_test')} is {'higher' if gap > 0 else 'lower'} than {cfg.unchecked_name('glucose_estimate')} (they differ)"

    notes = []
    removed = sum(1 for i in mats if i["kind"] == "questionable_reading_removed")
    if removed:
        notes.append(f"{_count_word(removed)} questionable glucose reading{'' if removed == 1 else 's'} {'was' if removed == 1 else 'were'} removed")
    if any(i["kind"] == "data_gap" for i in mats):
        notes.append("glucose readings had a gap")
    notes += [f"{i['label']} data was incomplete" for i in mats if i["kind"] == "low_completeness"]
    if "severe_range_appeared_or_cleared" in row["anchors_crossed"]:
        notes.append("time at severe high or low glucose appeared or disappeared")
    if row["anchors_questionable"]:
        notes.append("an apparent large change was ignored because it came only from a removed reading")
    if notes:
        view["data_notes"] = notes
    top = _top_items(cfg, row, view, tags)
    return {"top_items": top, **view} if top else view
