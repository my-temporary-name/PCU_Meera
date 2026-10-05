# Task: Rebuild Baseline Engine as Cross-Domain Memory (Short / Mid / Long)

## 0. Read this first

The current Baseline Engine build is glucose-only and writes one short sentence per window. That is a statistics row with a caption, not memory. It cannot answer "what was going on with her that week," because it has no sleep, activity, heart rate, adherence, meals, mood, or diary in it.

This task **extends** the current build. Keep the existing glucose metric code (Mean, GMI, TIR, TAR, TBR, %CV, completeness) and the existing `numeric_summary` table. Add a richer, cross-domain memory record per window, and a richer LLM step on top of it.

Nothing here is tailored to one patient. No hard-coded dates, names, biomarkers, or thresholds in code. Everything patient- or stream-specific comes from config (Section 4) and from the data in the Personal Data Store.

---

## 1. What we want, in plain words

For every window of her life (a day, a week, a month-checkpoint), the system should hold a **detailed, retrievable record** of:

1. How her glucose behaved (the clinical CGM metrics, plus how it behaved across the day)
2. What else was going on in the same window: sleep, activity, heart rate, BP, adherence, mood, meals and food, location, hydration, screen time, diary and context events, any other biomarker that crossed a threshold
3. How that window compares with the prior comparable window and with her own cumulative history
4. Which signals moved together (association only, never cause)
5. How trustworthy the window is (data completeness, gaps, known data-quality issues)

A later component (Findings Engine) will query these records to answer three questions: **what is normal for her, what happened, and what was happening alongside it.** The memory must be rich enough that those queries return something useful, not a caption.

---

## 2. Non-negotiable principles

1. **Code computes every number.** The LLM never calculates, rounds, estimates, or infers a number.
2. **The LLM synthesizes and describes.** It organizes already-computed facts into a structured memory entry.
3. **Association, never causation.** Output may say "coincided with." It may never say "caused," "due to," "because of," "led to."
4. **No diagnosis, advice, or prediction** anywhere in memory.
5. **An LLM failure must never lose or block numeric work.** Numeric records are saved first. LLM output is attached afterward and may be null.
6. **One store.** Read from and write to the existing `personal_data_store.db`. No parallel copies in other files.
7. **Report problems, don't patch them silently.** If input data looks wrong, surface it in the report and in `data_quality_flags`. Do not edit or drop source data on your own.
8. **Everything in IST (+05:30).** Earlier pipeline outputs contain some UTC-formatted timestamps. Normalize to IST before windowing, or window boundaries will be wrong.

---

## 3. The three tiers

| Tier | Window | Cadence | Comparison |
|---|---|---|---|
| **Short-term** | One calendar day | Every day | vs the previous day, and vs cumulative-to-date |
| **Mid-term** | Rolling trailing 7 days | Recomputed every day | vs the 7 days immediately before it, and vs cumulative-to-date |
| **Long-term** | Cumulative from day 1 to the checkpoint, plus the last 30-day block | One checkpoint every 30 days | vs the previous checkpoint |

Why long-term is monthly: a cumulative window that grows by one day barely moves, so a daily comparison is noise against noise. Comparing monthly lets the average actually shift between checkpoints.

Episodic memory and write-back from Findings Engine are **out of scope** for this task (Section 14).

---

## 4. Stream registry (this is what keeps it generic)

Do not write per-stream `if` branches. Define a config table, and loop over it.

```yaml
streams:
  - name: cgm_glucose_reading
    domain: glucose
    source: raw_events        # store table
    kind: continuous          # continuous | daily | event | categorical
    day_agg: [mean, min, max, time_of_day_profile]
  - name: sleep_duration
    domain: sleep
    source: raw_events
    kind: daily
    day_agg: [value]
  - name: step_count
    domain: activity
    source: raw_events
    kind: hourly
    day_agg: [sum, peak_hour]
  - name: continuous_heart_rate
    domain: heart_rate
    source: context_ingest    # see 4.1
    kind: continuous
    day_agg: [mean, min, max]
  - name: resting_heart_rate
    domain: heart_rate
    source: raw_events
    kind: daily
    day_agg: [value]
  - name: medication_adherence
    domain: adherence
    source: context_ingest
    kind: event
    day_agg: [per_medication_taken, overall_pct]
  - name: mood_state
    domain: mood
    source: context_ingest
    kind: categorical
    day_agg: [by_time_block]
  - name: meal_events
    domain: meals
    source: context_ingest
    kind: event
    day_agg: [list_with_food_description]
  - name: diary_context
    domain: diary
    source: context_ingest
    kind: event
    day_agg: [list_with_category_and_severity_note]
  # also: blood pressure, hydration, screen_time, sedentary_time, location,
  # menstrual_cycle (only if the patient has this stream), bmi, waist_hip_ratio
```

