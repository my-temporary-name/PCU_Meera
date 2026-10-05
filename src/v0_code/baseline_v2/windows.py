"""Week and month tiers (spec section 4), built from the day windows and the cleaned glucose series. Code only; the same rules as the day tier.

Week  = the rolling trailing `week_days` days, one for EVERY day from the 7th on, compared with the 7 days before it.
Month = cumulative from day 1 plus the last `month_every_days` days, a checkpoint every 30 days (and a final partial one for the latest
        data), compared with the previous checkpoint's last-30-day window.

A window's value for a stream is the mean of its daily values (needs `min_days_in_window` days with data); glucose is pooled over the
window's CLEANED readings, adherence over taken / expected doses. Flat bands come from the stream's daily values strictly before the window
starts. Nothing reads a date after the window's end.
"""

import calendar
import statistics
from collections import Counter, defaultdict
from datetime import date as _date, datetime, timedelta

from v0_code.baseline_v2 import anchors as anchors_mod
from v0_code.baseline_v2.config import MATERIAL_STATUS_RANK, Config
from v0_code.baseline_v2.data import Reading, StoreView
from v0_code.baseline_v2.material import build_material
from v0_code.baseline_v2.profile import STATUS_RANK, build_profile
from v0_code.baseline_v2.render import (code_line, diary_severity_rank, early_code_line, fallback_code_line, month_text, notable_reason, week_text)
from v0_code.baseline_v2.tags import co_movement, make_tag
from v0_code.baseline_v2.trust import clean_series, confidence, glucose_metrics, is_reliable, with_questionable


# ---- small pure helpers (unit-tested) ------------------------------------------------------------------------------------------------------

def weekday_name(d: str) -> str:
    return calendar.day_name[_date.fromisoformat(d).weekday()]


def checkpoint_indices(n_days: int, every: int) -> list[int]:
    idx = list(range(every - 1, n_days, every))
    if not idx or idx[-1] != n_days - 1:
        idx.append(n_days - 1)             # always represent the most recent data, even if it is less than `every` days after the last checkpoint
    return idx



def split_month_diary(cfg: Config, events: list[dict]) -> tuple[list[dict], dict | None]:
    """The month tier lists diary entries only at `diary.month_min_severity` or worse, at most `diary.month_max_listed` of them (most severe
    first, then most recent; shown in date order). Everything else is counted by category: (listed, {"count", "by_category"} or None)."""
    cutoff = diary_severity_rank(cfg, cfg.month_min_severity)
    eligible = sorted(((i, e) for i, e in enumerate(events) if diary_severity_rank(cfg, e.get("severity_note")) <= cutoff),
                      key=lambda ie: (diary_severity_rank(cfg, ie[1].get("severity_note")), tuple(-ord(c) for c in ie[1].get("date", "")), ie[0]))
    keep = {i for i, _ in eligible[:cfg.month_max_listed]}
    listed = [e for i, e in enumerate(events) if i in keep]
    rest = [e for i, e in enumerate(events) if i not in keep]
    if not rest:
        return listed, None
    return listed, {"count": len(rest), "by_category": dict(Counter(e.get("category") or "event" for e in rest))}


def reading_status_items(cfg: Config, ss, window: list[dict], earlier: list[dict], min_rank: int) -> list[dict]:
    """A stream judged reading by reading (e.g. blood pressure): a reading takes the worse of its components' statuses, its usual is the most
    common status among EARLIER readings (needs min_days_for_compare of them), and the window reports each status that is at least
    `min_rank` severe and worse than usual, as k of n readings."""
    def status(r: dict) -> str | None:
        sts = [r.get(f"{c}_status") for c in ss.components if r.get(f"{c}_status")]
        return max(sts, key=lambda s: STATUS_RANK.get(s, 0)) if sts else None
    w = [s for s in map(status, window) if s]
    hist = [s for s in map(status, earlier) if s]
    if not w or len(hist) < cfg.min_days_for_compare:
        return []
    c = Counter(hist)
    usual = max(c, key=lambda k: (c[k], k))
    out = []
    for st, k in sorted(Counter(w).items(), key=lambda kv: (-STATUS_RANK.get(kv[0], 0), kv[0])):
        if STATUS_RANK.get(st, 0) >= min_rank and STATUS_RANK.get(st, 0) > STATUS_RANK.get(usual, 0):
            out.append({"kind": "status_worse_than_usual", "measure": ss.name, "status": st, "usual": usual, "days": k, "of": len(w), "unit": "readings"})
    return out


