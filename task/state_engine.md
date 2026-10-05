# State Engine: Definition Spec

> **Superseded by `docs/state_engine_notes.md` and `docs/state_engine_reference_examples.md` wherever they differ.**

## 0. How to read this document

This document says **what the State Engine is**: its purpose, inputs, rules, outputs and the keys that appear in them. It does not say how to build it. Module layout, function names, data structures and code style are yours to decide.

Where this document is silent, state your assumption in your report. Do not invent behaviour silently.

Where this document says a value is **a default**, it must live in config, not in code.

Items marked **[verify]** are details I took from earlier specs and reports. Check them against the real code and database, and say where they differ.

---

## 1. What the State Engine is

> **State Engine compares the latest reading of each measure against the patient's baseline and shows where the person stands right now.**

That is the whole definition. It has not been widened.

It produces a **Current State Snapshot**: for every measure, the latest value, how old it is, what is usual for this person, and where the value sits against that usual. When a measure has been off her usual for long enough, it opens a **deviation item** and passes it on.

### 1.1 What it is not

- It does not explain why a value is off (no candidates, no statistics, no findings).
- It does not compare today with yesterday or this week with last week. That is the Baseline Engine's job.
- It does not compute or change the baseline. It only reads it.
- It does not send alerts or messages. A dangerous single reading is handled upstream by the Alert Dispatcher, which acts before the store.
- It does not use an LLM.
- It does not recompute clinical statuses. It carries the Threshold Evaluator's status as given.

---

## 2. Where it sits

```
new reading
   |
Upstream: Plausibility Filter -> Threshold Evaluator -> (Alert Dispatcher for dangerous values)
   |
Personal Data Store  (raw_events, context_events)
   |                                         |
   | every tick (15 min)                      | once a day, after the day ends
   v                                         v
STATE ENGINE                            Baseline Engine v2 (built; table memory_v2)
   ^                                         |
   |_______ reads her usual (read-only) _____|
   |
   +--> state_log (every snapshot), state_items (deviation items), hand-off record
```

**Order in time:** a reading is stored, then State Engine runs on it immediately. The Baseline Engine runs later, after midnight. State Engine compares with the baseline as it stood at the **start of the day**, so today's data is never inside the yardstick used to judge today.

**Downstream (not built yet, out of scope):** Rulebook Lookup reads the hand-off record. For now the hand-off is written to a log only.

---

## 3. Time model

| Term | Meaning |
|---|---|
| **Tick** | One evaluation, every `tick_minutes` (default 15). The fastest stream (glucose, continuous heart rate) arrives every 15 minutes, so 15 is the natural unit. |
| **as_of** | The timestamp a tick represents, in the patient's timezone (same timezone setting the Baseline Engine uses). |
| **baseline_asof** | The date of the last completed baseline day. For every tick on date D, `baseline_asof = D - 1`. Fixed for the whole day. |
| **Replay** | Historical data is stepped tick by tick. "Now" is the as_of we choose. The same rules apply as live. |

### 3.1 Availability (no look-ahead)

A value may be used only at or after the moment it could have been known.

- A value with its own timestamp is available from that timestamp.
- Some records have only a date (daily medicine records, mood blocks, diary entries, lab results). Each stream has an `available_at` rule in config: a clock time, a time per block, or `end_of_day`. Before that time the record does not exist for the State Engine.
- The Baseline Engine's usual is available from the start of the day (`baseline_asof = D - 1`).

### 3.2 Early days

For the first `min_history_days` (default 14, same as the Baseline Engine) there is no usual. Entries show the latest value, age and clinical status, with `usual: null` and `position: "no_baseline_yet"`. No deviation items open from position. A severe clinical status can still trigger a hand-off.

---

## 4. Inputs

### 4.1 From the Personal Data Store

**`raw_events`** [verify column names]: readings that passed the Plausibility Filter and carry the Threshold Evaluator's status.

| Key | Meaning |
|---|---|
| `id` | surrogate row key |
| `event_id` | label (repeats across months; not unique) |
| `timestamp` | ISO time with offset |
| `biomarker` | stream name (e.g. `cgm_glucose_reading`, `sleep_duration`, `resting_heart_rate`, `blood_pressure_systolic`) |
| `value` | numeric value |
| `status` | clinical status from the Threshold Evaluator (`normal`, `borderline_low`, `borderline_high`, `low`, `high`, or other values the evaluator emits) |
| `source_type`, `paired_to`, `candidate_type`, `lag_minutes` | reading versus pairing rows; State Engine uses only reading rows |

