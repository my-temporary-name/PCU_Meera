"""Code-computed cross-domain memory records (day/week/month) — no LLM here.

Builds the JSON record described in task/baseline.md section 5, reusing the existing glucose
window code untouched (logic/baseline_glucose.py) and adding every other domain on top, driven
by the stream registry (logic/registry.py) so adding a biomarker is a config change, not a new
branch here. Computes anchors_crossed (spec change A) and data_quality_flags in code; the LLM
step downstream only explains what's already been decided.
"""

import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from v0_code.data.store import PersonalDataStore
from v0_code.logic import stream_tables as st
from v0_code.logic.patient_config import MIN_USUAL_DAYS
from v0_code.logic.anchors import evaluate_anchors, questionable_anchors
from v0_code.logic.data_quality import (
    ARTIFACT_FLAGS, IMPLAUSIBLE_RATE_MG_DL_PER_15MIN, KNOWN_CLIP_ARTIFACT_VALUE, MAX_READING_FLAG_THRESHOLD,
    cleaned_deltas, cleaned_metrics, effective_deltas, flag_details, questionable_timestamps,
)
from v0_code.logic.registry import numeric_streams
from v0_code.logic.baseline_glucose import EXPECTED_PER_DAY, _deltas as _glucose_deltas, _metrics as _glucose_metrics, compute_glucose_windows

# NOTE (by design, not a bug): the Threshold Evaluator's glucose `status` uses fasting-glucose cut-offs
# (70/99/125, diagnostic), while every CGM metric here uses the ADA management bands (70/180/250/54).
# One reading can be `high` in raw_events and still count as time-in-range in these records.
PERIODS = [("overnight", 0, 6), ("morning", 6, 12), ("afternoon", 12, 18), ("evening", 18, 24)]
MEAL_WINDOW_MIN = 150
AUG22_DISCREPANCY_DATE = "2026-08-22"
# Per-stream "flat" bands (absolute, config not inline): |change| <= band is reported as flat.
# Mechanical, not clinical — they only decide how code labels a direction for the LLM to repeat.
FLAT_BANDS = {"glucose_mean": 2.0, "sleep_hours": 0.25, "steps": 250.0, "resting_hr": 1.0, "adherence_pct": 2.0}
DOMAIN_STREAM = {"sleep": "sleep_hours", "steps": "steps", "adherence": "adherence_pct", "resting_hr": "resting_hr"}
LOW_COMPLETENESS_PCT = 70.0  # any stream with expected data below this gets a low_completeness flag
# Mood categories ranked by distress, not by list order: positive_uplifted is the *least* distressed,
# so it must never rank as a day's "worst" mood.
DISTRESS_RANK = {"positive_uplifted": 0, "calm_stable": 1, "mild_stress": 2, "tired_low_energy": 3, "anxious": 4, "overwhelmed_high_distress": 5}
# Flag kinds that make a window "not quiet" (a data gap, low completeness, or a probable sensor artifact).
# Statuses that can count as a deviation (borderline or worse) — and only when they differ from the stream's usual status.
MATERIAL_STATUSES = {"high", "low", "borderline_high", "borderline_low"}


def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _direction(curr: float | None, prior: float | None, stream: str) -> str | None:
    if curr is None or prior is None:
        return None
    return _dir_from_delta(curr - prior, stream)


def _dir_from_delta(delta: float | None, stream: str) -> str | None:
    if delta is None:
        return None
    return "flat" if abs(delta) <= FLAT_BANDS[stream] else ("up" if delta > 0 else "down")


