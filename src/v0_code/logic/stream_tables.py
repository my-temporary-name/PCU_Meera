"""Registry-driven, code-computed tables over day records — no per-stream branches here.

Everything the LLM must not infer is computed in this module: week aggregates (one aggregator
per `agg` kind, looked up from the registry), per-stream direction vs the prior window, delta vs
cumulative history, and the confidence label.

Conventions (task/baseline.md + review decisions):
- Direction flat-band = 0.5 x population SD of that stream's *daily values before this window*
  (config override in FLAT_BAND_OVERRIDES, keyed by the stream's label). Too little history or
  too few days in either window -> "insufficient_data", never a guess.
- Delta vs cumulative = window value - mean of daily values *before the window start* (the window
  itself is excluded). None while the window is unreliable or there is no history.
- Mood is reduced to a number: the count of time blocks in a strain category (patient_config.STRAIN_CATEGORIES:
  mild stress, tired, anxious, overwhelmed). Calm and uplifted blocks do not count.
"""

import statistics
from collections import Counter
from typing import Any, Callable

from v0_code.logic.patient_config import STRAIN_CATEGORIES
from v0_code.logic.registry import REGISTRY, Stream, numeric_streams

MIN_BAND_HISTORY_DAYS = 14  # daily values needed before the window to trust an SD-based band
MIN_DAYS_IN_WINDOW = 4  # of 7 days needed for a week-level value to count
FLAT_BAND_OVERRIDES: dict[str, float] = {}  # label -> absolute flat band; empty = use 0.5 x SD


def _get(rec: dict, path: tuple[str, ...]) -> Any:
    cur: Any = rec
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def clean_peak(post_meal_entry: dict) -> float:
    """A meal's post-meal peak without questionable readings (the raw peak when none were excluded)."""
    q = post_meal_entry.get("questionable_excluded")
    return q["metrics_without_them"]["peak_glucose"] if q else post_meal_entry["peak_glucose"]


def day_value(s: Stream, rec: dict) -> float | None:
    """The stream's single numeric value for one day, from the day record."""
    if s.agg == "adherence":
        return rec["adherence"]["overall_pct"]
    if s.agg == "mood":
        blocks = rec.get("mood") or {}
        return float(sum(1 for b in blocks.values() if b["category"] in STRAIN_CATEGORIES)) if blocks else None
    if s.agg == "meals":
        peaks = [clean_peak(m) for m in rec.get("post_meal", [])]  # cleaned: a sensor spike is not a meal peak
        return round(statistics.fmean(peaks), 2) if peaks else None
    v = _get(rec, s.path) if s.path else None
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def daily_values(rec: dict) -> dict[str, float | None]:
    return {s.label: day_value(s, rec) for s in numeric_streams()}


# ---- directions & cumulative deltas ----------------------------------------------------------------------


def direction_detail(curr: float | None, prior: float | None, history: list[float], label: str) -> tuple[str, float | None, float | None]:
    """(direction, change, flat band). change = curr - prior; band is None when no band could be formed."""
    if curr is None or prior is None:
        return "insufficient_data", None, None
    if label in FLAT_BAND_OVERRIDES:
        band = FLAT_BAND_OVERRIDES[label]
    elif len(history) >= MIN_BAND_HISTORY_DAYS:
        band = 0.5 * statistics.pstdev(history)
    else:
        return "insufficient_data", None, None
    delta = curr - prior
    return ("flat" if abs(delta) <= band else ("up" if delta > 0 else "down")), round(delta, 2), band


def direction(curr: float | None, prior: float | None, history: list[float], label: str) -> str:
    return direction_detail(curr, prior, history, label)[0]


def stream_tables(curr: dict[str, float | None], prior: dict[str, float | None], hist: dict[str, list[float]]) -> tuple[dict, dict, dict]:
    """Per numeric stream label: (directions, changes vs the prior window, strengths). strength is
    |change| / flat band — how far past 'flat' the stream moved — and ranks co-movers."""
    dirs, changes, strengths = {}, {}, {}
    for lab in curr:
        d, ch, band = direction_detail(curr[lab], prior.get(lab), hist.get(lab, []), lab)
        dirs[lab], changes[lab] = d, ch
        strengths[lab] = round(abs(ch) / band, 2) if ch is not None and band else None
    return dirs, changes, strengths


def cumulative_delta(curr: float | None, history: list[float], reliable: bool) -> float | None:
    if not reliable or curr is None or not history:
        return None
    return round(curr - statistics.fmean(history), 2)


