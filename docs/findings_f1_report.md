# Findings Engine, stage F1 report (code layer only, PI absent)

Run: `uv run python -m v0_code.findings_engine.run --config config/findings_meera_iyer_v1.yaml --stage F1` -> `output/findings_engine.db` (own database; the State, Rulebook, Evidence and Personal Data Store databases are opened read-only and their checksums were unchanged).

## Case counts by gap (287 hand-offs; max span 36 h)

| gap | cases | counted hand-offs in cases | versions | unattached (deferred, no open case) |
|---|---:|---:|---:|---:|
| 3 h | 176 | 279 | 284 | 6 |
| **6 h (configured)** | **116** | **279** | **284** | 4 |
| 12 h | 90 (85 with no span cap; chains up to 60.5 h, so the 36 h cap splits 5) | 279 | 284 | 3 |

At 6 h: 116 cases, 279 counted hand-offs, 4 deferred hand-offs recorded inside a case, 4 unattached, 284 versions (= 279 + 5 completions). Versions per case: {1: 54, 2: 24, 3: 14, 4: 11, 5: 2, 6: 4, 8: 4, 9: 1, 10: 1, 11: 1}. Longest case 27.75 h; at most 3 cases start on a day.

## Cases before 10 December 2025

27 cases, 80 versions: **all descriptive** (every relationship factor is `insufficient(history)` or not exposed; history note `not_enough_history_yet` on every one). The first relationship-mode version is `fnd_case_2025-12-15T08:45:00+05:30_v1`.

| case | counted hand-offs | versions | mode | history note |
|---|---:|---:|---|---|
| 2025-10-15T00:15:00+ | 11 | 11 | descriptive | not_enough_history_yet |
| 2025-10-16T19:30:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-10-18T10:15:00+ | 4 | 4 | descriptive | not_enough_history_yet |
| 2025-10-19T07:00:00+ | 3 | 3 | descriptive | not_enough_history_yet |
| 2025-10-19T19:15:00+ | 9 | 9 | descriptive | not_enough_history_yet |
| 2025-10-21T21:00:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-10-23T21:45:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-10-24T08:15:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-10-27T20:30:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-10-28T23:00:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-10-31T05:15:00+ | 6 | 6 | descriptive | not_enough_history_yet |
| 2025-11-03T02:00:00+ | 4 | 4 | descriptive | not_enough_history_yet |
| 2025-11-07T08:15:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-11-08T11:00:00+ | 1 | 2 | descriptive | not_enough_history_yet |
| 2025-11-08T19:15:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-11-10T00:30:00+ | 6 | 6 | descriptive | not_enough_history_yet |
| 2025-11-11T06:45:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-11-13T21:00:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-11-17T00:15:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-11-17T07:00:00+ | 2 | 2 | descriptive | not_enough_history_yet |
| 2025-11-17T21:00:00+ | 3 | 3 | descriptive | not_enough_history_yet |
| 2025-11-18T08:17:00+ | 3 | 3 | descriptive | not_enough_history_yet |
| 2025-11-18T22:15:00+ | 8 | 8 | descriptive | not_enough_history_yet |
| 2025-11-19T22:45:00+ | 4 | 4 | descriptive | not_enough_history_yet |
| 2025-11-20T23:00:00+ | 2 | 2 | descriptive | not_enough_history_yet |
| 2025-12-02T19:15:00+ | 1 | 1 | descriptive | not_enough_history_yet |
| 2025-12-09T21:00:00+ | 1 | 1 | descriptive | not_enough_history_yet |

## Modes

- every version: descriptive 165, relationship 119
- last version of each case: descriptive 67, relationship 49

## Wording classes: 11, not 14

The spec defines 11 (Amendment 9). Factor counts, over every version (a factor is counted in each version it appears in) and over the last version of each case:

| class | every version | last version per case |
|---|---:|---:|
| asserted | 105 | 40 |
| asserted_same_day | 76 | 38 |
| hedged | 8 | 1 |
| hedged_same_day | 2 | 1 |
| exposure_only | 320 | 138 |
| exposure_only_history | 403 | 137 |
| contrary_note | 2 | 2 |
| not_mentioned | 1605 | 686 |
| not_known_yet | 560 | 188 |
| event_unusual | 42 | 21 |
| artifact_note | 3 | 3 |
| **total** | 3126 | 1255 |

Factor kinds (every version): relationship 2582, event 320, unavailable 224. `unavailable` = a factor with no relationship key (reasons `no_definition`, `no_meal_kind`), always `not_mentioned`.

## Groups

Last versions: 6 entangled and 14 co-exposed groups, in 18 of 116 cases (sizes: entangled 2 x6; co-exposed 2 x9, 3 x3, 4 x1, 5 x1). Over every version: 10 entangled, 34 co-exposed.

