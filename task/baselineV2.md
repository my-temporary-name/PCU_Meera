# Baseline Engine v2 — Spec for Claude Code

## 0. What this is

A rebuild of the Baseline Engine's design. **Code computes every fact. The LLM writes a short plain-words gist and nothing else.** The goal is a memory that is correct by construction, cheap to run, and generic across patients.

**Reuse, don't rewrite, what is already verified:** the glucose metric formulas (TIR/TAR/TBR/%CV/GMI), the stream registry mechanism, anchor evaluation, the record builder sections, the tests. **Change:** the structure around them, as described below.

**Do not delete or alter** `raw_events`, `numeric_summary`, or the existing `memory_records` rows. Write v2 output to a new table (Section 8) so old results stay available for comparison. Rebuilding the database must require an explicit flag.

---

## 1. Rules (each comes from a mistake we made)

1. **Code writes every fact:** numbers, dates, quotes, lists, caveats, deviation lists, co-movement, the day-by-day list, `is_notable` and its reason. The LLM sees no numbers and writes no numbers.
2. **At most four output checks** for the LLM (Section 7.4). Do not add more without approval. A check that rejects correct text is a bug in the check.
3. **"Quiet" means nothing deviated from her own usual**, not "no anchor crossed". Chronic oddities (steps low on 95% of days) are recorded once in the month tier, not in every entry.
4. **Clean first, then compute.** Questionable readings are excluded before any metric, delta, anchor or tag is computed. Raw values appear only in a caveat.
5. **Everything is as-of the window's end date.** No window may depend on later data.
6. **Nothing patient-specific in code:** timezone, pronoun, medications, thresholds, anchors, strain categories, step floors, device ranges all live in config.
7. **A window never has an empty memory.** The code-built entry is the memory; the LLM gist is optional.
8. **Fix data problems at the source or report them.** Never patch silently downstream.
9. **Every rule has a test** (Section 10).
10. **Process:** no design changes mid-stage. Bugs are fixed only with a test that failed first. Anything else goes on a parked list and is reported.

---

## 2. Inputs and config

**Inputs:** the Personal Data Store (`raw_events`, `context_events`) and one config file. No source CSVs are read inside the engine.

**Config (YAML), loaded per patient and versioned (store `config_version` on every row):**

```yaml
patient:
  timezone: "Asia/Kolkata"       # all windowing happens in this zone
  pronoun: "she"                 # she | he | they
  strain_mood_categories: [tired_low_energy, mild_stress, anxious, overwhelmed_high_distress]
history:
  min_days_for_compare: 14
  reliable_completeness_pct: 70
glucose:
  device_range: [40, 400]        # readings outside are removed as questionable
  max_step_change_per_15min: 75  # larger jumps are removed as questionable
streams:                          # one row per stream; add a row, not code
  - {name: cgm_glucose_reading, domain: glucose, kind: continuous}
  - {name: sleep_duration, domain: sleep, kind: daily}
  - {name: step_count, domain: activity, kind: hourly}
  - {name: continuous_heart_rate, domain: heart_rate, kind: continuous}
  - {name: resting_heart_rate, domain: heart_rate, kind: daily}
  - {name: medication_adherence, domain: adherence, kind: event}
  - {name: mood_state, domain: mood, kind: categorical}
  - {name: hydration, domain: lifestyle, kind: daily}
  - {name: screen_time, domain: lifestyle, kind: daily}
  - {name: sedentary_time, domain: activity, kind: daily}
  # blood_pressure: list readings only; no deviation logic in this version
flat_band:
  sd_multiplier: 0.5             # flat band = this x SD of the stream's daily values before the window
size_labels:
  small_below: 2                 # multiples of the flat band
  moderate_below: 4              # at or above this = large
anchors:                          # evaluated on CLEANED values
  glucose_TIR_change_points: {day: 10, week: 10, month: 10}
  glucose_CV_change_points:  {day: 8,  week: 8,  month: 8}
  glucose_GMI_change:        {week: 0.3, month: 0.2}
  severe_range_appeared_or_cleared: true
  sleep_hours_change:        {day: 1.5, week: 1.5, month: 1.5}
  resting_hr_change_bpm:     {day: 8, week: 8, month: 8}
  adherence_meds_changed:    {day: "min(2, n_meds)"}
  adherence_pct_change:      {week: 15, month: 10}
  steps_abs_change:          {day: 3000, week_mean: 1500}
  lab_cgm_discordance:       {month: 0.5}   # |lab HbA1c - GMI over prior 90 days|
gist:
  model: "openai/gpt-5-mini"
  reasoning_effort: "low"
  timeout_seconds: 90
  sdk_retries: 0
  concurrency: 6
  batch_size: {day: 4, week: 2, month: 1}
  week_gist_weekday: "Sunday"    # weeks ending on this day get a gist; others only if an anchor crossed
```

