# State Engine: hand-offs before and after adverse / favourable items

Read-only report on `output/state_engine.db` after the change (before = a copy of the database taken just before it). Items: 565 before and after (the same ids; every column except `handed_off_at` and the new `item_class` is identical). Hand-offs: 565 before, 316 after. No interpretation.

## 1. Items by class

| item_class | items |
|---|---|
| adverse | 316 |
| favourable | 249 |

| trigger | item_class | items |
|---|---|---|
| persistence | adverse | 293 |
| persistence | favourable | 249 |
| severe | adverse | 23 |


## 2. Hand-offs before and after, by measure x direction

| measure | direction | before | after |
|---|---|---|---|
| glucose | above | 99 | 99 |
| glucose | below | 186 | 5 |
| heart_rate | above | 124 | 124 |
| heart_rate | below | 49 | 29 |
| resting_heart_rate | above | 12 | 12 |
| resting_heart_rate | below | 14 | 0 |
| medication_adherence | below | 24 | 24 |
| screen_time | above | 8 | 8 |
| screen_time | below | 6 | 0 |
| sleep_duration | below | 10 | 10 |
| blood_pressure | above | 3 | 3 |
| blood_pressure | below | 7 | 0 |
| step_count | above | 9 | 0 |
| sedentary_time | below | 9 | 0 |
| hydration | above | 3 | 0 |
| hydration | below | 2 | 2 |

Total hand-offs: 565 before, 316 after.


### By month x measure x direction

