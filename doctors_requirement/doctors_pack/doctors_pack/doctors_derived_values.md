# Values derived from existing data, with check values

**Purpose.** Formulas and Meera's computed values for everything the doctors' tab can show without new data. Claude Code should **recompute each value from the store (or from `final/*.csv` where the series is CSV-only) and compare** with the value here. A difference above the stated tolerance should be reported, not fixed.

**Reference date:** 2026-09-17. **Nothing here is invented:** every value is calculated from an existing file.

## 1. Conventions that change the numbers

- **Glucose cleaning (the Baseline Engine's rule):** drop readings outside 40 to 400 mg/dL; then drop a reading that jumps more than 75 mg/dL **from the last kept reading**. This leaves 33,573 of 33,581 raw readings (the store holds 33,576 because five readings above 600 are rejected earlier). Comparing with the previous *raw* reading instead gives 33,566 and slightly different daily means; do not use that variant.
- **GMI** = 3.31 + 0.02392 x mean glucose (mg/dL), rounded to 2 decimals. **Gap** = HbA1c minus the rounded GMI.
- **Lab windows** cover the 90 days before the lab date's midnight; the lab day itself is excluded (the Baseline's convention). Including the lab day changes the 6 March gap from +0.55 to +0.56.
- **Time in range** = readings 70 to 180 mg/dL. Percentages are shares of cleaned readings.
- The Baseline parses a date-only lab timestamp in the machine's local time zone. Run the check on the same time zone (IST).

## 2. CGM metrics

| Window | Readings | Mean | SD | CV | Time in range 70 to 180 | Below 70 | Above 180 | GMI |
|---|---|---|---|---|---|---|---|---|
| Whole year (2025-10-01 to 2026-09-17) | 33,573 | 126.62 | 17.24 | 13.6% | 99.25% | 0.01% | 0.74% | 6.34 |
| 90 days to 2026-09-17 inclusive | 8,682 | 120.00 | 16.39 | 13.7% | 99.82% | 0.01% | 0.17% | 6.18 |
| 14 days to 2026-09-17 inclusive | 1,422 | 133.92 | 15.19 | 11.3% | 98.95% | 0.00% | 1.05% | 6.51 |

Tolerance: 0.05 on means and GMI, 0.1 on percentages.

- **Readings below 70 mg/dL:** 4, all exactly 65.0 (2025-11-08 11:00, 2026-01-20 16:00, 2026-03-22 11:00, 2026-08-19 15:00). These are the known isolated artifact readings, not hypoglycemia. A fifth artifact (2026-08-22 10:30, 76.3) is above 70. **The tab must not count them as hypoglycemic events.**
- **Readings below 54:** 0. **Days with any reading above 180:** 68 (248 readings).
- **Daily means (check values):** 2025-11-08 123.27; 2025-11-18 150.97; 2026-04-23 114.49; 2026-08-22 120.16; 2026-09-17 136.79.

## 3. HbA1c against CGM (the discordance the document's section 4 talks about)

| Lab date | HbA1c | Mean glucose, 90 days before | GMI | Gap (HbA1c minus GMI) | Readings |
|---|---|---|---|---|---|
| 2025-12-18 | 7.6 | 132.7 | 6.48 | +1.12 | 7,436 |
| 2026-03-06 | 7.0 | 131.2 | 6.45 | +0.55 | 8,579 |
| 2026-09-17 | 7.4 | 119.8 | 6.18 | +1.22 | 8,599 |

The 2025-09-15 lab has no CGM before it. **Data note:** HbA1c 7.0 to 7.6 sits with a CGM mean of about 120 to 133 and a time in range of 99%. The labs and the CGM were generated separately. The doctors' document says discordance between measures is a reason to consider fructosamine or glycated albumin (section 4). See doctors_questions.md Q12.

## 4. Two-hour post-meal glucose from CGM (not the OGTT value)

For each meal, the cleaned reading nearest to 120 minutes after the meal start (within 7 minutes).

| Meal | Meals with a value | Median | 90th percentile | Maximum | Share at or above 180 | Median, last 30 days |
|---|---|---|---|---|---|---|
| Breakfast | 346 | 138.3 | 152.6 | 176.8 | 0.0% | 136.1 |
| Lunch | 347 | 138.0 | 153.2 | 180.8 | 0.3% | 136.7 |
| Dinner | 346 | 135.8 | 152.3 | 169.4 | 0.0% | 135.4 |

Meal kinds are matched by label text (breakfast, lunch, dinner including festive and late dinners); 8 meals have no kind. The most recent dinner (festive dinner, 2026-09-17 21:28) has a 2-hour value of 152.9 mg/dL. The document gives no band for ordinary post-meal glucose; show values only.

## 5. Body measures

| Measure | First (2025-10-01) | Last (2026-09-17) | Formula or note |
|---|---|---|---|
| Weight (kg) | 71.4 | 72.1 | Range 71.3 to 72.9; 59 weekly values |
| Height (cm) | 160 | 160 | Fixed |
| BMI | 27.89 | 28.16 | kg / m2 |
| Waist (cm) | 88.9 | 91.5 |  |
| Hip (cm) | 103.8 | 105.2 |  |
| WHR | 0.856 | 0.87 | waist / hip |
| WHtR | 0.556 | 0.572 | waist / height; 3 decimals |

Tolerance: exact to the stored precision.

## 6. Labs on the four dates

