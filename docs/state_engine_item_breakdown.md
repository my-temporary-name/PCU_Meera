# State Engine: item breakdown

Read-only. Source: `output/state_engine.db` (565 items, 565 hand-offs). No interpretation. Month and day are by `opened_at` (Asia/Kolkata). Direction is `above` / `below` the patient's usual. CSV exports: `output/state_items.csv`, `output/state_handoffs.csv`.

## a) Items opened by month x measure x direction

| month | measure | above | below | total |
|---|---|---|---|---|
| 2025-10 | glucose | 16 | 1 | 17 |
| 2025-10 | heart_rate | 20 |  | 20 |
| 2025-10 | resting_heart_rate | 1 |  | 1 |
| 2025-10 | medication_adherence |  | 1 | 1 |
| 2025-10 | screen_time | 1 | 2 | 3 |
| 2025-10 | sleep_duration |  | 1 | 1 |
| 2025-10 | sedentary_time |  | 1 | 1 |
| 2025-10 | step_count | 1 |  | 1 |
| 2025-10 | hydration | 1 |  | 1 |
| 2025-11 | glucose | 17 | 2 | 19 |
| 2025-11 | heart_rate | 13 | 2 | 15 |
| 2025-11 | resting_heart_rate | 1 |  | 1 |
| 2025-11 | medication_adherence |  | 2 | 2 |
| 2025-11 | screen_time | 3 |  | 3 |
| 2025-11 | sleep_duration |  | 1 | 1 |
| 2025-11 | blood_pressure | 2 |  | 2 |
| 2025-11 | hydration |  | 1 | 1 |
| 2025-12 | glucose | 2 | 4 | 6 |
| 2025-12 | heart_rate | 12 |  | 12 |
| 2025-12 | medication_adherence |  | 1 | 1 |
| 2025-12 | screen_time |  | 1 | 1 |
| 2025-12 | sedentary_time |  | 2 | 2 |
| 2025-12 | step_count | 2 |  | 2 |
| 2026-01 | glucose | 30 | 5 | 35 |
| 2026-01 | heart_rate | 8 |  | 8 |
| 2026-01 | resting_heart_rate | 1 |  | 1 |
| 2026-01 | medication_adherence |  | 6 | 6 |
| 2026-01 | blood_pressure |  | 1 | 1 |
| 2026-02 | glucose | 14 | 13 | 27 |
| 2026-02 | heart_rate | 12 |  | 12 |
| 2026-02 | resting_heart_rate | 1 |  | 1 |
| 2026-02 | medication_adherence |  | 3 | 3 |
| 2026-02 | screen_time |  | 1 | 1 |
| 2026-02 | sleep_duration |  | 1 | 1 |
| 2026-02 | blood_pressure |  | 1 | 1 |
| 2026-02 | sedentary_time |  | 2 | 2 |
| 2026-02 | step_count | 2 |  | 2 |
| 2026-02 | hydration | 1 |  | 1 |
| 2026-03 | glucose | 16 | 15 | 31 |
| 2026-03 | heart_rate | 23 |  | 23 |
| 2026-03 | resting_heart_rate | 4 |  | 4 |
| 2026-03 | medication_adherence |  | 5 | 5 |
| 2026-03 | screen_time | 2 | 1 | 3 |
| 2026-03 | sleep_duration |  | 3 | 3 |
| 2026-03 | sedentary_time |  | 1 | 1 |
| 2026-03 | step_count | 1 |  | 1 |
| 2026-04 | glucose |  | 30 | 30 |
| 2026-04 | heart_rate | 13 | 5 | 18 |
| 2026-04 | resting_heart_rate | 1 | 2 | 3 |
| 2026-04 | medication_adherence |  | 2 | 2 |
| 2026-04 | sleep_duration |  | 1 | 1 |
| 2026-04 | blood_pressure |  | 1 | 1 |
| 2026-04 | sedentary_time |  | 2 | 2 |
| 2026-04 | step_count | 2 |  | 2 |
| 2026-05 | glucose |  | 25 | 25 |
| 2026-05 | heart_rate |  | 7 | 7 |
| 2026-05 | resting_heart_rate |  | 6 | 6 |
| 2026-05 | medication_adherence |  | 1 | 1 |
| 2026-05 | blood_pressure |  | 1 | 1 |
| 2026-06 | glucose | 2 | 10 | 12 |
| 2026-06 | hydration |  | 1 | 1 |
| 2026-07 | glucose |  | 12 | 12 |
| 2026-07 | heart_rate | 3 |  | 3 |
| 2026-07 | medication_adherence |  | 2 | 2 |
| 2026-07 | sleep_duration |  | 1 | 1 |
| 2026-08 | glucose |  | 69 | 69 |
| 2026-08 | heart_rate |  | 33 | 33 |
| 2026-08 | resting_heart_rate |  | 6 | 6 |
| 2026-08 | blood_pressure |  | 3 | 3 |
| 2026-09 | glucose | 2 |  | 2 |
| 2026-09 | heart_rate | 20 | 2 | 22 |
| 2026-09 | resting_heart_rate | 3 |  | 3 |
| 2026-09 | medication_adherence |  | 1 | 1 |
| 2026-09 | screen_time | 2 | 1 | 3 |
| 2026-09 | sleep_duration |  | 2 | 2 |
| 2026-09 | blood_pressure | 1 |  | 1 |
| 2026-09 | sedentary_time |  | 1 | 1 |
| 2026-09 | step_count | 1 |  | 1 |
| 2026-09 | hydration | 1 |  | 1 |


Totals over the year:

| measure | above | below | total |
|---|---|---|---|
| glucose | 99 | 186 | 285 |
| heart_rate | 124 | 49 | 173 |
| resting_heart_rate | 12 | 14 | 26 |
| medication_adherence | 0 | 24 | 24 |
| screen_time | 8 | 6 | 14 |
| sleep_duration | 0 | 10 | 10 |
| blood_pressure | 3 | 7 | 10 |
| sedentary_time | 0 | 9 | 9 |
| step_count | 9 | 0 | 9 |
| hydration | 3 | 2 | 5 |


## b) Glucose and heart rate by direction

### Items per direction by month


**glucose**

