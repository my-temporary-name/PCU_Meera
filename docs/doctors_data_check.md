# Doctors' view: data check (read-only)

Checked on 2026-10-08 against `output/personal_data_store.db` (the store, md5 `5db1fdfe`, identical to `backups/personal_data_store_2026-10-05.db`) and `final/*.csv`. Nothing was changed: no pipeline code, no database, no commit. The only file written is this report (scratch scripts were run from the session scratchpad).

## Summary

| Question | Answer |
|---|---|
| Is the store built from the correct glucose copy? | **Yes.** `final/glucose_stream_yearly.csv` has md5 `508468f16a3ab169fca3672a9efb9df1` (expected `508468f1`). The same file is in `~/Synthetic1/final/` and inside `~/Synthetic1/final.zip`. |
| Store versus that CSV, row by row | **0 differing values.** The store has 33,576 raw glucose rows, the CSV 33,581. The 5 missing rows are the readings above 600 mg/dL, rejected by the plausibility filter before the store (see 1.1). Nothing is in the store that is not in the CSV. |
| The older copy | I found no file with md5 `404bc89e`. The monthly files in `~/Synthetic1/<month>/glucose_stream_*.csv` (33,581 rows in all) reproduce your older-copy figures exactly: **15,732 of 33,581 values differ, mean absolute difference 7.14 mg/dL** (over the differing values). So they hold the older series. |
| Whole-year metrics | All match your expected values (section 1.2). |
| Daily means | 4 of 5 match. **2026-04-23 differs: 114.49 against your 114.37.** |
| Readings after cleaning | **33,573 against your 33,566 (7 more).** Same cause as the 23 April difference. |
| Lab gaps | 90-day windows match your numbers for 18 Dec 2025 and 17 Sep 2026; for 6 Mar 2026 the Baseline gives 6.45 and +0.55 against your 6.44 and +0.56 (within tolerance, caused by whether the lab day is in the window). |

## PART 1: the glucose copy

### 1.1 The CSV and the store

| | Rows |
|---|---|
| `final/glucose_stream_yearly.csv` | 33,581 (all `type = glucose`, `unit = mg/dL`, `source = cgm_synthetic`, `context` empty in every row) |
| Store, `raw_events` (`biomarker = cgm_glucose_reading`, `source_type = reading`) | 33,576, from 2025-10-01T00:00 to 2026-09-17T23:45 |
| In the CSV and not in the store | 5 |
| In the store and not in the CSV | 0 |
| Common rows with a different value | 0 |

Keyed by `(event_id, timestamp)`. The 5 CSV-only rows are the plausibility rejects (all above the 600 mg/dL ceiling, all while she was active):

| event_id | timestamp | value |
|---|---|---|
| evt_glu_01213 | 2025-10-13T15:00 | 612.0 |
| evt_glu_00437 | 2026-02-05T13:00 | 613.9 |
| evt_glu_02157 | 2026-06-23T11:00 | 603.5 |
| evt_glu_01973 | 2026-07-21T13:00 | 611.0 |
| evt_glu_00525 | 2026-09-06T11:00 | 614.2 |

So the store's "raw" glucose is the CSV minus these 5, not the full 33,581. If you need the 33,581, read the CSV.

**Older copy.** Concatenating the monthly files (33,581 rows, matched to the yearly file by timestamp): 15,732 values differ, mean absolute difference 7.136 mg/dL over the differing values (3.34 mg/dL over all 33,581). The store against the monthly files: 15,729 of 33,576 differ (3 of the 5 rejected readings are among the 15,732). The `dhara_mehta_v1_dataset` copy under `~/Synthetic1/` is another patient (md5 `35525891`) and is not an older copy of hers.

### 1.2 Cleaning and whole-year metrics

Cleaning is the Baseline Engine's own code (`baseline_v2.trust.clean_series`, config `config/patient_meera_iyer_v1.yaml`): device range 40 to 400 mg/dL, and a jump of more than 75 mg/dL per 15 minutes (scaled by the gap) from the **last kept** reading.

Readings after cleaning: **33,573 of 33,576 in the store** (33,581 in the CSV). Removed by the Baseline (3):

