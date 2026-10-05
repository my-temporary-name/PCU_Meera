# State Engine: reference examples (real output)

These replace the hand-assembled example in `task/state_engine.md` section 9. Everything below is exported from the State Engine's own database `output/state_engine.db`, produced by `uv run python -m v0_code.state_engine.run --replay --rebuild` (config `meera_iyer_v1-state-847708f80ed7`, baseline `meera_iyer_v1-fb3c0fa91857`). JSON is pretty-printed here; it is stored compact. Nothing was edited.

Notes on reading it: `usual.context.minutes_since_meal` is the nearest 15-minute bucket; an item's `opened_at` / `closed_at` are the moment the triggering value became available (here equal to the tick); `usual_alt` is the other glucose basis (clock time) for information; `run.close_count` counts consecutive readings at "slightly" or better while an item is open.

## 1. Snapshot at 2026-09-17T22:45 (`state_log`, one row per tick)

```json
{
  "as_of": "2026-09-17T22:45:00+05:30",
  "baseline_asof": "2026-09-16",
  "config_version": "meera_iyer_v1-state-847708f80ed7",
  "baseline_config_version": "meera_iyer_v1-fb3c0fa91857",
  "early_days": false,
  "measures": {
    "glucose": {
      "value": 185.4,
      "unit": "mg/dL",
      "value_time": "2026-09-17T22:45:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": "high",
      "usual": {
        "basis": "meal_relative",
        "context": {
          "meal_kind": "dinner",
          "minutes_since_meal": 75
        },
        "n": 345,
        "median": 160.9,
        "sd": 14.58
      },
      "usual_alt": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "22:45",
          "band_minutes": 30
        },
        "n": 1733,
        "median": 124.9,
        "sd": 16.59,
        "z": 3.65,
        "label": "clearly above"
      },
      "position": {
        "z": 1.68,
        "label": "slightly above"
      },
      "run": {
        "direction": "above",
        "count": 0,
        "close_count": 1
      },
      "open_item_id": "glucose_2026-09-17T22:30",
      "open_item_class": "adverse"
    },
    "heart_rate": {
      "value": 103.2,
      "unit": "bpm",
      "value_time": "2026-09-17T22:45:00+05:30",
      "age_minutes": 0,
      "current": true,
      "rejected_latest": false,
      "clinical_status": null,
      "usual": {
        "basis": "clock_time",
        "context": {
          "time_of_day": "22:45",
          "band_minutes": 30
        },
        "n": 1755,
        "median": 74.4,
        "sd": 9.6
      },
      "position": {
        "z": 3.0,
        "label": "clearly above"
      },
      "run": {
        "direction": "above",
        "count": 3,
        "close_count": 0
      },
      "open_item_id": "heart_rate_2026-09-17T21:45",
      "open_item_class": "adverse"
    },
    "step_count": {
      "value": 2126.0,
      "unit": "steps",
      "value_time": "2026-09-17T00:00:00+05:30",
      "age_minutes": 1365,
      "current": true,
      "clinical_status": "low",
      "usual": {
        "basis": "profile",
        "n": 338,
        "median": 2092.0,
        "sd": 1379.55
      },
      "position": {
        "z": 0.02,
        "label": "within"
      },
      "open_item_id": null,
      "open_item_class": null,
      "overdue": false
    },
    "sleep_duration": {
      "value": 3.8,
      "unit": "hours",
      "value_time": "2026-09-17T07:00:00+05:30",
      "age_minutes": 945,
      "current": true,
      "clinical_status": "low",
      "usual": {
        "basis": "profile",
        "n": 351,
        "median": 6.9,
        "sd": 0.8
      },
      "position": {
        "z": -3.86,
        "label": "clearly below"
      },
      "open_item_id": "sleep_duration_2026-09-14T07:00",
      "open_item_class": "adverse",
      "overdue": false
    },
    "resting_heart_rate": {
      "value": 93.0,
      "unit": "bpm",
      "value_time": "2026-09-17T07:08:00+05:30",
      "age_minutes": 937,
      "current": true,
      "clinical_status": "normal",
      "usual": {
        "basis": "profile",
        "n": 351,
        "median": 77.0,
        "sd": 5.4
      },
      "position": {
        "z": 2.96,
        "label": "clearly above"
      },
      "open_item_id": "resting_heart_rate_2026-09-17T07:08",
      "open_item_class": "adverse",
      "overdue": false
    },
    "blood_pressure": {
      "value": {
        "systolic": 138.0,
        "diastolic": 94.0
      },
      "unit": "mmHg",
      "value_time": "2026-09-17T08:08:00+05:30",
      "age_minutes": 877,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "systolic": {
          "n": 140,
          "median": 125.0,
          "sd": 7.69
        },
        "diastolic": {
          "n": 140,
          "median": 81.0,
          "sd": 5.06
        }
      },
      "position": {
        "systolic": {
          "z": 1.69,
          "label": "slightly above"
        },
        "diastolic": {
          "z": 2.57,
          "label": "clearly above"
        },
        "worst": "diastolic",
        "label": "clearly above"
      },
      "open_item_id": "blood_pressure_2026-09-16T08:13",
      "open_item_class": "adverse",
      "overdue": false
    },
    "medication_adherence": {
      "taken": 1,
      "expected": 3,
      "missed": [
        "metformin",
        "levothyroxine"
      ],
      "value_time": "2026-09-17T21:00:00+05:30",
      "current": true,
      "usual": {
        "basis": "history_percentile",
        "share_all_taken": 0.52,
        "share_two_or_more_missed": 0.1
      },
      "position": {
        "share_at_least_as_bad": 0.1,
        "label": "clearly below"
      },
      "open_item_id": "medication_adherence_2026-09-11T21:00",
      "open_item_class": "adverse",
      "overdue": false
    },
    "mood_state": {
      "label": "tired",
      "block": "evening",
      "value_time": "2026-09-17T21:00:00+05:30",
      "current": true
    },
    "hydration": {
      "value": 1934.0,
      "unit": "mL",
      "value_time": "2026-09-17T00:00:00+05:30",
      "age_minutes": 1365,
      "current": true,
      "clinical_status": "borderline_low",
      "usual": {
        "basis": "profile",
        "n": 350,
        "median": 2026.0,
        "sd": 175.67
      },
      "position": {
        "z": -0.52,
        "label": "within"
      },
      "open_item_id": null,
      "open_item_class": null,
      "overdue": false
    },
    "screen_time": {
      "value": 9.5,
      "unit": "hours",
      "value_time": "2026-09-17T00:00:00+05:30",
      "age_minutes": 1365,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "n": 350,
        "median": 5.45,
        "sd": 1.46
      },
      "position": {
        "z": 2.77,
        "label": "clearly above"
      },
      "open_item_id": "screen_time_2026-09-17T00:00",
      "open_item_class": "adverse",
      "overdue": false
    },
    "sedentary_time": {
      "value": 689.0,
      "unit": "minutes",
      "value_time": "2026-09-17T00:00:00+05:30",
      "age_minutes": 1365,
      "current": true,
      "clinical_status": "high",
      "usual": {
        "basis": "profile",
        "n": 350,
        "median": 683.5,
        "sd": 68.73
      },
      "position": {
        "z": 0.08,
        "label": "within"
      },
      "open_item_id": null,
      "open_item_class": null,
      "overdue": false
    },
    "hba1c": {
      "value": 7.0,
      "unit": "%",
      "value_time": "2026-03-07T00:00:00+05:30",
      "age_minutes": 280725,
      "current": false,
      "clinical_status": "high",
      "overdue": true
    }
  },
  "context": {
    "last_meal": {
      "label": "festive_dinner",
      "time": "2026-09-17T21:28:00+05:30",
      "minutes_ago": 77
    },
    "diary_today": [
      {
        "category": "life_event",
        "text": "Quarter-close deadline day, delivered the numbers, largely deskbound, minimal proper meals"
      },
      {
        "category": "social_interaction",
        "text": "Reflected with husband on the layered month - tired, foggy, aware of slipped walks and medication timing; resolved to reset once both pressures ease, honestly acknowledging tonight wasn't that night"
      }
    ],
    "yesterday_memory_headline": "Missed multiple medicines during a stressful festival and work day."
  },
  "open_items": [
    "medication_adherence_2026-09-11T21:00",
    "sleep_duration_2026-09-14T07:00",
    "blood_pressure_2026-09-16T08:13",
    "screen_time_2026-09-17T00:00",
    "resting_heart_rate_2026-09-17T07:08",
    "heart_rate_2026-09-17T21:45",
    "glucose_2026-09-17T22:30"
  ],
  "open_item_classes": {
    "medication_adherence_2026-09-11T21:00": "adverse",
    "sleep_duration_2026-09-14T07:00": "adverse",
    "blood_pressure_2026-09-16T08:13": "adverse",
    "screen_time_2026-09-17T00:00": "adverse",
    "resting_heart_rate_2026-09-17T07:08": "adverse",
    "heart_rate_2026-09-17T21:45": "adverse",
    "glucose_2026-09-17T22:30": "adverse"
  },
  "quality": [
    "overdue:hba1c"
  ]
}
```

