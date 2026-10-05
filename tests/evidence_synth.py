"""A synthetic second patient for the Evidence Engine tests: other stream names, other time zone, other meal kinds, other block names, its own rulebook and library.
Planted relationships: a skipped pill raises that day's mean; a stressed morning raises the late meal's peak; an unwell note shortens the next night's sleep; steps in
the previous hour raise the hour's value. Everything else is noise."""

import csv
import json
import math
import random
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=9))
START = date(2026, 1, 1)

BASELINE = """
patient:
  id: synth_patient
  timezone: "Asia/Tokyo"
  pronoun: "they"
  strain_mood_categories: [stressed]
  medication_id_regex: ""
history: {min_days_for_compare: 14, reliable_completeness_pct: 70}
glucose: {device_range: [40, 400], max_step_change_per_15min: 75, expected_per_day: 96, gap_hours_flag: 1.0}
streams:
  - {name: gl_cgm, domain: glucose, kind: continuous, label: glucose, unit: mg/dL, agg: glucose_mean, source: raw, expected_per_day: 96}
  - {name: time_in_range, domain: glucose, kind: derived, label: time in range, unit: percentage points, agg: glucose_tir_pct}
  - {name: variability, domain: glucose, kind: derived, label: variability, unit: percentage points, agg: glucose_cv_pct}
flat_band: {sd_multiplier: 0.5}
size_labels: {small_below: 2, moderate_below: 4}
anchors:
  glucose_TIR_change_points: {day: 10}
  glucose_CV_change_points: {day: 8}
  severe_range_appeared_or_cleared: true
gist: {}
"""

STATE = """
state:
  baseline_config: {baseline}
  db_path: state.db
  tick_minutes: 15
  min_history_days: 14
  min_samples_usual: 30
  overdue_grace: 1.5
  last_meal_window_minutes: 1440
  position: {{method_default: sd, thresholds_sd: [1, 2, 4], thresholds_percentile: [0.35, 0.15, 0.05]}}
  persistence: {{open_label: clearly, close_label: slightly, n_open: 2, n_close: 2}}
  severe: {{position: far, statuses: [critical_high, critical_low]}}
  glucose: {{usual_basis: meal_relative_with_clock_fallback, meal_window_minutes: 180, meal_bucket_minutes: 15, clock_band_minutes: 30, meal_kinds: [brunch, supper]}}
  streams:
    gl_cgm: {{key: sugar, kind: continuous, source: {{table: raw, name: gl_cgm}}, freshness_minutes: 30, available_at: timestamp, usual_basis: glucose, adverse_directions: [above], cleaning: baseline_glucose}}
    sleep_h: {{key: rest, kind: daily, source: {{table: raw, name: sleep_h}}, role: sleep, cadence: daily, freshness_minutes: 1440, available_at: timestamp, usual_basis: profile, adverse_directions: [below], n_open: 1, n_close: 1}}
    pills: {{key: pills, kind: count, source: {{table: context, name: pills}}, cadence: daily, freshness: end_of_day, available_at: "21:00", usual_basis: history_percentile, adverse_directions: [below], n_open: 1, n_close: 1}}
    mood_log: {{key: feeling, kind: label, source: {{table: context, name: mood_log, block_key: part}}, cadence: three_per_day, freshness_minutes: 480, available_at: {{am: "11:00", pm: "17:00"}}, position_method: none}}
  context_streams:
    diary: {{name: notes, available_at: "21:00"}}
"""

EVIDENCE = """
evidence:
  method_version: ev-v0
  history: {{min_history_units: 60, min_history_days: 60, detrend: {{method: trailing_median, window_days: 30, min_prior_values: 10}}}}
  min_exposed: 15
  min_reference: 30
  permutation: {{n: 2000, min_shift_fraction: 0.05}}
  multiplicity: {{method: benjamini_hochberg, q: 0.10, family: x}}
  labels: {{p_suggestive: 0.10, effect_floor_binary: 0.10, effect_floor_continuous: 0.10, contrary_p: 0.10}}
  placebo: {{shift_fraction: 0.30}}
  overlap: {{tail_quantile: 0.25, min_share_given_a: 0.25, min_ratio: 2.0, among: [supported, suggestive]}}
  event_exposure: {{tail_quantile: 0.25}}
  percentile_check: {{history_min: 30, supported_min_percentile: 90}}
  shape_check: {{isolated_min_step: 30, rebound_tolerance: 20, steep_drop_min: 30}}
  pattern_repeat: {{dawn_window: "04:00-09:00", dawn_min_rise: 20, min_share: 0.5, min_days: 14}}
  location: {{home_types: [home], clinic_types: [clinic]}}
  presence_flags: {{anything: {{flag_a: false, flag_b: true}}}}
  resting_heart_rate_pick: last
  stream_map:
    glucose: {{table: raw, name: gl_cgm}}
    meals: {{table: context, name: food_log}}
    sleep: {{table: raw, name: sleep_h}}
    mood: {{table: context, name: mood_log}}
    diary: {{table: context, name: notes}}
    steps_hourly: {{table: context, name: steps_h}}
    adherence: {{table: context, name: pills}}
    nothing_here: null
  paths:
    library: {d}/library.yaml
    state_config: {d}/state.yaml
    rulebook_dir: {d}
    candidates_file: candidates.csv
    store_db: {d}/store.db
    db_path: {d}/evidence.db
"""

