"""Code-rendered facts: every list, number, date, quote and caveat in a memory entry is written here, not by the model.

The model writes only a headline, a few "what stood out" sentences and a notable reason (nodes/memory_writer.py).
Everything below is deterministic, built from the stored record, and generic: units, plain names and wording
come from the stream registry, the plain-label tables and patient_config, never from per-patient branches.

`render_window(record)` returns sections, each a list of plain-English lines:
  material_changes  every deviation the code found (the guarantee: anything in record["material_changes"] is
                    rendered here — tests/test_rendering.py checks every kind)
  numbers           the window's own values, with questionable readings removed
  what_changed      direction and amount vs the previous window (cleaned), for every stream that moved
  co_movement       the strongest same/opposite co-movers, each with direction and amount
  trajectory        by time of day (day), day by day (week), month by month (month)
  caveats           what was removed or missing, and what the numbers would be with it
  steady            streams that did not move
"""

from dataclasses import dataclass
from typing import Any

from v0_code.logic.data_quality import effective_deltas
from v0_code.logic.record_view import plain_value
from v0_code.logic.registry import numeric_streams

TOP_CO_MOVERS = 4         # strongest same/opposite co-movers rendered
TOP_CO_MOVERS_QUIET = 2   # a quiet window renders at most this many

STATUS_WORDS = {
    "high": "above the reference range", "low": "below the reference range",
    "borderline_high": "slightly above the reference range", "borderline_low": "slightly below the reference range",
    "normal": "within the reference range",
}


def fmt(v: Any, nd: int = 2) -> str:
    if v is None:
        return "not available"
    if isinstance(v, float):
        return (f"{v:.{nd}f}".rstrip("0").rstrip(".")) or "0"
    return str(v)


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def measure_name(raw: str) -> str:
    """Plain name for a biomarker/stream id ('step_count' -> 'steps'; unknown ids lose their underscores)."""
    return plain_value(raw)


def phrase(change: float | None, unit: str = "", count_like: bool = False) -> str:
    """'down 1.82 hours' / '3 fewer strained periods of the day' — the wording of a change, without its label."""
    if change is None:
        return "not available"
    if change == 0:
        return "no change"
    n = fmt(abs(change))
    if count_like:
        return f"{n} {'more' if change > 0 else 'fewer'} {unit}"
    return f"{'up' if change > 0 else 'down'} {n}{(' ' + unit) if unit else ''}"


def move(label: str, change: float | None, unit: str = "", count_like: bool = False) -> str:
    """'Sleep: down 1.82 hours' / 'Mood: 3 fewer strained periods of the day'."""
    return f"{_cap(label)}: {phrase(change, unit, count_like)}"


def val(v: Any, unit: str = "") -> str:
    """A value with its unit, or 'not available' with no dangling unit."""
    return "not available" if v is None else f"{fmt(v)}{(' ' + unit) if unit else ''}"


def days(n: int) -> str:
    return f"{n} day" + ("" if n == 1 else "s")


# ---- anchors: what each one measures, so a crossing is written with its numbers ----------------------------
# name -> (label, key in the effective deltas, unit, comparison noun)
ANCHOR_SOURCE: dict[str, tuple[str, str, str]] = {
    "glucose_TIR_change_points": ("time in range", "glucose_tir_pct", "percentage points"),
    "glucose_CV_change_points": ("variability", "glucose_cv_pct", "percentage points"),
    "glucose_GMI_change": ("GMI", "glucose_gmi_pct", "points"),
    "sleep_hours_change": ("sleep", "sleep_hours", "hours"),
    "resting_hr_change_bpm": ("heart rate at rest", "resting_hr_mean", "bpm"),
    "steps_change_abs": ("steps", "activity_steps", "steps"),
    "steps_mean_change_abs": ("average steps per day", "activity_steps_mean", "steps"),
    "adherence_pct_change": ("medication adherence", "adherence_overall_pct", "percentage points"),
}
_VS = {"day": "the previous day", "week": "the previous week", "month": "the previous checkpoint"}