| month | above | below | total |
|---|---|---|---|
| 2025-10 | 16 | 1 | 17 |
| 2025-11 | 17 | 2 | 19 |
| 2025-12 | 2 | 4 | 6 |
| 2026-01 | 30 | 5 | 35 |
| 2026-02 | 14 | 13 | 27 |
| 2026-03 | 16 | 15 | 31 |
| 2026-04 | 0 | 30 | 30 |
| 2026-05 | 0 | 25 | 25 |
| 2026-06 | 2 | 10 | 12 |
| 2026-07 | 0 | 12 | 12 |
| 2026-08 | 0 | 69 | 69 |
| 2026-09 | 2 | 0 | 2 |


**heart_rate**

| month | above | below | total |
|---|---|---|---|
| 2025-10 | 20 | 0 | 20 |
| 2025-11 | 13 | 2 | 15 |
| 2025-12 | 12 | 0 | 12 |
| 2026-01 | 8 | 0 | 8 |
| 2026-02 | 12 | 0 | 12 |
| 2026-03 | 23 | 0 | 23 |
| 2026-04 | 13 | 5 | 18 |
| 2026-05 | 0 | 7 | 7 |
| 2026-06 | 0 | 0 | 0 |
| 2026-07 | 3 | 0 | 3 |
| 2026-08 | 0 | 33 | 33 |
| 2026-09 | 20 | 2 | 22 |


### Peak value and peak position by direction

Peak = the reading with the largest position while the item was open. `peak |z|` is the stored `peak_metric` (the position in SDs of her own spread at the peak). Peak label counts are `size_peak` (clearly / far) with the direction.


| measure | direction | items | median peak value | min peak value | max peak value | median peak abs z | peak position labels (count) |
|---|---|---|---|---|---|---|---|
| glucose | above | 99 | 147.1 | 137.8 | 246.8 | 2.5 | clearly above 89, far above 10 |
| glucose | below | 186 | 101.15 | 65.0 | 134.8 | 2.36 | clearly below 181, far below 5 |
| heart_rate | above | 124 | 111.6 | 77.0 | 136.8 | 3.08 | clearly above 101, far above 23 |
| heart_rate | below | 49 | 56.0 | 50.6 | 71.4 | 2.3 | clearly below 49 |


(units: glucose mg/dL, heart rate bpm.)


## c) The 10 days in August 2026 with the most items opened

Ties are broken by date.

| date | items | measures | direction |
|---|---|---|---|
| 2026-08-21 | 11 | glucose 11 | below 11 |
| 2026-08-04 | 10 | glucose 8, heart_rate 2 | below 10 |
| 2026-08-17 | 10 | glucose 7, heart_rate 3 | below 10 |
| 2026-08-01 | 9 | glucose 7, heart_rate 1, blood_pressure 1 | below 9 |
| 2026-08-03 | 8 | glucose 6, heart_rate 2 | below 8 |
| 2026-08-26 | 8 | glucose 7, resting_heart_rate 1 | below 8 |
| 2026-08-08 | 7 | glucose 4, heart_rate 3 | below 7 |
| 2026-08-20 | 7 | glucose 3, heart_rate 3, resting_heart_rate 1 | below 7 |
| 2026-08-15 | 5 | heart_rate 5 | below 5 |
| 2026-08-16 | 5 | heart_rate 4, glucose 1 | below 5 |


## d) Items of exactly 30 minutes (154)

### By measure

| measure | items |
|---|---|
| glucose | 106 |
| heart_rate | 48 |

### By direction

| direction | items |
|---|---|
| above | 60 |
| below | 94 |

### By month

| month | items |
|---|---|
| 2025-10 | 12 |
| 2025-11 | 7 |
| 2025-12 | 6 |
| 2026-01 | 14 |
| 2026-02 | 14 |
| 2026-03 | 16 |
| 2026-04 | 14 |
| 2026-05 | 9 |
| 2026-06 | 7 |
| 2026-07 | 6 |
| 2026-08 | 42 |
| 2026-09 | 7 |


### By measure x direction

| measure | above | below |
|---|---|---|
| glucose | 36 | 70 |
| heart_rate | 24 | 24 |


## e) The days with more than 5 items opened (35)

| date | items | measures | direction |
|---|---|---|---|
| 2025-10-15 | 8 | glucose 4, heart_rate 2, resting_heart_rate 1, medication_adherence 1 | above 7, below 1 |
| 2025-10-19 | 9 | heart_rate 3, glucose 2, screen_time 1, sedentary_time 1, step_count 1, sleep_duration 1 | above 5, below 4 |
| 2025-10-20 | 8 | heart_rate 5, glucose 2, hydration 1 | above 8 |
| 2025-10-31 | 6 | glucose 5, heart_rate 1 | above 6 |
| 2025-11-10 | 6 | glucose 5, blood_pressure 1 | above 6 |
| 2025-11-19 | 9 | heart_rate 4, glucose 3, hydration 1, resting_heart_rate 1 | above 8, below 1 |
| 2025-12-25 | 6 | heart_rate 2, screen_time 1, sedentary_time 1, step_count 1, glucose 1 | above 4, below 2 |
| 2026-01-12 | 8 | glucose 6, heart_rate 2 | above 8 |
| 2026-01-24 | 8 | glucose 7, heart_rate 1 | above 8 |
| 2026-01-28 | 7 | glucose 7 | above 7 |
| 2026-01-30 | 8 | glucose 7, medication_adherence 1 | above 7, below 1 |
| 2026-02-13 | 8 | heart_rate 3, sedentary_time 1, step_count 1, sleep_duration 1, blood_pressure 1, glucose 1 | above 4, below 4 |
| 2026-02-17 | 6 | glucose 6 | above 6 |
| 2026-03-04 | 12 | glucose 6, heart_rate 5, resting_heart_rate 1 | above 8, below 4 |
| 2026-03-06 | 8 | glucose 8 | below 8 |
| 2026-03-16 | 8 | glucose 5, heart_rate 1, sleep_duration 1, medication_adherence 1 | above 6, below 2 |
| 2026-03-17 | 11 | glucose 6, heart_rate 3, screen_time 1, resting_heart_rate 1 | above 11 |
| 2026-04-11 | 8 | heart_rate 6, glucose 2 | above 6, below 2 |
| 2026-04-17 | 8 | glucose 8 | below 8 |
| 2026-04-18 | 8 | glucose 5, heart_rate 3 | above 3, below 5 |
| 2026-04-25 | 7 | glucose 3, heart_rate 3, resting_heart_rate 1 | below 7 |
| 2026-05-17 | 6 | glucose 6 | below 6 |
| 2026-05-25 | 13 | glucose 10, heart_rate 2, resting_heart_rate 1 | below 13 |
| 2026-05-27 | 6 | glucose 4, heart_rate 1, resting_heart_rate 1 | below 6 |
| 2026-07-03 | 7 | glucose 7 | below 7 |
| 2026-08-01 | 9 | glucose 7, heart_rate 1, blood_pressure 1 | below 9 |
| 2026-08-03 | 8 | glucose 6, heart_rate 2 | below 8 |
| 2026-08-04 | 10 | glucose 8, heart_rate 2 | below 10 |
| 2026-08-08 | 7 | glucose 4, heart_rate 3 | below 7 |
| 2026-08-17 | 10 | glucose 7, heart_rate 3 | below 10 |
| 2026-08-20 | 7 | glucose 3, heart_rate 3, resting_heart_rate 1 | below 7 |
| 2026-08-21 | 11 | glucose 11 | below 11 |
| 2026-08-26 | 8 | glucose 7, resting_heart_rate 1 | below 8 |
| 2026-09-13 | 8 | heart_rate 4, hydration 1, screen_time 1, sedentary_time 1, step_count 1 | above 6, below 2 |
| 2026-09-17 | 7 | heart_rate 4, screen_time 1, resting_heart_rate 1, glucose 1 | above 7 |