## The two named records

### fnd_case_2026-09-17T21:45:00+05:30_v2

Code line:

> Heart rate and glucose were clearly above her usual. Present: a stressed or low-mood period on the same day, short sleep the night before (among the very lowest she has had), missed doses on the same day or the day before. The size of this meal's rise was among the very highest she has had within the hour or so after dinners. A stressed or low-mood period on the same day and short sleep the night before often occur together, so their separate roles cannot be told apart. Missed doses on the same day or the day before and short sleep the night before were present together, so none of them stands alone as the explanation. A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history. Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner in her history. Short sleep the night before has tended to move together with higher glucose peaks after dinner in her history. Also present, with no link claimed: more activity in the hour before (high for her) and her thyroid medicine. Not known yet: the day's step total.

```json
{
 "as_of": "2026-09-17T22:30:00+05:30",
 "case_id": "case_2026-09-17T21:45:00+05:30",
 "checks": {
  "failed": [],
  "passed": true
 },
 "closed": false,
 "completion_ids": [],
 "evidence_ids": [
  "ev_handoff_heart_rate_2026-09-17T21:45",
  "ev_handoff_glucose_2026-09-17T22:30"
 ],
 "factors": [
  {
   "candidate": "activity",
   "exposure": "exposed",
   "factor_id": "f1",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "kind": "relationship",
   "label": "not_supported",
   "position": "high for her",
   "rank": 1,
   "relationship_evidence_ids": [
    "rel|steps_window_hourly@60m->hr_hour_mean|2026-09-17|ev-v0"
   ],
   "relationship_key": "steps_window_hourly@60m->hr_hour_mean",
   "weight_tier": "primary",
   "wording_class": "exposure_only"
  },
  {
   "candidate": "stress_mood",
   "exposure": "exposed",
   "factor_id": "f2",
   "flags": [
    "same_day_unverified"
   ],
   "group": "g1",
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "kind": "relationship",
   "label": "supported",
   "position": null,
   "rank": 2,
   "relationship_evidence_ids": [
    "rel|strained_period@same_day->hr_day_mean|2026-09-17|ev-v0"
   ],
   "relationship_key": "strained_period@same_day->hr_day_mean",
   "weight_tier": "primary",
   "wording_class": "asserted_same_day"
  },
  {
   "candidate": "illness_fever",
   "exposure": "not_exposed",
   "factor_id": "f3",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "kind": "relationship",
   "label": "not_supported",
   "position": null,
   "rank": 3,
   "relationship_evidence_ids": [
    "rel|symptom_entry@3d->hr_day_mean|2026-09-17|ev-v0"
   ],
   "relationship_key": "symptom_entry@3d->hr_day_mean",
   "weight_tier": "primary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "hydration",
   "exposure": "not_exposed",
   "factor_id": "f4",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "kind": "relationship",
   "label": "supported",
   "position": null,
   "rank": 4,
   "relationship_evidence_ids": [
    "rel|hydration_total@prev_day->hr_day_mean|2026-09-17|ev-v0"
   ],
   "relationship_key": "hydration_total@prev_day->hr_day_mean",
   "weight_tier": "secondary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "sleep",
   "exposure": "exposed",
   "factor_id": "f5",
   "flags": [
    "same_day_unverified"
   ],
   "group": "g1",
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "kind": "relationship",
   "label": "supported",
   "position": "among the very lowest she has had",
   "rank": 6,
   "relationship_evidence_ids": [
    "rel|sleep_hours@prev_night->hr_day_mean|2026-09-17|ev-v0"
   ],
   "relationship_key": "sleep_hours@prev_night->hr_day_mean",
   "weight_tier": "secondary",
   "wording_class": "asserted_same_day"
  },
  {
   "candidate": "alcohol",
   "exposure": "not_exposed",
   "factor_id": "f6",
   "flags": [
    "small_group"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "insufficient_reason": "small_group",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 7,
   "relationship_evidence_ids": [
    "rel|alcohol_entry@720m->hr_day_mean|2026-09-17|ev-v0"
   ],
   "relationship_key": "alcohol_entry@720m->hr_day_mean",
   "weight_tier": "secondary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "thyroid_status",
   "exposure": null,
   "factor_id": "f7",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "kind": "event",
   "label": "not_applicable",
   "position": null,
   "rank": 8,
   "relationship_key": null,
   "weight_tier": "tertiary",
   "wording_class": "exposure_only"
  },
  {
   "candidate": "meal_digestive",
   "exposure": null,
   "factor_id": "f8",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_heart_rate_2026-09-17T21:45"
   ],
   "insufficient_reason": "no_definition",
   "kind": "unavailable",
   "label": "insufficient",
   "position": null,
   "rank": 9,
   "relationship_key": null,
   "weight_tier": "tertiary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "meal_composition",
   "exposure": "exposed",
   "factor_id": "f9",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
   ],
   "kind": "event",
   "label": "supported",
   "position": "among the very highest she has had within the hour or so after dinners",
   "rank": 1,
   "relationship_key": null,
   "weight_tier": "primary",
   "wording_class": "event_unusual"
  },
  {
   "candidate": "medication_adherence",
   "exposure": "exposed",
   "factor_id": "f10",
   "flags": [
    "same_day_unverified"
   ],
   "group": "g2",
   "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
   ],
   "kind": "relationship",
   "label": "supported",
   "position": null,
   "rank": 2,
   "relationship_evidence_ids": [
    "rel|missed_dose@2d->post_meal_peak:dinner|2026-09-17|ev-v0"
   ],
   "relationship_key": "missed_dose@2d->post_meal_peak:dinner",
   "weight_tier": "secondary",
   "wording_class": "asserted_same_day"
  },
  {
   "candidate": "sleep",
   "exposure": "exposed",
   "factor_id": "f11",
   "flags": [],
   "group": "g2",
   "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
   ],
   "kind": "relationship",
   "label": "supported",
   "position": "among the very lowest she has had",
   "rank": 3,
   "relationship_evidence_ids": [
    "rel|sleep_hours@prev_night->post_meal_peak:dinner|2026-09-17|ev-v0"
   ],
   "relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner",
   "weight_tier": "secondary",
   "wording_class": "asserted"
  },
  {
   "candidate": "stress_mood",
   "exposure": "exposed",
   "factor_id": "f12",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
   ],
   "kind": "relationship",
   "label": "not_supported",
   "position": null,
   "rank": 4,
   "relationship_evidence_ids": [
    "rel|strained_period@1d->post_meal_peak:dinner|2026-09-17|ev-v0"
   ],
   "relationship_key": "strained_period@1d->post_meal_peak:dinner",
   "weight_tier": "secondary",
   "wording_class": "exposure_only"
  },
  {
   "candidate": "activity",
   "exposure": "not_yet_available",
   "factor_id": "f13",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
   ],
   "kind": "relationship",
   "label": "not_supported",
   "position": null,
   "rank": 5,
   "relationship_evidence_ids": [
    "rel|steps_total@1d->post_meal_peak:dinner|2026-09-17|ev-v0"
   ],
   "relationship_key": "steps_total@1d->post_meal_peak:dinner",
   "weight_tier": "secondary",
   "wording_class": "not_known_yet"
  },
  {
   "candidate": "illness_symptoms",
   "exposure": "not_exposed",
   "factor_id": "f14",
   "flags": [
    "contrary",
    "placebo_fired"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
   ],
   "kind": "relationship",
   "label": "not_supported",
   "position": null,
   "rank": 6,
   "relationship_evidence_ids": [
    "rel|symptom_entry@3d->post_meal_peak:dinner|2026-09-17|ev-v0"
   ],
   "relationship_key": "symptom_entry@3d->post_meal_peak:dinner",
   "weight_tier": "secondary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "alcohol",
   "exposure": "not_exposed",
   "factor_id": "f15",
   "flags": [
    "small_group"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
   ],
   "insufficient_reason": "small_group",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 10,
   "relationship_evidence_ids": [
    "rel|alcohol_entry@1d->post_meal_peak:dinner|2026-09-17|ev-v0"
   ],
   "relationship_key": "alcohol_entry@1d->post_meal_peak:dinner",
   "weight_tier": "tertiary",
   "wording_class": "not_mentioned"
  }
 ],
 "finding_id": "fnd_case_2026-09-17T21:45:00+05:30_v2",
 "groups": [
  {
   "group_id": "g1",
   "members": [
    "f2",
    "f5"
   ],
   "reason": "entangled"
  },
  {
   "group_id": "g2",
   "members": [
    "f10",
    "f11"
   ],
   "reason": "co_exposed"
  }
 ],
 "handoff_ids": [
  "handoff_heart_rate_2026-09-17T21:45",
  "handoff_glucose_2026-09-17T22:30"
 ],
 "history_note": "enough",
 "local_date": "2026-09-17",
 "measures": [
  {
   "direction": "above",
   "measure": "heart_rate",
   "measure_id": "m1",
   "opened_at": "2026-09-17T21:45:00+05:30",
   "strength": "clearly"
  },
  {
   "direction": "above",
   "measure": "glucose",
   "measure_id": "m2",
   "opened_at": "2026-09-17T22:30:00+05:30",
   "strength": "clearly"
  }
 ],
 "mode": "relationship",
 "not_known_yet": [
  "the day's step total"
 ],
 "provisional": true,
 "refs": {
  "diary": [
   {
    "context_id": "ctx_1110",
    "view_id": "d1"
   },
   {
    "context_id": "ctx_1109",
    "view_id": "d2"
   },
   {
    "context_id": "ctx_1108",
    "view_id": "d3"
   }
  ],
  "pi_memories": [],
  "state_memory": [
   {
    "view_id": "s1",
    "window_id": "day_2026-09-16"
   },
   {
    "view_id": "s2",
    "window_id": "week_ENDING_2026-09-16"
   },
   {
    "view_id": "s3",
    "window_id": "month_ENDING_2026-08-26"
   }
  ]
 },
 "repeat": [
  {
   "pi_status": null,
   "relationship_key": "strained_period@same_day->hr_day_mean",
   "seen_before": "none"
  },
  {
   "pi_status": null,
   "relationship_key": "sleep_hours@prev_night->hr_day_mean",
   "seen_before": "none"
  },
  {
   "pi_status": null,
   "relationship_key": "missed_dose@2d->post_meal_peak:dinner",
   "seen_before": "none"
  },
  {
   "pi_status": null,
   "relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner",
   "seen_before": "none"
  }
 ],
 "status": "ok",
 "text": {
  "headline": "Heart rate and glucose were clearly above her usual.",
  "sentences": [
   {
    "refs": [],
    "text": "Present: a stressed or low-mood period on the same day, short sleep the night before (among the very lowest she has had), missed doses on the same day or the day before."
   },
   {
    "refs": [],
    "text": "The size of this meal's rise was among the very highest she has had within the hour or so after dinners."
   },
   {
    "refs": [],
    "text": "A stressed or low-mood period on the same day and short sleep the night before often occur together, so their separate roles cannot be told apart."
   },
   {
    "refs": [],
    "text": "Missed doses on the same day or the day before and short sleep the night before were present together, so none of them stands alone as the explanation."
   },
   {
    "refs": [],
    "text": "A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history."
   },
   {
    "refs": [],
    "text": "Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day."
   },
   {
    "refs": [],
    "text": "Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner in her history."
   },
   {
    "refs": [],
    "text": "Short sleep the night before has tended to move together with higher glucose peaks after dinner in her history."
   },
   {
    "refs": [],
    "text": "Also present, with no link claimed: more activity in the hour before (high for her) and her thyroid medicine."
   },
   {
    "refs": [],
    "text": "Not known yet: the day's step total."
   }
  ],
  "source": "code_line"
 },
 "version": 2
}
```

