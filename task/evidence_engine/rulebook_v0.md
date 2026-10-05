# Rulebook Lookup v0: the lookup table

**Status: draft, unreviewed.** Built from published clinical-education sources found in one search pass. It has not been reviewed by a doctor. Every row carries `review_status = unreviewed`. A weight is a **prior** about what to test first; it is never evidence and never appears as a confidence in a Finding.

Companion machine-readable files: `rulebook_v0_rules.csv` (one row per condition) and `rulebook_v0_candidates.csv` (one row per checklist item).

## How to read it

- **Condition** = measure + direction + one context flag. A State Engine hand-off matches exactly one rule.
- **Checklist** = ordered candidates (what to test), each with the data it needs, how far back to look, and what is compared. The packet holds these rules only, never readings.
- **Weight tier** = `primary` (always tested), `secondary`, `tertiary`.
- **Budget** = how many candidates Evidence Engine tests for that rule: all primary, up to the secondary maximum, up to the tertiary maximum, never more than the total. It is static, in this file.
- **Skipped candidates** are recorded, not hidden: no stream for the patient, or `applies_if` not met.

### Ordering and structured columns

- **Order inside a tier:** secondary and tertiary candidates are ordered by evidence level (A before B before C before D), so the budget cuts the weakest-evidenced candidates first. Primary candidates are all tested, so their order is only for reading.
- **Structured columns** in `rulebook_v0_candidates.csv` (`requires_streams`, `lookback_kind`, `lookback_value`, `applies_if_rule`, `check_type`, `data_status_meera_code`) are the machine-readable form. The `*_text` columns are the same content in plain words, for people. If they ever disagree, the structured columns win. The grammar is defined in the Rulebook Lookup spec.

### Evidence levels (my own scale, not GRADE)

- **A**: several authoritative clinical-education sources agree
- **B**: some clinical sources, a review, or a clear mechanism
- **C**: plausible or reasoned; little or no direct sourcing in this pass
- **D**: no clinical evidence; behavioural proxy

### Evidence bar for calling a result supported (placeholders)

- Standard: smaller group >= 10 days and effect size >= 0.4 (placeholder, not a clinical standard)
- Raised bar, used when more than 4 candidates are tested: smaller group >= 15 days and effect size >= 0.5 (placeholder)

## The conditions at a glance

| Rule | Condition | Meera hand-offs / year | Candidates | Budget (primary / secondary max / tertiary max / total) | Status |
|---|---|---|---|---|---|
| `glucose_above_post_meal` | a meal was logged within 180 minutes before the item opened | 40 | 10 | all (1) / 5 / 2 / 8 | active |
| `glucose_above_no_recent_meal` | no meal logged within 180 minutes (between meals, overnight, fasting) | 59 | 9 | all (2) / 3 / 2 / 7 | active |
| `glucose_below` | adverse only: clinical status low, or position far | 5 | 6 | all (2) / 3 / 1 / 6 | active |
| `heart_rate_above` | continuous heart rate, adverse direction | 124 | 9 | all (3) / 3 / 2 / 8 | active |
| `resting_heart_rate_above` | daily resting heart rate | 12 | 7 | all (2) / 3 / 1 / 6 | active |
| `sleep_below` | last night's sleep below her usual | 10 | 7 | all (1) / 3 / 2 / 6 | active |
| `medication_adherence_below` | missed doses worse than her usual | 24 | 6 | all (2) / 3 / 1 / 6 | active |
| `blood_pressure_above` | systolic or diastolic above her usual | 3 | 8 | all (2) / 3 / 2 / 7 | active |
| `hydration_below` | daily fluid intake below her usual | 2 | 5 | all (2) / 2 / 1 / 5 | active |
| `screen_time_above` | daily screen time above her usual | 8 | 2 | 0 / 2 / 0 / 2 | deferred |

A hand-off that matches no rule returns an empty checklist and is logged.

## Rule by rule

### `glucose_above_post_meal`