def _anchor_line(name: str, record: dict) -> str:
    eff = effective_deltas(record.get("deltas", {}))
    vs = _VS.get(record["tier"], "the previous window")
    if name in ANCHOR_SOURCE:
        label, key, unit = ANCHOR_SOURCE[name]
        return f"Large change: {label} {phrase(eff.get(key), unit)} vs {vs}."
    if name == "adherence_meds_changed":
        return f"Large change: {fmt(eff.get('adherence_meds_changed_count'))} medicines changed status vs {vs}."
    if name == "severe_range_appeared_or_cleared":
        return (f"Large change: severe high or low glucose time {fmt(eff.get('glucose_severe_total_curr'))}% "
                f"(was {fmt(eff.get('glucose_severe_total_prior'))}% in {vs}).")
    if name == "lab_cgm_discordance":
        return f"Large change: lab HbA1c and the sensor-estimated GMI are {fmt(abs(eff.get('lab_cgm_gap') or 0))} points apart."
    return f"Large change: {plain_value(name)}."


def _reading_reason(value: float) -> str:
    if value == 65.0:
        return "it looks like a sensor clipping error (the same stuck value)"
    if value > 400:
        return "it looks like a sensor error (above 400 mg/dL)"
    return "it looks like a sensor error (a jump that fast is not physiological)"


def _flag_line(flag: str) -> str:
    parts = flag.split(":")
    if parts[0] == "gap_hours":
        return f"Glucose readings had a gap of {parts[1]} hours."
    if parts[0] == "low_completeness":
        return f"{_cap(measure_name(parts[1]))} data was incomplete ({parts[2]}% of the expected readings)."
    return flag


def _material_lines(item: dict, record: dict) -> list[str]:
    k = item["kind"]
    if k == "anchor_crossed":
        return [_anchor_line(item["detail"], record)]
    if k == "missed_dose":
        return [f"Missed dose: {measure_name(item['medicine'])}."]
    if k == "missed_doses":
        return [f"Missed doses: {measure_name(item['medicine'])}, {item['missed']} of {item['of']} days."]
    if k == "unusual_status":
        where = f" on {item['days']} of 7 days" if "days" in item else ""
        return [f"{_cap(measure_name(item['measure']))} {STATUS_WORDS.get(item['status'], item['status'])}{where} (unusual for her)."]
    if k == "data_quality":
        return [_flag_line(item["flag"])]
    if k == "questionable_reading":
        t = item["time"].replace("T", " ")[:16]
        return [f"Reading removed: {fmt(item['value'])} mg/dL at {t}, because {_reading_reason(item['value'])}."]
    if k == "lab_result":
        gap = item.get("gap_hba1c_minus_gmi")
        tail = f"; {fmt(abs(gap))} points {'above' if gap > 0 else 'below'} the sensor-estimated GMI" if gap is not None else ""
        return [f"Lab HbA1c {fmt(item['hba1c_pct'])}% on {item['lab_date']}{tail}."]
    if k == "diary_events":  # the events themselves are added below (they need the record, not the item)
        return []
    return [str(item)]


def _diary_lines(record: dict) -> list[str]:
    events = record.get("events_in_window")
    if events is None:  # day record
        events = [{"date": record.get("date"), **e} for e in record.get("diary_events", [])]
    out = []
    for e in events:
        note = f" ({e['severity_note']})" if e.get("severity_note") else ""
        out.append(f"Diary, {e.get('date')} [{plain_value(e.get('category') or 'event')}]: \"{e.get('text')}\"{note}")
    return out


def render_material(record: dict) -> list[str]:
    """One or more lines for every item in record["material_changes"]; diary events appear verbatim with their date."""
    lines: list[str] = []
    for item in record.get("material_changes", []):
        lines += _material_lines(item, record)
        if item["kind"] == "diary_events":
            lines += _diary_lines(record) or [f"Diary events in the last 30 days: {item['count']}."]
    return lines