### fnd_case_2025-11-18T08:17:00+05:30_v3

Code line:

> Blood pressure and glucose were clearly above her usual. Present: missed doses on the same day or the day before, short sleep the night before (among the very lowest she has had), a symptom noted in the diary on the same day or in the days before, a stressed or low-mood period on the same day. The size of this meal's rise was among the very highest she has had within the couple of hours after lunches. Not known yet: where the reading was taken, the day's mood record and the day's step total. There is not enough history yet to say what usually goes with this.

```json
{
 "as_of": "2025-11-18T15:15:00+05:30",
 "case_id": "case_2025-11-18T08:17:00+05:30",
 "checks": {
  "failed": [],
  "passed": true
 },
 "closed": false,
 "completion_ids": [],
 "evidence_ids": [
  "ev_handoff_blood_pressure_2025-11-18T08:17",
  "ev_handoff_glucose_2025-11-18T11:15",
  "ev_handoff_glucose_2025-11-18T15:15"
 ],
 "factors": [
  {
   "candidate": "medication_adherence",
   "exposure": "exposed",
   "factor_id": "f1",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_blood_pressure_2025-11-18T08:17"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 1,
   "relationship_evidence_ids": [
    "rel|missed_dose@2d->systolic_reading|2025-11-18|ev-v0"
   ],
   "relationship_key": "missed_dose@2d->systolic_reading",
   "weight_tier": "primary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "measurement_context",
   "exposure": "not_yet_available",
   "factor_id": "f2",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_blood_pressure_2025-11-18T08:17"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 2,
   "relationship_evidence_ids": [
    "rel|clinic_reading@at_open->systolic_reading|2025-11-18|ev-v0"
   ],
   "relationship_key": "clinic_reading@at_open->systolic_reading",
   "weight_tier": "primary",
   "wording_class": "not_known_yet"
  },
  {
   "candidate": "stress_mood",
   "exposure": "no_data",
   "factor_id": "f3",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_blood_pressure_2025-11-18T08:17"
   ],
   "insufficient_reason": "no_ordered_exposure",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 3,
   "relationship_evidence_ids": [
    "rel|strained_period@same_day->systolic_reading|2025-11-18|ev-v0"
   ],
   "relationship_key": "strained_period@same_day->systolic_reading",
   "weight_tier": "secondary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "sleep",
   "exposure": "exposed",
   "factor_id": "f4",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_blood_pressure_2025-11-18T08:17"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": "among the very lowest she has had",
   "rank": 4,
   "relationship_evidence_ids": [
    "rel|sleep_hours@prev_night->systolic_reading|2025-11-18|ev-v0"
   ],
   "relationship_key": "sleep_hours@prev_night->systolic_reading",
   "weight_tier": "secondary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "salt_in_meals",
   "exposure": null,
   "factor_id": "f5",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_blood_pressure_2025-11-18T08:17"
   ],
   "insufficient_reason": "no_definition",
   "kind": "unavailable",
   "label": "insufficient",
   "position": null,
   "rank": 5,
   "relationship_key": null,
   "weight_tier": "secondary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "alcohol_caffeine",
   "exposure": "not_exposed",
   "factor_id": "f6",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_blood_pressure_2025-11-18T08:17"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 6,
   "relationship_evidence_ids": [
    "rel|alcohol_entry@720m->systolic_reading|2025-11-18|ev-v0"
   ],
   "relationship_key": "alcohol_entry@720m->systolic_reading",
   "weight_tier": "tertiary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "pain_or_illness",
   "exposure": "not_exposed",
   "factor_id": "f7",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_blood_pressure_2025-11-18T08:17"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 7,
   "relationship_evidence_ids": [
    "rel|symptom_entry@same_day->systolic_reading|2025-11-18|ev-v0"
   ],
   "relationship_key": "symptom_entry@same_day->systolic_reading",
   "weight_tier": "tertiary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "medication_adherence",
   "exposure": "exposed",
   "factor_id": "f8",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T11:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 1,
   "relationship_evidence_ids": [
    "rel|missed_dose@2d->non_meal_mean|2025-11-18|ev-v0"
   ],
   "relationship_key": "missed_dose@2d->non_meal_mean",
   "weight_tier": "primary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "illness_symptoms",
   "exposure": "exposed",
   "factor_id": "f9",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T11:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 2,
   "relationship_evidence_ids": [
    "rel|symptom_entry@3d->non_meal_mean|2025-11-18|ev-v0"
   ],
   "relationship_key": "symptom_entry@3d->non_meal_mean",
   "weight_tier": "primary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "stress_mood",
   "exposure": "not_yet_available",
   "factor_id": "f10",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T11:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 3,
   "relationship_evidence_ids": [
    "rel|strained_period@1d->non_meal_mean|2025-11-18|ev-v0"
   ],
   "relationship_key": "strained_period@1d->non_meal_mean",
   "weight_tier": "secondary",
   "wording_class": "not_known_yet"
  },
  {
   "candidate": "sleep",
   "exposure": "exposed",
   "factor_id": "f11",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T11:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": "among the very lowest she has had",
   "rank": 4,
   "relationship_evidence_ids": [
    "rel|sleep_hours@prev_night->non_meal_mean|2025-11-18|ev-v0"
   ],
   "relationship_key": "sleep_hours@prev_night->non_meal_mean",
   "weight_tier": "secondary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "activity",
   "exposure": "not_exposed",
   "factor_id": "f12",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T11:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 5,
   "relationship_evidence_ids": [
    "rel|steps_total@prev_day->non_meal_mean|2025-11-18|ev-v0"
   ],
   "relationship_key": "steps_total@prev_day->non_meal_mean",
   "weight_tier": "secondary",
   "wording_class": "not_mentioned"
  },
  {
   "candidate": "meal_composition",
   "exposure": "exposed",
   "factor_id": "f13",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T15:15"
   ],
   "kind": "event",
   "label": "supported",
   "position": "among the very highest she has had within the couple of hours after lunches",
   "rank": 1,
   "relationship_key": null,
   "weight_tier": "primary",
   "wording_class": "event_unusual"
  },
  {
   "candidate": "medication_adherence",
   "exposure": "exposed",
   "factor_id": "f14",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T15:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 2,
   "relationship_evidence_ids": [
    "rel|missed_dose@2d->post_meal_peak:lunch|2025-11-18|ev-v0"
   ],
   "relationship_key": "missed_dose@2d->post_meal_peak:lunch",
   "weight_tier": "secondary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "sleep",
   "exposure": "exposed",
   "factor_id": "f15",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T15:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": "among the very lowest she has had",
   "rank": 3,
   "relationship_evidence_ids": [
    "rel|sleep_hours@prev_night->post_meal_peak:lunch|2025-11-18|ev-v0"
   ],
   "relationship_key": "sleep_hours@prev_night->post_meal_peak:lunch",
   "weight_tier": "secondary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "stress_mood",
   "exposure": "exposed",
   "factor_id": "f16",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T15:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 4,
   "relationship_evidence_ids": [
    "rel|strained_period@1d->post_meal_peak:lunch|2025-11-18|ev-v0"
   ],
   "relationship_key": "strained_period@1d->post_meal_peak:lunch",
   "weight_tier": "secondary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "activity",
   "exposure": "not_yet_available",
   "factor_id": "f17",
   "flags": [
    "same_day_unverified"
   ],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T15:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 5,
   "relationship_evidence_ids": [
    "rel|steps_total@1d->post_meal_peak:lunch|2025-11-18|ev-v0"
   ],
   "relationship_key": "steps_total@1d->post_meal_peak:lunch",
   "weight_tier": "secondary",
   "wording_class": "not_known_yet"
  },
  {
   "candidate": "illness_symptoms",
   "exposure": "exposed",
   "factor_id": "f18",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T15:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 6,
   "relationship_evidence_ids": [
    "rel|symptom_entry@3d->post_meal_peak:lunch|2025-11-18|ev-v0"
   ],
   "relationship_key": "symptom_entry@3d->post_meal_peak:lunch",
   "weight_tier": "secondary",
   "wording_class": "exposure_only_history"
  },
  {
   "candidate": "alcohol",
   "exposure": "not_exposed",
   "factor_id": "f19",
   "flags": [],
   "group": null,
   "handoff_ids": [
    "handoff_glucose_2025-11-18T15:15"
   ],
   "insufficient_reason": "history",
   "kind": "relationship",
   "label": "insufficient",
   "position": null,
   "rank": 10,
   "relationship_evidence_ids": [
    "rel|alcohol_entry@1d->post_meal_peak:lunch|2025-11-18|ev-v0"
   ],
   "relationship_key": "alcohol_entry@1d->post_meal_peak:lunch",
   "weight_tier": "tertiary",
   "wording_class": "not_mentioned"
  }
 ],
 "finding_id": "fnd_case_2025-11-18T08:17:00+05:30_v3",
 "groups": [],
 "handoff_ids": [
  "handoff_blood_pressure_2025-11-18T08:17",
  "handoff_glucose_2025-11-18T11:15",
  "handoff_glucose_2025-11-18T15:15"
 ],
 "history_note": "not_enough_history_yet",
 "local_date": "2025-11-18",
 "measures": [
  {
   "direction": "above",
   "measure": "blood_pressure",
   "measure_id": "m1",
   "opened_at": "2025-11-18T08:17:00+05:30",
   "strength": "clearly"
  },
  {
   "direction": "above",
   "measure": "glucose",
   "measure_id": "m2",
   "opened_at": "2025-11-18T11:15:00+05:30",
   "strength": "clearly"
  }
 ],
 "mode": "descriptive",
 "not_known_yet": [
  "where the reading was taken",
  "the day's mood record",
  "the day's step total"
 ],
 "provisional": true,
 "refs": {
  "diary": [
   {
    "context_id": "ctx_106",
    "view_id": "d1"
   }
  ],
  "pi_memories": [],
  "state_memory": [
   {
    "view_id": "s1",
    "window_id": "day_2025-11-17"
   },
   {
    "view_id": "s2",
    "window_id": "week_ENDING_2025-11-17"
   }
  ]
 },
 "repeat": [],
 "status": "ok",
 "text": {
  "headline": "Blood pressure and glucose were clearly above her usual.",
  "sentences": [
   {
    "refs": [],
    "text": "Present: missed doses on the same day or the day before, short sleep the night before (among the very lowest she has had), a symptom noted in the diary on the same day or in the days before, a stressed or low-mood period on the same day."
   },
   {
    "refs": [],
    "text": "The size of this meal's rise was among the very highest she has had within the couple of hours after lunches."
   },
   {
    "refs": [],
    "text": "Not known yet: where the reading was taken, the day's mood record and the day's step total."
   },
   {
    "refs": [],
    "text": "There is not enough history yet to say what usually goes with this."
   }
  ],
  "source": "code_line"
 },
 "version": 3
}
```