- **Applies when:** a meal was logged within 180 minutes before the item opened  
- **Measure and direction:** glucose, above  
- **Meera hand-offs in the year:** 40  
- **Status:** active  
- **Budget:** primary all (1), secondary up to 5, tertiary up to 2, at most 8 tested  
- **Why this budget:** 9 candidates exist; all primary plus up to 5 secondary and 2 tertiary keeps the finding readable. Strong data for most streams.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | meal_composition | meal_events; food_content | 240 minutes | this meal's response vs her earlier meals of the same kind -> peak glucose within 150 min of the meal | A | S1;S2;S3;S4 | available | - |
| 2 | secondary | medication_adherence | medication_adherence | 2 days | evenings after a missed dose vs evenings with all doses taken -> post-meal peak | A | S1;S2;S3;S4 | available | patient takes a glucose-lowering medicine |
| 3 | secondary | sleep | sleep_duration | previous night | days after short sleep vs normal sleep -> post-meal peak | A | S2;S3 | available | - |
| 4 | secondary | stress_mood | mood_state; diary_context | 1 day | strained days vs calm days -> post-meal peak | A | S1;S2;S3 | available | - |
| 5 | secondary | activity | step_count | 1 day | low-activity days vs normal days -> post-meal peak | A | S1;S2;S3;S4 | partial (daily steps only) | - |
| 6 | secondary | illness_symptoms | diary_context (symptom) | 3 days | days with a symptom entry vs none -> post-meal peak | A | S1;S3 | available | - |
| 7 | secondary | meal_timing | meal_events | same day | meals at or after her usual latest hour vs earlier meals -> peak glucose | C | none | available | - |
| 8 | tertiary | other_medications | medication list | current | presence of steroids or similar glucose-raising medicines -> mean glucose | A | S1;S3 | none | patient has such a medicine listed |
| 9 | tertiary | cycle_phase | menstrual_cycle | current cycle | phase vs other phases -> mean and peak glucose | B | S19 | verify: not confirmed to be in the store | a cycle stream exists |
| 10 | tertiary | alcohol | diary_context (substance_use) | 1 day | days with an alcohol entry vs none -> post-meal peak | C | none | partial (diary only) | - |

- *meal_composition*: Food and carbohydrate load are the first-listed causes of highs.
- *sleep*: Poor or short sleep is listed as a cause of highs.
- *stress_mood*: Stress hormones raise glucose.
- *illness_symptoms*: Illness or infection is a leading listed cause.
- *meal_timing*: Plausible (evening glucose tolerance is lower) but not sourced in this pass.
- *cycle_phase*: Evidence is mainly type 1 diabetes; effect varies between people.
- *alcohol*: Effect direction on glucose is mixed.

### `glucose_above_no_recent_meal`

- **Applies when:** no meal logged within 180 minutes (between meals, overnight, fasting)  
- **Measure and direction:** glucose, above  
- **Meera hand-offs in the year:** 59  
- **Status:** active  
- **Budget:** primary all (2), secondary up to 3, tertiary up to 2, at most 7 tested  
- **Why this budget:** 9 candidates; medication and illness lead because no meal explains it. Fewer streams are informative without a meal.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | medication_adherence | medication_adherence | 2 days | days with a missed dose vs none -> next overnight/fasting mean glucose | A | S1;S2;S3;S4 | available | patient takes a glucose-lowering medicine |
| 2 | primary | illness_symptoms | diary_context (symptom) | 3 days | days with a symptom entry vs none -> mean glucose in the window | A | S1;S2;S3;S4 | available | - |
| 3 | secondary | stress_mood | mood_state; diary_context | 1 day | strained days vs calm days -> mean glucose in the window | A | S1;S2;S3 | available | - |
| 4 | secondary | sleep | sleep_duration | previous night | days after short sleep vs normal -> mean glucose in the window | A | S2;S3 | available | - |
| 5 | secondary | activity | step_count | previous day | low-activity days vs normal -> mean glucose in the window | A | S1;S2;S3;S4 | partial (daily steps only) | - |
| 6 | secondary | prior_evening_meal | meal_events; food_content | previous evening | heavy or late previous dinner vs usual dinners -> overnight mean glucose | B | S1;S2 | available | - |
| 7 | secondary | dawn_effect | time of day | same morning | early-morning rise on most mornings vs this morning only -> glucose 04:00-09:00 | B | S2 | available (from glucose) | only for items opening between 04:00 and 09:00 |
| 8 | tertiary | other_medications | medication list | current | steroids or similar -> mean glucose | A | S1;S3 | none | patient has such a medicine listed |
| 9 | tertiary | cycle_phase | menstrual_cycle | current cycle | phase vs other phases -> mean glucose | B | S19 | verify: not confirmed to be in the store | a cycle stream exists |

