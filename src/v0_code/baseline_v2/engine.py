"""Baseline Engine v2, day tier (Stage A). Code only, no LLM.

For every calendar day: clean the glucose series first, compute the day's facts, learn what is normal for her from history STRICTLY BEFORE
the day, tag every stream against its own flat band, evaluate the anchors on cleaned values, and list what deviated. Nothing here reads a
later date than the window's own (spec rule 5); tests/test_v2_invariants.py rebuilds from a truncated store to prove it.
"""

import statistics
from collections import defaultdict
from datetime import datetime, timedelta

from v0_code.baseline_v2 import anchors as anchors_mod
from v0_code.baseline_v2.config import MATERIAL_STATUS_RANK, Config
from v0_code.baseline_v2.data import StoreView
from v0_code.baseline_v2.material import build_material
from v0_code.baseline_v2.profile import build_profile, day_status
from v0_code.baseline_v2.render import code_line, deviation_text, early_code_line, notable_reason
from v0_code.baseline_v2.tags import co_movement, make_tag
from v0_code.baseline_v2.trust import clean_series, confidence, glucose_metrics, is_reliable, max_gap_hours, with_questionable

PERIODS = [("overnight", 0, 6), ("morning", 6, 12), ("afternoon", 12, 18), ("evening", 18, 24)]
MEAL_WINDOW_MIN = 150


def _period_stats(readings) -> dict:
    out = {}
    for name, h0, h1 in PERIODS:
        vals = [r.value for r in readings if h0 <= r.dt.hour < h1]
        out[name] = ({"mean": round(statistics.fmean(vals), 2), "max": max(vals), "tir_pct": round(100 * sum(1 for v in vals if 70 <= v <= 180) / len(vals), 2)} if vals else None)
    return out


def _post_meal(readings, meals, tz) -> list[dict]:
    out = []
    for m in sorted(meals, key=lambda r: r.timestamp or ""):
        if not m.timestamp:
            continue
        mt = datetime.fromisoformat(m.timestamp).astimezone(tz)
        pre = [r for r in readings if r.dt <= mt]
        window = [r for r in readings if mt <= r.dt <= mt + timedelta(minutes=MEAL_WINDOW_MIN)]
        if not pre or not window:
            continue
        peak = max(window, key=lambda r: r.value)
        out.append({"meal_label": m.category or "meal", "meal_time": m.timestamp, "food_description": m.value_text, "pre_meal_glucose": pre[-1].value,
                    "peak_glucose": peak.value, "rise": round(peak.value - pre[-1].value, 1), "minutes_to_peak": round((peak.dt - mt).total_seconds() / 60)})
    return out


def meds_worsened(prev_per_med: dict | None, per_med: dict) -> int | None:
    """Medicines that got WORSE since the previous day (taken -> missed). A recovery is not counted; a medicine with no previous day cannot have
    worsened. None when there is no previous day."""
    if prev_per_med is None:
        return None
    return sum(1 for med, s in per_med.items() if prev_per_med.get(med) == "taken" and s == "missed")


def stream_day_status(sc, readings) -> str | None:
    """A day's clinical status for a stream from its readings (ts, value, status). A continuous stream has none: its individual readings are
    not judged against a reference range (heart rate in zero-step hours includes sleep), it feeds averages, trends and direction tags only.
    The decision is the stream's `kind` in config, never its name."""
    if sc.kind == "continuous":
        return None
    return day_status([s for _, _, s in readings])


def _first(rows):
    return rows[0] if rows else (None, None, None)


def build_windows(cfg: Config, view: StoreView) -> dict[str, list[dict]]:
    """All three tiers: day, rolling week, month checkpoint."""
    from v0_code.baseline_v2.windows import build_week_and_month
    days = build_days(cfg, view)
    weeks, months = build_week_and_month(cfg, view, days)
    return {"day": days, "week": weeks, "month": months}


