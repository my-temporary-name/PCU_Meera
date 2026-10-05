# State Engine: report on all 565 deviation items

Read-only. Source: `output/state_engine.db` (tables `state_items`, `state_handoffs`, `state_log`), the full replay 2025-10-01 to 2026-09-17 (33792 ticks). No interpretation. A day is a local calendar day (Asia/Kolkata); an item belongs to the day of its `opened_at`. Durations are `closed_at - opened_at`; items still open at the end of the data are listed separately where relevant.

## 1. Counts

### By measure

| measure | items | still open | closed: recovered | closed: stale | closed: expired |
|---|---|---|---|---|---|
| glucose | 285 | 0 | 284 | 1 | 0 |
| heart_rate | 173 | 1 | 172 | 0 | 0 |
| resting_heart_rate | 26 | 1 | 25 | 0 | 0 |
| medication_adherence | 24 | 1 | 23 | 0 | 0 |
| screen_time | 14 | 1 | 13 | 0 | 0 |
| sleep_duration | 10 | 1 | 9 | 0 | 0 |
| blood_pressure | 10 | 1 | 9 | 0 | 0 |
| sedentary_time | 9 | 0 | 9 | 0 | 0 |
| step_count | 9 | 0 | 8 | 0 | 1 |
| hydration | 5 | 0 | 5 | 0 | 0 |

### By trigger

| trigger | items |
|---|---|
| persistence | 542 |
| severe | 23 |



### By direction and size at open

| direction | size at open | items |
|---|---|---|
| above | clearly | 242 |
| above | far | 16 |
| below | clearly | 300 |
| below | far | 7 |


### By month opened (and measure)

| month | items | glucose | heart_rate | resting_heart_rate | medication_adherence | screen_time | sleep_duration | blood_pressure | sedentary_time | step_count | hydration |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-10 | 46 | 17 | 20 | 1 | 1 | 3 | 1 |  | 1 | 1 | 1 |
| 2025-11 | 44 | 19 | 15 | 1 | 2 | 3 | 1 | 2 |  |  | 1 |
| 2025-12 | 24 | 6 | 12 |  | 1 | 1 |  |  | 2 | 2 |  |
| 2026-01 | 51 | 35 | 8 | 1 | 6 |  |  | 1 |  |  |  |
| 2026-02 | 51 | 27 | 12 | 1 | 3 | 1 | 1 | 1 | 2 | 2 | 1 |
| 2026-03 | 71 | 31 | 23 | 4 | 5 | 3 | 3 |  | 1 | 1 |  |
| 2026-04 | 59 | 30 | 18 | 3 | 2 |  | 1 | 1 | 2 | 2 |  |
| 2026-05 | 40 | 25 | 7 | 6 | 1 |  |  | 1 |  |  |  |
| 2026-06 | 13 | 12 |  |  |  |  |  |  |  |  | 1 |
| 2026-07 | 18 | 12 | 3 |  | 2 |  | 1 |  |  |  |  |
| 2026-08 | 111 | 69 | 33 | 6 |  |  |  | 3 |  |  |  |
| 2026-09 | 37 | 2 | 22 | 3 | 1 | 3 | 2 | 1 | 1 | 1 | 1 |


## 2. Duration of continuous items (glucose, heart rate)

Closed items only; items still open at the end of the data are counted separately.


| measure | items | closed | open at end | median duration | p90 duration | shortest | longest |
|---|---|---|---|---|---|---|---|
| glucose | 285 | 285 | 0 | 0h 45m | 3h 24m | 0h 30m | 1d 2h 0m |
| heart_rate | 173 | 172 | 1 | 1h 0m | 5h 58m | 0h 30m | 1d 18h 15m |
| both | 458 | 457 | 1 | 1h 0m | 4h 15m | 0h 30m | 1d 18h 15m |

(p90 by linear interpolation between ranks.)

## 3. Items opened per day: August 2026 versus November 2025


| month | days | items opened | per day (mean) | per day (median) | min / day | max / day | days with none |
|---|---|---|---|---|---|---|---|
| 2026-08 | 31 | 111 | 3.58 | 3 | 0 | 11 | 7 |
| 2025-11 | 30 | 44 | 1.47 | 0.0 | 0 | 9 | 18 |


2026-08 by measure: glucose 69, heart_rate 33, resting_heart_rate 6, blood_pressure 3


2025-11 by measure: glucose 19, heart_rate 15, screen_time 3, blood_pressure 2, medication_adherence 2, sleep_duration 1, hydration 1, resting_heart_rate 1


## 4. What opened on the listed days


