# V0, the year in numbers

Computed on findings_loop_polish.db, pi_loop_polish.db and state_engine.db (read-only; `scripts/v0_docs.py`). Data: 1 Oct 2025 to 17 Sep 2026, one patient.

## Alerts (State Engine hand-offs) by type and month

287 alerts in all (a hand-off is an alert handed to the pipeline).

| measure and direction | total | 2025-10 | 2025-11 | 2025-12 | 2026-01 | 2026-02 | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| blood_pressure above | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| glucose above | 99 | 16 | 17 | 2 | 30 | 14 | 16 | 0 | 0 | 2 | 0 | 0 | 2 |
| glucose below | 5 | 0 | 1 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 2 | 0 |
| heart_rate above | 124 | 20 | 13 | 12 | 8 | 12 | 23 | 13 | 0 | 0 | 3 | 0 | 20 |
| hydration below | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| medication_adherence below | 24 | 1 | 2 | 1 | 6 | 3 | 5 | 2 | 1 | 0 | 2 | 0 | 1 |
| resting_heart_rate above | 12 | 1 | 1 | 0 | 1 | 1 | 4 | 1 | 0 | 0 | 0 | 0 | 3 |
| screen_time above | 8 | 1 | 3 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| sleep_duration below | 10 | 1 | 1 | 0 | 0 | 1 | 3 | 1 | 0 | 0 | 1 | 0 | 2 |

## Cases and versions by month

| month | cases | versions |
|---|---|---|
| 2025-10 | 11 | 39 |
| 2025-11 | 14 | 39 |
| 2025-12 | 7 | 15 |
| 2026-01 | 16 | 47 |
| 2026-02 | 18 | 31 |
| 2026-03 | 18 | 53 |
| 2026-04 | 7 | 17 |
| 2026-05 | 1 | 1 |
| 2026-06 | 3 | 3 |
| 2026-07 | 6 | 6 |
| 2026-08 | 2 | 4 |
| 2026-09 | 13 | 29 |

Total: 116 cases, 284 versions (a version is a case's text as of each new alert or completion).

## Texts

- written by the model in the last run (prompt p-v5): 143
- kept from earlier prompts (re-checked under the final checks): 132
- code-line fallbacks: 9 (3.2%)
- all: 284

Fallback reasons (the checks that failed on the last attempt):

| failed check(s) | versions |
|---|---|
| claim_level | 3 |
| no_repeated_phrase | 3 |
| structure | 1 |
| claim_level, no_digits_dates_counts | 1 |
| no_copied_diary_or_internal_words | 1 |

## PI

- weekly jobs: 51 (calendar weeks, Monday to Sunday)
- long-term memories (relationships): 29; versions written: 174
- mid-term weekly memories sealed: 51

Status at the end:

| status | memories |
|---|---|
| candidate | 3 |
| retracted | 1 |
| supported | 25 |

Status transitions over the year (every move, all memories):

| transition | count |
|---|---|
| candidate to supported | 26 |
| supported to weakened | 1 |
| weakened to retracted | 1 |

Situations lines: 133 of 174 memory versions carry one.

## Known limit: repeated headline or sentence

- versions whose headline is repeated as one of their sentences: **10**
- versions with a sentence written twice: **3**
- versions affected in all: **13** of 284