| month | measure | direction | before | after |
|---|---|---|---|---|
| 2025-10 | glucose | above | 16 | 16 |
| 2025-10 | glucose | below | 1 | 0 |
| 2025-10 | heart_rate | above | 20 | 20 |
| 2025-10 | resting_heart_rate | above | 1 | 1 |
| 2025-10 | medication_adherence | below | 1 | 1 |
| 2025-10 | screen_time | above | 1 | 1 |
| 2025-10 | screen_time | below | 2 | 0 |
| 2025-10 | sleep_duration | below | 1 | 1 |
| 2025-10 | step_count | above | 1 | 0 |
| 2025-10 | sedentary_time | below | 1 | 0 |
| 2025-10 | hydration | above | 1 | 0 |
| 2025-11 | glucose | above | 17 | 17 |
| 2025-11 | glucose | below | 2 | 1 |
| 2025-11 | heart_rate | above | 13 | 13 |
| 2025-11 | heart_rate | below | 2 | 0 |
| 2025-11 | resting_heart_rate | above | 1 | 1 |
| 2025-11 | medication_adherence | below | 2 | 2 |
| 2025-11 | screen_time | above | 3 | 3 |
| 2025-11 | sleep_duration | below | 1 | 1 |
| 2025-11 | blood_pressure | above | 2 | 2 |
| 2025-11 | hydration | below | 1 | 1 |
| 2025-12 | glucose | above | 2 | 2 |
| 2025-12 | glucose | below | 4 | 0 |
| 2025-12 | heart_rate | above | 12 | 12 |
| 2025-12 | medication_adherence | below | 1 | 1 |
| 2025-12 | screen_time | below | 1 | 0 |
| 2025-12 | step_count | above | 2 | 0 |
| 2025-12 | sedentary_time | below | 2 | 0 |
| 2026-01 | glucose | above | 30 | 30 |
| 2026-01 | glucose | below | 5 | 1 |
| 2026-01 | heart_rate | above | 8 | 8 |
| 2026-01 | resting_heart_rate | above | 1 | 1 |
| 2026-01 | medication_adherence | below | 6 | 6 |
| 2026-01 | blood_pressure | below | 1 | 0 |
| 2026-02 | glucose | above | 14 | 14 |
| 2026-02 | glucose | below | 13 | 0 |
| 2026-02 | heart_rate | above | 12 | 12 |
| 2026-02 | resting_heart_rate | above | 1 | 1 |
| 2026-02 | medication_adherence | below | 3 | 3 |
| 2026-02 | screen_time | below | 1 | 0 |
| 2026-02 | sleep_duration | below | 1 | 1 |
| 2026-02 | blood_pressure | below | 1 | 0 |
| 2026-02 | step_count | above | 2 | 0 |
| 2026-02 | sedentary_time | below | 2 | 0 |
| 2026-02 | hydration | above | 1 | 0 |
| 2026-03 | glucose | above | 16 | 16 |
| 2026-03 | glucose | below | 15 | 1 |
| 2026-03 | heart_rate | above | 23 | 23 |
| 2026-03 | resting_heart_rate | above | 4 | 4 |
| 2026-03 | medication_adherence | below | 5 | 5 |
| 2026-03 | screen_time | above | 2 | 2 |
| 2026-03 | screen_time | below | 1 | 0 |
| 2026-03 | sleep_duration | below | 3 | 3 |
| 2026-03 | step_count | above | 1 | 0 |
| 2026-03 | sedentary_time | below | 1 | 0 |
| 2026-04 | glucose | below | 30 | 0 |
| 2026-04 | heart_rate | above | 13 | 13 |
| 2026-04 | heart_rate | below | 5 | 2 |
| 2026-04 | resting_heart_rate | above | 1 | 1 |
| 2026-04 | resting_heart_rate | below | 2 | 0 |
| 2026-04 | medication_adherence | below | 2 | 2 |
| 2026-04 | sleep_duration | below | 1 | 1 |
| 2026-04 | blood_pressure | below | 1 | 0 |
| 2026-04 | step_count | above | 2 | 0 |
| 2026-04 | sedentary_time | below | 2 | 0 |
| 2026-05 | glucose | below | 25 | 0 |
| 2026-05 | heart_rate | below | 7 | 6 |
| 2026-05 | resting_heart_rate | below | 6 | 0 |
| 2026-05 | medication_adherence | below | 1 | 1 |
| 2026-05 | blood_pressure | below | 1 | 0 |
| 2026-06 | glucose | above | 2 | 2 |
| 2026-06 | glucose | below | 10 | 0 |
| 2026-06 | hydration | below | 1 | 1 |
| 2026-07 | glucose | below | 12 | 0 |
| 2026-07 | heart_rate | above | 3 | 3 |
| 2026-07 | medication_adherence | below | 2 | 2 |
| 2026-07 | sleep_duration | below | 1 | 1 |
| 2026-08 | glucose | below | 69 | 2 |
| 2026-08 | heart_rate | below | 33 | 21 |
| 2026-08 | resting_heart_rate | below | 6 | 0 |
| 2026-08 | blood_pressure | below | 3 | 0 |
| 2026-09 | glucose | above | 2 | 2 |
| 2026-09 | heart_rate | above | 20 | 20 |
| 2026-09 | heart_rate | below | 2 | 0 |
| 2026-09 | resting_heart_rate | above | 3 | 3 |
| 2026-09 | medication_adherence | below | 1 | 1 |
| 2026-09 | screen_time | above | 2 | 2 |
| 2026-09 | screen_time | below | 1 | 0 |
| 2026-09 | sleep_duration | below | 2 | 2 |
| 2026-09 | blood_pressure | above | 1 | 1 |
| 2026-09 | step_count | above | 1 | 0 |
| 2026-09 | sedentary_time | below | 1 | 0 |
| 2026-09 | hydration | above | 1 | 0 |


### By month (all measures)

| month | before | after |
|---|---|---|
| 2025-10 | 46 | 40 |
| 2025-11 | 44 | 41 |
| 2025-12 | 24 | 15 |
| 2026-01 | 51 | 46 |
| 2026-02 | 51 | 31 |
| 2026-03 | 71 | 54 |
| 2026-04 | 59 | 19 |
| 2026-05 | 40 | 7 |
| 2026-06 | 13 | 3 |
| 2026-07 | 18 | 6 |
| 2026-08 | 111 | 23 |
| 2026-09 | 37 | 31 |


## 3. Hand-offs on the story days (after the change)

The number in brackets is the hand-off count on that day before the change.