def bp_status_items(cfg: Config, window: list[dict], earlier: list[dict], min_rank: int) -> list[dict]:
    """Blood pressure through the shared reading-level status path (the configured status stream named blood_pressure)."""
    ss = next(s for s in cfg.status_streams if s.name == "blood_pressure")
    return reading_status_items(cfg, ss, window, earlier, min_rank)


def best_and_worst(days: list[dict]) -> tuple[dict | None, dict | None, bool]:
    """Best = highest time in range, ties broken by the LOWEST mean glucose; worst = lowest time in range, ties by the HIGHEST mean (then the
    earlier date, so the pick is deterministic). When every day is identical on both, naming a best and a worst day would invent a difference:
    returns (None, None, True)."""
    ok = [d for d in days if d.get("tir_pct") is not None and d.get("glucose_mean") is not None]
    if len(ok) < 2:
        return None, None, False
    if len({(d["tir_pct"], d["glucose_mean"]) for d in ok}) == 1:
        return None, None, True
    best = min(ok, key=lambda d: (-d["tir_pct"], d["glucose_mean"], d["date"]))
    worst = min(ok, key=lambda d: (d["tir_pct"], -d["glucose_mean"], d["date"]))
    return best, worst, False


def worst_mood(blocks: dict, cfg: Config) -> str | None:
    """The day's most distressed mood category, ranked by the configured distress order (not by list order)."""
    cats = [b["category"] for b in blocks.values() if b.get("category")]
    return max(cats, key=lambda c: (cfg.distress_rank(c), c)) if cats else None


def chronic_findings(history: dict[str, list[str]], cfg: Config) -> list[dict]:
    """Streams non-normal on at least `chronic_min_share_pct` of the days so far (needs min_days_for_compare days of status). Recorded once, in
    the month tier, instead of in every entry."""
    out = []
    for stream, sts in history.items():
        n = len(sts)
        if n < cfg.min_days_for_compare:
            continue
        share = 100 * sum(1 for s in sts if s != "normal") / n
        if share >= cfg.chronic_min_share_pct:
            sc = cfg.stream(stream)
            c = Counter(sts)
            out.append({"measure": stream, "label": sc.display if sc else stream, "share_pct": round(share, 1), "days": n, "usual_status": max(c, key=lambda k: (c[k], k))})
    return sorted(out, key=lambda f: (-f["share_pct"], f["measure"]))


def lab_link(labs: list[tuple[datetime, float, str | None]], kept: list[Reading], cfg: Config, as_of: str) -> list[dict]:
    """Each lab (up to `as_of`) next to the glucose-based estimate (GMI) over the 90 days BEFORE the lab, and the signed gap (lab minus GMI)."""
    out = []
    for dt, value, status in labs:
        if dt.date().isoformat() > as_of:
            continue
        window = [r for r in kept if dt - timedelta(days=90) <= r.dt < dt]
        gmi = glucose_metrics([r.value for r in window], cfg.glucose_expected_per_day * 90)["gmi_pct"] if window else None
        out.append({"lab_date": dt.date().isoformat(), "hba1c_pct": value, "hba1c_status": status, "gmi_90d_prior": gmi,
                    "gap_hba1c_minus_gmi": round(value - gmi, 2) if gmi is not None else None, "cgm_days": len({r.dt.date() for r in window})})
    return out


