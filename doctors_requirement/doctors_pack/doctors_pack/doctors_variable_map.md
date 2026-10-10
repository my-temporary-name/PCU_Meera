# NMG Lite variable map for Meera: where every variable comes from

> **SUPERSEDED** by doctors_variable_map_v2.md (all 54 variables now have a source).


**Purpose.** For each variable in section 1 of the doctors' document (NMG Lite Version 1), this file says where Meera's value comes from, whether the pipeline's store holds it, and how to derive it when it is not stored. Claude Code uses it to build the doctors' tab. Nothing here changes the pipeline or any existing file.

**Count.** The document names 54 distinct variables (my earlier count of 53 was approximate; two diagnoses that appear twice in the document, diabetes and hypertension, are counted once).

| Status | Meaning | Variables | Share |
|---|---|---|---|
| DATA | In a data file now | 22 | 41% |
| DERIVE | Calculated from data we have | 7 | 13% |
| PERSONA | Not in any data file, but stated in the persona document (pre_requisit.zip, Realistic_Persona_Meera.md); extract, do not invent | 8 | 15% |
| PARTIAL | Some of it exists; the rest is missing | 4 | 7% |
| MISSING | Not recorded anywhere | 13 | 24% |

Usable today (DATA, DERIVE or PERSONA): 37 of 54 (69%). Of the 13 missing, 6 are tests (apoB, Lp(a), UACR, documented steatosis, MASLD, imaging) and 7 are "not documented" flags that are probably "none" but must be confirmed.

## How to read the table

- **Source** names the file and column in the dataset (`final/`). Series values are not copied here.
- **In the store?** comes from Claude Code's check (docs/doctors_data_check.md). "Yes" means the series is in `raw_events` or `context_events` and equals its CSV exactly. The exact stream names are in that report.
- **PERSONA** items are real facts about the synthetic patient, written before the data was generated. They live in the doctors' extras file, not in the pipeline.

## The variables

