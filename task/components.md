# Task: Build Signal Plausibility Filter & Threshold Evaluator

## Context

This is the first stage of the Upstream layer in the UMC (Unified Medical Context) architecture. These two components run **in strict sequence** on every incoming reading, before anything else touches the data:

```
Raw value → [Plausibility Filter] → PASS? → [Threshold Evaluator] → tagged output
                    ↓ NO
            rejected_readings log (stops here)
```

**No ML or LLM is used anywhere in this task.** Both components are pure lookup-and-compare logic against fixed reference tables — deterministic, auditable, same input always produces the same output. Do not add any generative text, natural-language explanation, or inferred judgment beyond what's explicitly defined in the reference CSVs.

---

## Reference Files (read-only inputs — do not modify)

1. **`plausibility_bounds.csv`** — physiological floor/ceiling per biomarker, plus a `context_check_rule` column describing how to cross-reference against activity/location data
2. **`threshold_ranges_full.csv`** — clinical normal/borderline/abnormal ranges per biomarker, with `age_group` variants where applicable (e.g., eGFR differs for 18-59 vs 60-plus)
3. **Patient data files** (from the final corrected dataset): `glucose_stream_yearly.csv`, `vitals_yearly.csv`, `weight_yearly.csv`, `bmi_full_year.csv`, `steps_hourly_yearly.csv`, `location_full_year.csv`, and the lab panel files (`lab_panels_yearly.csv`, `hba1c_full_year.csv`, `lipid_panel_full_year.csv`, `hepatic_panel_full_year.csv`, `renal_panel_full_year.csv`, `waist_hip_ratio_full_year.csv`)

Read all reference and data files first, before writing any processing logic.

---

## Component 1: Signal Plausibility Filter

**Purpose:** Reject physiologically impossible values before they can be misread as real clinical events.

### Logic
For each incoming reading:
1. Match its biomarker to the corresponding row in `plausibility_bounds.csv`
2. If `value < plausible_floor` OR `value > plausible_ceiling`:
   - Apply that row's `context_check_rule`:
     - If the rule requires a context check (e.g., glucose/BP/HR checks nearby `steps_hourly` and `location_full_year` data at the same timestamp) and that context is available and confirms implausibility (e.g., person was active/awake) → result = `CONFIRMED_ERROR`
     - If context check is required but no context data is available at that timestamp → result = `FLAGGED_ERROR`
     - If the rule says "no context check needed" (this applies to all lab-drawn values — cholesterol, ALT, AST, GGT, creatinine, HbA1c, etc.) → result = `CONFIRMED_ERROR` directly, no cross-referencing needed
3. If the value is within bounds → result = `PASS`

### Output
One row per reading processed, in a new file `plausibility_filter_results.csv`, with columns:
```
event_id, biomarker, timestamp, raw_value, filter_result, reason
```
Only `PASS`, `FLAGGED_ERROR`, or `CONFIRMED_ERROR` are valid values for `filter_result` — no other labels.

Only readings marked `PASS` proceed to Component 2. Readings marked `FLAGGED_ERROR` or `CONFIRMED_ERROR` do NOT get passed to the Threshold Evaluator — they stop here.

---

## Component 2: Threshold Evaluator

**Purpose:** Classify every biologically-plausible reading against its clinical reference range.

### Logic
For each reading that received `PASS` from Component 1:
1. Match its biomarker to the corresponding row(s) in `threshold_ranges_full.csv`
2. If the biomarker has `age_group` or sex-specific variants (e.g., `hdl_c_male` vs `hdl_c_female`, `egfr` at 18-59 vs 60-plus), select the correct row using the patient's known age and sex (from `age_fact.csv` and `sex_fact.csv`)
3. Compare the value against that row's `normal_low`/`normal_high`, `borderline_low`/`borderline_high`, and `abnormal_low`/`abnormal_high` columns
4. Assign exactly one status from this fixed list — do not invent any status not listed here:
   - `normal`
   - `borderline_low`
   - `borderline_high`
   - `low`
   - `high`
   - `critical_low` (only if the biomarker's row actually defines a critical tier — most do not)
   - `critical_high` (same condition)
5. Attach the value from that row's confidence/source column if present (if this column doesn't exist yet in the CSV, flag this back to me rather than guessing a value)

### Output
One row per evaluated reading, in a new file `threshold_evaluation_results.csv`, with columns:
```
event_id, biomarker, timestamp, value, age_group_used, status, confidence_source
```

---

## Important Constraints

- **Do not fabricate a threshold tier that isn't in the source CSV.** If a biomarker's row only has normal/borderline/abnormal (no critical tier), never output "critical" for it.
- **Do not silently drop rejected readings.** Every value that fails the Plausibility Filter must still produce a row in the output file, tagged with why it was rejected — this is for audit purposes, not deletion.
- **Do not add any natural-language generation, summarization, or inferred reasoning beyond what the `reason` field mechanically states** (e.g., "exceeds plausible_ceiling (600); context check: steps>0 same hour, person active" — a templated string built from the actual values checked, not a generated sentence).
- **Process the full year of data** (18 October 2025 – 17 September 2026) across all applicable files — this is not a single-day or single-file task.

---

## Verification Before Finishing

After running both components on the full dataset, report back:
1. Total readings processed by the Plausibility Filter, broken down by `PASS` / `FLAGGED_ERROR` / `CONFIRMED_ERROR`
2. Confirm the count of `CONFIRMED_ERROR` results roughly matches the known deliberately-injected errors in the dataset (approximately 12 implausible glucose values, one per month, plus the corrected data from recent fixes)
3. Total readings processed by the Threshold Evaluator, broken down by status
4. Spot-check: show the full output row for the known Sep 17, 2026 fasting glucose reading (~138 mg/dL) and confirm it correctly shows `status: high`
5. Spot-check: show the full output row for the Aug 22, 2026 hypo event (66.5 mg/dL) and confirm it correctly shows `status: low`

Do not proceed to any further component (Alert Dispatcher, Short-Range Correlator, etc.) — this task is scoped strictly to these two components only.