Anchor thresholds above are starting heuristics, not clinical standards. Do not retune them in this task. Report fire rates.

---

## 3. Normal profile (as-of any date)

For each stream, computed only from history strictly before the window:
- typical level (median) and spread (SD) of daily values
- **flat band** = `sd_multiplier` x SD
- **usual status** = most common threshold status over that history (needs `min_days_for_compare` days)
- **share of days non-normal** (feeds `chronic_findings`)

Glucose also gets the ADA set (mean, GMI, TIR 70-180, TAR >180 and >250, TBR <70 and <54, %CV, completeness) per window. These are glucose-specific clinical bands and are allowed to disagree with the Threshold Evaluator's bands (70/99/125). Say so in a code comment.

Before `min_days_for_compare` days of history: no flat band, no usual status, no direction tags (`not_enough_data`).

---

## 4. Windows and facts (code)

| Tier | Window | Compared with |
|---|---|---|
| day | one calendar day (config timezone) | previous day |
| week | rolling trailing 7 days, computed for every day | previous 7 days |
| month | cumulative from day 1, plus the last 30 days, every 30 days | previous checkpoint |

Keep the v1 record sections (glucose, glucose by period, post-meal, sleep, activity, heart rate, BP readings, adherence per medication, mood, meals, lifestyle, location, diary events, threshold crossings, completeness, week aggregates, month trajectory and lab link). The changes are below.

### 4.1 Direction tags with size labels
For every numeric stream in the registry, per window:
`{measure, direction: up|down|flat|not_enough_data, size: none|small|moderate|large, delta}`
- flat if |delta| < flat band
- small if 1x to <2x the band; moderate if 2x to <4x; large if 4x or more (configurable)
- Mood uses "strained periods of the day" (count of periods in the config strain categories). Direction wording: more or fewer strained periods. Never "mood went up/down".
- Delta is stored for code and tests. It is never shown to the LLM.

