Here's the exact file list to hand off alongside the task document, split by role.

## Reference files (the rules — pass these regardless)
- `plausibility_bounds.csv`
- `threshold_ranges_full.csv`
- `age_fact.csv`
- `sex_fact.csv`

## Data files that actually need to go THROUGH both components

These are the files containing biomarkers that exist in your threshold/plausibility tables — only these should be evaluated:

| File | Why it's included |
|---|---|
| `glucose_stream_yearly.csv` | fasting_glucose / cgm_glucose_reading |
| `vitals_yearly.csv` | blood_pressure_systolic, blood_pressure_diastolic, resting_heart_rate |
| `weight_yearly.csv` | weight |
| `bmi_full_year.csv` | bmi |
| `waist_hip_ratio_full_year.csv` | waist_hip_ratio |
| `hba1c_full_year.csv` | hba1c |
| `lipid_panel_full_year.csv` | total_cholesterol, ldl_c, hdl_c, triglycerides |
| `hepatic_panel_full_year.csv` | alt, ast, ggt |
| `renal_panel_full_year.csv` | creatinine, egfr |
| `lab_panels_yearly.csv` | duplicate/backup source for the above lab values (only needed if the individual extraction files above are considered incomplete — otherwise this is redundant with the six files above it) |
| `steps_hourly_yearly.csv` | step_count (also needed as **context data** for the Plausibility Filter's cross-checks on glucose/BP/HR) |
| `sleep_yearly.csv` | sleep_duration |
| `sedentary_time_full_year.csv` | sedentary_time |
| `screen_time_full_year.csv` | screen_time |
| `hydration_full_year.csv` | hydration |

## Needed only as supporting context (not evaluated themselves, just referenced)
- `location_full_year.csv` — used by the Plausibility Filter's context-check rule, not evaluated on its own

## Correctly excluded — no threshold/plausibility rows exist for these
`meal_events_yearly.csv`, `food_content_full_year.csv`, `context_events_yearly.csv`, `adherence_yearly.csv`, `allergies_standing_record.csv`, `vaccination_history.csv`, `menstrual_cycle_full_year.csv`, `cognitive_mental_health_full_year.csv`, and both diary/generation-log `.md` files — none of these have a numeric clinical range to check against, so they should not be run through either component.

**One redundancy worth resolving before handoff:** `lab_panels_yearly.csv` duplicates the same values already split out into `hba1c_full_year.csv`, `lipid_panel_full_year.csv`, `hepatic_panel_full_year.csv`, and `renal_panel_full_year.csv`. I'd only pass the four split files, not the combined one, to avoid double-evaluating the same lab draw twice.