- *medication_adherence*: Skipped doses are a first-listed cause.
- *illness_symptoms*: Illness raises glucose through stress hormones.
- *prior_evening_meal*: Carbohydrate load is a listed cause; carry-over to the next window is reasoned.
- *dawn_effect*: A repeating pattern is not a one-off event.

### `glucose_below`

- **Applies when:** adverse only: clinical status low, or position far  
- **Measure and direction:** glucose, below  
- **Meera hand-offs in the year:** 5  
- **Status:** active  
- **Budget:** primary all (2), secondary up to 3, tertiary up to 1, at most 6 tested  
- **Why this budget:** In a patient on metformin alone a true low is uncommon, so the first check is a sensor artifact. Few candidates; small budget.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | sensor_artifact | glucose stream shape | 60 minutes either side | a sudden steep drop from steady values, short run, rebound on the next reading, no meal or activity before it -> shape of the reading vs its neighbours | B | S7;S8 | available | - |
| 2 | primary | meal_skipped_or_delayed | meal_events | 12 hours | gap since last meal vs her usual gap -> hours since last meal | A | S5;S6 | available | - |
| 3 | secondary | unusual_activity | step_count | 1 day | activity above her usual vs normal -> steps | A | S5;S6 | partial (daily steps only) | - |
| 4 | secondary | alcohol | diary_context (substance_use) | 12 hours | alcohol entry present vs none -> presence | A | S6 | partial (diary only) | - |
| 5 | secondary | hypoglycemic_agent | medication list | current | whether insulin or a sulfonylurea is taken; dose timing vs the low -> medication list and dose times | A | S5;S6 | skipped for this patient | patient takes insulin or a sulfonylurea |
| 6 | tertiary | illness_poor_intake | diary_context (symptom) | 1 day | illness with reduced eating vs none -> presence | C | none | available | - |

- *sensor_artifact*: Compression lows (often overnight) and new-sensor effects can read falsely low. Also check whether the low is an isolated reading.
- *meal_skipped_or_delayed*: Missed or delayed meals are a leading cause in people on glucose-lowering medicine.
- *alcohol*: Alcohol suppresses liver glucose production.
- *hypoglycemic_agent*: Metformin alone does not cause significant hypoglycemia (S5, S6).
- *illness_poor_intake*: Reasoned; not sourced in this pass.

### `heart_rate_above`

- **Applies when:** continuous heart rate, adverse direction  
- **Measure and direction:** heart_rate, above  
- **Meera hand-offs in the year:** 124  
- **Status:** active  
- **Budget:** primary all (3), secondary up to 3, tertiary up to 2, at most 8 tested  
- **Why this budget:** Largest group by count and many plausible causes, so a larger budget; hourly steps are missing for this patient, which limits the activity check.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | activity | step_count (hourly if available) | 60 minutes | exertion in the preceding hour vs rest -> heart rate above her usual | A | S9 | partial (daily steps only; hourly steps not in the store) | - |
| 2 | primary | stress_mood | mood_state; diary_context | same day | strained periods vs calm periods -> heart rate above her usual | A | S9;S10 | available | - |
| 3 | primary | illness_fever | diary_context (symptom) | 3 days | symptom days vs none -> heart rate above her usual | A | S9;S10 | available | - |
| 4 | secondary | hydration | hydration | previous day | low-intake days vs normal -> heart rate above her usual | A | S9 | available | - |
| 5 | secondary | caffeine_stimulants | caffeine intake | 6 hours | caffeine/stimulant vs none -> heart rate above her usual | A | S9;S10 | none (no stream) | - |
| 6 | secondary | sleep | sleep_duration | previous night | days after short sleep vs normal -> heart rate above her usual | B | S10 | available | - |
| 7 | secondary | alcohol | diary_context (substance_use) | 12 hours | alcohol entry vs none -> heart rate above her usual | B | S9 | partial (diary only) | - |
| 8 | tertiary | thyroid_status | lab (TSH); medication | current | thyroid status and levothyroxine dose -> heart rate level | A | S9;S10 | partial (condition known; TSH not in the store) | patient has a thyroid condition or takes thyroid medicine |
| 9 | tertiary | meal_digestive | meal_events | 90 minutes | heart rate after meals vs between meals -> heart rate above her usual | C | none | available | - |

