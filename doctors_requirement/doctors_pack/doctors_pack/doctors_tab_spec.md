# Spec for the NMG Lite view (the doctors' tab)

For Claude Code. This tab is **inputs, then fixed rules, then display**. No model, no learning, no explanation step, and nothing from the pipeline. It is built from the CSV files only.

## 1. What the tab is, and is not

- It applies the NMG Lite attention bands (doctors_bands_encoded.md, rule IDs below) to Meera's data and shows each domain's value, colour, trend and context.
- It never combines the colours into one overall colour. It never states a diagnosis, a cause or a risk score. Section 8 of the document (the future risk score) is shown as "not computed".
- **Always show this sentence at the top of the tab:** "Green, Amber and Red are domain-specific clinical-attention signals from NMG Lite. They are not diagnostic criteria and not a validated composite risk score." (cover letter of the document)
- Everything is synthetic. Show a "synthetic patient" notice, and a small "persona" or "best guess" badge on every value that comes from a row whose `source` says so (see doctors_data_dictionary.md).

## 2. Inputs

Existing files (`final/`): glucose_stream_yearly, lab_panels_yearly, hba1c_full_year, lipid_panel_full_year, renal_panel_full_year, hepatic_panel_full_year, bmi_full_year, waist_hip_ratio_full_year, weight_yearly, vitals_yearly, sleep_yearly, steps_hourly_yearly, sedentary_time_full_year, adherence_yearly, meal_events_yearly, context_events_yearly (diary), age_fact, sex_fact, allergies_standing_record.
New files (`doctors_data/`): the 12 CSVs in doctors_data_dictionary.md.
Derived values and their check values: doctors_derived_values.md. Where the document gives a rule, use the rule ID from doctors_bands_encoded.md.

## 3. Layout

1. **Header strip.** Female, 43, Finance Manager. Glycemic state: Type 2 diabetes since 2022-02-04 (rule S4). Other conditions from conditions_standing_record.csv with dates (hypertension 2023, subclinical hypothyroidism 2021, MASLD 2025, perimenopause 2025). Allergy: sulfa drugs. Current medicines from medications_history.csv.
2. **Domain board.** One row per domain, in this order: Anthropometry, Glycemia, Blood pressure, Lipids, Kidney, Liver, Physical activity, Lifestyle and modifiers. Columns: domain, latest values with dates, signal, her own baseline and direction, change since diagnosis, events around the last change, suggested review, provenance badges.
3. **Domain drawer.** Click a row for the full trend from 2021 to 2026 (history file joined to the data year) with: band lines (for example HbA1c goal 7.0, LDL goal 70, TG 150, BP 130/80), the diagnosis date, medicine starts and changes, clinic visits, the ultrasound, and any lab with a best-guess badge.
4. **Follow-up panel.** The suggested row from the document's section 5 and when each review is due (section 6 below). Wording: "Suggested review", never "Action".
5. **Notices** (section 8 below).

## 4. Domain by domain

| Domain | Values shown | Rule IDs | If data is missing |
|---|---|---|---|
| Anthropometry | BMI, waist, hip, WHR, WHtR, weight (latest, trend) | A1 to A4; worst signal wins | Show 'not recorded'; do not colour |
| Glycemia | HbA1c, fasting glucose, goal (from treatment_goals), CGM mean, GMI, time in range 70 to 180, 2-hour post-meal values (labelled 'from CGM, not OGTT'), fructosamine | G1 to G6 | Do not colour from CGM alone |
| Blood pressure | Latest home and clinic readings, 28-day home mean, goal | N1: **no band in the document** | Values and trend only, no colour |
| Lipids | TC, LDL-C, HDL-C, TG, non-HDL-C, TG/HDL-C, apoB, Lp(a), treatment status | L1 to L6 | Missing apoB or Lp(a): leave out of the rule |
| Kidney | Creatinine, eGFR, UACR | K1 to K4 | Missing UACR: show 'UACR not recorded' and do not give Green |
| Liver | ALT, AST, GGT, HSI, ultrasound, MASLD status | N2: **no band in the document** | Values and trend only, no colour |
| Physical activity | Latest IPAQ category and MET-minutes, steps (median, 30-day), sedentary hours | P1 to P3 | 'Not computed' if no IPAQ |
| Lifestyle and modifiers | Tobacco, alcohol, sleep (7-night average with source), family history, occupation pattern, PCOS, gestational history | M1 to M3 | Count only recorded modifiers |

## 5. Definitions (display conventions, not clinical rules)

- **Latest value:** the most recent value in the union of the history file and the data-year files, with its date and age in days.
- **Her baseline (lab-type series):** the median of the earlier values from the previous 24 months (at least 2 values). **Direction:** latest minus baseline; "steady" if the absolute change is at or under the tolerance below, otherwise "up" or "down".
- **Her baseline (daily series: CGM, home BP, sleep, steps, resting heart rate):** the median of the 90 days that end 28 days before the latest date, compared with the last 28 days.
- **Since diagnosis:** the latest value against the value at the diagnosis visit (2022-02-04).
- **Events around the last change:** every item dated between the previous measurement and the latest one, from medications_history (start, stop, dose change), clinic_visits_history (key_decision), imaging_reports, conditions_standing_record (diagnoses) and the diary categories healthcare_interaction and symptom. Show them as markers, never as causes.
- **Tolerances** (invented display conventions; the doctors may change them):

