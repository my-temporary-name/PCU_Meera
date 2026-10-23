# 1. Plausibility Filter and Threshold Evaluator

Audience: engineers working on the UMC upstream pipeline.
Scope: graph nodes `plausibility_filter` and `threshold_evaluator`, plus the `load_inputs` node that feeds them.
Spec: `task/components.md` (sources of the numbers: `understand/how_the_numbers_flow.md` §1, the pipeline's own CSVs).

These two components are **100% deterministic and lookup-only**. No ML/LLM, no probabilistic logic. The `reason` string on every filter row is a template filled with the values that were actually checked.

---

## 1. What they do

| | Question it answers | Output |
|---|---|---|
| **Plausibility Filter** | "Could this reading physically be real?" Compares each raw reading with a fixed floor and ceiling for that measure. It never judges good or bad. | `PASS`, `FLAGGED_ERROR` or `CONFIRMED_ERROR` per reading |
| **Threshold Evaluator** | "Is this (plausible) reading normal, borderline or abnormal for this person?" Compares it with a reference range chosen by age and sex. | One of 5 statuses: `normal`, `borderline_low`, `borderline_high`, `low`, `high` |

Only `PASS` readings go on. A rejected reading never reaches the evaluator, and nothing downstream sees it.

---

## 2. Position in the graph

```
load_inputs ──► plausibility_filter ──(conditional)──► threshold_evaluator ──► short_range_linker ──► …
                                      │
                                      └─ no PASS reading at all ──► END   (route_after_filter)
```

Defined in `src/v0_code/graph/builder.py`. The conditional edge is `route_after_filter` (`nodes/plausibility_filter.py:35`): it ends the run only if `state.passed_readings` is empty.

### Code layout

| File | Role |
|---|---|
| `data/loaders.py` | Reads reference tables and patient files, normalises every source into `Reading` |
| `nodes/load_inputs.py` | Node 1: puts loader output into state |
| `nodes/plausibility_filter.py` | Node 2: thin wrapper. Reads state, calls `check_plausibility`, writes the CSV, returns partial state |
| `logic/plausibility.py` | Pure decision logic for the filter. No LangGraph imports |
| `nodes/threshold_evaluator.py` | Node 3: thin wrapper. Daily step aggregation, skip rule, CSV |
| `logic/threshold.py` | Pure decision logic for the evaluator. No LangGraph imports |
| `graph/state.py` | `UMCState` (one Pydantic model) and the `Reading`, `FilterResult`, `ThresholdResult` records |

Design rule: nodes are thin wrappers and decisions live in `logic/`, so the logic is unit-testable and new nodes can be added without touching it. Nodes return partial dict updates that LangGraph merges into `UMCState`.

---

## 3. Inputs

### 3.1 Reference tables (`ranges/`)

**`plausibility_bounds.csv`**: one row per biomarker (23 rows). Columns used by code: `biomarker`, `plausible_floor`, `plausible_ceiling`. The other columns (`floor_meaning`, `ceiling_meaning`, `context_check_rule`) document intent only. The rule is implemented in code, not parsed from the CSV.

**`threshold_ranges_full.csv`**: 36 rows. Columns: `category, biomarker, unit, age_group, normal_low, normal_high, borderline_low, borderline_high, abnormal_low, abnormal_high`. Empty cell = no such bound.

Note: `abnormal_high` holds the abnormal **cut-point** even for rows where the abnormal side is low (e.g. eGFR `60`, HDL `40`). Code therefore never assumes `abnormal_high` means "upper side". See §5.2. The `abnormal_low` column is not read by the code.

### 3.2 Patient facts (`final/`)

| File | Used for |
|---|---|
| `age_fact.csv` (`date_of_birth`) | Age at each reading's date, to pick an age-banded row |
| `sex_fact.csv` (`sex`) | Picks `_male` / `_female` rows |
| `steps_hourly_yearly.csv` | `steps_by_hour`, keyed `YYYY-MM-DDTHH`, used for context checks and the resting rule |
| `location_full_year.csv` | `location_by_date`, keyed `YYYY-MM-DD` (location is daily) |

### 3.3 Readings (`data/loaders.py`)

Every source row becomes `Reading(event_id, biomarker, timestamp, value, source_file)`. Two mapping tables define which file column becomes which biomarker:

- `WIDE_FILES`: one row per date, several measures per row (HbA1c, lipid, hepatic, renal panels; BMI; waist-hip ratio; sedentary, screen time, hydration). `event_id` is synthesised as `{biomarker}_{date}`.
- `LONG_FILES`: event-style files, with the biomarker chosen by the row's `type` value (CGM glucose, weight, hourly steps, sleep, resting HR, continuous HR, fasting glucose).

Blood pressure `"129/86"` is split into two readings (`..._sys`, `..._dia`), so one measurement counts twice.

**Which lab files are used:** the four split lab files, not `lab_panels_yearly.csv`, with one exception: `fasting_glucose` lives only in `lab_panels_yearly.csv`. `tsh`, `hsi` and the excluded files in `task/inputs.md` are not evaluated.

Result: **77,797 readings** across 24 measures enter the filter.

---

## 4. Plausibility Filter, how it works

`logic/plausibility.py:check_plausibility(reading, bounds, steps_by_hour, location_by_date) -> FilterResult`

### 4.1 Decision procedure

```
1. bounds row = bounds[ BOUNDS_ALIASES.get(biomarker, biomarker) ]
     no row                       → FLAGGED_ERROR  "no plausibility_bounds row for biomarker"
2. floor <= value <= ceiling      → PASS           "within [floor, ceiling]"
3. out of bounds, breach = "below plausible_floor (x)" | "exceeds plausible_ceiling (x)"
     biomarker needs a context check?
        yes → _context_check()  → CONFIRMED_ERROR or FLAGGED_ERROR
        no  → CONFIRMED_ERROR   "…; context check: none required"
```

Bounds are inclusive on both ends. Only an **out-of-bounds** reading triggers a context check; an in-bounds reading passes without looking at context.

### 4.2 Context check (only glucose, BP and heart rate)

Three sets in the module decide who gets one:

| Set | Members | Meaning |
|---|---|---|
| `ACTIVE_CONTEXT_BIOMARKERS` | `fasting_glucose`, `cgm_glucose_reading`, `blood_pressure_systolic`, `blood_pressure_diastolic` | An extreme value is implausible if the person was active |
| `RESTING_CONTEXT_BIOMARKERS` | `resting_heart_rate`, `continuous_heart_rate` | An extreme value is implausible if the person was resting |
| everything else (labs, weight, BMI, steps, sleep, etc.) | | No context check. Out of bounds is `CONFIRMED_ERROR` directly |

Context lookups:

- **Steps:** matched by hour bucket, `timestamp[:13]` (e.g. `2026-02-05T13`).
- **Location:** matched by date, `timestamp[:10]`, because the location file is daily.
- "Active" means `steps > 0` **or** a location other than `home` / `home_wfh`.

`_context_check` returns, in this order of precedence:

| # | Condition | Label | Detail |
|---|---|---|---|
| 1 | No steps and no location available | `FLAGGED_ERROR` | `no context data at timestamp` |
| 2 | Resting-type biomarker, `steps == 0` | `CONFIRMED_ERROR` | `person resting` |
| 2b | Resting-type biomarker, otherwise | `FLAGGED_ERROR` | `resting not confirmed` |
| 3 | BP and location in `{hospital, clinic}` | `FLAGGED_ERROR` | `clinical setting` (an extreme BP at a clinic may be real) |
| 4 | Active (steps > 0 or location not at home) | `CONFIRMED_ERROR` | `person active` |
| 4b | Otherwise | `FLAGGED_ERROR` | `activity not confirmed` |

Meaning of the labels:

- `CONFIRMED_ERROR`: out of bounds **and** context agrees it cannot be real. Dropped.
- `FLAGGED_ERROR`: out of bounds but context is missing or does not settle it. Dropped from the pipeline too (only `PASS` continues), but marked as less certain.

### 4.3 Aliases

`BOUNDS_ALIASES = {"continuous_heart_rate": "resting_heart_rate"}`. The 15-minute wearable stream has no bounds row of its own, so it reuses `resting_heart_rate` (30–220 bpm). Physiological limits are the same.

### 4.4 Example `reason` strings (templated)

```
within [3, 18]
exceeds plausible_ceiling (600); context check: steps=107 same hour, location=office, person active
below plausible_floor (60); context check: no context data at timestamp
exceeds plausible_ceiling (20000); context check: none required
```

### 4.5 Node behaviour (`nodes/plausibility_filter.py`)

1. Runs `check_plausibility` on **every** reading in `state.readings`.
2. `passed_readings` = readings whose result is `PASS`.
3. Writes `output/plausibility_filter_results.csv` with columns `event_id, biomarker, timestamp, raw_value, filter_result, reason`. **Row order is loader order, not sorted.**
4. Writes to state: `filter_results`, `passed_readings`, `filter_output`, `filter_counts` (a count per label).

---

## 5. Threshold Evaluator, how it works

### 5.1 Row selection

`logic/threshold.py:select_row` → `evaluate_threshold`.

1. **Age** = `age_on(dob, reading.timestamp)`: whole years at the reading's date (the birthday not yet reached this year is subtracted).
2. **Name** = `THRESHOLD_ALIASES.get(biomarker, biomarker)`:
   - `cgm_glucose_reading` → `fasting_glucose` (there is no CGM row)
   - `continuous_heart_rate` → `resting_heart_rate`
3. The first row where `row.biomarker in (name, f"{name}_{sex}")` **and** `_group_matches(age_group, age, sex)`:
   - `all_adult` matches everyone;
   - `adult_male` / `adult_female` match by sex only (this is how `ggt`, whose sex is in the `age_group` column, works; `hdl_c`, `creatinine`, `waist_hip_ratio` resolve through the `_male` / `_female` biomarker suffix instead);
   - `"18-59"`, `"60-plus"`, `"18-64"`, `"65-plus"` are numeric age bands (`plus` means no upper limit).
4. No matching row → returns `None`; the node counts it in `no_threshold_row`.

### 5.2 Status assignment (`assign_status`)

Side-based tiering, **not** based on which column holds the abnormal cut-point. This is needed because the CSV's `abnormal_high` column contains the cut-point even for low-side rows.

```
if value inside [normal_low, normal_high]            → normal      (a missing bound is open-ended)

if value < normal_low:                                (low side)
    has_band = borderline_low and borderline_high exist and borderline_high < normal_low
    → borderline_low  if has_band and value >= borderline_low
    → low             otherwise

else value > normal_high:                             (high side)
    has_band = borderline_low and borderline_high and normal_high exist and borderline_low >= normal_high
    → high            if abnormal_high exists and value >= abnormal_high
    → borderline_high if has_band
    → high            otherwise
```

Notes:

- Only statuses the row can support are emitted. If a row has no borderline band (ALT, AST, HDL, creatinine, heart rate and others), the reading is `normal` or `high`/`low`, never `borderline_*`.
- **No critical tiers exist** in the reference table, so `critical_*` is never emitted.
- The five statuses are the complete output alphabet.
- `confidence_source` is written **blank on purpose**: the threshold CSV has no such column and values must not be invented.

Worked examples (fasting-glucose row: normal 70–99, borderline 100–125, abnormal ≥ 126):

| value | status | why |
|---|---|---|
| 85 | `normal` | inside 70–99 |
| 65 | `low` | below 70; the row has no low-side borderline band |
| 110 | `borderline_high` | above 99, below the cut-point 126, band exists |
| 140 | `high` | ≥ `abnormal_high` 126 |

eGFR, age 18–59 (normal 90–120, borderline 60–89, `abnormal_high` 60 acting as the low-side cut-point): 75 → `borderline_low`; 55 → `low`.

### 5.3 What is not evaluated, and why (`threshold_evaluator_node`)

Candidates = passed readings, **minus** `steps_hourly`, **plus** daily `step_count` rows (below). Then, for each candidate:

```
skip_reason()  → not None  → counted in state.not_applicable, no status
evaluate_threshold() → None → counted in state.no_threshold_row, no status
otherwise      → a ThresholdResult row
```

Three things cut the **77,792** passed readings down to **44,469** status rows (gap **33,323**):

**(a) Continuous heart rate is judged only at rest: 25,444 readings get no status.**
The only reference is the 60–100 bpm range, which is a *resting* range (a heart rate of 110 while walking is not "high"). `skip_reason` (`RESTING_ONLY = {"continuous_heart_rate"}`) therefore evaluates a reading only if the step count for that hour (`timestamp[:13]`) is exactly `0`.

- no step row for that hour → skipped, reason `no activity data to confirm resting state`
- `steps > 0` → skipped, reason `not at rest (steps > 0 in that hour)`

Of the 33,792 readings in the year, 8,348 are at rest (mostly night) and 25,444 are not applicable. The reference CSVs have no continuous-HR row and are intentionally unmodified.

A missing step hour is *unknown*, not zero. The code never treats it as rest.

**(b) Hourly steps are summed to daily totals: 8,160 readings become 340 rows.**
A day-level range (`step_count`) makes no sense for one hour. `_daily_step_counts` sums the **plausible** hourly values by `timestamp[:10]` into synthetic readings `event_id = step_count_<date>`, `biomarker = step_count`, `timestamp = <date>`. The hourly readings are removed from the candidate list. 12 days have no hourly rows and therefore no daily total.
Because the sum uses only `PASS` readings, a rejected hour would be left out of its day's total (none occurred: all 8,160 passed).

**(c) Weight has no threshold row: 59 readings get no status.** It is plausibility-checked but never evaluated (counted in `no_threshold_row`).

### 5.4 Output (`output/threshold_evaluation_results.csv`)

Columns: `event_id, biomarker, timestamp, value, age_group_used, status, confidence_source`. `age_group_used` is the `age_group` of the row that matched (e.g. `all_adult`). State gets `threshold_results`, `threshold_output`, `status_counts`, `no_threshold_row`, `not_applicable`.

---

## 6. Data flow summary

```
24 measures, source CSVs (final/)
   │ load_inputs: normalise to Reading, split BP                          77,797 readings
   ▼
plausibility_filter ── bounds + steps_by_hour + location_by_date ───────► plausibility_filter_results.csv
   │ PASS only                                                            77,792 passed / 5 rejected
   ▼
threshold_evaluator ── thresholds + DOB + sex + steps_by_hour ──────────► threshold_evaluation_results.csv
   │ skip heart rate not at rest, sum steps to days, no weight            44,469 status rows
   ▼
short_range_linker (glucose with status high/low) ─► personal_data_store ─► …
```

The 44,469 status rows are what the Linker and the Personal Data Store receive. The Linker looks only at glucose readings with status `high` (14,692) or `low` (5).

---

## 7. Numbers on the real data (patient `meera_iyer_v1`, Oct 2025 – Sep 2026)

### 7.1 Filter result

77,797 checked, **77,792 `PASS`, 5 `CONFIRMED_ERROR`**, 0 `FLAGGED_ERROR`. All five are CGM glucose above the 600 mg/dL ceiling, and each was confirmed by context (she was active):

| When (IST) | Value (mg/dL) | Context found |
|---|---|---|
| 13 Oct 2025 15:00 | 612.0 | steps 107, office |
| 5 Feb 2026 13:00 | 613.9 | steps 131, mall |
| 23 Jun 2026 11:00 | 603.5 | steps 151, home (working) |
| 21 Jul 2026 13:00 | 611.0 | steps 176, home (working) |
| 6 Sep 2026 11:00 | 614.2 | steps 90, home |

### 7.2 Per-measure arithmetic

| Measure | Checked | Passed | Given a status |
|---|---|---|---|
| CGM glucose | 33,581 | 33,576 | 33,576 |
| Continuous heart rate | 33,792 | 33,792 | 8,348 |
| Hourly steps | 8,160 | 8,160 | 340 (as daily totals) |
| Resting heart rate | 353 | 353 | 353 |
| Sedentary time | 352 | 352 | 352 |
| Screen time | 352 | 352 | 352 |
| Hydration | 352 | 352 | 352 |
| Sleep duration | 352 | 352 | 352 |
| Blood pressure, systolic | 141 | 141 | 141 |
| Blood pressure, diastolic | 141 | 141 | 141 |
| BMI | 59 | 59 | 59 |
| Waist–hip ratio | 59 | 59 | 59 |
| Weight | 59 | 59 | 0 |
| 11 labs × 4 draws | 44 | 44 | 44 |
| **Total** | **77,797** | **77,792** | **44,469** |

Reconciliation: 33,576 + 8,348 + 340 + 1,761 + 282 + 118 + 44 = **44,469**, and 77,792 − 44,469 = **33,323** = 25,444 heart-rate readings with no status + (8,160 hourly steps − 340 daily rows) + 59 weights.

### 7.3 Status distribution of the 44,469 rows

| Status | Rows |
|---|---|
| `borderline_high` | 18,397 |
| `high` | 15,194 |
| `normal` | 9,602 |
| `low` | 969 |
| `borderline_low` | 307 |

Most of these are CGM glucose. It is judged with the **diagnostic fasting-glucose limits (70 / 99 / 125 mg/dL)**, which are strict, so a lot of ordinary daytime glucose lands in `borderline_high` / `high`. The Baseline Engine uses CGM management targets (70–180 time in range, 54 / 250 severe), so the two **disagree by design**. This is a deliberate non-bug.

---

## 8. Gotchas and decisions to check before changing anything

1. **`event_id` is not unique** in the source files. Glucose, steps, sleep, vitals, weight and lab ids restart every month (2,976 unique ids over 33,581 glucose rows). Never join or filter readings by `event_id` alone. Pair by position or by `(event_id, timestamp)`.
2. **`abnormal_high` is a cut-point, not a side.** Do not infer "high side" from the column. `assign_status` decides by comparing against `normal_low` / `normal_high`.
3. **Resting heart-rate rule.** Do not add a status for readings during activity. Do not treat a missing step hour as zero steps (this once made the resting figure equal the all-day mean on days without step data).
4. **Context granularity differs:** steps by hour (`[:13]`), location by date (`[:10]`).
5. **Glucose ceiling catches only gross errors.** The spec expected about 12 injected glucose errors (one per month); the data has 5 above 600. Two further spikes (599.0 and 590.0) sit just under the ceiling and `PASS`. The spec's "22 Aug 2026 low of 66.5 mg/dL" does not exist (that day's CGM minimum is 76.3; the year's minimum is 65.0). These are reported, not patched.
6. **Data starts 2025-10-01** (labs 2025-09-15), not 18 Oct as the spec says. All rows are processed.
7. **`confidence_source` is intentionally empty** and `reason` must stay a template built from the checked values. Do not turn either into free text.
8. **Weight is filtered but not evaluated** (no range). `tsh`, `hsi` and the files marked excluded in `task/inputs.md` are not evaluated at all.
9. **CSV row order is loader order**, not time order. Sort explicitly if you need order.

## 9. Running and inspecting

```bash
uv sync
uv run v0-code            # runs the whole graph; writes both CSVs and prints a verification report
```

This writes `output/plausibility_filter_results.csv` and `output/threshold_evaluation_results.csv`. `uv run v0-code` refuses to run if `output/personal_data_store.db` already exists unless you pass `--rebuild`, and a rebuild wipes the v1 memory entries. The doctor dashboard shows this component on `#/stage/threshold`.

Quick checks on the outputs:

```bash
# count of each filter label
cut -d, -f5 output/plausibility_filter_results.csv | sort | uniq -c
# rejected readings with their reasons
grep -v ',PASS,' output/plausibility_filter_results.csv
```