- *activity*: Exertion is the most common physiological cause; without hourly data the test cannot isolate the hour.
- *stress_mood*: Stress and anxiety release hormones that raise heart rate.
- *illness_fever*: Fever and infection raise heart rate.
- *hydration*: Dehydration raises heart rate.
- *caffeine_stimulants*: Skipped for this patient: no stream.
- *meal_digestive*: Reasoned; small effect; not sourced in this pass.

### `resting_heart_rate_above`

- **Applies when:** daily resting heart rate  
- **Measure and direction:** resting_heart_rate, above  
- **Meera hand-offs in the year:** 12  
- **Status:** active  
- **Budget:** primary all (2), secondary up to 3, tertiary up to 1, at most 6 tested  
- **Why this budget:** Daily value, so tests run on days, not readings; sample sizes are small, so the budget is kept modest.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | sleep | sleep_duration | previous night | days after short sleep vs normal -> daily resting heart rate | B | S10 | available | - |
| 2 | primary | illness_fever | diary_context (symptom) | 3 days | symptom days vs none -> daily resting heart rate | A | S9;S10 | available | - |
| 3 | secondary | stress_mood | mood_state; diary_context | previous day | strained days vs calm days -> daily resting heart rate | A | S9;S10 | available | - |
| 4 | secondary | hydration | hydration | previous day | low-intake days vs normal -> daily resting heart rate | A | S9;S18 | available | - |
| 5 | secondary | alcohol | diary_context (substance_use) | previous evening | alcohol entry vs none -> daily resting heart rate | B | S9 | partial (diary only) | - |
| 6 | tertiary | thyroid_status | lab (TSH); medication | current | thyroid status and dose -> resting heart rate level | A | S9;S10 | partial (TSH not in the store) | patient has a thyroid condition or takes thyroid medicine |
| 7 | tertiary | unusual_activity_prior_day | step_count | previous day | very high or very low activity vs usual -> daily resting heart rate | C | none | partial (daily steps only) | - |

- *sleep*: Lack of sleep raises stress hormones and heart rate.
- *unusual_activity_prior_day*: Reasoned; not sourced in this pass.

### `sleep_below`

- **Applies when:** last night's sleep below her usual  
- **Measure and direction:** sleep_duration, below  
- **Meera hand-offs in the year:** 10  
- **Status:** active  
- **Budget:** primary all (1), secondary up to 3, tertiary up to 2, at most 6 tested  
- **Why this budget:** One strong primary cause (stress); several behavioural secondary causes with weaker data.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | stress_mood | mood_state; diary_context | same evening and day | strained days vs calm days -> sleep duration that night | A | S13;S14 | available | - |
| 2 | secondary | meal_timing | meal_events | evening | late dinner vs usual dinner time -> sleep duration that night | A | S13;S14 | available | - |
| 3 | secondary | alcohol_caffeine | diary_context (substance_use); caffeine intake | evening | alcohol or caffeine vs none -> sleep duration that night | A | S13;S14 | partial (alcohol via diary only; no caffeine stream) | - |
| 4 | secondary | screen_time | screen_time | evening | high screen time vs usual -> sleep duration that night | B | S14 | partial (daily total, not evening) | - |
| 5 | secondary | illness_symptoms | diary_context (symptom) | same day | symptom days vs none -> sleep duration that night | C | none | available | - |
| 6 | tertiary | travel_environment | location; diary_context (environment) | same day | travel or unusual location vs usual -> sleep duration that night | B | S13 | partial | - |
| 7 | tertiary | overnight_glucose | glucose stream | overnight | high overnight glucose vs normal -> sleep duration that night | C | S18 | available (from glucose) | - |

- *stress_mood*: Stress is the most commonly cited cause of short-term sleep difficulty.
- *meal_timing*: Eating late is a listed cause.
- *screen_time*: Screen use before bed is a listed habit; a daily total is a weak proxy.
- *illness_symptoms*: Short-term illness disrupts sleep, but this was found only in a low-quality source.
- *travel_environment*: Changing time zones disturbs sleep (S13); weather and noise are reasoned.
- *overnight_glucose*: Uncontrolled diabetes increases urination (S18); the link to short sleep is reasoned.