# ---- window values, profile, deltas ------------------------------------------------------------------------------------------------------------

def _delta(a, b):
    return round(a - b, 4) if a is not None and b is not None else None


def window_values(cfg: Config, days: list[dict], kept_vals: list[float]) -> tuple[dict, dict | None]:
    """One value per configured stream for a whole window, plus the pooled glucose metrics."""
    metrics = glucose_metrics(kept_vals, cfg.glucose_expected_per_day * len(days))
    out: dict[str, float | None] = {}
    for sc in cfg.streams:
        if sc.agg == "glucose_mean":
            out[sc.name] = metrics["mean"] if metrics else None
        elif sc.agg == "glucose_tir_pct":
            out[sc.name] = metrics["tir_pct"] if metrics else None
        elif sc.agg == "glucose_cv_pct":
            out[sc.name] = metrics["cv_pct"] if metrics else None
        elif sc.agg == "adherence_pct":
            meds = [s for d in days for s in d["facts"]["adherence"]["per_medication"].values()]
            out[sc.name] = round(100 * sum(1 for s in meds if s == "taken") / len(meds), 1) if meds else None
        elif sc.agg == "post_meal_peak":
            peaks = [m["peak_glucose"] for d in days for m in d["facts"]["post_meal"]]
            out[sc.name] = round(statistics.fmean(peaks), 2) if peaks else None
        else:
            xs = [d["facts"]["daily_values"].get(sc.name) for d in days]
            xs = [x for x in xs if x is not None]
            out[sc.name] = round(statistics.fmean(xs), 2) if len(xs) >= cfg.min_days_in_window else None
    return out, metrics


def profile_before(cfg: Config, day_rows: list[dict], start_idx: int) -> dict:
    hist = day_rows[:start_idx]
    return {sc.name: build_profile([d["facts"]["daily_values"][sc.name] for d in hist if d["facts"]["daily_values"].get(sc.name) is not None],
                                   [d["facts"]["statuses"][sc.name] for d in hist if d["facts"]["statuses"].get(sc.name)], cfg) for sc in cfg.streams}


def _anchor_deltas(vals: dict, prev: dict, metrics: dict | None, pmetrics: dict | None, lab_gap=None) -> dict:
    sev = lambda m: (m["tar_severe_pct"] + m["tbr_severe_pct"]) if m else None
    return {"tir": _delta(vals.get("time_in_range"), prev.get("time_in_range")), "cv": _delta(vals.get("variability"), prev.get("variability")),
            "gmi": _delta(metrics and metrics["gmi_pct"], pmetrics and pmetrics["gmi_pct"]), "sleep": _delta(vals.get("sleep_duration"), prev.get("sleep_duration")),
            "resting_hr": _delta(vals.get("resting_heart_rate"), prev.get("resting_heart_rate")), "steps": _delta(vals.get("step_count"), prev.get("step_count")),
            "adherence_pct": _delta(vals.get("medication_adherence"), prev.get("medication_adherence")), "meds_changed": None,
            "severe_curr": sev(metrics), "severe_prior": sev(pmetrics), "lab_gap": lab_gap}


# ---- the shared window builder -------------------------------------------------------------------------------------------------------------------