### 2025-11-18: 5 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| glucose_2025-11-18T00:15 | glucose | above | clearly | persistence | 00:15 | 2025-11-18 08:30 | recovered | closed |
| blood_pressure_2025-11-18T08:17 | blood_pressure | above | clearly | persistence | 08:17 | 2025-11-22 08:10 | recovered | closed |
| glucose_2025-11-18T11:15 | glucose | above | clearly | persistence | 11:15 | 2025-11-18 14:00 | recovered | closed |
| glucose_2025-11-18T15:15 | glucose | above | clearly | persistence | 15:15 | 2025-11-18 20:45 | recovered | closed |
| heart_rate_2025-11-18T22:15 | heart_rate | above | clearly | persistence | 22:15 | 2025-11-19 03:30 | recovered | closed |


### 2025-11-19: 9 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| hydration_2025-11-19T00:00 | hydration | below | clearly | persistence | 00:00 | 2025-11-21 00:00 | recovered | closed |
| heart_rate_2025-11-19T04:00 | heart_rate | above | clearly | persistence | 04:00 | 2025-11-19 05:00 | recovered | closed |
| glucose_2025-11-19T04:30 | glucose | above | clearly | persistence | 04:30 | 2025-11-19 08:30 | recovered | closed |
| resting_heart_rate_2025-11-19T07:04 | resting_heart_rate | above | far | severe | 07:04 | 2025-11-21 07:30 | recovered | closed |
| glucose_2025-11-19T11:15 | glucose | above | clearly | persistence | 11:15 | 2025-11-19 21:45 | recovered | closed |
| heart_rate_2025-11-19T12:15 | heart_rate | above | clearly | persistence | 12:15 | 2025-11-19 13:15 | recovered | closed |
| heart_rate_2025-11-19T13:45 | heart_rate | above | clearly | persistence | 13:45 | 2025-11-19 17:30 | recovered | closed |
| heart_rate_2025-11-19T22:45 | heart_rate | above | clearly | persistence | 22:45 | 2025-11-19 23:15 | recovered | closed |
| glucose_2025-11-19T23:15 | glucose | above | far | severe | 23:15 | 2025-11-20 08:30 | recovered | closed |


### 2025-11-20: 4 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| heart_rate_2025-11-20T03:15 | heart_rate | above | clearly | persistence | 03:15 | 2025-11-20 03:45 | recovered | closed |
| glucose_2025-11-20T08:45 | glucose | above | far | severe | 08:45 | 2025-11-20 21:45 | recovered | closed |
| glucose_2025-11-20T23:00 | glucose | above | clearly | persistence | 23:00 | 2025-11-21 00:15 | recovered | closed |
| heart_rate_2025-11-20T23:45 | heart_rate | above | clearly | persistence | 23:45 | 2025-11-21 00:15 | recovered | closed |


### 2026-04-06: 5 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| heart_rate_2026-04-06T00:00 | heart_rate | above | far | severe | 00:00 | 2026-04-06 08:30 | recovered | closed |
| sleep_duration_2026-04-06T07:00 | sleep_duration | below | clearly | persistence | 07:00 | 2026-04-07 07:00 | recovered | closed |
| resting_heart_rate_2026-04-06T07:27 | resting_heart_rate | above | far | severe | 07:27 | 2026-04-08 07:05 | recovered | closed |
| heart_rate_2026-04-06T09:30 | heart_rate | above | clearly | persistence | 09:30 | 2026-04-06 10:15 | recovered | closed |
| heart_rate_2026-04-06T11:30 | heart_rate | above | clearly | persistence | 11:30 | 2026-04-07 00:15 | recovered | closed |


### 2026-09-14: 4 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| heart_rate_2026-09-14T00:00 | heart_rate | above | far | severe | 00:00 | 2026-09-14 05:45 | recovered | closed |
| heart_rate_2026-09-14T06:15 | heart_rate | above | clearly | persistence | 06:15 | 2026-09-15 04:45 | recovered | closed |
| sleep_duration_2026-09-14T07:00 | sleep_duration | below | clearly | persistence | 07:00 |  |  | open |
| resting_heart_rate_2026-09-14T07:22 | resting_heart_rate | above | clearly | persistence | 07:22 | 2026-09-16 07:25 | recovered | closed |


