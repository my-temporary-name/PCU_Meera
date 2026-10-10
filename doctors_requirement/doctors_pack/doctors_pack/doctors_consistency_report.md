# Consistency report for the doctors' extra data

Checks run on the new files after creation. Everything new was created additively; the existing files were only read.

| Check | Result | Passed |
|---|---|---|
| eGFR (history) = CKD-EPI 2021, female, at her age on each date | 9 panels; includes a one-visit dip to 82.9 when creatinine was 0.9 on 2023-06-12 | yes |
| HOMA1-IR = insulin x fasting glucose / 405 | 5 dates | yes |
| Fasting glucose used for HOMA matches the existing lab file on its 4 dates | 132, 145, 128, 138 | yes |
| TG/HDL-C in the history lipids | 2.96 to 4.32; 3.0 or higher at every panel from diagnosis | yes |
| Fructosamine through the document's own formula (HbA1c = 0.017 x F + 1.61) gives an HbA1c equivalent close to the CGM GMI, not the lab HbA1c | 6.18 to 6.49 against lab HbA1c 7.0 to 7.6 | yes |
| Medicines start after their diagnoses; metformin 500 mg ends the day before 1000 mg starts | levothyroxine 2021-11-01 after 2021-10-12; metformin 2022-02-10 after 2022-02-04; amlodipine 2023-01-20 = hypertension date; 1000 mg 2023-06-15 after the 2023-06-12 visit | yes |
| Age on the reference date | 43 = age_fact.csv | yes |
| BMI, WHR and WHtR recompute from weight, waist, hip and height | 11 rows | yes |
| Continuity into the data year: 2025-06-17 (71.0 kg, waist 88.2, hip 103.6) to 2025-10-01 (71.4, 88.9, 103.8) | +0.4 kg, +0.7 cm, +0.2 cm | yes |
| BMI on 2025-06-17 against the persona's 27.7 early in the year | 27.73 | yes |
| HbA1c path across history and data year: 7.2 (2025-06) then 7.1, 7.6, 7.0, 7.2, 7.4 | no step above 0.6 | yes |
| Lipids and liver enzymes continue from 2025-03/06 into the data year | LDL 126 to 124; TG 176 to 175; ALT 46 to 45 | yes |
| No new test repeats an existing lab (date, type) | 0 overlaps | yes |
| IPAQ categories follow the official criteria and match the wearable (median 2,106 steps a day, 11.4 h sedentary) | low, low, low, low, low | yes |
| HbA1c on every clinic visit equals the lab value of that date | 17 visits | yes |
| TSH 4.7 on 2026-06-17 (mildly above 4.5), as the persona intends | 4.7 mIU/L | yes |
| Existing dataset files unchanged (read only) | glucose_stream_yearly.csv md5 508468f1 (the correct copy, 508468f1); lab_panels_yearly.csv md5 e8c9ffaa | yes |

All 17 checks pass. They show the new data agrees with its own formulas and with the persona; they do not make it clinically true.

## Inconsistencies that remain, deliberately

| Item | What differs | What was done |
|---|---|---|
| HbA1c against CGM | Labs 7.0 to 7.6; CGM GMI 6.2 to 6.5; time in range 99.25% | Kept, and now explained: fructosamine is set concordant with the CGM (a 'glycation gap', document reference [22]). A clinician will still see the gap |
| Steps | Persona 3,000 to 9,000 a day; data median 2,106 | Not changed. IPAQ is set to 'low' to agree with the wearable |
| Hypoglycemia | None real; four isolated 65.0 artifacts | Not changed. The tab must not count them |
| Home blood pressure | Persona 128 to 142 / 82 to 90; data median 125/81 | Not changed. Clinic readings are a little higher, as clinic readings usually are |
| eGFR in the data year | 93.7 on all four dates; equation gives 94.3 at age 42 | Not changed |
| Medicine id med_001 | Unused in adherence_yearly.csv | medications_history.csv records the 500 mg dose as the superseded one |
| Alcohol entries | 6 diary entries between 25 Dec and 14 Feb; persona says 1 to 2 a month | Not changed |
| Weight at the reference date | Persona 73.5 kg; data 72.1 kg | Not changed |

## What a reviewer should look at first

1. The invented clinical statements: MASLD on ultrasound (2025-06-17), the father's age at bypass (64, so not premature), the treatment goals, Lp(a) 48 nmol/L, UACR 14 and 18 mg/g, and the fructosamine story.
2. Whether a clinic visit history from 2021 is wanted at all; it is there for the doctors' request to show 'treatment context and response to intervention'.
