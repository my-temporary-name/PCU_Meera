# Data dictionary for the doctors' extra files

All files are in `doctors_data/`. They are **additive**: no existing file was edited. They use the same conventions as the existing dataset (patient_id `meera_iyer_v1`, IST timestamps, mg/dL, CRLF line ends). Regenerate them with `make_doctors_data.py` (fixed values, no randomness).

## Provenance, in the `source` column

| Value | Meaning |
|---|---|
| `persona_document` | Stated in Realistic_Persona_Meera.md (pre_requisit.zip). Not invented |
| `synthetic_best_guess_v1` | Invented here as the most plausible value, consistent with the persona and the existing data. **No doctor has reviewed it** |
| a mix, for example `persona_document (year); synthetic_best_guess_v1 (day)` | The year or fact is stated; the day or detail is a best guess |

The tab should show a small badge for each: "persona" or "best guess". Replacing a best guess means editing one CSV row.

## Files

| File | Rows | What it holds | Columns | Provenance of rows |
|---|---|---|---|---|
| `labs_history_2021_2025.csv` | 95 | Lab results at 11 clinic visits from 2021-10-12 to 2025-06-17, long format like lab_panels_yearly.csv. Types: fasting_glucose, hba1c, total_cholesterol, ldl_c, hdl_c, triglycerides, creatinine, egfr (CKD-EPI 2021), alt, ast, ggt, tsh, uacr. A test is absent when it was not measured at that visit. | event_id, patient_id, timestamp, type, value, unit, source | 0 persona; 95 best guess |
| `labs_additional_2025_2026.csv` | 36 | (a) New tests on the four existing lab dates: apob, fasting_insulin, homa_ir, fructosamine, uacr (2 dates), lp_a (1 date). (b) A new interim panel on 2026-06-17 with the usual types plus hsi. The existing lab_panels_yearly.csv is not changed. | event_id, patient_id, timestamp, type, value, unit, source | 0 persona; 36 best guess |
| `anthropometry_history.csv` | 11 | Weight, BMI, waist, hip, WHR and WHtR at the same 11 visits, continuing into the weekly series in bmi_full_year.csv and waist_hip_ratio_full_year.csv. | patient_id, date, weight_kg, height_cm, bmi, waist_cm, hip_cm, whr, whtr, source | 0 persona; 11 best guess |
| `bp_clinic_history.csv` | 18 | Seated clinic blood pressure at visits, including the two high readings that led to the 2023 hypertension diagnosis, plus clinic readings on the five data-year visit dates. The home readings stay in vitals_yearly.csv. | patient_id, date, systolic, diastolic, position, measured_by, source | 0 persona; 18 best guess |
| `clinic_visits_history.csv` | 17 | 17 visits with reason, HbA1c, weight, clinic BP and the key decision (treatment starts and changes, imaging orders). Gives the treatment context the doctors ask for. | patient_id, visit_date, visit_type, reason, hba1c_percent, weight_kg, clinic_bp, key_decision, source | 0 persona; 17 best guess |
| `conditions_standing_record.csv` | 14 | Diagnoses with dates, plus explicit 'none documented' rows for ASCVD, heart failure, CKD, PCOS, gestational diabetes and complications. date_basis says whether the date is stated or a best guess. | patient_id, condition, status, diagnosed_date, date_basis, note, source | 5 persona; 9 best guess |
| `medications_history.csv` | 7 | Medicines with dose, frequency, start and end dates, status, and the id used in adherence_yearly.csv. Includes explicit 'none' rows for lipid-lowering therapy and glucocorticoids. | patient_id, medication, indication, dose, frequency, start_date, end_date, status, data_adherence_id, source | 5 persona; 2 best guess |
| `family_history_standing_record.csv` | 7 | First-degree family history with onset age and a premature-or-not flag; 'not documented' rows for PCOS, gestational diabetes and inherited conditions. | patient_id, relative, degree, condition, age_at_onset, event_year, premature, source | 3 persona; 4 best guess |
| `lifestyle_standing_record.csv` | 10 | Tobacco, alcohol, caffeine, occupation, household, diet pattern, sleep source, physical-activity summary. | patient_id, domain, value, detail, as_of_date, source | 7 persona; 3 best guess |
| `treatment_goals_standing_record.csv` | 9 | Targets the doctors' bands and follow-up rows depend on: HbA1c, LDL-C, blood pressure, TG, TG/HDL-C, sleep, activity, weight, kidney monitoring. | patient_id, goal_domain, target, rationale, set_by, set_date, source | 0 persona; 9 best guess |
| `imaging_reports.csv` | 2 | Abdominal ultrasound (grade 1 steatosis) and the ECG already noted in vitals_yearly.csv on 2026-04-06. | patient_id, date, modality, indication, finding, grade, impression, source | 0 persona; 2 best guess |
| `ipaq_short_quarterly.csv` | 5 | Five IPAQ-Short entries with MET-minutes and the official category, consistent with the steps and sedentary files. | patient_id, date, vigorous_days, vigorous_min_per_day, moderate_days, moderate_min_per_day, walking_days, walking_min_per_day, sitting_hours_weekday, met_min_week_vigorous, met_min_week_moderate, met_min_week_walking, met_min_week_total, category, source | 0 persona; 5 best guess |

## Units and formats

- Glucose, lipids and creatinine in mg/dL; HbA1c in %; eGFR in mL/min/1.73 m2; UACR in mg/g; apoB in mg/dL; Lp(a) in nmol/L; insulin in uU/mL; fructosamine in umol/L; TSH in mIU/L; ALT, AST and GGT in U/L.
- Dates are `YYYY-MM-DD`, or `YYYY-MM-DDT08:00:00+05:30` in the long lab files. Empty means not applicable or not measured.
- HOMA1-IR = insulin x fasting glucose (mg/dL) / 405. eGFR is CKD-EPI 2021 (female). HSI = 8 x ALT/AST + BMI + 4.

## How the new files join the existing ones

| New file | Joins to existing file | On |
|---|---|---|
| labs_history, labs_additional | lab_panels_yearly.csv, hba1c_full_year.csv, lipid_panel_full_year.csv, renal_panel_full_year.csv, hepatic_panel_full_year.csv | timestamp or date, and type. Union all of them for one lab series. The only new date inside the data year is 2026-06-17 |
| anthropometry_history | bmi_full_year.csv, waist_hip_ratio_full_year.csv | date. Last history row 2025-06-17; the weekly series starts 2025-10-01 |
| bp_clinic_history | vitals_yearly.csv (home readings) | date. Show clinic and home readings with different markers |
| medications_history | adherence_yearly.csv | data_adherence_id = medication_id |
| conditions, goals, family, lifestyle | none | standing records, one row each |
| ipaq_short_quarterly | steps_hourly_yearly.csv, sedentary_time_full_year.csv | date, for context only |

## The gap this data closes

All 54 variables in the doctors' section 1 now have a source (see doctors_variable_map_v2.md). Not computed on purpose: the metabolic risk score (the document's section 8), any overall colour, and any diagnosis.
