# Ground-truth manifest and scoring plan for the first patient (Meera)

## 0. Purpose and honesty note

The Evidence Engine runs on **synthetic** data. It will find whatever the generator put in, so a good-looking result proves little. This manifest says **what was actually built into the data**, so the engine can be scored: how many of its `supported` relationships are real, how many only reflect shared story days, and how many are not built in at all.

**How it was made.** I read the generation scripts that were on disk (monthly glucose, steps and sleep scripts, and the hydration, screen time, sedentary and mood scripts). Items marked **verified** quote those scripts. Items marked **recalled** come from the project record: the continuous heart-rate generator is not on disk, so its description is from my notes and has not been re-checked. Items marked **unverified** need a check against the original generator before they are used for scoring.

This is a reading of script structure, not a full audit of every number.

## 1. How the data was made, in four lines

1. **Glucose** is a day-by-day story. Each day carries a **condition label** (for example `normal`, `illness`, `mild_stress`, `festive`, `crisis_day2_worst`, `minor_lapse`). The label sets a baseline range and the size of each meal's rise. Noise of about plus or minus 6 mg/dL is added. *(verified)*
2. **Steps, sleep, missed doses, mood, blood pressure, resting heart rate and diary** were written by hand, day by day, from the same story. They are not computed from each other. *(verified for steps, sleep, mood; the others by the same script pattern)*
3. **A few streams are formulas of others** (section 3).
4. **Everything correlates with everything on story days**, because one day's story sets all of them at once. That is realistic, but it is not a mechanism.

## 2. Glucose conditions (verified)

On each day, post-meal rises are drawn from a range set by the day's label; light dinners are always 10-22 mg/dL.

| Label (month) | Meal rise range (mg/dL) | Other effect |
|---|---|---|
| ordinary / `normal` | 38-54 | baseline 114-126 |
| `fear_response`, `fear_response_lingering` (Apr) | 30-42 | baseline 118-134 |
| `motivated_improving` (Apr) | 32-46 | baseline falls by up to 6 over the days |
| `motivated_high_activity` (Apr) | ordinary | daytime (09-20h) glucose lowered by 4-10 |
| `illness` (Jan, Jun, Oct) | 30-45 | |
| `mild_stress`, `monsoon_indoor_stress` (Dec, Jan, Feb, Jun) | 40-56 | |
| `travel_indulgent` (Jan) | 60-85 | richer food, alcohol |
| `minor_lapse`, `minor_lapse_deadline` (May) | 42-58 | the lapse days |
| `festive_mild` (Aug) | 45-62 | |
| `combined_pressure` (Sep) | 35-48 | |
| `festival_hosting`, `festival_peak_sleepdebt` (Sep) | | daytime (10-22h) effect |
| `wedding_peak`, `wedding_prep` (Feb) | | daytime (10-23h) effect |
| `anxious_stress`, `anxious_peak`, `festive_high_activity` (Mar) | see script | `festive_high_activity` has a daytime (10-22h) effect |
| `crisis_day2_worst`, `crisis_day3_worst`, `sedentary_stress`, `pre_crisis_anxious` (Nov) | see script | |
| `fasting` (Oct) | | effect before 20h |

Glucose does **not** depend on sleep, mood values, missed doses, diary text, hydration, screen time or blood pressure. It depends on those only through the day's label.

## 3. Direct formulas between streams (verified unless marked)

| Link | Form | Source |
|---|---|---|
| Daily steps to sedentary minutes | inverse linear: fewest steps give 780 minutes, most give 380, plus or minus 20 noise, clipped 350-800 | `gen_phaseD_sedentary_v3.py` |
| Sedentary minutes to screen time | ordinary days: `4.5 + (sedentary - 500) / 200` hours, plus or minus 0.8, clipped 2.5-8.0. Deadline-stress days: 8.5-10.5. Rest or illness days: 3.5-5.5 | `gen_phaseD_screentime.py` |
| Daily steps to hydration | ordinary days: `1800 + min(steps / 10, 500)` mL plus or minus 150. Fasting days 1200-1500. Illness days 1400-1800. High-activity or heat days 2300-2800 | `gen_phaseD_hydration.py` |
| Hourly steps to continuous heart rate | an activity boost on top of the day's resting rate | recalled |
| Mood tag to continuous heart rate | an offset on anxious or distressed periods | recalled |
| Sleep, context-event severity and meals to continuous heart rate | a night dip, an offset on severe event days, a meal bump | recalled |
| Diary text to location type | keyword classifier | `gen_phaseE_location.py` |

## 4. What was not built in

