# Evidence Engine scoring report (first patient, against the ground-truth manifest)

Read-only: the Evidence Engine's thresholds, library and code were not touched, every database was opened read-only, and the only thing written is this report (and the copy of the manifest in `docs/ground_truth_manifest.md`). Inputs: `relationship_evidence` for all 352 days (22,148 records), `event_evidence`, `event_completions`, and section 5 of the manifest. The scoring script lives in the session scratch directory, not in the repository; the method is described under each item so it can be rerun.

Terms: a *relationship* is a key such as `sleep_hours@prev_night->post_meal_peak:dinner`; the manifest's 49 rows expand to **63 keys** (7 post-meal rows x 3 meal kinds). A *relationship-day* is one record. *Tested* means the record has a permutation p-value (it passed the minimums). Counts are over relationship-days.

## 1. Doubts about the manifest classes (section 5), from the data

**Mechanical checks.** The class counts in the manifest are right (built_formula 2, built_by_story_day 19, unverified 4, not_built 24 = 49). Its Ordering column equals the library's for all 49 rows. The formulas of section 3 hold in the data: steps and sedentary minutes correlate at rho -0.96 (the inverse-linear formula, correlation 0.986, residual sd 11 minutes); steps and hydration at 0.69 (the formula `1800 + min(steps/10, 500)` correlates 0.77 with the data, median absolute error 79 mL); sedentary minutes and screen time at 0.43 (the ordinary-day formula correlates only 0.59, median error 0.47 hours, because deadline and rest days override it). The five artifact readings are at the stated times and values.

**Method for the rest.** For every key, on the last day (2026-09-17), I took the engine's own history table and measured: the raw (not detrended) rank correlation of exposure and outcome; how concentrated the exposure is on story days; how different the outcome is on story days; and the effect after removing story days (definitions in item 5). I looked for `not_built` keys with a large raw association that disappears on non-story days (a story coupling), or that follows a chain of two manifest formulas, and for built keys that show nothing. I changed nothing in the manifest.

**Doubts, most important first.**

1. **`sleep_hours@prev_night->` post-meal peak (3 kinds), `non_meal_mean`, `systolic_reading`, `missed_doses_day` are labelled `not_built`, but look story-coupled.** Raw rho between sleep and the peak is -0.40 (breakfast), -0.41 (lunch), -0.40 (`non_meal_mean`), -0.48 (systolic), and the outcomes are 0.4 to 0.5 standard deviations higher on story days. The engine's effect (0.28 to 0.33) disappears on the 79 or 80 days that have no mood override, no diary story entry and no log-listed condition (effect -0.11 to -0.22, wrong sign), and survives when only mood and diary days are removed (0.28 to 0.30). So the link runs through the glucose condition of the day, which is how the manifest itself describes `strained_period -> sleep` (`built_by_story_day`). `sleep -> glucose` should be the same class. The manifest's own text says it: sleep is hand-set from the story and glucose depends on the day's label.
2. **`late_meal@same_day->post_meal_peak` and `late_prior_dinner@prev_evening->` `non_meal_mean` / `sleep_hours_night` are `not_built` ("no shared story-day driver"), but late dinners sit on story days.** All 22 meals that start at or after 21:30 fall on days my reconstruction marks as story days (festivals, the wedding, travel, Holi, the September festival; the share of all dinner days that are story days is 74%, so 22 of 22 is not chance). `late_prior_dinner -> sleep` (supported on 242 days, effect 0.30) turns to -0.46 on non-story days, and the late dinners of 14 and 15 September coincide with the 4.0 to 4.5 hour nights.
3. **`missed_dose@2d->systolic_reading` is `not_built`, but the generation log couples them.** The log for 27 to 31 October says blood pressure and heart rate trend up and adherence dips to about 72% in the same stretch, and the November crisis does the same. Supported on 51 days (effect 0.54 to 0.61), and untestable once story days are removed (only 21 non-story readings).
4. **A chain of formulas, not independence: `hydration_total@prev_day->` `hr_day_mean` / `resting_hr_day`, `prior_day_glucose_mean@prev_day->fluid_intake_day`.** Hydration is a formula of the same day's steps (verified), steps drive hourly heart rate (recalled formula), and activity days lower glucose (section 2). Steps are strongly autocorrelated day to day, so a previous-day quantity inherits the link. Raw rho: hydration vs resting heart rate -0.20, prior-day glucose vs fluid -0.28. Effects are small (0.10 to 0.18); they survive removing mood and diary days (hydration) and vanish on non-story days (prior-day glucose, -0.04).
5. **`strained_period@prev_day->resting_hr_day` is `not_built`, with an effect of 0.99** (the largest `not_built` effect; 208 supported days). It still holds at 1.26 after removing mood and diary story days, because it picks days after a strained day that are themselves calm. Either the mood-to-heart-rate offset (recalled formula) reaches the next day's resting rate, or the story arcs last several days (the log's multi-day arcs). Not a clean `not_built`.
6. **The `built_by_story_day` rows that show nothing.** `non_home_day -> sleep_hours_night` (effect -0.02, sign right on only 66% of days), `non_home_day -> missed_doses_day` (-0.01), `non_home_day -> fluid_intake_day` is `not_built` and agrees; `symptom_entry@same_day->missed_doses_day` (-0.09, sign right on 26%); `symptom_entry@3d->post_meal_peak` for breakfast and lunch (about 0; only the dinner kind has the expected negative sign, -0.62 on average); `strained_period@1d` and `steps_total@1d -> post_meal_peak:dinner` have the *opposite* sign (-0.12, -0.12) while the lunch kind (stress; untestable for breakfast) and the breakfast and lunch kinds (steps) have the expected one. The manifest's statement that stress and illness days move all these together is not visible for these pairs.
7. **Expected signs for the `symptom_entry` rows that are not about peaks.** `symptom_entry@3d->non_meal_mean` and `symptom_entry@1d->day_min_glucose` carry "- for peaks" and the rationale about meal-rise ranges, which does not apply to a non-meal mean or a daily minimum (the engine finds +0.28 for the non-meal mean, the opposite of the expectation, 0% of days with the expected sign; the daily-minimum row has -0.73, but it is oriented so that a lower minimum is worse, so the sign needs a separate derivation).
8. **`steps_window_hourly -> hr_hour_mean` (built_formula).** The class is right, but the data show the generator ties heart rate to the **same** hour's steps: within a clock hour, the rank correlation of heart rate with the same hour's steps is 0.41 and with the previous hour's steps 0.12 (raw, all hours: 0.78 and 0.60). The library's exposure is the previous hour's row (spec 3.1 rule 8), so the engine measures the weak, lagged part. See "Surprises".
9. **The three `unverified` heart-rate rows with `sleep` and `symptom_entry@3d->resting_hr_day`** are strong in the data (mean effects 0.29 for `sleep -> hr_day_mean`, 0.41 for `sleep -> resting_hr_day`, 0.68 for `symptom_entry@3d -> resting_hr_day`; sign right on 98% to 100% of days), which agrees with the recalled description (sleep and event severity feed heart rate). `symptom_entry@3d->hr_day_mean` is weaker (effect 0.24 to 0.29, supported on 12% of days). I would class the first three as built. This needs the original heart-rate generator to settle.
10. **Small notes.** The `screen_hours` and `alcohol`, `environment`, `clinic`, `missed_dose@7d` pairs have no association or too few exposed days to see any, which fits `not_built`. The manifest's "Expected sign" for `not_built` rows is a dash. The manifest row for `strained_period@same_day->systolic_reading` (`built_by_story_day`) cannot be scored: it can never be ordered (no mood block has ended before an 08:00 reading).

