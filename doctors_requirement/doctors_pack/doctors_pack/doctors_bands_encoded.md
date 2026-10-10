# NMG Lite attention bands, encoded for the doctors' tab

**Purpose.** Every rule the tab would apply, in plain words, so the doctors can check it before it goes in the page. Source: NMG Lite Version 1 (Dr. Vishal Bhatia and Dr. Ruchi Bhatia, October 2026). Bracketed numbers point to the document's own reference list [1] to [28]. The document brackets only some statements; where it does not, the number is **my mapping** from the source it names (for example "ADA 2026" to [1] to [6], "KDIGO" to [19], "ICMR-INDIAB" to [9][10]) and should be confirmed by the doctors. I have not independently verified the 2026 guidelines; the document is the source of truth.

**Two kinds of rule, kept apart.**
- **G, guideline threshold:** a cutoff taken from a cited guideline or consensus.
- **B, NMG Lite operational band:** a clinician-defined attention band. The document says these are not diagnostic criteria and not a validated composite risk score. The tab must say so on screen.
- **F, formula; D, definition or state; S, suggestion** (follow-up).

**Rules the tab must follow (from the document).**
1. Green, Amber and Red are domain-specific. Never combine them into one overall colour.
2. Keep absolute values, treatment status, repeated values and the trend visible beside any colour.
3. For every core variable show four things: current value or state, comparison with her own baseline, direction of change, and the treatment, behaviour, illness or events around the change.
4. Follow-up is driven by clinical stability, treatment change, symptoms and organ risk, not by colour alone.

## Rules