**`context_events`** [verify column names]: streams that never passed through the Threshold Evaluator.

| Key | Meaning |
|---|---|
| `id`, `stream`, `timestamp`, `date` | row key, stream name, time, local date |
| `value_num`, `value_text`, `category`, `meta_json` | numeric value, text value, category label, extra fields |

Streams used: continuous heart rate, hourly steps, medicine records, mood, meals, diary, location, and any others in the registry.

### 4.2 From the Baseline Engine (read-only)

State Engine never reads the baseline windows as events and never writes to the baseline.

**a) Profile as-of a date.** The baseline package already provides `get_profile_asof(stream, date)`. Fields State Engine uses (names as in the baseline profile) [verify]:

```json
{
  "stream": "sleep_duration",
  "as_of": "2026-09-16",
  "n_days": 351,
  "median": 6.9,
  "sd": 0.80,
  "usual_status": "borderline_low",
  "share_non_normal": 0.55
}
```

**b) Reading-level usual (a capability State Engine requires; it does not exist today).** The profile above is a summary of daily values. A single 15-minute reading cannot be judged against the spread of daily averages, because every post-meal reading would look far above it. State Engine therefore needs, for continuous measures, her **typical reading** for a given context, as of a date. How this is provided (function or stored table) is for the builder to decide. It must:

- read only data before the as-of date (before the start of today),
- use the Baseline Engine's own cleaning of questionable readings,
- write nothing,
- return this shape:

```json
{
  "stream": "cgm_glucose_reading",
  "basis": "clock_time",
  "context": {"time_of_day": "22:45", "band_minutes": 30},
  "as_of": "2026-09-16",
  "n": 1733,
  "median": 124.9,
  "sd": 16.6,
  "p10": 110.0,
  "p90": 145.1
}
```

Two bases exist:
- `clock_time`: readings from earlier days within `band_minutes` of the time of day.
- `meal_relative`: readings from earlier days at the same number of minutes since a meal of the same kind. `context` is `{"meal_kind": "dinner", "minutes_since_meal": 75}`.

**c) Context only:** `get_memory(tier, date)` for yesterday's memory (for example "metformin missed yesterday"). Context, never used for comparison.

### 4.3 Config (all values below are defaults)

```yaml
state:
  tick_minutes: 15
  min_history_days: 14
  min_samples_usual: 30
  position:
    method_default: sd              # sd | percentile
    thresholds_sd: [1, 2, 4]        # within <1, slightly 1-2, clearly 2-4, far >=4
    thresholds_percentile: [0.35, 0.15, 0.05]   # share of earlier days at least as bad
  persistence:
    open_label: clearly             # position at or beyond this counts toward opening
    close_label: slightly           # position at or better than this counts toward closing
    n_open: 2
    n_close: 2
  severe:
    position: far
    statuses: [critical_high, critical_low]
  glucose:
    usual_basis: meal_relative_with_clock_fallback
    meal_window_minutes: 180
    meal_bucket_minutes: 15
    clock_band_minutes: 30
  streams:                          # same registry the Baseline Engine uses, with a state block each
    cgm_glucose_reading:   {cadence_minutes: 15,   freshness_minutes: 30,   available_at: timestamp, usual_basis: glucose, n_open: 2, n_close: 2}
    continuous_heart_rate: {cadence_minutes: 15,   freshness_minutes: 30,   available_at: timestamp, usual_basis: clock_time, n_open: 2, n_close: 2}
    step_count:            {cadence_minutes: 60,   freshness_minutes: 120,  available_at: timestamp, usual_basis: hour_of_day, n_open: 2, n_close: 2}
    sleep_duration:        {cadence: daily,        freshness_minutes: 1440, available_at: timestamp, usual_basis: profile, n_open: 1, n_close: 1}
    resting_heart_rate:    {cadence: daily,        freshness_minutes: 1440, available_at: timestamp, usual_basis: profile, n_open: 1, n_close: 1}
    blood_pressure:        {cadence_days: 3,       freshness_minutes: 5760, available_at: timestamp, usual_basis: profile, n_open: 1, n_close: 1}
    medication_adherence:  {cadence: daily,        freshness: end_of_day,   available_at: "21:00", usual_basis: history_percentile, n_open: 1, n_close: 1}
    mood_state:            {cadence: three_per_day, freshness_minutes: 480, available_at: {morning: "12:00", afternoon: "18:00", evening: "21:00"}, position_method: none}
    hydration:             {cadence: daily,        freshness_minutes: 1440, available_at: end_of_day, usual_basis: profile, n_open: 1, n_close: 1}
    screen_time:           {cadence: daily,        freshness_minutes: 1440, available_at: end_of_day, usual_basis: profile, n_open: 1, n_close: 1}
    sedentary_time:        {cadence: daily,        freshness_minutes: 1440, available_at: end_of_day, usual_basis: profile, n_open: 1, n_close: 1}
    hba1c:                 {cadence_days: 90,      freshness_minutes: 144000, available_at: end_of_day, position_method: none}
    diary_context:         {cadence: event,        freshness: end_of_day,   available_at: "21:00", position_method: none}
```