## Ten more code lines (last version of the case, one per month)

**fnd_case_2025-10-19T07:00:00+05:30_v3** (descriptive, 3 hand-offs, history `not_enough_history_yet`)

> Sleep was clearly below her usual. Heart rate was clearly above her usual. Present: a day away from home, more activity in the hour before (high for her), short sleep the night before (among the very lowest she has had), her thyroid medicine. Not known yet: the day's mood record. There is not enough history yet to say what usually goes with this.

**fnd_case_2025-11-17T21:00:00+05:30_v3** (descriptive, 3 hand-offs, history `not_enough_history_yet`)

> Doses taken were clearly below her usual. Heart rate and glucose were clearly above her usual. Present: a stressed or low-mood period on the same day, missed doses in the week before, short sleep the night before (among the very lowest she has had), a symptom noted in the diary on the same day or in the days before, her thyroid medicine, missed doses on the same day or the day before. Not known yet: where she was that day, the day's mood record and last night's sleep. There is not enough history yet to say what usually goes with this.

**fnd_case_2025-12-25T13:15:00+05:30_v3** (relationship, 3 hand-offs, history `enough`)

> Heart rate was clearly above her usual. Glucose was far above her usual. Present: more activity in the hour before (among the very highest she has had). The size of this meal's rise was among the very highest she has had within the hour or so after lunches. More activity in the hour before has tended to move together with higher heart rate in that hour in her history. Also present, with no link claimed: alcohol noted in the diary in the hours before and her thyroid medicine. Not known yet: the day's mood record, the day's medicine record and the day's step total.