## 3. Five random August 2026 items, in full

Chosen with `random.Random(20261003).sample(...)` from the 111 items opened in August 2026. For each: the `state_items` row, the `state_handoffs` record, and the `state_log` snapshot of the first tick at which the item is listed in `open_items`. JSON pretty-printed (stored compact).


### glucose_2026-08-01T02:00

Opened 2026-08-01T02:00:00+05:30; the snapshot is the tick 2026-08-01T02:00:00+05:30.

**Item (`state_items`)**

```json
{
  "item_id": "glucose_2026-08-01T02:00",
  "measure": "glucose",
  "direction": "below",
  "size_at_open": "clearly",
  "size_peak": "clearly",
  "opened_at": "2026-08-01T02:00:00+05:30",
  "peak_at": "2026-08-01T02:00:00+05:30",
  "closed_at": "2026-08-01T02:30:00+05:30",
  "peak_value": 98.3,
  "trigger": "persistence",
  "status": "closed",
  "handed_off_at": "2026-08-01T02:00:00+05:30",
  "close_reason": "recovered",
  "peak_metric": 2.2200876105343914,
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-07-31T20:18:00+05:30",
      "minutes_ago": 342
    },
    "medication": null,
    "sleep_last_night": {
      "value": 6.9,
      "position": "within"
    },
    "other_open_items": [],
    "diary_today_count": 0
  }
}
```

**Hand-off (`state_handoffs`)**

```json
{
  "handoff_id": "handoff_glucose_2026-08-01T02:00",
  "item_id": "glucose_2026-08-01T02:00",
  "written_at": "2026-08-01T02:00:00+05:30",
  "measure": "glucose",
  "direction": "below",
  "size": "clearly",
  "trigger": "persistence",
  "value": 98.3,
  "clinical_status": "normal",
  "usual_basis": "clock_time",
  "position_z": -2.22,
  "opened_at": "2026-08-01T02:00:00+05:30",
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-07-31T20:18:00+05:30",
      "minutes_ago": 342
    },
    "medication": null,
    "sleep_last_night": {
      "value": 6.9,
      "position": "within"
    },
    "other_open_items": [],
    "diary_today_count": 0
  },
  "snapshot_as_of": "2026-08-01T02:00:00+05:30"
}
```

**Snapshot at 2026-08-01T02:00:00+05:30 (`state_log`)**

```json
{
  "as_of": "2026-08-01T02:00:00+05:30",
  "baseline_asof": "2026-07-31",
  "config_version": "meera_iyer_v1-state-b597db13fd6e",
  "baseline_config_version": "meera_iyer_v1-fb3c0fa91857",
  "early_days": false,
  "measures": {
    "glucose": {
      "value": 98.3,
      "unit": "mg/dL",
      "value_time": "2026-08-01T02:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "normal",
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "02:00",
          "band_minutes": 30
        },
        "n": 1504,
        "median": 120.3,
        "sd": 9.91
      },
      "usual_alt": null,
      "position": {
        "z": -2.22,
        "label": "clearly below"
      },
      "run": {
        "direction": "below",
        "count": 2,
        "close_count": 0
      },
      "open_item_id": "glucose_2026-08-01T02:00"
    },
    "heart_rate": {
      "value": 57.1,
      "unit": "bpm",
      "value_time": "2026-08-01T02:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "low",
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "02:00",
          "band_minutes": 30
        },
        "n": 1520,
        "median": 68.9,
        "sd": 5.77
      },
      "position": {
        "z": -2.05,
        "label": "clearly below"
      },
      "run": {
        "direction": "below",
        "count": 1,
        "close_count": 0
      },
      "open_item_id": null
    },
    "step_count": {
      "value": 2010.0,
      "unit": "steps",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 120,
      "current": true,
      "clinical_status": "low",
      "usual": {
        "basis": "profile",
        "n": 293,
        "median": 2047.0,
        "sd": 1404.71
      },
      "position": {
        "z": -0.03,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sleep_duration": {
      "value": 6.9,
      "unit": "hours",
      "value_time": "2026-07-31T07:00:00+05:30",
      "age_minutes": 1140,
      "current": true,
      "clinical_status": "borderline_low",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 6.9,
        "sd": 0.79
      },
      "position": {
        "z": 0.0,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "resting_heart_rate": {
      "value": 72.0,
      "unit": "bpm",
      "value_time": "2026-07-31T07:00:00+05:30",
      "age_minutes": 1140,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 77.0,
        "sd": 4.56
      },
      "position": {
        "z": -1.1,
        "label": "slightly below"
      },
      "open_item_id": null,
      "overdue": false
    },
    "blood_pressure": {
      "value": {
        "systolic": 119.0,
        "diastolic": 80.0
      },
      "unit": "mmHg",
      "value_time": "2026-07-31T08:17:00+05:30",
      "age_minutes": 1063,
      "current": true,
      "clinical_status": "borderline_high",
      "usual": {
        "basis": "profile",
        "systolic": {
          "n": 119,
          "median": 125.0,
          "sd": 6.84
        },
        "diastolic": {
          "n": 119,
          "median": 81.0,
          "sd": 4.47
        }
      },
      "position": {
        "systolic": {
          "z": -0.88,
          "label": "within"
        },
        "diastolic": {
          "z": -0.22,
          "label": "within"
        },
        "worst": "systolic",
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "medication_adherence": {
      "taken": 3,
      "expected": 3,
      "missed": [],
      "value_time": "2026-07-31T21:00:00+05:30",
      "current": false,
      "usual": {
        "basis": "history_percentile",
        "share_all_taken": 0.5
      },
      "position": {
        "share_at_least_as_bad": 1.0,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "mood_state": {
      "label": "proud",
      "block": "evening",
      "value_time": "2026-07-31T21:00:00+05:30",
      "current": true
    },
    "hydration": {
      "value": 1956.0,
      "unit": "mL",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 120,
      "current": true,
      "clinical_status": "borderline_low",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 2021.0,
        "sd": 179.58
      },
      "position": {
        "z": -0.36,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "screen_time": {
      "value": 5.0,
      "unit": "hours",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 120,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 5.5,
        "sd": 1.39
      },
      "position": {
        "z": -0.36,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sedentary_time": {
      "value": 684.0,
      "unit": "minutes",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 120,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 689.0,
        "sd": 70.12
      },
      "position": {
        "z": -0.07,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "hba1c": {
      "value": 7.0,
      "unit": "%",
      "value_time": "2026-03-07T00:00:00+05:30",
      "age_minutes": 211800,
      "current": false,
      "clinical_status": "high",
      "overdue": true
    }
  },
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-07-31T20:18:00+05:30",
      "minutes_ago": 342
    },
    "diary_today": [],
    "yesterday_memory_headline": "Month-end reflection with improvement."
  },
  "open_items": [
    "glucose_2026-08-01T02:00"
  ],
  "quality": [
    "overdue:hba1c"
  ]
}
```