def _aggregate_material_inputs(cfg: Config, days: list[dict], earlier_days: list[dict], tier: str) -> dict:
    n = len(days)
    missed: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for d in days:
        for med, s in d["facts"]["adherence"]["per_medication"].items():
            missed[med][1] += 1
            missed[med][0] += s != "taken"
    status: dict[tuple, int] = Counter()
    for d in days:
        for i in d["material_changes"]:
            if i["kind"] == "status_worse_than_usual":
                status[(i["measure"], i["status"], i["usual"])] += 1
    status_items = [{"kind": "status_worse_than_usual", "measure": m, "status": st, "usual": u, "days": k, "of": n} for (m, st, u), k in sorted(status.items())]
    min_rank = MATERIAL_STATUS_RANK[cfg.min_material_status]
    for ss in cfg.status_streams:
        status_items += reading_status_items(cfg, ss, [r for d in days for r in d["facts"][ss.facts_key]], [r for d in earlier_days for r in d["facts"][ss.facts_key]], min_rank)
    diary = [{**e, "date": d["facts"]["date"]} for d in days for e in d["facts"]["diary_events"]]
    diary_summary = None
    if tier == "month":
        diary, diary_summary = split_month_diary(cfg, diary)
    gaps = [float(f["flag"].split(":")[1]) for d in days for f in d["data_quality"]["flags"] if f["flag"].startswith("gap_hours")]
    comp: dict[str, list[float]] = defaultdict(list)
    for d in days:
        for s, pct in d["facts"]["completeness_by_stream"].items():
            comp[s].append(pct)
    low = []
    for s, xs in comp.items():
        pct = round(statistics.fmean(xs), 1)
        if pct < cfg.reliable_completeness_pct:
            low.append({"stream": s, "label": cfg.stream(s).display if cfg.stream(s) else s, "pct": pct})
    return {
        "missed_counts": {m: (c[0], c[1]) for m, c in missed.items()},
        "status_items": status_items, "diary_events": diary, "diary_summary": diary_summary,
        "gap_hours": round(max(gaps), 1) if gaps else None, "gap_days": len(gaps),
        "low_completeness": sorted(low, key=lambda x: x["stream"]),
        "removed": [r for d in days for r in d["data_quality"]["questionable_readings"]],
    }