**fnd_case_2026-01-13T09:15:00+05:30_v2** (relationship, 2 hand-offs, history `enough`)

> Glucose was clearly above her usual. Present: short sleep the night before (low for her). The size of this meal's rise was among the very highest she has had within the hour or so after breakfasts. The size of this meal's rise was among the very highest she has had within the hour or so after lunches. Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. Not known yet: the day's medicine record and the day's step total.

**fnd_case_2026-02-07T11:15:00+05:30_v4** (relationship, 4 hand-offs, history `enough`)

> Heart rate was far above her usual. Present: more activity in the hour before (high for her). More activity in the hour before has tended to move together with higher heart rate in that hour in her history. Also present, with no link claimed: her thyroid medicine. Not known yet: the day's mood record.

**fnd_case_2026-03-14T01:00:00+05:30_v3** (relationship, 3 hand-offs, history `enough`)

> Heart rate and resting heart rate were clearly above her usual. Present: short sleep the night before (low for her). Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day. Also present, with no link claimed: her thyroid medicine and a stressed or low-mood period the day before. Not known yet: the day's mood record and last night's sleep.

**fnd_case_2026-04-02T19:15:00+05:30_v2** (relationship, 2 hand-offs, history `enough`)

> Heart rate was clearly above her usual. Doses taken were clearly below her usual. Present: more activity in the hour before (high for her). More activity in the hour before has tended to move together with higher heart rate in that hour in her history. Also present, with no link claimed: her thyroid medicine and missed doses in the week before. Not known yet: the day's mood record and where she was that day.