| ID | Domain | Signal | Rule | Variables | Kind | Refs | Note or decision needed |
|---|---|---|---|---|---|---|---|
| A1 | Anthropometry | Green | BMI under 23, and WHtR under 0.50, and WHR at or under 0.90 (men) or 0.80 (women) | BMI, WHtR, WHR, sex | B | [9][12][13][28] | Document lists the three together; read as all three must hold. Confirm (Q4) |
| A2 | Anthropometry | Amber | BMI 23 to 24.9, and/or WHtR 0.50 to 0.54, and/or WHR above the sex-specific threshold | BMI, WHtR, WHR | B | [2][3][12][13][28] | BMI 23 is the ADA Asian-ancestry screening threshold when other risk factors exist |
| A3 | Anthropometry | Red | BMI at or above 25, and/or waist at or above 90 cm (men) or 80 cm (women), and/or WHtR at or above 0.55 | BMI, waist, WHtR | G | [9][10][12][13][28] | ICMR-INDIAB definitions for BMI and waist |
| A4 | Anthropometry | Rule | When criteria disagree, the worst signal wins (Red over Amber over Green) | all of the above | B | none | My assumption; not stated in the document. Confirm (Q4) |
| A5 | Anthropometry | How to measure | Waist at the midpoint between the last palpable rib and the top of the iliac crest, snug tape, after normal expiration; hip at the widest point over the buttocks; BMI = kg/m2; WHR = waist/hip; WHtR = waist/height | waist, hip, height | F | [11] | Meera's values are a synthetic wearable and scale record; the method is not recorded |
| G1 | Glycemia | Green | FPG under 100 mg/dL and HbA1c under 5.7% | FPG, HbA1c | G | [1] |  |
| G2 | Glycemia | Amber | ADA prediabetes range: FPG 100 to 125, and/or HbA1c 5.7 to 6.4, and/or 2-hour OGTT glucose 140 to 199 | FPG, HbA1c, OGTT | G | [1] |  |
| G3 | Glycemia | Amber (higher attention) | Within prediabetes: FPG at or above 110 and/or HbA1c at or above 6.0. These are attention values, not separate ADA thresholds | FPG, HbA1c | B | [1] |  |
| G4 | Glycemia | Red | Known diabetes, or an ADA diabetes-range result needing confirmation: FPG at or above 126, HbA1c at or above 6.5, or OGTT 2-hour at or above 200 | diagnosis, FPG, HbA1c | G | [1] | For anyone with known diabetes this is always Red, so it carries no information for Meera (Q5) |
| G5 | Glycemia | Rule | Diagnosis without unequivocal hyperglycemia needs two abnormal results (the same test repeated or two different tests) | labs | G | [1] | Not needed for Meera: diagnosis is established |
| G6 | Glycemia | Rule | An ordinary postprandial glucose is not the OGTT 2-hour value. CGM data may be surfaced when the clinical question needs detail | CGM, meals | D | [1][4] | Label every derived 2-hour value as 'from CGM, not OGTT' |
| L1 | Lipids | Green | TG under 150; HDL-C not low (low = under 40 men, under 50 women); TG/HDL-C under 2.0; LDL-C at the individual risk-based goal | TG, HDL-C, LDL-C | B | [5][9][25] | The LDL goal is individual and not in the document (Q2) |
| L2 | Lipids | Amber | TG at or above 150 and/or low HDL-C; TG/HDL-C 2.0 to under 3.0; LDL-C above the individual goal and/or raised non-HDL-C or apoB | TG, HDL-C, LDL-C, non-HDL-C, apoB | B | [5][9][25] | TG/HDL-C bands are operational attention bands, not validated cutoffs |
| L3 | Lipids | Red | Marked or worsening dyslipidemia; TG/HDL-C at or above 3.0; LDL-C persistently above the goal despite appropriate management; other significant atherogenic burden | TG/HDL-C, LDL-C, treatment | B | [8][16][25] | 3.0 is the McLaughlin cut point (64% sensitivity, 68% specificity in one cohort). 'Marked' and 'worsening' are undefined (Q10) |
| L4 | Lipids | Reference | ADA 2026 LDL-C goal: under 70 mg/dL for diabetes aged 40 to 75 at higher cardiovascular risk; under 55 with established ASCVD | LDL-C, risk category | G | [5][25][26] | Whether Meera is 'higher risk' is a doctor's decision (Q2) |
| L5 | Lipids | Reference | Lp(a) at or above 125 nmol/L or 50 mg/dL is risk-enhancing; measure at least once in adulthood; not serially monitored | Lp(a) | G | [25][26] | No Lp(a) for Meera |
| L6 | Lipids | Formula | non-HDL-C = total cholesterol minus HDL-C; TG/HDL-C = TG / HDL-C in mg/dL | lipids | F | [8] |  |
| K1 | Kidney | Green | UACR under 30 mg/g; eGFR at or above 90, or 60 to 89 without another kidney-damage marker | UACR, eGFR | G | [6][19] | UACR missing for Meera |
| K2 | Kidney | Amber | Persistent UACR 30 to 299 and/or meaningful eGFR decline | UACR, eGFR trend | B | [6][19] | 'Meaningful decline' is undefined (Q7) |
| K3 | Kidney | Red | eGFR under 60 and/or UACR at or above 300, especially persistent or progressive | UACR, eGFR | G | [6][19] |  |
| K4 | Kidney | Rule | CKD needs abnormal structure or function for at least 3 months. Albuminuria A1 under 30, A2 30 to 299, A3 at or above 300 mg/g. eGFR 60 to 89 alone does not establish CKD | eGFR, UACR | G | [19] |  |
| P1 | Physical activity | Green | IPAQ moderate or high category (official frequency, duration and MET-minutes per week criteria) | IPAQ | G | [18] | No IPAQ for Meera (Q6) |
| P2 | Physical activity | Amber | IPAQ low category and/or increasing sedentary time | IPAQ, sedentary time trend | B | [18] | 'Increasing' is undefined (Q6) |
| P3 | Physical activity | Red | Persistently low activity with high sedentary exposure plus metabolic deterioration | IPAQ, sedentary time, metabolic trend | B | none | All three parts undefined (Q6) |
| M1 | Lifestyle and modifiers | Green | No tobacco; adequate sleep duration (at least 7 hours); no major modifier identified | tobacco, sleep | B | [17] |  |
| M2 | Lifestyle and modifiers | Amber | Tobacco or substance exposure, sleep under 7 hours, strong family history, PCOS, prior gestational diabetes, adverse occupational pattern, or another relevant modifier | modifiers | B | [17] | Sleep: average nightly duration, preferably over the prior 7 days, with the source identified |
| M3 | Lifestyle and modifiers | Red | Multiple major modifiers occurring with significant metabolic or organ abnormalities | modifiers, organ domains | B | none | Undefined: what counts as 'multiple' and 'major' (Q10) |
| N1 | Blood pressure | No band | Section 1 says to use standardized seated measurements and interpret with current hypertension guidance; treatment-dependent control stays visible. Section 3 has no Green, Amber or Red row | systolic, diastolic, treatment | D | none | Needs a decision (Q3) |
| N2 | Liver | No band | Section 1: keep the ALT and AST trend and any documented imaging or diagnosis. MASLD needs documented steatosis plus one cardiometabolic risk factor; abnormal ALT or AST alone does not establish it. Section 3 has no row | ALT, AST, imaging | D | [20] | Needs a decision (Q3) |
| S1 | Glycemic state | State | Lower metabolic risk: no major risk factor and glycemia below the prediabetes range | glycemia, risk factors | D | [1][2] |  |
| S2 | Glycemic state | State | Increased metabolic risk: normal glycemia with central adiposity or overweight, family history, hypertension, dyslipidemia, inactivity, PCOS, MASLD, CVD or other insulin-resistance features. A metabolic-risk state, not prediabetes | risk factors | D | [2][3] |  |
| S3 | Glycemic state | State | Prediabetes: HbA1c 5.7 to 6.4, FPG 100 to 125 or 2-hour OGTT 140 to 199 | glycemia | G | [1] |  |
| S4 | Glycemic state | State | Type 2 diabetes: established or new by ADA criteria, then described by treatment, glycemic trajectory, complications and organ involvement. This is Meera's state | diagnosis | G | [1] | Diagnosed 2022-02-04 (persona) |
| X1 | Extra detail | Formula | Estimated HbA1c (%) = 0.017 x fructosamine (umol/L) + 1.61. An HbA1c equivalent, not an ADA diagnostic conversion; does not replace a reliable HbA1c | fructosamine | F | [22] |  |
| X2 | Extra detail | Reference | Fructosamine reference interval depends on the assay: Mayo 200 to 285 umol/L; ARIC community sample 194.8 to 258.0. Use the reporting laboratory's interval | fructosamine | G | [14][15] | Reflects about the last 2 to 4 weeks of glycemia |
| X3 | Extra detail | Formula | HOMA1-IR = fasting insulin (uU/mL) x fasting glucose (mg/dL) / 405, or x glucose (mmol/L) / 22.5. No universal cutoff: keep fasting glucose, insulin, assay context and the value | insulin, FPG | F | [7][16] | Do not hard-code a threshold. The South Indian 1.23 is a population example only |
| X4 | Extra detail | Definition | PCOS (adults): at least two of hyperandrogenism, ovulatory dysfunction, polycystic ovarian morphology (or AMH) after excluding other causes | PCOS features | D | [27] |  |
| X5 | Extra detail | Principle | TG/HDL-C describes an insulin-resistant phenotype. LDL-C, non-HDL-C, apoB and Lp(a) describe atherogenic particle burden. The two are complementary, not interchangeable | lipids | D | [5][25][26] |  |