| timestamp | value | reason |
|---|---|---|
| 2025-12-09T10:00 | 599.0 | outside the device range |
| 2026-04-23T14:00 | 590.0 | outside the device range |
| 2026-05-20T10:00 | 65.0 | jump of more than 75 mg/dL per 15 minutes |

| Metric | Expected | Observed (Baseline cleaning, 33,573 readings) | Match |
|---|---|---|---|
| Readings | 33,566 | **33,573** | differs by 7 (see 1.4) |
| Mean | 126.62 | 126.616 | yes |
| SD | 17.24 | 17.241 (population 17.2409, sample 17.2411) | yes |
| CV | 13.6% | 13.62% (population SD) | yes |
| TIR 70 to 180 | 99.2% | 99.249% (33,321 readings) | yes |
| Below 70 | 0.01% | 0.0119% (4 readings) | yes |
| Above 180 | 0.7% | 0.739% (248 readings) | yes |
| GMI (3.31 + 0.02392 x mean) | 6.34 | 6.3387 | yes |

The same metrics computed on your 33,566-reading variant (1.4) are identical to two decimals, so the 7-reading difference does not move any whole-year figure. Range of the cleaned series: 65.0 to 246.8 mg/dL.

Daily mean glucose (mean of the cleaned readings of the local day):

| Date | Expected | Observed | Readings | Match |
|---|---|---|---|---|
| 2025-11-08 | 123.27 | 123.267 | 96 | yes |
| 2025-11-18 | 150.97 | 150.970 | 88 | yes |
| 2026-04-23 | 114.37 | **114.494** | 95 | **differs by 0.12** |
| 2026-08-22 | 120.16 | 120.165 | 96 | yes |
| 2026-09-17 | 136.79 | 136.786 | 83 | yes |

### 1.3 Lab discordance (HbA1c minus GMI)

GMI = 3.31 + 0.02392 x mean glucose of the cleaned readings in the window. "Before the lab" is the window the Baseline Engine uses: from the lab date's midnight minus N days up to (not including) the lab date's midnight, so **the lab day itself is excluded**. "Including the lab day" adds the lab date's readings (the window ends at the end of the lab date). Gap = HbA1c minus GMI.

| Lab date | HbA1c | Window | Before the lab date: mean, GMI, gap (readings) | Including the lab day: mean, GMI, gap |
|---|---|---|---|---|
| 2025-12-18 | 7.6 | 14 days | 131.07, 6.45, +1.15 (1,326) | 130.30, 6.43, +1.17 |
| | | 30 days | 134.75, 6.53, +1.07 (2,837) | 133.85, 6.51, +1.09 |
| | | 90 days | **132.67, 6.48, +1.12** (7,436) | 132.55, 6.48, +1.12 |
| 2026-03-06 | 7.0 | 14 days | 130.42, 6.43, +0.57 (1,344) | 129.17, 6.40, +0.60 |
| | | 30 days | 131.68, 6.46, +0.54 (2,854) | 130.61, 6.43, +0.57 |
| | | 90 days | **131.19, 6.45, +0.55** (8,579) | 131.02, 6.44, +0.56 |
| 2026-09-17 | 7.4 | 14 days | 133.74, 6.51, +0.89 (1,339) | 134.27, 6.52, +0.88 |
| | | 30 days | 121.61, 6.22, +1.18 (2,875) | 122.80, 6.25, +1.15 |
| | | 90 days | **119.84, 6.18, +1.22** (8,599) | 120.05, 6.18, +1.22 |

(The first lab, 2025-09-15, HbA1c 7.1, has no glucose before it: the CGM series starts on 1 Oct.)

**What the Baseline Engine used** (`baseline_v2/windows.py`, `lab_link`): the 90 days before the lab date, `lab midnight - 90 days <= reading < lab midnight`, on the cleaned readings; GMI from that window's mean, **rounded to 2 decimals**, and the gap is HbA1c minus that rounded GMI, rounded to 2 decimals. It reported 1.12, 0.55 and 1.22 (GMI 6.48, 6.45, 6.18; 78, 90 and 90 days of CGM).