**fnd_case_2026-06-12T22:30:00+05:30_v1** (relationship, 1 hand-offs, history `enough`)

> Glucose was clearly above her usual. Present: missed doses on the same day or the day before. The size of this meal's rise was high for her within the couple of hours after dinners. Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner in her history. Not known yet: the day's step total.

**fnd_case_2026-07-08T23:45:00+05:30_v1** (relationship, 1 hand-offs, history `enough`)

> Heart rate was clearly above her usual. Present: a stressed or low-mood period on the same day, short sleep the night before (low for her). A stressed or low-mood period on the same day and short sleep the night before often occur together, so their separate roles cannot be told apart. A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history. Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. Also present, with no link claimed: her thyroid medicine.

**fnd_case_2026-09-12T06:15:00+05:30_v3** (relationship, 3 hand-offs, history `enough`)

> Heart rate and resting heart rate were clearly above her usual. Present: low fluid intake the day before (low for her). Low fluid intake the day before has tended to move together with higher heart rate over the day in her history. Low fluid intake the day before has tended to move together with a higher resting heart rate in her history. Also present, with no link claimed: more activity in the hour before (high for her) and her thyroid medicine. Not known yet: the day's mood record and last night's sleep.

## Rare classes

**fnd_case_2026-01-01T20:15:00+05:30_v1**