Rules:
- A stream missing for a patient is skipped, not treated as an error. (A male patient will have no cycle stream. Do not write null placeholders for streams that don't exist.)
- Adding a biomarker means adding a registry row, not new code.

### 4.1 Context streams must come into the store first

Meals, food descriptions, mood, location, diary/context events, adherence, and continuous heart rate are **not** in `raw_events` today (they never passed through Threshold Evaluator). The memory builder should read only from the store, so add a small ingest step that loads them into a `context_events` table, **unchanged, no computation.** If you see a reason to do this differently, flag it before building. Do not read source CSVs directly inside the memory node.

---

## 5. The code-computed record (no LLM involved)

Build one JSON record per window and save it **before** any LLM call.

### 5.1 Short-term (day) record

| Section | Fields |
|---|---|
| **glucose** | mean, GMI, TIR (70-180), TAR (>180), TAR_severe (>250), TBR (<70), TBR_severe (<54), %CV, min and max with timestamps, reading count, completeness % |
| **glucose_by_period** | overnight (00-06), morning (06-12), afternoon (12-18), evening (18-24): mean, max, TIR each |
| **post_meal** | per meal that day: meal label, meal time, pre-meal glucose, peak glucose, rise, minutes to peak (use the 0-150 min window) |
| **sleep** | duration and quality for the night ending that morning |
| **activity** | total steps, peak step hour, sedentary minutes |
| **heart_rate** | continuous mean/min/max, resting HR for the day |
| **blood_pressure** | readings taken that day (often none) |
| **adherence** | per medication taken/missed, overall % |
| **mood** | label and category per time block (morning/afternoon/evening) |
| **meals** | each meal: label, time, food description |
| **lifestyle** | hydration, screen time, location |
| **diary_events** | every context/diary entry that day: category, text, severity note |
| **other_threshold_crossings** | every non-glucose biomarker that day with status in (high, low, borderline_high, borderline_low): biomarker, value, status |
| **completeness_by_stream** | % of expected readings present per stream |
| **deltas** | each numeric field vs previous day, and vs cumulative-to-date mean |

### 5.2 Mid-term (rolling week) record

Everything in 5.1 aggregated over the 7 days, plus:

| Section | Fields |
|---|---|
| **daily_trajectory** | array of 7 entries: date, glucose mean, TIR, sleep hours, steps, adherence %, mood-category of the worst block |
| **best_day / worst_day** | by TIR: date, TIR, mean, and that day's diary events and other threshold crossings |
| **weekday_vs_weekend** | glucose mean, steps, sleep for each group (only if both groups present in the window) |
| **stream_direction_table** | for every stream: this week's value, last week's value, direction (up / down / flat) using the stream's own flat-band from config |
| **events_in_window** | all diary/context events, with dates |
| **recurring_in_window** | patterns computed by code, e.g., "post-dinner peak above 180 on N of 7 days" |
| **deltas** | vs prior 7 days, and vs cumulative-to-date |

Do not compute correlation coefficients on 7 points. Use the direction table. Small-n correlations are misleading.

### 5.3 Long-term (monthly checkpoint) record

| Section | Fields |
|---|---|
| **cumulative** | the seven glucose metrics from day 1 to the checkpoint |
| **last_30_days** | the seven glucose metrics for the trailing 30 days |
| **monthly_trajectory** | one entry per completed month: seven glucose metrics, mean sleep, mean steps, mean adherence %, count of diary events by category |
| **lab_link** | each lab HbA1c with its date, and the GMI computed over the 90 days before that lab (both code-computed), so the CGM-estimated and lab values sit side by side |
| **domain_trends** | for sleep, steps, resting HR, adherence: first-month mean, latest-month mean, direction |
| **deltas** | vs previous checkpoint |

---

## 6. Reliability and data quality

- A window is `reliable = true` only if completeness is at least 70% for that window **and** at least 14 cumulative days of data exist so far. This adapts the ADA 14-day CGM standard; it is an adaptation, not a verbatim restatement. Say so in code comments.
- Every record carries `data_quality_flags`: a list of strings generated by code, for example `missing_stream:continuous_heart_rate`, `gap_hours:6`, `max_reading_above_400`.
- Flags describe issues. They never change values.

---

## 7. What the LLM does (and does not do)

**Input:** the code-computed record for the window, the prior comparable record, and the anchors below.

**Output:** one structured memory entry (schema in 8.3). It must be complete. Cover every section. A one-line summary is a failure.

The LLM does:
- Describe the window's trajectory in order
- State what changed vs the prior window, using the supplied deltas
- Note which signals moved in the same direction in the same window
- Weave in the diary and event text, quoted as given
- Describe repeated patterns code has already counted
- State data-quality caveats
- Decide `is_notable` and say why

The LLM does not: calculate, round, compare numbers it wasn't given a delta for, infer causes, diagnose, advise, or predict.

### 7.1 Anchors (starting heuristics, not clinical standards)

Pass these in the prompt as reference points for `is_notable`. They are engineering defaults, loaded from config, and can be tuned.

```json
{
  "glucose_TIR_change_points": 10,
  "glucose_CV_change_points": 8,
  "glucose_GMI_change": 0.3,
  "severe_range_appeared_or_cleared": true,
  "sleep_hours_change": 1.5,
  "adherence_pct_change": 20,
  "steps_pct_change": 30,
  "resting_hr_change_bpm": 8,
  "diary_event_present": true
}
```

---

## 8. LLM prompts

Provider: OpenRouter, model `openai/gpt-5-nano` (config value, one-line change). Key from `.env` via `python-dotenv`; `.env` must be in `.gitignore` before anything is committed.

### 8.1 System prompt (use verbatim)

```
You write memory entries for a personal health record system. The patient has diabetes.

You receive:
1. RECORD: a JSON record for one time window (a day, a rolling week, or a monthly checkpoint). Every number in it was computed by code.
2. PRIOR: the JSON record for the previous comparable window (may be null).
3. ANCHORS: reference thresholds that help you decide whether a change is notable.

Your job is to turn RECORD into a structured memory entry that a later reasoning step will retrieve to answer: what is normal for this person, what happened in this window, and what else was happening alongside it.

RULES. Follow all of them.
1. Use only values that appear in RECORD or PRIOR. Never calculate, estimate, average, or round a number. If you need a difference, use the supplied delta fields. If no delta is supplied, do not state a difference.
2. Every statement in your output must list the input field paths that support it in evidence_refs.
3. Describe relationships by co-occurrence only. Allowed: "coincided with", "alongside", "on the same days as", "moved in the same direction as". Forbidden: "caused", "because of", "due to", "led to", "resulted in", "triggered", "explains".
4. Do not diagnose, recommend, predict, or give advice.
5. If a field is null or missing, say it was not available. Never guess.
6. If RECORD.reliable is false, state that the window is not clinically reliable and keep every statement tentative.
7. Quote diary and event text exactly as given. Do not add details that are not in the text.
8. Be complete. Cover every section of the schema. If there is nothing to say for a section, return an empty list for it. Do not compress the window into one sentence.
9. Mention every entry in RECORD.data_quality_flags in data_quality_caveats.
10. Return valid JSON that matches the schema. No text before or after the JSON.
```

### 8.2 User prompt template

```
TIER: {tier}            # day | week | month
WINDOW_ID: {window_id}

TIER GUIDANCE:
{tier_guidance}

ANCHORS:
{anchors_json}

PRIOR:
{prior_record_json}

RECORD:
{record_json}

Return the memory entry as JSON using exactly this schema:
{output_schema}
```

**Tier guidance blocks (insert the matching one):**

- **day:** "Describe this single day: how glucose behaved across the day (use glucose_by_period and post_meal), what sleep, activity, heart rate, adherence, mood, meals and diary entries looked like, and anything else that crossed a threshold. Compare with PRIOR (the previous day)."
- **week:** "Describe the trajectory across the 7 days in order using daily_trajectory. Name the best and worst day and what was recorded on those days. Use stream_direction_table to say which streams moved in the same direction as glucose. Summarize events_in_window and recurring_in_window. Compare with PRIOR (the previous 7 days)."
- **month:** "Describe the long-run picture: cumulative metrics, the last 30 days, and monthly_trajectory. Use lab_link to place CGM-estimated GMI beside lab HbA1c where both exist. Use domain_trends for sleep, steps, resting HR, adherence. Compare with PRIOR (the previous checkpoint)."

### 8.3 Output schema

```json
{
  "window_id": "string",
  "tier": "day | week | month",
  "headline": "one sentence naming the single most important thing about this window",
  "trajectory": [
    {"statement": "string", "evidence_refs": ["field.path"]}
  ],
  "changes_vs_prior": [
    {"statement": "string", "evidence_refs": ["field.path"]}
  ],
  "co_movement": [
    {"statement": "string (co-occurrence wording only)", "streams": ["stream names"], "evidence_refs": ["field.path"]}
  ],
  "context_from_diary_and_events": [
    {"statement": "string", "quoted_text": "exact text or null", "date": "YYYY-MM-DD", "evidence_refs": ["field.path"]}
  ],
  "recurring_patterns": [
    {"statement": "string", "evidence_refs": ["field.path"]}
  ],
  "data_quality_caveats": ["string"],
  "is_notable": true,
  "notable_reason": "string or null (null only if is_notable is false)",
  "confidence": "low | moderate | high   (taken from RECORD.reliable and completeness, not your opinion)"
}
```

### 8.4 Format-only example (week). Numbers here are placeholders to show shape, not data

```json
{
  "window_id": "week_ENDING_2026-01-14",
  "tier": "week",
  "headline": "Glucose TIR fell and %CV rose this week while sleep and adherence also moved lower.",
  "trajectory": [
    {"statement": "TIR was highest on the first day of the window and lowest on the last two days.",
     "evidence_refs": ["daily_trajectory[0].tir", "daily_trajectory[5].tir", "daily_trajectory[6].tir"]}
  ],
  "changes_vs_prior": [
    {"statement": "TIR changed by the supplied delta versus the previous 7 days.",
     "evidence_refs": ["deltas.tir"]}
  ],
  "co_movement": [
    {"statement": "Sleep hours and adherence moved down in the same window in which TIR moved down.",
     "streams": ["sleep_duration", "medication_adherence", "cgm_glucose_reading"],
     "evidence_refs": ["stream_direction_table.sleep_duration", "stream_direction_table.medication_adherence"]}
  ],
  "context_from_diary_and_events": [
    {"statement": "A travel entry was logged during the window.",
     "quoted_text": "<exact diary text>", "date": "YYYY-MM-DD",
     "evidence_refs": ["events_in_window[0]"]}
  ],
  "recurring_patterns": [],
  "data_quality_caveats": ["gap_hours:6 on one day"],
  "is_notable": true,
  "notable_reason": "TIR change exceeds the 10-point anchor and %CV change exceeds the 8-point anchor.",
  "confidence": "high"
}
```

---

## 9. Output validation (required)

After every LLM response, before saving it as valid:

1. **JSON parses** and matches the schema.
2. **Numeric grounding:** extract every number from all statement fields. Each must appear in RECORD or PRIOR (dates, window ids, and numbers inside `quoted_text` are exempt). Ungrounded number means reject.
3. **Forbidden-language scan:** reject if any statement contains "caused", "because of", "due to", "led to", "resulted in", "triggered", "explains".
4. **Evidence refs resolve:** each `evidence_refs` path exists in RECORD or PRIOR.
5. **Quotes are exact:** every `quoted_text` is a substring of a diary/event text in RECORD.

On failure: retry that window once, appending the specific failures to the prompt. If it fails again, save the numeric record with `llm_status = 'rejected'`, store the raw response in `llm_raw` for inspection, and continue. Never block the run.

---

## 10. Storage

Add to `personal_data_store.db`. Do not drop or alter `raw_events` or `numeric_summary`.

```sql
CREATE TABLE context_events (          -- ingest of non-threshold streams (4.1)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT, timestamp TEXT, date TEXT,
    value_text TEXT, value_num REAL, category TEXT, meta_json TEXT
);

CREATE TABLE memory_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id TEXT UNIQUE,
    tier TEXT,                 -- day | week | month
    start_date TEXT, end_date TEXT,
    reliable INTEGER,
    record_json TEXT,          -- code-computed, always written first
    prior_window_id TEXT,
    data_quality_flags TEXT,
    memory_json TEXT,          -- validated LLM output, nullable
    is_notable INTEGER,        -- nullable
    llm_status TEXT,           -- ok | rejected | failed | skipped
    llm_raw TEXT
);
```

Read API (the future Findings Engine will use these; build them now):
- `get_memory(tier, date)`: returns record plus memory for the window ending on that date
- `get_memories_overlapping(start_date, end_date, tier=None)`
- `get_notable_memories(tier, since_date)`

---

## 11. Graph node and run behavior

`personal_data_store -> baseline_engine -> END` (unchanged position).

Per run:
1. Ingest context streams into `context_events` (idempotent).
2. Build all day, week, month `record_json` and save them. Print counts.
3. Run the LLM step in batches, defaulting to **3-4 windows per call** (these records are large, so batches must be small). Parse results back by `window_id`. Make batch size and model config values.
4. Validate (Section 9), save, report.

Order matters: all numeric records are saved before the first LLM call.

---

## 12. Known data caveats in the current inputs (report these; do not patch)

From files inspected earlier in this project:
- **Five glucose readings at exactly 65.0 mg/dL** are leftover artifacts of an earlier data-repair clip operation, not real hypoglycemia. They will count toward TBR.
- **Some implausible spikes (about 590 and 599 mg/dL) passed the Plausibility Filter** and sit in `raw_events`. They will distort %CV and TAR_severe for those days.
- **A deliberately placed hypoglycemic reading (66.5 mg/dL) around Aug 22 appears as roughly 76 mg/dL** in the processed output.
- **Weight has no threshold row**, so it never reached `raw_events`. Use BMI.
- **Threshold Evaluator `status` and CGM bands disagree by design.** Evaluator: 70/99/125 (diagnostic). CGM metrics: 70/180/250/54 (management). A reading can be "high" in one and in range in the other. Document this in code comments so no one treats it as a bug.

Handling: emit a `data_quality_flags` entry for any window where the max reading exceeds 400 or where a reading equals one of the known artifact values; list all of the above in the final report. Do not remove rows.

---

## 13. Verification and report back

When finished, report:
1. Counts: day, week, month records built; how many `reliable`
2. LLM outcomes: ok / rejected / failed counts, and the most common rejection reason
3. Three full examples printed in full (code record plus validated memory): one ordinary day, one week containing a diary event, one month checkpoint
4. The caveat list from Section 12 with how many windows were flagged
5. Total LLM calls and approximate token usage
6. Confirmation that no field in any `memory_json` introduces a number absent from its input

---

## 14. Out of scope

- Episodic memory and any write-back from Findings Engine
- Other biomarkers' clinical metric sets beyond what the registry carries as plain aggregates (BP staging, sleep regularity, etc. are a follow-up)
- Any recommendation, prediction, or causal statement
- Editing source data

---

## 15. Decisions to flag back to me before building, not decide silently

1. Is ingesting context streams into the store (4.1) acceptable, or do you see a better way to keep the memory node reading only from the store?
2. With records this large, is 3-4 windows per call right, or should long-term records go one per call? State the expected total call count.
3. `continuous_heart_rate` has not passed through Plausibility Filter or Threshold Evaluator. Do you want it flagged as an unfiltered stream in `data_quality_flags`, or run through the filter first?
4. Any anchor in 7.1 that you think would make `is_notable` fire on nearly every window, or on almost none.