**Does it match?** Yes for 18 Dec (6.48, +1.12) and 17 Sep (6.18, +1.22). For 6 Mar the Baseline gives GMI 6.45 and +0.55, you expect 6.44 and +0.56. Both are consistent with the data: the difference is only whether the lab day's readings (the 6 Mar glucose) are in the window. Your numbers equal the "including the lab day" column; the Baseline's equal the "before the lab date" column. Both differences (0.01) are within your tolerance.

### 1.4 Values that differ from yours by more than 0.05 (0.1 for gaps)

| Value | Yours | Observed | Likely cause |
|---|---|---|---|
| Readings after cleaning | 33,566 | 33,573 | Your jump rule compares each reading with the **previous raw** reading, so the reading right after a spike is removed too. The Baseline compares with the **last kept** reading, so after the spike is removed the next normal reading is kept. I reproduced your 33,566 with that variant: 15 removed = 7 above the 400 range (the five readings above 600 plus 599.0 and 590.0) + 8 more, namely the reading just after each of those 7 spikes (147.4, 141.8, 137.6, 126.0, 122.8, 112.7 and 130.8 mg/dL, all plausible) and the 65.0 on 20 May. |
| Daily mean, 2026-04-23 | 114.37 (94 readings) | 114.49 (95 readings) | The same cause: your variant also removes the 126.0 at 14:15, the reading right after the 590.0 spike. With it removed the day's mean is 114.37, which is your value. |

Nothing else differs by more than the tolerance. Below tolerance, for information: the 6 Mar lab GMI and gap (0.01 each, window definition, above).

## PART 2: where each series lives

The store has two tables: `raw_events` (readings that got a status, plus the pairings) and `context_events` (everything else). `raw_events` has no unit column and no patient id; units are implied by the series name.