def build_days(cfg: Config, view: StoreView) -> list[dict]:
    tz = cfg.tz
    kept, removed = clean_series(view.glucose_series, cfg)          # CLEAN FIRST: everything below is computed on `kept`
    kept_by, rem_by = defaultdict(list), defaultdict(list)
    for r in kept:
        kept_by[r.dt.date().isoformat()].append(r)
    for rm in removed:
        rem_by[rm.date].append(rm)
    exp = cfg.glucose_expected_per_day
    gname = view.glucose_stream
    hist_val = {s.name: [] for s in cfg.streams}
    hist_stat = {s.name: [] for s in cfg.streams}
    prev: dict | None = None
    days_with_data = 0
    out: list[dict] = []

    for date in view.dates:
        kr, rem = kept_by.get(date, []), rem_by.get(date, [])
        vals = [r.value for r in kr]
        metrics = glucose_metrics(vals, exp)
        raw_metrics = glucose_metrics(vals + [x.value for x in rem], exp)
        days_with_data += 1 if kr else 0

        meals = view.ctx_rows("meal_events", date)
        post = _post_meal(kr, meals, tz)
        post_all = _post_meal(sorted(kr + [type(kr[0])(x.ts, datetime.fromisoformat(x.ts).astimezone(tz), x.value) for x in rem], key=lambda r: r.dt) if kr else [], meals, tz)
        adh_rows = view.ctx_rows("medication_adherence", date)
        per_med = {r.category: r.value_text for r in adh_rows if r.category}
        mood_rows = view.ctx_rows("mood_state", date)
        mood_blocks = {r.meta.get("time_block", f"block{i}"): {"label": r.value_text, "category": r.category} for i, r in enumerate(mood_rows)}
        strained = sum(1 for b in mood_blocks.values() if b["category"] in cfg.strain_mood_categories)
        sl_v, sl_s = _first(view.raw_rows("sleep_duration", date))[1:]
        quality = next((r.value_text for r in view.ctx_rows("sleep_quality", date)), None)
        st_v, st_s = _first(view.raw_rows("step_count", date))[1:]
        sed_v, sed_s = _first(view.raw_rows("sedentary_time", date))[1:]
        hr_vals = [r.value_num for r in view.ctx_rows("continuous_heart_rate", date) if r.value_num is not None]
        rhr_v, rhr_s = _first(view.raw_rows("resting_heart_rate", date))[1:]
        sys_rows = {ts: (v, s) for ts, v, s in view.raw_rows("blood_pressure_systolic", date)}
        dia_rows = {ts: (v, s) for ts, v, s in view.raw_rows("blood_pressure_diastolic", date)}
        bp = [{"timestamp": ts, "systolic": sys_rows[ts][0], "diastolic": dia_rows[ts][0], "systolic_status": sys_rows[ts][1], "diastolic_status": dia_rows[ts][1]}
              for ts in sorted(sys_rows) if ts in dia_rows]
        hyd_v, hyd_s = _first(view.raw_rows("hydration", date))[1:]
        scr_v, scr_s = _first(view.raw_rows("screen_time", date))[1:]
        diary = [{"category": r.category, "text": r.value_text, "severity_note": (r.meta.get("note") or None)} for r in sorted(view.ctx_rows("diary_context", date), key=lambda r: r.timestamp or "")]

        # ---- daily value per configured stream (generic aggregators; the config row picks one)
        peaks = [m["peak_glucose"] for m in post]
        aggs = {
            "glucose_mean": lambda sc: metrics["mean"] if metrics else None,
            "glucose_tir_pct": lambda sc: metrics["tir_pct"] if metrics else None,
            "glucose_cv_pct": lambda sc: metrics["cv_pct"] if metrics else None,
            "value": lambda sc: _first(view.raw_rows(sc.name, date))[1],
            "mean": lambda sc: (round(statistics.fmean(v for v in (r.value_num for r in view.ctx_rows(sc.name, date)) if v is not None), 2)
                                if sc.source == "context_num" and any(r.value_num is not None for r in view.ctx_rows(sc.name, date))
                                else (round(statistics.fmean(v for _, v, _s in view.raw_rows(sc.name, date)), 2) if view.raw_rows(sc.name, date) else None)),
            "adherence_pct": lambda sc: round(100 * sum(1 for s in per_med.values() if s == "taken") / len(per_med), 1) if per_med else None,
            "strained_count": lambda sc: float(strained) if mood_blocks else None,
            "post_meal_peak": lambda sc: round(statistics.fmean(peaks), 2) if peaks else None,
        }
        dv = {sc.name: aggs[sc.agg](sc) for sc in cfg.streams}

        # ---- completeness per stream, and statuses
        n_meds = len(view.meds_by_date[date])
        completeness, statuses = {}, {}
        for sc in cfg.streams:
            if sc.kind == "derived":
                continue
            expected = sc.expected_per_day or (n_meds if sc.agg == "adherence_pct" else None)
            if sc.agg == "glucose_mean":
                n = len(kr)
            elif sc.source == "context_num":
                n = sum(1 for r in view.ctx_rows(sc.name, date) if r.value_num is not None)
            elif sc.source == "context":
                n = len(view.ctx_rows(sc.name, date))
            else:
                n = len(view.raw_rows(sc.name, date))
            if expected:
                completeness[sc.name] = round(min(100.0, 100 * n / expected), 1)
            if sc.agg != "glucose_mean" and sc.kind != "continuous":      # glucose's per-reading statuses use fasting cut-offs (see trust.py); continuous streams have no status
                statuses[sc.name] = stream_day_status(sc, view.raw_rows(sc.name, date))

        # ---- the as-of profile: history strictly before today
        profile = {sc.name: build_profile(hist_val[sc.name], hist_stat[sc.name], cfg) for sc in cfg.streams}
        prev_dv = prev["dv"] if prev else {}
        tags = [make_tag(sc, dv.get(sc.name), prev_dv.get(sc.name), profile[sc.name], cfg) for sc in cfg.streams]
        cm = co_movement(tags, gname)

        # ---- anchors on CLEANED values; the raw evaluation finds crossings that exist only because of a removed reading
        def delta(a, b):
            return round(a - b, 4) if a is not None and b is not None else None

        def anchor_deltas(m, pm, d, pd) -> dict:
            changed = meds_worsened(prev["per_med"] if prev is not None else None, per_med)
            return {"tir": delta(d.get("time_in_range"), pd.get("time_in_range")), "cv": delta(d.get("variability"), pd.get("variability")),
                    "gmi": delta(m and m["gmi_pct"], pm and pm["gmi_pct"]), "sleep": delta(d.get("sleep_duration"), pd.get("sleep_duration")),
                    "resting_hr": delta(d.get("resting_heart_rate"), pd.get("resting_heart_rate")), "steps": delta(d.get("step_count"), pd.get("step_count")),
                    "adherence_pct": delta(d.get("medication_adherence"), pd.get("medication_adherence")), "meds_changed": changed,
                    "severe_curr": (m["tar_severe_pct"] + m["tbr_severe_pct"]) if m else None, "severe_prior": (pm["tar_severe_pct"] + pm["tbr_severe_pct"]) if pm else None}

        clean_d = anchor_deltas(metrics, prev["metrics"] if prev else None, dv, prev_dv)
        raw_dv = {**dv, "time_in_range": raw_metrics["tir_pct"] if raw_metrics else None, "variability": raw_metrics["cv_pct"] if raw_metrics else None}
        raw_prev_dv = {**prev_dv, "time_in_range": prev["raw_metrics"]["tir_pct"] if prev and prev["raw_metrics"] else None,
                       "variability": prev["raw_metrics"]["cv_pct"] if prev and prev["raw_metrics"] else None} if prev else {}
        raw_d = anchor_deltas(raw_metrics, prev["raw_metrics"] if prev else None, raw_dv, raw_prev_dv)
        crossed, questionable = anchors_mod.split_questionable(cfg, "day", clean_d, raw_d, n_meds)

        # ---- trust: flags with their `affects`, reliability
        completeness_pct = metrics["completeness_pct"] if metrics else 0.0
        reliable = is_reliable(completeness_pct, days_with_data, cfg)
        gap = max_gap_hours(kr)
        twin = with_questionable(vals, [x.value for x in rem], exp)
        if rem and post_all and [m["peak_glucose"] for m in post_all] != peaks and post_all:
            twin["post_meal_peak_max"] = max(m["peak_glucose"] for m in post_all)
        low = [{"stream": sc.name, "label": sc.display, "pct": completeness[sc.name]} for sc in cfg.streams
               if sc.name in completeness and completeness[sc.name] < cfg.reliable_completeness_pct]
        flags = []
        if rem:
            flags.append({"flag": f"questionable_reading_removed:{len(rem)}", "affects": sorted(twin)})
        if gap > cfg.gap_hours_flag:
            flags.append({"flag": f"gap_hours:{round(gap, 1)}", "affects": ["completeness_pct", "n_readings"]})
        flags += [{"flag": f"low_completeness:{x['stream']}:{x['pct']}", "affects": [x["stream"]]} for x in low]
        removed_items = [{"time": x.ts, "value": x.value, "reason": x.reason} for x in rem]

        usual = {n: p["usual_status"] for n, p in profile.items()}
        material = build_material(anchors_crossed=crossed, per_medication=per_med, diary_events=diary, statuses=statuses, usual=usual, tags=tags,
                                  gap_hours=round(gap, 1) if gap > cfg.gap_hours_flag else None, low_completeness=low, removed=removed_items, date=date,
                                  min_status_rank=MATERIAL_STATUS_RANK[cfg.min_material_status])
        notable = bool(crossed)
        conf = confidence(reliable, completeness_pct)
        early = len(hist_val[gname]) < cfg.min_days_for_compare
        gist_status = "code_line_early" if early else ("code_line_quiet" if not material else None)

        facts = {
            "date": date, "glucose": metrics, "glucose_by_period": _period_stats(kr), "post_meal": post,
            "sleep": {"duration_hours": sl_v, "status": sl_s, "quality": quality},
            "activity": {"total_steps": st_v, "status": st_s, "sedentary_minutes": sed_v, "sedentary_status": sed_s},
            "heart_rate": {"continuous_mean": round(statistics.fmean(hr_vals), 1) if hr_vals else None, "continuous_min": min(hr_vals) if hr_vals else None,
                           "continuous_max": max(hr_vals) if hr_vals else None, "resting_daily": rhr_v, "resting_status": rhr_s},
            "blood_pressure": bp, "adherence": {"per_medication": per_med, "overall_pct": dv.get("medication_adherence")},
            "mood": {"blocks": mood_blocks, "strained_count": strained if mood_blocks else None},
            "meals": [{"label": r.category, "time": r.timestamp, "food_description": r.value_text} for r in sorted(meals, key=lambda r: r.timestamp or "")],
            "lifestyle": {"hydration_ml": hyd_v, "hydration_status": hyd_s, "screen_time_hours": scr_v, "screen_time_status": scr_s,
                          "location": next((r.value_text for r in view.ctx_rows("location", date)), None)},
            "diary_events": diary, "statuses": statuses, "completeness_by_stream": completeness, "daily_values": dv, "profile_asof": profile,
            "deltas": {"clean": clean_d, "raw": raw_d}, "days_of_data_so_far": days_with_data, "n_medications": n_meds,
        }
        row = {
            "window_id": f"day_{date}", "tier": "day", "start_date": date, "end_date": date, "reliable": reliable, "confidence": conf,
            "facts": facts, "tags": tags, "co_movement": cm, "material_changes": material, "anchors_crossed": crossed, "anchors_questionable": questionable,
            "is_notable": notable, "notable_reason": notable_reason(cfg, crossed, clean_d, tags), "deltas_clean": clean_d,
            "data_quality": {"flags": flags, "questionable_readings": removed_items, "metrics_with_questionable": twin, "completeness_pct": completeness_pct, "reliable": reliable},
            "gist_status": gist_status, "gist_headline": code_line(cfg, gist_status) if gist_status else None, "gist_sentences": [] if gist_status else None,
            "config_version": cfg.version, "quiet": not material,
        }
        row["deviation_text"] = deviation_text(cfg, row)
        if gist_status == "code_line_early":
            row["gist_headline"] = early_code_line(cfg, row)          # "Not enough history yet to compare." + the two most important things that happened
        out.append(row)

        for sc in cfg.streams:                                    # today becomes history only AFTER it has been judged
            if dv.get(sc.name) is not None:
                hist_val[sc.name].append(dv[sc.name])
            if statuses.get(sc.name):
                hist_stat[sc.name].append(statuses[sc.name])
        prev = {"dv": dv, "metrics": metrics, "raw_metrics": raw_metrics, "per_med": per_med}
    return out