def window_mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return round(statistics.fmean(present), 2) if len(present) >= MIN_DAYS_IN_WINDOW else None


# Domains whose several streams are the same measurement seen three ways: co-movement reports them
# once, under the domain's first registry label ("heart rate"), instead of listing "heart rate",
# "resting heart rate" and "daily resting heart rate" as three separate findings. Add a domain here
# to merge it; "lifestyle" is deliberately absent (hydration, screen time and sedentary time are
# genuinely different things).
MERGE_DOMAINS = {"heart_rate"}


def _merged(dirs: dict[str, str], changes: dict, strengths: dict) -> dict[str, dict]:
    """label -> {direction, change, strength}, one entry per merged domain (registry order). A merged
    domain takes the first of its streams that has a direction, and that stream's change/strength."""
    out: dict[str, dict] = {}
    seen: dict[str, str] = {}  # domain -> representative label already emitted
    known = {s.label for s in numeric_streams()}
    for s in numeric_streams():
        if s.label not in dirs:
            continue
        item = {"direction": dirs[s.label], "change": changes.get(s.label), "strength": strengths.get(s.label)}
        if s.domain not in MERGE_DOMAINS:
            out[s.label] = item
            continue
        rep = seen.setdefault(s.domain, s.label)
        if rep not in out or (out[rep]["direction"] == "insufficient_data" and item["direction"] != "insufficient_data"):
            out[rep] = item
    for k, v in dirs.items():  # anything not in the registry passes through untouched
        if k not in known:
            out.setdefault(k, {"direction": v, "change": changes.get(k), "strength": strengths.get(k)})
    return out


UNIT_BY_LABEL = {s.label: s.unit for s in numeric_streams()}


def candidates_from_directions(dirs: dict[str, str], changes: dict | None = None, strengths: dict | None = None) -> dict:
    """Which streams moved the same / opposite way as glucose. dirs must contain 'glucose'.

    `ranked` lists every same/opposite co-mover with its direction, unsigned amount of change and
    unit, strongest first (|change| / flat band). The LLM layer takes the top K from it, so the full
    record keeps every candidate while an entry only has to cover the strongest few."""
    changes, strengths = changes or {}, strengths or {}
    g = dirs.get("glucose")
    out = {"glucose_direction": g, "glucose_change": changes.get("glucose"), "same_direction": [], "opposite_direction": [],
           "flat": [], "moved_while_glucose_flat": [], "unavailable": [], "ranked": []}
    for k, item in _merged(dirs, changes, strengths).items():
        if k == "glucose":
            continue
        v = item["direction"]
        if v == "insufficient_data":
            out["unavailable"].append(k)
        elif v == "flat":
            out["flat"].append(k)
        elif g in ("up", "down"):
            relation = "same" if v == g else "opposite"
            out["same_direction" if relation == "same" else "opposite_direction"].append(k)
            out["ranked"].append({"name": k, "direction": v, "amount": abs(item["change"]) if item["change"] is not None else None,
                                  "unit": UNIT_BY_LABEL.get(k, ""), "relation": relation, "strength": item["strength"]})
        else:
            out["moved_while_glucose_flat"].append(k)
    out["ranked"].sort(key=lambda r: (r["strength"] is None, -(r["strength"] or 0), r["name"]))
    return out


# ---- week aggregators (one per `agg` kind; looked up from the registry) --------------------------------------

Ctx = dict  # {"best_date": str, "worst_date": str}
Days = list[tuple[str, dict]]  # [(date, day_record)]


def _present(days: Days, s: Stream) -> list[Any]:
    return [v for _, r in days if (v := _get(r, s.path)) is not None]


def agg_mean(days: Days, s: Stream, ctx: Ctx) -> dict:
    vals = _present(days, s)
    return {"mean": round(statistics.fmean(vals), 2) if vals else None, "n_days": len(vals)}


def agg_sum_mean(days: Days, s: Stream, ctx: Ctx) -> dict:
    vals = _present(days, s)
    return {"sum": round(sum(vals), 2) if vals else None, "mean_per_day": round(statistics.fmean(vals), 2) if vals else None, "n_days": len(vals)}


def agg_counts(days: Days, s: Stream, ctx: Ctx) -> dict:
    return {"counts": dict(Counter(_present(days, s))), "n_days": len(_present(days, s))}