def _build_window(cfg: Config, tier: str, day_rows: list[dict], kept_by: dict, removed_by: dict, start: int, end: int, prev: tuple[int, int] | None,
                  labs: list, kept_all: list[Reading], extra_facts: dict) -> dict:
    exp = cfg.glucose_expected_per_day
    days = day_rows[start:end + 1]
    dates = [d["facts"]["date"] for d in days]
    vals_list = [v for ds in dates for v in kept_by.get(ds, [])]
    rem_list = [r for ds in dates for r in removed_by.get(ds, [])]
    values, metrics = window_values(cfg, days, vals_list)
    raw_metrics = glucose_metrics(vals_list + [r.value for r in rem_list], exp * len(days))
    pdays = day_rows[prev[0]:prev[1] + 1] if prev else None
    pvals_list = [v for ds in [d["facts"]["date"] for d in pdays] for v in kept_by.get(ds, [])] if pdays else []
    pvalues, pmetrics = window_values(cfg, pdays, pvals_list) if pdays else ({}, None)
    praw = None
    if pdays:
        prem = [r.value for ds in [d["facts"]["date"] for d in pdays] for r in removed_by.get(ds, [])]
        praw = glucose_metrics(pvals_list + prem, exp * len(pdays))

    profile = profile_before(cfg, day_rows, start)
    tags = [make_tag(sc, values.get(sc.name), pvalues.get(sc.name) if pdays else None, profile[sc.name], cfg) for sc in cfg.streams]
    gname = next(sc.name for sc in cfg.streams if sc.agg == "glucose_mean")
    cm = co_movement(tags, gname)

    end_date = dates[-1]
    lab_gap = extra_facts.pop("_lab_gap", None)
    clean_d = _anchor_deltas(values, pvalues, metrics, pmetrics, lab_gap)
    raw_vals = {**values, "time_in_range": raw_metrics["tir_pct"] if raw_metrics else None, "variability": raw_metrics["cv_pct"] if raw_metrics else None}
    raw_prev = {**pvalues, "time_in_range": praw["tir_pct"] if praw else None, "variability": praw["cv_pct"] if praw else None}
    raw_d = _anchor_deltas(raw_vals, raw_prev, raw_metrics, praw, lab_gap)
    n_meds = day_rows[end]["facts"]["n_medications"]
    crossed, questionable = anchors_mod.split_questionable(cfg, tier, clean_d, raw_d, n_meds)

    agg = _aggregate_material_inputs(cfg, days, day_rows[:start], tier)
    twin = with_questionable(vals_list, [r.value for r in rem_list], exp * len(days))
    material = build_material(
        anchors_crossed=crossed, per_medication={}, diary_events=agg["diary_events"], statuses={}, usual={}, tags=tags, gap_hours=agg["gap_hours"], gap_days=agg["gap_days"],
        low_completeness=agg["low_completeness"], removed=agg["removed"], date=end_date, min_status_rank=MATERIAL_STATUS_RANK[cfg.min_material_status],
        missed_counts=agg["missed_counts"], status_items=agg["status_items"], diary_summary=agg["diary_summary"])
    completeness_pct = metrics["completeness_pct"] if metrics else 0.0
    days_so_far = day_rows[end]["facts"]["days_of_data_so_far"]
    reliable = is_reliable(completeness_pct, days_so_far, cfg)
    flags = []
    if agg["removed"]:
        flags.append({"flag": f"questionable_reading_removed:{len(agg['removed'])}", "affects": sorted(twin)})
    if agg["gap_hours"] is not None:
        flags.append({"flag": f"gap_hours:{agg['gap_hours']}", "affects": ["completeness_pct", "n_readings"]})
    flags += [{"flag": f"low_completeness:{x['stream']}:{x['pct']}", "affects": [x["stream"]]} for x in agg["low_completeness"]]
    hist_glucose_days = sum(1 for d in day_rows[:start] if d["facts"]["daily_values"].get(gname) is not None)
    early = hist_glucose_days < cfg.min_days_for_compare or prev is None
    gist_status = "code_line_early" if early else ("code_line_quiet" if not material else None)
    facts = {"start_date": dates[0], "end_date": end_date, "n_days": len(days), "glucose": metrics, "window_values": values, "prev_window_values": pvalues if pdays else None,
             "profile_asof": profile, "deltas": {"clean": clean_d, "raw": raw_d}, "days_of_data_so_far": days_so_far, "n_medications": n_meds, **extra_facts}
    row = {
        "window_id": f"{tier}_ENDING_{end_date}", "tier": tier, "start_date": dates[0], "end_date": end_date, "reliable": reliable, "confidence": confidence(reliable, completeness_pct),
        "facts": facts, "tags": tags, "co_movement": cm, "material_changes": material, "anchors_crossed": crossed, "anchors_questionable": questionable,
        "is_notable": bool(crossed), "notable_reason": notable_reason(cfg, crossed, clean_d, tags), "deltas_clean": clean_d,
        "data_quality": {"flags": flags, "questionable_readings": agg["removed"], "metrics_with_questionable": twin, "completeness_pct": completeness_pct, "reliable": reliable},
        "gist_status": gist_status, "gist_headline": code_line(cfg, gist_status) if gist_status else None, "gist_sentences": [] if gist_status else None,
        "config_version": cfg.version, "quiet": not material,
    }
    return row