Freshness limits, cadences, availability times and the persistence defaults are proposals. They are per-patient config.

---

## 5. Measures and how each is compared

| Class | Measures | Arrives | Compared with |
|---|---|---|---|
| Continuous | glucose, continuous heart rate | every tick | the reading-level usual (4.2b) |
| Hourly | steps | hourly | usual for that hour of day |
| Daily value | sleep, resting heart rate, hydration, screen time, sedentary time | once a day | the profile (4.2a) |
| Periodic value | blood pressure (systolic and diastolic judged separately; the worse of the two is the entry's position) | every few days | the profile |
| Count of events | medicine doses (taken of expected, which are missed) | once a day | her own history as a percentile (share of earlier days at least as bad) |
| Label only | mood, diary, meals, location | when logged | not compared; carried as context |
| Lab | HbA1c | about every 3 months | not compared; value and status shown |

A measure absent from the stream registry does not appear. A measure with no data at all appears as `no_data`.

---

## 6. What happens at each tick (the rules)

**R1. Intake.** For each measure, take the newest value that is available at `as_of` (3.1). If it is newer than the entry's current value, it replaces it. Otherwise the entry keeps its last value and its age grows.

**R2. Validity.** A value that the baseline's cleaning would treat as questionable (outside the device range, or an impossible jump) is rejected. The entry keeps its last good value and records a quality note. A rejected value never counts toward a run.

**R3. Freshness.** `age_minutes = as_of - value_time`. If it exceeds the measure's freshness limit, `current = false`. A measure that is not current has no active run; a stale value never opens or keeps open an item.

**R4. Clinical status.** Carry the status from `raw_events`. Never recompute it. A status that is not attached (for context-only streams) is `null`.

**R5. The usual.** Choose the usual for the measure:
- Daily and periodic measures: the profile as of `baseline_asof`.
- Continuous measures: the reading-level usual. For glucose with `meal_relative_with_clock_fallback`, use `meal_relative` if a meal was logged within `meal_window_minutes` before `as_of` and the meal kind has at least `min_samples_usual` earlier samples at that bucketed minutes-since-meal. Otherwise use `clock_time`. The other basis is also computed and kept in the entry as `usual_alt` for information.
- Hourly measures: usual for that hour of day.
- Count measures: the percentile of her own earlier days.

If fewer than `min_samples_usual` samples exist, or the date is inside the early-days period, `usual` is null and `position` is `no_baseline_yet`.

**R6. Position.** `z = (value - median) / sd`. Label by `|z|`: under 1 `within`, 1 to under 2 `slightly`, 2 to under 4 `clearly`, 4 or more `far`, with direction `above` or `below`. For percentile measures use the share of earlier days at least as bad: at most 5% `far`, at most 15% `clearly`, at most 35% `slightly`, otherwise `within`. Blood pressure takes the worse of systolic and diastolic. These labels are about the **patient's own spread** and are not the Baseline Engine's size labels (which use the flat band, 0.5 x SD), so the same word does not mean the same distance. Do not mix them.

**R7. Run counting (persistence).** Per measure, track a run: the direction and the number of consecutive new readings at or beyond `open_label` in the same direction.
- A new reading at or beyond `open_label` in the same direction adds 1.
- A new reading in the other direction starts a new run at 1 if it qualifies, otherwise the run is 0.
- A new reading within `slightly` or better resets the run to 0.
- A tick with no new reading for a continuous measure neither adds nor resets. If the value becomes stale (R3) the run is cleared.

**R8. Opening an item.** When the run reaches the measure's `n_open`, a deviation item opens. Daily and periodic measures have `n_open: 1`, so one reading is enough. A **severe** value opens an item at once: position `far`, or a clinical status in `severe.statuses`. Upstream's Alert Dispatcher is unaffected and still acts on its own.

**R9. While open.** Track the peak (largest position, with its value and time). Count consecutive new readings at or better than `close_label`.

**R10. Closing.** An item closes when that count reaches `n_close`, or when a new value for a daily measure arrives that is at or better than `close_label`. A closed item has a start, a peak and an end. A new deviation afterwards opens a new item.

**R11. Hand-off.** When an item opens, exactly one hand-off record is written, with the context at that moment (last meal, medicines today, diary entries available so far, sleep). An item is never handed off twice. If an item is still open, nothing further is written for it.

**R12. Write.** Write the snapshot to `state_log`, and write or update items in `state_items`. A tick for an `as_of` that already exists produces the same row (idempotent).

---

## 7. Outputs

### 7.1 Current State Snapshot (one per tick)

```json
{
  "as_of": "2026-09-17T22:45:00+05:30",
  "baseline_asof": "2026-09-16",
  "config_version": "<hash of the state config>",
  "baseline_config_version": "meera_iyer_v1-fb3c0fa91857",
  "early_days": false,
  "measures": {
    "glucose": {
      "value": 185.4, "unit": "mg/dL", "value_time": "2026-09-17T22:45:00+05:30",
      "age_minutes": 0, "current": true, "rejected_latest": false,
      "clinical_status": "high",
      "usual": {"basis": "meal_relative", "context": {"meal_kind": "dinner", "minutes_since_meal": 75},
                "n": 345, "median": 160.9, "sd": 14.7},
      "usual_alt": {"basis": "clock_time", "context": {"time_of_day": "22:45", "band_minutes": 30},
                    "n": 1733, "median": 124.9, "sd": 16.6, "z": 3.6, "label": "clearly above"},
      "position": {"z": 1.7, "label": "slightly above"},
      "run": {"direction": "above", "count": 0, "close_count": 1},
      "open_item_id": "glucose_2026-09-17T22:30"
    },
    "heart_rate": {
      "value": 103.2, "unit": "bpm", "value_time": "2026-09-17T22:45:00+05:30",
      "age_minutes": 0, "current": true, "clinical_status": null,
      "usual": {"basis": "clock_time", "context": {"time_of_day": "22:45", "band_minutes": 30},
                "n": 1733, "median": 74.4, "sd": 9.6},
      "position": {"z": 3.0, "label": "clearly above"},
      "run": {"direction": "above", "count": 6, "close_count": 0},
      "open_item_id": "heart_rate_2026-09-17T21:45"
    },
    "sleep_duration": {
      "value": 3.8, "unit": "h", "value_time": "2026-09-17T07:00:00+05:30",
      "age_minutes": 945, "current": true, "clinical_status": "low",
      "usual": {"basis": "profile", "n": 351, "median": 6.9, "sd": 0.80},
      "position": {"z": -3.9, "label": "clearly below"},
      "open_item_id": "sleep_duration_2026-09-17T07:00"
    },
    "resting_heart_rate": {
      "value": 93, "unit": "bpm", "value_time": "2026-09-17T07:08:00+05:30",
      "age_minutes": 937, "current": true, "clinical_status": null,
      "usual": {"basis": "profile", "n": 352, "median": 77.0, "sd": 5.52},
      "position": {"z": 2.9, "label": "clearly above"},
      "open_item_id": "resting_heart_rate_2026-09-17T07:08"
    },
    "blood_pressure": {
      "value": {"systolic": 138, "diastolic": 94}, "unit": "mmHg",
      "value_time": "2026-09-17T08:08:00+05:30", "age_minutes": 877, "current": true,
      "clinical_status": "high",
      "usual": {"basis": "profile", "systolic": {"n": 140, "median": 125, "sd": 7.7},
                "diastolic": {"n": 140, "median": 81, "sd": 5.1}},
      "position": {"systolic": {"z": 1.7, "label": "slightly above"},
                   "diastolic": {"z": 2.6, "label": "clearly above"},
                   "worst": "diastolic", "label": "clearly above"},
      "open_item_id": "blood_pressure_2026-09-17T08:08"
    },
    "medication_adherence": {
      "taken": 1, "expected": 3, "missed": ["metformin", "levothyroxine"],
      "value_time": "2026-09-17T21:00:00+05:30", "current": true,
      "usual": {"basis": "history_percentile", "share_all_taken": 0.52, "share_two_or_more_missed": 0.10},
      "position": {"share_at_least_as_bad": 0.10, "label": "clearly below"},
      "open_item_id": "medication_adherence_2026-09-17T21:00"
    },
    "mood_state": {"label": "tired", "block": "evening", "value_time": "2026-09-17T21:00:00+05:30", "current": true},
    "hba1c": {"value": 7.0, "unit": "%", "value_time": "2026-03-06T00:00:00+05:30",
              "age_minutes": 281985, "current": false, "clinical_status": "high"}
  },
  "context": {
    "last_meal": {"label": "festive_dinner", "time": "2026-09-17T21:28:00+05:30", "minutes_ago": 77},
    "diary_today": [
      {"category": "life_event", "text": "Quarter-close deadline day, delivered the numbers, largely deskbound, minimal proper meals"},
      {"category": "social_interaction", "text": "Reflected with husband on the layered month - tired, foggy, aware of slipped walks and medication timing; resolved to reset once both pressures ease, honestly acknowledging tonight wasn't that night"}
    ],
    "yesterday_memory_headline": null
  },
  "open_items": ["sleep_duration_2026-09-17T07:00", "resting_heart_rate_2026-09-17T07:08", "blood_pressure_2026-09-17T08:08",
                 "medication_adherence_2026-09-17T21:00", "heart_rate_2026-09-17T21:45", "glucose_2026-09-17T22:30"],
  "quality": []
}
```

### 7.2 Persisted outputs

State Engine's live snapshot is the newest `state_log` row. There is no second copy.

**`state_log`** (append-only, one row per tick; names are a suggestion)

| Key | Meaning |
|---|---|
| `as_of` | the tick timestamp (key) |
| `baseline_asof` | date of the usual used |
| `config_version` | hash of the state config |
| `n_open_items`, `any_stale` | quick-query columns |
| `snapshot_json` | the whole snapshot (7.1) |

**`state_items`** (one row per deviation item)

| Key | Meaning |
|---|---|
| `item_id` | `<measure>_<opened_at>` |
| `measure` | the measure key as in the snapshot |
| `direction` | `above` or `below` |
| `size_at_open`, `size_peak` | position label at opening and at its worst |
| `opened_at`, `peak_at`, `closed_at` | timestamps (`closed_at` null while open) |
| `peak_value` | the value at the worst point |
| `trigger` | `persistence` or `severe` |
| `status` | `open` or `closed` |
| `handed_off_at` | when the hand-off record was written |
| `context_json` | context at the moment it opened |

### 7.3 Hand-off record

```json
{
  "handoff_id": "handoff_glucose_2026-09-17T22:30",
  "item_id": "glucose_2026-09-17T22:30",
  "written_at": "2026-09-17T22:30:00+05:30",
  "measure": "glucose",
  "direction": "above",
  "size": "clearly",
  "trigger": "persistence",
  "value": 185.0,
  "clinical_status": "high",
  "usual_basis": "meal_relative",
  "position_z": 2.3,
  "opened_at": "2026-09-17T22:30:00+05:30",
  "context": {
    "last_meal": {"label": "festive_dinner", "time": "2026-09-17T21:28:00+05:30", "minutes_ago": 62},
    "medication": {"taken": 1, "expected": 3, "missed": ["metformin", "levothyroxine"]},
    "sleep_last_night": {"value": 3.8, "position": "clearly below"},
    "other_open_items": ["sleep_duration", "resting_heart_rate", "blood_pressure", "medication_adherence", "heart_rate"],
    "diary_today_count": 2
  },
  "snapshot_as_of": "2026-09-17T22:30:00+05:30"
}
```

### 7.4 Quality notes (strings in `quality`)

| Code | Meaning |
|---|---|
| `rejected_latest:<measure>` | the newest value was rejected as questionable; last good value kept |
| `stale:<measure>` | value is past its freshness limit |
| `no_data:<measure>` | no value has ever arrived |
| `no_baseline_yet` | early days; no usual available |
| `usual_fallback:<measure>` | fewer than `min_samples_usual` samples; the other basis was used |
| `baseline_late` | the baseline for `D - 1` is not available; the previous day's usual is used and marked one day old |

---

## 8. Key dictionary

### 8.1 Input keys

| Source | Keys |
|---|---|
| `raw_events` | `id`, `event_id`, `timestamp`, `biomarker`, `value`, `status`, `source_type`, `paired_to`, `candidate_type`, `lag_minutes` |
| `context_events` | `id`, `stream`, `timestamp`, `date`, `value_num`, `value_text`, `category`, `meta_json` |
| Baseline profile | `stream`, `as_of`, `n_days`, `median`, `sd`, `usual_status`, `share_non_normal` |
| Reading-level usual | `stream`, `basis`, `context`, `as_of`, `n`, `median`, `sd`, `p10`, `p90` |
| Config | every key in 4.3 |

### 8.2 Working keys (exist during a tick, partly in the snapshot)

| Key | Meaning |
|---|---|
| `as_of`, `baseline_asof` | tick time; date of the usual |
| `value`, `value_time`, `age_minutes`, `current` | the latest available value and its freshness |
| `rejected_latest` | the newest value was rejected |
| `clinical_status` | carried from the Threshold Evaluator |
| `usual`, `usual_alt` | the usual chosen and the alternative basis |
| `z`, `label`, `share_at_least_as_bad` | position |
| `run.direction`, `run.count`, `run.close_count` | persistence counters |
| `severe` | boolean, true for a severe value |
| `minutes_since_meal` (bucketed), `meal_kind` | meal-relative context for glucose |

### 8.3 Output keys

`snapshot` (7.1), `state_log` row (7.2), `state_items` row (7.2), hand-off record (7.3), `quality` codes (7.4). All keys appear in the sections above.

---

## 9. Worked example: Meera, 2026-09-17, 21:30 to 23:30

Real values from the input files. The usuals were computed from earlier days with the baseline's definitions, not read from the database. Dinner was logged at 21:28. Medicines (1 of 3 taken) are available from 21:00 and the diary from 21:00 per the example config. Glucose uses `meal_relative_with_clock_fallback`, so it is compared with her usual at the same minutes after dinner.

| Tick | Glucose | Minutes after meal (bucket) | Usual after meal | z | Glucose position | Heart rate | Usual (clock) | z | HR position | Event |
|---|---|---|---|---|---|---|---|---|---|---|
| 21:30 | 124.7 | 2 (0) | 120.4 | +0.4 | within | 106.9 | 85.4 | +2.1 | clearly above | HR run = 1 |
| 21:45 | 136.1 | 17 (15) | 127.4 | +0.7 | within | 112.0 | 83.6 | +2.7 | clearly above | **HR item opens** |
| 22:00 | 157.2 | 32 (30) | 136.8 | +1.7 | slightly above | 99.4 | 80.9 | +1.8 | slightly above | HR close count = 1 |
| 22:15 | 172.3 | 47 (45) | 144.5 | +2.2 | clearly above | 98.8 | 78.7 | +2.0 | clearly above | glucose run = 1; HR close count resets |
| 22:30 | 185.0 | 62 (60) | 153.5 | +2.3 | clearly above | 102.9 | 76.3 | +2.8 | clearly above | **glucose item opens; hand-off written** |
| 22:45 | 185.4 | 77 (75) | 160.9 | +1.7 | slightly above | 103.2 | 74.4 | +3.0 | clearly above | glucose close count = 1 (peak value 185.4) |
| 23:00 | 177.3 | 92 (90) | 153.9 | +1.6 | slightly above | 93.2 | 72.3 | +2.2 | clearly above | **glucose item closes** (2 readings at slightly or better) |
| 23:15 | 162.0 | 107 (105) | 146.1 | +1.2 | slightly above | 93.0 | 70.6 | +2.6 | clearly above | HR still open |
| 23:30 | 152.9 | 122 (120) | 137.3 | +1.2 | slightly above | 92.3 | 69.2 | +3.0 | clearly above | HR still open |

Glucose has clinical status `high` from the 21:45 reading on (the Threshold Evaluator's reference is a fasting one, so almost every post-meal reading reads `high`). This is why the clinical status cannot be the deviation flag.

Compared with the **clock-time** usual instead (shown as `usual_alt`), glucose reads clearly above from 22:15 to 23:30 (z +2.1 to +3.6). Most of that is because dinner was at 21:28, while her usual dinner is about 20:16. The meal-relative usual says it is a high post-dinner value, not an extreme one.

**The closed glucose item**, as stored:

```json
{
  "item_id": "glucose_2026-09-17T22:30",
  "measure": "glucose",
  "direction": "above",
  "size_at_open": "clearly",
  "size_peak": "clearly",
  "opened_at": "2026-09-17T22:30:00+05:30",
  "peak_at": "2026-09-17T22:30:00+05:30",
  "closed_at": "2026-09-17T23:00:00+05:30",
  "peak_value": 185.4,
  "trigger": "persistence",
  "status": "closed",
  "handed_off_at": "2026-09-17T22:30:00+05:30"
}
```

The slow measures (sleep, resting heart rate, blood pressure, medicines) opened items earlier in the day, when they became available (07:00, 07:08, 08:08, 21:00). Each stays open until a newer value for that measure is within `slightly` or better.

---

## 10. Properties that must hold

1. **Deterministic.** The same inputs and config always give the same state log. A replay reproduces the log exactly.
2. **No look-ahead.** No tick uses a value before its availability time, nor a usual that includes the tick's own date.
3. **Read-only toward everything else.** Nothing is written to `raw_events`, `context_events`, `memory_v2` or any baseline table.
4. **Idempotent.** Running the same tick again writes the same row and no duplicate items or hand-offs.
5. **One hand-off per item,** and none for items that never open.
6. **A rejected or stale value never counts** toward a run, and never keeps an item open.
7. **A measure with no new value at a tick** keeps its last value and its age grows.
8. **The clinical status is only carried,** never recomputed.
9. **Generic.** No patient-specific value, stream name, medicine, threshold or timezone appears outside config and the stream registry. A second patient with different streams (for example no mood stream) runs with config changes only.
10. **No LLM** and no network call anywhere in the engine.
11. **The first `min_history_days` days** produce snapshots without positions and without persistence-triggered items.

---

## 11. Limits, assumptions and open items

| Item | What I assumed | Where it matters |
|---|---|---|
| Position labels, the 2-in-a-row rule, freshness limits and availability times | Proposals, not clinical standards. All in config. | Tuning per patient |
| Glucose usual | Meal-relative with clock-time fallback (the default above) | A late meal reads as a deviation on the clock-time basis |
| Meal kind | Matched by label text (for example a label containing "dinner") | A patient whose meal labels differ needs a mapping in config |
| Count measures (medicines) | A percentile of her own history, not a spread | Few days of history make the percentile coarse |
| Blood pressure | One reading, judged against the profile, with systolic and diastolic separately | No BP staging |
| Daily records with no time | Need an `available_at` rule | Without one, the evening's data could be used too early in a replay |
| Hourly steps | Compared with the usual for that hour of day | An hour still in progress is not compared |
| Severe statuses | `critical_high` and `critical_low`, if the evaluator emits them. The data seen so far uses `borderline` and `high`/`low` only. | Severe path may be rarely used |
| Baseline is built once per day | If late, the previous usual is used and marked | Live use needs a scheduler (out of scope) |
| Size of the log | About 33,800 ticks a year at roughly 3 to 4 KB each (an estimate, not measured) | Storage only |

Known data issues carried from the baseline (report, do not patch): the five isolated 65.0 glucose readings are not caught by the generic rule; labs sit above the glucose-based estimate; some location and diary-note inputs contain errors and are shown as given.

---

## 12. Glossary

| Term | Meaning |
|---|---|
| Tick | One evaluation of all measures at one moment |
| Usual | Her typical level and spread for a measure, as of the start of today |
| Position | Where the latest value sits against her usual, in units of her own spread |
| Run | Consecutive new readings at or beyond the opening position, in one direction |
| Deviation item | A record that a measure has been off her usual for long enough, with a start, a peak and an end |
| Hand-off | One record written when an item opens, for the next component |
| Current | A value inside its freshness limit |
| Clinical status | The Threshold Evaluator's tag (for example `high`), carried unchanged |
| Questionable reading | A value the baseline's cleaning rejects (outside the device range or an impossible jump) |
| as-of | Using only what was known at that moment |