TAGS = """
lookback_tags:
  minutes_before_open: "{value}m"
  days_ending_at_open: "{value}d"
  previous_night: prev_night
  previous_calendar_day: prev_day
  previous_evening: prev_evening
  same_calendar_day: same_day
  at_open: at_open
  minutes_around_open: "pm{value}m"
shifted_tags: [same_day, 1d, 2d, 3d]
evening: {start: "18:00", end: "24:00"}
"""

LIBRARY = "library_version: synth-v0\n" + TAGS + """
sources:
  glucose: {clean: baseline}
  meals: {label_field: category}
  steps_hourly: {span_minutes: 60}
outcomes:
  meal_peak:
    {unit: meal, unit_source: meals, scope: event_kind, forward_minutes: 150, value: {primitive: max_after_event, source: glucose, window_minutes: 150}, worse_is: higher, outcome_date: opened_date, exposure_shift_days: 0}
  day_level:
    {unit: day, value: {primitive: mean_of_day, source: glucose}, worse_is: higher, outcome_date: opened_date, exposure_shift_days: 0}
  night_len:
    {unit: day, value: {primitive: dated_record, source: sleep, pick: last}, worse_is: lower, outcome_date: opened_date, exposure_shift_days: -1}
  hour_level:
    {unit: hour, value: {primitive: mean_of_hour, source: glucose}, worse_is: higher, outcome_date: opened_date, exposure_shift_days: 0}
exposures:
  pill_skip: {form: binary, risk_side: exposed, resolution: date, value: {primitive: any_in_window, source: adherence, match: {field: text, equals: skipped}}}
  rest_hours: {form: continuous, risk_side: low, resolution: timestamp, value: {primitive: value_in_window, source: sleep}}
  stress_block: {form: binary, risk_side: exposed, resolution: block, value: {primitive: any_in_window, source: mood, match: {field: category, in_ref: baseline.strain_mood_categories}}}
  unwell_note: {form: binary, risk_side: exposed, resolution: timestamp, value: {primitive: any_in_window, source: diary, match: {field: category, equals: unwell}}}
  steps_before: {form: continuous, risk_side: high, resolution: timestamp, value: {primitive: value_in_window, source: steps_hourly}}
  late_start: {form: binary, risk_side: exposed, resolution: timestamp, value: {primitive: event_start_minute, source: meals, kind: same_as_unit}, binarize: {op: at_or_above_quantile, quantile: 0.75}}
event_checks:
  anything: {type: presence_check, facts: anything}
  peak_check: {type: percentile_vs_history, measure: peak_at_elapsed, source: glucose, unit_source: meals, worse: higher}
  gap_check: {type: percentile_vs_history, measure: hours_since_last_event, source: meals, worse: higher}
  artifact: {type: shape_check, measure: isolated_reading, source: glucose, window_minutes: 60}
  rise: {type: pattern_repeat, measure: rise_in_window, source: glucose}
  rates: {type: pattern_repeat, measure: rate_by_group, source: adherence, group_field: category, match: {field: text, equals: skipped}}
pairs:
  - {rule: r_meal, rank: 1, tier: primary, candidate: skip, check_type: group_comparison, status: runnable, exposure: pill_skip, outcome: meal_peak, key: "pill_skip@2d->meal_peak:{meal_kind}", ordering: same_day_unverified}
  - {rule: r_meal, rank: 2, tier: secondary, candidate: rest, check_type: group_comparison, status: runnable, exposure: rest_hours, outcome: meal_peak, key: "rest_hours@prev_night->meal_peak:{meal_kind}", ordering: ordered}
  - {rule: r_meal, rank: 3, tier: secondary, candidate: stress, check_type: group_comparison, status: runnable, exposure: stress_block, outcome: meal_peak, key: "stress_block@1d->meal_peak:{meal_kind}", ordering: ordered}
  - {rule: r_meal, rank: 4, tier: secondary, candidate: unwell, check_type: group_comparison, status: runnable, exposure: unwell_note, outcome: meal_peak, key: "unwell_note@3d->meal_peak:{meal_kind}", ordering: ordered}
  - {rule: r_meal, rank: 5, tier: tertiary, candidate: late, check_type: group_comparison, status: runnable, exposure: late_start, outcome: meal_peak, key: "late_start@same_day->meal_peak:{meal_kind}", ordering: ordered}
  - {rule: r_meal, rank: 6, tier: tertiary, candidate: nothing, check_type: group_comparison, status: no_definition, reason: no_stream}
  - {rule: r_day, rank: 1, tier: primary, candidate: skip, check_type: group_comparison, status: runnable, exposure: pill_skip, outcome: day_level, key: "pill_skip@2d->day_level", ordering: same_day_unverified}
  - {rule: r_day, rank: 2, tier: secondary, candidate: stress, check_type: group_comparison, status: runnable, exposure: stress_block, outcome: day_level, key: "stress_block@1d->day_level", ordering: same_day_unverified}
  - {rule: r_day, rank: 3, tier: secondary, candidate: unwell, check_type: group_comparison, status: runnable, exposure: unwell_note, outcome: day_level, key: "unwell_note@prev_day->day_level", ordering: ordered}
  - {rule: r_night, rank: 1, tier: primary, candidate: unwell, check_type: group_comparison, status: runnable, exposure: unwell_note, outcome: night_len, key: "unwell_note@same_day->night_len", ordering: ordered}
  - {rule: r_night, rank: 2, tier: secondary, candidate: skip, check_type: group_comparison, status: runnable, exposure: pill_skip, outcome: night_len, key: "pill_skip@1d->night_len", ordering: ordered}
  - {rule: r_hour, rank: 1, tier: primary, candidate: steps, check_type: group_comparison, status: runnable, exposure: steps_before, outcome: hour_level, key: "steps_before@60m->hour_level", ordering: ordered}
  - {rule: r_hour, rank: 2, tier: secondary, candidate: anything, check_type: presence_check, status: event_level, event_check: anything}
  - {rule: r_hour, rank: 3, tier: tertiary, candidate: artifact, check_type: shape_check, status: event_level, event_check: artifact}
  - {rule: r_meal, rank: 7, tier: tertiary, candidate: peak_check, check_type: percentile_vs_history, status: event_level, event_check: peak_check}
  - {rule: r_meal, rank: 8, tier: tertiary, candidate: gap_check, check_type: percentile_vs_history, status: event_level, event_check: gap_check}
  - {rule: r_day, rank: 4, tier: tertiary, candidate: rise, check_type: pattern_repeat, status: event_level, event_check: rise}
  - {rule: r_day, rank: 5, tier: tertiary, candidate: rates, check_type: pattern_repeat, status: event_level, event_check: rates}
"""