| Series | In the store? | Table and name | Source file in `final/` |
|---|---|---|---|
| Fasting glucose | yes | `raw_events`, `fasting_glucose` (4) | `lab_panels_yearly.csv` (type `fasting_glucose`, mg/dL) |
| HbA1c | yes | `raw_events`, `hba1c` (4) | `hba1c_full_year.csv` (`hba1c_percent`) |
| Total cholesterol, LDL, HDL, triglycerides | yes | `raw_events`, `total_cholesterol`, `ldl_c`, `hdl_c`, `triglycerides` (4 each) | `lipid_panel_full_year.csv` |
| Creatinine, eGFR | yes | `raw_events`, `creatinine`, `egfr` (4 each) | `renal_panel_full_year.csv` |
| ALT, AST, GGT | yes | `raw_events`, `alt`, `ast`, `ggt` (4 each) | `hepatic_panel_full_year.csv` |
| Steatosis index (HSI) | **no, CSV only** | not in the store | `hepatic_panel_full_year.csv`, column `hsi` (42.8, 42.8, 42.8, 42.9); `bmi_used` is also only there |
| TSH | **no, CSV only** | not in the store | `lab_panels_yearly.csv`, type `tsh` (mIU/L), 4 rows: 2.7, 3.2, 2.9, 3.0 |
| Weight | **no, CSV only** | not in the store (it passes the plausibility filter but has no reference range, so it never gets a status row) | `weight_yearly.csv` (59 rows, kg); the kg values are also in `bmi_full_year.csv` and `waist_hip_ratio_full_year.csv` |
| BMI | yes | `raw_events`, `bmi` (59) | `bmi_full_year.csv`; `weight_kg` and `height_cm` are not stored |
| Waist and hip | **ratio only** | `raw_events`, `waist_hip_ratio` (59) | `waist_hip_ratio_full_year.csv`; `waist_cm` and `hip_cm` are CSV only |
| Blood pressure | yes, split | `raw_events`, `blood_pressure_systolic` and `blood_pressure_diastolic` (141 each) | `vitals_yearly.csv` (type `blood_pressure`, text such as `129/86`) |
| Resting heart rate | yes | `raw_events`, `resting_heart_rate` (353) | `vitals_yearly.csv` (type `resting_hr`) |
| Continuous heart rate | yes, two places | `context_events`, `continuous_heart_rate` (33,792, all readings); `raw_events`, `continuous_heart_rate` (8,348, only the readings in an hour with zero steps, which carry a status) | `continuous_heart_rate_yearly.csv` |
| Sleep | yes, two places | `raw_events`, `sleep_duration` (352, hours); `context_events`, `sleep_quality` (352; text such as `poor`, hours in `value_num`) | `sleep_yearly.csv` (`value`, `quality`) |
| Hourly steps | yes, context only | `context_events`, `step_count_hourly` (8,160) | `steps_hourly_yearly.csv` (type `steps_hourly`, count) |
| Daily steps | yes | `raw_events`, `step_count` (340) | `sedentary_time_full_year.csv`, column `total_steps` (empty on 12 days); equals the sum of the hourly values on every day |
| Sedentary time | yes | `raw_events`, `sedentary_time` (352, minutes) | `sedentary_time_full_year.csv` (`sedentary_minutes`) |
| Hydration | yes | `raw_events`, `hydration` (352, mL) | `hydration_full_year.csv` (`hydration_ml`) |
| Screen time | yes | `raw_events`, `screen_time` (352, hours) | `screen_time_full_year.csv` (`screen_time_hours`) |
| Medicine adherence | yes | `context_events`, `medication_adherence` (1,056 = 3 medicines x 352 days; `value_text` taken or missed, `value_num` 1 or 0, `category` = medicine id) | `adherence_yearly.csv` (`medication_id`, `taken`) |
| Mood | yes | `context_events`, `mood_state` (1,056 = 3 blocks x 352 days; `value_text` = label, `category` = category, block in `meta_json`) | `cognitive_mental_health_full_year.csv` |
| Menstrual cycle | **no, CSV only** | not in the store | `menstrual_cycle_full_year.csv` (352 rows; says `menopause_status = peri`) |
| Meals and food content | yes | `context_events`, `meal_events` (1,055; `category` = meal label, `value_text` = food description) | `meal_events_yearly.csv` (time and label) joined with `food_content_full_year.csv` (food description) |
| Diary entries | yes | `context_events`, `diary_context` (129; `category`, `value_text` = description, `meta_json.note` = severity note) | `context_events_yearly.csv`. The long narrative diary (`Meera_Diary_Yearly_Oct2025_Sep2026.md`) is a file only |
| Location | yes | `context_events`, `location` (352; `value_text` = type, e.g. office, home_wfh) | `location_full_year.csv` |
| Allergies | **no, CSV only** | not in the store | `allergies_standing_record.csv` (2 rows) |
| Vaccinations | **no, CSV only** | not in the store | `vaccination_history.csv` (2 rows) |
| Age and sex facts | **no, CSV only** | not in the store; the pipeline reads them from the CSVs when it runs | `age_fact.csv` (date of birth 1983-04-12; age 43 as of 2026-09-17), `sex_fact.csv` (female) |

Values equal the CSV values in every series that is in the store: I compared glucose, resting heart rate, blood pressure (both parts), sleep, daily steps, sedentary time, hydration, screen time, BMI, waist-hip ratio, HbA1c, fasting glucose, the lipid, hepatic and renal values, and found 0 differences.

### Column, name and unit differences between the CSVs and the store

- **Names:** CSV type `glucose` is stored as `cgm_glucose_reading`; `resting_hr` as `resting_heart_rate`; `steps_hourly` as the stream `step_count_hourly`; `hba1c_percent` as `hba1c`; `whr` as `waist_hip_ratio`; `total_steps` as `step_count`; `sedentary_minutes` as `sedentary_time`; `hydration_ml` as `hydration`; `screen_time_hours` as `screen_time`; `medication_id` as the `category` of `medication_adherence`.
- **Units:** the store has no unit column. Units are implied: mg/dL, bpm, mmHg, hours (sleep, screen time), minutes (sedentary), mL (hydration), % (HbA1c, TIR), count (steps).
- **Dropped columns:** `patient_id` everywhere, `source` everywhere, `unit`, and the `context` column of the glucose and vitals files (empty for glucose; one vitals row carries a note, "walk-in consultation, elevated HR noted, ECG normal", that is not in the store). `quality` of the sleep file becomes its own stream.
- **Shapes:** blood pressure `129/86` is split into two rows; adherence `True/False` becomes `taken/missed` text plus 1/0; the mood file's `time_block` goes into `meta_json`.
- **Timestamp formats are mixed** in `raw_events`: the time series carry `YYYY-MM-DDTHH:MM:SS+05:30`; the daily series and most labs are date-only (`YYYY-MM-DD`); `fasting_glucose` (from `lab_panels_yearly.csv`) carries `...T08:00:00+05:30`, the other labs date-only. The Baseline's `lab_link` parses the date-only lab timestamp as a naive datetime and converts it to the config timezone, which uses the **machine's local timezone**. This machine is in IST so the result is right; on a machine in another timezone the lab midnight, and so the 90-day window, would shift. I read this in the code and did not test it on another timezone.
- **Two files with 2025-09-15 labs:** `lab_panels_2025_09.csv` (11 rows) and `lab_panels_yearly.csv` (44 rows) the 11 rows of the first are identical (same type, date and value) to the September rows of the second, so the September panel is a duplicate, and the store holds one value per lab per date.
- **Counts that differ by design:** CSV rows against the store for glucose (33,581 against 33,576, the plausibility rejects), continuous heart rate (33,792 in `context_events`, 8,348 in `raw_events`), daily steps (the CSV has 352 rows with 12 empty; the store has 340), weight (59 in the CSV, none stored).

