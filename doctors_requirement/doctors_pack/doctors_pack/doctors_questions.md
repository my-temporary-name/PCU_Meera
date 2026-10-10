# Questions for the doctors (NMG Lite view)

> **STATUS UPDATE.** Best guesses now exist in the data, so the tab no longer needs the defaults below: HbA1c goal under 7.0 (Q1), LDL-C goal under 70 (Q2), father's age at bypass 64 so not premature (Q13), IPAQ entries (Q6), UACR, apoB, Lp(a), insulin, fructosamine, ultrasound (Q9) and a mid-year panel (Q12). They are marked `synthetic_best_guess_v1`; the doctors can still replace them. Q3, Q4, Q5, Q7, Q10, Q11 and Q14 remain open.


**Purpose.** The decisions only the clinicians can make. Each has a default, so the tab can be built now and updated when you answer. Nothing below changes the pipeline.

**Why these are asked.** The document defines the bands, but several rules are ambiguous or depend on this patient (her goals, her risk category). We would rather ask than guess a clinical judgement.

| # | Question | Why it matters and what her data shows | Options |
|---|---|---|---|
| Q1 | What is Meera's HbA1c goal? | Her HbA1c was 7.1, 7.6, 7.0 and 7.4. Follow-up row F4 (every 3 to 6 months, at goal) or F5 (every 1 to 3 months, not at goal) depends on it. Metformin was last raised on 2023-06-15, so no treatment change happened in the data year. | Give a number (for example under 7.0, under 7.5 or under 8.0), or say the tab should show the HbA1c without a goal and without a follow-up row |
| Q2 | Which LDL-C goal applies, and is she 'higher cardiovascular risk'? | ADA 2026 (as quoted): under 70 mg/dL for diabetes aged 40 to 75 at higher risk, under 55 with ASCVD. Her LDL-C is 118 to 130 on no lipid-lowering drug. She has diabetes, treated hypertension, central adiposity, TG/HDL-C near 4, and a father with coronary disease (bypass 2019). | Goal under 70; goal under 55; or leave the LDL-C unscored |
| Q3 | Should blood pressure and liver have attention bands? | Section 1 lists both, but section 3 has no row for either. Her BP readings: median 125/81, last 138/94, 64% at or above 130/80, 8% at or above 140/90. ALT 39 to 45, AST 30 to 33, GGT 43 to 50, steatosis index 42.8. | Give bands; or show values and trend with no colour (my default) |
| Q4 | When anthropometry criteria disagree, does the worst signal win? Must all three Green criteria hold? | Her BMI 28.2 and waist 91.5 cm are Red; her WHR 0.87 is Amber. I assume Red wins, and that Green needs all three. | Confirm or correct |
| Q5 | Glycemia is Red for every person with known diabetes. Do you want a finer signal for her? | As written the Red carries no information for Meera, whose HbA1c is 7.0 to 7.6 and whose CGM time in range is 99%. | Keep as written; add HbA1c against her goal; or add a CGM-based line (time in range, GMI) |
| Q6 | May steps and sedentary time stand in for IPAQ, and how are 'increasing', 'persistently' and 'high' defined? | IPAQ cannot be computed. Her median is 2,106 steps a day (94% of days under 4,000) and 11.4 hours sedentary. The persona says 3,000 to 9,000 steps; the data is lower than the persona. | Allow a labelled stand-in with your thresholds; or show 'not computed' |
| Q7 | What is a 'meaningful eGFR decline'? | Her eGFR is 93.7 at all four dates. The question matters for any patient with more variation. | A rule (for example a drop of a stated size over a stated time), or leave unscored |
| Q8 | Is the wearable sleep average acceptable as the sleep source? | The document asks for a prior-7-day average 'with the source identified'. Her last 7 nights average 4.9 h, after a 3.8 h night on 17 September; her year median is 6.9 h. | Accept the synthetic wearable as the source, or require another |
| Q9 | Which gaps should be filled, and which shown as 'not recorded'? | See doctors_extras.md part B. Tests with no value: UACR, apoB, Lp(a), fasting insulin and HOMA-IR, fructosamine, liver imaging. Facts not documented: family PCOS and gestational diabetes, own PCOS and gestational history, ASCVD, heart failure. | Tick which to propose values for; the rest stay 'not recorded' |
| Q10 | What do 'marked or worsening dyslipidemia', 'persistently', and 'multiple major modifiers' mean in rules L3, M3 and P3? | The document names the idea but no threshold. | A rule for each, or leave as a clinician judgement shown without a colour |
| Q11 | Which follow-up row applies, and how should it be shown? | The document says these are suggestions. I would show 'Suggested review: ...' next to the row and never as a decision or an alert. | Confirm the wording and the row (depends on Q1) |
| Q12 | How should the HbA1c against CGM discordance be shown? | Over 90 days her GMI is 6.48, 6.45 and 6.18 against HbA1c 7.6, 7.0 and 7.4 (gaps +1.12, +0.55, +1.22), with 99% time in range. This comes from how the synthetic labs and the CGM were generated, not from a clinical story. Your section 4 says discordance is a reason to consider fructosamine or glycated albumin. | Show as discordance (and propose fructosamine values, see extras B5); show without comment; or ask us to regenerate the labs |
| Q13 | Her father's coronary artery disease: was it premature? | The persona says bypass surgery in 2019 but not his age. 'Premature' means a male relative under 55 (as usually defined). | Give his age, or leave the field as 'age not stated' |
| Q14 | Name and wording of the tab and its on-screen statement. | The letter says the signals are not diagnostic criteria and not a validated composite risk score. I would show that sentence at the top of the tab, and name it 'NMG Lite view'. | Approve or edit the wording |

## Defaults if you do not answer

| Question | Default |
|---|---|
| Q1 HbA1c goal | None; show HbA1c and no follow-up row |
| Q2 LDL-C goal | Leave LDL-C unscored; show TG/HDL-C and TG and HDL-C per the document |
| Q3 BP and liver | Values and trend, no colour |
| Q4 precedence | Worst signal wins |
| Q5 glycemia | Red as written, with the CGM line beside it |
| Q6 activity | 'Not computed'; show steps and sedentary time as plain values |
| Q7, Q10 | Unscored |
| Q8 sleep | Accept the wearable source, labelled |
| Q9 gaps | All shown as 'not recorded' |
| Q11 follow-up | Not shown |
| Q12 discordance | Shown as discordance, no extra values |
| Q13 | 'Age not stated' |
| Q14 | 'NMG Lite view', with the letter's sentence on screen |