### `medication_adherence_below`

- **Applies when:** missed doses worse than her usual  
- **Measure and direction:** medication_adherence, below  
- **Meera hand-offs in the year:** 24  
- **Status:** active  
- **Budget:** primary all (2), secondary up to 3, tertiary up to 1, at most 6 tested  
- **Why this budget:** Behavioural; WHO framework gives categories rather than ranked causes, so evidence is general and the budget small.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | routine_disruption | location; diary_context | same day | days with travel, events or an unusual location vs ordinary days -> missed-dose rate | B | S11;S12 | available | - |
| 2 | primary | stress_mood | mood_state; diary_context | same day | strained days vs calm days -> missed-dose rate | A | S11;S12 | available | - |
| 3 | secondary | illness_symptoms | diary_context (symptom) | same day | symptom days vs none -> missed-dose rate | B | S11 | available | - |
| 4 | secondary | recent_adherence_pattern | medication_adherence | 7 days | misses in the prior days vs a clean prior week -> missed-dose rate | B | S11 | available | - |
| 5 | secondary | sleep_prior_night | sleep_duration | previous night | short-sleep days vs normal -> missed-dose rate | C | none | available | - |
| 6 | tertiary | regimen_factors | medication list; dose times | current | which medicine or time of day is missed most -> per-medicine miss rate | A | S11;S12 | available | - |

- *routine_disruption*: Disrupted routine and forgetfulness are patient-related adherence factors.
- *stress_mood*: Psychosocial stress and depression are named in the WHO framework.
- *illness_symptoms*: Condition-related factors (symptoms) are in the WHO framework.
- *recent_adherence_pattern*: Adherence barriers change over time and persist.
- *sleep_prior_night*: Reasoned; not sourced in this pass.
- *regimen_factors*: Therapy-related factors (number of medicines, dose times, side effects).

### `blood_pressure_above`

- **Applies when:** systolic or diastolic above her usual  
- **Measure and direction:** blood_pressure, above  
- **Meera hand-offs in the year:** 3  
- **Status:** active  
- **Budget:** primary all (2), secondary up to 3, tertiary up to 2, at most 7 tested  
- **Why this budget:** Only a few readings a month, so tests have very few days; keep to well-sourced candidates and report small samples plainly.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | medication_adherence | medication_adherence | 2 days | readings after a missed antihypertensive dose vs after taken doses -> systolic and diastolic | B | S20;S11 | available | patient takes a blood pressure medicine |
| 2 | primary | measurement_context | location; time of day | same reading | readings at a clinic or at unusual times vs at home -> systolic and diastolic | A | S15;S16 | partial | - |
| 3 | secondary | stress_mood | mood_state; diary_context | same day | strained days vs calm days -> systolic and diastolic | A | S15;S17 | available | - |
| 4 | secondary | sleep | sleep_duration | previous night | short-sleep days vs normal -> systolic and diastolic | A | S15;S16 | available | - |
| 5 | secondary | salt_in_meals | food_content; meal_events | previous 24 hours | salty or festive meals vs usual meals -> systolic and diastolic | B | S15;S17 | partial (food descriptions only) | - |
| 6 | tertiary | alcohol_caffeine | diary_context (substance_use); caffeine intake | previous 12 hours | alcohol or caffeine vs none -> systolic and diastolic | B | S15;S16 | partial | - |
| 7 | tertiary | pain_or_illness | diary_context (symptom) | same day | pain or symptom days vs none -> systolic and diastolic | B | S17;S20 | available | - |
| 8 | tertiary | other_medications | medication list | current | NSAIDs, decongestants or steroids -> systolic and diastolic | B | S15;S20 | none | patient has such a medicine listed |

- *medication_adherence*: Missing blood pressure medication is commonly listed; a lower-quality source for this exact point.
- *measurement_context*: Clinic anxiety, a full bladder and recent caffeine change readings.
- *sleep*: Poor sleep raises blood pressure.
- *salt_in_meals*: One high-salt meal can raise pressure temporarily.

### `hydration_below`

