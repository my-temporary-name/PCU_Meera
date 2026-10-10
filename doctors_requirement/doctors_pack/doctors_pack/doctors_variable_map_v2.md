# Variable map, version 2 (after the new data files)

Replaces doctors_variable_map.md. All 54 variables in section 1 of the NMG Lite document now have a source and a value for Meera as of 2026-09-17.

| Provenance | Meaning | Variables | Share |
|---|---|---|---|
| E | Existing data file | 22 | 41% |
| D | Derived by formula from existing data | 5 | 9% |
| P | Stated in the persona document | 9 | 17% |
| B | Best guess created here (needs a doctor's review) | 18 | 33% |

| # | Variable | Domain | Value for Meera | Source file and column | Provenance |
|---|---|---|---|---|---|
| 1 | Age | Demographics | 43 | age_fact.csv: age_years; date_of_birth | E |
| 2 | Sex | Demographics | female | sex_fact.csv: sex | E |
| 3 | Occupation | Demographics | Finance Manager, mid-size manufacturing company | lifestyle_standing_record.csv: domain = Occupation | P |
| 4 | Height | Anthropometry | 160 cm | bmi_full_year.csv: height_cm | E |
| 5 | Weight | Anthropometry | 72.1 kg (2026-09-17) | weight_yearly.csv; history: anthropometry_history.csv | E |
| 6 | BMI | Anthropometry | 28.16 | bmi_full_year.csv: bmi; history: anthropometry_history.csv | E |
| 7 | Waist | Anthropometry | 91.5 cm | waist_hip_ratio_full_year.csv: waist_cm; history file | E |
| 8 | Hip | Anthropometry | 105.2 cm | waist_hip_ratio_full_year.csv: hip_cm; history file | E |
| 9 | WHR | Anthropometry | 0.870 | waist_hip_ratio_full_year.csv: whr | E |
| 10 | WHtR | Anthropometry | 0.572 | waist_cm / height_cm; also anthropometry_history.csv: whtr | D |
| 11 | Fasting plasma glucose | Glycemia | 138 mg/dL (2026-09-17) | lab_panels_yearly.csv; labs_history; labs_additional (2026-06-17) | E |
| 12 | HbA1c | Glycemia | 7.4 % (2026-09-17) | hba1c_full_year.csv; labs_history; labs_additional (2026-06-17) | E |
| 13 | 2-hour postprandial glucose | Glycemia | median 135.8 (dinner); last dinner 152.9 | CGM + meals; see doctors_derived_values.md section 4. Not the OGTT value | D |
| 14 | Known diabetes | Glycemia | Type 2 diabetes, diagnosed 2022-02-04 | conditions_standing_record.csv | P |
| 15 | Systolic BP | Blood pressure | 138 (home, 2026-09-17); clinic 138 | vitals_yearly.csv; bp_clinic_history.csv | E |
| 16 | Diastolic BP | Blood pressure | 94 home; 90 clinic | same | E |
| 17 | Hypertension diagnosis | Blood pressure | moderate, diagnosed 2023-01-20 | conditions_standing_record.csv | P |
| 18 | BP treatment | Blood pressure | amlodipine 5 mg daily from 2023-01-20 | medications_history.csv; adherence_yearly.csv | P |
| 19 | Total cholesterol | Lipids | 206 | lipid_panel_full_year.csv; labs_history; labs_additional | E |
| 20 | LDL-C | Lipids | 126 | same | E |
| 21 | HDL-C | Lipids | 45 | same | E |
| 22 | Triglycerides | Lipids | 180 | same | E |
| 23 | Non-HDL-C | Lipids | 161 | total_cholesterol minus hdl_c | D |
| 24 | TG/HDL-C | Lipids | 4.00 | triglycerides / hdl_c | D |
| 25 | apoB | Lipids | 101 mg/dL (2026-09-17) | labs_additional_2025_2026.csv: type apob | B |
| 26 | Lp(a) | Lipids | 48 nmol/L (2026-03-06) | labs_additional_2025_2026.csv: type lp_a | B |
| 27 | Creatinine | Kidney | 0.8 mg/dL | renal_panel_full_year.csv; labs_history | E |
| 28 | eGFR | Kidney | 93.7 | renal_panel_full_year.csv; labs_history | E |
| 29 | UACR | Kidney | 18 mg/g (2026-09-17) | labs_additional_2025_2026.csv: type uacr; history in labs_history | B |
| 30 | ALT | Liver | 43 U/L | hepatic_panel_full_year.csv; labs_history; labs_additional | E |
| 31 | AST | Liver | 32 U/L | same | E |
| 32 | Documented hepatic steatosis or MASLD | Liver | yes (grade 1 steatosis, 2025-06-17; MASLD) | conditions_standing_record.csv; imaging_reports.csv | B |
| 33 | Liver imaging | Liver | abdominal ultrasound 2025-06-17 | imaging_reports.csv | B |
| 34 | Physical activity (IPAQ) | Lifestyle | low category, 258 MET-min/week (2026-09-17) | ipaq_short_quarterly.csv | B |
| 35 | Sedentary time | Lifestyle | median 684 min a day (11.4 h) | sedentary_time_full_year.csv: sedentary_minutes | E |
| 36 | Diet | Lifestyle | irregular timing; see detail | lifestyle_standing_record.csv: domain = Diet pattern; meal_events_yearly.csv | P |
| 37 | Tobacco | Lifestyle | never smoker | lifestyle_standing_record.csv | P |
| 38 | Alcohol and other substances | Lifestyle | occasional social alcohol 1 to 2 times a month; no other substance | lifestyle_standing_record.csv; diary category substance_use | P |
| 39 | Sleep | Lifestyle | 7-night average 4.94 h; year median 6.9 h; source: wearable | sleep_yearly.csv; lifestyle_standing_record.csv: Sleep source | E |
| 40 | First-degree family history of T2D | Family | yes: mother, onset 58 | family_history_standing_record.csv | P |
| 41 | Premature CVD in the family | Family | no: father, bypass in 2019 at 64 | family_history_standing_record.csv | B |
| 42 | PCOS in the family | Family | not documented | family_history_standing_record.csv | B |
| 43 | Gestational diabetes in the family | Family | not documented | same | B |
| 44 | Known inherited or genetic factors | Family | not documented | same | B |
| 45 | Prediabetes | Disease | not applicable (diabetes is established) | glycemic state rule S4 | D |
| 46 | Dyslipidemia | Disease | yes (high TG, low HDL-C), untreated | conditions_standing_record.csv | B |
| 47 | Obesity | Disease | yes (BMI 28.16) | conditions_standing_record.csv | B |
| 48 | ASCVD | Disease | none documented | conditions_standing_record.csv | B |
| 49 | Heart failure | Disease | none documented | same | B |
| 50 | CKD | Disease | none documented (eGFR 93.7, UACR 18) | same | B |
| 51 | MASLD | Disease | yes | same | B |
| 52 | PCOS (own) | Disease | none documented | same | B |
| 53 | History of gestational diabetes | Disease | none documented | same | B |
| 54 | Medications | Disease | metformin 1000 mg twice daily, amlodipine 5 mg daily, levothyroxine 50 mcg daily; no lipid-lowering therapy | medications_history.csv | P |

**Reading the provenance.** E and D are as real as the existing dataset. P is stated in the persona. B is invented here and shown on the page with a "best guess" badge. In B, the "none documented" rows are 'persona silent', not a clinical finding.
