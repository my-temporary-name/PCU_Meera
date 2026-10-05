# State Engine: final counts

From `output/state_engine.db` after the final change (full replay 2025-10-01 to 2026-09-17, 33,792 ticks). Item class: `adverse` / `favourable` by config `adverse_directions`; a favourable item gets no hand-off unless its position is `far` (or, for non-continuous measures, its carried clinical status is abnormal on that side). No interpretation.

## Totals

|  | count |
|---|---|
| items | 565 |
| hand-offs | 287 |
| items: adverse | 287 |
| items: favourable (no hand-off) | 278 |
| hand-offs: persistence | 264 |
| hand-offs: severe | 23 |


## By measure x direction

| measure | direction | items | adverse | favourable | hand-offs |
|---|---|---|---|---|---|
| glucose | above | 99 | 99 | 0 | 99 |
| glucose | below | 186 | 5 | 181 | 5 |
| heart_rate | above | 124 | 124 | 0 | 124 |
| heart_rate | below | 49 | 0 | 49 | 0 |
| resting_heart_rate | above | 12 | 12 | 0 | 12 |
| resting_heart_rate | below | 14 | 0 | 14 | 0 |
| medication_adherence | below | 24 | 24 | 0 | 24 |
| screen_time | above | 8 | 8 | 0 | 8 |
| screen_time | below | 6 | 0 | 6 | 0 |
| sleep_duration | below | 10 | 10 | 0 | 10 |
| blood_pressure | above | 3 | 3 | 0 | 3 |
| blood_pressure | below | 7 | 0 | 7 | 0 |
| step_count | above | 9 | 0 | 9 | 0 |
| sedentary_time | below | 9 | 0 | 9 | 0 |
| hydration | above | 3 | 0 | 3 | 0 |
| hydration | below | 2 | 2 | 0 | 2 |


## Per month (by `opened_at` / `written_at`)

| month | items | adverse | favourable | hand-offs |
|---|---|---|---|---|
| 2025-10 | 46 | 40 | 6 | 40 |
| 2025-11 | 44 | 41 | 3 | 41 |
| 2025-12 | 24 | 15 | 9 | 15 |
| 2026-01 | 51 | 46 | 5 | 46 |
| 2026-02 | 51 | 31 | 20 | 31 |
| 2026-03 | 71 | 54 | 17 | 54 |
| 2026-04 | 59 | 17 | 42 | 17 |
| 2026-05 | 40 | 1 | 39 | 1 |
| 2026-06 | 13 | 3 | 10 | 3 |
| 2026-07 | 18 | 6 | 12 | 6 |
| 2026-08 | 111 | 2 | 109 | 2 |
| 2026-09 | 37 | 31 | 6 | 31 |


## Per month x measure (hand-offs)

| month | glucose | heart_rate | resting_heart_rate | medication_adherence | screen_time | sleep_duration | blood_pressure | step_count | sedentary_time | hydration |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-10 | 16 | 20 | 1 | 1 | 1 | 1 |  |  |  |  |
| 2025-11 | 18 | 13 | 1 | 2 | 3 | 1 | 2 |  |  | 1 |
| 2025-12 | 2 | 12 |  | 1 |  |  |  |  |  |  |
| 2026-01 | 31 | 8 | 1 | 6 |  |  |  |  |  |  |
| 2026-02 | 14 | 12 | 1 | 3 |  | 1 |  |  |  |  |
| 2026-03 | 17 | 23 | 4 | 5 | 2 | 3 |  |  |  |  |
| 2026-04 |  | 13 | 1 | 2 |  | 1 |  |  |  |  |
| 2026-05 |  |  |  | 1 |  |  |  |  |  |  |
| 2026-06 | 2 |  |  |  |  |  |  |  |  | 1 |
| 2026-07 |  | 3 |  | 2 |  | 1 |  |  |  |  |
| 2026-08 | 2 |  |  |  |  |  |  |  |  |  |
| 2026-09 | 2 | 20 | 3 | 1 | 2 | 2 | 1 |  |  |  |