def agg_list(days: Days, s: Stream, ctx: Ctx) -> dict:
    items = [{"date": d, **x} for d, r in days for x in (_get(r, s.path) or [])]
    return {"readings": items, "n_readings": len(items)}


def agg_adherence(days: Days, s: Stream, ctx: Ctx) -> dict:
    per: dict[str, dict[str, int]] = {}
    for _, r in days:
        for med, status in r["adherence"]["per_medication"].items():
            slot = per.setdefault(med, {"taken": 0, "expected": 0})
            slot["expected"] += 1
            slot["taken"] += status == "taken"
    taken, expected = sum(v["taken"] for v in per.values()), sum(v["expected"] for v in per.values())
    return {"overall_pct": round(100 * taken / expected, 1) if expected else None, "per_medication": per}


def agg_mood(days: Days, s: Stream, ctx: Ctx) -> dict:
    out: dict[str, dict[str, dict[str, int]]] = {}
    for _, r in days:
        for block, m in (r.get("mood") or {}).items():
            counts = out.setdefault(block, {"counts": {}})["counts"]
            counts[m["category"]] = counts.get(m["category"], 0) + 1
    return out


def agg_meals(days: Days, s: Stream, ctx: Ctx) -> dict:
    counts = Counter(m["label"] for _, r in days for m in r.get("meals", []))
    meals = [m for _, r in days for m in r.get("post_meal", [])]
    raw = [m["peak_glucose"] for m in meals]
    clean = [clean_peak(m) for m in meals]
    by_date = dict(days)

    def foods(date: str) -> list[dict]:
        return [{"label": m["label"], "food": m["food_description"]} for m in by_date.get(date, {}).get("meals", [])]

    out = {
        "meals_by_label": dict(counts),
        "post_meal_peak_mean": round(statistics.fmean(raw), 2) if raw else None,
        "post_meal_peak_max": max(raw) if raw else None,
        "foods_best_day": foods(ctx.get("best_date", "")),
        "foods_worst_day": foods(ctx.get("worst_date", "")),
    }
    if raw != clean:  # same shape as the glucose sections: raw stays, the version without questionable readings sits beside it
        excluded = sorted(v for m in meals for v in m.get("questionable_excluded", {}).get("excluded_values", []))
        out["questionable_excluded"] = {
            "n_excluded": len(excluded), "excluded_values": excluded,
            "metrics_without_them": {"post_meal_peak_mean": round(statistics.fmean(clean), 2), "post_meal_peak_max": max(clean)},
            "metrics_with_them": {"post_meal_peak_mean": out["post_meal_peak_mean"], "post_meal_peak_max": out["post_meal_peak_max"]},
        }
    return out


def agg_crossings(days: Days, s: Stream, ctx: Ctx) -> dict:
    c = Counter((x["biomarker"], x["status"]) for _, r in days for x in r.get("other_threshold_crossings", []))
    # A list of {measure, status, days} (not "biomarker:status" string keys) so the plain-English view can
    # translate the measure and the status; a raw key like "sleep_duration:borderline_low" got echoed into prose.
    return {"counts": [{"measure": b, "status": st_, "days": n} for (b, st_), n in sorted(c.items())]}


AGGREGATORS: dict[str, Callable[[Days, Stream, Ctx], dict]] = {
    "mean": agg_mean, "sum_mean": agg_sum_mean, "counts": agg_counts, "list": agg_list,
    "adherence": agg_adherence, "mood": agg_mood, "meals": agg_meals, "crossings": agg_crossings,
}  # "glucose" has no aggregator: the week glucose section already carries the window metrics


def week_aggregates(days: Days, ctx: Ctx) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for s in REGISTRY:
        fn = AGGREGATORS.get(s.agg or "")
        if fn is None:
            continue
        out[s.name] = fn(days, s, ctx)
        if s.expected_per_day:  # completeness: mean of the days' completeness for this stream
            vals = [r["completeness_by_stream"][s.name] for _, r in days if s.name in r.get("completeness_by_stream", {})]
            out[s.name]["completeness_pct"] = round(statistics.fmean(vals), 1) if vals else None
    return out


# ---- confidence (code, not the model's opinion) ---------------------------------------------------------------


def confidence(reliable: bool, glucose_completeness_pct: float | None) -> str:
    """high = reliable and glucose completeness >= 90; moderate = reliable and >= 70; low otherwise."""
    c = glucose_completeness_pct or 0.0
    if reliable and c >= 90:
        return "high"
    if reliable and c >= 70:
        return "moderate"
    return "low"