class MemoryData:
    """Everything pulled from the store once, grouped in memory — avoids per-window SQL."""

    def __init__(self, store: PersonalDataStore):
        raw = store.conn.execute("SELECT * FROM raw_events WHERE source_type='reading'").fetchall()
        ctx = store.conn.execute("SELECT * FROM context_events").fetchall()

        self.raw_by_bio_date: dict[tuple[str, str], list] = defaultdict(list)
        for r in raw:
            self.raw_by_bio_date[(r["biomarker"], r["timestamp"][:10])].append(r)

        self.ctx_by_stream_date: dict[tuple[str, str], list] = defaultdict(list)
        for r in ctx:
            self.ctx_by_stream_date[(r["stream"], r["date"])].append(r)

        glucose_rows = [(r["timestamp"], r["value"]) for r in raw if r["biomarker"] == "cgm_glucose_reading"]
        self.glucose_by_date: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for ts, v in glucose_rows:
            self.glucose_by_date[ts[:10]].append((ts, v))
        for vals in self.glucose_by_date.values():
            vals.sort()

        windows = compute_glucose_windows(glucose_rows)
        self.glucose_day: dict[str, object] = {w.window_start: w for w in windows if w.window_type == "day"}
        self.glucose_week: dict[str, object] = {w.window_end: w for w in windows if w.window_type == "week"}

        self.dates: list[str] = sorted(self.glucose_by_date)
        # A stream's "usual" status: the most common day-level status (a day's own most common reading status) across
        # the history BEFORE that day — an expanding window, so nothing in a window depends on data after it. With fewer
        # than MIN_USUAL_DAYS prior days there is no usual yet and any non-normal status counts as a deviation. A non-normal
        # day is only a deviation when it differs from the usual: steps "low" on 95% of days is her baseline, a borderline
        # sleep night is not.
        day_mode: dict[tuple[str, str], str] = {}
        for (bio, d), rows in self.raw_by_bio_date.items():
            c = Counter(r["status"] for r in rows if r["status"])
            if bio != "cgm_glucose_reading" and c:
                day_mode[(bio, d)] = max(c, key=lambda k: (c[k], k))
        self.day_status_mode = day_mode
        self.usual_before: dict[tuple[str, str], str | None] = {}  # (biomarker, date) -> usual status from days before `date`
        seen: dict[str, Counter] = defaultdict(Counter)
        for (bio, d), mode in sorted(day_mode.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            hist = seen[bio]
            self.usual_before[(bio, d)] = max(hist, key=lambda k: (hist[k], k)) if sum(hist.values()) >= MIN_USUAL_DAYS else None
            hist[mode] += 1
        # Readings code treats as questionable (clipped 65.0, >400, implausible jump). Metrics are also
        # computed without them so an entry can rest on cleaned values (logic/data_quality.py).
        self.questionable_ts: set[str] = set()
        for readings in self.glucose_by_date.values():
            self.questionable_ts |= questionable_timestamps(readings)
        self._daily: dict[str, dict[str, float | None]] = {}  # stream label -> {date: daily value}, filled as day records are built
        self._flags_by_date: dict[str, list[str]] = {}
        self._day_cache: dict[str, dict] = {}  # populated by build_day_record as it runs, date-ascending
        self.n_meds = len({r["category"] for r in ctx if r["stream"] == "medication_adherence"})
        self.hba1c = sorted((r for (bio, _d), rows in self.raw_by_bio_date.items() for r in rows if bio == "hba1c"), key=lambda r: r["timestamp"])


# ---- per-day sections -------------------------------------------------------------------------


def _glucose_section(date: str, data: MemoryData) -> dict:
    w = data.glucose_day.get(date)
    values = data.glucose_by_date.get(date, [])
    if w is None or not values:
        return {}
    min_ts, min_v = min(values, key=lambda p: p[1])
    max_ts, max_v = max(values, key=lambda p: p[1])
    out = {
        "mean": w.mean, "gmi_pct": w.gmi_pct, "tir_pct": w.tir_pct, "tar_pct": w.tar_pct,
        "tar_severe_pct": w.tar_severe_pct, "tbr_pct": w.tbr_pct, "tbr_severe_pct": w.tbr_severe_pct,
        "cv_pct": w.cv_pct, "min_value": min_v, "min_timestamp": min_ts, "max_value": max_v,
        "max_timestamp": max_ts, "n_readings": w.n_readings, "completeness_pct": w.completeness_pct,
    }
    return _with_cleaned(out, [date], data, EXPECTED_PER_DAY)


def _deltas_with_cleaned(deltas: dict, curr_dates: list[str], prior_dates: list[str], data: "MemoryData", curr_exp: int, prior_exp: int) -> dict:
    """Adds `questionable_excluded` to a deltas dict: the glucose changes recomputed without questionable readings
    in either window. The raw changes (which the anchors use) stay; nothing is overwritten."""
    curr = [r for d in curr_dates for r in data.glucose_by_date.get(d, [])]
    prior = [r for d in prior_dates for r in data.glucose_by_date.get(d, [])] or None
    c = cleaned_deltas(curr, prior, data.questionable_ts, curr_exp, prior_exp, set(deltas))
    if c:
        deltas["questionable_excluded"] = c
    return deltas


def _with_cleaned(metrics: dict, dates: list[str], data: "MemoryData", expected: int) -> dict:
    """Adds `questionable_excluded` (the metrics recomputed without questionable readings) when the
    window holds any. The raw metrics stay as they are; nothing is overwritten."""
    readings = [r for d in dates for r in data.glucose_by_date.get(d, [])]
    c = cleaned_metrics(readings, data.questionable_ts, expected)
    if c:
        metrics["questionable_excluded"] = c
    return metrics


def _glucose_by_period(date: str, data: MemoryData) -> dict:
    values = data.glucose_by_date.get(date, [])
    out = {}
    for name, h0, h1 in PERIODS:
        vals = [v for ts, v in values if h0 <= int(ts[11:13]) < h1]
        out[name] = (
            {"mean": round(statistics.fmean(vals), 2), "max": max(vals), "tir_pct": round(100 * sum(1 for v in vals if 70 <= v <= 180) / len(vals), 2)}
            if vals else {"mean": None, "max": None, "tir_pct": None}
        )
    return out


def _post_meal(date: str, data: MemoryData) -> list[dict]:
    values = data.glucose_by_date.get(date, [])
    meals = sorted(data.ctx_by_stream_date.get(("meal_events", date), []), key=lambda r: r["timestamp"])
    out = []
    for m in meals:
        mt = _dt(m["timestamp"])
        pre = [v for ts, v in values if _dt(ts) <= mt]
        window = [(ts, v) for ts, v in values if mt <= _dt(ts) <= mt + timedelta(minutes=MEAL_WINDOW_MIN)]
        if not pre or not window:
            continue
        pre_v = pre[-1]
        peak_ts, peak_v = max(window, key=lambda p: p[1])
        entry = {
            "meal_label": m["category"], "meal_time": m["timestamp"], "food_description": m["value_text"],
            "pre_meal_glucose": pre_v, "peak_glucose": peak_v, "rise": round(peak_v - pre_v, 1),
            "minutes_to_peak": round((_dt(peak_ts) - mt).total_seconds() / 60),
        }
        # Peak without questionable readings (a 599 spike inside the meal window is not a real peak).
        dropped = [v for ts, v in window if ts in data.questionable_ts]
        clean_window = [(ts, v) for ts, v in window if ts not in data.questionable_ts]
        if dropped and clean_window:
            clean_peak = max(v for _, v in clean_window)
            entry["questionable_excluded"] = {
                "n_excluded": len(dropped), "excluded_values": sorted(dropped),
                "metrics_without_them": {"peak_glucose": clean_peak, "rise": round(clean_peak - pre_v, 1)},
                "metrics_with_them": {"peak_glucose": peak_v, "rise": entry["rise"]},
            }
        out.append(entry)
    return out


def _sleep_section(date: str, data: MemoryData) -> dict:
    rows = data.raw_by_bio_date.get(("sleep_duration", date), [])
    quality = data.ctx_by_stream_date.get(("sleep_quality", date), [])
    return {
        "duration_hours": rows[0]["value"] if rows else None,
        "status": rows[0]["status"] if rows else None,
        "quality": quality[0]["value_text"] if quality else None,
    }


def _activity_section(date: str, data: MemoryData, steps_by_hour: dict[str, float]) -> dict:
    steps_rows = data.raw_by_bio_date.get(("step_count", date), [])
    sedentary_rows = data.raw_by_bio_date.get(("sedentary_time", date), [])
    hourly = {h: steps_by_hour.get(f"{date}T{h:02d}", 0) for h in range(24)}
    peak_hour = max(hourly, key=hourly.get) if any(hourly.values()) else None
    return {
        "total_steps": steps_rows[0]["value"] if steps_rows else None,
        "status": steps_rows[0]["status"] if steps_rows else None,
        "peak_step_hour": peak_hour,
        "sedentary_minutes": sedentary_rows[0]["value"] if sedentary_rows else None,
    }


def _heart_rate_section(date: str, data: MemoryData, steps_by_hour: dict[str, float]) -> dict:
    # resting_period_mean = mean of the 15-min continuous readings taken in hours with 0 steps
    # (a per-day average over many readings). resting_heart_rate_daily = the single resting HR
    # value in vitals_yearly for that day. They are different measurements and can disagree; the
    # resting-HR anchor and every resting-HR delta use resting_period_mean, never the daily value.
    hr_rows = data.ctx_by_stream_date.get(("continuous_heart_rate", date), [])
    resting_row = data.raw_by_bio_date.get(("resting_heart_rate", date), [])
    all_vals = [r["value_num"] for r in hr_rows if r["value_num"] is not None]
    # "At rest" requires a step reading that is present AND zero. A missing step hour (12 days have none)
    # is unknown, not zero — treating it as rest made resting_period_mean equal the all-day mean.
    resting_vals = [r["value_num"] for r in hr_rows if r["value_num"] is not None and steps_by_hour.get(r["timestamp"][:13]) == 0]
    return {
        "continuous_mean": round(statistics.fmean(all_vals), 1) if all_vals else None,
        "continuous_min": min(all_vals) if all_vals else None,
        "continuous_max": max(all_vals) if all_vals else None,
        "resting_period_mean": round(statistics.fmean(resting_vals), 1) if resting_vals else None,
        "resting_heart_rate_daily": resting_row[0]["value"] if resting_row else None,
        "resting_heart_rate_status": resting_row[0]["status"] if resting_row else None,
    }


def _blood_pressure_section(date: str, data: MemoryData) -> list[dict]:
    sys_rows = {r["timestamp"]: r for r in data.raw_by_bio_date.get(("blood_pressure_systolic", date), [])}
    dia_rows = {r["timestamp"]: r for r in data.raw_by_bio_date.get(("blood_pressure_diastolic", date), [])}
    out = []
    for ts in sorted(sys_rows):
        if ts in dia_rows:
            out.append({"timestamp": ts, "systolic": sys_rows[ts]["value"], "diastolic": dia_rows[ts]["value"],
                        "systolic_status": sys_rows[ts]["status"], "diastolic_status": dia_rows[ts]["status"]})
    return out


def _adherence_section(date: str, data: MemoryData) -> dict:
    rows = data.ctx_by_stream_date.get(("medication_adherence", date), [])
    per_med = {r["category"]: r["value_text"] for r in rows}
    overall_pct = round(100 * sum(1 for r in rows if r["value_text"] == "taken") / len(rows), 1) if rows else None
    return {"per_medication": per_med, "overall_pct": overall_pct}


def _mood_section(date: str, data: MemoryData) -> dict:
    rows = data.ctx_by_stream_date.get(("mood_state", date), [])
    return {r["meta_json"] and json.loads(r["meta_json"])["time_block"]: {"label": r["value_text"], "category": r["category"]} for r in rows}


def _meals_section(date: str, data: MemoryData) -> list[dict]:
    rows = sorted(data.ctx_by_stream_date.get(("meal_events", date), []), key=lambda r: r["timestamp"])
    return [{"label": r["category"], "time": r["timestamp"], "food_description": r["value_text"]} for r in rows]


def _lifestyle_section(date: str, data: MemoryData) -> dict:
    hydration = data.raw_by_bio_date.get(("hydration", date), [])
    screen = data.raw_by_bio_date.get(("screen_time", date), [])
    location = data.ctx_by_stream_date.get(("location", date), [])
    return {
        "hydration_ml": hydration[0]["value"] if hydration else None,
        "screen_time_hours": screen[0]["value"] if screen else None,
        "location": location[0]["value_text"] if location else None,
    }


def _diary_events_section(date: str, data: MemoryData) -> list[dict]:
    rows = sorted(data.ctx_by_stream_date.get(("diary_context", date), []), key=lambda r: r["timestamp"] or "")
    out = []
    for r in rows:
        meta = json.loads(r["meta_json"]) if r["meta_json"] else {}
        out.append({"category": r["category"], "text": r["value_text"], "severity_note": meta.get("note") or None})
    return out


def _other_threshold_crossings(date: str, data: MemoryData) -> list[dict]:
    out = []
    for (bio, d), rows in data.raw_by_bio_date.items():
        if d != date or bio == "cgm_glucose_reading":
            continue
        for r in rows:
            if r["status"] in ("high", "low", "borderline_high", "borderline_low"):
                out.append({"biomarker": bio, "value": r["value"], "status": r["status"]})
    return out


def _unusual_statuses(date: str, data: MemoryData) -> list[dict]:
    """Non-normal day-level statuses that differ from the stream's usual status from history before this day (MemoryData.usual_before)."""
    out = []
    for (bio, d), mode in sorted(data.day_status_mode.items()):
        if d == date and mode in MATERIAL_STATUSES and mode != data.usual_before.get((bio, d)):
            out.append({"measure": bio, "status": mode})
    return out


def _completeness_by_stream(date: str, data: MemoryData) -> dict:
    from v0_code.logic.registry import REGISTRY

    out = {}
    for s in REGISTRY:
        if s.expected_per_day is None:
            continue
        if s.source == "raw_events":
            n = len(data.raw_by_bio_date.get((s.name, date), []))
        else:
            n = len(data.ctx_by_stream_date.get((s.name, date), []))
        out[s.name] = round(100 * n / s.expected_per_day, 1)
    return out


def _data_quality_flags_day(date: str, data: MemoryData) -> list[str]:
    flags = []
    values = [v for _, v in data.glucose_by_date.get(date, [])]
    if any(v == KNOWN_CLIP_ARTIFACT_VALUE for v in values):
        flags.append("known_clip_artifact_reading:65.0")
    if values and max(values) > MAX_READING_FLAG_THRESHOLD:
        flags.append(f"max_reading_above_{MAX_READING_FLAG_THRESHOLD}")
    if date == AUG22_DISCREPANCY_DATE:
        flags.append("known_discrepancy:spec_expected_66.5_hypo_data_shows_~76")
    g = data.glucose_by_date.get(date, [])
    if g:
        gaps = [(_dt(g[i + 1][0]) - _dt(g[i][0])).total_seconds() / 3600 for i in range(len(g) - 1)]
        if gaps and max(gaps) > 1:
            flags.append(f"gap_hours:{round(max(gaps), 1)}")
        if len(g) > 1:
            worst = max(abs(g[i + 1][1] - g[i][1]) / max((_dt(g[i + 1][0]) - _dt(g[i][0])).total_seconds() / 900, 1e-9) for i in range(len(g) - 1))
            if worst > IMPLAUSIBLE_RATE_MG_DL_PER_15MIN:
                flags.append(f"implausible_rate_of_change:{round(worst, 1)}")
    for stream, pct in _completeness_by_stream(date, data).items():
        if pct < LOW_COMPLETENESS_PCT:
            flags.append(f"low_completeness:{stream}:{pct}")
    return flags


# ---- material changes -------------------------------------------------------------------------
#
# "Quiet" means nothing deviated — not merely "no anchor crossed". material_changes lists, in code, every
# deviation: anchors crossed (on cleaned values), missed medicine doses, non-normal statuses that differ from the
# stream's usual, diary events, data gaps / low completeness, and every questionable reading that was removed.
# A day or week is quiet exactly when the list is empty. logic/render.py renders each item kind as a sentence, so
# whatever is in this list is guaranteed to appear in the entry (tests/test_rendering.py checks each kind).
# Glucose's own per-reading statuses are not counted: they use fasting cut-offs (see the band note at the top of this
# module) and would make every window non-quiet.

MATERIAL_KINDS = ("anchor_crossed", "missed_dose", "missed_doses", "unusual_status", "diary_events", "data_quality", "questionable_reading", "lab_result")


def _is_material_flag(flag: str) -> bool:
    return flag.split(":")[0] in ("gap_hours", "low_completeness")


def _quality_items(flags: list[str], glucose: dict) -> list[dict]:
    """Gap / low-completeness flags, and one item per removed questionable reading (what, when, how large)."""
    out = [{"kind": "data_quality", "flag": f} for f in flags if _is_material_flag(f)]
    q = glucose.get("questionable_excluded")
    if q:
        out += [{"kind": "questionable_reading", **r} for r in q.get("excluded_readings", [])]
    return out


def material_changes_day(record: dict) -> list[dict]:
    out: list[dict] = [{"kind": "anchor_crossed", "detail": a} for a in record["anchors_crossed"]]
    out += [{"kind": "missed_dose", "medicine": med} for med, status in record["adherence"]["per_medication"].items() if status != "taken"]
    out += [{"kind": "unusual_status", **x} for x in record.get("unusual_statuses", [])]
    if record["diary_events"]:
        out.append({"kind": "diary_events", "count": len(record["diary_events"])})
    return out + _quality_items(record["data_quality_flags"], record["glucose"])


def material_changes_week(record: dict, days: list[dict], aggregates: dict) -> list[dict]:
    out: list[dict] = [{"kind": "anchor_crossed", "detail": a} for a in record["anchors_crossed"]]
    for med, v in sorted(aggregates["medication_adherence"]["per_medication"].items()):
        if v["taken"] < v["expected"]:
            out.append({"kind": "missed_doses", "medicine": med, "missed": v["expected"] - v["taken"], "of": v["expected"]})
    out += [{"kind": "unusual_status", **x} for x in record.get("unusual_statuses", [])]
    if record["events_in_window"]:
        out.append({"kind": "diary_events", "count": len(record["events_in_window"])})
    return out + _quality_items(record["data_quality_flags"], record["glucose"])


def week_unusual_statuses(days: list[dict]) -> list[dict]:
    c: Counter = Counter((x["measure"], x["status"]) for r in days for x in r.get("unusual_statuses", []))
    return [{"measure": m, "status": st_, "days": n} for (m, st_), n in sorted(c.items())]


def material_changes_month(record: dict, last30_flags: list[str], new_labs: list[dict], last30_diary: int) -> list[dict]:
    out: list[dict] = [{"kind": "anchor_crossed", "detail": a} for a in record["anchors_crossed"]]
    out += [{"kind": "lab_result", "lab_date": x["lab_date"], "hba1c_pct": x["hba1c_pct"], "gap_hba1c_minus_gmi": x["gap_hba1c_minus_gmi"]} for x in new_labs]
    if last30_diary:
        out.append({"kind": "diary_events", "count": last30_diary})
    return out + _quality_items(last30_flags, record["last_30_days"])


def pick_best_worst(days: list[dict]) -> tuple[dict, dict, bool]:
    """(best day, worst day, all_identical). Best = highest TIR, ties broken by the LOWEST mean glucose; worst =
    lowest TIR, ties by the HIGHEST mean (then the earlier date, so the pick is deterministic). When every day is
    identical on both, naming a best and a worst day would invent a difference, so the caller says so instead."""
    best = min(days, key=lambda r: (-r["glucose"]["tir_pct"], r["glucose"]["mean"], r["date"]))
    worst = min(days, key=lambda r: (r["glucose"]["tir_pct"], -r["glucose"]["mean"], r["date"]))
    return best, worst, len({(r["glucose"]["tir_pct"], r["glucose"]["mean"]) for r in days}) == 1


def worst_mood_category(mood: dict) -> str | None:
    """The day's most distressed mood category — ranked by distress, not by list order, so positive_uplifted
    can never be the 'worst' when anything else was recorded."""
    return max(mood.values(), key=lambda m: DISTRESS_RANK.get(m["category"], -1))["category"] if mood else None


# ---- day record ---------------------------------------------------------------------------


def build_day_record(date: str, data: MemoryData, steps_by_hour: dict[str, float]) -> dict:
    glucose = _glucose_section(date, data)
    if not glucose:
        return {}
    sleep = _sleep_section(date, data)
    activity = _activity_section(date, data, steps_by_hour)
    hr = _heart_rate_section(date, data, steps_by_hour)
    adherence = _adherence_section(date, data)

    idx = data.dates.index(date)
    prior_date = data.dates[idx - 1] if idx > 0 else None
    prior_record = data._day_cache.get(prior_date) if prior_date else None  # set by caller loop

    deltas = {
        "glucose_tir_pct": round(glucose["tir_pct"] - prior_record["glucose"]["tir_pct"], 2) if prior_record else None,
        "glucose_cv_pct": round(glucose["cv_pct"] - prior_record["glucose"]["cv_pct"], 2) if prior_record else None,
        "glucose_gmi_pct": round(glucose["gmi_pct"] - prior_record["glucose"]["gmi_pct"], 2) if prior_record else None,
        "glucose_mean": round(glucose["mean"] - prior_record["glucose"]["mean"], 2) if prior_record else None,
        "adherence_overall_pct": round(adherence["overall_pct"] - prior_record["adherence"]["overall_pct"], 1) if prior_record and adherence["overall_pct"] is not None and prior_record["adherence"]["overall_pct"] is not None else None,
        "glucose_severe_total_curr": glucose["tar_severe_pct"] + glucose["tbr_severe_pct"],
        "glucose_severe_total_prior": (prior_record["glucose"]["tar_severe_pct"] + prior_record["glucose"]["tbr_severe_pct"]) if prior_record else None,
        "sleep_hours": round(sleep["duration_hours"] - prior_record["sleep"]["duration_hours"], 2) if prior_record and sleep["duration_hours"] is not None and prior_record["sleep"]["duration_hours"] is not None else None,
        "resting_hr_mean": round(hr["resting_period_mean"] - prior_record["heart_rate"]["resting_period_mean"], 1) if prior_record and hr["resting_period_mean"] is not None and prior_record["heart_rate"].get("resting_period_mean") is not None else None,
        "activity_steps": round(activity["total_steps"] - prior_record["activity"]["total_steps"], 0) if prior_record and activity["total_steps"] is not None and prior_record["activity"]["total_steps"] is not None else None,
        "adherence_meds_changed_count": (
            sum(1 for med, status in adherence["per_medication"].items() if prior_record["adherence"]["per_medication"].get(med) != status)
            if prior_record else None
        ),
    }

    _deltas_with_cleaned(deltas, [date], [prior_date] if prior_date else [], data, EXPECTED_PER_DAY, EXPECTED_PER_DAY)
    n_meds = len(adherence["per_medication"]) or data.n_meds
    record = {
        "window_id": f"day_{date}",
        "tier": "day",
        "date": date,
        "glucose": glucose,
        "glucose_by_period": _glucose_by_period(date, data),
        "post_meal": _post_meal(date, data),
        "sleep": sleep,
        "activity": activity,
        "heart_rate": hr,
        "blood_pressure": _blood_pressure_section(date, data),
        "adherence": adherence,
        "mood": _mood_section(date, data),
        "meals": _meals_section(date, data),
        "lifestyle": _lifestyle_section(date, data),
        "diary_events": _diary_events_section(date, data),
        "other_threshold_crossings": _other_threshold_crossings(date, data),
        "unusual_statuses": _unusual_statuses(date, data),
        "completeness_by_stream": _completeness_by_stream(date, data),
        "deltas": deltas,
    }
    reliable = data.glucose_day[date].reliable
    flags = _data_quality_flags_day(date, data)
    # Anchors read the cleaned changes (questionable readings removed). `anchors_crossed_raw` is what they would have
    # said on the raw values; `anchors_suppressed` is the difference — crossings that existed only because of a bad reading.
    anchors_crossed = evaluate_anchors("day", effective_deltas(deltas), n_meds)
    anchors_crossed_raw = evaluate_anchors("day", {k: v for k, v in deltas.items() if k != "questionable_excluded"}, n_meds)
    record["reliable"], record["data_quality_flags"], record["anchors_crossed"] = reliable, flags, anchors_crossed
    record["anchors_crossed_raw"], record["anchors_suppressed"] = anchors_crossed_raw, [a for a in anchors_crossed_raw if a not in anchors_crossed]
    record["has_diary_event"] = len(record["diary_events"]) > 0  # the structured context-event log, not the daily narrative
    # Directions / changes / cumulative deltas for every numeric registry stream (see logic/stream_tables.py).
    vals = st.daily_values(record)
    hist = {lab: [v for d in data.dates[:idx] if (v := data._daily.get(lab, {}).get(d)) is not None] for lab in vals}
    prior_vals = {lab: (data._daily.get(lab, {}).get(prior_date) if prior_date else None) for lab in vals}
    dirs, changes, strengths = st.stream_tables(vals, prior_vals, hist)
    record["stream_direction_table"] = dirs
    record["stream_change_table"] = changes  # value minus the previous day's value, in the stream's own unit
    record["deltas_vs_cumulative"] = {lab: st.cumulative_delta(vals[lab], hist[lab], reliable) for lab in vals}
    record["co_movement_candidates"] = st.candidates_from_directions(dirs, changes, strengths)
    record["confidence"] = st.confidence(reliable, glucose["completeness_pct"])
    for lab, v in vals.items():
        data._daily.setdefault(lab, {})[date] = v
    data._flags_by_date[date] = flags
    prior_flags = data._flags_by_date.get(prior_date, []) if prior_date else []
    record["anchors_questionable"] = questionable_anchors(anchors_crossed, flags + prior_flags)
    record["data_quality_details"] = flag_details(flags) + flag_details(prior_flags, "previous window")
    record["material_changes"] = material_changes_day(record)
    record["quiet"] = not record["material_changes"]
    data._day_cache[date] = {"glucose": glucose, "sleep": sleep, "heart_rate": hr, "activity": activity, "adherence": adherence}
    return {"record": record, "reliable": reliable, "flags": flags, "anchors_crossed": anchors_crossed, "anchors_questionable": record["anchors_questionable"], "prior_window_id": f"day_{prior_date}" if prior_date else None}


# ---- week record ----------------------------------------------------------------------------


def build_week_record(end_date: str, data: MemoryData, day_records: dict[str, dict]) -> dict | None:
    idx = data.dates.index(end_date)
    if idx < 6:
        return None
    week_dates = data.dates[idx - 6 : idx + 1]
    days = [day_records[d]["record"] for d in week_dates if d in day_records]
    if len(days) < 7:
        return None  # a day with zero glucose readings — shouldn't happen, but never half-build a week

    w = data.glucose_week.get(end_date)
    prior_end_idx = idx - 7
    prior_w = data.glucose_week.get(data.dates[prior_end_idx]) if prior_end_idx >= 6 else None

    daily_trajectory = []
    for d, rec in zip(week_dates, days):
        worst_block = worst_mood_category(rec["mood"])
        daily_trajectory.append({
            "date": d, "glucose_mean": rec["glucose"]["mean"], "tir_pct": rec["glucose"]["tir_pct"],
            "sleep_hours": rec["sleep"]["duration_hours"], "steps": rec["activity"]["total_steps"],
            "adherence_pct": rec["adherence"]["overall_pct"], "worst_mood_category": worst_block,
            "missed_medicines": [m for m, status in rec["adherence"]["per_medication"].items() if status != "taken"],
            "diary_event_count": len(rec["diary_events"]),
        })

    # Best = highest TIR, ties broken by the LOWEST mean glucose; worst = lowest TIR, ties by the HIGHEST mean
    # (then the earlier date, so the pick is deterministic). If every day is identical on both, naming a best and
    # a worst day would be inventing a difference: the record says so instead.
    best, worst, all_days_identical = pick_best_worst(days)

    weekday_vals, weekend_vals = defaultdict(list), defaultdict(list)
    for d, rec in zip(week_dates, days):
        bucket = weekend_vals if _dt(d + "T00:00:00+05:30").weekday() >= 5 else weekday_vals
        for field, section, key in (("glucose_mean", "glucose", "mean"), ("steps", "activity", "total_steps"), ("sleep_hours", "sleep", "duration_hours")):
            v = rec[section][key]
            if v is not None:
                bucket[field].append(v)
    weekday_vs_weekend = None
    if weekday_vals and weekend_vals:
        weekday_vs_weekend = {
            "weekday": {k: round(statistics.fmean(v), 2) for k, v in weekday_vals.items()},
            "weekend": {k: round(statistics.fmean(v), 2) for k, v in weekend_vals.items()},
        }

    def _mean_of(section: str, key: str) -> float | None:
        vals = [r[section][key] for r in days if r[section].get(key) is not None]
        return round(statistics.fmean(vals), 2) if vals else None

    this_week = {"glucose_mean": w.mean, "sleep_hours": _mean_of("sleep", "duration_hours"), "steps": _mean_of("activity", "total_steps"),
                 "resting_hr": _mean_of("heart_rate", "resting_period_mean"), "adherence_pct": _mean_of("adherence", "overall_pct")}
    prior_days = [day_records[d]["record"] for d in data.dates[prior_end_idx - 6 : prior_end_idx + 1] if d in day_records] if prior_end_idx >= 6 else []
    prior_week = None
    if len(prior_days) == 7:
        prior_week = {
            "glucose_mean": prior_w.mean if prior_w else None,
            "sleep_hours": round(statistics.fmean([r["sleep"]["duration_hours"] for r in prior_days if r["sleep"]["duration_hours"] is not None]), 2) if any(r["sleep"]["duration_hours"] is not None for r in prior_days) else None,
            "steps": round(statistics.fmean([r["activity"]["total_steps"] for r in prior_days if r["activity"]["total_steps"] is not None]), 2) if any(r["activity"]["total_steps"] is not None for r in prior_days) else None,
            "resting_hr": round(statistics.fmean([r["heart_rate"]["resting_period_mean"] for r in prior_days if r["heart_rate"]["resting_period_mean"] is not None]), 2) if any(r["heart_rate"]["resting_period_mean"] is not None for r in prior_days) else None,
            "adherence_pct": round(statistics.fmean([r["adherence"]["overall_pct"] for r in prior_days if r["adherence"]["overall_pct"] is not None]), 2) if any(r["adherence"]["overall_pct"] is not None for r in prior_days) else None,
        }
    # Registry-driven tables: aggregates per stream, direction vs the prior week (flat band = 0.5 x SD of
    # earlier daily values), and delta vs cumulative history *before* this week (None while unreliable).
    labels = [x.label for x in numeric_streams()]
    prior_dates_w = data.dates[prior_end_idx - 6 : prior_end_idx + 1] if prior_end_idx >= 6 else []
    hist_w = {lab: [v for d in data.dates[: idx - 6] if (v := data._daily.get(lab, {}).get(d)) is not None] for lab in labels}
    cur_w = {lab: st.window_mean([data._daily.get(lab, {}).get(d) for d in week_dates]) for lab in labels}
    prev_w = {lab: (st.window_mean([data._daily.get(lab, {}).get(d) for d in prior_dates_w]) if prior_dates_w else None) for lab in labels}
    stream_direction_table, stream_change_table, strengths_w = st.stream_tables(cur_w, prev_w, hist_w)
    aggregates = st.week_aggregates(list(zip(week_dates, days)), {"best_date": "" if all_days_identical else best["date"], "worst_date": "" if all_days_identical else worst["date"]})

    events_in_window = [{"date": d, **e} for d, rec in zip(week_dates, days) for e in rec["diary_events"]]

    meal_peaks = defaultdict(int)
    for rec in days:
        for pm in rec["post_meal"]:
            if pm["peak_glucose"] > 180:
                meal_peaks[pm["meal_label"]] += 1
    recurring = [{"pattern": f"post_{label}_peak_above_180", "count": n, "of_days": 7} for label, n in meal_peaks.items() if n >= 3]

    glucose_section = {
        "mean": w.mean, "gmi_pct": w.gmi_pct, "tir_pct": w.tir_pct, "tar_pct": w.tar_pct, "tar_severe_pct": w.tar_severe_pct,
        "tbr_pct": w.tbr_pct, "tbr_severe_pct": w.tbr_severe_pct, "cv_pct": w.cv_pct, "completeness_pct": w.completeness_pct,
    }
    _with_cleaned(glucose_section, week_dates, data, EXPECTED_PER_DAY * 7)
    deltas = {
        "glucose_tir_pct": w.delta_tir_pct, "glucose_cv_pct": w.delta_cv_pct, "glucose_gmi_pct": w.delta_gmi_pct,
        "glucose_severe_total_curr": w.tar_severe_pct + w.tbr_severe_pct,
        "glucose_severe_total_prior": (prior_w.tar_severe_pct + prior_w.tbr_severe_pct) if prior_w else None,
        "sleep_hours": round(this_week["sleep_hours"] - prior_week["sleep_hours"], 2) if prior_week and this_week["sleep_hours"] is not None and prior_week["sleep_hours"] is not None else None,
        "resting_hr_mean": round(this_week["resting_hr"] - prior_week["resting_hr"], 2) if prior_week and this_week["resting_hr"] is not None and prior_week["resting_hr"] is not None else None,
        "activity_steps_mean": round(this_week["steps"] - prior_week["steps"], 1) if prior_week and this_week["steps"] is not None and prior_week["steps"] is not None else None,
        "adherence_overall_pct": round(this_week["adherence_pct"] - prior_week["adherence_pct"], 1) if prior_week and this_week["adherence_pct"] is not None and prior_week["adherence_pct"] is not None else None,
    }

    _deltas_with_cleaned(deltas, week_dates, prior_dates_w, data, EXPECTED_PER_DAY * 7, EXPECTED_PER_DAY * 7)
    record = {
        "window_id": f"week_ENDING_{end_date}", "tier": "week", "start_date": week_dates[0], "end_date": end_date,
        "glucose": glucose_section,
        "daily_trajectory": daily_trajectory,
        "best_day": None if all_days_identical else {"date": best["date"], "tir_pct": best["glucose"]["tir_pct"], "mean": best["glucose"]["mean"], "diary_events": best["diary_events"], "other_threshold_crossings": best["other_threshold_crossings"]},
        "worst_day": None if all_days_identical else {"date": worst["date"], "tir_pct": worst["glucose"]["tir_pct"], "mean": worst["glucose"]["mean"], "diary_events": worst["diary_events"], "other_threshold_crossings": worst["other_threshold_crossings"]},
        "best_and_worst_day_note": "all 7 days had the same time in range and the same average glucose" if all_days_identical else None,
        "weekday_vs_weekend": weekday_vs_weekend,
        "stream_direction_table": stream_direction_table,
        "events_in_window": events_in_window,
        "recurring_in_window": recurring,
        "deltas": deltas,
    }
    flags = sorted({f for d in week_dates if d in day_records for f in day_records[d]["flags"]})
    # Anchors read the cleaned changes (questionable readings removed). `anchors_crossed_raw` is what they would have
    # said on the raw values; `anchors_suppressed` is the difference — crossings that existed only because of a bad reading.
    anchors_crossed = evaluate_anchors("week", effective_deltas(deltas), data.n_meds)
    anchors_crossed_raw = evaluate_anchors("week", {k: v for k, v in deltas.items() if k != "questionable_excluded"}, data.n_meds)
    record["reliable"], record["data_quality_flags"], record["anchors_crossed"] = w.reliable, flags, anchors_crossed
    record["anchors_crossed_raw"], record["anchors_suppressed"] = anchors_crossed_raw, [a for a in anchors_crossed_raw if a not in anchors_crossed]
    record["has_diary_event"] = len(events_in_window) > 0
    record["stream_change_table"] = stream_change_table  # window mean minus the previous window's mean, in the stream's own unit
    record["co_movement_candidates"] = st.candidates_from_directions(stream_direction_table, stream_change_table, strengths_w)
    record["aggregates"] = aggregates
    record["deltas_vs_cumulative"] = {lab: st.cumulative_delta(cur_w[lab], hist_w[lab], w.reliable) for lab in labels}
    record["confidence"] = st.confidence(w.reliable, w.completeness_pct)
    prior_week_dates = data.dates[prior_end_idx - 6 : prior_end_idx + 1] if prior_end_idx >= 6 else []
    prior_week_flags = [f for d in prior_week_dates for f in data._flags_by_date.get(d, [])]
    record["anchors_questionable"] = questionable_anchors(anchors_crossed, flags + prior_week_flags)
    record["data_quality_details"] = flag_details(flags) + flag_details(sorted(set(prior_week_flags)), "previous window")
    record["unusual_statuses"] = week_unusual_statuses(days)
    record["material_changes"] = material_changes_week(record, days, aggregates)
    record["quiet"] = not record["material_changes"]
    return {"record": record, "reliable": w.reliable, "flags": flags, "anchors_crossed": anchors_crossed, "anchors_questionable": record["anchors_questionable"],
            "prior_window_id": f"week_ENDING_{data.dates[prior_end_idx]}" if prior_end_idx >= 6 else None,
            "start_date": week_dates[0], "end_date": end_date}


# ---- month (30-day checkpoint) record ---------------------------------------------------------


def _delta_of_means(day_records: dict[str, dict], dates: list[str], prior_dates: list[str], section: str, key: str, ndigits: int) -> float | None:
    """mean(key over dates) - mean(key over prior_dates), using the day records' own values; None if either side has no data."""
    def mean_of(ds: list[str]) -> float | None:
        vals = [day_records[d]["record"][section][key] for d in ds if d in day_records and day_records[d]["record"][section].get(key) is not None]
        return statistics.fmean(vals) if vals else None
    cur, prev = mean_of(dates), mean_of(prior_dates) if prior_dates else None
    return round(cur - prev, ndigits) if cur is not None and prev is not None else None


def checkpoint_indices(n_dates: int) -> list[int]:
    idx = list(range(29, n_dates, 30))
    if not idx or idx[-1] != n_dates - 1:
        idx.append(n_dates - 1)  # always represent the most recent data, even if < 30 days since the last checkpoint
    return idx


def build_month_record(checkpoint_idx: int, prior_checkpoint_idx: int | None, data: MemoryData, day_records: dict[str, dict]) -> dict:
    checkpoint_date = data.dates[checkpoint_idx]
    cum_dates = data.dates[: checkpoint_idx + 1]
    cum_values = [v for d in cum_dates for _, v in data.glucose_by_date[d]]
    cumulative = _with_cleaned(_glucose_metrics(cum_values, EXPECTED_PER_DAY * len(cum_dates)), cum_dates, data, EXPECTED_PER_DAY * len(cum_dates))

    last30_dates = data.dates[max(0, checkpoint_idx - 29) : checkpoint_idx + 1]
    last30_values = [v for d in last30_dates for _, v in data.glucose_by_date[d]]
    last_30_days = _with_cleaned(_glucose_metrics(last30_values, EXPECTED_PER_DAY * len(last30_dates)), last30_dates, data, EXPECTED_PER_DAY * len(last30_dates))

    current_month = checkpoint_date[:7]
    months = sorted({d[:7] for d in cum_dates})
    monthly_trajectory = []
    for ym in months:
        month_dates = [d for d in cum_dates if d[:7] == ym]
        month_values = [v for d in month_dates for _, v in data.glucose_by_date[d]]
        recs = [day_records[d]["record"] for d in month_dates if d in day_records]
        diary_counts: dict[str, int] = defaultdict(int)
        for r in recs:
            for e in r["diary_events"]:
                diary_counts[e["category"]] += 1
        monthly_trajectory.append({
            "month": ym, "partial": ym == current_month,
            "glucose": _with_cleaned(_glucose_metrics(month_values, EXPECTED_PER_DAY * len(month_dates)), month_dates, data, EXPECTED_PER_DAY * len(month_dates)),
            "mean_sleep_hours": round(statistics.fmean([r["sleep"]["duration_hours"] for r in recs if r["sleep"]["duration_hours"] is not None]), 2) if any(r["sleep"]["duration_hours"] is not None for r in recs) else None,
            "mean_steps": round(statistics.fmean([r["activity"]["total_steps"] for r in recs if r["activity"]["total_steps"] is not None]), 1) if any(r["activity"]["total_steps"] is not None for r in recs) else None,
            "mean_adherence_pct": round(statistics.fmean([r["adherence"]["overall_pct"] for r in recs if r["adherence"]["overall_pct"] is not None]), 1) if any(r["adherence"]["overall_pct"] is not None for r in recs) else None,
            "diary_event_counts_by_category": dict(diary_counts),
        })

    lab_link = []
    for lab in data.hba1c:
        lab_date = lab["timestamp"][:10]
        if lab_date > checkpoint_date:
            continue
        window_start = (_dt(lab["timestamp"]) - timedelta(days=90)).strftime("%Y-%m-%d")
        pre_lab_values = [v for d in cum_dates if window_start <= d < lab_date for _, v in data.glucose_by_date[d]]
        lab_link.append({
            "lab_date": lab_date, "hba1c_pct": lab["value"], "hba1c_status": lab["status"],
            "cgm_gmi_pct_90d_prior": _glucose_metrics(pre_lab_values, EXPECTED_PER_DAY * 90)["gmi_pct"] if pre_lab_values else None,
        })
        lab_link[-1]["gap_hba1c_minus_gmi"] = round(lab["value"] - lab_link[-1]["cgm_gmi_pct_90d_prior"], 2) if lab_link[-1]["cgm_gmi_pct_90d_prior"] is not None else None

    completed = [m for m in monthly_trajectory if not m["partial"]] or monthly_trajectory
    first_m, latest_m = completed[0], completed[-1]
    domain_trends = {}
    for domain, key in (("sleep", "mean_sleep_hours"), ("steps", "mean_steps"), ("adherence", "mean_adherence_pct")):
        f_, l_ = first_m[key], latest_m[key]
        domain_trends[domain] = {"first_month": f_, "latest_month": l_, "delta_latest_minus_first": round(l_ - f_, 2) if f_ is not None and l_ is not None else None, "direction": _direction(l_, f_, DOMAIN_STREAM[domain])}
    resting_hr_by_month = {ym: round(statistics.fmean(vals), 1) if (vals := [day_records[d]["record"]["heart_rate"]["resting_period_mean"] for d in cum_dates if d[:7] == ym and d in day_records and day_records[d]["record"]["heart_rate"]["resting_period_mean"] is not None]) else None for ym in (first_m["month"], latest_m["month"])}
    f_, l_ = resting_hr_by_month[first_m["month"]], resting_hr_by_month[latest_m["month"]]
    domain_trends["resting_hr"] = {"first_month": f_, "latest_month": l_, "delta_latest_minus_first": round(l_ - f_, 2) if f_ is not None and l_ is not None else None, "direction": _direction(l_, f_, "resting_hr")}

    prior_cumulative = prior_last30 = None
    p_last30_dates: list[str] = []
    if prior_checkpoint_idx is not None:
        p_cum_dates = data.dates[: prior_checkpoint_idx + 1]
        prior_cumulative = _glucose_metrics([v for d in p_cum_dates for _, v in data.glucose_by_date[d]], EXPECTED_PER_DAY * len(p_cum_dates))
        p_last30_dates = data.dates[max(0, prior_checkpoint_idx - 29) : prior_checkpoint_idx + 1]
        prior_last30 = _glucose_metrics([v for d in p_last30_dates for _, v in data.glucose_by_date[d]], EXPECTED_PER_DAY * len(p_last30_dates))

    # HbA1c-vs-CGM gap for labs drawn inside this checkpoint's own 30 days (a lab is judged once, at the
    # checkpoint that follows it, not at every later one). Largest absolute gap if there are several.
    new_labs = [x for x in lab_link if last30_dates[0] <= x["lab_date"] <= checkpoint_date and x["gap_hba1c_minus_gmi"] is not None]
    lab_cgm_gap = max((x["gap_hba1c_minus_gmi"] for x in new_labs), key=abs) if new_labs else None

    deltas = {
        "glucose_tir_pct": _glucose_deltas(last_30_days, prior_last30)["delta_tir_pct"],
        "glucose_cv_pct": _glucose_deltas(last_30_days, prior_last30)["delta_cv_pct"],
        "glucose_gmi_pct": _glucose_deltas(last_30_days, prior_last30)["delta_gmi_pct"],
        "glucose_severe_total_curr": last_30_days["tar_severe_pct"] + last_30_days["tbr_severe_pct"],
        "glucose_severe_total_prior": (prior_last30["tar_severe_pct"] + prior_last30["tbr_severe_pct"]) if prior_last30 else None,
        "cumulative_mean": _glucose_deltas(cumulative, prior_cumulative)["delta_mean"],
        # Change in the trailing-30-day mean vs the previous checkpoint's trailing-30-day mean (same basis as the
        # glucose deltas above). domain_trends (first month vs latest month) is a separate, long-run view.
        "sleep_hours": _delta_of_means(day_records, last30_dates, p_last30_dates, "sleep", "duration_hours", 2),
        "resting_hr_mean": _delta_of_means(day_records, last30_dates, p_last30_dates, "heart_rate", "resting_period_mean", 2),
        "adherence_overall_pct": _delta_of_means(day_records, last30_dates, p_last30_dates, "adherence", "overall_pct", 1),
        "lab_cgm_gap": lab_cgm_gap,
    }

    _deltas_with_cleaned(deltas, last30_dates, p_last30_dates, data, EXPECTED_PER_DAY * len(last30_dates), EXPECTED_PER_DAY * max(len(p_last30_dates), 1))
    record = {
        "window_id": f"month_ENDING_{checkpoint_date}", "tier": "month", "start_date": cum_dates[0], "end_date": checkpoint_date,
        "cumulative": cumulative, "last_30_days": last_30_days, "monthly_trajectory": monthly_trajectory,
        "lab_link": lab_link, "domain_trends": domain_trends, "deltas": deltas,
    }
    flags = sorted({f for d in cum_dates if d in day_records for f in day_records[d]["flags"]})
    # Anchors read the cleaned changes (questionable readings removed). `anchors_crossed_raw` is what they would have
    # said on the raw values; `anchors_suppressed` is the difference — crossings that existed only because of a bad reading.
    anchors_crossed = evaluate_anchors("month", effective_deltas(deltas), data.n_meds)
    anchors_crossed_raw = evaluate_anchors("month", {k: v for k, v in deltas.items() if k != "questionable_excluded"}, data.n_meds)
    reliable = last_30_days["completeness_pct"] >= 70
    record["reliable"], record["data_quality_flags"], record["anchors_crossed"] = reliable, flags, anchors_crossed
    record["anchors_crossed_raw"], record["anchors_suppressed"] = anchors_crossed_raw, [a for a in anchors_crossed_raw if a not in anchors_crossed]
    record["confidence"] = st.confidence(reliable, last_30_days["completeness_pct"])
    record["has_diary_event"] = any(day_records[d]["record"]["diary_events"] for d in cum_dates if d in day_records)
    p_last30 = data.dates[max(0, prior_checkpoint_idx - 29) : prior_checkpoint_idx + 1] if prior_checkpoint_idx is not None else []
    last30_flags = sorted({f for d in last30_dates for f in data._flags_by_date.get(d, [])})
    prior30_flags = sorted({f for d in p_last30 for f in data._flags_by_date.get(d, [])})
    record["anchors_questionable"] = questionable_anchors(anchors_crossed, last30_flags + prior30_flags)
    record["data_quality_details"] = flag_details(last30_flags) + flag_details(prior30_flags, "previous window")
    last30_diary = sum(len(day_records[d]["record"]["diary_events"]) for d in last30_dates if d in day_records)
    record["material_changes"] = material_changes_month(record, last30_flags, new_labs, last30_diary)
    record["quiet"] = False  # a checkpoint is a long-run summary, never a "quiet" short entry
    prior_window_id = f"month_ENDING_{data.dates[prior_checkpoint_idx]}" if prior_checkpoint_idx is not None else None
    return {"record": record, "reliable": reliable, "flags": flags, "anchors_crossed": anchors_crossed, "anchors_questionable": record["anchors_questionable"],
            "prior_window_id": prior_window_id, "start_date": cum_dates[0], "end_date": checkpoint_date}


# ---- orchestrator -----------------------------------------------------------------------------


def build_all_records(store: PersonalDataStore, steps_by_hour: dict[str, float]) -> dict:
    """Builds every day/week/month record_json (no LLM). Returns {'day': {...}, 'week': {...},
    'month': [...]} keyed/ordered for the caller to insert and, later, send to the LLM step."""
    data = MemoryData(store)

    day_records: dict[str, dict] = {}
    for date in data.dates:
        rec = build_day_record(date, data, steps_by_hour)
        if rec:
            day_records[date] = rec

    week_records: dict[str, dict] = {}
    for date in data.dates:
        rec = build_week_record(date, data, day_records)
        if rec:
            week_records[date] = rec

    month_records: list[dict] = []
    idxs = checkpoint_indices(len(data.dates))
    for pos, ci in enumerate(idxs):
        prior_ci = idxs[pos - 1] if pos > 0 else None
        month_records.append(build_month_record(ci, prior_ci, data, day_records))

    return {"day": day_records, "week": week_records, "month": month_records}