### glucose_2026-08-01T07:00

Opened 2026-08-01T07:00:00+05:30; the snapshot is the tick 2026-08-01T07:00:00+05:30.

**Item (`state_items`)**

```json
{
  "item_id": "glucose_2026-08-01T07:00",
  "measure": "glucose",
  "direction": "below",
  "size_at_open": "clearly",
  "size_peak": "clearly",
  "opened_at": "2026-08-01T07:00:00+05:30",
  "peak_at": "2026-08-01T07:15:00+05:30",
  "closed_at": "2026-08-01T08:00:00+05:30",
  "peak_value": 97.1,
  "trigger": "persistence",
  "status": "closed",
  "handed_off_at": "2026-08-01T07:00:00+05:30",
  "close_reason": "recovered",
  "peak_metric": 2.2970943071397536,
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-07-31T20:18:00+05:30",
      "minutes_ago": 642
    },
    "medication": null,
    "sleep_last_night": {
      "value": 6.9,
      "position": "within"
    },
    "other_open_items": [],
    "diary_today_count": 0
  }
}
```

**Hand-off (`state_handoffs`)**

```json
{
  "handoff_id": "handoff_glucose_2026-08-01T07:00",
  "item_id": "glucose_2026-08-01T07:00",
  "written_at": "2026-08-01T07:00:00+05:30",
  "measure": "glucose",
  "direction": "below",
  "size": "clearly",
  "trigger": "persistence",
  "value": 98.2,
  "clinical_status": "normal",
  "usual_basis": "clock_time",
  "position_z": -2.16,
  "opened_at": "2026-08-01T07:00:00+05:30",
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-07-31T20:18:00+05:30",
      "minutes_ago": 642
    },
    "medication": null,
    "sleep_last_night": {
      "value": 6.9,
      "position": "within"
    },
    "other_open_items": [],
    "diary_today_count": 0
  },
  "snapshot_as_of": "2026-08-01T07:00:00+05:30"
}
```

**Snapshot at 2026-08-01T07:00:00+05:30 (`state_log`)**