### 2026-09-15: 4 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| heart_rate_2026-09-15T05:15 | heart_rate | above | clearly | persistence | 05:15 | 2026-09-15 05:45 | recovered | closed |
| heart_rate_2026-09-15T06:15 | heart_rate | above | clearly | persistence | 06:15 | 2026-09-15 08:30 | recovered | closed |
| heart_rate_2026-09-15T09:15 | heart_rate | above | clearly | persistence | 09:15 | 2026-09-15 21:15 | recovered | closed |
| heart_rate_2026-09-15T22:30 | heart_rate | above | clearly | persistence | 22:30 | 2026-09-16 05:15 | recovered | closed |


### 2026-09-16: 3 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| heart_rate_2026-09-16T07:00 | heart_rate | above | clearly | persistence | 07:00 | 2026-09-16 07:30 | recovered | closed |
| blood_pressure_2026-09-16T08:13 | blood_pressure | above | clearly | persistence | 08:13 |  |  | open |
| heart_rate_2026-09-16T18:45 | heart_rate | above | clearly | persistence | 18:45 | 2026-09-17 05:30 | recovered | closed |


### 2026-09-17: 7 items opened

| item_id | measure | direction | size at open | trigger | opened_at | closed_at | close reason | status |
|---|---|---|---|---|---|---|---|---|
| screen_time_2026-09-17T00:00 | screen_time | above | clearly | persistence | 00:00 |  |  | open |
| heart_rate_2026-09-17T06:15 | heart_rate | above | clearly | persistence | 06:15 | 2026-09-17 08:15 | recovered | closed |
| resting_heart_rate_2026-09-17T07:08 | resting_heart_rate | above | clearly | persistence | 07:08 |  |  | open |
| heart_rate_2026-09-17T08:45 | heart_rate | above | clearly | persistence | 08:45 | 2026-09-17 09:15 | recovered | closed |
| heart_rate_2026-09-17T12:15 | heart_rate | above | clearly | persistence | 12:15 | 2026-09-17 21:15 | recovered | closed |
| heart_rate_2026-09-17T21:45 | heart_rate | above | clearly | persistence | 21:45 |  |  | open |
| glucose_2026-09-17T22:30 | glucose | above | clearly | persistence | 22:30 | 2026-09-17 23:00 | recovered | closed |


## 5. Days with zero items, and days with more than 5