**Effect of these doubts on scoring.** Every one of the 1,991 `supported` relationship-days labelled `not_built` belongs to a key named in doubts 1 to 5 (sleep: 957 days; prior-day glucose to fluid: 258; late dinner: 314; strained previous day: 208; hydration: 152; late meal lunch: 51; missed dose to systolic: 51). No `not_built` key outside the doubted ones is ever `supported`.

## 2. Item 1: class table

| class | manifest rows | keys | relationship-days | tested days | supported | suggestive | not_supported | supported share of tested |
|---|---|---|---|---|---|---|---|---|
| built_formula | 2 | 2 | 704 | 530 | 371 | 39 | 120 | 70.0% |
| built_by_story_day | 19 | 27 | 9,488 | 5,299 | 1,969 | 488 | 2,842 | 37.2% |
| unverified | 4 | 4 | 1,408 | 1,068 | 735 | 186 | 147 | 68.8% |
| not_built | 24 | 30 | 10,548 | 4,687 | 1,991 | 409 | 2,287 | 42.5% |

(The `unverified` rows are scored separately from `built_formula`, as the manifest asks. Supported shares of tested days: built_formula 70%, unverified 69%, built_by_story_day 37%, not_built 42%.)

## 3. Item 2: precision (share of `supported` relationship-days by class)

| class | supported days | share |
|---|---|---|
| built_formula | 371 | 7.3% |
| built_by_story_day | 1,969 | 38.9% |
| unverified | 735 | 14.5% |
| not_built | 1,991 | 39.3% |
| **all** | **5,066** | |

**The `not_built` share, the engine's false-find rate against the manifest, is 39.3% of supported days** (38.8% counting suggestive as well). Only 22% of supported days are built formulas or unverified heart-rate rows, 39% are story-day links (expected, section 8 of the manifest). As item 1 says, all of the `not_built` share comes from 14 keys whose class I doubt; if they are reclassified the false-find rate against the revised manifest is 0 of 5,066 supported days, and the question moves to whether the story-day links are mechanisms (they are not, by the manifest's own account).

Supported days that carry `same_day_unverified`: built_formula 209 of 371, built_by_story_day 1,346 of 1,969, unverified 735 of 735, not_built 324 of 1,991.

Largest contributors among `not_built`:

| key | supported days |
|---|---|
| `sleep_hours@prev_night->non_meal_mean` | 267 |
| `sleep_hours@prev_night->post_meal_peak:breakfast` | 262 |
| `sleep_hours@prev_night->post_meal_peak:lunch` | 261 |
| `prior_day_glucose_mean@prev_day->fluid_intake_day` | 258 |
| `late_prior_dinner@prev_evening->sleep_hours_night` | 242 |
| `strained_period@prev_day->resting_hr_day` | 208 |
| `sleep_hours@prev_night->systolic_reading` | 159 |
| `hydration_total@prev_day->resting_hr_day` | 121 |
| `late_prior_dinner@prev_evening->non_meal_mean` | 72 |
| `late_meal@same_day->post_meal_peak:lunch` | 51 |
| `missed_dose@2d->systolic_reading` | 51 |
| `hydration_total@prev_day->hr_day_mean` | 31 |
| `sleep_hours@prev_night->missed_doses_day` | 6 |
| `sleep_hours@prev_night->post_meal_peak:dinner` | 2 |

## 4. Item 3: recall of the formulas

| relationship | class | first tested | first supported | first suggestive or better | tested days | supported days | share |
|---|---|---|---|---|---|---|---|
| `steps_window_hourly@60m->hr_hour_mean` | built_formula | 2025-12-10 | 2025-12-10 | 2025-12-10 | 282 | 162 | 57.4% |
| `strained_period@same_day->hr_day_mean` | built_formula | 2026-01-13 | 2026-01-28 | 2026-01-13 | 248 | 209 | 84.3% |
| `symptom_entry@3d->hr_day_mean` | unverified | 2026-01-09 | 2026-01-28 | 2026-01-23 | 252 | 31 | 12.3% |
| `sleep_hours@prev_night->hr_day_mean` | unverified | 2025-12-10 | 2025-12-10 | 2025-12-10 | 282 | 244 | 86.5% |
| `sleep_hours@prev_night->resting_hr_day` | unverified | 2025-12-10 | 2025-12-10 | 2025-12-10 | 282 | 255 | 90.4% |
| `symptom_entry@3d->resting_hr_day` | unverified | 2026-01-09 | 2026-01-09 | 2026-01-09 | 252 | 205 | 81.3% |

`steps_window_hourly->hr_hour_mean` is supported on the first day it can be tested (2025-12-10, the first day with 60 distinct dates) but only on 57% of its tested days: its effect (median 0.12) sits just above the 0.10 floor. `strained_period@same_day->hr_day_mean` is `suggestive` from its first tested day (2026-01-13) and `supported` from 2026-01-28, on 84% of tested days, with effects of 1.4 to 1.6. Both are first tested only in December and January because of the history minimum (60 usable units and 60 distinct dates; the mood relationship also needs 15 exposed days).

## 5. Item 4: sign check (share of tested days whose effect has the expected sign)

Expected sign from the manifest, in the engine's orientation (`+` unless the manifest says `-`). `built_formula` and `unverified` rows are included; `not_built` rows have no expected sign.

| key | class | expected | tested days | sign matches | mean effect | supported days | sign matches among supported |
|---|---|---|---|---|---|---|---|
| `missed_dose@2d->non_meal_mean` | built_by_story_day | + | 210 | 72% | 0.109 | 51 | 100% |
| `symptom_entry@3d->non_meal_mean` | built_by_story_day | - | 252 | 0% | 0.278 | 37 | 0% |
| `strained_period@1d->non_meal_mean` | built_by_story_day | + | 248 | 100% | 0.911 | 229 | 100% |
| `steps_total@prev_day->non_meal_mean` | built_by_story_day | + | 281 | 100% | 0.231 | 213 | 100% |
| `high_steps_day@1d->day_min_glucose` | built_by_story_day | + | 277 | 100% | 0.609 | 232 | 100% |
| `symptom_entry@1d->day_min_glucose` | built_by_story_day | - | 93 | 100% | -0.733 | 0 |  |
| `steps_window_hourly@60m->hr_hour_mean` | built_formula | + | 282 | 100% | 0.124 | 162 | 100% |
| `strained_period@same_day->hr_day_mean` | built_formula | + | 248 | 100% | 1.431 | 209 | 100% |
| `symptom_entry@3d->hr_day_mean` | unverified | + | 252 | 98% | 0.287 | 31 | 100% |
| `sleep_hours@prev_night->hr_day_mean` | unverified | + | 282 | 100% | 0.288 | 244 | 100% |
| `sleep_hours@prev_night->resting_hr_day` | unverified | + | 282 | 100% | 0.409 | 255 | 100% |
| `symptom_entry@3d->resting_hr_day` | unverified | + | 252 | 100% | 0.678 | 205 | 100% |
| `strained_period@same_day->sleep_hours_night` | built_by_story_day | + | 253 | 100% | 0.816 | 232 | 100% |
| `symptom_entry@same_day->sleep_hours_night` | built_by_story_day | + | 92 | 100% | 0.349 | 0 |  |
| `non_home_day@same_day->sleep_hours_night` | built_by_story_day | + | 281 | 66% | 0.025 | 0 |  |
| `non_home_day@same_day->missed_doses_day` | built_by_story_day | + | 281 | 76% | 0.098 | 3 | 100% |
| `strained_period@same_day->missed_doses_day` | built_by_story_day | + | 248 | 100% | 0.689 | 229 | 100% |
| `symptom_entry@same_day->missed_doses_day` | built_by_story_day | + | 93 | 26% | -0.014 | 0 |  |
| `strained_period@same_day->systolic_reading` | built_by_story_day | + | 0 | never tested | | | |
| `symptom_entry@same_day->systolic_reading` | built_by_story_day | + | 0 | never tested | | | |
| `symptom_entry@same_day->fluid_intake_day` | built_by_story_day | + | 93 | 100% | 1.022 | 73 | 100% |
| `missed_dose@2d->post_meal_peak:breakfast` | built_by_story_day | + | 210 | 72% | 0.135 | 83 | 100% |
| `missed_dose@2d->post_meal_peak:lunch` | built_by_story_day | + | 210 | 63% | 0.03 | 11 | 100% |
| `strained_period@1d->post_meal_peak:breakfast` | built_by_story_day | + | 0 | never tested | | | |
| `strained_period@1d->post_meal_peak:lunch` | built_by_story_day | + | 192 | 100% | 0.855 | 178 | 100% |
| `steps_total@1d->post_meal_peak:breakfast` | built_by_story_day | + | 278 | 100% | 0.157 | 146 | 100% |
| `steps_total@1d->post_meal_peak:lunch` | built_by_story_day | + | 279 | 100% | 0.168 | 167 | 100% |
| `symptom_entry@3d->post_meal_peak:breakfast` | built_by_story_day | - | 219 | 58% | -0.017 | 0 |  |
| `symptom_entry@3d->post_meal_peak:lunch` | built_by_story_day | - | 221 | 56% | -0.004 | 0 |  |
| `missed_dose@2d->post_meal_peak:dinner` | built_by_story_day | + | 210 | 100% | 0.235 | 85 | 100% |
| `strained_period@1d->post_meal_peak:dinner` | built_by_story_day | + | 247 | 7% | -0.116 | 0 |  |
| `steps_total@1d->post_meal_peak:dinner` | built_by_story_day | + | 280 | 19% | -0.124 | 0 |  |
| `symptom_entry@3d->post_meal_peak:dinner` | built_by_story_day | - | 251 | 100% | -0.615 | 0 |  |