```json
{
  "as_of": "2026-08-01T07:00:00+05:30",
  "baseline_asof": "2026-07-31",
  "config_version": "meera_iyer_v1-state-b597db13fd6e",
  "baseline_config_version": "meera_iyer_v1-fb3c0fa91857",
  "early_days": false,
  "measures": {
    "glucose": {
      "value": 98.2,
      "unit": "mg/dL",
      "value_time": "2026-08-01T07:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "normal",
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "07:00",
          "band_minutes": 30
        },
        "n": 1520,
        "median": 120.25,
        "sd": 10.21
      },
      "usual_alt": null,
      "position": {
        "z": -2.16,
        "label": "clearly below"
      },
      "run": {
        "direction": "below",
        "count": 2,
        "close_count": 0
      },
      "open_item_id": "glucose_2026-08-01T07:00"
    },
    "heart_rate": {
      "value": 80.4,
      "unit": "bpm",
      "value_time": "2026-08-01T07:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": null,
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "07:00",
          "band_minutes": 30
        },
        "n": 1520,
        "median": 83.2,
        "sd": 6.91
      },
      "position": {
        "z": -0.41,
        "label": "within"
      },
      "run": {
        "direction": "below",
        "count": 0,
        "close_count": 0
      },
      "open_item_id": null
    },
    "step_count": {
      "value": 2010.0,
      "unit": "steps",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 420,
      "current": true,
      "clinical_status": "low",
      "usual": {
        "basis": "profile",
        "n": 293,
        "median": 2047.0,
        "sd": 1404.71
      },
      "position": {
        "z": -0.03,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sleep_duration": {
      "value": 7.4,
      "unit": "hours",
      "value_time": "2026-08-01T07:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 304,
        "median": 6.9,
        "sd": 0.79
      },
      "position": {
        "z": 0.63,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "resting_heart_rate": {
      "value": 72.0,
      "unit": "bpm",
      "value_time": "2026-07-31T07:00:00+05:30",
      "age_minutes": 1440,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 77.0,
        "sd": 4.56
      },
      "position": {
        "z": -1.1,
        "label": "slightly below"
      },
      "open_item_id": null,
      "overdue": false
    },
    "blood_pressure": {
      "value": {
        "systolic": 119.0,
        "diastolic": 80.0
      },
      "unit": "mmHg",
      "value_time": "2026-07-31T08:17:00+05:30",
      "age_minutes": 1363,
      "current": true,
      "clinical_status": "borderline_high",
      "usual": {
        "basis": "profile",
        "systolic": {
          "n": 119,
          "median": 125.0,
          "sd": 6.84
        },
        "diastolic": {
          "n": 119,
          "median": 81.0,
          "sd": 4.47
        }
      },
      "position": {
        "systolic": {
          "z": -0.88,
          "label": "within"
        },
        "diastolic": {
          "z": -0.22,
          "label": "within"
        },
        "worst": "systolic",
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "medication_adherence": {
      "taken": 3,
      "expected": 3,
      "missed": [],
      "value_time": "2026-07-31T21:00:00+05:30",
      "current": false,
      "usual": {
        "basis": "history_percentile",
        "share_all_taken": 0.5
      },
      "position": {
        "share_at_least_as_bad": 1.0,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "mood_state": {
      "label": "proud",
      "block": "evening",
      "value_time": "2026-07-31T21:00:00+05:30",
      "current": false
    },
    "hydration": {
      "value": 1956.0,
      "unit": "mL",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 420,
      "current": true,
      "clinical_status": "borderline_low",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 2021.0,
        "sd": 179.58
      },
      "position": {
        "z": -0.36,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "screen_time": {
      "value": 5.0,
      "unit": "hours",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 420,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 5.5,
        "sd": 1.39
      },
      "position": {
        "z": -0.36,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sedentary_time": {
      "value": 684.0,
      "unit": "minutes",
      "value_time": "2026-08-01T00:00:00+05:30",
      "age_minutes": 420,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "n": 303,
        "median": 689.0,
        "sd": 70.12
      },
      "position": {
        "z": -0.07,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "hba1c": {
      "value": 7.0,
      "unit": "%",
      "value_time": "2026-03-07T00:00:00+05:30",
      "age_minutes": 212100,
      "current": false,
      "clinical_status": "high",
      "overdue": true
    }
  },
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-07-31T20:18:00+05:30",
      "minutes_ago": 642
    },
    "diary_today": [],
    "yesterday_memory_headline": "Month-end reflection with improvement."
  },
  "open_items": [
    "glucose_2026-08-01T07:00"
  ],
  "quality": [
    "overdue:hba1c"
  ]
}
```


### glucose_2026-08-03T17:00

Opened 2026-08-03T17:00:00+05:30; the snapshot is the tick 2026-08-03T17:00:00+05:30.

**Item (`state_items`)**

```json
{
  "item_id": "glucose_2026-08-03T17:00",
  "measure": "glucose",
  "direction": "below",
  "size_at_open": "clearly",
  "size_peak": "clearly",
  "opened_at": "2026-08-03T17:00:00+05:30",
  "peak_at": "2026-08-03T21:00:00+05:30",
  "closed_at": "2026-08-03T22:00:00+05:30",
  "peak_value": 115.7,
  "trigger": "persistence",
  "status": "closed",
  "handed_off_at": "2026-08-03T17:00:00+05:30",
  "close_reason": "recovered",
  "peak_metric": 2.665270057195449,
  "context": {
    "last_meal": {
      "label": "lunch",
      "time": "2026-08-03T13:33:00+05:30",
      "minutes_ago": 207
    },
    "medication": null,
    "sleep_last_night": {
      "value": 7.3,
      "position": "within"
    },
    "other_open_items": [
      "resting_heart_rate",
      "blood_pressure"
    ],
    "diary_today_count": 0
  }
}
```

**Hand-off (`state_handoffs`)**

```json
{
  "handoff_id": "handoff_glucose_2026-08-03T17:00",
  "item_id": "glucose_2026-08-03T17:00",
  "written_at": "2026-08-03T17:00:00+05:30",
  "measure": "glucose",
  "direction": "below",
  "size": "clearly",
  "trigger": "persistence",
  "value": 98.3,
  "clinical_status": "normal",
  "usual_basis": "clock_time",
  "position_z": -2.11,
  "opened_at": "2026-08-03T17:00:00+05:30",
  "context": {
    "last_meal": {
      "label": "lunch",
      "time": "2026-08-03T13:33:00+05:30",
      "minutes_ago": 207
    },
    "medication": null,
    "sleep_last_night": {
      "value": 7.3,
      "position": "within"
    },
    "other_open_items": [
      "resting_heart_rate",
      "blood_pressure"
    ],
    "diary_today_count": 0
  },
  "snapshot_as_of": "2026-08-03T17:00:00+05:30"
}
```

**Snapshot at 2026-08-03T17:00:00+05:30 (`state_log`)**