> Heart rate was clearly above her usual. Present: more activity in the hour before (high for her), low fluid intake the day before (low for her). More activity in the hour before has tended to move together with higher heart rate in that hour in her history. On days like this, her heart rate over the day has tended to be lower. Also present, with no link claimed: her thyroid medicine. Not known yet: the day's mood record.

**fnd_case_2026-02-13T16:45:00+05:30_v2**

> Heart rate was clearly above her usual. Present: more activity in the hour before (among the very highest she has had), short sleep the night before (low for her). More activity in the hour before and short sleep the night before were present together, so none of them stands alone as the explanation. More activity in the hour before has tended to move together with higher heart rate in that hour in her history. Short sleep the night before may be linked to higher heart rate over the day in her history, on the same day. Also present, with no link claimed: her thyroid medicine. Not known yet: the day's mood record.

**fnd_case_2026-02-17T18:30:00+05:30_v2**

> Glucose was clearly above her usual. Present: low activity the day before (among the very lowest she has had), a symptom noted in the diary on the same day or in the days before. Low activity the day before has tended to move together with higher glucose between meals in her history. On days like this, her glucose peaks after dinner have tended to be lower. Also present, with no link claimed: missed doses on the same day or the day before. Not known yet: the day's mood record and the day's step total.

**fnd_case_2025-11-08T11:00:00+05:30_v2**