## 2. The glucose item that opened at 22:30 and closed at 23:00 (`state_items`)

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
  "peak_value": 185.0,
  "trigger": "persistence",
  "status": "closed",
  "handed_off_at": "2026-09-17T22:30:00+05:30",
  "item_class": "adverse",
  "close_reason": "recovered",
  "peak_metric": 2.2106936280772804,
  "context": {
    "last_meal": {
      "label": "festive_dinner",
      "time": "2026-09-17T21:28:00+05:30",
      "minutes_ago": 62
    },
    "medication": {
      "taken": 1,
      "expected": 3,
      "missed": [
        "metformin",
        "levothyroxine"
      ]
    },
    "sleep_last_night": {
      "value": 3.8,
      "position": "clearly below"
    },
    "other_open_items": [
      "heart_rate",
      "sleep_duration",
      "resting_heart_rate",
      "blood_pressure",
      "medication_adherence",
      "screen_time"
    ],
    "diary_today_count": 2
  }
}
```

## 3. Its hand-off record (`state_handoffs`, written once when the item opened)

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
  "position_z": 2.21,
  "opened_at": "2026-09-17T22:30:00+05:30",
  "context": {
    "last_meal": {
      "label": "festive_dinner",
      "time": "2026-09-17T21:28:00+05:30",
      "minutes_ago": 62
    },
    "medication": {
      "taken": 1,
      "expected": 3,
      "missed": [
        "metformin",
        "levothyroxine"
      ]
    },
    "sleep_last_night": {
      "value": 3.8,
      "position": "clearly below"
    },
    "other_open_items": [
      "heart_rate",
      "sleep_duration",
      "resting_heart_rate",
      "blood_pressure",
      "medication_adherence",
      "screen_time"
    ],
    "diary_today_count": 2
  },
  "snapshot_as_of": "2026-09-17T22:30:00+05:30"
}
```