| Value | 2025-09-15 | 2025-12-18 | 2026-03-06 | 2026-09-17 | Formula or note |
|---|---|---|---|---|---|
| Fasting glucose (mg/dL) | 132.0 | 145.0 | 128.0 | 138.0 |  |
| HbA1c (%) | 7.1 | 7.6 | 7.0 | 7.4 |  |
| Total cholesterol | 205 | 212 | 198 | 206 |  |
| LDL-C | 124 | 130 | 118 | 126 |  |
| HDL-C | 46 | 44 | 47 | 45 | Low for a woman: under 50 |
| Triglycerides | 175 | 195 | 162 | 180 | At or above 150 in every panel |
| Non-HDL-C | 159 | 168 | 151 | 161 | total cholesterol minus HDL-C |
| TG/HDL-C | 3.8 | 4.43 | 3.45 | 4.0 | TG / HDL-C; 2 decimals; 3.0 or higher at every date |
| Creatinine (mg/dL) | 0.8 | 0.8 | 0.8 | 0.8 |  |
| eGFR (stored) | 93.7 | 93.7 | 93.7 | 93.7 | Constant, because creatinine is constant |
| ALT | 45 | 44 | 39 | 43 | Mildly elevated, as the persona intends |
| AST | 33 | 33 | 30 | 32 |  |
| GGT | 48 | 50 | 43 | 47 |  |
| Steatosis index (HSI) | 42.8 | 42.8 | 42.8 | 42.9 | An index, not a diagnosis. CSV only |
| TSH (mIU/L) | 2.7 | 3.2 | 2.9 | 3.0 | CSV only. All inside a normal range |

**eGFR check.** CKD-EPI 2021 for a woman with creatinine 0.8 mg/dL gives 94.3 at age 42 and **93.7 at age 43**. The dataset stores 93.7 on all four dates, so it matches the equation only on the last date (the first three differ by 0.6). A trivial inconsistency, noted for completeness.

**Direction over the year** (first to last, with the peak): HbA1c 7.1 to 7.4 (peak 7.6 in December); fasting glucose 132 to 138 (peak 145); LDL-C 124 to 126 (peak 130); triglycerides 175 to 180 (peak 195); HDL-C 46 to 45. The shape is improve, worsen, improve, worsen, as the persona intends, not a straight line.

## 7. Sleep, activity and heart rate

| Value | Result | Formula or note |
|---|---|---|
| Sleep, whole year (352 nights) | mean 6.68 h; median 6.9 h; 54.8% of nights under 7 h | sleep_yearly.csv |
| Sleep, average of the last 7 nights | 4.94 h | The document asks for a prior-7-day average; the last night was 3.8 h |
| Sleep, average of the last 30 nights | 6.46 h |  |
| Daily steps (sum of hourly steps, 340 days) | median 2,106; mean 2,353; last-30-day mean 2,625 | steps_hourly_yearly.csv summed per day |
| Days at or above 7,000 steps | 1.8% | The Threshold Evaluator's daily step reference is 7,000 |
| Days under 4,000 steps | 93.8% |  |
| Sedentary time | median 684 min a day (11.4 h); last-30-day median 661 min | sedentary_time_full_year.csv |
| Resting heart rate | median 77 bpm; last-30-day median 73; range 64 to 102 | vitals_yearly.csv; last value of each day |

**IPAQ.** It cannot be computed (it needs days, duration and intensity of activity). Steps and sedentary time may only be shown as a labelled stand-in. See doctors_questions.md Q6.

## 8. Blood pressure

| Value | Result |
|---|---|
| Readings | 141 (about every 2 to 3 days) |
| First and last | 129/86 and 138/94 (on 2026-09-17) |
| Median, whole year | 125/81 |
| Mean of the last 28 days | 125.5/82.5 (14 readings) |
| Range | systolic 108 to 152; diastolic 70 to 94 |
| Readings at or above 130 or 80 | 63.8% |
| Readings at or above 140 or 90 | 7.8% |

The document has no band for blood pressure, so the last two rows are descriptive shares, not signals.

## 9. Medicines and the diary

| Medicine id in the data | Taken, whole year | Taken, last 90 days |
|---|---|---|
| med_002_metformin (1000 mg twice daily) | 82.7% | 85.6% |
| med_003_amlodipine (5 mg daily) | 77.0% | 75.6% |
| med_004_levothyroxine (50 mcg daily) | 80.4% | 85.6% |

Doses are from the persona. The id `med_001` is unused in the data; it was probably metformin 500 mg twice daily, superseded on 2023-06-15 (to confirm). Alcohol diary entries (category substance_use): 2025-12-25, 2025-12-31, 2026-01-12, 2026-01-13, 2026-02-13, 2026-02-14.

## 10. Flags derived from the document's own definitions

| Flag | Result | Basis |
|---|---|---|
| Glycemic state | Type 2 diabetes (established) | Diagnosed 2022-02-04 (persona). Prediabetes does not apply |
| Obesity | Yes | BMI 28.16 at or above 25 (ICMR-INDIAB); waist 91.5 cm at or above 80 cm |
| Central adiposity | Yes | WHtR 0.572 at or above 0.55; WHR 0.870 above 0.80 |
| High TG | Yes | 180 at or above 150 (all four panels) |
| Low HDL-C | Yes | 45 under 50 (woman) (all four panels) |
| High LDL-C by ICMR (130 or more) | No on the last panel (126); 130 in December | Epidemiologic definition only; the treatment goal is individual |
| TG/HDL-C at or above 3.0 | Yes (4.00 on the last panel) |  |
| Sleep under 7 hours | Yes on average of the last 7 nights (4.94 h); median of the year 6.9 h |  |
| CKD | Not excludable | UACR missing; eGFR normal |

## 11. Not computed, on purpose

- **No composite or overall score**, as the document requires.
- **No metabolic risk score** (document section 8).
- **No HbA1c goal, LDL goal or follow-up row.** They need the doctors' decision.