### 2025-11-17: 5 hand-offs (5)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_heart_rate_2025-11-17T00:15 | heart_rate | above | clearly | persistence | 79.2 | normal | 00:15 |
| handoff_sleep_duration_2025-11-17T07:00 | sleep_duration | below | clearly | persistence | 4.8 | low | 07:00 |
| handoff_heart_rate_2025-11-17T08:15 | heart_rate | above | clearly | persistence | 115.1 |  | 08:15 |
| handoff_medication_adherence_2025-11-17T21:00 | medication_adherence | below | clearly | persistence | {"taken": 1, "expected": 3, "missed": ["med_003_amlodipine", "med_004_levothyroxine"]} |  | 21:00 |
| handoff_heart_rate_2025-11-17T23:45 | heart_rate | above | clearly | persistence | 79.9 |  | 23:45 |


### 2025-11-18: 5 hand-offs (5)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_glucose_2025-11-18T00:15 | glucose | above | clearly | persistence | 144.2 | high | 00:15 |
| handoff_blood_pressure_2025-11-18T08:17 | blood_pressure | above | clearly | persistence | {"systolic": 136.0, "diastolic": 91.0} | high | 08:17 |
| handoff_glucose_2025-11-18T11:15 | glucose | above | clearly | persistence | 146.0 | high | 11:15 |
| handoff_glucose_2025-11-18T15:15 | glucose | above | clearly | persistence | 174.3 | high | 15:15 |
| handoff_heart_rate_2025-11-18T22:15 | heart_rate | above | clearly | persistence | 96.6 |  | 22:15 |


### 2025-11-19: 9 hand-offs (9)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_hydration_2025-11-19T00:00 | hydration | below | clearly | persistence | 1248.0 | low | 00:00 |
| handoff_heart_rate_2025-11-19T04:00 | heart_rate | above | clearly | persistence | 84.5 | normal | 04:00 |
| handoff_glucose_2025-11-19T04:30 | glucose | above | clearly | persistence | 152.0 | high | 04:30 |
| handoff_resting_heart_rate_2025-11-19T07:04 | resting_heart_rate | above | far | severe | 92.0 | normal | 07:04 |
| handoff_glucose_2025-11-19T11:15 | glucose | above | clearly | persistence | 156.5 | high | 11:15 |
| handoff_heart_rate_2025-11-19T12:15 | heart_rate | above | clearly | persistence | 109.6 |  | 12:15 |
| handoff_heart_rate_2025-11-19T13:45 | heart_rate | above | clearly | persistence | 111.6 |  | 13:45 |
| handoff_heart_rate_2025-11-19T22:45 | heart_rate | above | clearly | persistence | 92.5 |  | 22:45 |
| handoff_glucose_2025-11-19T23:15 | glucose | above | far | severe | 155.9 | high | 23:15 |


### 2025-11-20: 4 hand-offs (4)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_heart_rate_2025-11-20T03:15 | heart_rate | above | clearly | persistence | 84.5 | normal | 03:15 |
| handoff_glucose_2025-11-20T08:45 | glucose | above | far | severe | 175.1 | high | 08:45 |
| handoff_glucose_2025-11-20T23:00 | glucose | above | clearly | persistence | 160.2 | high | 23:00 |
| handoff_heart_rate_2025-11-20T23:45 | heart_rate | above | clearly | persistence | 84.7 | normal | 23:45 |


### 2026-04-06: 5 hand-offs (5)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_heart_rate_2026-04-06T00:00 | heart_rate | above | far | severe | 106.4 | high | 00:00 |
| handoff_sleep_duration_2026-04-06T07:00 | sleep_duration | below | clearly | persistence | 4.5 | low | 07:00 |
| handoff_resting_heart_rate_2026-04-06T07:27 | resting_heart_rate | above | far | severe | 102.0 | high | 07:27 |
| handoff_heart_rate_2026-04-06T09:30 | heart_rate | above | clearly | persistence | 109.7 |  | 09:30 |
| handoff_heart_rate_2026-04-06T11:30 | heart_rate | above | clearly | persistence | 106.5 |  | 11:30 |


### 2026-09-14: 4 hand-offs (4)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_heart_rate_2026-09-14T00:00 | heart_rate | above | far | severe | 95.6 | normal | 00:00 |
| handoff_heart_rate_2026-09-14T06:15 | heart_rate | above | clearly | persistence | 112.8 |  | 06:15 |
| handoff_sleep_duration_2026-09-14T07:00 | sleep_duration | below | clearly | persistence | 4.3 | low | 07:00 |
| handoff_resting_heart_rate_2026-09-14T07:22 | resting_heart_rate | above | clearly | persistence | 92.0 | normal | 07:22 |