> Glucose was far below her usual. This reading may be a sensor artifact. Not known yet: the day's step total. There is not enough history yet to say what usually goes with this.

## Deviations, observations and parked items

Changed without being asked (each has a test): none of the specs' numbers. Choices I made that you may want to overrule:

1. **A code-line defect found while reading the samples, fixed with a failing test first.** A `contrary_note` sentence ("On days like this, ...") appeared without its exposure being named anywhere. Contrary factors are now listed under "Present:" (both modes) and not repeated under "Also present". The stored findings were rebuilt (`--rebuild`, own database only) after the fix.
2. **The same exposure tested against several outcomes** (for example short sleep for heart rate and for glucose) is several factors, as the spec says, but is named once in "Present:" / "Also present" and described once per relationship.
3. **Example A in the spec (9.1) showed `history_note: enough_for_some`**; by Amendment 14 (no `insufficient(history)` factor) it is `enough`. Fixed in the spec.
4. **Factor kind `unavailable`** (not in the spec): a factor without a relationship key that is not an event check (`no_definition`, `no_meal_kind`). Always `not_mentioned`. 224 factor rows over every version.
5. **Extra factor fields** `rank`, `weight_tier` (copied through, never used by a rule) and `relationship_evidence_ids` (Evidence ids, so the record references evidence by id) are in the record beyond the spec's key list.
6. **Position words and strength words live in the shared phrase book**, not the findings config (the spec's section 10 lists them under `findings:`). `kind_fallback: meal` (the noun for an event whose meal kind is unknown) and a `code_line:` block of fixed sentences were added to the phrase book so no word of the domain is in code.
7. **At a 12 h gap the 36 h span cap matters**: 90 cases with the cap, 85 without (the figure in the amendments was computed without it).
8. `case_handoffs` has 283 rows: 279 counted + 4 deferred inside a case. The other 4 deferred hand-offs are in `unattached_handoffs`.
9. A completion is attached to the case that holds its hand-off; no completion has arrived after a case closed (none can: a completion is at most about 2 h after its hand-off, the gap is 6 h).

Observations (not changed; for your decision):

- **Static presence facts** (`presence_check`, e.g. "her thyroid medicine") appear under "Also present" in most code lines (136 of 287 hand-offs have one). Per spec 7.3 they are `exposure_only`; they are true but carry no information case by case. Suggest leaving them for the text layer's view to drop, or excluding `presence_check` from the code line.
- **", on the same day" suffix**: a `same_day_unverified` claim whose window phrase does not say "same day" (for example short sleep the night before, outcome measured over the day) reads "... in her history, on the same day." The spec requires same-day wording; the phrase is awkward for the night-before window.
- **`contrary_note` wording** is the spec's "On days like this, ..."; with several claims in the line the "this" is the preceding Present list, now at least named.
- Several lines repeat "has tended to move together with" for every claim (up to 5 in one case); the text layer should fold these.
- State-memory references per version (windows with a `code_line_early` headline are skipped): 3 windows on 206 versions, 2 on 49, 1 on 18, none on 11.

Parked (unchanged from Step 1): the PI candidate without a demotion path (item 23); a structured `subject` field for the diary (whose symptom); the overview's wording table; rulebook lookback fixes.

## Checks

- Determinism: two independent runs (separate database files) give identical rows in every table; a third run into the same file wrote 0 and found 284 identical.
- As-of audit (independent of the writer, from the stored records against the source databases): 738 evidence reads, 2,719 relationship-evidence ids, 6 completion references, 241 diary references, 734 state-memory references; zero reads later than `as_of` (an evidence record's event time and outcome date, a relationship-evidence date, a completion's evaluation time, a diary timestamp, a window's end date before the local date). A planted late read is caught (test).
- Tests: 860 passed before the last fix; the Findings tests are `tests/test_findings_{wording,factors,cases,store}.py` and `tests/test_phrasebook.py` (the second synthetic patient runs through cases, versions, factors, code line, context and audit on config alone; a test enforces that no stream, measure, medicine or patient name appears in either engine's code).
