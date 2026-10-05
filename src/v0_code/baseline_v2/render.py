"""Everything a human reads, written by code (spec rule 1: code writes numbers, dates, quotes, lists, caveats, deviation lists, notable reason).

`deviation_text` is the rendered plain-language block stored with every window; the code lines ("Not enough history yet to compare.",
"Nothing deviated from her usual.") are templates. Nothing here calls a model.
"""

import re
from decimal import ROUND_HALF_UP, Decimal

from v0_code.baseline_v2.anchors import ANCHOR_STREAM, SOURCE
from v0_code.baseline_v2.config import Config

STATUS_WORDS = {"high": "above the reference range", "low": "below the reference range", "borderline_high": "slightly above the reference range",
                "borderline_low": "slightly below the reference range", "normal": "within the reference range"}


# plain words and units for the glucose metrics shown in a caveat ("what the numbers would have been with the removed reading")
METRIC_WORDS = {"mean": ("average glucose", "mg/dL"), "gmi_pct": ("GMI", "%"), "tir_pct": ("time in range", "%"), "tar_pct": ("time above range", "%"),
                "tar_severe_pct": ("time above 250", "%"), "tbr_pct": ("time below range", "%"), "tbr_severe_pct": ("time below 54", "%"), "cv_pct": ("variability", "%"),
                "min_value": ("lowest glucose", "mg/dL"), "max_value": ("highest glucose", "mg/dL"), "post_meal_peak_max": ("highest peak after meals", "mg/dL")}


def fmt(v, nd: int = 2) -> str:
    if v is None:
        return "not available"
    if isinstance(v, float):
        return f"{v:.{nd}f}".rstrip("0").rstrip(".") or "0"
    return str(v)


def status_suffix(status: str | None) -> str:
    """Borderline and abnormal statuses are always SHOWN next to the value in the numbers, whether or not they count as a deviation."""
    return f" ({STATUS_WORDS[status]})" if status and status != "normal" and status in STATUS_WORDS else ""


DEFAULT_WHOLE_NUMBER_UNITS = ("steps", "mL", "minutes")