# ---- numbers ----------------------------------------------------------------------------------------------

def effective_metrics(section: dict) -> dict:
    """A glucose metrics dict with questionable readings removed (the raw values stay in the record)."""
    q = section.get("questionable_excluded")
    out = {k: v for k, v in section.items() if k != "questionable_excluded"}
    if q:
        out.update(q["metrics_without_them"])
    return out


def _glucose_line(g: dict, prefix: str = "Glucose") -> str:
    m = effective_metrics(g)
    return (f"{prefix}: average {fmt(m['mean'])} mg/dL, GMI {fmt(m['gmi_pct'])}%, time in range {fmt(m['tir_pct'])}%, "
            f"above range {fmt(m['tar_pct'])}% (above 250: {fmt(m['tar_severe_pct'])}%), below range {fmt(m['tbr_pct'])}% "
            f"(below 54: {fmt(m['tbr_severe_pct'])}%), variability {fmt(m['cv_pct'])}%, "
            f"{(str(m['n_readings']) + ' readings, ') if 'n_readings' in m else ''}{fmt(m['completeness_pct'])}% of the expected readings.")


def _day_numbers(r: dict) -> list[str]:
    out = [_glucose_line(r["glucose"])]
    sl, ac, hr, lf = r["sleep"], r["activity"], r["heart_rate"], r["lifestyle"]
    out.append(f"Sleep: {val(sl['duration_hours'], 'hours')}, quality {sl.get('quality') or 'not recorded'}.")
    out.append(f"Activity: steps {val(ac['total_steps'])}, sedentary time {val(ac['sedentary_minutes'], 'minutes')}.")
    out.append(f"Heart rate: average {val(hr['continuous_mean'], 'bpm')}, average at rest {val(hr['resting_period_mean'], 'bpm')}, daily resting value {val(hr['resting_heart_rate_daily'], 'bpm')}.")
    for bp in r.get("blood_pressure", []):
        out.append(f"Blood pressure: {fmt(bp['systolic'])}/{fmt(bp['diastolic'])} at {bp['timestamp'][11:16]}.")
    meds = r["adherence"]["per_medication"]
    out.append("Medicines: " + (", ".join(f"{measure_name(m)} {s}" for m, s in meds.items()) or "none recorded") + f" ({fmt(r['adherence']['overall_pct'])}% taken).")
    if r.get("mood"):
        out.append("Mood: " + ", ".join(f"{b} {plain_value(m['category'])}" for b, m in r["mood"].items()) + ".")
    out.append(f"Lifestyle: hydration {val(lf['hydration_ml'], 'mL')}, screen time {val(lf['screen_time_hours'], 'hours')}, location {plain_value(lf['location'] or 'not recorded')}.")
    return out


def _agg_mean(agg: dict, key: str) -> str:
    a = agg.get(key) or {}
    return f"average {fmt(a.get('mean'))}" if a.get("mean") is not None else "not available"


