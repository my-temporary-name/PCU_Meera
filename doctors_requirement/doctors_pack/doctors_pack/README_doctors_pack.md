# Doctors' pack: what is here and what to give Claude Code

The doctors' NMG Lite framework (their submission of October 2026) needs data we did not have. This pack creates it and tells Claude Code how to build the tab. It does not use the pipeline.

## Data (doctors_data/): 12 CSV files, 231 rows, all new, nothing existing edited

- `anthropometry_history.csv`: 11 rows
- `bp_clinic_history.csv`: 18 rows
- `clinic_visits_history.csv`: 17 rows
- `conditions_standing_record.csv`: 14 rows
- `family_history_standing_record.csv`: 7 rows
- `imaging_reports.csv`: 2 rows
- `ipaq_short_quarterly.csv`: 5 rows
- `labs_additional_2025_2026.csv`: 36 rows
- `labs_history_2021_2025.csv`: 95 rows
- `lifestyle_standing_record.csv`: 10 rows
- `medications_history.csv`: 7 rows
- `treatment_goals_standing_record.csv`: 9 rows
- `make_doctors_data.py`: the script that creates them (fixed values, no randomness)

Every row has a `source`: `persona_document` (stated in the persona) or `synthetic_best_guess_v1` (invented, no doctor has reviewed it).

## Guidance (doctors_pack/)

| File | Use |
|---|---|
| `doctors_tab_spec.md` | **Start here.** Layout, rules per domain, definitions, expected results for Meera, notices |
| `doctors_data_dictionary.md` | Columns, units, provenance and joins for the 12 new files |
| `doctors_bands_encoded.md` | The doctors' 38 rules with IDs (A1, G4, L3, K1 and so on) and the follow-up table |
| `doctors_variable_map_v2.md` | All 54 variables with Meera's value, source file and provenance |
| `doctors_derived_values.md` | Formulas and check values from the existing data (CGM, labs, steps, BP) |
| `doctors_consistency_report.md` | 17 checks on the new data and the problems that remain on purpose |
| `doctors_questions.md` | The doctors' open decisions (several now have a best guess) |
| superseded: `doctors_variable_map.md`, `doctors_extras.md` | Kept for history |

## What to give Claude Code

Copy `doctors_data/` and `doctors_pack/` next to the existing `final/` folder, then:

```
Build the NMG Lite view (a new tab in the dashboard) from doctors_pack/doctors_tab_spec.md.
Read the other files in doctors_pack/ as the spec refers to them. Use only the CSV files in final/ and doctors_data/; do not use the pipeline databases for this tab.
Do not change any file in final/ or doctors_data/. Recompute the check values in doctors_derived_values.md and the expected results in section 7 of the spec, and report any difference before showing the tab.
Show the sentence from section 1 of the spec at the top, a provenance badge on every best-guess or persona value, and the notices in section 8.
```