## Follow-up and reassessment (section 5), as suggestions

The document says these are suggested contact intervals, not ADA mandates. The tab would show the row that applies as a suggestion only, and only after the doctors say which row applies to Meera (Q1, Q11).

| ID | Clinical situation | Suggested clinical follow-up | Reassessment logic | Refs |
|---|---|---|---|---|
| F1 | Lower metabolic risk, normal screening | Routine preventive care | Repeat diabetes screening at least every 3 years, sooner if risk changes | [1][2] |
| F2 | Increased metabolic risk without prediabetes | About every 6 to 12 months; sooner if worsening | Reassess weight and waist, blood pressure, lifestyle and metabolic tests by individual risk | [2] |
| F3 | Prediabetes | About every 6 to 12 months; consider 3 to 6 months if very high risk or changing fast | Test for progression to diabetes at least yearly | [2] |
| F4 | Stable type 2 diabetes at individual goals | About every 3 to 6 months | Assess glycemic status at least twice a year when stable and at goal; HbA1c reflects about 2 to 3 months | [1][4] |
| F5 | Type 2 diabetes not at goal, or recent treatment change | About every 1 to 3 months, sooner when needed | Assess glycemic status more often, for example every 3 months, after treatment change, goals not met, frequent or severe hypo- or hyperglycemia, or health change | [4] |
| F6 | Medication start or titration, insulin adjustment, symptomatic hyperglycemia, recurrent hypoglycemia, acute illness, adherence concern | Days to 2 to 4 weeks by urgency; weekly during active titration or safety concern | Targeted glucose, CGM, blood pressure, renal function or electrolyte monitoring by therapy | [4] |
| F7 | Lipid-lowering therapy started or changed | By cardiovascular risk, treatment intensity, response and tolerability | Recheck lipids 4 to 12 weeks after a change, then yearly when stable; Lp(a) once in adulthood | [25] |
| F8 | Diabetes without established CKD | Routine diabetes follow-up | eGFR and UACR at least yearly in all people with type 2 diabetes | [6] |
| F9 | Established CKD | By eGFR, albuminuria and progression risk | eGFR and UACR 1 to 4 times a year by stage; highest risk every 1 to 3 months | [6][19] |

**Which row applies to Meera** depends on whether she is "at individualized goals". Her HbA1c was 7.1, 7.6, 7.0 and 7.4. No treatment change happened in the data year (metformin was last raised on 2023-06-15). So the answer is F4 if her goal is above about 7.4, and F5 if it is 7.0 or lower. Only the doctors can say (Q1).

## What this file does not contain

- No Green, Amber or Red for blood pressure or liver (the document has none).
- No threshold for HOMA-IR, and no numeric weights for a risk score (section 8 of the document: the future score must be learned from Indian longitudinal data).
- No rule I invented. Where the document is ambiguous the "Note" column says so and points to a question in doctors_questions.md.