| question | days | of 352 |
|---|---|---|
| days on which no item opened | 194 | 352 |
| days on which no item was open at any tick | 159 | 352 |
| days on which more than 5 items opened | 35 | 352 |
| days on which more than 5 items were open at the same time (max over the day's ticks) | 13 | 352 |


Days on which no item opened: 2025-10-01 to 2025-10-14; 2025-10-17; 2025-10-22; 2025-10-25 to 2025-10-26; 2025-10-30; 2025-11-02; 2025-11-05 to 2025-11-06; 2025-11-09; 2025-11-12; 2025-11-14 to 2025-11-16; 2025-11-21 to 2025-12-01; 2025-12-03 to 2025-12-08; 2025-12-10 to 2025-12-14; 2025-12-16 to 2025-12-19; 2025-12-22 to 2025-12-23; 2025-12-27 to 2025-12-30; 2026-01-02 to 2026-01-03; 2026-01-05; 2026-01-07; 2026-01-09; 2026-01-11; 2026-01-15 to 2026-01-19; 2026-01-21; 2026-01-23; 2026-01-25; 2026-01-27; 2026-01-29; 2026-01-31 to 2026-02-02; 2026-02-05; 2026-02-11; 2026-02-16; 2026-02-18; 2026-02-20; 2026-02-23; 2026-02-25 to 2026-02-26; 2026-02-28; 2026-03-02; 2026-03-07; 2026-03-18 to 2026-03-20; 2026-03-24 to 2026-04-01; 2026-04-03 to 2026-04-05; 2026-04-08 to 2026-04-10; 2026-04-13 to 2026-04-15; 2026-04-21 to 2026-04-24; 2026-04-27 to 2026-04-28; 2026-05-02 to 2026-05-03; 2026-05-05 to 2026-05-14; 2026-05-16; 2026-05-19; 2026-05-23 to 2026-05-24; 2026-05-30 to 2026-06-05; 2026-06-07 to 2026-06-11; 2026-06-14 to 2026-06-16; 2026-06-18; 2026-06-20 to 2026-06-27; 2026-06-29 to 2026-07-02; 2026-07-04 to 2026-07-07; 2026-07-09; 2026-07-12 to 2026-07-15; 2026-07-17; 2026-07-19 to 2026-07-24; 2026-07-26 to 2026-07-28; 2026-07-31; 2026-08-10 to 2026-08-12; 2026-08-24 to 2026-08-25; 2026-08-28 to 2026-08-29; 2026-09-01; 2026-09-03 to 2026-09-07; 2026-09-10

Days on which no item was open at any tick: 2025-10-01 to 2025-10-14; 2025-10-22; 2025-10-25 to 2025-10-26; 2025-11-02; 2025-11-05 to 2025-11-06; 2025-11-09; 2025-11-15 to 2025-11-16; 2025-11-23 to 2025-12-01; 2025-12-03 to 2025-12-08; 2025-12-11 to 2025-12-14; 2025-12-16 to 2025-12-19; 2025-12-22 to 2025-12-23; 2025-12-28 to 2025-12-30; 2026-01-02 to 2026-01-03; 2026-01-15 to 2026-01-19; 2026-01-21; 2026-01-23; 2026-01-25; 2026-01-29; 2026-02-01 to 2026-02-02; 2026-02-05; 2026-02-11; 2026-02-18; 2026-02-20; 2026-02-23; 2026-02-25 to 2026-02-26; 2026-03-02; 2026-03-07; 2026-03-19 to 2026-03-20; 2026-03-24 to 2026-04-01; 2026-04-04 to 2026-04-05; 2026-04-09 to 2026-04-10; 2026-04-14 to 2026-04-15; 2026-04-27 to 2026-04-28; 2026-05-03; 2026-05-06 to 2026-05-14; 2026-05-16; 2026-05-23 to 2026-05-24; 2026-06-01 to 2026-06-05; 2026-06-07 to 2026-06-11; 2026-06-14 to 2026-06-16; 2026-06-18; 2026-06-20 to 2026-06-27; 2026-06-29 to 2026-07-02; 2026-07-04 to 2026-07-07; 2026-07-12 to 2026-07-15; 2026-07-19 to 2026-07-24; 2026-07-26 to 2026-07-28; 2026-08-11 to 2026-08-12; 2026-08-24 to 2026-08-25; 2026-08-28 to 2026-08-29; 2026-09-03 to 2026-09-07


Days on which more than 5 items opened (date: items opened): 2025-10-15: 8, 2025-10-19: 9, 2025-10-20: 8, 2025-10-31: 6, 2025-11-10: 6, 2025-11-19: 9, 2025-12-25: 6, 2026-01-12: 8, 2026-01-24: 8, 2026-01-28: 7, 2026-01-30: 8, 2026-02-13: 8, 2026-02-17: 6, 2026-03-04: 12, 2026-03-06: 8, 2026-03-16: 8, 2026-03-17: 11, 2026-04-11: 8, 2026-04-17: 8, 2026-04-18: 8, 2026-04-25: 7, 2026-05-17: 6, 2026-05-25: 13, 2026-05-27: 6, 2026-07-03: 7, 2026-08-01: 9, 2026-08-03: 8, 2026-08-04: 10, 2026-08-08: 7, 2026-08-17: 10, 2026-08-20: 7, 2026-08-21: 11, 2026-08-26: 8, 2026-09-13: 8, 2026-09-17: 7


Days on which more than 5 items were open at once (date: maximum open at one tick): 2025-10-20: 6, 2025-11-19: 7, 2025-11-20: 7, 2026-02-13: 6, 2026-02-14: 8, 2026-02-15: 9, 2026-02-16: 8, 2026-03-17: 6, 2026-09-13: 7, 2026-09-14: 7, 2026-09-15: 7, 2026-09-16: 7, 2026-09-17: 7

## 6. Hand-offs close to another hand-off


| question | hand-offs |
|---|---|
| total hand-offs | 565 |
| have another hand-off written within 30 minutes (before or after) | 84 |
| were written within 30 minutes AFTER another hand-off | 46 |
| clusters (hand-offs chained by gaps of 30 minutes or less) | 519 |
| hand-offs written at exactly the same moment as another | 22 |


## 7. The 10 shortest and the 10 longest items

Among the 559 closed items. Ties are broken by opening time. 154 closed items share the shortest duration (0h 30m).

### 10 shortest

| item_id | measure | direction | size at open | size at peak | trigger | opened_at | closed_at | duration | close reason |
|---|---|---|---|---|---|---|---|---|---|
| heart_rate_2025-10-15T00:15 | heart_rate | above | clearly | clearly | persistence | 2025-10-15 00:15 | 2025-10-15 00:45 | 0h 30m | recovered |
| glucose_2025-10-15T20:00 | glucose | above | clearly | clearly | persistence | 2025-10-15 20:00 | 2025-10-15 20:30 | 0h 30m | recovered |
| heart_rate_2025-10-16T00:15 | heart_rate | above | clearly | clearly | persistence | 2025-10-16 00:15 | 2025-10-16 00:45 | 0h 30m | recovered |
| heart_rate_2025-10-16T04:00 | heart_rate | above | clearly | clearly | persistence | 2025-10-16 04:00 | 2025-10-16 04:30 | 0h 30m | recovered |
| glucose_2025-10-16T19:30 | glucose | above | clearly | clearly | persistence | 2025-10-16 19:30 | 2025-10-16 20:00 | 0h 30m | recovered |
| glucose_2025-10-19T21:30 | glucose | below | clearly | clearly | persistence | 2025-10-19 21:30 | 2025-10-19 22:00 | 0h 30m | recovered |
| heart_rate_2025-10-20T04:30 | heart_rate | above | clearly | clearly | persistence | 2025-10-20 04:30 | 2025-10-20 05:00 | 0h 30m | recovered |
| glucose_2025-10-20T14:45 | glucose | above | clearly | clearly | persistence | 2025-10-20 14:45 | 2025-10-20 15:15 | 0h 30m | recovered |
| glucose_2025-10-23T21:45 | glucose | above | clearly | clearly | persistence | 2025-10-23 21:45 | 2025-10-23 22:15 | 0h 30m | recovered |
| glucose_2025-10-31T05:15 | glucose | above | clearly | clearly | persistence | 2025-10-31 05:15 | 2025-10-31 05:45 | 0h 30m | recovered |


### 10 longest

| item_id | measure | direction | size at open | size at peak | trigger | opened_at | closed_at | duration | close reason |
|---|---|---|---|---|---|---|---|---|---|
| blood_pressure_2026-04-16T08:09 | blood_pressure | below | clearly | clearly | persistence | 2026-04-16 08:09 | 2026-04-25 08:15 | 9d 0h 6m | recovered |
| blood_pressure_2026-08-13T08:10 | blood_pressure | below | clearly | clearly | persistence | 2026-08-13 08:10 | 2026-08-22 08:08 | 8d 23h 58m | recovered |
| medication_adherence_2025-11-17T21:00 | medication_adherence | below | clearly | far | persistence | 2025-11-17 21:00 | 2025-11-22 21:00 | 5d 0h 0m | recovered |
| screen_time_2026-03-10T00:00 | screen_time | above | clearly | clearly | persistence | 2026-03-10 00:00 | 2026-03-15 00:00 | 5d 0h 0m | recovered |
| screen_time_2026-09-08T00:00 | screen_time | above | clearly | clearly | persistence | 2026-09-08 00:00 | 2026-09-13 00:00 | 5d 0h 0m | recovered |
| screen_time_2025-10-29T00:00 | screen_time | above | clearly | clearly | persistence | 2025-10-29 00:00 | 2025-11-02 00:00 | 4d 0h 0m | recovered |
| sedentary_time_2026-02-13T00:00 | sedentary_time | below | clearly | far | persistence | 2026-02-13 00:00 | 2026-02-17 00:00 | 4d 0h 0m | recovered |
| step_count_2026-02-13T00:00 | step_count | above | clearly | far | persistence | 2026-02-13 00:00 | 2026-02-17 00:00 | 4d 0h 0m | recovered |
| screen_time_2026-09-13T00:00 | screen_time | below | clearly | clearly | persistence | 2026-09-13 00:00 | 2026-09-17 00:00 | 4d 0h 0m | recovered |
| sedentary_time_2026-09-13T00:00 | sedentary_time | below | clearly | clearly | persistence | 2026-09-13 00:00 | 2026-09-17 00:00 | 4d 0h 0m | recovered |


### Items still open at the end of the data (2026-09-17T23:45:00+05:30): 6

| item_id | measure | direction | size at open | opened_at | open for |
|---|---|---|---|---|---|
| medication_adherence_2026-09-11T21:00 | medication_adherence | below | clearly | 2026-09-11 21:00 | 6d 2h 45m |
| sleep_duration_2026-09-14T07:00 | sleep_duration | below | clearly | 2026-09-14 07:00 | 3d 16h 45m |
| blood_pressure_2026-09-16T08:13 | blood_pressure | above | clearly | 2026-09-16 08:13 | 1d 15h 32m |
| screen_time_2026-09-17T00:00 | screen_time | above | clearly | 2026-09-17 00:00 | 23h 45m |
| resting_heart_rate_2026-09-17T07:08 | resting_heart_rate | above | clearly | 2026-09-17 07:08 | 16h 37m |
| heart_rate_2026-09-17T21:45 | heart_rate | above | clearly | 2026-09-17 21:45 | 2h 0m |