```json
{
  "as_of": "2026-08-03T17:00:00+05:30",
  "baseline_asof": "2026-08-02",
  "config_version": "meera_iyer_v1-state-b597db13fd6e",
  "baseline_config_version": "meera_iyer_v1-fb3c0fa91857",
  "early_days": false,
  "measures": {
    "glucose": {
      "value": 98.3,
      "unit": "mg/dL",
      "value_time": "2026-08-03T17:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "normal",
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "17:00",
          "band_minutes": 30
        },
        "n": 1519,
        "median": 120.2,
        "sd": 10.38
      },
      "usual_alt": null,
      "position": {
        "z": -2.11,
        "label": "clearly below"
      },
      "run": {
        "direction": "below",
        "count": 2,
        "close_count": 0
      },
      "open_item_id": "glucose_2026-08-03T17:00"
    },
    "heart_rate": {
      "value": 76.6,
      "unit": "bpm",
      "value_time": "2026-08-03T17:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": null,
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "17:00",
          "band_minutes": 30
        },
        "n": 1530,
        "median": 84.0,
        "sd": 9.26
      },
      "position": {
        "z": -0.8,
        "label": "within"
      },
      "run": {
        "direction": "below",
        "count": 0,
        "close_count": 0
      },
      "open_item_id": null
    },
    "step_count": {
      "value": 1794.0,
      "unit": "steps",
      "value_time": "2026-08-03T00:00:00+05:30",
      "age_minutes": 1020,
      "current": true,
      "clinical_status": "low",
      "usual": {
        "basis": "profile",
        "n": 295,
        "median": 2047.0,
        "sd": 1401.89
      },
      "position": {
        "z": -0.18,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sleep_duration": {
      "value": 7.3,
      "unit": "hours",
      "value_time": "2026-08-03T07:00:00+05:30",
      "age_minutes": 600,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 306,
        "median": 6.9,
        "sd": 0.79
      },
      "position": {
        "z": 0.51,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "resting_heart_rate": {
      "value": 67.0,
      "unit": "bpm",
      "value_time": "2026-08-03T07:29:00+05:30",
      "age_minutes": 571,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 306,
        "median": 77.0,
        "sd": 4.62
      },
      "position": {
        "z": -2.17,
        "label": "clearly below"
      },
      "open_item_id": "resting_heart_rate_2026-08-02T07:18",
      "overdue": false
    },
    "blood_pressure": {
      "value": {
        "systolic": 108.0,
        "diastolic": 70.0
      },
      "unit": "mmHg",
      "value_time": "2026-08-01T08:05:00+05:30",
      "age_minutes": 3415,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "systolic": {
          "n": 120,
          "median": 125.0,
          "sd": 6.84
        },
        "diastolic": {
          "n": 120,
          "median": 81.0,
          "sd": 4.45
        }
      },
      "position": {
        "systolic": {
          "z": -2.49,
          "label": "clearly below"
        },
        "diastolic": {
          "z": -2.47,
          "label": "clearly below"
        },
        "worst": "systolic",
        "label": "clearly below"
      },
      "open_item_id": "blood_pressure_2026-08-01T08:05",
      "overdue": false
    },
    "medication_adherence": {
      "taken": 2,
      "expected": 3,
      "missed": [
        "metformin"
      ],
      "value_time": "2026-08-02T21:00:00+05:30",
      "current": false,
      "usual": {
        "basis": "history_percentile",
        "share_all_taken": 0.51,
        "share_one_or_more_missed": 0.49
      },
      "position": {
        "share_at_least_as_bad": 0.49,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "mood_state": {
      "label": "calm",
      "block": "morning",
      "value_time": "2026-08-03T12:00:00+05:30",
      "current": true
    },
    "hydration": {
      "value": 1836.0,
      "unit": "mL",
      "value_time": "2026-08-03T00:00:00+05:30",
      "age_minutes": 1020,
      "current": true,
      "clinical_status": "borderline_low",
      "usual": {
        "basis": "profile",
        "n": 305,
        "median": 2021.0,
        "sd": 179.26
      },
      "position": {
        "z": -1.03,
        "label": "slightly below"
      },
      "open_item_id": null,
      "overdue": false
    },
    "screen_time": {
      "value": 5.9,
      "unit": "hours",
      "value_time": "2026-08-03T00:00:00+05:30",
      "age_minutes": 1020,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 305,
        "median": 5.5,
        "sd": 1.39
      },
      "position": {
        "z": 0.29,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sedentary_time": {
      "value": 695.0,
      "unit": "minutes",
      "value_time": "2026-08-03T00:00:00+05:30",
      "age_minutes": 1020,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "n": 305,
        "median": 689.0,
        "sd": 69.94
      },
      "position": {
        "z": 0.09,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "hba1c": {
      "value": 7.0,
      "unit": "%",
      "value_time": "2026-03-07T00:00:00+05:30",
      "age_minutes": 215580,
      "current": false,
      "clinical_status": "high",
      "overdue": true
    }
  },
  "context": {
    "last_meal": {
      "label": "lunch",
      "time": "2026-08-03T13:33:00+05:30",
      "minutes_ago": 207
    },
    "diary_today": [],
    "yesterday_memory_headline": "Missed metformin during a family visit."
  },
  "open_items": [
    "blood_pressure_2026-08-01T08:05",
    "resting_heart_rate_2026-08-02T07:18",
    "glucose_2026-08-03T17:00"
  ],
  "quality": [
    "overdue:hba1c"
  ]
}
```


### heart_rate_2026-08-09T18:30

Opened 2026-08-09T18:30:00+05:30; the snapshot is the tick 2026-08-09T18:30:00+05:30.

**Item (`state_items`)**

```json
{
  "item_id": "heart_rate_2026-08-09T18:30",
  "measure": "heart_rate",
  "direction": "below",
  "size_at_open": "clearly",
  "size_peak": "clearly",
  "opened_at": "2026-08-09T18:30:00+05:30",
  "peak_at": "2026-08-09T18:30:00+05:30",
  "closed_at": "2026-08-09T19:00:00+05:30",
  "peak_value": 67.2,
  "trigger": "persistence",
  "status": "closed",
  "handed_off_at": "2026-08-09T18:30:00+05:30",
  "close_reason": "recovered",
  "peak_metric": 2.2834491716410525,
  "context": {
    "last_meal": {
      "label": "lunch",
      "time": "2026-08-09T13:30:00+05:30",
      "minutes_ago": 300
    },
    "medication": null,
    "sleep_last_night": {
      "value": 7.4,
      "position": "within"
    },
    "other_open_items": [
      "resting_heart_rate",
      "blood_pressure"
    ],
    "diary_today_count": 0
  }
}
```

**Hand-off (`state_handoffs`)**

```json
{
  "handoff_id": "handoff_heart_rate_2026-08-09T18:30",
  "item_id": "heart_rate_2026-08-09T18:30",
  "written_at": "2026-08-09T18:30:00+05:30",
  "measure": "heart_rate",
  "direction": "below",
  "size": "clearly",
  "trigger": "persistence",
  "value": 67.2,
  "clinical_status": null,
  "usual_basis": "clock_time",
  "position_z": -2.28,
  "opened_at": "2026-08-09T18:30:00+05:30",
  "context": {
    "last_meal": {
      "label": "lunch",
      "time": "2026-08-09T13:30:00+05:30",
      "minutes_ago": 300
    },
    "medication": null,
    "sleep_last_night": {
      "value": 7.4,
      "position": "within"
    },
    "other_open_items": [
      "resting_heart_rate",
      "blood_pressure"
    ],
    "diary_today_count": 0
  },
  "snapshot_as_of": "2026-08-09T18:30:00+05:30"
}
```

**Snapshot at 2026-08-09T18:30:00+05:30 (`state_log`)**