## PART 3: rows and dates in the store

`raw_events` (source type `reading`, 44,469 rows) and `context_events` (45,952 rows). The `raw_events` table also holds 138,118 pairing rows (`source_type = pairing`), 182,587 rows in all.

| Series | Table | Rows | First | Last |
|---|---|---|---|---|
| cgm_glucose_reading | raw_events | 33,576 | 2025-10-01T00:00 | 2026-09-17T23:45 |
| continuous_heart_rate | raw_events | 8,348 | 2025-10-01 | 2026-09-17 |
| continuous_heart_rate | context_events | 33,792 | 2025-10-01 | 2026-09-17 |
| step_count (daily) | raw_events | 340 | 2025-10-01 | 2026-09-17 |
| step_count_hourly | context_events | 8,160 | 2025-10-01 | 2026-09-17 |
| sleep_duration | raw_events | 352 | 2025-10-01 | 2026-09-17 |
| sleep_quality | context_events | 352 | 2025-10-01 | 2026-09-17 |
| resting_heart_rate | raw_events | 353 | 2025-10-01 | 2026-09-17 |
| sedentary_time | raw_events | 352 | 2025-10-01 | 2026-09-17 |
| hydration | raw_events | 352 | 2025-10-01 | 2026-09-17 |
| screen_time | raw_events | 352 | 2025-10-01 | 2026-09-17 |
| blood_pressure_systolic | raw_events | 141 | 2025-10-01 | 2026-09-17 |
| blood_pressure_diastolic | raw_events | 141 | 2025-10-01 | 2026-09-17 |
| bmi | raw_events | 59 | 2025-10-01 | 2026-09-17 |
| waist_hip_ratio | raw_events | 59 | 2025-10-01 | 2026-09-17 |
| hba1c | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| fasting_glucose | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| total_cholesterol | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| ldl_c | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| hdl_c | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| triglycerides | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| creatinine | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| egfr | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| alt | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| ast | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| ggt | raw_events | 4 | 2025-09-15 | 2026-09-17 |
| medication_adherence | context_events | 1,056 | 2025-10-01 | 2026-09-17 |
| mood_state | context_events | 1,056 | 2025-10-01 | 2026-09-17 |
| meal_events | context_events | 1,055 | 2025-10-01 | 2026-09-17 |
| diary_context | context_events | 129 | 2025-10-01 | 2026-09-17 |
| location | context_events | 352 | 2025-10-01 | 2026-09-17 |
| weight, TSH, HSI, waist and hip separately, menstrual cycle, allergies, vaccinations, age and sex | not in the store | 0 | | |

The four lab dates are 2025-09-15, 2025-12-18, 2026-03-06 and 2026-09-17. The glucose series ends at 2026-09-17T23:45, so the lab on 17 Sep falls on the last day of data.

## How to reproduce

The comparisons were run with the Baseline Engine's own `Config`, `StoreView`, `clean_series`, `glucose_metrics` and `lab_link`, opening the store read-only. The jump-rule variants were run directly on the CSV. No project file was modified.