def _week_numbers(r: dict) -> list[str]:
    out = [_glucose_line(r["glucose"])]
    a = r["aggregates"]
    st = a.get("step_count", {})
    out.append(f"Sleep: {_agg_mean(a, 'sleep_duration')} hours per day. Steps: average {fmt(st.get('mean_per_day'))} per day ({st.get('n_days')} days with data). "
               f"Sedentary: {_agg_mean(a, 'sedentary_time')} minutes per day.")
    out.append(f"Heart rate: {_agg_mean(a, 'continuous_heart_rate')} bpm, at rest {_agg_mean(a, 'resting_period_heart_rate')} bpm, daily resting value {_agg_mean(a, 'resting_heart_rate')} bpm.")
    ad = a.get("medication_adherence", {})
    out.append(f"Medicines: {fmt(ad.get('overall_pct'))}% taken (" + ", ".join(f"{measure_name(m)} {v['taken']} of {v['expected']}" for m, v in sorted(ad.get("per_medication", {}).items())) + ").")
    mood = a.get("mood_state", {})
    if mood:
        out.append("Mood by time of day: " + "; ".join(f"{b}: " + ", ".join(f"{plain_value(c)} {n}" for c, n in sorted(v["counts"].items())) for b, v in mood.items() if isinstance(v, dict)) + ".")
    meals = a.get("meal_events", {})
    if meals:
        peak_mean, peak_max = meals.get("post_meal_peak_mean"), meals.get("post_meal_peak_max")
        q = meals.get("questionable_excluded")
        if q:
            peak_mean, peak_max = q["metrics_without_them"]["post_meal_peak_mean"], q["metrics_without_them"]["post_meal_peak_max"]
        out.append(f"Meals: {sum(meals.get('meals_by_label', {}).values())} logged; peak glucose after meals averaged {fmt(peak_mean)} mg/dL, highest {fmt(peak_max)} mg/dL.")
    loc = a.get("location", {}).get("counts")
    if loc:
        out.append("Location: " + ", ".join(f"{plain_value(k)} {days(n)}" for k, n in sorted(loc.items())) + ".")
    return out


def _month_numbers(r: dict) -> list[str]:
    out = [_glucose_line(r["cumulative"], "Whole history so far"), _glucose_line(r["last_30_days"], "Last 30 days")]
    for lab in r.get("lab_link", []):
        gap = lab.get("gap_hba1c_minus_gmi")
        gmi = lab.get("cgm_gmi_pct_90d_prior")
        out.append(f"Lab {lab['lab_date']}: HbA1c {fmt(lab['hba1c_pct'])}%; sensor-estimated GMI over the 90 days before "
                   + (f"{fmt(gmi)}%" + (f" (gap {fmt(gap)} points)." if gap is not None else ".") if gmi is not None else "not available (no sensor data that far back)."))
    return out


# ---- what changed / co-movement ---------------------------------------------------------------------------------

_DOMAIN_RENDER = {"sleep": ("sleep", "hours"), "steps": ("steps per day", "steps"), "adherence": ("medication adherence", "percentage points"),
                  "resting_hr": ("heart rate at rest", "bpm")}
_GLUCOSE_METRIC_DELTAS = (("time in range", "glucose_tir_pct", "percentage points"), ("variability", "glucose_cv_pct", "percentage points"),
                          ("GMI", "glucose_gmi_pct", "points"))


def _what_changed(r: dict) -> list[str]:
    eff = effective_deltas(r.get("deltas", {}))
    out: list[str] = []
    if r["tier"] == "month":
        for label, key, unit in _GLUCOSE_METRIC_DELTAS + (("sleep", "sleep_hours", "hours"), ("heart rate at rest", "resting_hr_mean", "bpm"),
                                                           ("medication adherence", "adherence_overall_pct", "percentage points")):
            if eff.get(key) is not None:
                out.append(move(label, eff[key], unit) + f" vs {_VS['month']}")
        for dom, t in (r.get("domain_trends") or {}).items():
            label, unit = _DOMAIN_RENDER.get(dom, (plain_value(dom), ""))
            if t.get("delta_latest_minus_first") is not None:
                out.append(move(f"{label} since the first month", t["delta_latest_minus_first"], unit))
        return out
    ch, dirs = r["stream_change_table"], r["stream_direction_table"]
    for s in numeric_streams():
        if dirs.get(s.label) in ("up", "down"):
            c = eff.get("glucose_mean", ch[s.label]) if s.label == "glucose" and "glucose_mean" in eff else ch[s.label]
            avg = " on average" if s.count_like and r["tier"] == "week" else ""
            out.append(move(s.label if s.label != "glucose" else "average glucose", c, s.unit, s.count_like) + avg + f" vs {_VS[r['tier']]}")
    for label, key, unit in _GLUCOSE_METRIC_DELTAS:
        if eff.get(key) is not None:
            out.append(move(label, eff[key], unit) + f" vs {_VS[r['tier']]}")
    return out