def _week_extras(cfg: Config, days: list[dict]) -> dict:
    """Day-by-day list, best/worst day, aggregates, diary events — everything code prints for a week."""
    traj = []
    for d in days:
        f = d["facts"]
        g = f["glucose"]
        traj.append({"date": f["date"], "glucose_mean": g["mean"] if g else None, "tir_pct": g["tir_pct"] if g else None, "sleep_hours": f["sleep"]["duration_hours"],
                     "steps": f["activity"]["total_steps"], "adherence_pct": f["adherence"]["overall_pct"], "worst_mood": worst_mood(f["mood"]["blocks"], cfg),
                     "missed_medicines": sorted(m for m, s in f["adherence"]["per_medication"].items() if s != "taken"), "diary_event_count": len(f["diary_events"]),
                     "removed_readings": len(d["data_quality"]["questionable_readings"]),
                     "gap_hours": next((float(x["flag"].split(":")[1]) for x in d["data_quality"]["flags"] if x["flag"].startswith("gap_hours")), None)})
    best, worst, identical = best_and_worst(traj)
    pick = lambda t: None if t is None else {"date": t["date"], "tir_pct": t["tir_pct"], "glucose_mean": t["glucose_mean"]}
    per_med: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    mood: dict[str, Counter] = defaultdict(Counter)
    meals: Counter = Counter()
    loc: Counter = Counter()
    steps = [t["steps"] for t in traj if t["steps"] is not None]
    for d in days:
        f = d["facts"]
        for med, s in f["adherence"]["per_medication"].items():
            per_med[med][1] += 1
            per_med[med][0] += s == "taken"
        for block, b in f["mood"]["blocks"].items():
            mood[block][b["category"]] += 1
        meals.update(m["label"] for m in f["meals"])
        if f["lifestyle"]["location"]:
            loc[f["lifestyle"]["location"]] += 1
    peaks = [m["peak_glucose"] for d in days for m in d["facts"]["post_meal"]]
    by_date = {d["facts"]["date"]: d for d in days}
    foods = lambda t: [] if t is None else [{"label": m["label"], "food": m["food_description"]} for m in by_date[t["date"]]["facts"]["meals"]]
    comp = defaultdict(list)
    for d in days:
        for s, pct in d["facts"]["completeness_by_stream"].items():
            comp[s].append(pct)
    taken = sum(v[0] for v in per_med.values())
    expected = sum(v[1] for v in per_med.values())
    return {
        "daily_trajectory": traj, "best_day": pick(best), "worst_day": pick(worst),
        "best_and_worst_note": "all days had the same time in range and the same average glucose" if identical else None,
        "events_in_window": [{**e, "date": d["facts"]["date"]} for d in days for e in d["facts"]["diary_events"]],
        "aggregates": {
            "steps": {"sum": round(sum(steps), 1) if steps else None, "mean_per_day": round(statistics.fmean(steps), 2) if steps else None, "n_days": len(steps)},
            "adherence": {"overall_pct": round(100 * taken / expected, 1) if expected else None, "per_medication": {m: {"taken": v[0], "expected": v[1]} for m, v in sorted(per_med.items())}},
            "mood_by_block": {b: dict(c) for b, c in mood.items()}, "meals_by_label": dict(meals),
            "post_meal_peak_mean": round(statistics.fmean(peaks), 2) if peaks else None, "post_meal_peak_max": max(peaks) if peaks else None,
            "foods_best_day": foods(best), "foods_worst_day": foods(worst), "location_days": dict(loc),
            "blood_pressure": [{**b, "date": d["facts"]["date"]} for d in days for b in d["facts"]["blood_pressure"]],
            "completeness_by_stream": {s: round(statistics.fmean(x), 1) for s, x in comp.items()},
        },
    }