The `symptom_entry -> post-meal peak` rows are negative only for dinner (mean -0.62, the `contrary` flag); breakfast (-0.02) and lunch (-0.00) are indistinguishable from zero (sign right on 58% and 56% of days). The manifest's claim that illness days draw smaller meal rises is visible for dinner only.

## 6. Item 5: story-day control

**Story days: how the list was built.** The glucose condition label of each day is not in any file the engine can read (the `context` column of the glucose stream is empty), so I built the list from three sources, as the manifest defines:

1. *mood override*: a day with at least one mood block other than `calm_stable` (57 days);
2. *diary*: a day with a diary entry of category `life_event`, `symptom`, `healthcare_interaction`, `travel` or `environment` (95 days; 129 diary entries in all);
3. *glucose condition other than normal*: the label is not available, so I reconstructed it from the monthly generation logs (`final/Generation_Logs_Yearly_Oct2025_Sep2026.md`): every bullet of "Key diary-driven decisions" starts with a date or date range; a bullet counts as a non-normal condition if its text names a condition (illness, stress, festive, fasting, wedding, travel, crisis, anxiety, lapse, recovery, Holi, Diwali, monsoon, and so on) and is not a plain normal/stable/reflection bullet. 71 bullets were used and 17 were left out. This gives 262 days. The keyword rule is my judgement and it is broad.

Two variants are used: **A** = mood override or diary (103 days, 29% of the 352) and **B** = A plus the log reconstruction (**268 days, 76%**, leaving 84 days with nothing special; 80 of them inside the history of 2026-09-17). B is the manifest's definition as closely as the data allow; A needs no judgement. B removes so much that most relationships cannot be tested afterwards, so each variant has a matched control: **RA / RB** remove the same *number* of randomly chosen dates (seeded) from the same history and run the same test. If a relationship survives random removal but not story-day removal, the story days carry the effect.

Procedure: for each `not_built` key that is `supported` on 30 or more days (12 keys), on each of its supported days I took the engine's history table as of that day, dropped the rows whose outcome date is a story day, and repeated the test with the engine's own statistic, permutation (2,000 shifts, same seed rule) and minimums. A day *survives* if the test is still possible and the effect is at least 0.10 with an unadjusted p of at most 0.10 (the `suggestive` criterion; the Benjamini-Hochberg family cannot be rebuilt). A key *survives* if that holds on at least half of its supported days. Detrended outcomes are used as they were (the baselines were computed before the removal).