- Glucose from sleep, mood, adherence, symptoms, hydration, screen time or blood pressure (except through the day's label).
- Sleep, mood, adherence, blood pressure and resting heart rate from each other.
- Meal timing to the size of a meal's rise (the rise depends on the label and on light versus ordinary meals, not on the clock).
- Alcohol, weather and travel effects (a handful of days only).

## 5. The 49 runnable relationships, classified

Classes: **built_formula** (a formula in section 3), **built_by_story_day** (both streams are set by the same story-day label, so a link is expected but is not a mechanism), **not_built** (nothing ties them), **unverified** (needs a check against the original heart-rate generator). Counts: built_formula 2, built_by_story_day 19, unverified 4, not_built 24.

| Relationship key | Class | Expected sign (oriented) | Why | Ordering |
|---|---|---|---|---|
| `missed_dose@2d->post_meal_peak:{meal_kind}` | built_by_story_day | + (weak) | Only the May `minor_lapse` days (meal rises 42-58) tie a lapse to glucose; elsewhere adherence is hand-set independently. | same_day_unverified |
| `sleep_hours@prev_night->post_meal_peak:{meal_kind}` | not_built | - | Glucose does not depend on sleep, except on the September `festival_peak_sleepdebt` days. | ordered |
| `strained_period@1d->post_meal_peak:{meal_kind}` | built_by_story_day | + | Stress and anxiety condition days draw larger meal rises (42-56 vs 38-54) and a higher baseline. | ordered |
| `steps_total@1d->post_meal_peak:{meal_kind}` | built_by_story_day | + | High-activity condition days lower daytime glucose by 4-10 mg/dL; steps are high on the same days. | same_day_unverified |
| `symptom_entry@3d->post_meal_peak:{meal_kind}` | built_by_story_day | - for peaks | Illness days draw meal rises from a lower range (30-45 vs 38-54 mg/dL on ordinary days), so the expected sign against post-meal peaks is negative; the engine's `contrary` flag agrees. | ordered |
| `late_meal@same_day->post_meal_peak:{meal_kind}` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `alcohol_entry@1d->post_meal_peak:{meal_kind}` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `missed_dose@2d->non_meal_mean` | built_by_story_day | + (weak) | Only the May `minor_lapse` days (meal rises 42-58) tie a lapse to glucose; elsewhere adherence is hand-set independently. | same_day_unverified |
| `symptom_entry@3d->non_meal_mean` | built_by_story_day | - for peaks | Illness days draw meal rises from a lower range (30-45 vs 38-54 mg/dL on ordinary days), so the expected sign against post-meal peaks is negative; the engine's `contrary` flag agrees. | same_day_unverified |
| `strained_period@1d->non_meal_mean` | built_by_story_day | + | Stress and anxiety condition days draw larger meal rises (42-56 vs 38-54) and a higher baseline. | same_day_unverified |
| `sleep_hours@prev_night->non_meal_mean` | not_built | - | Glucose does not depend on sleep, except on the September `festival_peak_sleepdebt` days. | same_day_unverified |
| `steps_total@prev_day->non_meal_mean` | built_by_story_day | + | High-activity condition days lower daytime glucose by 4-10 mg/dL; steps are high on the same days. | ordered |
| `late_prior_dinner@prev_evening->non_meal_mean` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `high_steps_day@1d->day_min_glucose` | built_by_story_day | + | High-activity condition days lower daytime glucose by 4-10 mg/dL; steps are high on the same days. | same_day_unverified |
| `alcohol_entry@720m->day_min_glucose` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `symptom_entry@1d->day_min_glucose` | built_by_story_day | - for peaks | Illness days draw meal rises from a lower range (30-45 vs 38-54 mg/dL on ordinary days), so the expected sign against post-meal peaks is negative; the engine's `contrary` flag agrees. | same_day_unverified |
| `steps_window_hourly@60m->hr_hour_mean` | built_formula | + | Heart rate was generated from hourly steps (activity boost). Recalled from the project record; the generator script is not on disk. | ordered |
| `strained_period@same_day->hr_day_mean` | built_formula | + | Mood tag adds a heart-rate offset (anxiety). Recalled; script not on disk. | same_day_unverified |
| `symptom_entry@3d->hr_day_mean` | unverified | + | Heart rate also depended on sleep and on context-event severity (recalled); the exact form is not verified. | same_day_unverified |
| `hydration_total@prev_day->hr_day_mean` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `sleep_hours@prev_night->hr_day_mean` | unverified | + | Heart rate also depended on sleep and on context-event severity (recalled); the exact form is not verified. | same_day_unverified |
| `alcohol_entry@720m->hr_day_mean` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `sleep_hours@prev_night->resting_hr_day` | unverified | + | Heart rate also depended on sleep and on context-event severity (recalled); the exact form is not verified. | same_day_unverified |
| `symptom_entry@3d->resting_hr_day` | unverified | + | Heart rate also depended on sleep and on context-event severity (recalled); the exact form is not verified. | same_day_unverified |
| `strained_period@prev_day->resting_hr_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `hydration_total@prev_day->resting_hr_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `alcohol_entry@prev_evening->resting_hr_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `strained_period@same_day->sleep_hours_night` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | ordered |
| `late_prior_dinner@prev_evening->sleep_hours_night` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `alcohol_entry@prev_evening->sleep_hours_night` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `screen_hours@prev_evening->sleep_hours_night` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `symptom_entry@same_day->sleep_hours_night` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | ordered |
| `non_home_day@same_day->sleep_hours_night` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | ordered |
| `non_home_day@same_day->missed_doses_day` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | same_day_unverified |
| `strained_period@same_day->missed_doses_day` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | same_day_unverified |
| `symptom_entry@same_day->missed_doses_day` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | same_day_unverified |
| `missed_dose@7d->missed_doses_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | excludes_outcome_day |
| `sleep_hours@prev_night->missed_doses_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | same_day_unverified |
| `missed_dose@2d->systolic_reading` | not_built | - | No generator link and no shared story-day driver found in the scripts. | same_day_unverified |
| `clinic_reading@at_open->systolic_reading` | not_built | - | No generator link and no shared story-day driver found in the scripts. | same_day_unverified |
| `strained_period@same_day->systolic_reading` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | no_ordered_exposure |
| `sleep_hours@prev_night->systolic_reading` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `alcohol_entry@720m->systolic_reading` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `symptom_entry@same_day->systolic_reading` | built_by_story_day | + | These streams are hand-set per day from the story; stress, illness and travel days move them together. | ordered |
| `symptom_entry@same_day->fluid_intake_day` | built_by_story_day | + | Hydration script lists illness days with lower intake (1400-1800 mL vs about 2000+). | same_day_unverified |
| `non_home_day@same_day->fluid_intake_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | same_day_unverified |
| `prior_day_glucose_mean@prev_day->fluid_intake_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |
| `environment_entry@same_day->fluid_intake_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | same_day_unverified |
| `alcohol_entry@prev_evening->fluid_intake_day` | not_built | - | No generator link and no shared story-day driver found in the scripts. | ordered |

## 6. Known artifacts in the glucose stream (for the shape check)

Five isolated readings that are not real glucose events: four are exactly 65.0 mg/dL (2025-11-08 11:00, 2026-01-20 16:00, 2026-03-22 11:00, 2026-08-19 15:00), left by a floor applied to impossible low values; the fifth (2026-08-22 10:30, 76.3) is a hypoglycemia reading that was designed at 66.5 and later altered. Expected result of the shape check: all five `supported` ("consistent with an artifact" or an isolated dip). The engine's placeholder tolerance gave `supported` for three and `not_supported` for two (by under 2 mg/dL).

Also: two 'implausible' spikes (2026-04-23 590, 2025-12-09 599) are removed by the cleaning rule before any statistic; they are not part of the shape check.

## 7. Scoring plan (for Claude Code, after the manifest is reviewed)

Inputs: `relationship_evidence` for every day, `event_evidence`, and the table in section 5. Outputs: one report.

1. **Class table.** For each class: number of relationships, days tested, and the share of tested days labelled `supported`, `suggestive`, `not_supported`.
2. **Precision.** Of all `supported` relationship-days, the share in `built_formula`, `built_by_story_day`, `unverified` and `not_built`. The `not_built` share is the engine's false-find rate against the manifest.
3. **Recall of the formulas.** For each `built_formula` relationship: the first date it is `supported`, and the share of tested days supported.
4. **Sign check.** For each built relationship with an expected sign, the share of days where the effect has that sign (the `symptom_entry` to post-meal peak relationships should be negative).
5. **Story-day control.** For each `not_built` relationship labelled `supported` on 30 or more days, repeat the daily statistic after removing **story days** (days with a mood override, a diary entry of category life_event, symptom, healthcare, travel or environment, or a glucose condition other than `normal`) and report whether the effect survives. Report the list of story days used.
6. **Shape check.** Report the five artifact readings and their labels against section 6.
7. **Placebo.** Report the fire rate by month (already available).

Do not change any threshold as part of scoring. Report; the owner decides.

## 8. What the scoring can and cannot tell us

- It can tell us whether the engine finds the formulas, how often it labels unbuilt pairs `supported`, and whether story-day coincidence explains those.
- It cannot tell us whether the engine works on a real person. Real data has real mechanisms and real noise. The first real patient is the real test.
- A high `built_by_story_day` share among `supported` relationships is **expected** and is not an error. It is the reason Findings must word these as associations, and why overlap and cluster handling matter.