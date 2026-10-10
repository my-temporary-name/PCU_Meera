# Extras for the doctors' tab: persona facts, proposed new values, and inconsistencies

> **SUPERSEDED.** Part B's proposals are now real files in `doctors_data/` (see doctors_data_dictionary.md and doctors_variable_map_v2.md). Part A (persona facts) and Part D (inconsistencies) still hold; Part D is repeated in doctors_consistency_report.md.


**Purpose.** What the doctors' framework needs that the dataset files do not hold. It has three parts and a list of problems.

**Rules.** Nothing here edits an existing file or touches the pipeline. Part A is **extracted** from the persona document (pre_requisit.zip, Realistic_Persona_Meera.md); nothing is invented. Part B is **proposed synthetic values**, each marked PROPOSED, to be accepted, changed or dropped by the doctors. Anything accepted goes in a separate file and is labelled synthetic on the page.

## Part A. Facts already in the persona (no invention)

| Item | Fact | Persona section |
|---|---|---|
| Type 2 diabetes | Diagnosed 2022-02-04 (about 4.5 years before the reference date), found on a routine check after unexplained fatigue and a family-history flag | 2 |
| Hypertension (moderate) | Diagnosed 2023; medicated | 2 |
| Subclinical hypothyroidism | Diagnosed 2021 (before the diabetes); managed | 2 |
| Mild anxiety | Self-reported, intermittent, not formally diagnosed | 2 |
| Reproductive stage | Perimenopausal since about early 2025; menopause_status = peri throughout the year; irregular cycles of 24 to 45 days with some anovulatory months | 2b |
| Management stage | Oral medication, dose adjusted once; a borderline candidate for a second agent if control does not improve | 2 |
| Allergy | Sulfa drugs (rash), confirmed 2019-04-02 (allergies_standing_record.csv) | 2 |
| Family history | Mother: Type 2 diabetes, diagnosed at 58. Father: hypertension and coronary artery disease, bypass surgery in 2019 (his age is not stated) | 2 |
| Tobacco | No smoking | 7 |
| Alcohol | Occasional social alcohol (wine or beer), about 1 to 2 times a month, rising slightly in stressful periods | 7 |
| Caffeine | Occasional dependency: 3 to 4 cups a day in stressful periods | 7 |
| Occupation and family | Finance Manager at a mid-size manufacturing company; full-time; quarter-end cycles; 2 to 3 trips a quarter. Married, two children (12 and 15); ageing parents nearby with occasional caregiving | 1 |
| Usual sleep and screen | Sleep generally 5.5 to 6.5 h, worse in quarter-close; screen time 7 to 9 h a day | 7 |
| Adherence intent | About 75 to 80% overall, with several imperfect periods; occasional missed refills | 3 |

**Medicines** (persona section 3):

| Medicine | Dose | Frequency | Start date | Note |
|---|---|---|---|---|
| Metformin | 500 mg | twice daily | 2022-02-10 | Initial. Presumably the unused id med_001 (to confirm) |
| Metformin | 1,000 mg | twice daily | 2023-06-15 | Dose raised after a suboptimal HbA1c. Data id med_002 |
| Amlodipine | 5 mg | once daily | 2023-01-20 | Blood pressure. Data id med_003 |
| Levothyroxine | 50 mcg | once daily | 2021-11-01 | Thyroid. Data id med_004 |

**Treatment history:** the only change in the last four years is the metformin increase on 2023-06-15. No treatment change happens in the data year (2025-10-01 to 2026-09-17).

## Part B. Proposed synthetic values (PROPOSED, not in any file)

Dates reuse the four existing lab dates (2025-09-15, 2025-12-18, 2026-03-06, 2026-09-17) so they line up with the labs already there.