```json
{
  "as_of": "2026-08-09T18:30:00+05:30",
  "baseline_asof": "2026-08-08",
  "config_version": "meera_iyer_v1-state-b597db13fd6e",
  "baseline_config_version": "meera_iyer_v1-fb3c0fa91857",
  "early_days": false,
  "measures": {
    "glucose": {
      "value": 106.1,
      "unit": "mg/dL",
      "value_time": "2026-08-09T18:30:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "borderline_high",
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "18:30",
          "band_minutes": 30
        },
        "n": 1559,
        "median": 120.0,
        "sd": 10.38
      },
      "usual_alt": null,
      "position": {
        "z": -1.34,
        "label": "slightly below"
      },
      "run": {
        "direction": "below",
        "count": 0,
        "close_count": 0
      },
      "open_item_id": null
    },
    "heart_rate": {
      "value": 67.2,
      "unit": "bpm",
      "value_time": "2026-08-09T18:30:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": null,
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "18:30",
          "band_minutes": 30
        },
        "n": 1560,
        "median": 89.7,
        "sd": 9.85
      },
      "position": {
        "z": -2.28,
        "label": "clearly below"
      },
      "run": {
        "direction": "below",
        "count": 2,
        "close_count": 0
      },
      "open_item_id": "heart_rate_2026-08-09T18:30"
    },
    "step_count": {
      "value": 3133.0,
      "unit": "steps",
      "value_time": "2026-08-09T00:00:00+05:30",
      "age_minutes": 1110,
      "current": true,
      "clinical_status": "low",
      "usual": {
        "basis": "profile",
        "n": 301,
        "median": 2052.0,
        "sd": 1389.7
      },
      "position": {
        "z": 0.78,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sleep_duration": {
      "value": 7.4,
      "unit": "hours",
      "value_time": "2026-08-09T07:00:00+05:30",
      "age_minutes": 690,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 312,
        "median": 6.9,
        "sd": 0.79
      },
      "position": {
        "z": 0.64,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "resting_heart_rate": {
      "value": 64.0,
      "unit": "bpm",
      "value_time": "2026-08-09T07:05:00+05:30",
      "age_minutes": 685,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 312,
        "median": 77.0,
        "sd": 4.77
      },
      "position": {
        "z": -2.72,
        "label": "clearly below"
      },
      "open_item_id": "resting_heart_rate_2026-08-07T07:20",
      "overdue": false
    },
    "blood_pressure": {
      "value": {
        "systolic": 109.0,
        "diastolic": 73.0
      },
      "unit": "mmHg",
      "value_time": "2026-08-07T08:03:00+05:30",
      "age_minutes": 3507,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "systolic": {
          "n": 122,
          "median": 125.0,
          "sd": 7.07
        },
        "diastolic": {
          "n": 122,
          "median": 81.0,
          "sd": 4.58
        }
      },
      "position": {
        "systolic": {
          "z": -2.26,
          "label": "clearly below"
        },
        "diastolic": {
          "z": -1.75,
          "label": "slightly below"
        },
        "worst": "systolic",
        "label": "clearly below"
      },
      "open_item_id": "blood_pressure_2026-08-07T08:03",
      "overdue": false
    },
    "medication_adherence": {
      "taken": 3,
      "expected": 3,
      "missed": [],
      "value_time": "2026-08-08T21:00:00+05:30",
      "current": false,
      "usual": {
        "basis": "history_percentile",
        "share_all_taken": 0.51
      },
      "position": {
        "share_at_least_as_bad": 1.0,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "mood_state": {
      "label": "focused",
      "block": "afternoon",
      "value_time": "2026-08-09T18:00:00+05:30",
      "current": true
    },
    "hydration": {
      "value": 2211.0,
      "unit": "mL",
      "value_time": "2026-08-09T00:00:00+05:30",
      "age_minutes": 1110,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 311,
        "median": 2021.0,
        "sd": 178.08
      },
      "position": {
        "z": 1.07,
        "label": "slightly above"
      },
      "open_item_id": null,
      "overdue": false
    },
    "screen_time": {
      "value": 5.4,
      "unit": "hours",
      "value_time": "2026-08-09T00:00:00+05:30",
      "age_minutes": 1110,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 311,
        "median": 5.5,
        "sd": 1.38
      },
      "position": {
        "z": -0.07,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sedentary_time": {
      "value": 653.0,
      "unit": "minutes",
      "value_time": "2026-08-09T00:00:00+05:30",
      "age_minutes": 1110,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "n": 311,
        "median": 688.0,
        "sd": 69.35
      },
      "position": {
        "z": -0.5,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "hba1c": {
      "value": 7.0,
      "unit": "%",
      "value_time": "2026-03-07T00:00:00+05:30",
      "age_minutes": 224310,
      "current": false,
      "clinical_status": "high",
      "overdue": true
    }
  },
  "context": {
    "last_meal": {
      "label": "lunch",
      "time": "2026-08-09T13:30:00+05:30",
      "minutes_ago": 300
    },
    "diary_today": [],
    "yesterday_memory_headline": "Nothing deviated from her usual."
  },
  "open_items": [
    "resting_heart_rate_2026-08-07T07:20",
    "blood_pressure_2026-08-07T08:03",
    "heart_rate_2026-08-09T18:30"
  ],
  "quality": [
    "overdue:hba1c"
  ]
}
```


### heart_rate_2026-08-20T04:00

Opened 2026-08-20T04:00:00+05:30; the snapshot is the tick 2026-08-20T04:00:00+05:30.

**Item (`state_items`)**

```json
{
  "item_id": "heart_rate_2026-08-20T04:00",
  "measure": "heart_rate",
  "direction": "below",
  "size_at_open": "clearly",
  "size_peak": "clearly",
  "opened_at": "2026-08-20T04:00:00+05:30",
  "peak_at": "2026-08-20T04:00:00+05:30",
  "closed_at": "2026-08-20T05:15:00+05:30",
  "peak_value": 53.9,
  "trigger": "persistence",
  "status": "closed",
  "handed_off_at": "2026-08-20T04:00:00+05:30",
  "close_reason": "recovered",
  "peak_metric": 2.40523281172318,
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-08-19T20:01:00+05:30",
      "minutes_ago": 479
    },
    "medication": null,
    "sleep_last_night": {
      "value": 6.9,
      "position": "within"
    },
    "other_open_items": [
      "glucose",
      "blood_pressure"
    ],
    "diary_today_count": 0
  }
}
```

**Hand-off (`state_handoffs`)**