## 4. Ticks 21:30 to 23:30 on 2026-09-17

Read from the `state_log` snapshot of each tick (query: `SELECT snapshot_json FROM state_log WHERE as_of = '<tick>'`); events come from `state_items` and `state_handoffs`.

| tick | glucose | min after meal (bucket) | usual after meal (median) | z | glucose position | glucose run | heart rate | usual (clock median) | z | heart rate position | heart rate run | events at this tick |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 21:30 | 124.7 | 0 | 121.55 | 0.28 | within | above 0 / close 0 | 106.9 | 85.4 | 2.07 | clearly above | above 1 / close 0 |  |
| 21:45 | 136.1 | 15 | 128.1 | 0.67 | within | above 0 / close 0 | 112.0 | 83.6 | 2.66 | clearly above | above 2 / close 0 | heart_rate item opens (heart_rate_2026-09-17T21:45); hand-off written |
| 22:00 | 157.2 | 30 | 137.25 | 1.65 | slightly above | above 0 / close 0 | 99.4 | 80.9 | 1.76 | slightly above | above 0 / close 1 |  |
| 22:15 | 172.3 | 45 | 144.9 | 2.2 | clearly above | above 1 / close 0 | 98.8 | 78.7 | 2.02 | clearly above | above 1 / close 0 |  |
| 22:30 | 185.0 | 60 | 153.8 | 2.21 | clearly above | above 2 / close 0 | 102.9 | 76.3 | 2.79 | clearly above | above 2 / close 0 | glucose item opens (glucose_2026-09-17T22:30); hand-off written |
| 22:45 | 185.4 | 75 | 160.9 | 1.68 | slightly above | above 0 / close 1 | 103.2 | 74.4 | 3.0 | clearly above | above 3 / close 0 |  |
| 23:00 | 177.3 | 90 | 153.4 | 1.66 | slightly above | above 0 / close 0 | 93.2 | 72.3 | 2.24 | clearly above | above 4 / close 0 | glucose item closes (recovered) |
| 23:15 | 162.0 | 105 | 145.1 | 1.3 | slightly above | above 0 / close 0 | 93.0 | 70.6 | 2.57 | clearly above | above 5 / close 0 |  |
| 23:30 | 152.9 | 120 | 135.8 | 1.37 | slightly above | above 0 / close 0 | 92.3 | 69.2 | 3.07 | clearly above | above 6 / close 0 |  |