def _steady(r: dict) -> list[str]:
    dirs = r.get("stream_direction_table") or {}
    return [lab for lab, d in dirs.items() if d == "flat"]


def _co_movement(r: dict, quiet: bool) -> list[str]:
    cand = r.get("co_movement_candidates")
    if not cand:
        return []
    from v0_code.logic.registry import numeric_streams as ns
    count_like = {s.label for s in ns() if s.count_like}
    g_dir, g_chg = cand["glucose_direction"], cand.get("glucose_change")
    out = []
    for c in cand["ranked"][: TOP_CO_MOVERS_QUIET if quiet else TOP_CO_MOVERS]:
        rel = "the same way as" if c["relation"] == "same" else "the opposite way to"
        signed = c["amount"] if c["direction"] == "up" else -c["amount"]
        avg = " on average" if c["name"] in count_like and r["tier"] == "week" else ""
        out.append(f"{move(c['name'], signed, c['unit'], c['name'] in count_like)}{avg}, {rel} glucose ({g_dir} {fmt(abs(g_chg))} mg/dL)")
    return out


# ---- trajectory -------------------------------------------------------------------------------------------------------

def _day_trajectory(r: dict) -> list[str]:
    out = []
    for name, v in r["glucose_by_period"].items():
        out.append(f"{_cap(name)}: " + ("no readings." if v["mean"] is None else f"average {fmt(v['mean'])} mg/dL, highest {fmt(v['max'])} mg/dL, {fmt(v['tir_pct'])}% in range."))
    for m in r.get("post_meal", []):
        peak = m["questionable_excluded"]["metrics_without_them"]["peak_glucose"] if m.get("questionable_excluded") else m["peak_glucose"]
        out.append(f"After {plain_value(m['meal_label'])} (\"{m['food_description']}\"): glucose {fmt(m['pre_meal_glucose'])} before, peak {fmt(peak)} mg/dL {m['minutes_to_peak']} minutes after.")
    return out


def _week_trajectory(r: dict) -> list[str]:
    best = (r.get("best_day") or {}).get("date")
    worst = (r.get("worst_day") or {}).get("date")
    out = []
    for d in r["daily_trajectory"]:
        tags = []
        if d["date"] == best:
            tags.append("best day")
        if d["date"] == worst:
            tags.append("worst day")
        if d.get("missed_medicines"):
            tags.append("missed " + ", ".join(measure_name(m) for m in d["missed_medicines"]))
        if d.get("diary_event_count"):
            tags.append(f"{d['diary_event_count']} diary event(s)")
        out.append(f"{d['date']}: average glucose {fmt(d['glucose_mean'])} mg/dL, time in range {fmt(d['tir_pct'])}%, sleep {fmt(d['sleep_hours'])} hours, "
                   f"steps {fmt(d['steps'])}, medicines taken {fmt(d['adherence_pct'])}%, worst mood {plain_value(d['worst_mood_category'] or 'none recorded')}"
                   + (f" [{'; '.join(tags)}]" if tags else ""))
    if r.get("best_and_worst_day_note"):
        out.append(_cap(r["best_and_worst_day_note"]) + ".")
    return out


def _month_trajectory(r: dict) -> list[str]:
    out = []
    for m in r["monthly_trajectory"]:
        g = effective_metrics(m["glucose"])
        out.append(f"{m['month']}{' (partial)' if m['partial'] else ''}: average glucose {fmt(g['mean'])} mg/dL, time in range {fmt(g['tir_pct'])}%, "
                   f"sleep {fmt(m['mean_sleep_hours'])} hours, steps {fmt(m['mean_steps'])}, medicines taken {fmt(m['mean_adherence_pct'])}%.")
    return out


# ---- caveats ---------------------------------------------------------------------------------------------------------------