| Series | Steady if the change is at or under |
|---|---|
| HbA1c (%) | 0.3 |
| Fasting glucose (mg/dL) | 10 |
| Total cholesterol, LDL-C, TG (mg/dL) | 10, 8, 15 |
| HDL-C (mg/dL) | 3 |
| TG/HDL-C | 0.3 |
| eGFR | 5 |
| ALT, AST, GGT (U/L) | 5 |
| UACR (mg/g) | 5 |
| TSH (mIU/L) | 0.5 |
| Weight (kg) | 1.0 |
| BMI | 0.4 |
| Waist (cm) | 2 |
| WHR | 0.01 |
| Blood pressure (mmHg) | 5 |
| Sleep (h) | 0.5 |
| Daily steps | 15% |
| Sedentary (min a day) | 30 |
| Resting heart rate (bpm) | 3 |

## 6. Suggested review and due dates

The document's section 5 as suggestions only (rules F1 to F9). Choose the row from the goal in treatment_goals_standing_record.csv:
- HbA1c at or under goal: F4, next review by the last HbA1c date plus 6 months; above goal: F5, by the last date plus 3 months.
- eGFR and UACR: F8, yearly. Lp(a): once in adulthood (done). Lipids: show the date of the last panel; the document gives a recheck interval only after a change in therapy.
- Show "due in N days" or "overdue by N days" against the as-of date 2026-09-17.

## 7. Expected results for Meera (use these as tests; as of 2026-09-17)

| Domain | Expected signal | Why |
|---|---|---|
| Anthropometry | Red | BMI 28.16 (25 or more), waist 91.5 cm (80 or more), WHtR 0.572 (0.55 or more) [A3]; WHR 0.870 is also above 0.80 [A2] |
| Glycemia | Red | Known type 2 diabetes [G4]. HbA1c 7.4 is above her goal of 7.0; fasting glucose 138 |
| Blood pressure | No colour | Latest home 138/94, clinic 138/90, 28-day home mean 125.5/82.5; above her goal of 130/80 on the latest readings |
| Lipids | Red | TG/HDL-C 4.00 is 3.0 or higher [L3]. Also TG 180 (150 or more), HDL-C 45 (under 50), LDL-C 126 above goal 70 (Amber triggers). No lipid-lowering therapy |
| Kidney | Green | eGFR 93.7 (90 or more) and UACR 18 (under 30) [K1] |
| Liver | No colour | ALT 43, AST 32, GGT 47, HSI 42.9; grade 1 steatosis on ultrasound 2025-06-17; MASLD documented |
| Physical activity | Amber | IPAQ low (258 MET-min a week on 2026-09-17) [P2]. Five low entries in a row and 11.4 h sedentary: Red would need the doctors' definition of 'persistently', 'high' and 'deterioration' [P3, Q6] |
| Lifestyle and modifiers | Amber | Sleep 7-night average 4.94 h (under 7); mother with T2D; adverse occupational pattern; MASLD; perimenopause [M2]. Reads Red if 'multiple major modifiers with significant abnormalities' is taken literally [M3, Q10] |
| Glycemic state | Type 2 diabetes | [S4] |
| Suggested review | F5, HbA1c review by 2026-12-17 | HbA1c 7.4 against goal 7.0; no treatment change in the data year |

Baseline, direction and change since diagnosis for the main labs (the same definitions as above):

| Series | Latest date | Latest | 24-month baseline | Direction | Since diagnosis |
|---|---|---|---|---|---|
| HbA1c (%) | 2026-09-17 | 7.4 | 7.2 | steady (+0.2) | 8.0 (2022-02-04), down 0.6 |
| Fasting glucose | 2026-09-17 | 138 | 134 | steady (+4) | 162, down 24 |
| LDL-C | 2026-09-17 | 126 | 125 | steady (+1) | 140, down 14 |
| HDL-C | 2026-09-17 | 45 | 46 | steady (-1) | 44, up 1 |
| Triglycerides | 2026-09-17 | 180 | 175.5 | steady (+4.5) | 190, down 10 |
| eGFR | 2026-09-17 | 93.7 | 93.7 | steady (0) | 96.7, down 3.0 |
| ALT | 2026-09-17 | 43 | 44 | steady (-1) | 38, up 5 |
| UACR | 2026-09-17 | 18 | 13 | steady (+5, at the tolerance; 'at or under' counts as steady) | 18, unchanged |
| TSH | 2026-09-17 | 3.0 | 3.1 | steady (-0.1) | 4.2, down 1.2 |
| Weight (kg) | 2026-09-17 | 72.1 | 71.8 (61 values: weekly series and 3 history rows) | steady (+0.3) | 69.5, up 2.6 |
| Waist (cm) | 2026-09-17 | 91.5 | 90.5 (61 values) | steady (+1.0) | 86.0, up 5.5 |

## 8. Notices the tab must show

1. **HbA1c and CGM differ.** Lab HbA1c 7.0 to 7.6% against a CGM-based estimate (GMI) of 6.2 to 6.5% and 99% time in range. Fructosamine (269 to 287 umol/L) follows the CGM. Say: "Possible glycation gap: HbA1c reads higher than glucose monitoring (document reference 22)". Do not explain further.
2. **Four readings of 65.0 mg/dL are isolated sensor artifacts,** not hypoglycemia. Do not count them as events.
3. **Activity data conflict.** Wearable steps are low (median 2,106 a day) and the IPAQ is low. Do not mix in the persona's step range.
4. **Only a few lab dates exist in the data year** (five, one of them best guess). Always show the date of each value.
5. **Best-guess values** carry a badge: UACR, apoB, Lp(a), insulin and HOMA-IR, fructosamine, the interim 2026-06-17 panel, the ultrasound, the goals, the family history details and all pre-2025-09 history.

## 9. Out of scope

No risk score, no overall colour, no advice, no diagnosis, no use of the pipeline's cases, memory or evidence. No change to any existing data file.