### 2026-09-15: 4 hand-offs (4)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_heart_rate_2026-09-15T05:15 | heart_rate | above | clearly | persistence | 86.1 | normal | 05:15 |
| handoff_heart_rate_2026-09-15T06:15 | heart_rate | above | clearly | persistence | 107.8 |  | 06:15 |
| handoff_heart_rate_2026-09-15T09:15 | heart_rate | above | clearly | persistence | 116.8 |  | 09:15 |
| handoff_heart_rate_2026-09-15T22:30 | heart_rate | above | clearly | persistence | 101.1 |  | 22:30 |


### 2026-09-16: 3 hand-offs (3)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_heart_rate_2026-09-16T07:00 | heart_rate | above | clearly | persistence | 98.4 |  | 07:00 |
| handoff_blood_pressure_2026-09-16T08:13 | blood_pressure | above | clearly | persistence | {"systolic": 138.0, "diastolic": 92.0} | high | 08:13 |
| handoff_heart_rate_2026-09-16T18:45 | heart_rate | above | clearly | persistence | 109.8 |  | 18:45 |


### 2026-09-17: 7 hand-offs (7)

| hand-off | measure | direction | size | trigger | value | clinical status | written_at |
|---|---|---|---|---|---|---|---|
| handoff_screen_time_2026-09-17T00:00 | screen_time | above | clearly | persistence | 9.5 | high | 00:00 |
| handoff_heart_rate_2026-09-17T06:15 | heart_rate | above | clearly | persistence | 101.1 |  | 06:15 |
| handoff_resting_heart_rate_2026-09-17T07:08 | resting_heart_rate | above | clearly | persistence | 93.0 | normal | 07:08 |
| handoff_heart_rate_2026-09-17T08:45 | heart_rate | above | clearly | persistence | 111.9 |  | 08:45 |
| handoff_heart_rate_2026-09-17T12:15 | heart_rate | above | clearly | persistence | 109.9 |  | 12:15 |
| handoff_heart_rate_2026-09-17T21:45 | heart_rate | above | clearly | persistence | 112.0 |  | 21:45 |
| handoff_glucose_2026-09-17T22:30 | glucose | above | clearly | persistence | 185.0 | high | 22:30 |


## 4. August 2026 and May 2026

| month | items opened | hand-offs before | hand-offs after | favourable items (no hand-off) |
|---|---|---|---|---|
| 2026-08 | 111 | 111 | 23 | 88 |
| 2026-05 | 40 | 40 | 7 | 33 |


## 5. Items of exactly 30 minutes among hand-offs

Before: 154 of 565 hand-offs. After: **77** of 316.

| measure | direction | before | after |
|---|---|---|---|
| glucose | above | 36 | 36 |
| glucose | below | 70 | 4 |
| heart_rate | above | 24 | 24 |
| heart_rate | below | 24 | 13 |


## 6. Glucose below her usual that still has a hand-off (5)

Before the change there were 186 glucose-below hand-offs (all 186 items). `value` is the glucose at opening; `peak` is the lowest-position reading while open.

| item | trigger | size at open | size at peak | clinical status at open | value at open (mg/dL) | peak value (mg/dL) | opened_at | closed_at |
|---|---|---|---|---|---|---|---|---|
| glucose_2025-11-08T11:00 | severe | far | far | low | 65.0 | 65.0 | 2025-11-08 11:00 | 2025-11-08 11:30 |
| glucose_2026-01-20T16:00 | severe | far | far | low | 65.0 | 65.0 | 2026-01-20 16:00 | 2026-01-20 16:30 |
| glucose_2026-03-22T11:00 | severe | far | far | low | 65.0 | 65.0 | 2026-03-22 11:00 | 2026-03-22 11:30 |
| glucose_2026-08-19T15:00 | severe | far | far | low | 65.0 | 65.0 | 2026-08-19 15:00 | 2026-08-19 17:15 |
| glucose_2026-08-22T10:30 | severe | far | far | normal | 76.3 | 76.3 | 2026-08-22 10:30 | 2026-08-22 11:00 |