_CAVEAT_METRICS = {
    "mean": ("average glucose", "mg/dL"), "gmi_pct": ("GMI", "%"), "tir_pct": ("time in range", "%"), "tar_pct": ("time above range", "%"),
    "tar_severe_pct": ("time above 250", "%"), "tbr_pct": ("time below range", "%"), "tbr_severe_pct": ("time below 54", "%"),
    "cv_pct": ("variability", "%"), "max_value": ("highest glucose", "mg/dL"), "min_value": ("lowest glucose", "mg/dL"),
    "glucose_cv_pct": ("change in variability", "points"), "glucose_tir_pct": ("change in time in range", "points"),
    "glucose_gmi_pct": ("change in GMI", "points"), "glucose_mean": ("change in average glucose", "mg/dL"),
    "glucose_severe_total_curr": ("severe time", "%"), "glucose_severe_total_prior": ("severe time in the previous window", "%"),
    "post_meal_peak_mean": ("average peak after meals", "mg/dL"), "post_meal_peak_max": ("highest peak after meals", "mg/dL"),
    "peak_glucose": ("peak after the meal", "mg/dL"), "rise": ("rise after the meal", "mg/dL"),
}


def _would_be(q: dict) -> str:
    return ", ".join(f"{_CAVEAT_METRICS.get(k, (k, ''))[0]} {fmt(v)}{_CAVEAT_METRICS.get(k, ('', ''))[1] and (' ' + _CAVEAT_METRICS[k][1])}" for k, v in q["metrics_with_them"].items())


def _caveats(r: dict) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def walk(node: Any, where: str) -> None:
        if isinstance(node, dict):
            q = node.get("questionable_excluded")
            if q and q.get("metrics_with_them"):
                line = (f"The values above exclude {q['n_excluded']} questionable reading(s) "
                        f"({', '.join(fmt(v) for v in q['excluded_values'])}); with them included: {_would_be(q)}.")
                if line not in seen:
                    seen.add(line)
                    out.append(line)
            for k, v in node.items():
                if k != "questionable_excluded":
                    walk(v, k)
        elif isinstance(node, list):
            for x in node:
                walk(x, where)

    walk({k: v for k, v in r.items() if k in ("glucose", "deltas", "aggregates", "post_meal", "last_30_days")}, "")
    for a in r.get("anchors_suppressed", []):
        out.append(f"A large change ({plain_value(a)}) was ignored: it existed only because of a removed reading.")
    if not r.get("reliable", True):
        out.append("This window is not clinically reliable (too little glucose data, or too early in the record).")
    unavailable = [lab for lab, d in (r.get("stream_direction_table") or {}).items() if d == "insufficient_data"]
    if unavailable:
        out.append("Not enough history to compare: " + ", ".join(unavailable) + ".")
    return out


# ---- direction tags ----------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Tag:
    term: str        # the measure's name as the model will write it: "average glucose", "sedentary time", ...
    direction: str   # up | down | flat | insufficient
    text: str        # "sedentary time: up 49.71 minutes" / "average glucose: flat"


def _tag(term: str, direction: str, change: float | None, unit: str = "", count_like: bool = False, qualifier: str = "") -> Tag:
    if direction == "insufficient":
        body = "not enough data"
    elif direction == "flat":
        body = "flat"
    else:
        body = phrase(change, unit, count_like)
    return Tag(term, direction, f"{term}: {body}{qualifier}")


def _sign(c: float | None) -> str:
    return "insufficient" if c is None else ("flat" if c == 0 else ("up" if c > 0 else "down"))


_FALLBACK_DELTA = {"sleep": "sleep_hours", "resting heart rate": "resting_hr_mean", "medication adherence": "adherence_overall_pct", "steps": "activity_steps"}
_FALLBACK_DELTA_ALT = {"steps": "activity_steps_mean"}