CANDIDATES = [
    ("r_meal", 1, "primary", "skip", "group_comparison", "days_ending_at_open", 2), ("r_meal", 2, "secondary", "rest", "group_comparison", "previous_night", ""),
    ("r_meal", 3, "secondary", "stress", "group_comparison", "days_ending_at_open", 1), ("r_meal", 4, "secondary", "unwell", "group_comparison", "days_ending_at_open", 3),
    ("r_meal", 5, "tertiary", "late", "group_comparison", "same_calendar_day", ""), ("r_meal", 6, "tertiary", "nothing", "group_comparison", "at_open", ""),
    ("r_day", 1, "primary", "skip", "group_comparison", "days_ending_at_open", 2), ("r_day", 2, "secondary", "stress", "group_comparison", "days_ending_at_open", 1),
    ("r_day", 3, "secondary", "unwell", "group_comparison", "previous_calendar_day", ""),
    ("r_night", 1, "primary", "unwell", "group_comparison", "same_calendar_day", ""), ("r_night", 2, "secondary", "skip", "group_comparison", "days_ending_at_open", 1),
    ("r_hour", 1, "primary", "steps", "group_comparison", "minutes_before_open", 60), ("r_hour", 2, "secondary", "anything", "presence_check", "at_open", ""),
    ("r_hour", 3, "tertiary", "artifact", "shape_check", "minutes_around_open", 60), ("r_meal", 7, "tertiary", "peak_check", "percentile_vs_history", "minutes_before_open", 240),
    ("r_meal", 8, "tertiary", "gap_check", "percentile_vs_history", "minutes_before_open", 720), ("r_day", 4, "tertiary", "rise", "pattern_repeat", "same_calendar_day", ""),
    ("r_day", 5, "tertiary", "rates", "pattern_repeat", "days_ending_at_open", 7),
]