| # | Domain | Variable | Status | Source | In the store? | How |
|---|---|---|---|---|---|---|
| 1 | Demographics | Age | DATA | age_fact.csv: date_of_birth 1983-04-12; age_years 43 as of 2026-09-17 | No (CSV only) | Calculate from the birth date |
| 2 | Demographics | Sex | DATA | sex_fact.csv: sex = female | No (CSV only) |  |
| 3 | Demographics | Occupation | PERSONA | Persona section 1: Finance Manager, mid-size manufacturing company; full-time; quarter-end cycles; 2 to 3 trips a quarter | No | Not a data field. Take from doctors_extras.md part A |
| 4 | Anthropometry | Height | DATA | bmi_full_year.csv: height_cm = 160 (fixed) | No (CSV only) |  |
| 5 | Anthropometry | Weight | DATA | weight_yearly.csv: 59 weekly values | No (CSV only) |  |
| 6 | Anthropometry | BMI | DATA | bmi_full_year.csv: bmi (59 weekly) | Yes (raw_events) | Computed from weight and height |
| 7 | Anthropometry | Waist circumference | DATA | waist_hip_ratio_full_year.csv: waist_cm (59 weekly) | No (CSV only; the store holds the ratio only) |  |
| 8 | Anthropometry | Hip circumference | DATA | waist_hip_ratio_full_year.csv: hip_cm | No (CSV only) |  |
| 9 | Anthropometry | WHR | DATA | waist_hip_ratio_full_year.csv: whr | Yes (raw_events) |  |
| 10 | Anthropometry | WHtR | DERIVE | waist_cm / height_cm | n/a | Same dates as the waist readings |
| 11 | Glycemia | Fasting plasma glucose | DATA | lab_panels_yearly.csv: type fasting_glucose (4 dates) | Yes (raw_events) |  |
| 12 | Glycemia | HbA1c | DATA | hba1c_full_year.csv: hba1c_percent (4 dates) | Yes (raw_events) |  |
| 13 | Glycemia | 2-hour postprandial glucose | DERIVE | CGM reading nearest 120 minutes after each meal start (meal_events_yearly.csv + glucose_stream_yearly.csv) | n/a | Not the 75 g OGTT value; the document says to keep them apart |
| 14 | Glycemia | Known diabetes (diagnosis) | PERSONA | Persona section 2: Type 2 diabetes, diagnosed 2022-02-04 | No | Not a data field. Take from doctors_extras.md part A |
| 15 | Blood pressure | Systolic BP | DATA | vitals_yearly.csv: type blood_pressure, value 'sys/dia' (141 readings) | Yes (split into two series) | Split the text value |
| 16 | Blood pressure | Diastolic BP | DATA | same as systolic | Yes |  |
| 17 | Blood pressure | Hypertension diagnosis | PERSONA | Persona section 2: hypertension (moderate), diagnosed 2023, medicated | No | Take from doctors_extras.md part A |
| 18 | Blood pressure | BP treatment | PERSONA | Persona section 3: amlodipine 5 mg once daily from 2023-01-20; adherence_yearly.csv: med_003_amlodipine | Adherence yes (context_events) | Dose and start date from the persona; daily taken or missed from the data |
| 19 | Lipids | Total cholesterol | DATA | lipid_panel_full_year.csv: total_cholesterol (4 dates) | Yes |  |
| 20 | Lipids | LDL-C | DATA | lipid_panel_full_year.csv: ldl_c | Yes |  |
| 21 | Lipids | HDL-C | DATA | lipid_panel_full_year.csv: hdl_c | Yes |  |
| 22 | Lipids | Triglycerides | DATA | lipid_panel_full_year.csv: triglycerides | Yes |  |
| 23 | Lipids | Non-HDL-C | DERIVE | total_cholesterol minus hdl_c | n/a |  |
| 24 | Lipids | TG/HDL-C ratio | DERIVE | triglycerides / hdl_c (both mg/dL) | n/a |  |
| 25 | Lipids | apoB | MISSING | Not in any file | No | See doctors_extras.md part B |
| 26 | Lipids | Lp(a) | MISSING | Not in any file | No | See doctors_extras.md part B |
| 27 | Kidney | Serum creatinine | DATA | renal_panel_full_year.csv: creatinine (4 dates, all 0.8) | Yes |  |
| 28 | Kidney | eGFR | DATA | renal_panel_full_year.csv: egfr (4 dates, all 93.7) | Yes | Constant because creatinine is constant. See doctors_derived_values.md section 6 |
| 29 | Kidney | UACR | MISSING | Not in any file | No | See doctors_extras.md part B |
| 30 | Liver | ALT | DATA | hepatic_panel_full_year.csv: alt (4 dates) | Yes |  |
| 31 | Liver | AST | DATA | hepatic_panel_full_year.csv: ast | Yes |  |
| 32 | Liver | Documented hepatic steatosis or MASLD | MISSING | hepatic_panel_full_year.csv holds a steatosis index (hsi 42.8 to 42.9) and GGT, which are not a diagnosis | hsi: No (CSV only) | See doctors_extras.md part B |
| 33 | Liver | Imaging | MISSING | Not in any file | No | See doctors_extras.md part B |
| 34 | Lifestyle | Physical activity (IPAQ) | PARTIAL | steps_hourly_yearly.csv (hourly steps, 340 days) and sedentary_time_full_year.csv: sedentary_minutes | Yes (steps, sedentary) | No IPAQ days, duration or intensity. Steps and sedentary time can only be shown as a labelled stand-in |
| 35 | Lifestyle | Sedentary time | DATA | sedentary_time_full_year.csv: sedentary_minutes (340 days) | Yes |  |
| 36 | Lifestyle | Diet | PARTIAL | meal_events_yearly.csv (1,055 meals) and food_content_full_year.csv (descriptions) | Yes (context_events) | Free-text food content; no structured diet score |
| 37 | Lifestyle | Tobacco | PERSONA | Persona section 7: no smoking | No | Take from doctors_extras.md part A |
| 38 | Lifestyle | Alcohol and other substances | PERSONA | Persona section 7: occasional social alcohol about 1 to 2 times a month; coffee 3 to 4 cups a day in stressful periods. Diary: 6 alcohol entries (category substance_use) | Diary yes | Persona gives the pattern; the diary gives six dated entries |
| 39 | Lifestyle | Sleep | DATA | sleep_yearly.csv: duration in hours (352 nights) | Yes | The document asks for a 7-day average "with source identified": source is the synthetic wearable |
| 40 | Family and genetic | First-degree family history of T2D | PERSONA | Persona section 2: mother, Type 2 diabetes, diagnosed at 58 | No | Take from doctors_extras.md part A |
| 41 | Family and genetic | Premature CVD in a first-degree relative | PARTIAL | Persona section 2: father has coronary artery disease, bypass surgery in 2019. His age at onset is not stated | No | Cannot decide 'premature' without the father's age. See doctors_questions.md |
| 42 | Family and genetic | PCOS in the family | MISSING | Not documented | No |  |
| 43 | Family and genetic | Gestational diabetes in the family | MISSING | Not documented | No |  |
| 44 | Family and genetic | Known inherited or genetic factors | MISSING | Not documented | No |  |
| 45 | Existing disease and treatment | Prediabetes | DERIVE | Not applicable: diabetes is established, so the glycemic state is T2D (document section 2) | n/a |  |
| 46 | Existing disease and treatment | Dyslipidemia | DERIVE | Derived from the lipid bands: TG at or above 150, and HDL-C below 50 (woman) at every date | n/a | No diagnosis is recorded |
| 47 | Existing disease and treatment | Obesity | DERIVE | BMI at or above 25 (ICMR-INDIAB), waist at or above 80 cm (woman) | n/a |  |
| 48 | Existing disease and treatment | ASCVD (own) | MISSING | Not documented. The persona lists no cardiovascular disease for Meera | No | Record as 'none documented', not as 'none' |
| 49 | Existing disease and treatment | Heart failure | MISSING | Not documented | No | Same |
| 50 | Existing disease and treatment | CKD | PARTIAL | eGFR 93.7 at every date, but UACR is missing, so CKD cannot be excluded or graded | eGFR yes | The document requires an abnormality for 3 months and a UACR |
| 51 | Existing disease and treatment | MASLD | MISSING | Needs documented steatosis (see Liver) | No |  |
| 52 | Existing disease and treatment | PCOS (own) | MISSING | Not in the persona's comorbidity list | No |  |
| 53 | Existing disease and treatment | History of gestational diabetes | MISSING | Not documented | No |  |
| 54 | Existing disease and treatment | Medications | PERSONA | Persona section 3: metformin 500 mg twice daily from 2022-02-10, raised to 1000 mg twice daily on 2023-06-15; amlodipine 5 mg daily from 2023-01-20; levothyroxine 50 mcg daily from 2021-11-01. Daily taken or missed: adherence_yearly.csv | Adherence yes | Names, doses and start dates only exist in the persona |

## Series that exist only as CSV files (not in the store)

Steatosis index (hsi), TSH, weight, waist and hip separately, the menstrual cycle, allergies, vaccinations, the age and sex facts. The doctors' tab must read these from `final/*.csv`.

## Series sizes (from the data check)

All series in the store run 2025-10-01 to 2026-09-17; the labs start on 2025-09-15. Glucose 33,576 raw rows in the store (33,581 in the CSV: five readings above 600 mg/dL are rejected before the store). Continuous heart rate 33,792; hourly steps 8,160; blood pressure 141; each lab 4; adherence and mood 1,056; meals 1,055; diary 129.