def fmt_unit(v, unit: str, cfg: Config | None = None) -> str:
    """A number in its unit's precision: units listed in config `rendering.whole_number_units` (steps, mL, minutes) print as whole numbers
    (half rounds up); every other unit keeps up to two decimals."""
    whole = cfg.whole_number_units if cfg is not None else DEFAULT_WHOLE_NUMBER_UNITS
    if v is not None and unit in whole:
        d = Decimal(str(v))
        n = int(abs(d).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        return str(-n if d < 0 and n else n)
    return fmt(v)


def phrase(delta: float | None, unit: str, count_like: bool = False, cfg: Config | None = None) -> str:
    """A change in words. A count of periods is "N more" / "N fewer" (its label already names the periods); everything else "up/down N unit"."""
    if delta is None:
        return "not available"
    if delta == 0:
        return "no change"
    n = fmt_unit(abs(delta), unit, cfg)
    if count_like:
        return f"{n} {'more' if delta > 0 else 'fewer'}"
    return f"{'up' if delta > 0 else 'down'} {n}{(' ' + unit) if unit else ''}"


EARLY_LINE = "Not enough history yet to compare."


def code_line(cfg: Config, status: str) -> str:
    return EARLY_LINE if status == "code_line_early" else f"Nothing deviated from {cfg.possessive} usual."


# ---- which material items matter most (for the code lines that stand in for a gist) -------------------------------------------------------------

def diary_severity_rank(cfg: Config, note: str | None) -> int:
    """0 = most severe. The configured severity keywords are searched in the entry's note (most severe present wins); a note with none of them
    (or no note) is unranked and sorts after every ranked one."""
    order = cfg.diary_severity_order
    text = (note or "").lower()
    hits = [i for i, kw in enumerate(order) if re.search(rf"\b{re.escape(kw.lower())}\b", text)]
    return min(hits) if hits else len(order)


_KIND_PRIORITY = {"anchor_crossed": 0, "diary_event": 1, "diary_summary": 1, "missed_dose": 2, "large_change": 3, "status_worse_than_usual": 4}


def _priority_key(cfg: Config, indexed: tuple[int, dict]):
    i, item = indexed
    k = item["kind"]
    sev = diary_severity_rank(cfg, item.get("severity_note")) if k == "diary_event" else (len(cfg.diary_severity_order) + 1 if k == "diary_summary" else 0)
    return (_KIND_PRIORITY.get(k, 9), sev, i)


def top_material_lines(cfg: Config, row: dict, n: int = 2) -> list[str]:
    """The n most important material items as plain sentences: anchors crossed, diary events (most severe first), missed doses, large
    changes, status deviations, then everything else; ties keep the order the items were built in."""
    ranked = sorted(enumerate(row["material_changes"]), key=lambda x: _priority_key(cfg, x))
    return [_material_line(cfg, item, row["deltas_clean"], row["tags"]) for _, item in ranked[:n]]


def _as_sentence(line: str) -> str:
    """A material line ends with its own full stop, except a diary line, which ends with the quote or the severity note."""
    return line if line.endswith((".", "!", "?")) else line + "."


def early_code_line(cfg: Config, row: dict) -> str:
    return " ".join([EARLY_LINE, *map(_as_sentence, top_material_lines(cfg, row, 2))])


def priority_lines(cfg: Config, row: dict) -> list[str]:
    """One code line per kind, in the SAME priority as the gist view's top_items: the diary theme (moderate or worse), ALL missed medicines, anchors and
    large changes together (ordered by size, large first), status deviations. Diary summaries ("N other diary entries") never lead anything."""
    mats, tags, deltas = row["material_changes"], row["tags"], row["deltas_clean"]
    line = lambda i: _material_line(cfg, i, deltas, tags)
    items: list[str] = []
    cutoff = diary_severity_rank(cfg, cfg.month_min_severity)
    theme = [(diary_severity_rank(cfg, i.get("severity_note")), k, i) for k, i in enumerate(mats) if i["kind"] == "diary_event" and diary_severity_rank(cfg, i.get("severity_note")) <= cutoff]
    if theme:
        items.append(line(min(theme, key=lambda x: (x[0], x[1]))[2]))
    missed = [i for i in mats if i["kind"] == "missed_dose"]
    if missed:
        items.append(" ".join(line(i) for i in missed))
    size = {"large": 0, "moderate": 1, "small": 2}
    by_measure = {t["measure"]: t for t in tags}
    changes = []
    for i in mats:
        if i["kind"] == "anchor_crossed":
            t = by_measure.get(ANCHOR_STREAM.get(i["anchor"], ""))
            changes.append((size.get(t["size"], 3) if t else -1, line(i)))
        elif i["kind"] == "large_change":
            changes.append((0, line(i)))
    if changes:
        items.append(" ".join(text for _, text in sorted(changes, key=lambda c: c[0])))
    status = [line(i) for i in mats if i["kind"] == "status_worse_than_usual"]
    if status:
        items.append(" ".join(status))
    return items


def fallback_code_line(cfg: Config, row: dict) -> str:
    """The code line stored when the model fails twice: the first two items of `priority_lines`."""
    top = priority_lines(cfg, row)[:2]
    return " ".join(map(_as_sentence, top)) if top else f"Nothing deviated from {cfg.possessive} usual."


def plural_categories(counts: dict[str, int]) -> str:
    """{"life_event": 6, "symptom": 4} -> "6 life events, 4 symptoms" (largest first, then by name)."""
    return ", ".join(f"{n} {c.replace('_', ' ')}{'' if n == 1 else 's'}" for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _tag_for(tags: list[dict], measure: str) -> dict | None:
    return next((t for t in tags if t["measure"] == measure), None)


def anchor_phrase(cfg: Config, name: str, deltas: dict, tags: list[dict]) -> str:
    """One crossed anchor in words: what it measures, which way, how much, and its size label (numbers are allowed here: it is code)."""
    if name in SOURCE:
        key, label, unit = SOURCE[name]
        tag = _tag_for(tags, ANCHOR_STREAM.get(name, ""))
        size = f" ({tag['size']})" if tag and tag["size"] != "none" else ""
        return f"{label} {phrase(deltas.get(key), unit, cfg=cfg)}{size}"
    if name == "adherence_meds_changed":
        return f"{deltas.get('meds_changed')} medicines went from taken to missed"
    if name == "severe_range_appeared_or_cleared":
        return f"severe high or low glucose time {fmt(deltas.get('severe_curr'))}% (was {fmt(deltas.get('severe_prior'))}%)"
    if name == "lab_cgm_discordance":
        return f"lab HbA1c and the glucose-based estimate differ by {fmt(abs(deltas.get('lab_gap') or 0))} points"
    return name.replace("_", " ")


def notable_reason(cfg: Config, crossed: list[str], deltas: dict, tags: list[dict]) -> str | None:
    if not crossed:
        return None
    return "; ".join(anchor_phrase(cfg, a, deltas, tags) for a in crossed) + "."


def _material_line(cfg: Config, item: dict, deltas: dict, tags: list[dict]) -> str:
    k = item["kind"]
    if k == "anchor_crossed":
        text = anchor_phrase(cfg, item["anchor"], deltas, tags)
        if item["anchor"] == "lab_cgm_discordance":                  # a difference between two measurements, not a change over time
            return f"{text[:1].upper()}{text[1:]}."
        return f"Notable change: {text}."
    if k == "missed_dose":
        return f"Missed dose: {cfg.medicine_name(item['medicine'])}" + (f", {item['days']} of {item['of']} days." if item.get("of") else ".")
    if k == "diary_event":
        note = f" ({item['severity_note']})" if item.get("severity_note") else ""
        return f"Diary, {item['date']} [{(item.get('category') or 'event').replace('_', ' ')}]: \"{item['text']}\"{note}"
    if k == "diary_summary":
        return f"{item['count']} other diary entr{'y' if item['count'] == 1 else 'ies'}: {plural_categories(item['by_category'])}."
    if k == "status_worse_than_usual":
        sc, ss = cfg.stream(item["measure"]), next((s for s in cfg.status_streams if s.name == item["measure"]), None)
        name = (sc.display if sc else ss.label if ss else item["measure"].replace("_", " ")).capitalize()
        when = f" on {item['days']} of {item['of']} {item.get('unit', 'days')}" if item.get("of") else ""
        return f"{name} {STATUS_WORDS.get(item['status'], item['status'])}{when}, worse than its usual ({STATUS_WORDS.get(item['usual'], item['usual'])})."
    if k == "large_change":
        return f"Large change in {item['label']}: {item.get('direction_word', item['direction'])}."
    if k == "data_gap":
        return f"Glucose readings had a gap of {fmt(item['hours'], 1)} hours" + (f" (longest, on {item['days']} day(s))." if item.get("days") else ".")
    if k == "low_completeness":
        return f"{item['label'].capitalize()} data was incomplete ({fmt(item['pct'], 1)}% of the expected readings)."
    if k == "questionable_reading_removed":
        return f"Reading removed: {fmt(item['value'])} mg/dL at {item['time'].replace('T', ' ')[:16]}, because it looks like a sensor error ({item['reason']})."
    return str(item)


def material_lines(cfg: Config, row: dict) -> list[str]:
    """The material changes of any window as plain sentences (the same lines the deviation text prints)."""
    return [_material_line(cfg, i, row["deltas_clean"], row["tags"]) for i in row["material_changes"]]


def _caveats(row: dict, window: str) -> list[str]:
    cav = []
    dq = row["data_quality"]
    if dq["questionable_readings"]:
        vals = ", ".join(fmt(r["value"]) for r in dq["questionable_readings"])
        twin = ", ".join(f"{METRIC_WORDS.get(k, (k.replace('_', ' '), ''))[0]} {fmt(v)}{(' ' + METRIC_WORDS[k][1]) if k in METRIC_WORDS else ''}" for k, v in dq["metrics_with_questionable"].items())
        cav.append(f"The glucose values above exclude {len(dq['questionable_readings'])} questionable reading(s) ({vals}); with them included: {twin}.")
    for a in row["anchors_questionable"]:
        cav.append(f"A notable change ({a.replace('_', ' ')}) was ignored: it existed only because of a removed reading.")
    if not row["reliable"]:
        cav.append(f"This {window} is not clinically reliable (too little glucose data, or too early in the record).")
    ne = [t["label"] for t in row["tags"] if t["direction"] == "not_enough_data"]
    if ne:
        cav.append("Not enough history to compare: " + ", ".join(ne) + ".")
    return cav


def _section(out: list[str], title: str, lines: list[str]) -> None:
    out.append(f"{title}:")
    out.extend([f"  - {x}" for x in lines] or ["  - none"])


def _changed_and_comove(cfg: Config, row: dict, vs: str, out: list[str]) -> None:
    moved = [t for t in row["tags"] if t["direction"] in ("up", "down")]
    _section(out, f"WHAT CHANGED vs the previous {vs}", [f"{t['label'].capitalize()}: {phrase(t['delta'], t['unit'], t['count_like'], cfg)} ({t['size']})" for t in moved])
    cm = row["co_movement"]
    lines = []
    if cm["glucose_direction"] in ("up", "down"):
        lines += [f"{e['measure'].capitalize()}: {e['direction_word']} ({e['size']}), the same way as glucose ({cm['glucose_direction']})" for e in cm["same_direction"]]
        lines += [f"{e['measure'].capitalize()}: {e['direction_word']} ({e['size']}), the opposite way to glucose ({cm['glucose_direction']})" for e in cm["opposite_direction"]]
    _section(out, "MOVED TOGETHER WITH GLUCOSE", lines)


def _glucose_line(g: dict | None, label: str) -> str:
    if not g:
        return f"{label}: no usable readings."
    return (f"{label}: average {fmt(g['mean'])} mg/dL, GMI {fmt(g['gmi_pct'])}%, time in range {fmt(g['tir_pct'])}%, above range {fmt(g['tar_pct'])}% (above 250: {fmt(g['tar_severe_pct'])}%), "
            f"below range {fmt(g['tbr_pct'])}% (below 54: {fmt(g['tbr_severe_pct'])}%), variability {fmt(g['cv_pct'])}%, {g['n_readings']} readings ({fmt(g['completeness_pct'])}% of expected).")


def week_text(cfg: Config, row: dict) -> str:
    f, a = row["facts"], row["facts"]["aggregates"]
    out: list[str] = []
    _section(out, "THINGS THAT DEVIATED", material_lines(cfg, row))
    wv = f["window_values"]
    nums = [_glucose_line(f["glucose"], "Glucose")]
    nums.append(f"Sleep: average {fmt(wv.get('sleep_duration'))} hours per day. Steps: average {fmt_unit(a['steps']['mean_per_day'], 'steps', cfg)} per day ({a['steps']['n_days']} days with data). "
                f"Sedentary: average {fmt_unit(wv.get('sedentary_time'), 'minutes', cfg)} minutes per day.")
    nums.append(f"Heart rate: average {fmt(wv.get('continuous_heart_rate'))} bpm, daily resting value average {fmt(wv.get('resting_heart_rate'))} bpm.")
    ad = a["adherence"]
    if ad["per_medication"]:
        nums.append(f"Medicines: {fmt(ad['overall_pct'])}% taken (" + ", ".join(f"{cfg.medicine_name(m)} {v['taken']} of {v['expected']}" for m, v in ad["per_medication"].items()) + ").")
    if a["mood_by_block"]:
        nums.append("Mood by time of day: " + "; ".join(f"{b}: " + ", ".join(f"{c.replace('_', ' ')} {n}" for c, n in sorted(cs.items())) for b, cs in a["mood_by_block"].items()) + ".")
    if a["meals_by_label"]:
        nums.append(f"Meals: {sum(a['meals_by_label'].values())} logged; peak glucose after meals averaged {fmt(a['post_meal_peak_mean'])} mg/dL, highest {fmt(a['post_meal_peak_max'])} mg/dL.")
    if a["location_days"]:
        nums.append("Location: " + ", ".join(f"{k.replace('_', ' ')} {v} day{'s' if v != 1 else ''}" for k, v in sorted(a["location_days"].items())) + ".")
    nums += [f"Blood pressure {b['date']}: {fmt(b['systolic'])}/{fmt(b['diastolic'])} at {b['timestamp'][11:16]}." for b in a["blood_pressure"]]
    _section(out, "NUMBERS", nums)
    _changed_and_comove(cfg, row, "week", out)
    best, worst = (f["best_day"] or {}).get("date"), (f["worst_day"] or {}).get("date")
    day_lines = []
    for t in f["daily_trajectory"]:
        tags = [x for x, on in (("best day", t["date"] == best), ("worst day", t["date"] == worst)) if on]
        if t["missed_medicines"]:
            tags.append("missed " + ", ".join(cfg.medicine_name(m) for m in t["missed_medicines"]))
        if t["diary_event_count"]:
            tags.append(f"{t['diary_event_count']} diary event(s)")
        if t["removed_readings"]:
            tags.append(f"{t['removed_readings']} reading(s) removed")
        if t["gap_hours"]:
            tags.append(f"glucose gap {fmt(t['gap_hours'], 1)} h")
        day_lines.append(f"{t['date']}: average glucose {fmt(t['glucose_mean'])} mg/dL, time in range {fmt(t['tir_pct'])}%, sleep {fmt(t['sleep_hours'])} hours, steps {fmt_unit(t['steps'], 'steps', cfg)}, "
                         f"medicines taken {fmt(t['adherence_pct'])}%, worst mood {(t['worst_mood'] or 'none recorded').replace('_', ' ')}" + (f" [{'; '.join(tags)}]" if tags else ""))
    if f["best_and_worst_note"]:
        day_lines.append(f["best_and_worst_note"].capitalize() + ".")
    _section(out, "DAY BY DAY", day_lines)
    _section(out, "CAVEATS", _caveats(row, "week"))
    _section(out, "STEADY (no meaningful change)", [t["label"] for t in row["tags"] if t["direction"] == "flat"])
    return "\n".join(out)


def month_text(cfg: Config, row: dict) -> str:
    f = row["facts"]
    out: list[str] = []
    _section(out, "THINGS THAT DEVIATED", material_lines(cfg, row))
    wv = f["window_values"]
    nums = [_glucose_line(f["cumulative"], "Whole history so far"), _glucose_line(f["last_30_days"], f"Last {cfg.month_every_days} days"),
            f"Last {cfg.month_every_days} days: sleep average {fmt(wv.get('sleep_duration'))} hours, steps average {fmt_unit(wv.get('step_count'), 'steps', cfg)} per day, medicines taken {fmt(wv.get('medication_adherence'))}%, "
            f"daily resting heart rate average {fmt(wv.get('resting_heart_rate'))} bpm."]
    _section(out, "NUMBERS", nums)
    _changed_and_comove(cfg, row, "checkpoint", out)
    _section(out, "MONTH BY MONTH", [f"{m['month']}{' (partial)' if m['partial'] else ''}: average glucose {fmt(m['glucose']['mean'])} mg/dL, time in range {fmt(m['glucose']['tir_pct'])}%, "
                                     f"sleep {fmt(m['mean_sleep_hours'])} hours, steps {fmt_unit(m['mean_steps'], 'steps', cfg)}, medicines taken {fmt(m['adherence_pct'])}%." for m in f["monthly_trajectory"] if m["glucose"]])
    _section(out, "LAB LINK", [f"Lab {l['lab_date']}: HbA1c {fmt(l['hba1c_pct'])}%; glucose-based estimate over the 90 days before " + (f"{fmt(l['gmi_90d_prior'])}% (gap {fmt(l['gap_hba1c_minus_gmi'])} points, {l['cgm_days']} days of sensor data)." if l["gmi_90d_prior"] is not None else "not available (no sensor data that far back).") for l in f["lab_link"]])
    _section(out, "CHRONIC FINDINGS", [f"{c['label'].capitalize()}: non-normal on {fmt(c['share_pct'], 1)}% of {c['days']} days so far (usually {STATUS_WORDS.get(c['usual_status'], c['usual_status'])})." for c in f["chronic_findings"]])
    _section(out, "CAVEATS", _caveats(row, "checkpoint"))
    _section(out, "STEADY (no meaningful change)", [t["label"] for t in row["tags"] if t["direction"] == "flat"])
    return "\n".join(out)


def deviation_text(cfg: Config, day: dict) -> str:
    f, tags, deltas = day["facts"], day["tags"], day["deltas_clean"]
    out: list[str] = []

    def section(title: str, lines: list[str]) -> None:
        out.append(f"{title}:")
        out.extend([f"  - {x}" for x in lines] or ["  - none"])

    section("THINGS THAT DEVIATED", material_lines(cfg, day))

    g = f["glucose"]
    nums = []
    if g:
        nums.append(f"Glucose: average {fmt(g['mean'])} mg/dL, GMI {fmt(g['gmi_pct'])}%, time in range {fmt(g['tir_pct'])}%, above range {fmt(g['tar_pct'])}% "
                    f"(above 250: {fmt(g['tar_severe_pct'])}%), below range {fmt(g['tbr_pct'])}% (below 54: {fmt(g['tbr_severe_pct'])}%), variability {fmt(g['cv_pct'])}%, "
                    f"{g['n_readings']} readings ({fmt(g['completeness_pct'])}% of expected).")
    else:
        nums.append("Glucose: no usable readings.")
    sl, ac, hr, lf = f["sleep"], f["activity"], f["heart_rate"], f["lifestyle"]
    nums.append(f"Sleep: {fmt(sl['duration_hours'])} hours{status_suffix(sl['status'])}, quality {sl.get('quality') or 'not recorded'}.")
    nums.append(f"Activity: steps {fmt_unit(ac['total_steps'], 'steps', cfg)}{status_suffix(ac['status'])}, sedentary time {fmt_unit(ac['sedentary_minutes'], 'minutes', cfg)} minutes{status_suffix(ac['sedentary_status'])}.")
    nums.append(f"Heart rate: average {fmt(hr['continuous_mean'])} bpm, daily resting value {fmt(hr['resting_daily'])} bpm{status_suffix(hr['resting_status'])}.")
    nums += [f"Blood pressure: {fmt(b['systolic'])}/{fmt(b['diastolic'])} at {b['timestamp'][11:16]}." for b in f["blood_pressure"]]
    meds = f["adherence"]["per_medication"]
    if meds:
        nums.append("Medicines: " + ", ".join(f"{cfg.medicine_name(m)} {s}" for m, s in sorted(meds.items())) + f" ({fmt(f['adherence']['overall_pct'])}% taken).")
    if f["mood"]["blocks"]:
        nums.append("Mood by time of day: " + ", ".join(f"{b} {v['category'].replace('_', ' ')}" for b, v in f["mood"]["blocks"].items()) + f" ({f['mood']['strained_count']} strained periods of the day).")
    nums.append(f"Lifestyle: hydration {fmt_unit(lf['hydration_ml'], 'mL', cfg)} mL{status_suffix(lf['hydration_status'])}, screen time {fmt(lf['screen_time_hours'])} hours{status_suffix(lf['screen_time_status'])}, location {(lf['location'] or 'not recorded').replace('_', ' ')}.")
    section("NUMBERS", nums)

    moved = [t for t in tags if t["direction"] in ("up", "down")]
    section("WHAT CHANGED vs the previous day", [f"{t['label'].capitalize()}: {phrase(t['delta'], t['unit'], t['count_like'], cfg)} ({t['size']})" for t in moved])
    cm = day["co_movement"]
    comove = []
    if cm["glucose_direction"] in ("up", "down"):
        comove += [f"{e['measure'].capitalize()}: {e['direction_word']} ({e['size']}), the same way as glucose ({cm['glucose_direction']})" for e in cm["same_direction"]]
        comove += [f"{e['measure'].capitalize()}: {e['direction_word']} ({e['size']}), the opposite way to glucose ({cm['glucose_direction']})" for e in cm["opposite_direction"]]
    section("MOVED TOGETHER WITH GLUCOSE", comove)

    post = [f"After {m['meal_label'].replace('_', ' ')} (\"{m['food_description']}\"): glucose {fmt(m['pre_meal_glucose'])} before, peak {fmt(m['peak_glucose'])} mg/dL {m['minutes_to_peak']} minutes after."
            for m in f["post_meal"]]
    per = [f"{k.capitalize()}: " + ("no readings." if v is None else f"average {fmt(v['mean'])} mg/dL, highest {fmt(v['max'])} mg/dL, {fmt(v['tir_pct'])}% in range.")
           for k, v in f["glucose_by_period"].items()]
    section("TRAJECTORY", per + post)

    cav = []
    dq = day["data_quality"]
    if dq["questionable_readings"]:
        vals = ", ".join(fmt(r["value"]) for r in dq["questionable_readings"])
        twin = ", ".join(f"{METRIC_WORDS.get(k, (k.replace('_', ' '), ''))[0]} {fmt(v)}{(' ' + METRIC_WORDS[k][1]) if k in METRIC_WORDS else ''}" for k, v in dq["metrics_with_questionable"].items())
        cav.append(f"The glucose values above exclude {len(dq['questionable_readings'])} questionable reading(s) ({vals}); with them included: {twin}.")
    for a in day["anchors_questionable"]:
        cav.append(f"A notable change ({a.replace('_', ' ')}) was ignored: it existed only because of a removed reading.")
    if not day["reliable"]:
        cav.append("This window is not clinically reliable (too little glucose data, or too early in the record).")
    ne = [t["label"] for t in tags if t["direction"] == "not_enough_data"]
    if ne:
        cav.append("Not enough history to compare: " + ", ".join(ne) + ".")
    section("CAVEATS", cav)
    section("STEADY (no meaningful change)", [t["label"] for t in tags if t["direction"] == "flat"])
    return "\n".join(out)