def _month_extras(cfg: Config, view: StoreView, day_rows: list[dict], kept_by: dict, end_idx: int, kept_all: list[Reading], partial: bool) -> dict:
    exp = cfg.glucose_expected_per_day
    upto = day_rows[: end_idx + 1]
    cum_vals = [v for d in upto for v in kept_by.get(d["facts"]["date"], [])]
    months: dict[str, list[dict]] = defaultdict(list)
    for d in upto:
        months[d["facts"]["date"][:7]].append(d)
    traj = []
    for ym, ds in sorted(months.items()):
        vals = [v for d in ds for v in kept_by.get(d["facts"]["date"], [])]
        mean = lambda xs: round(statistics.fmean(xs), 2) if xs else None
        meds = [s for d in ds for s in d["facts"]["adherence"]["per_medication"].values()]
        diary = Counter(e["category"] for d in ds for e in d["facts"]["diary_events"])
        traj.append({"month": ym, "partial": ym == upto[-1]["facts"]["date"][:7], "n_days": len(ds), "glucose": glucose_metrics(vals, exp * len(ds)),
                     "mean_sleep_hours": mean([d["facts"]["sleep"]["duration_hours"] for d in ds if d["facts"]["sleep"]["duration_hours"] is not None]),
                     "mean_steps": mean([d["facts"]["activity"]["total_steps"] for d in ds if d["facts"]["activity"]["total_steps"] is not None]),
                     "adherence_pct": round(100 * sum(1 for s in meds if s == "taken") / len(meds), 1) if meds else None, "diary_events_by_category": dict(diary)})
    hist: dict[str, list[str]] = defaultdict(list)
    for d in upto:
        for s, st in d["facts"]["statuses"].items():
            if st:
                hist[s].append(st)
    end_date = upto[-1]["facts"]["date"]
    links = lab_link(view.labs(cfg.lab_biomarker), kept_all, cfg, end_date)
    since = upto[max(0, end_idx - cfg.month_every_days + 1)]["facts"]["date"]
    recent = [l["gap_hba1c_minus_gmi"] for l in links if l["lab_date"] >= since and l["gap_hba1c_minus_gmi"] is not None]
    return {"partial": partial, "cumulative": glucose_metrics(cum_vals, exp * len(upto)), "monthly_trajectory": traj, "lab_link": links,
            "chronic_findings": chronic_findings(hist, cfg), "_lab_gap": max(recent, key=abs) if recent else None, "last_n_start": since}


def build_week_and_month(cfg: Config, view: StoreView, day_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    kept, removed = clean_series(view.glucose_series, cfg)
    kept_by, removed_by = defaultdict(list), defaultdict(list)
    for r in kept:
        kept_by[r.dt.date().isoformat()].append(r.value)
    for rm in removed:
        removed_by[rm.date].append(rm)
    labs = view.labs(cfg.lab_biomarker)
    n, w = len(day_rows), cfg.week_days

    weeks = []
    for end in range(w - 1, n):
        start = end - w + 1
        prev = (start - w, start - 1) if start - w >= 0 else None
        row = _build_window(cfg, "week", day_rows, kept_by, removed_by, start, end, prev, labs, kept, _week_extras(cfg, day_rows[start:end + 1]))
        if row["gist_status"] is None and cfg.week_gist_weekday and not (weekday_name(row["end_date"]) == cfg.week_gist_weekday or row["anchors_crossed"]):
            row["gist_status"] = "code_line_week_skipped"        # only when a weekday rule is configured: other weeks get a code line (the top two items)
            row["gist_sentences"] = []
        row["deviation_text"] = week_text(cfg, row)
        if row["gist_status"] == "code_line_week_skipped":
            row["gist_headline"] = fallback_code_line(cfg, row)
        elif row["gist_status"] == "code_line_early":
            row["gist_headline"] = early_code_line(cfg, row)
        weeks.append(row)

    months = []
    every = cfg.month_every_days
    idxs = checkpoint_indices(n, every)
    for k, c in enumerate(idxs):
        start = max(0, c - every + 1)
        pc = idxs[k - 1] if k else None
        prev = (max(0, pc - every + 1), pc) if pc is not None else None
        extras = _month_extras(cfg, view, day_rows, kept_by, c, kept, partial=(c != idxs[0] and (c + 1) % every != 0) if k == len(idxs) - 1 else False)
        extras["partial"] = (c + 1) % every != 0
        row = _build_window(cfg, "month", day_rows, kept_by, removed_by, start, c, prev, labs, kept, extras)
        row["facts"]["checkpoint_index"] = c
        row["facts"]["last_30_days"] = row["facts"].pop("glucose")           # the compared window: the last `month_every_days` days (named for the default 30)
        row["facts"]["start_date"] = day_rows[0]["facts"]["date"]            # cumulative from day 1; the compared window starts at last_n_start
        row["start_date"] = day_rows[0]["facts"]["date"]
        row["deviation_text"] = month_text(cfg, row)
        if row["gist_status"] == "code_line_early":
            row["gist_headline"] = early_code_line(cfg, row)
        months.append(row)
    return weeks, months