| key | supported days | A survive | A untestable | B survive | B untestable | RA survive | RB survive | median effect before | after A | after B |
|---|---|---|---|---|---|---|---|---|---|---|
| `hydration_total@prev_day->hr_day_mean` | 31 | 31 (100%) | 0 | 0 (0%) | 0 | 84% | 32% | 0.118 | 0.151 | 0.101 |
| `hydration_total@prev_day->resting_hr_day` | 121 | 121 (100%) | 0 | 2 (2%) | 50 | 91% | 36% | 0.167 | 0.159 | 0.107 |
| `late_meal@same_day->post_meal_peak:lunch` | 51 | 46 (90%) | 0 | 0 (0%) | 50 | 55% | 0% | 0.321 | 0.322 | -0.01 |
| `late_prior_dinner@prev_evening->non_meal_mean` | 72 | 0 (0%) | 41 | 0 (0%) | 49 | 42% | 15% | 0.396 | 0.008 | 0.239 |
| `late_prior_dinner@prev_evening->sleep_hours_night` | 242 | 0 (0%) | 55 | 0 (0%) | 170 | 69% | 10% | 0.336 | 0.026 | -0.441 |
| `missed_dose@2d->systolic_reading` | 51 | 0 (0%) | 51 | 0 (0%) | 51 | 0% | 0% | 0.543 | None | None |
| `prior_day_glucose_mean@prev_day->fluid_intake_day` | 258 | 52 (20%) | 24 | 0 (0%) | 183 | 85% | 19% | 0.196 | 0.092 | -0.038 |
| `sleep_hours@prev_night->non_meal_mean` | 267 | 241 (90%) | 26 | 0 (0%) | 187 | 90% | 27% | 0.293 | 0.275 | -0.115 |
| `sleep_hours@prev_night->post_meal_peak:breakfast` | 262 | 241 (92%) | 21 | 0 (0%) | 183 | 92% | 26% | 0.285 | 0.261 | -0.106 |
| `sleep_hours@prev_night->post_meal_peak:lunch` | 261 | 233 (89%) | 28 | 0 (0%) | 182 | 89% | 27% | 0.306 | 0.255 | -0.091 |
| `sleep_hours@prev_night->systolic_reading` | 159 | 72 (45%) | 87 | 0 (0%) | 159 | 35% | 0% | 0.248 | 0.276 | None |
| `strained_period@prev_day->resting_hr_day` | 208 | 115 (55%) | 93 | 0 (0%) | 208 | 84% | 0% | 0.97 | 0.82 | None |