- **Applies when:** daily fluid intake below her usual  
- **Measure and direction:** hydration, below  
- **Meera hand-offs in the year:** 2  
- **Status:** active  
- **Budget:** primary all (2), secondary up to 2, tertiary up to 1, at most 5 tested  
- **Why this budget:** Evidence describes causes of dehydration, not of low logged intake; budget kept small and basis marked as partly reasoned.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | primary | illness_symptoms | diary_context (symptom) | same day | symptom days vs none -> daily fluid intake | B | S18 | available | - |
| 2 | primary | busy_routine | location; screen_time; diary_context | same day | workload or travel days vs ordinary days -> daily fluid intake | C | S18 | available | - |
| 3 | secondary | high_prior_glucose | glucose stream | previous day | high-glucose days vs normal -> daily fluid intake | A | S18 | available | - |
| 4 | secondary | weather_environment | diary_context (environment) | same day | hot or humid days vs ordinary days -> daily fluid intake | B | S18 | partial (diary only) | - |
| 5 | tertiary | alcohol | diary_context (substance_use) | previous evening | alcohol entry vs none -> daily fluid intake | B | S18 | partial (diary only) | - |

- *illness_symptoms*: Fever, vomiting and diarrhea cause fluid loss; appetite and intake also fall when ill.
- *busy_routine*: Forgetfulness is a reasoned cause of low intake.
- *high_prior_glucose*: Uncontrolled diabetes increases urination and dehydration risk.
- *weather_environment*: Heat increases fluid need.

### `screen_time_above`

- **Applies when:** daily screen time above her usual  
- **Measure and direction:** screen_time, above  
- **Meera hand-offs in the year:** 8  
- **Status:** deferred  
- **Budget:** primary 0, secondary up to 2, tertiary up to 0, at most 2 tested  
- **Why this budget:** No clinical evidence base. Recorded but not used to generate findings until a doctor-advisor decides otherwise.

| # | Tier | Candidate | Data it needs | Look back | What is compared | Evid. | Sources | Meera's data | Applies if |
|---|---|---|---|---|---|---|---|---|---|
| 1 | secondary | workload_events | diary_context | same day | deadline or workload days vs ordinary days -> daily screen time | D | none | available | - |
| 2 | secondary | illness_bedrest | diary_context (symptom) | same day | symptom days vs none -> daily screen time | D | none | available | - |

- *workload_events*: No clinical evidence; behavioural proxy.
- *illness_bedrest*: No clinical evidence; behavioural proxy.

## Sources

Quality varies. The strongest are Mayo Clinic pages, health-system pages and the WHO adherence framework table. Several are patient-education or consumer pages. None is a guideline text read in full, and I did not read the ADA Standards of Care directly. Some search results were copies on unrelated websites and were not used.