| # | Item | Proposed value | Why this value | Consistency checked against | Refs |
|---|---|---|---|---|---|
| B1 | UACR (mg/g) | 2025-09-15: 14; 2026-09-17: 18 | Two values, since the document asks for UACR at least yearly. Both are under 30 (category A1). A small rise matches the drift in blood pressure and weight. | eGFR 93.7 at every date; treated hypertension; 4.5 years of diabetes; no albuminuria documented | [6][19] |
| B2 | apoB (mg/dL) | 2025-09-15: 100; 2025-12-18: 106; 2026-03-06: 95; 2026-09-17: 101 | About 0.63 x her non-HDL-C (159, 168, 151, 161), so it moves with her lipid panels. The document gives no apoB cutoff | LDL-C 118 to 130; TG 162 to 195; no lipid-lowering therapy | [5][25] |
| B3 | Lp(a) (nmol/L) | 2026-03-06: 48 | One value (the document says measure once in adulthood). Below the risk-enhancing level of 125 nmol/L (about 50 mg/dL). The alternative, a high value, would fit her father's coronary disease but is a bigger clinical statement | Father's CAD (bypass 2019); no other lipid disease | [25][26] |
| B4 | Fasting insulin (uU/mL) and HOMA1-IR | Insulin 14.0, 17.0, 12.5, 15.0; HOMA1-IR 4.56, 6.09, 3.95, 5.11 | Insulin moves with her fasting glucose (132, 145, 128, 138). HOMA1-IR = insulin x glucose (mg/dL) / 405. The document sets no cutoff, so the tab shows values only | BMI 28; TG/HDL-C 3.5 to 4.4; on metformin | [7][16] |
| B5 | Fructosamine (umol/L) | No default. Option 1: not recorded. Option 2, concordant with HbA1c: 2025-09-15 323, 2025-12-18 352, 2026-03-06 317, 2026-09-17 341. Option 3, concordant with the CGM: 2025-12-18 286, 2026-03-06 285, 2026-09-17 269 | Uses the document's own formula, HbA1c = 0.017 x fructosamine + 1.61, run backwards. Option 3 would put fructosamine at or just under the top of the Mayo interval (200 to 285) while HbA1c is high, which shows the discordance the document's section 4 describes | HbA1c 7.0 to 7.6 against CGM GMI 6.2 to 6.5 | [14][15][22] |
| B6 | Liver imaging and steatosis | Option 1: not recorded (default). Option 2: abdominal ultrasound on 2026-03-06 reports mild (grade 1) hepatic steatosis; with type 2 diabetes and overweight this meets the document's MASLD definition | Option 2 agrees with the steatosis index (42.8, above the usual 36 threshold), ALT 39 to 45 and GGT 43 to 50, BMI 28, and only occasional alcohol. It adds a diagnosis (MASLD), so it is a clinical statement the doctors must accept | HSI 42.8; mildly raised ALT and GGT; alcohol 1 to 2 times a month | [20] |

All values above are plausible, not verified against real patients. They are consistent with the existing labs and the persona; they are not clinical findings.

## Part C. Deliberately not invented

| Item | Reason |
|---|---|
| IPAQ | Not invented. It needs days, duration and intensity of activity that no file holds. See Q6 |
| HbA1c goal, LDL-C goal, risk category, follow-up row | The doctors' decisions (Q1, Q2, Q11) |
| Premature CVD in the family | Needs the father's age (Q13) |
| Own and family PCOS, own and family gestational diabetes, inherited factors, ASCVD, heart failure | Not documented in the persona. Record as 'not documented', not as 'none'. If the doctors want 'none', they should say so |
| Blood pressure and liver bands | Not in the document (Q3) |

## Part D. Inconsistencies already in the data or persona

The tab will show these to a careful reader. We list them so the doctors are not surprised and so nobody fixes them silently.

| Item | Persona or plan says | Data shows | Effect |
|---|---|---|---|
| Steps | Persona: 3,000 to 4,000 a day in heavy weeks and 7,000 to 9,000 in lighter ones | Data: median 2,106; 94% of days under 4,000; 1.8% at or above 7,000; maximum 8,385 | The data is much lower than the persona. Affects the activity row |
| Weight, BMI, waist at the reference date | Persona: 73.5 kg, BMI 28.7, waist 92 cm | Data: 72.1 kg, BMI 28.16, waist 91.5 cm | Small; same direction |
| Blood pressure | Persona: about 128 to 142 / 82 to 90 | Data: median 125/81, range 108 to 152 / 70 to 94 | Data is lower and wider |
| TSH | Persona: one mildly out-of-range reading mid-year | Data: 2.7, 3.2, 2.9, 3.0 on four dates, none out of range; no mid-year panel | The out-of-range reading was never generated |
| HbA1c against CGM | Labs 7.0 to 7.6 | CGM GMI 6.18 to 6.48; time in range 99.25% | The labs and the CGM were generated separately. See Q12 |
| Hypoglycemia | The recipe planned one real day below 70 mg/dL | The only values below 70 are four isolated 65.0 artifacts; the planned 2026-08-22 low reads 76.3 | No real hypoglycemia exists in the data |
| eGFR | Creatinine 0.8 stable | eGFR 93.7 at all four dates; the equation gives 94.3 at age 42 | Trivial |
| Alcohol | Persona: 1 to 2 times a month | Diary: 6 entries, all between 25 Dec and 14 Feb | Fewer than the persona and clustered |
| Medicine ids | Persona lists metformin twice (500 mg, then 1,000 mg) | Data uses med_002 to med_004; med_001 is unused | Probably the superseded 500 mg dose |
| Sleep | Persona: generally 5.5 to 6.5 h | Data: mean 6.68 h, median 6.9 h | Data is a little higher |

## Part E. What we would put on the page if nothing is accepted

Every Part B item shows as "not recorded in this synthetic record". Part A items show as recorded facts with their source ("persona document"). Part D items stay as they are.
