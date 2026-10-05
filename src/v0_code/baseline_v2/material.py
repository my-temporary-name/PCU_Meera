"""Material changes (spec section 4.2): a typed list built by code, in this order. `quiet` is exactly "the list is empty".

 1 anchor_crossed (cleaned values only)   2 missed_dose   3 diary_event (+ diary_summary: the month tier counts the entries it does not list)
 4 status_worse_than_usual   5 large_change   6 data_gap / low_completeness   7 questionable_reading_removed

Missed doses and diary events are always material. A status counts only when it is WORSE than that stream's usual status (so steps "low" on
95% of days is not news, and a stream with no usual yet — fewer than min_days of history — contributes nothing here).
"""

from v0_code.baseline_v2.anchors import ANCHOR_STREAM
from v0_code.baseline_v2.profile import STATUS_RANK

MATERIAL_KINDS = ("anchor_crossed", "missed_dose", "diary_event", "diary_summary", "status_worse_than_usual", "large_change", "data_gap", "low_completeness", "questionable_reading_removed")


def build_material(*, anchors_crossed: list[str], per_medication: dict[str, str], diary_events: list[dict], statuses: dict[str, str | None],
                   usual: dict[str, str | None], tags: list[dict], gap_hours: float | None, low_completeness: list[dict], removed: list[dict], date: str,
                   min_status_rank: int = 2, missed_counts: dict[str, tuple[int, int]] | None = None, status_items: list[dict] | None = None,
                   gap_days: int | None = None, diary_summary: dict | None = None) -> list[dict]:
    """Day windows pass per_medication / statuses / usual. Week and month windows pass already-aggregated inputs instead: missed_counts
    (medicine -> (days missed, days with data)) and status_items (the days' own status items, grouped), so the same rules give the same kinds."""
    out: list[dict] = [{"kind": "anchor_crossed", "anchor": a} for a in anchors_crossed]
    if missed_counts is None:
        out += [{"kind": "missed_dose", "medicine": med, "days": 1} for med, status in sorted(per_medication.items()) if status != "taken"]
    else:
        out += [{"kind": "missed_dose", "medicine": med, "days": n, "of": of} for med, (n, of) in sorted(missed_counts.items()) if n > 0]
    out += [{"kind": "diary_event", "date": date, **e} for e in diary_events]        # an event that carries its own date keeps it
    if diary_summary:
        out.append({"kind": "diary_summary", **diary_summary})
    out += list(status_items or [])
    for stream, st in sorted(statuses.items()):
        u = usual.get(stream)
        # min_status_rank (config min_material_status): abnormal = 2 (low/high only), borderline = 1. Lower statuses are shown in the numbers, not here.
        if st is not None and u is not None and STATUS_RANK.get(st, 0) >= min_status_rank and STATUS_RANK.get(st, 0) > STATUS_RANK.get(u, 0):
            out.append({"kind": "status_worse_than_usual", "measure": stream, "status": st, "usual": u})
    # A measure that another item already reports (a crossed anchor, a missed dose, a status deviation) does not get a second "large move" line.
    represented = {ANCHOR_STREAM[a] for a in anchors_crossed if a in ANCHOR_STREAM} | {i["measure"] for i in out if i["kind"] == "status_worse_than_usual"}
    if any(s != "taken" for s in per_medication.values()) or any(n > 0 for n, _ in (missed_counts or {}).values()):
        represented |= {t["measure"] for t in tags if t["domain"] == "adherence"}
    out += [{"kind": "large_change", "measure": t["measure"], "label": t["label"], "direction": t["direction"], "direction_word": t.get("direction_word", t["direction"]),
             "size": t["size"]} for t in tags if t["size"] == "large" and t["measure"] not in represented]
    if gap_hours is not None:
        out.append({"kind": "data_gap", "hours": gap_hours, **({"days": gap_days} if gap_days else {})})
    out += [{"kind": "low_completeness", **lc} for lc in low_completeness]
    out += [{"kind": "questionable_reading_removed", **r} for r in removed]
    return out
