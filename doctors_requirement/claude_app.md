## The picture in four lines

- **What we're building:** a new tab in the dashboard, the "NMG Lite view", for the doctors. It's the doctors' framework applied to Meera's data.
- **How it works:** inputs, then fixed rules, then display. No pipeline, no model, no explanation step.
- **What it shows per domain:** the latest value, a Green, Amber or Red signal (never one overall colour), her trend and change since diagnosis, the events around the change, and a suggested review date.
- **Claude Code's job:** read the CSVs, implement the rules, draw the tab, and prove it matches the expected results for Meera.

## 1. Inputs

**Existing files** (`final/`, read only, 19 files):

| For | Files |
|---|---|
| Glucose | `glucose_stream_yearly.csv` (the correct copy, md5 508468f1), `meal_events_yearly.csv` |
| Labs | `lab_panels_yearly.csv`, `hba1c_full_year.csv`, `lipid_panel_full_year.csv`, `renal_panel_full_year.csv`, `hepatic_panel_full_year.csv` |
| Body | `bmi_full_year.csv`, `waist_hip_ratio_full_year.csv`, `weight_yearly.csv` |
| Vitals and lifestyle | `vitals_yearly.csv`, `sleep_yearly.csv`, `steps_hourly_yearly.csv`, `sedentary_time_full_year.csv`, `adherence_yearly.csv` |
| Context and identity | `context_events_yearly.csv` (diary), `age_fact.csv`, `sex_fact.csv`, `allergies_standing_record.csv` |

**New files** (`doctors_data/`, 12 files, 231 rows): `labs_history_2021_2025`, `labs_additional_2025_2026`, `anthropometry_history`, `bp_clinic_history`, `clinic_visits_history`, `conditions_standing_record`, `medications_history`, `family_history_standing_record`, `lifestyle_standing_record`, `treatment_goals_standing_record`, `imaging_reports`, `ipaq_short_quarterly`.

**Not used:** the pipeline databases (State, Evidence, Findings, PI, Baseline) and the first dashboard's tabs. This tab does not touch them.

## 2. Rules

| Where | What it contains |
|---|---|
| `doctors_bands_encoded.md` | The **38 band rules** with IDs (A1 to X5): Green, Amber and Red per domain, glycemic states, formulas, and the **9 follow-up rows**. Marks each as a guideline cutoff or an NMG Lite operational band, with references. |
| `doctors_tab_spec.md` | **Display rules**: layout, which rules apply to each domain, what to do when data is missing, definitions of baseline, direction, "since diagnosis", "events around the change" and "due", the tolerance table, the on-screen sentence and notices, and **expected results for Meera**. |
| `doctors_derived_values.md` | Formulas and conventions (CGM cleaning, GMI, eGFR, TG/HDL) with check values. |
| `doctors_data_dictionary.md` | Columns, units, provenance and how the new files join the existing ones. |
| `doctors_variable_map_v2.md` | Each of the 54 variables with its source file and Meera's value. |
| The doctors' own document | The source of truth if Claude Code doubts a rule. |

**Rules that exist in no file, with the default I set:**

| Gap | Default |
|---|---|
| Blood pressure and liver have no bands in the document | Show values and trend, no colour |
| When criteria disagree | Worst signal wins |
| "Persistently", "high", "multiple major modifiers", "meaningful decline" | Not scored as Red; shown as Amber with a note |
| Direction tolerances | My table (a display convention) |
| Goals (HbA1c, LDL-C, BP) | The best-guess rows in `treatment_goals_standing_record.csv` |
| IPAQ | The IPAQ file, all "low" |

## 3. What Claude Code does

1. Copies the two folders next to `final/`.
2. Loads and joins the CSVs: the history and the data year become one series per lab.
3. Implements the rules in the page code with their IDs, so every colour traces to a rule.
4. Builds the header strip, the domain board, the domain drawer with trends and event markers, the follow-up panel and the notices.
5. Recomputes the check values in `doctors_derived_values.md` and the expected results in section 7 of the spec, and **reports any difference before showing the tab**.
6. Adds the on-screen sentence ("not diagnostic criteria, not a composite risk score") and a "persona" or "best guess" badge on the right values.

It does not change any existing file, use the pipeline, compute a risk score or add an overall colour.

## 4. The brief to paste

```
We are adding one tab to our dashboard: the "NMG Lite view" for doctors. It applies the clinicians' NMG Lite framework (Dr. V. Bhatia and Dr. R. Bhatia, October 2026) to one synthetic patient, Meera Iyer. It is inputs, then fixed rules, then display: no model, no learning, and nothing from the pipeline databases.

Target: <path or repo of the dashboard to add the tab to>.
Read first: doctors_pack/README_doctors_pack.md, then doctors_tab_spec.md.
Inputs: the 19 CSV files in final/ and the 12 CSV files in doctors_data/ (listed in doctors_pack/doctors_tab_spec.md section 2 and doctors_data_dictionary.md). Do not modify any of them.
Rules: doctors_bands_encoded.md (rule IDs), the definitions in the spec, formulas in doctors_derived_values.md.

Do this:
1. Implement the rules with their IDs, so every colour can be traced to a rule.
2. Build the header strip, domain board, domain drawer, follow-up panel and notices as in the spec.
3. Never show an overall colour. Show the on-screen sentence from spec section 1. Show provenance badges.
4. Before showing the tab, recompute the check values in doctors_derived_values.md and the expected results in spec section 7 and report every difference.
5. Where the spec says no band or undefined, follow the default in the spec and list those places in your report.

Stop after the report. Do not start other work.
```

## Two things I need from you before you send it

- **Which dashboard is the target?** My published page (I can give you the HTML file) or the `github.io/PCU_Meera` one, whose source I haven't seen. That fills the `Target:` line.
- **The folders must sit where Claude Code can read them.** The zip has `doctors_data/` and `doctors_pack/` already arranged.

## Caveat

I haven't built the tab, so the expected results are my reading of the rules. That's why the brief makes Claude Code check them and report differences before showing anything.