def direction_tags(record: dict) -> list[Tag]:
    """One tag per key measure — the ONLY source for an up / down / flat claim in the model's headline and sentences.
    Day and week: direction vs the previous window from the code's own flat bands. Month: vs the previous checkpoint, plus
    the long-run trend since the first month (a measure may then carry two tags; a claim that matches either is fine)."""
    eff = effective_deltas(record.get("deltas", {}))
    tags: list[Tag] = []
    if record["tier"] == "month":
        vs = " (vs the previous checkpoint)"
        for term, key, unit in (("time in range", "glucose_tir_pct", "percentage points"), ("variability", "glucose_cv_pct", "percentage points"),
                                ("GMI", "glucose_gmi_pct", "points"), ("sleep", "sleep_hours", "hours"),
                                ("resting heart rate", "resting_hr_mean", "bpm"), ("medication adherence", "adherence_overall_pct", "percentage points")):
            c = eff.get(key)
            tags.append(_tag(term, _sign(c), c, unit, qualifier=vs))
        for dom, t in (record.get("domain_trends") or {}).items():
            term, unit = {"sleep": ("sleep", "hours"), "steps": ("steps", "steps"), "adherence": ("medication adherence", "percentage points"),
                          "resting_hr": ("resting heart rate", "bpm")}.get(dom, (dom, ""))
            c = t.get("delta_latest_minus_first")
            tags.append(_tag(term, _sign(c), c, unit, qualifier=" (since the first month)"))
        return tags
    dirs, ch = record["stream_direction_table"], record["stream_change_table"]
    for s in numeric_streams():
        d = dirs.get(s.label, "insufficient")
        d = "insufficient" if d == "insufficient_data" else d
        if s.label == "glucose":
            c = eff.get("glucose_mean", ch.get("glucose"))
            tags.append(_tag("average glucose", d, c, "mg/dL"))
            continue
        c, qualifier = ch.get(s.label), ""
        if d == "insufficient":  # too little history for a flat band, but the anchors/material lines may still show a change: stay consistent with them
            key = _FALLBACK_DELTA.get(s.label)
            fallback = eff.get(key) if key and key in eff else (eff.get(_FALLBACK_DELTA_ALT.get(s.label, "")))
            if fallback is not None:
                d, c, qualifier = _sign(fallback), fallback, " (early in the record: no flat band yet)"
        tags.append(_tag(s.label, d, c, s.unit, s.count_like, qualifier))
    for term, key, unit in _GLUCOSE_METRIC_DELTAS:
        c = eff.get(key)
        tags.append(_tag(term, _sign(c), c, unit))
    return tags


# ---- entry point -----------------------------------------------------------------------------------------------------------------

def render_window(record: dict) -> dict[str, list[str]]:
    tier = record["tier"]
    quiet = bool(record.get("quiet"))
    numbers = {"day": _day_numbers, "week": _week_numbers, "month": _month_numbers}[tier](record)
    trajectory = {"day": _day_trajectory, "week": _week_trajectory, "month": _month_trajectory}[tier](record)
    return {
        "material_changes": render_material(record),
        "numbers": numbers,
        "what_changed": _what_changed(record),
        "co_movement": _co_movement(record, quiet),
        "trajectory": trajectory,
        "caveats": _caveats(record),
        "steady": _steady(record),
        "direction_tags": [t.text for t in direction_tags(record)],
    }


SECTION_TITLES = {
    "material_changes": "THINGS THAT DEVIATED", "numbers": "NUMBERS", "what_changed": "WHAT CHANGED vs the previous window",
    "co_movement": "MOVED TOGETHER WITH GLUCOSE", "trajectory": "TRAJECTORY", "caveats": "CAVEATS", "steady": "STEADY (no meaningful change)",
    "direction_tags": "DIRECTION TAGS (the only source for any up / down / flat claim)",
}


def render_text(rendered: dict[str, list[str]]) -> str:
    """The rendered sections as the plain text the model reads (and a doctor could)."""
    blocks = []
    for key, title in SECTION_TITLES.items():
        lines = rendered.get(key) or []
        blocks.append(f"{title}:\n" + ("\n".join(f"- {x}" for x in lines) if lines else "- none"))
    return "\n\n".join(blocks)