| ID | Source | Type |
|---|---|---|
| S1 | [Mayo Clinic: Hyperglycemia, symptoms and causes](https://www.mayoclinic.org/diseases-conditions/hyperglycemia/symptoms-causes/syc-20373631) | clinical reference |
| S2 | [Abbott FreeStyle Libre: Understanding hyperglycemia](https://www.freestyle.abbott/en-in/understanding-your-glucose/chapter-two/understanding-hyperglycemia.html) | device-maker patient education |
| S3 | [Teladoc Health library: Understanding high glucose levels (ADA target ranges)](https://www.teladochealth.com/library/article/understanding-high-glucose-levels) | health-library article |
| S4 | [St. Clair Health: High Blood Glucose handout](https://stclair.org/wp-content/uploads/2024/03/High-Blood-Glucose.pdf) | health-system handout |
| S5 | [Mayo Clinic Q&A: Low blood sugar a concern for patient with diabetes](https://newsnetwork.mayoclinic.org/discussion/mayo-clinic-q-and-a-low-blood-sugar-a-concern-for-patient-with-diabetes) | clinical reference |
| S6 | [Touch Endocrinology: Hypoglycaemia in type 2 diabetes (Barnett review)](https://www.touchendocrinology.com/wp-content/uploads/sites/5/2015/06/barnettrelayout.pdf) | review article |
| S7 | [University of Michigan Depression Center KB: CGM reading low values at night](https://teamdynamix.umich.edu/TDClient/210/DepressionCenter/KB/Article/10689/CGM-Is-Reading-Low-Values-at-Night-Causes-and-Solutions) | research-group knowledge base |
| S8 | [diabetesed.net: Troubleshooting CGM accuracy](https://diabetesed.net/troubleshooting-cgm-accuracy/) | diabetes-educator resource |
| S9 | [Bon Secours / Mercy Health: Sinus tachycardia (triggers and risk factors)](https://www.bonsecours.com/health-care-services/heart-care-cardiology/conditions/sinus-tachycardia) | health-system page |
| S10 | [The Healthy (Reader's Digest): 9 reasons your heart is racing](https://www.thehealthy.com/?p=360002) | consumer health article quoting a cardiologist |
| S11 | [BMJ Open 2020 (PMC7044979), Table 1: WHO five dimensions affecting adherence](https://pmc.ncbi.nlm.nih.gov/articles/PMC7044979/table/T1) | peer-reviewed table of the WHO framework |
| S12 | [Abbott ACARE Pro: WHO five-dimensions model of adherence barriers](https://acarepro.abbott.com/articles/general-topics/models-determinants-language/) | professional education summary |
| S13 | [Sleep Health Foundation (Australia): Common causes of inadequate sleep](https://sleephealthfoundation.org.au/sleep-disorders/common-causes-of-inadequate-sleep) | sleep-health charity fact sheet |
| S14 | [UC Health: Insomnia (cites CDC key sleep disorders)](https://www.uchealth.org/diseases-conditions/insomnia/) | health-system page |
| S15 | [Thrombosis.org: Everyday things that can temporarily raise blood pressure (cites 2025 AHA/ACC guideline)](https://thrombosis.org/patients/patient-articles/everyday-things-that-can-temporarily-raise-blood-pressure) | patient article citing guideline |
| S16 | [AARP: Surprising causes of high blood pressure (cites AHA)](https://www.aarp.org/health/conditions-treatments/surprising-causes-high-blood-pressure) | consumer health article |
| S17 | [Livestrong: Causes of sudden increase in blood pressure (cites NIH, Mayo, AHA, CDC)](https://livestrong.com/article/31644-causes-sudden-increase-blood-pressure) | consumer health article |
| S18 | [Mayo Clinic: Dehydration, symptoms and causes](https://www.mayoclinic.org/diseases-conditions/dehydration/symptoms-causes/syc-20354086) | clinical reference |
| S19 | [Diabetes Care 2026 study as summarized by Medical Dialogues; PMC studies on cycle phase (mostly type 1 diabetes)](https://medicaldialogues.in/diabetes-endocrinology/news/phases-of-menstrual-cycle-may-influence-glucose-control-in-type-1-diabetes-study-176319) | news summary of a journal study; individual effects inconsistent |
| S20 | [Doctors Note (ubiehealth): blood pressure spikes and heart rate pages](https://ubiehealth.com/doctors-note/blood-pressure-high-spikes-47-medical-steps-causes23e2) | consumer health site (lower quality; used only to corroborate) |

## What is weakly supported

- Candidates marked **C** or **D** are reasoned, not sourced.
- `meal_timing`, `unusual_activity_prior_day`, `meal_digestive` and `illness_poor_intake` are reasoned.
- The cycle-phase candidate rests mainly on type 1 diabetes studies, with inconsistent individual effects; type 2 evidence was not found in this pass.
- The tier assignments (which candidate is primary) are my judgment from how often and how prominently sources list each cause. No source ranks them.
- Hydration evidence concerns causes of dehydration (fluid loss), not low logged intake.
- Screen time has no evidence base; the rule is deferred.

## Review checklist for the doctor-advisor

1. Are the primary candidates right for each condition?
2. Should any secondary or tertiary candidate be removed or promoted?
3. Is anything important missing (for example thyroid status for heart rate, or perimenopause for sleep and glucose)?
4. Which conditions need `applies_if` rules (for example type of glucose-lowering medicine)?
5. Are the budgets sensible, and what evidence bar should apply when several candidates are tested?
6. Should the screen-time rule be dropped?

## Data availability for the first patient

Not in the store: caffeine, pain, hourly steps, weight. Alcohol and weather appear only as diary categories. The cycle stream was not confirmed in the store. Candidates that need these are skipped and reported.