def make_store(path, n_days=240, seed=7, plant=True, pills_always_taken=False, extra=None):
    """Returns the path. `extra(readings, ctx)` can edit the generated rows before they are written."""
    rng = random.Random(seed)
    readings, ctx = [], []
    skipped, unwell_prev = {}, False
    moods = {}
    unwell_days = set()
    meals_by_day = {}
    for i in range(n_days):
        d = START + timedelta(days=i)
        skipped[d] = False if pills_always_taken else rng.random() < 0.3
        moods[d] = {"am": rng.random() < 0.25, "pm": rng.random() < 0.25}
        if rng.random() < 0.10:
            unwell_days.add(d)
        meals_by_day[d] = [("brunch", 10 * 60 + rng.randint(-30, 30)), ("supper", 19 * 60 + 30 + rng.randint(-45, 45))]
    for i in range(n_days):
        d = START + timedelta(days=i)
        ds = d.isoformat()
        steps = {h: (rng.randint(0, 900) if 6 <= h <= 22 else 0) for h in range(24)}
        for h in range(24):
            ctx.append(("steps_h", f"{ds}T{h:02d}:00:00+09:00", ds, None, float(steps[h]), None, "{}"))
        sleep = 7.5 + rng.gauss(0, 0.5) - (1.3 if plant and (d - timedelta(days=1)) in unwell_days else 0)
        readings.append((f"s{i}", f"{ds}T06:30:00+09:00", "sleep_h", round(sleep, 2), "normal"))
        ctx.append(("pills", None, ds, "skipped" if skipped[d] else "taken", 0.0 if skipped[d] else 1.0, "pill_a", "{}"))
        for part, hh in (("am", "11:00"), ("pm", "17:00")):
            ctx.append(("mood_log", None, ds, None, None, "stressed" if moods[d][part] else "fine", json.dumps({"part": part})))
        if d in unwell_days:
            ctx.append(("notes", f"{ds}T{rng.randint(8, 20):02d}:00:00+09:00", ds, "text", None, "unwell", "{}"))
        if rng.random() < 0.15:
            ctx.append(("notes", f"{ds}T{rng.randint(8, 20):02d}:00:00+09:00", ds, "text", None, "party", "{}"))
        for kind, minute in meals_by_day[d]:
            ctx.append(("food_log", f"{ds}T{minute // 60:02d}:{minute % 60:02d}:00+09:00", ds, "food", None, f"{kind}_x", "{}"))
        for k in range(96):
            tmin = k * 15
            g = 100 + 8 * math.sin(2 * math.pi * k / 96) - 0.02 * i + rng.gauss(0, 2)
            if plant and skipped[d]:
                g += 8
            for kind, m0 in meals_by_day[d]:
                tau = tmin - m0
                if 0 <= tau <= 150:
                    amp = 40 + (20 if plant and kind == "supper" and moods[d]["am"] else 0)
                    g += amp * math.sin(math.pi * tau / 150)
            if plant:
                g += 0.03 * steps[(tmin // 60 - 1) % 24] if tmin >= 60 else 0
            readings.append((f"g{i}_{k}", f"{ds}T{tmin // 60:02d}:{tmin % 60:02d}:00+09:00", "gl_cgm", round(g, 1), "normal"))
    if extra:
        extra(readings, ctx)
    from v0_code.data.store import PersonalDataStore
    store = PersonalDataStore(path, reset=True)
    store.insert_readings(readings)
    store.insert_context_events(ctx)
    store.conn.close()
    return path


def make_patient(d, n_days=240, **kw) -> Path:
    """Write every file of the synthetic patient into `d` and return the evidence config path."""
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "baseline.yaml").write_text(BASELINE)
    (d / "state.yaml").write_text(STATE.format(baseline=str(d / "baseline.yaml")))
    (d / "library.yaml").write_text(LIBRARY)
    with open(d / "candidates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rule_id", "rank", "weight_tier", "candidate", "check_type", "lookback_kind", "lookback_value"])
        w.writerows(CANDIDATES)
    make_store(d / "store.db", n_days=n_days, **kw)
    (d / "evidence.yaml").write_text(EVIDENCE.format(d=str(d)))
    return d / "evidence.yaml"