### 4.2 Material changes (the heart of the entry)
A typed list, built by code, in this order:
1. `anchor_crossed` (cleaned values only)
2. `missed_dose` (medicine, count of days in window)
3. `diary_event` (category, text, severity note, date)
4. `status_worse_than_usual` (a status worse than that stream's usual status)
5. `large_change` (any tag with size large)
6. `data_gap` or `low_completeness` (stream, share)
7. `questionable_reading_removed`

`quiet = (list is empty)`. Missed doses and diary events are always material.

### 4.3 Co-movement
Computed from the tags, never by the LLM. Report only if glucose moved beyond its flat band. List measures that moved the same way as glucose and the opposite way, one entry per domain (merge heart rate variants). Also keep a `flat` list. Never report flat/flat as co-movement.

### 4.4 Other code-rendered pieces
- Day-by-day list for week tier (date, glucose average, time in range, sleep, steps, adherence, worst mood, flags, best/worst day with tie-break by mean glucose).
- `chronic_findings` in the month tier only: streams non-normal on 50% or more of days, as a percent.
- Lab link: each lab HbA1c next to GMI over the prior 90 days, and the signed gap.
- `deviation_text`: a rendered, plain-language block of the above for humans (what v1 called "code-rendered").

---

## 5. Trust layer (code)

- **Reliability:** reliable = completeness at least `reliable_completeness_pct` and at least `min_days_for_compare` days of data so far. This adapts the ADA 14-day/70% guidance to window level; say so in a comment.
- **Questionable readings (generic detector, no hard-coded values):**
  - a reading outside `device_range`
  - a change versus the previous reading greater than `max_step_change_per_15min`
- Questionable readings are **removed before any computation**. The raw values are recorded in `questionable_readings` and a caveat shows what the metrics would have been with them included.
- Every data-quality flag carries an `affects` list of metrics, and the caveat is written by code next to those metrics only.
- Flags: `low_completeness:<stream>:<pct>` for any stream under the reliability threshold (including 0%), `gap_hours:<n>`, `questionable_reading_removed:<n>`.
- **Known upstream data issues (report, do not patch):** five isolated glucose readings at exactly 65.0 mg/dL (a data-repair artifact; the rate rule above will not catch them) and labs that run above CGM-derived GMI. List them in the final report.

---

## 6. Anchors and notable

- Anchors are evaluated on cleaned values. A crossing that exists only because of a removed reading is recorded in `anchors_questionable` and does not count.
- `is_notable = len(anchors_crossed) > 0`. Computed by code. The LLM never decides it.
- `notable_reason` is a code-written sentence from the crossed anchors (names, direction, size label; numbers are allowed here because it is code).
- Report fire rates per anchor and tier. Report dead anchors (never fired). Do not retune. If a tier's notable rate is above 60% or below 3%, report it before doing anything else.

---

## 7. The gist (LLM)

### 7.1 When it runs
| Case | What is stored |
|---|---|
| Fewer than `min_days_for_compare` days of history | code line: "Not enough history yet to compare." status `code_line_early` |
| Quiet window (no material changes) | code line: "Nothing deviated from her usual." status `code_line_quiet` |
| Day with material changes | LLM gist |
| Week | LLM gist. With `week_gist_weekday: none` (the default) every non-early, non-quiet week is queued; with a weekday name only weeks ending on it or with an anchor crossed are, and the rest get a code line from the top two material changes, status `code_line_week_skipped` |
| Month checkpoint | LLM gist |
| LLM failed after one retry | code line from the top two material changes, status `code_line_fallback` |

Use the config pronoun. Code lines are templates; write them in code.

### 7.2 What the LLM sees: the "gist view" (no numbers)
Build it from the stored facts with all digits removed. Use words:
- tags as `{measure, direction, size}`
- frequencies as words: "on one day", "on a few days", "on most days", "every day"
- medicines named with a frequency word
- diary entries: category, text, severity note (the text may contain digits; the model must not repeat them)
- co-movement lists, material-change types (not counts), reliable yes/no, and plain data-quality notes (e.g., "one questionable glucose reading was removed")

Never include dates, counts, numeric values, field names, or internal labels in the view. The one allowed digit token is `HbA1c`.

**Additions after Stage C (these are in the code and tested):**
- `top_items` is the first key of the view: up to three items in words, one per kind, in this order: (a) the diary theme, the most severe entry that is moderate or worse; (b) missed medicines with frequency words; (c) anchors crossed and large changes together, ordered by size with large first; (d) status deviations. The headline must cover the first item (system prompt rule 12).
- The glucose measure is named "average glucose" in the view, tags and checker aliases (bare "glucose" stays an alias so claims are still checked).
- Wording size floor: a measure that crossed an anchor is worded, and checked, as at least `gist.anchor_size_floor` (moderate). The stored tag is unchanged.
- Reliability appears only when it is "no". A place appears only when it is not one of her `gist.usual_place_count` (2) most frequent places before the window.
- Blood pressure appears as a status deviation ("on a few readings"); the month view adds long-standing patterns (non-normal on most days), the HbA1c versus glucose-based estimate line ("HbA1c is higher than the glucose-based estimate (they differ)"), and the categories of less serious diary entries as words. A month drops an unusual-status item that a long-standing pattern already covers.

### 7.3 Word rules (size label → allowed wording)
| size | direction words allowed |
|---|---|
| small | "a little", "slightly" |
| moderate | "clearly", "noticeably" |
| large | "sharply", "markedly", "much" |
| none / flat | "steady", "unchanged" (only in the unremarkable summary, never as a standalone sentence about a flat measure) |

### 7.4 Output checks (these four only)
1. **Direction and size words agree with the tags.** Bind a direction word to the nearest preceding measure *in the same clause*; a direction word with no measure in its clause binds to nothing. Match measures by longest phrase first ("glucose variability", "average glucose", "post-meal glucose peak" are separate measures). A claim about a measure whose tag is `not_enough_data` is a failure.
2. **No causal language:** stems caus*, trigger*, "led to", "resulted in", "results in", "as a result", "due to", because, explains, attributable, "driven by", responsible, "thanks to", affected, impacted, influenced, contributed. (The bare stem result* is not on the list: "follow-up results were reassuring" is not causal.)
3. **No digits, dates, month names, or quoted text** (including any run of five or more words copied from a diary entry), and none of the internal words: anchor, tag, stream, record, field, flag, window, tier, notable, direction table.
4. **Structure:** valid JSON, headline of at most 15 words, 2 to 4 sentences, nothing else.

Also rejected (check 3 wording): "tentative", "tentatively", "uncertain", unless the view says the window is not reliable. A phrase like "fell below / rose above / was above / was below the reference range" is a status, not a trend: the verb is not read as a direction word. Non-breaking and look-alike hyphens (U+2010, U+2011, U+2012, U+FE63, U+FF0D) are read as hyphens.

Matching details (code): text and measure phrases are normalised the same way (lower case, possessives removed, plurals reduced to a singular stem, hyphens read as spaces), so "post-meal glucose peaks" is one measure and the longest phrase wins in every form. Ambiguous aliases (blood sugar, activity, stress) are not aliases. The month lab line has its own measure names (`gist.unchecked_measures`) that are recognised but never compared with a direction tag. Code finishes the headline (capital letter, full stop) before the checks run. Digits: only the token `HbA1c` is allowed.

Do not add other checks. Log every rejection with its reason. If week-tier fallbacks exceed 10% of attempted windows, make the sentence-level direction check a warning (logged and counted) and keep it strict for the headline. This needs no new approval.

### 7.5 Prompts

**System prompt (use verbatim):**
```
You write a short plain-words summary of one time window in a person's health record. The person has diabetes.

You receive a GIST VIEW: a list of measures with direction and size, which measures moved with or against glucose, medicines missed, unusual statuses, diary entries, and data-quality notes. All numbers were removed on purpose. Code already stores every number.

Write:
1. headline: one sentence, at most 15 words.
2. sentences: 2 to 4 short sentences.

RULES. Follow all of them.
1. Do not write any digit, date, month name, count, or number word used as a count. Say "on a few days", "most days", "sharply", not figures.
2. Use only the facts in the GIST VIEW. Do not invent settings, reasons, or details. In particular, do not say where or how something was measured unless the view says so.
3. Direction words (up, down, higher, lower, rose, fell, more, fewer) must match the direction given for that measure, and intensity words must match its size: small = "a little" or "slightly"; moderate = "clearly" or "noticeably"; large = "sharply", "markedly" or "much". Never describe a measure whose direction is "not_enough_data".
4. One measure per direction claim. Do not write one direction word that covers two measures.
5. Describe relationships only as co-occurrence: "alongside", "while", "in a week when", "at the same time as". Never use: caused, because, due to, led to, resulted in, triggered, explains, driven by.
6. If the view contains diary entries, name the main theme in plain words in the headline (for example "a family member's hospitalization" or "a work trip"). Paraphrase. Do not quote the diary. Do not repeat numbers or dates from it.
7. Mention every missed medicine and every unusual status in the view that matters to the picture. Do not mention measures that are steady.
8. If the view says the window is not reliable, say that comparisons are tentative.
9. Do not give advice, diagnoses, or predictions.
10. Do not use these words: anchor, tag, stream, record, field, flag, window, tier, notable.
11. Refer to the person with the pronoun in the view.
12. The headline must cover the first item in TOP ITEMS; mention the others in the sentences.

Return only JSON: {"headline": "...", "sentences": ["...", "..."]}
```

**User prompt template:**
```
TIER: {tier}
PRONOUN: {pronoun}

TIER GUIDANCE:
{tier_guidance}

GIST VIEW:
{gist_view_json}
```

**Tier guidance (insert the matching one):**
- **day:** "Say what stood out about this one day: what changed against the previous day, which medicine was missed, and what the diary says. Keep it to what is in the view."
- **week:** "Say what the week looked like overall and what moved with or against glucose. If there were diary entries, give the main theme. Do not list single days."
- **month:** "Say how the period compares with the previous checkpoint and how the long-run picture looks. If a lab result and the glucose-based estimate differ, say they differ, in words only. Name any measure that has been non-normal on most days as a long-standing pattern."

**Batching:** several windows per call are allowed. Send them as `{"1": view, "2": view, ...}` and require the same keys back, `{"1": {"headline": ..., "sentences": [...]}, ...}`. Parse by key. A missing key counts as that window's failure and is retried alone.

**Retry addendum (appended on the single retry, with the specific failures):**
```
Your previous answer failed these checks: {failure_list}.
Rewrite it. Keep to the facts in the view. Do not use digits or dates. Make every direction word match the stated direction and size for its own measure.
```

**Format-only example (placeholders, not data):**
View: measures = glucose up (large), sleep down (large), medication adherence down (large), resting heart rate up (large); steps flat. Missed medicines: metformin on a few days. Diary: a symptom entry about a relative being tired, then entries about hospital days.
Output:
```json
{"headline": "A family member's hospitalization, with higher glucose, much less sleep and many missed doses.",
 "sentences": [
  "Glucose rose sharply while sleep fell markedly and resting heart rate rose sharply.",
  "Medication adherence fell markedly, with metformin missed on a few days.",
  "Diary entries describe a relative falling ill and spending several days in hospital."]}
```

---

## 8. Storage

New table; the old tables stay.

```sql
CREATE TABLE memory_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_id TEXT UNIQUE,
    tier TEXT, start_date TEXT, end_date TEXT,
    reliable INTEGER, confidence TEXT,          -- computed in code from reliability and completeness
    facts_json TEXT,                            -- all code-computed facts
    tags_json TEXT,                             -- direction tags with size labels
    material_changes_json TEXT,
    anchors_crossed TEXT, anchors_questionable TEXT,
    is_notable INTEGER, notable_reason TEXT,    -- code only
    deviation_text TEXT,                        -- code-rendered, human-readable
    data_quality_json TEXT,
    gist_headline TEXT, gist_sentences TEXT,    -- LLM or code line
    gist_status TEXT,                           -- gist_ok | gist_retry_ok | code_line_early | code_line_quiet | code_line_week_skipped | code_line_fallback
    llm_raw TEXT, usage_json TEXT,
    config_version TEXT
);
```

**Retrieval (return parsed objects, not raw rows):**
- `get_memory(tier, date)`
- `get_memories_between(start_date, end_date, tier)`
- `get_notable(tier, since_date)`
- `get_profile_asof(stream, date)`

Default returns exclude `facts_json` unless `full=True`. The gist text is stored separately so it can be embedded later (do not build embeddings now).

---

## 9. Run behaviour

- Stages are resumable and idempotent; save after each batch.
- 90-second timeout per call, SDK retries 0, one explicit retry per failed window, `reasoning_effort: low`, usage (input, output, reasoning tokens) and wall time logged per call.
- The default command never wipes data. Rebuilding needs an explicit flag.
- Stop and report if first-attempt gist failure exceeds 25% in a tier after the early days, or if the digit/date check fails on an accepted entry.
- Stage D (`python -m v0_code.baseline_v2.stage_d`): day, then week, then month, in waves (`gist.wave_windows`), batch sizes 4, 2, 1, saved after every window; resumable and idempotent. After the first 40 day windows five entries are printed as a checkpoint and the run continues. If fallbacks exceed 10% of attempted windows the sentence-level direction check becomes a counted warning (the headline stays strict) and the run continues. `--reset-gists` returns model-written gists to pending to regenerate them under a changed prompt or view.

---

## 10. Tests (write these first)

**Invariants, run over every window:**
- every missed dose in a window appears in its material changes and deviation text
- every diary event in a window appears in deviation text, verbatim and dated
- no window's output depends on data dated after its end date
- a questionable reading never appears in any computed metric, delta, anchor or tag
- `is_notable` is false when `anchors_crossed` is empty
- best day and worst day differ unless all days tie; worst mood ranks by distress
- a direction word never binds to a measure it isn't attached to (cover: "slightly higher blood pressure", "more activity", "more stress", "glucose variability fell", "estimated glucose", "post-meal glucose peak")

**Per anchor:** fires on a synthetic window that should trigger it; silent on a quiet one.

**Golden windows (this patient's data):**
- the week ending 2025-11-22 shows sleep down, adherence down, resting heart rate up, glucose up, and a diary theme about a relative's hospitalization in the gist
- the week ending 2025-12-09 is not notable
- the day 2025-12-26 lists the missed metformin dose
- the day 2026-04-23 lists the removed 590 reading and is not notable from it

**Fixture patient:** build a tiny patient with 2 medications, no mood stream, UTC+0 timezone, pronoun "he", and different step floors. The engine must run with config changes only. Report any code edit needed to make it pass. Add it to the suite.

---

## 11. Build order and gates

**Stage A (no LLM):** profile, day tier facts, material changes, tags, trust layer, anchors, storage, retrieval. Run all days. Report: quiet fraction, fire rates, dead anchors, flagged windows. **Stop.** I hand-read 10 day entries.

**Stage B (no LLM):** week and month tiers. Report the same. **Stop.** I hand-read 10 more.

**Stage C (LLM, small sample):** about 12 windows chosen across tiers, including the golden windows and two diary-heavy days. Show gist views, outputs and validation. **Stop.**

**Stage D (full gist run):** day, then week, then month, in one run if no stop rule fires. Report once at the end.

Between stages: no design changes. Fix bugs with a failing test first. Park everything else.

## 12. Report after each stage

Counts by tier and status; quiet fraction; fire rate per anchor and tier; dead anchors; first-attempt and final gist failure rates and reasons; calls, tokens (including reasoning), time; five random full entries per tier; list of parked items; the known upstream data issues from Section 5.

## 13. Out of scope

Clinical metric sets beyond glucose (BP staging, sleep regularity), embeddings and similarity search, Findings Engine, episodic write-back, any change to upstream components, retuning anchors.

## 14. Defaults assumed for the open decisions (change in config, not code)

1. LLM gist runs only on windows with material changes; others get code lines.
2. Rolling weeks are computed for every day in code; the gist runs only for weeks ending on `week_gist_weekday` or with an anchor crossed.
3. The device range and step-change rule handle the 590/599 artifacts. Lowering the Plausibility Filter's glucose ceiling is a separate upstream decision.
4. Reuse verified v1 modules; do not start from a blank repo.