```json
{
  "handoff_id": "handoff_heart_rate_2026-08-20T04:00",
  "item_id": "heart_rate_2026-08-20T04:00",
  "written_at": "2026-08-20T04:00:00+05:30",
  "measure": "heart_rate",
  "direction": "below",
  "size": "clearly",
  "trigger": "persistence",
  "value": 53.9,
  "clinical_status": "low",
  "usual_basis": "clock_time",
  "position_z": -2.41,
  "opened_at": "2026-08-20T04:00:00+05:30",
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-08-19T20:01:00+05:30",
      "minutes_ago": 479
    },
    "medication": null,
    "sleep_last_night": {
      "value": 6.9,
      "position": "within"
    },
    "other_open_items": [
      "glucose",
      "blood_pressure"
    ],
    "diary_today_count": 0
  },
  "snapshot_as_of": "2026-08-20T04:00:00+05:30"
}
```

**Snapshot at 2026-08-20T04:00:00+05:30 (`state_log`)**

```json
{
  "as_of": "2026-08-20T04:00:00+05:30",
  "baseline_asof": "2026-08-19",
  "config_version": "meera_iyer_v1-state-b597db13fd6e",
  "baseline_config_version": "meera_iyer_v1-fb3c0fa91857",
  "early_days": false,
  "measures": {
    "glucose": {
      "value": 95.3,
      "unit": "mg/dL",
      "value_time": "2026-08-20T04:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "normal",
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "04:00",
          "band_minutes": 30
        },
        "n": 1602,
        "median": 119.35,
        "sd": 10.7
      },
      "usual_alt": null,
      "position": {
        "z": -2.25,
        "label": "clearly below"
      },
      "run": {
        "direction": "below",
        "count": 1,
        "close_count": 0
      },
      "open_item_id": "glucose_2026-08-20T02:45"
    },
    "heart_rate": {
      "value": 53.9,
      "unit": "bpm",
      "value_time": "2026-08-20T04:00:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "low",
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "04:00",
          "band_minutes": 30
        },
        "n": 1615,
        "median": 68.9,
        "sd": 6.24
      },
      "position": {
        "z": -2.41,
        "label": "clearly below"
      },
      "run": {
        "direction": "below",
        "count": 2,
        "close_count": 0
      },
      "open_item_id": "heart_rate_2026-08-20T04:00"
    },
    "step_count": {
      "value": 2583.0,
      "unit": "steps",
      "value_time": "2026-08-20T00:00:00+05:30",
      "age_minutes": 240,
      "current": true,
      "clinical_status": "low",
      "usual": {
        "basis": "profile",
        "n": 311,
        "median": 2069.0,
        "sd": 1371.43
      },
      "position": {
        "z": 0.37,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sleep_duration": {
      "value": 6.9,
      "unit": "hours",
      "value_time": "2026-08-19T07:00:00+05:30",
      "age_minutes": 1260,
      "current": true,
      "clinical_status": "borderline_low",
      "usual": {
        "basis": "profile",
        "n": 322,
        "median": 6.9,
        "sd": 0.78
      },
      "position": {
        "z": 0.0,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "resting_heart_rate": {
      "value": 69.0,
      "unit": "bpm",
      "value_time": "2026-08-19T07:21:00+05:30",
      "age_minutes": 1239,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 322,
        "median": 77.0,
        "sd": 5.0
      },
      "position": {
        "z": -1.6,
        "label": "slightly below"
      },
      "open_item_id": null,
      "overdue": false
    },
    "blood_pressure": {
      "value": {
        "systolic": 112.0,
        "diastolic": 70.0
      },
      "unit": "mmHg",
      "value_time": "2026-08-19T08:14:00+05:30",
      "age_minutes": 1186,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "systolic": {
          "n": 126,
          "median": 125.0,
          "sd": 7.44
        },
        "diastolic": {
          "n": 126,
          "median": 81.0,
          "sd": 4.75
        }
      },
      "position": {
        "systolic": {
          "z": -1.75,
          "label": "slightly below"
        },
        "diastolic": {
          "z": -2.32,
          "label": "clearly below"
        },
        "worst": "diastolic",
        "label": "clearly below"
      },
      "open_item_id": "blood_pressure_2026-08-13T08:10",
      "overdue": false
    },
    "medication_adherence": {
      "taken": 3,
      "expected": 3,
      "missed": [],
      "value_time": "2026-08-19T21:00:00+05:30",
      "current": false,
      "usual": {
        "basis": "history_percentile",
        "share_all_taken": 0.52
      },
      "position": {
        "share_at_least_as_bad": 1.0,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "mood_state": {
      "label": "content",
      "block": "evening",
      "value_time": "2026-08-19T21:00:00+05:30",
      "current": true
    },
    "hydration": {
      "value": 2128.0,
      "unit": "mL",
      "value_time": "2026-08-20T00:00:00+05:30",
      "age_minutes": 240,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 322,
        "median": 2022.0,
        "sd": 176.59
      },
      "position": {
        "z": 0.6,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "screen_time": {
      "value": 4.8,
      "unit": "hours",
      "value_time": "2026-08-20T00:00:00+05:30",
      "age_minutes": 240,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 322,
        "median": 5.45,
        "sd": 1.36
      },
      "position": {
        "z": -0.48,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "sedentary_time": {
      "value": 663.0,
      "unit": "minutes",
      "value_time": "2026-08-20T00:00:00+05:30",
      "age_minutes": 240,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "n": 322,
        "median": 685.0,
        "sd": 68.4
      },
      "position": {
        "z": -0.32,
        "label": "within"
      },
      "open_item_id": null,
      "overdue": false
    },
    "hba1c": {
      "value": 7.0,
      "unit": "%",
      "value_time": "2026-03-07T00:00:00+05:30",
      "age_minutes": 239280,
      "current": false,
      "clinical_status": "high",
      "overdue": true
    }
  },
  "context": {
    "last_meal": {
      "label": "dinner",
      "time": "2026-08-19T20:01:00+05:30",
      "minutes_ago": 479
    },
    "diary_today": [],
    "yesterday_memory_headline": "Nothing deviated from her usual."
  },
  "open_items": [
    "blood_pressure_2026-08-13T08:10",
    "glucose_2026-08-20T02:45",
    "heart_rate_2026-08-20T04:00"
  ],
  "quality": [
    "overdue:hba1c"
  ]
}
```