**Result.** Of the 12 `not_built` keys with 30 or more supported days, **7 survive variant A** (removal of mood and diary days only) and **0 survive variant B** (the manifest's definition with my log reconstruction). Under B none survives, and for the sleep rows B is well below the random control (0% against 25% to 28%, RB), so the story days do carry that effect; for the hydration rows 0% and 2% against 32% to 36%; for prior-day glucose 0% against 19%. Several keys cannot be tested at all under B (50 to 208 of their supported days), and for them RB is low too, so for those the control is silent rather than negative: `late_meal` lunch, `missed_dose -> systolic` and `strained previous day -> resting heart rate` (whose exposure is itself defined by the mood override that B removes). Read B as "the effect does not survive when 76% of the days are removed, and in the 80 plainly ordinary days the sleep and prior-glucose effects have the opposite sign", not as a precise estimate.

Caveat on the control: `strained_period`, `symptom_entry` and similar exposures are defined by the same overrides that define story days, so removing story days removes their exposed days by construction; the control only tests exposures that are not part of the definition (sleep, hydration, late meals, prior-day glucose, missed dose, steps).

**Story days used (B), by date range:**

```
2025-10-01..10-03, 2025-10-06, 2025-10-08, 2025-10-10, 2025-10-13..10-16, 2025-10-18..10-21, 2025-10-25, 2025-10-27..11-12, 2025-11-14, 2025-11-16..11-26, 2025-12-01..12-17, 2025-12-19..12-20, 2025-12-24..12-25, 2025-12-28, 2025-12-31, 2026-01-06..01-14, 2026-01-17..01-18, 2026-01-22..01-31, 2026-02-04..03-05, 2026-03-09..03-23, 2026-03-26, 2026-03-31, 2026-04-06..05-16, 2026-05-25..05-29, 2026-06-01..06-27, 2026-07-01..07-13, 2026-07-29, 2026-07-31..08-28, 2026-09-01..09-17
```

**Of which A (mood override or diary), by date range:**

```
2025-10-01..10-02, 2025-10-06, 2025-10-10, 2025-10-13..10-16, 2025-10-18..10-20, 2025-10-25, 2025-10-29, 2025-10-31, 2025-11-04..11-05, 2025-11-11, 2025-11-14, 2025-11-16..11-21, 2025-11-24, 2025-12-13, 2025-12-19, 2025-12-24..12-25, 2025-12-31, 2026-01-06..01-08, 2026-01-12, 2026-01-14, 2026-01-17, 2026-01-22, 2026-01-25..01-26, 2026-02-04, 2026-02-07..02-08, 2026-02-12..02-16, 2026-03-02..03-05, 2026-03-09, 2026-03-11..03-13, 2026-03-17..03-18, 2026-03-20, 2026-03-26, 2026-03-31, 2026-04-06..04-08, 2026-04-11, 2026-04-14, 2026-04-18, 2026-04-20, 2026-05-01, 2026-05-06, 2026-05-11, 2026-05-13..05-16, 2026-05-25, 2026-06-06, 2026-06-08..06-10, 2026-06-16..06-17, 2026-06-19, 2026-06-25, 2026-07-08..07-11, 2026-07-13, 2026-07-29, 2026-07-31, 2026-08-15, 2026-08-24, 2026-08-27..08-28, 2026-09-01, 2026-09-03, 2026-09-07, 2026-09-10..09-12, 2026-09-14, 2026-09-16..09-17
```

**Generation-log bullets used for the glucose-condition days:**

- October 2025: Oct 1-2  (Navami/Dussehra): high activity, festive meal flags applied per Section 1/4 of translation_rules.m
- October 2025: Oct 3, 6, 8  (office stress days): sedentary classification, steps 1,400-1,500/day, glucose baseline 130-140
- October 2025: Oct 10  (Karva Chauth): fasting day rules applied — extended low-normal glucose plateau through the day (~2
- October 2025: Oct 14-16  (illness): sick-day step rule applied (0-30/hr), elevated but blunted glucose response, poor-to-fai
- October 2025: Oct 18-21  (Diwali cluster): festive meal + high activity rules stacked, step counts 6,600-7,000/day, glucose 
- October 2025: Oct 27-31  (quarter-close): sedentary_stress classification, BP/HR trending toward upper range, adherence dipp
- November 2025: Nov 1-2 : recovery/rest classification after October's intensity, light-to-moderate activity, good sleep
- November 2025: Nov 3-11  (quarter-close): sedentary_stress escalating to sedentary_stress_peak on deadline days (10-11), poo
- November 2025: Nov 12 : recovery classification (the "crash day" after deadline), good sleep, light activity
- November 2025: Nov 14  (Children's Day): moderate activity (standing/walking at school), festive_mild glucose condition, g
- November 2025: Nov 17 : pre_crisis_anxious condition — elevated baseline glucose/BP begins BEFORE the hospitalization itse
- November 2025: Nov 18-20  (INFLECTION POINT + LAG CORRELATION): activity drops to the month's lowest (664-907 steps), sleep b
- November 2025: Nov 21-23 : crisis_easing/recovery_deep — gradual tapering, not instant snap-back, sleep improving to 8.0hrs b
- November 2025: Nov 24-26 : recovery classification, still elevated relative to pre-crisis baseline
- December 2025: Dec 1-2 : recovery_early classification — glucose still elevated (avg 137-138) carrying forward from Novembe
- December 2025: Dec 3-14 : stabilizing/normal classification — gradual settling, adherence recovering from crisis-window lows
- December 2025: Dec 7, 28 : father visits logged as positive/social context events, distinct in tone from November's clinical 
- December 2025: Dec 15-17 : mild_stress classification (year-end pressure) — deliberately less severe than October/November pe
- December 2025: Dec 20, 24, 25 : festive_high classification — Christmas cluster shows genuinely highest step counts of the month (
- December 2025: Dec 31 : festive_mild, NYE — later bedtime reflected in sleep data (5.5hrs vs typical 6.6-7.5), stayed up h
- January 2026: Jan 6-8  (mild illness): sore throat -> confirmed cold -> lingering congestion, step counts drop to 243-255 
- January 2026: Jan 9-11 : recovery to normal, good sleep return
- January 2026: Jan 12-14  (Chennai travel): travel_indulgent condition — richer client-dinner food + wine explicitly generate
- January 2026: Jan 14 : Makar Sankranti observed only briefly while traveling — logged as context event distinct from a fu
- January 2026: Jan 17-18  (allergy flare): new soap/detergent reaction, resolving by Jan 18 — first allergy data point in the
- January 2026: Jan 22-25  (daughter's exam stress): logged as secondhand household tension — deliberately NOT applied as a st
- January 2026: Jan 26-31 : Republic Day calm, then a moderate (not severe) month-end work push, sleep dipping only mildly (5.
- February 2026: Feb 4-12  (wedding build-up): mild distraction/excitement, one high-activity shopping day (Feb 7: 6,174 steps
- February 2026: Feb 12 : half-day + evening hands-on prep, high activity (6,790 steps)
- February 2026: Feb 13-15  (WEDDING PEAK — the month's centerpiece): highest activity of the ENTIRE dataset so far — Feb 13 hi
- February 2026: Feb 16  (crash/recovery day): steps collapse to 360 (sharpest single-day activity drop in the dataset), glu
- February 2026: Feb 17-20 : gradual recovery, not instant
- February 2026: Feb 21-28 : stable close, mild month-end work pressure (26-27), notably less severe than October/November/Marc
- March 2026: Mar 1-2 : normal baseline, mild pre-emptive anxiety noted (context only, no strong biomarker effect yet)
- March 2026: Mar 3-4  (Holi): festive_high_activity classification on Mar 4 — 8,092 steps (second-highest single day in t
- March 2026: Mar 5 : recovery_mild, sore from Holi's activity
- March 2026: Mar 9-18  (AUDIT STRESS — the month's centerpiece, DELIBERATE ANXIETY-SPECIFIC MECHANISM): steps bottom out a
- March 2026: Mar 13 : the abandoned-walk-attempt explicitly modeled — a partial step spike (80-150, vs a full walk's 300
- March 2026: Mar 17  (peak stress): highest glucose average of the anxiety window (144.2) but with a LOWER max (182.1) t
- March 2026: Mar 18-23 : gradual recovery, sleep quality genuinely improving night by night (poor -> fair -> good), appetit
- March 2026: Mar 26  (Gudi Padwa): small, low-key festive bump, moderate_active classification
- March 2026: Mar 31  (fiscal year-end): "busy but not chaotic" — moderate_active, not sedentary_stress, reflecting genui
- April 2026: Apr 6-7  (HEALTH SCARE - FEAR-RESPONSE MECHANISM, distinct from all prior disruption types): steps drop to 5
- April 2026: Apr 6  18:30: clinic-sourced HR reading (98 bpm) logged directly from the walk-in consultation, with conte
- April 2026: Apr 8  (wake-up moment): motivated_transition classification, first deliberate evening walk logged as a ge
- April 2026: Apr 9-30  (SUSTAINED POSITIVE TREND - first genuine "up" period in the entire 12-month dataset): post-scare a
- April 2026: Apr 14  (diabetologist visit): logged as a proactive, voluntary healthcare_interaction - structurally disti
- April 2026: Apr 15-30  (THERAPEUTIC RESPONSE CURVE): glucose shows genuine gradual decline - daily averages drift from ~12
- May 2026: May 1-10  (habit continuation with heat effect): activity stays elevated, but pre-monsoon heat genuinely redu
- May 2026: May 11-15  (MINOR LAPSE - deliberately the SMALLEST negative episode in the dataset): 3 consecutive missed wal
- May 2026: May 14  (deadline day): the single worst day of the lapse, still capped at moderate severity
- May 2026: May 16  (DELIBERATE RESTART): explicitly modeled as a conscious behavioral choice (context event), not a pa
- May 2026: May 25-29  (RESILIENT STRETCH): the best sustained glucose average (114.3) and highest activity baseline of th
- June 2026: Jun 1-9 : motivated_stable baseline continuing from May's resilient stretch
- June 2026: Jun 9 : walk cut short mid-session by first proper monsoon shower
- June 2026: Jun 10-27  (MONSOON ADAPTATION, not collapse): monsoon_indoor days average 1,317 steps, meaningfully higher th
- June 2026: Jun 16-18  (SECOND SEASONAL ILLNESS): mirrors January's illness mechanism (230-484 steps), monsoon-triggered r
- June 2026: Jun 22-24 : full recovery, motivated_stable resumes
- June 2026: Jun 25-27 : mid-year review mild stress, deliberately less intense than prior stress peaks
- July 2026: Jul 1-7 : motivated_stable baseline, monsoon well-adapted by now
- July 2026: Jul 8-13  (PARENTING WORRY ARC - deliberately the MILDEST stress signature in the dataset): a caregiving/rela
- July 2026: Jul 8-9 : difficult conversation, tense dinner, poor sleep (5.2-5.5 hrs) - disruption shows up primarily in 
- July 2026: Jul 11  (cafe walk with daughter): genuinely the LOWEST glucose day of the worry window (114.7) - deliberat
- August 2026: Aug 1-26  (SUSTAINED STABLE BASELINE - deliberately the calmest month in the dataset): no crisis, no illness,
- August 2026: Aug 27-28  (Raksha Bandhan): the ONLY deviation in the whole month - small, brief, joyful, not a meaningful di
- September 2026 (FINAL MONTH - closes at reference date Sep 17): Sep 1-6 : motivated_stable/festive_mild baseline, Janmashtami observed calmly (Sep 3-4)
- September 2026 (FINAL MONTH - closes at reference date Sep 17): Sep 7-11  (QUARTER-CLOSE RESUMES): steps drop to 614-788/day (3+ consecutive missed walks), glucose baseline 
- September 2026 (FINAL MONTH - closes at reference date Sep 17): Sep 12-13  (FESTIVAL PREP): activity SPIKES to 4,982-5,197 steps/day - but this is hosting/ prep activity (coo
- September 2026 (FINAL MONTH - closes at reference date Sep 17): Sep 14  (Ganesh Chaturthi, festival begins): 6,381 steps, the month's activity peak, but sleep crashes to 4
- September 2026 (FINAL MONTH - closes at reference date Sep 17): Sep 15-16  (combined work+festival pressure): activity moderates (2,126-4,995) as office hours resume alongsid
- September 2026 (FINAL MONTH - closes at reference date Sep 17): Sep 17  (REFERENCE DATE - the culmination): sleep bottoms at 3.8 hrs (worst single night in the entire 12-m

**Bullets left out (treated as normal or no effect):**

- November 2025: Nov 16: first mention of father's condition — no direct biomarker effect on Meera yet, log
- November 2025: Nov 27-30: normal/light classification, evening walk resumes Nov 27, closing the month cal
- January 2026: Jan 1-5: normal/moderate_active classification — genuine calm baseline after December's st
- February 2026: Feb 1-6: normal baseline, steady office routine
- April 2026: Apr 1-5: normal baseline, calm post-fiscal-year-end lull
- May 2026: May 17-24: steady return to stable baseline
- May 2026: May 31: full-month reflection logged as "realistic pride rather than perfection" - matchin
- June 2026: Jun 30: half-year reflection logged as context event
- July 2026: Jul 10 (teacher meeting): purposeful movement from the meeting itself
- July 2026: Jul 13: cautiously positive teacher update
- July 2026: Jul 14-18: gradual stabilization, deliberate relationship-repair
- July 2026: Jul 19-28: normal life resumes
- July 2026: Jul 29 (Guru Purnima): small, calm family observance
- July 2026: Jul 31: month-end reflection, genuine improvement by month's end
- August 2026: Aug 15 (Independence Day): mild positive social day, no disruption
- August 2026: Aug 29: pleasantly tired post-celebration day, quick return to baseline
- August 2026: Aug 31: month-end reflection explicitly naming the month as "genuinely calm, stable"

## 7. Item 6: the shape check against section 6

| hand-off | manifest reading | engine target | previous / next | isolated | rebound | steep drop | engine label | manifest expects |
|---|---|---|---|---|---|---|---|---|
| 2025-11-08T11:00 | 65.0 | 65.0 | 125.1 / 113.1 | True | True | True | **supported** | supported |
| 2026-01-20T16:00 | 65.0 | 65.0 | 136.3 / 114.1 | True | False | True | **not_supported** | supported |
| 2026-03-22T11:00 | 65.0 | 65.0 | 130.3 / 125.2 | True | True | True | **supported** | supported |
| 2026-08-19T15:00 | 65.0 | 65.0 | 136.0 / 114.4 | True | False | True | **not_supported** | supported |
| 2026-08-22T10:30 | 76.3 | 76.3 | 132.1 / 119.6 | True | True | True | **supported** | supported |

Three of the five are `supported`; two are `not_supported`: for 2026-01-20 and 2026-08-19 the reading after the dip is 22.2 and 21.6 mg/dL below the reading before it, against the placeholder rebound tolerance of 20 (a miss of 2.2 and 1.6 mg/dL). All five targets are in the cleaned series (none was removed by the cleaning rule) and all five are steep, isolated drops. By the manifest's own expectation (all five artifacts) the check has recall 3 of 5 with the placeholder tolerance; with a tolerance of 25 mg/dL it would be 5 of 5. I did not change it.

## 8. Item 7: placebo fire rate by month

| month | fired | tested | rate |
|---|---|---|---|
| 2025-10 | 0 | 0 | 0.0% |
| 2025-11 | 0 | 0 | 0.0% |
| 2025-12 | 55 | 520 | 10.6% |
| 2026-01 | 132 | 989 | 13.3% |
| 2026-02 | 75 | 1054 | 7.1% |
| 2026-03 | 179 | 1293 | 13.8% |
| 2026-04 | 103 | 1286 | 8.0% |
| 2026-05 | 68 | 1333 | 5.1% |
| 2026-06 | 61 | 1345 | 4.5% |
| 2026-07 | 136 | 1460 | 9.3% |
| 2026-08 | 125 | 1488 | 8.4% |
| 2026-09 | 59 | 816 | 7.2% |
| **year** | **993** | **11,584** | **8.57%** |

The tested count is zero in October and November (history minimum). The rate sits under the 10% a placebo p of at most 0.10 would give, as the effect floor must also be met.

## 9. Surprises

1. **The engine misses most of the one real hourly formula because of its own ordering rule.** Heart rate follows the *same* hour's steps (within-clock-hour rho 0.41); the library, correctly by spec 3.1 rule 8, uses the previous hour (rho 0.12). Result: effect 0.086 to 0.124, `supported` on only 57% of tested days, and `not_supported` on the last day despite p = 0.0015.
2. **All of the false finds are concentrated in 14 keys, and sleep alone is 48%.** The `not_built` false-find rate of 39% is really one coupling (sleep, glucose condition and the story) counted four times, plus a few chains.
3. **The story-day definition covers 76% of the year** once the log is included. Whatever is "story" is most days, so a control by removal has little left to work with, and the manifest's own distinction between "formula" and "story" days is thin: the same days that carry story are the days that carry the formulas.
4. **The largest effects are on the exposures defined by the story itself** (`strained_period` 0.65 to 1.6, `symptom_entry@same_day->fluid` 1.04, `high_steps` 0.51): the engine finds what the generator wrote, and the same-day pairs are all `same_day_unverified`.
5. **The dinner kind behaves differently from breakfast and lunch** (opposite sign for stress and steps; the only kind where illness lowers the peak). The manifest says light dinners always draw 10 to 22 mg/dL rises, which may be why it does not follow the label-driven pattern of the other two kinds; I did not check this against the generator.
6. **`strained_period` on the previous day predicts today's resting heart rate** with the biggest `not_built` effect (0.99), also on calm days.
7. **Unverified heart-rate rows are the strongest relationships in the dataset** (sleep to resting rate: supported on 90% of tested days).
8. **Seven of the 12 `not_built` keys with a supported run survive removal of mood and diary days only** (the three sleep rows with glucose, both hydration rows, the late lunch, and the previous-day strain row), so for those the link does not come from the mood or diary days; the evidence points to the log-listed condition days.

## 10. What I did not do

No threshold, library row or code was changed; the manifest was not edited; no finding was drawn about whether the engine works on a real person (manifest section 8). The story-day list item 3 is my reconstruction and should be checked by the owner before the numbers under variant B are used.

