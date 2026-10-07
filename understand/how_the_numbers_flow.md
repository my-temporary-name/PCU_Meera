# How the numbers flow through the pipeline

A running note, one section per component, so that at the end we can see how every number was transformed from the raw readings to the final notes. Each section says what the component does, which numbers come in, which go out, and exactly why they differ. Every figure was read from the pipeline's own outputs (`output/*.csv`, `output/*.db`) or from the dashboard data built from them. Nothing here is estimated.

Sections added so far: **1. Plausibility filter and Threshold evaluator**, **2. Short-range linker and Personal Data Store**, **3. Baseline Engine**, **4. State Engine**, **5. Rulebook Lookup**, **6. Evidence Engine**, **7. Findings Engine**, **8. PI**.

---

## The running chain (filled in as we go)

| # | Component | Comes in | Goes out | Why they differ |
|---|---|---|---|---|
| 1a | Plausibility filter | 77,797 raw readings | 77,792 passed, 5 rejected | 5 glucose readings above the 600 mg/dL ceiling |
| 1b | Threshold evaluator | 77,792 passed readings | 44,469 rows with a status | heart rate judged only at rest, hourly steps summed to days, weight has no range (see section 1) |
| 2a | Short-range linker | 44,469 status rows, of which 14,697 are glucose readings with status high (14,692) or low (5) | 138,118 pairings ("this happened nearby") | only high and low glucose is linked; each is checked against 8 kinds of nearby events and each match is a row |
| 2b | Personal Data Store | 44,469 status rows + 138,118 pairings, plus 45,952 context events | 182,587 rows in `raw_events` + 45,952 rows in `context_events` | 44,469 + 138,118 = 182,587; context events are a separate table |
| 3 | Baseline Engine | 44,469 status rows + 45,952 context events (the 138,118 pairings and the 8,160 hourly steps are not used) | 710 windows: 352 days, 346 weeks, 12 months; 590 with a model-written gist | days become values, windows are compared with her own usual; 105 day and 15 week/month windows get a code-written line instead of a model gist (see section 3) |
| 4 | State Engine | her usual from the Baseline plus the newest reading of 10 watched measures at each of 33,792 ticks | 565 deviation items (287 adverse, 278 favourable) and 287 alerts | an item opens only after the measure is at least "clearly" off her usual on two ticks in a row; only adverse items (the bad direction for that measure) become alerts (see section 4) |
| 5 | Rulebook Lookup | 287 alerts (hand-offs) | 287 packets (279 ok, 8 deferred) holding 1,899 selected candidate factors, 373 skipped, 153 not selected | one packet per alert; each alert matches one fixed rule; a candidate is skipped when it cannot apply to that alert (see section 5) |
| 6 | Evidence Engine | 287 packets (1,899 selected factors) plus her whole history | 22,148 daily relationship records (63 relationships x 352 days) and 287 alert evidence records (with 5 completions) | a relationship is tested only after 60 usable units and 60 distinct days, so October and November have none; 69 library entries give 49 runnable pairs, 63 after the meal-kind split (see section 6) |
| 7 | Findings Engine | 279 counted alerts (8 deferred ones do not count), their evidence records, diary, Baseline gists and PI's earlier notes | 116 cases and 284 versions (279 + 5 completions), each with a structured layer and a text (132 kept, 143 model-written, 9 code-line fallbacks) | alerts within 6 hours join one case (at most 36 hours); each arrival makes a new version; code decides what may be said, a model only words it (see section 7) |
| 8 | PI | 284 Findings versions (as entries) plus the Evidence Engine's daily labels | 51 weekly memories, 29 long-term notes with 174 versions (25 supported, 3 candidate, 1 retracted at the end) | a note exists only for a relationship Findings used; a status changes only after 2 or more consecutive decisive weeks (see section 8) |

---

## 1. Plausibility filter and Threshold evaluator (component 1 of 8)

Dashboard page: `#/stage/threshold`. Outputs: `output/plausibility_filter_results.csv`, `output/threshold_evaluation_results.csv`. No model is used anywhere in this component.

### The two steps

1. **Plausibility filter.** Asks "could this reading be real?" It checks each raw reading against a fixed physical range for that measure (for example a glucose of 612 mg/dL). Output: pass or reject. It does not judge whether a value is good or bad for her.
2. **Threshold evaluator.** Asks "is this reading normal, high or low?" It compares each passed reading with a reference range and gives it a **status**: normal, borderline high, borderline low, high or low. The status is the label.

77,792 is how many readings passed step 1. 44,469 is how many received a status in step 2. Not every reading that passes can be given a status, which is why the second number is smaller.

### Step 1 in numbers

- **77,797 readings checked.** Every reading in her files for the year: 24 measures. Blood pressure such as "129/86" is split into a systolic and a diastolic reading, so it counts twice.
- **77,792 passed, 5 rejected.**
- **The 5 rejections** are all CGM glucose readings above the 600 mg/dL ceiling:

| When (IST) | Value (mg/dL) | Context found |
|---|---|---|
| 13 Oct 2025 15:00 | 612.0 | steps 107 in that hour, at the office, active |
| 5 Feb 2026 13:00 | 613.9 | steps 131, at the mall, active |
| 23 Jun 2026 11:00 | 603.5 | steps 151, home (working), active |
| 21 Jul 2026 13:00 | 611.0 | steps 176, home (working), active |
| 6 Sep 2026 11:00 | 614.2 | steps 90, at home, active |

  For each one the filter also looked at her context. A real glucose above 600 while she was walking around is not believable, so each was marked a **confirmed error**, not just flagged. A rejected reading goes no further.

### Step 2 in numbers: why 77,792 became 44,469

The gap is **33,323** readings. It comes from three places.

**1. Heart rate: 25,444 readings get no status.**
- Her watch records heart rate every 15 minutes: 33,792 readings in the year.
- The only reference range available is 60 to 100 bpm, and that is a *resting* range. A heart rate of 110 while walking is normal, not "high".
- So a heart-rate reading is judged only when she was at rest, meaning the step counter showed zero steps in that hour. That is 8,348 readings, mostly at night.
- The other 25,444 happened during activity, or there is no step record for that hour. They are counted as "not applicable" and get no status.

**2. Hourly steps: 8,160 readings become 340 rows.**
- Steps are recorded per hour (8,160 readings). Each hour is checked by the filter, but one hour of steps means nothing against a daily range.
- The evaluator therefore adds the hours into **daily totals** first and judges those: 340 daily step counts.
- 8,160 readings leave and 340 rows come in. The 12 days that have no hourly steps have no daily total either.

**3. Weight: 59 readings get no status.** Weight passes the filter, but there is no reference range for it.

### The arithmetic, measure by measure

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
| 11 lab results (HbA1c, total cholesterol, LDL, HDL, triglycerides, ALT, AST, GGT, creatinine, eGFR, fasting glucose), 4 draws each | 44 | 44 | 44 |
| **Total** | **77,797** | **77,792** | **44,469** |

Check: 33,576 + 8,348 + 340 + 1,761 (resting heart rate, sedentary, screen time, hydration, sleep) + 282 (blood pressure) + 118 (BMI, waist–hip) + 44 (labs) = **44,469**. And 77,792 − 44,469 = **33,323** = 25,444 heart-rate readings with no status + 8,160 hourly steps − 340 daily rows that replace them + 59 weights.

### What the statuses are

Each of the 44,469 status rows carries one of five labels:

| Status | Rows |
|---|---|
| borderline high | 18,397 |
| high | 15,194 |
| normal | 9,602 |
| low | 969 |
| borderline low | 307 |

Most of these are glucose. They use the **diagnostic fasting-glucose limits (70, 99 and 125 mg/dL)**, which are strict, so a lot of ordinary daytime glucose counts as borderline high or high. These statuses are not the same as the CGM management targets used by the Baseline Engine (time in range 70 to 180), so the two can disagree. This is intentional, not a bug.

### Things to remember about this component

- The glucose ceiling catches only gross errors. The specification expected about 12 injected glucose errors (one a month); the data has 5 above the ceiling. Two more spikes (599.0 and 590.0) sit just under it and pass.
- The specification's "22 Aug 2026 low glucose of 66.5" does not exist in the data (that day's minimum is 76.3, the year's minimum 65.0).
- `event_id` is not unique in the source files (ids restart each month), so a reading is identified by its id together with its timestamp.
- Name mapping: CGM glucose is judged against the fasting-glucose row, because there is no CGM row. Sex-specific rows (HDL, creatinine, waist–hip ratio) and age come from her own fact files.

### What goes to the next component

The 44,469 status rows are what the Linker and the Personal Data Store receive. Only glucose readings with status **high** or **low** are looked at by the Linker (borderline and fasting-glucose rows are excluded).

---

## 2. Short-range linker and Personal Data Store (component 2 of 8)

Dashboard page: `#/stage/linker`. Outputs: `output/short_range_pairings.csv` and `output/personal_data_store.db` (tables `raw_events` and `context_events`). No model is used. The linker never claims a cause: a pairing only says "this happened nearby".

### The three words

- **Pairing.** One row that links a glucose reading to something that happened near it in time, for example "glucose 128.6 mg/dL at 08:15 on 1 Oct, and breakfast (dosa, chutney, coffee) was 10 minutes before". Each pairing says what kind of thing it is (`candidate_type`), when it happened, and how many minutes it was from the glucose reading (`lag_minutes`).
- **Store rows.** The number of rows in the Personal Data Store's main table, `raw_events`. It holds exactly two kinds of row: the 44,469 readings that got a status in component 1 (every status, normal included) and the 138,118 pairings. 44,469 + 138,118 = **182,587**.
- **Context events.** The other things in her life that were recorded but are never given a status: heart rate, hourly steps, medication taken, mood, meals, location, sleep quality and diary entries. They are kept in a separate table, `context_events`, 45,952 rows, so the linker (and later components) can look things up in them.

### Step 1: which glucose readings are linked

Only CGM glucose readings whose status is **high or low** are linked.

| Glucose status from component 1 | Readings | Linked? |
|---|---|---|
| borderline high | 18,120 | no |
| high | 14,692 | yes |
| normal | 759 | no |
| low | 5 | yes |
| **Linked** | **14,697** | |

So 14,697 glucose readings are checked. Borderline readings and the separate fasting-glucose lab results are deliberately left out.

### Step 2: what each glucose reading is checked against

For each of the 14,697 readings the linker looks for eight kinds of nearby events and writes one row per match:

| Kind | What counts as nearby | Rows | How the rows arise |
|---|---|---|---|
| medication | a medicine logged that calendar day (the adherence record has no time) | 44,091 | exactly 3 per reading (she has 3 medicines): 14,697 x 3 |
| activity | an hour of steps that started up to 90 minutes before, with steps above 0 | 20,978 | one per matching hour, so a reading can have several or none |
| diary | the diary entry of that day | 14,697 | one per reading |
| heart rate | a summary (average, minimum, maximum, count) of the heart rate within 2 hours either side | 14,697 | one per reading |
| mood | the mood record for that part of the day (morning, afternoon or evening) | 14,697 | one per reading |
| sleep | the sleep record of the night before | 14,697 | one per reading |
| meal | a meal up to 150 minutes before | 8,370 | one per matching meal |
| context event | an event logged the same calendar day | 5,891 | one per matching event |
| **Total** | | **138,118** | about 9.4 pairings per glucose reading |

The four kinds that have exactly 14,697 rows are the ones that always match once per reading. Medication is always 3 per reading because three medicines are logged every day. Meals, activity and context events vary, because they only produce a row when something nearby exists.

### Step 3: what the store holds

`raw_events` (182,587 rows):
- 44,469 rows with `source_type = reading` (the status rows from component 1);
- 138,118 rows with `source_type = pairing`.

`context_events` (45,952 rows), by stream:

| Stream | Rows |
|---|---|
| continuous heart rate (every 15 minutes) | 33,792 |
| hourly steps | 8,160 |
| medication adherence | 1,056 (3 medicines x 352 days) |
| mood state | 1,056 (3 time blocks x 352 days) |
| meal events | 1,055 |
| location | 352 |
| sleep quality | 352 |
| diary entries | 129 |
| **Total** | **45,952** |

These are readings the pipeline already parsed. They are written as they are, and nothing is computed on them here.

### Which things are always paired, and which depend on the data

Two levels, one fixed and one dynamic.

**Fixed: what is checked.** For every high or low glucose reading the linker always checks the same eight kinds of nearby events. The list was agreed in conversation (it is not in `task/`), and the time windows are fixed numbers: 150 minutes for a meal, 90 minutes for activity, 2 hours either side for heart rate, the same calendar day for medication, diary and context events, the night before for sleep, and the part of the day for mood. There is no learning and no model, so the same reading with the same surroundings always gets the same pairings.

**Dynamic: whether a row is written.** That depends on what actually happened near the reading:

| Behaviour | Kinds | Rows per glucose reading |
|---|---|---|
| Always exactly one | heart rate (a summary), mood, sleep, diary | 1 each (14,697 each) |
| Always exactly three | medication (she has three medicines, each logged every day) | 3 (44,091 in all) |
| Zero, one or several | meal, activity, context event | one row per matching meal, active hour or event; most readings have no meal in the previous 150 minutes (8,370 meal rows for 14,697 readings) |

What the row says (for example "breakfast: dosa, chutney, coffee" or "metformin taken") comes from that moment's data.

**What is not dynamic.** The linker does not choose which kinds to look at based on the glucose value (a reading of 130 and a reading of 250 are checked against the same eight kinds). It does not rank or filter pairings by relevance, and it does not say which one mattered. Choosing what deserves attention happens later: the Rulebook Lookup picks candidate factors for each alert, and the Evidence Engine tests them on her own history.

### Things to remember

- A pairing is not a cause. It is only "this was nearby", and later components decide whether it matters.
- Ids repeat across the year (for example glucose ids restart each month), so a pairing is keyed by the glucose reading's id **and** its timestamp. 14,697 distinct readings produce the 138,118 pairings.
- The Personal Data Store only stores and returns rows; it computes nothing. The Baseline Engine, the State Engine and the later components read from it.
- The hourly steps (8,160 rows) sit in `context_events` only so the Rulebook can later look up activity by the hour; the Baseline and State engines do not use that stream.

### What goes to the next component

The store (`raw_events` and `context_events`) is what the Baseline Engine reads, to build its day, week and month windows. The pairings are kept in the store for later lookup; the Baseline Engine does not use them.

---

## 3. Baseline Engine (component 3 of 8)

Dashboard pages: `#/stage/baseline` and `#/baselines` ("Her baseline"). Output: table `memory_v2` in `output/personal_data_store.db`. Code is deterministic Python except one step, the gist, where a model words facts that code has already decided.

### What comes in from component 2

The engine reads only the store, and only two tables of it. It re-reads no source file, and it never sees alerts.

| From the store | Rows | What the engine takes |
|---|---|---|
| `raw_events` where `source_type = reading` | 44,469 | time, measure, value and status |
| `context_events` (all streams) | 45,952 | stream, time, date, text, number, category and extra details |

Not used: the **138,118 pairings** (the Baseline and State engines do not refer to them) and the **8,160 hourly steps** in the context table (they are for the Rulebook; the Baseline uses the 340 daily step totals from the status rows).

**Where the 45,952 context events come from.** It is a plain copy of eight source files, reshaped into one layout. Nothing is computed or matched.

| Stream | Source file | Rows | Why that count |
|---|---|---|---|
| Continuous heart rate | `continuous_heart_rate_yearly.csv` | 33,792 | 352 days x 96 readings (every 15 minutes) |
| Hourly steps | `steps_hourly_yearly.csv` | 8,160 | 340 days x 24 hours (12 days have none) |
| Medication adherence | `adherence_yearly.csv` | 1,056 | 352 days x 3 medicines |
| Mood | `cognitive_mental_health_full_year.csv` | 1,056 | 352 days x 3 time blocks |
| Meals | `meal_events_yearly.csv` | 1,055 | about 3 meals a day (347 days have 3, 3 days have 2, 2 days have 4) |
| Location | `location_full_year.csv` | 352 | one per day |
| Sleep quality | `sleep_yearly.csv` | 352 | one per night |
| Diary entries | `context_events_yearly.csv` | 129 | the diary's event log |
| **Total** | | **45,952** | |

**What the three groups of leftover rows are** (this answers "were they not linked, or not labelled?"):

| Group | Rows | What happened |
|---|---|---|
| Status rows, not linked | 29,772 | they got a status but are not high or low glucose, so the linker did not pair them (borderline and normal glucose, and every other measure) |
| Context events | 45,952 | never went through the status step: 4,000 things that cannot get a status by nature (medication 1,056, mood 1,056, meals 1,055, location 352, sleep quality 352, diary 129); 33,792 heart-rate readings (only 8,348 had a status because the range is for rest, the other 25,444 were saved here instead of being thrown away); 8,160 hourly steps (judged in the status table as 340 daily totals) |
| Dropped after the filter | 59 | weight readings passed the plausibility filter but have no reference range, so they were kept nowhere |

Nearly all of the 33,323 passed readings that got no status in component 1 end up in the context table (25,444 heart-rate readings and 8,160 hourly steps); only the 59 weights are lost.

### What the engine does with them, step by step

**Step 0. Load and group by day.** Every row is assigned to a local calendar day in her time zone: 352 days, 1 Oct 2025 to 17 Sep 2026.

**Step 1. Clean the glucose first.** A glucose reading is removed before any metric is computed if it is outside the device range (40 to 400 mg/dL) or jumps more than 75 mg/dL per 15 minutes from the last kept reading (scaled by the gap). Only the earlier readings are looked at. Across the year, **3 readings** were removed, on 3 days; one is the 599.0 spike on 9 Dec, which passed the plausibility filter's 600 ceiling. Five isolated readings of exactly 65.0 still pass both rules (a known limit, reported and not patched). The raw values are recorded, and a twin set of metrics shows what they would have been with the removed readings included.

**Step 2. Turn each day into a handful of numbers.**

| From | What a day becomes |
|---|---|
| CGM glucose (about 96 readings) | average, time in range (70 to 180), time above (180 and 250) and below (70 and 54), variability (CV), estimated HbA1c (GMI), lowest and highest |
| Meals + glucose | the post-meal peak (up to 150 minutes after a meal) |
| Continuous heart rate (96 context readings) | the day's average |
| Resting heart rate, sleep, daily steps, sedentary time, hydration, screen time | the day's own value |
| Medication taken or missed (3 a day) | adherence % and which medicine was missed |
| Mood (3 blocks a day) | the number of strained blocks (mild stress, tired, anxious, overwhelmed); calm and uplifted do not count |
| Status rows | the day's status: the most common status among that day's readings |
| Diary, location, sleep quality, blood pressure | listed as context for that day |

Each stream also gets a completeness figure against its expected readings per day (for example 96 for glucose and heart rate, 3 for mood), so a gappy day is marked. A missing step hour is unknown, never zero.

**Step 3. Her usual, as of each day.** For each measure: the median, the standard deviation and a flat band (half a standard deviation), computed only from the days strictly before the window, so nothing ever uses later data. It needs 14 days of history before it trusts the figure (before that the record says "learning"). From the status rows it also records her usual status against clinical limits and how often she is outside them (for example steps low on 98% of days, sedentary time high on 95%).

**Step 4. Build the windows.**
- **Week:** the 7 days ending on each day from the 7th, **346** in all, compared with the 7 days before. A window's value is the mean of its daily values; glucose is pooled over the cleaned readings; adherence is taken over expected doses.
- **Month:** a checkpoint every 30 days plus a last partial one, **12** in all. It looks at the last 30 days and keeps the whole year so far in view, compared with the previous checkpoint. That is why every month record's stored start date is 1 Oct.

**Step 5. Label the changes.** Each change against the previous window is compared with her own flat band and becomes flat, up or down, with a size: small, moderate or large. When glucose moved, the engine also lists which other measures moved the same way or the opposite way. This is a note that two things changed together, not a link.

**Step 6. Decide what is notable.** Configured thresholds are checked on the cleaned values: for example adherence dropping, steps crossing an absolute floor, sleep falling by hours, or a lab HbA1c differing from the glucose estimate. A crossing that exists only because of a bad reading is set aside and not counted. A window with at least one crossing is notable.

| Tier | Windows | Notable | Quiet (nothing material) |
|---|---|---|---|
| Day | 352 | 67 | 91 |
| Week | 346 | 79 | 0 |
| Month | 12 | 4 | 0 |
| **Total** | **710** | | |

**Step 7. List the material changes.** For each window the engine builds a typed list: thresholds crossed, every missed dose, diary entries, statuses worse than her usual, large changes and data gaps. A window with an empty list is quiet. A week or month aggregates the lists of its days (for example "missed on 6 of 7 days").

**Step 8. The gist.** The only step with a model (see below).

### What the engine outputs

One record per window in `memory_v2`:

| Part of the record | What it is | Example (week of 11 to 17 Sep 2026) |
|---|---|---|
| Numbers | the window's value for each of 13 measures, plus the previous window's values | resting heart rate 88 bpm, previous week 80 |
| Glucose detail | average, GMI, time in range, time above and below, variability, lowest, highest, completeness | average 134, time in range 98.6%, 655 readings, 97% complete |
| Her usual | median, spread, flat band and number of days for each measure, from earlier days only | resting heart rate usual 76, ± 5, from 345 days |
| Directions | each change against the previous window: flat, up or down, with a size | heart rate up 17 bpm (large); sleep down 1.4 h (moderate) |
| Notable flag and reason | which thresholds were crossed, decided by code | adherence down 52 points; steps up 2,545 |
| Material changes | a typed list | metformin missed 6 of 7 days; three diary entries |
| Data quality | questionable readings removed, reliable flag | none removed; reliable |
| Moved together | the other measures that moved with glucose, when glucose moved | listed only when glucose moved |
| Gist (text) | a headline and a few sentences worded from the facts | "Missed medicines during festival preparations and deadline pressure." |

It outputs numbers, directions, flags and a short text. It does **not** output relationships or causes ("moved together" is only a note), and it is not the PI memory: the "memory" here is a summary of what happened in each window. The factor-to-outcome relationships come later, from the Evidence Engine.

### The gist: what the model gets and which windows get it

The model does **not** receive the whole record. The code builds a reduced "gist view":
- no digits at all: counts and frequencies become words ("most days", "a few days"); a test checks every queued window (the word HbA1c is the one allowed exception);
- only measures that moved, each with a direction and a size word;
- a priority list first: serious diary themes, then missed medicines, then large changes and crossed thresholds, then statuses worse than usual; the headline must cover the first item;
- context lines: diary themes, the places she was (only when not among her two most common), and for months any long-standing patterns and the lab-versus-estimate line.

It does not receive her usual, the flat bands, the daily trajectory or the data-quality internals. The notable flag and its reason are never written by the model.

| Tier | Windows | Code-written line (no model) | Sent to the model | Passed first try | Passed after a retry |
|---|---|---|---|---|---|
| Day | 352 | 105 (14 too early + 91 quiet) | 247 | 225 | 22 |
| Week | 346 | 14 (too early) | 332 | 295 | 37 |
| Month | 12 | 1 (too early) | 11 | 8 | 3 |
| **Total** | **710** | **120** | **590** | **528** | **62** |

- Model: `openai/gpt-5-mini` with low reasoning, through OpenRouter; batches of 4 days, 2 weeks or 1 month per call.
- Four checks on every answer: direction and size match the facts; no causal words; no digits, dates, quotes or internal words; correct structure.
- One retry with the failures appended; a window that still fails gets a code-written fallback line. In the final store there are **0 fallbacks**.
- The model returns only a headline and sentences. Every fact was decided by code.

### Who uses the output

- The **State Engine** reads her usual (median and spread) to decide when a reading is off.
- The **Findings Engine** reads the day and week gists as context for a case.
- The dashboard's **Her baseline** page shows the numbers, her usual, the directions and the gist.

### How and when the Baseline Engine updates itself

- **Data drives it, alerts do not.** The engine reads only readings and context from the store. It never reads an alert, a finding or a PI note, so nothing downstream can change a baseline number. The order is the other way round: the State Engine compares a reading with the baseline and raises an alert when it is off.
- **New days of data are what changes it.** Each new day adds its readings and context to the store. When the engine runs, it builds that day's window, the week window ending that day and, every 30 days, a month checkpoint.
- **Her usual shifts as days accumulate.** The usual for any day is the median and spread of the days before it, so every new day nudges it slightly. Every window records the usual as it was known on its own date, which is why the usual line on the "How her baseline moved" chart drifts through the year.
- **It is a batch build, not event-driven.** Nothing triggers it except running the engine. The day windows are recomputed identically each time, so a rebuild writes the same results.
- **A window is never compared with itself.** A window's values affect only the usual of later windows.
- **Re-running keeps old gists.** When a window already has a model-written gist, an upsert keeps it. The engine does not yet detect that the underlying facts changed, so an old gist can survive a data change (a known, parked item).

**Do the values that caused an alert go into the baseline?** Yes. An alert is a derived record that the Baseline Engine never sees, but the readings behind it are ordinary rows in the store, and the engine cannot tell which ones triggered an alert. So the baseline is built from everything: calm days, bad days and the readings that triggered alerts. The only values kept out are glucose readings removed as artefacts (outside 40 to 400 mg/dL, or an impossible jump). One reading barely moves the median, but a persistent pattern does: if she stays off her normal for a long stretch, her usual drifts toward the new level, and the same reading then produces a smaller alert later.

### Things to remember

- Her "usual" is her running history up to that day. It includes her bad stretches (the hospital week, the missed-medicine months). It describes how she has typically been so far, not necessarily how she is when well, and it is not a fixed reference period.
- Glucose here uses the CGM management bands (70, 180, 250, 54). The status rows from component 1 use the diagnostic fasting bands (70, 99, 125). The two disagree by design.
- The Baseline Engine has no time-of-day or post-meal patterns and no blood-pressure usual; the State Engine computes those from earlier readings.
- Of the 138,118 pairings and the 8,160 hourly steps, nothing reaches the Baseline Engine.

### What goes to the next component

The 710 windows are written to `memory_v2`. The State Engine reads her usual from them to compare the latest reading of each measure and open deviation items; the Findings Engine reads the gists later as context.

---

## 4. State Engine (component 4 of 8)

Dashboard page: `#/stage/state`. Output: `output/state_engine.db` (tables `state_log`, `state_items`, `state_handoffs`; its own file, never the store). No model is used. The engine compares the latest reading of each watched measure with her usual from the Baseline Engine, opens an item when a measure stays off her usual, and writes one hand-off (an alert) for each adverse item. It reads the store and the Baseline windows read-only, and writes nothing back.

### What comes in

- **From the Baseline Engine:** her usual (median and spread) for each measure, as of each day, from `memory_v2`.
- **From the store:** the newest available reading of each watched measure.
- **From config:** which direction is bad for each measure, and how many ticks in a row it must stay off (`config/state_meera_iyer_v1.yaml`).

### What a tick is

A tick is a moment in time, not a reading. The year is replayed as **33,792 ticks**, one every 15 minutes from 1 Oct 2025 00:00 to 17 Sep 2026 23:45 (352 days x 96). At each tick the engine looks at the newest available value of every watched measure. Glucose and heart rate have a new value at every tick; the daily measures have a new value once a day, and in between the engine keeps the last one. A continuous value older than its freshness limit is stale, and a daily or periodic value is overdue after 1.5 times its normal cadence; about 19% of ticks had at least one stale or overdue measure.

### What it watches (12 streams in config, 10 can open items)

| Measure | New value | Her usual is based on | Bad direction | Items | Adverse |
|---|---|---|---|---|---|
| Glucose | every 15 min | time since her last meal (clock time as a fallback) | above | 285 | 104 |
| Heart rate | every 15 min | the same time of day on earlier days | above | 173 | 124 |
| Resting heart rate | daily | the Baseline's median and spread | above | 26 | 12 |
| Medication taken | daily, at 21:00 | her earlier days, by percentile | below | 24 | 24 |
| Screen time | end of day | the Baseline's median and spread | above | 14 | 8 |
| Blood pressure | about every 3 days | her earlier readings | above | 10 | 3 |
| Sleep | daily | the Baseline's median and spread | below | 10 | 10 |
| Sedentary time | end of day | the Baseline's median and spread | above | 9 | 0 |
| Steps | end of day | the Baseline's median and spread | below | 9 | 0 |
| Hydration | end of day | the Baseline's median and spread | below | 5 | 2 |
| **Total** | | | | **565** | **287** |

Glucose and heart rate account for 458 of the 565 items. Two streams are listed but never opened: **mood** (a label with no usual and no direction, three records a day) and **HbA1c** (a lab every 90 days with no usual). **Meals and diary** are context only, used to describe an item, never compared. Everything else in the store (the other labs, BMI, weight, waist-hip ratio, the hourly steps) is not watched.

### What "spread" is and where it comes from

Her spread is the standard deviation (the population one, the same definition the Baseline uses) of her own earlier values for that measure. It is how much the measure normally wobbles. It is not a textbook value.

- **Heart rate:** the engine takes her earlier heart-rate readings from within 30 minutes of the tick's time of day (wrapping around midnight), excluding the tick's own day. The median is her usual and the standard deviation is her spread. At 22:45 (the engine's own check against the specification) the usual was about 74.4 bpm and the spread about 9.6.
- **Glucose:** the usual depends on how long since her last meal of that kind (nearest 15-minute bucket, up to 180 minutes), with a clock-time fallback. At 22:45 the usual was about 124.9 mg/dL and the spread about 16.6, from 1,733 earlier readings.
- **Daily measures:** the Baseline's median and spread for that day, from the days before it. Blood pressure has no Baseline profile, so its usual is computed from her earlier readings (it needs 14).
- A usual built on fewer than 30 readings (reading-level) or 14 earlier days (profile-level) is left empty, so nothing is judged. A value never sits inside its own usual: an end-of-day value is judged against the profile as of the start of its own date.

### How far off is "off": position

Position is `(value - usual) / spread`, in units of her own spread:

| Label | How far from her usual |
|---|---|
| within | under 1 spread |
| slightly | 1 to 2 spreads |
| clearly | 2 to 4 spreads |
| far | 4 or more |

For example, a heart rate of 95 at 22:45 is about (95 - 74.4) / 9.6 = 2.1 spreads above her usual, so "clearly" above. These labels are not the Baseline's size labels (which use half a spread), so the same word means a different distance.

### How an item opens and closes (persistence)

- **Open:** a measure at least "clearly" off her usual in the same direction on **two ticks in a row** (one reading is enough for the daily and periodic measures, which have one new value a day or less). A reading that is "far" off opens an item at once (a severe item).
- **Close:** the measure is back to "slightly" or better on two ticks in a row (one for the daily measures).
- **Stale or overdue** values close an item too, with a different close reason.
- The time recorded for an item is the moment the triggering value became available, not the tick that noticed it.

One item is one episode, however long it lasts.

### Adverse versus favourable (this is direction, not recovery)

- Each measure has one direction that is bad for her (the table above). A deviation in that direction is an **adverse** item; a deviation in the other direction is a **favourable** item (for example heart rate far below her usual, glucose below her usual, steps well above her usual).
- It is not about how many times it happened, and it is not recovery. Moving back toward her usual is simply how any item **closes**: 557 of the 565 closed because the value recovered.
- Only adverse items become alerts. A favourable item is recorded but handed on only if it is far off or abnormal on that side (a status of low or high). None was, except **5 glucose lows**, which are counted as adverse.

### The numbers

| Count | Number |
|---|---|
| Ticks | 33,792 |
| Items | 565 |
| Adverse items | 287 |
| Favourable items | 278 (no hand-off) |
| Hand-offs (alerts) | 287 (one per adverse item) |
| Hand-offs opened by persistence | 264 |
| Hand-offs opened as severe (far) | 23 |

How the items ended: 557 recovered, 1 expired, 1 stale, 6 were still open at the end of the data. Adverse items stayed open about 9.7 hours on average (favourable about 10.4 hours).

By measure and direction:

| Measure | Direction | Items | Adverse | Favourable | Alerts |
|---|---|---|---|---|---|
| glucose | above | 99 | 99 | 0 | 99 |
| glucose | below | 186 | 5 | 181 | 5 |
| heart rate | above | 124 | 124 | 0 | 124 |
| heart rate | below | 49 | 0 | 49 | 0 |
| resting heart rate | above | 12 | 12 | 0 | 12 |
| resting heart rate | below | 14 | 0 | 14 | 0 |
| medication taken | below | 24 | 24 | 0 | 24 |
| screen time | above | 8 | 8 | 0 | 8 |
| screen time | below | 6 | 0 | 6 | 0 |
| sleep | below | 10 | 10 | 0 | 10 |
| blood pressure | above | 3 | 3 | 0 | 3 |
| blood pressure | below | 7 | 0 | 7 | 0 |
| steps | above | 9 | 0 | 9 | 0 |
| sedentary time | below | 9 | 0 | 9 | 0 |
| hydration | above | 3 | 0 | 3 | 0 |
| hydration | below | 2 | 2 | 0 | 2 |

By month (alerts, which are the adverse items): October 40, November 41, December 15, January 46, February 31, March 54, April 17, May 1, June 3, July 6, August 2, September 31. The favourable items are most common from April to August (for example 109 in August, almost all glucose below her usual).

About the 33,792 ticks: 22,067 (65%) had no open item; at most 9 items were open at once, and the average was about 0.7.

### Things to remember

- A tick is a moment, not a reading; glucose and heart rate are the only measures with a new value at every tick.
- Hourly steps are not in the store the engine reads from, so steps are a daily measure here.
- The State Engine never writes back to the store or to the Baseline; the Baseline never reads an alert.
- The specification's worked example reproduces (items open and close at 21:45, 22:30 and 23:00); differences and assumptions are in `docs/state_engine_notes.md`.

### What goes to the next component

The 287 alerts (hand-offs) go to the Rulebook Lookup, one packet per alert, matched by the hand-off id. The 278 favourable items stay in the State Engine's own database.

---

## 5. Rulebook Lookup (component 5 of 8)

Dashboard page: `#/stage/rulebook`. Output: `output/rulebook_lookup.db` (table `rulebook_packets`) and `output/rulebook_lookup_report.md`. Rulebook data: `task/evidence_engine/rulebook_v0_rules.csv` (10 rules), `rulebook_v0_candidates.csv` (69 candidates) and `rulebook_v0.md` (the sources). Config: `config/rulebook_meera_iyer_v1.yaml`. The Rulebook Lookup is deterministic, stateless and uses no model. It reads no data and writes no conclusion. It is a lookup that answers one question for each alert: **which factors should be checked as possible background for this alert?**

### What comes in and what goes out

- **In:** the 287 alerts (hand-offs) from the State Engine. Each carries the measure, direction, size, trigger, how many spreads off, the basis of her usual, the value, the clinical status, the time it opened and how long since her last meal.
- **Out:** exactly one **packet** per alert, so **287 packets**: 279 `ok` and 8 `deferred`. A packet is an ordered checklist of candidate factors, each with the check to run, the data it needs and the window to look in. A packet holds no data and no result.

### The rulebook: 10 rules, 69 candidates

The rulebook is a fixed table, written in advance from published clinical-education sources (version `v0-draft-1`, marked unreviewed). It was not learned from her.

- **A rule** is one kind of alert: a measure and a direction. Glucose above is split by context, using the time since the last meal: a meal within 180 minutes, or no meal in that time. Each alert matches exactly one rule. The matching is mechanical, so the same alert always gets the same packet.
- **A candidate** is one factor worth checking for a rule, such as activity in the previous hour or short sleep the night before. Each rule has 2 to 10 of them, in a fixed order, in three weight tiers (primary, secondary, tertiary).
- **A budget** per rule caps how many candidates go into a packet: all the primary ones, up to a maximum of secondary and of tertiary, and a maximum in total.

| Rule | Alerts | Candidates | Budget (primary + secondary + tertiary, maximum) |
|---|---|---|---|
| Heart rate above | 124 | 9 | 3 + 3 + 2 (8) |
| Glucose above, no recent meal | 59 | 9 | 2 + 3 + 2 (7) |
| Glucose above, within 180 minutes of a meal | 40 | 10 | 1 + 5 + 2 (8) |
| Medication taken below | 24 | 6 | 2 + 3 + 1 (6) |
| Resting heart rate above | 12 | 7 | 2 + 3 + 1 (6) |
| Sleep below | 10 | 7 | 1 + 3 + 2 (6) |
| Glucose below | 5 | 6 | 2 + 3 + 1 (6) |
| Blood pressure above | 3 | 8 | 2 + 3 + 2 (7) |
| Hydration below | 2 | 5 | 2 + 2 + 1 (5) |
| Screen time above (deferred) | 8 | 2 | rule not switched on |
| **Total** | **287** | **69** | |

9 rules are active and 1 is deferred. A deferred rule still gets a packet, but it lists every candidate as "not selected, rule deferred" and nothing is tested. That is the 8 deferred packets and the 16 `rule_deferred` entries (2 candidates x 8).

### What happens to the candidates of each packet

| Group | Total | Meaning |
|---|---|---|
| Selected | 1,899 | 632 primary, 910 secondary and 357 tertiary. Each active packet has 5 to 8 selected: 66 packets have 5, 46 have 6, 43 have 7, 124 have 8 (279 in all) |
| Skipped | 373 | the candidate cannot apply to this alert (see below) |
| Not selected | 153 | 137 cut by the budget cap and 16 from the deferred packets |

About 14 of the 69 candidates are never selected for any alert. Every active packet carries `evidence_bar_hint: raised`, because more candidates are selected (5 to 8) than the evidence limit of 4, so the Evidence Engine will hold the results to a higher bar; the 8 deferred packets have `standard`.

### How a candidate is judged not suitable

The rule is static, but a candidate is skipped when it cannot apply to a particular alert. Two fixed checks decide it, in the rulebook's own mini-language, with no data analysis.

**Check 1: "applies only if".** Some candidates carry a condition, tested against the alert and her configuration:

| Condition type | Example | Decided by |
|---|---|---|
| Time of day | the dawn effect applies only if the alert opened between 04:00 and 09:00 | the alert's own opening time |
| Medicine class present | "other medications" applies only if she takes a glucose-raising medicine | her medicines in the config |
| Patient flag | "medication adherence" for glucose applies only if she takes a glucose-lowering medicine | the config, derived from her medicines or stated |
| Stream present | "cycle phase" applies only if a cycle stream exists | whether the config maps a stream for it |

Her medicines are set in `config/rulebook_meera_iyer_v1.yaml`: metformin counts as glucose-lowering, amlodipine as antihypertensive and levothyroxine as thyroid. None is glucose-raising, insulin, a sulfonylurea or a blood-pressure-raising medicine.

**Check 2: "requires these data streams".** Each candidate lists the data it needs. If her config maps none of it, the candidate is skipped with the reason "no stream".

**The 373 skips:**

| Skipped candidate | Alerts | Why it didn't apply |
|---|---|---|
| Caffeine (stimulants) | 124 (all heart-rate packets) | no data stream: there is no caffeine data anywhere |
| Other medications (glucose-raising) | 99 (all glucose-above packets) | she takes no such medicine |
| Cycle phase | 99 (all glucose-above packets) | no cycle stream in the store (see below) |
| Dawn effect | 43 of the 59 no-recent-meal packets | the alert did not open between 04:00 and 09:00 (the other 16 kept it) |
| Insulin or sulfonylurea | 5 (all glucose-below packets) | she takes neither |
| Blood-pressure-raising medicine | 3 (all blood-pressure packets) | she takes none |

124 + 99 + 99 + 43 + 5 + 3 = 373.

**The cycle data.** A cycle file exists: `final/menstrual_cycle_full_year.csv`, 352 daily rows (cycle day, phase, anovulatory flag, pregnancy status, menopause status). It is never copied into the store (the context ingest has no cycle stream, and the store holds 0 rows for it), so the Rulebook treats the cycle as unavailable. Ingesting it is a parked task. The file also says `menopause_status = peri`, so the evidence for a cycle-phase candidate is not established for her case. The TSH lab rows are in the same position: the lab file has them, the store does not, and the config maps them to nothing.

**Things the check does not do.**
- It does not ask whether there is enough history to test the candidate. That is the Evidence Engine's job, which is why a candidate can pass here and later be labelled "insufficient".
- The thyroid candidate for heart rate applies if she has a thyroid condition or takes a thyroid medicine. The "has a thyroid condition" flag is set to true from her persona document, because the data has no condition list. Levothyroxine would trigger it on its own.
- Hourly steps are an ingest-only stream used here: the heart-rate "activity" candidate resolves to hourly steps, with the daily step count as a fallback alternative.

### Static, with fixed conditions

- The 10 rules, 69 candidates, budgets and conditions are always followed. Nothing in the rulebook changes by itself.
- What varies between packets of the same rule is only which candidates survive the two checks, and the windows resolved from the alert's own time (for example "60 minutes before the alert opened").
- The rulebook decides only **which factors to check**. It says nothing about whether any of them matters for her.

### What goes to the next component

The packet's selected candidates go to the Evidence Engine, one packet per alert, matched by the hand-off id (`packet_<hand-off id>`). The Evidence Engine tests each candidate on her own history and writes 287 alert evidence records, plus its daily refresh of 22,148 relationship records.

---

## 6. Evidence Engine (component 6 of 8)

Dashboard page: `#/stage/evidence`. Output: `output/evidence_engine.db` (tables `relationship_evidence`, `event_evidence`, `event_completions`). Library: `config/evidence_library_v0.yaml`; patient config: `config/evidence_meera_iyer_v1.yaml`. Spec: `task/evidence_engine_spec.md`. The Evidence Engine is deterministic, uses numpy, and uses no model. It tests, with statistics on **her own history**, whether each factor in a rulebook packet shows up in her data, and returns numbers and a label for each. It never explains and never claims a cause. It does not decide beliefs or statuses (that is PI), does not group alerts into cases (that is Findings), does not search for new factors, and does not read PI, the Baseline gists or the free text of the diary (only diary category and time).

### What comes in

- **From the Rulebook Lookup:** the 287 packets: 279 active packets with 1,899 selected factors, and 8 deferred packets with none.
- **From the State Engine:** the hand-off record of each alert (time, measure, direction and so on).
- **From the store:** her whole history of readings and context, read-only.
- **From its own library:** 69 entries, one for each rulebook candidate, checked against the rulebook when loaded.

### From 69 library entries to 63 relationships

| Kind | Count |
|---|---|
| Runnable as a relationship (factor to outcome) | 49 |
| Event-level checks (one-off facts about an alert) | 11 |
| No data definition yet | 7 |
| Rule deferred | 2 |
| **Library entries** | **69** |

The 11 event-level checks are meal composition, dawn effect, sensor artifact, meal skipped or delayed, regimen factors, and the presence checks (other medications x3, hypoglycemic agent, thyroid status x2). The 7 without a definition are cycle phase (x2, no stream), caffeine (no stream), meal digestive, unusual activity the day before, salt in meals (no definition) and overnight glucose (shares the night with the outcome). The 2 deferred belong to the screen-time rule.

All 49 runnable keys are different: the same factor under two rules is a different relationship because its outcome differs. Seven of the 49 are post-meal glucose peaks and are tested separately for breakfast, lunch and dinner: 49 - 7 + (7 x 3) = **63 relationships**.

### Two jobs, two clocks

**1. The daily refresh (relationships).** Every day of the year it re-tests every relationship using only her history up to that day. 63 relationships x 352 days gives **22,148 daily records** (42 on day 1, 56 on day 2, 63 on each of the other 350 days). It runs in about 9 seconds, is deterministic (two runs are identical row for row), and writes records once and never changes them.

**2. Event evidence (one record per alert).** For each of the 287 packets it looks up each listed factor's label for the alert's date, adds the event-level checks and the factor's exposure state at the moment the alert opened, and writes one record: **287 records** covering the 1,899 factors.

### How one relationship is tested

1. **History table.** One row per earlier unit (a day, a meal, an hour or a reading) with the factor's value and the outcome (for example her average glucose between meals that day). The factor must have happened before the unit started; every exposure window is anchored to the outcome date or the unit start, never to the alert's time. A meal enters the history only after its 150-minute window has ended.
2. **Detrend.** The outcome is replaced by its difference from her own recent median (the previous 30 days, of the same meal kind for meals, of the same clock hour for hours). It needs at least 10 earlier values, so the first rows are dropped.
3. **Minimums.** The label is insufficient unless there are **at least 60 usable units AND 60 distinct outcome dates**; for a present/absent factor also at least 15 exposed and 30 unexposed units; and the factor and outcome must vary.
4. **Effect.** For a present/absent factor, the standardized difference between the two groups; for a numeric factor, the Spearman rank correlation. An effect must be at least 0.10 in the expected direction.
5. **Significance.** The factor's series is rotated by a random offset 2,000 times (keeping its day-to-day pattern) and it counts how often chance does as well as the real effect. Benjamini-Hochberg at q = 0.10 is applied across all relationships refreshed that day (the "family").
6. **Placebo.** The test is repeated once with the factor shifted by 30% of the series. If the placebo also passes the suggestive rule, the relationship gets the flag `placebo_fired` and cannot be labelled supported. About 8.6% of placebos fired, which estimates the false-positive rate.
7. **Seeds** are SHA-256 of the key, the date and the method version, so a re-run gives identical results.

| Label | Rule |
|---|---|
| supported | not insufficient; adjusted p at most 0.10; effect at least the floor in the expected direction |
| suggestive | not insufficient; unadjusted p at most 0.10 and effect at least the floor, but the adjusted p is above 0.10 |
| not supported | enough data, but neither holds |
| insufficient | a minimum is not met |

### When it starts: 60 days, not 30

The minimum is **60 usable units and 60 distinct days**. The "30" in the settings is the detrending baseline (the previous 30 days, at least 10 values), which delays the true start slightly. The Baseline and State engines use their own minimums (14 days; 30 readings for reading-level usuals); they do not affect this one.

The data started on 1 Oct 2025, but the first label other than insufficient appeared on **10 December 2025** (9 relationships that day, 19 the next). October and November have no tested relationship at all. 25 relationships left "insufficient" by the end of December, 10 more in January and 6 in February; the last came in April, June and July. **48 of the 63** were tested at some point in the year; **15 never reached the minimums** (mainly the alcohol pairs).

### The numbers

**The 22,148 daily records:**

| Label | Records |
|---|---|
| supported | 5,066 |
| suggestive | 1,122 |
| not supported | 5,396 |
| insufficient | 10,564 |

Supported records by month grow from 0 in October and November to 192 in December and 794 in August. On 17 Sep 2026: 63 relationships, 48 tested, 28 supported, 2 suggestive, 18 not supported, 15 insufficient. A relationship changes its label on average 0.28 times a week.

**The 1,899 factors in the 287 alert records:**

| Label | Factors |
|---|---|
| supported | 405 |
| suggestive | 91 |
| not supported | 356 |
| insufficient | 882 |
| not applicable (presence checks) | 160 |
| not yet available | 5 |

The 882 insufficient factors: not enough history 445, group too small 276, no definition 137, no ordered exposure 12, no meal kind 12. Another 373 candidates were skipped upstream by the packets (section 5) and never reach the Evidence Engine.

### The event-level checks and exposure states

- **Percentile versus history** (meal composition, meal skipped or delayed): how unusual this meal's response is against her earlier meals of the same kind. Supported if it is at or beyond the 90th percentile and at least 30 earlier meals exist.
- **Shape check** (sensor artifact): whether a glucose low looks like an artifact (isolated, steep drop, rebounds). It needs the reading after the alert, so the record is written "not yet available" and completed an hour later. 5 alerts needed completion, all glucose-below: 3 supported (consistent with an artifact) and 2 not supported (the rebound was 1.6 and 2 mg/dL over the placeholder tolerance).
- **Pattern repeat** (dawn effect, regimen factors): descriptive frequencies over earlier days.
- **Presence check:** a fact from the config (for example the thyroid flag).
- **Exposure state** of each factor at the moment the alert opened: `exposed`, `not_exposed`, `not_yet_available` (the record exists but has not arrived yet, for example a daily total that comes at the end of the day) or `no_data`.
- **Overlap:** among supported or suggestive factors, each pair that is entangled (one nearly always present when the other is) is flagged, so the text cannot treat them as separate.

### What the "63 relationships" list is, and how to read a bar

- **The list is fixed; the results are hers.** The 63 are the candidate pairs the library knows how to test (the same list would be used for any patient). They are not relationships discovered in her. What the dashboard shows for each one is how it performed against her own history over the year.
- **A bar is the share of the year's days that got each label,** always in the order green (supported), amber (suggestive), blue (not supported), grey (insufficient). It is **not a timeline**, so the grey always sits at the end. The chip beside it is the label on the last day (17 Sep 2026).
- **How to read the shapes:**

| Shape | Meaning |
|---|---|
| all green | supported on almost every day: the link showed up in her history and kept showing up |
| mostly green with a grey end | supported on most days; the grey is the days with too little history to test (mainly the first two months, since a relationship needs 60 days). The typical shape |
| a mix of green, amber and blue | shows up on some days and not on others: not steady, so read it as weak |
| mostly blue | tested on enough days and the link did not show up in her data |
| all grey | never testable in the year (too few days with the factor present, or not enough data) |

- On 17 Sep 2026: 28 supported, 2 suggestive, 18 not supported and 15 insufficient. 48 of the 63 were tested at some point.
- A label changes on average 0.28 times a week, so the mix of colours in a bar also shows how steady the relationship was.

### What the Evidence Engine does and does not do

- **It tests; it does not interpret or rank.** It answers one narrow question per relationship: does this pattern show up in her data more than chance would give? It labels each of the 63 independently. It does not say why, does not compare relationships to say which is stronger, and does not decide which is prominent over time. That comes from PI, which tracks how consistently a relationship was supported across weeks.
- **It reports what was true at the moment of each alert.** For every factor on an alert it records whether the factor was present, absent, not yet available or has no data when the alert opened. A relationship can be supported in general and still not be present for a particular alert.
- **It runs event-level checks on the alert itself:** how unusual this meal's glucose response is against her earlier meals of the same kind, whether a glucose low looks like a sensor artifact, the dawn pattern, per-medicine miss rates, and presence facts such as the thyroid flag.
- **It attaches flags that limit what the text may say later:** a placebo that fires blocks the label "supported"; a same-day pair is marked `same_day_unverified` because the order inside a day cannot be confirmed; two factors that nearly always occur together are flagged as entangled so they cannot be presented as independent. The Findings Engine has to respect these.
- **It never looks ahead.** Every test uses only data that existed on the day, and each record is checked for having arrived by the alert's time (that is what "not yet available" is for).
- **Its daily labels feed PI,** which turns them into weekly labels and long-term notes.

### Things to remember

- A label says how well a link shows up in her history. It is not a cause, and it is the label for one moment, not a belief (that is PI).
- Same-day relationships are marked `same_day_unverified` (22 pairs), because the order of factor and outcome inside a day cannot be confirmed.
- A relationship with no ordered exposure (no mood block can end before a breakfast) is intentionally insufficient.
- The 5 glucose lows that were not yet available are the only records that get a completion, and the original record is never changed.

### What goes to the next component

The 287 alert evidence records (and the daily relationship labels by date) go to the Findings Engine, matched by the evidence id `ev_<hand-off id>`. PI later reads the daily labels by date to build its weekly labels.

---

## 7. Findings Engine (component 7 of 8)

Dashboard pages: `#/stage/findings`, `#/cases`, `#/case/<id>`. Final output: `output/findings_loop_polish.db` (tables `cases`, `findings`, `finding_text`, `finding_llm`, `case_handoffs`, `unattached_handoffs`, `meta`). Code: `src/v0_code/findings_engine/` and the loop driver `src/v0_code/loop_engine/`. Method `fe-v0`, text prompt `p-v5`, checks `ck-v7`. The structured layer is deterministic code; the text is the only place a model is used, and it is checked.

In one line: it groups alerts into cases, decides by code which factors may be mentioned and how strongly, and only then has a model word it.

### What comes in

- **The counted alerts:** 279 hand-offs. Eight more hand-offs belong to the deferred screen-time rule; they never make a version (4 are recorded inside a case that already existed but do not count, 4 sit outside any case).
- **The Evidence records** for each alert, and the packets.
- **Context, always as of that moment:** diary entries (category, time and text), the Baseline gists (yesterday's day window, the week and the latest month) and PI's earlier notes.

### Alert, case and version

- **An alert** is one fact about one moment: a measure stayed off her usual and was handed on. Once written it is fixed.
- **A case** groups alerts that arrive close together: an alert joins the open case if it comes within 6 hours of the case's last alert, up to 36 hours in all.
- **A version** is the written account of a whole case at one point in time. Each new alert in a case creates a new version that includes everything known so far (version 3 knows alerts 1, 2 and 3). An earlier version is never changed.
- **Alert and version are not the same thing,** but they are tied: an alert is the cause of a version and a version is the cumulative picture after that alert. The March 16 case has 11 alerts and 10 versions, because one of its alerts (screen time, a deferred rule) is recorded in the case but made no version.

### The numbers

| | Number |
|---|---|
| Alerts from the State Engine | 287 |
| less deferred screen-time alerts (4 recorded in a case, 4 outside any case) | - 8 |
| **Counted alerts, each making one version** | **279** |
| plus completions (a second event for five of those same alerts) | + 5 |
| **Versions** | **284** |
| **Cases** | **116** |

Reading 287 - 284 = 3 as "3 alerts missing" is wrong; the real gap is the 8 deferred alerts, and the 5 completions are added on top of the 279.

**The 5 completions.** They are not new alerts. They belong to five glucose-below alerts (adverse lows, for example the 65.0 mg/dL reading on 8 Nov 2025 at 11:00). Their evidence includes a sensor-artifact check, which needs the reading after the alert, so at the moment the alert opens the evidence says "not yet available". About an hour later the next reading is known and the check is completed. That second event is recorded as one more version of the same case. These five alerts therefore account for 10 of the 284 versions.

**Alerts per case:** 58 cases have 1 alert, 21 have 2, 13 have 3, 11 have 4, 2 have 5, 4 have 6, 4 have 8, and one each has 9, 10 and 11. **Versions per case:** 54 have 1, 24 have 2, 14 have 3, 11 have 4, 2 have 5, 4 have 6, 4 have 8, and one each has 9, 10 and 11.

### The structured layer, decided by code

- **Factors.** Each version lists the factors from the evidence records of all the alerts in the case so far, merged by relationship. The 284 versions carry **3,126** factor entries in total.
- **Wording class.** A fixed rule turns each factor's Evidence label and exposure into one of 11 classes that cap what the text may say:

| Class | Entries | What the text may say |
|---|---|---|
| not mentioned | 1,605 | nothing (not usable) |
| not known yet | 560 | that it is not known yet |
| present, little history | 403 | it was present, with a note that there is not enough history |
| present, no link | 320 | it was present |
| stated as a pattern | 105 | "has tended to move together with" the outcome |
| same-day pattern | 76 | as above, and the text must say same day |
| unusual event | 42 | how unusual this event was |
| may be linked | 8 | only "may be linked to" |
| possible artifact | 3 | may be a sensor artifact |
| contrary note | 2 | on days with this, the outcome tended to be lower |
| may be linked, same day | 2 | may be linked, and say same day |

- **Mode.** A version is `relationship` only when an exposed relationship factor has a pattern or "may be linked" class; otherwise it is `descriptive`. By version: 165 descriptive and 119 relationship. By each case's last version: **67 descriptive and 49 relationship**. All 27 cases before 10 December are descriptive; the first relationship version is on 15 Dec 2025.
- **History note.** 204 versions have enough history; 80 say "not enough history yet", all from before December.
- **Groups.** 44 co-exposed groups are marked (two factors that were both present), so the text can say so.
- **Measures per version:** 180 mention one measure, 77 two, 16 three and 11 four.
- **What is not yet known:** 260 versions carry a list of items that are not known yet at that moment (for example the day's mood record or sleep).
- **A PI status never changes the class, the mode or the group.** PI's notes only add "this has come up before" wording.

### The context recorded with each version (references only)

- diary entries: 170 versions;
- Baseline windows (yesterday's day, the week, the latest month): 273 versions;
- PI memories read as of that moment: all 284 (a strict "before this version" read).

Only a little of this reaches the model: yesterday's day-window headline if that day was notable (and none in a sensor-artifact version), at most one sentence may cite it, and never beside a claim about a relationship.

### The text

1. Every version first gets a **code line** built straight from the structured layer (stored with the finding).
2. The model then words it from a **numberless view** (no digits, only what may be mentioned, with the wording class as the limit). The answer is checked by code: direction and claim strength, causal words, digits and copied diary text, internal words, structure, repeated phrases, clinical terms that are not in the view. One retry with the failures appended, then the code line is used.
3. **Final texts of the 284 versions:** 132 kept from an earlier prompt (the view did not change and the text still passes today's checks), 143 model-written, **9 code-line fallbacks (3.2%)**. Sentences per version: 3 have none, 35 have 1, 61 have 2, 92 have 3, 50 have 4 and the rest up to 11.
4. In the last polish run 151 texts were rewritten. 43 failed their first attempt: repeated phrase 12, claim strength 8, causal wording 7, copied diary or internal words 6, digits 4, structure 4, clinical terms 2. Token use in the stored call log: about 483,000 in and 485,000 out.
5. **Known limit:** 13 versions repeat the headline as a sentence or write a sentence twice.

### What goes to PI

Every version goes into PI's open week (matched by `finding_id`), with the code line first and the final text swapped in at the week barrier. PI then reads the findings by week to build its weekly labels and long-term notes, and later versions read PI's notes back as of their time.

---

## 8. PI: the findings memory (component 8 of 8)

Dashboard pages: `#/stage/pi` and `#/pi`. Final output: `output/pi_loop_polish.db` (tables `pi_mid_entries`, `pi_mid_memories`, `pi_long_memories`, `pi_weekly_runs`, `pi_text`, `pi_llm`, `pi_entry_keys`, `pi_meta`). Code: `src/v0_code/pi_engine/`; config `config/pi_meera_iyer_v1.yaml`; spec `task/pi_spec.md`. PI is deterministic code. Its only model use is one optional "situations" sentence per note. In V0 it **creates, updates and retrieves** memories and nothing else. It writes only its own database; the Findings and Evidence databases are read-only.

### What comes in

- **Every Findings version**, put into PI's open week as it is written, first with its code line and then with the final text swapped in at the week barrier: **284 entries** over the **35 weeks** that had any.
- **The Evidence Engine's daily labels**, read by date, to judge each relationship each week.

### Three things that are easy to mix up

| Thing | What it is | How many |
|---|---|---|
| Weekly job | A process, not a memory. Once a week (Monday to Sunday, closing at 23:59:59 Sunday) PI runs and does the updating, and writes a run record | 51 (2025-W40 to 2026-W38) |
| Mid-term memory | A weekly memory: the collection of that week's entries (the latest version of each case). Open while the week runs and sealed by the job | 51 weeks, stored 102 times (once open, once sealed) |
| Long-term memory (note) | One per relationship, kept across weeks, with a status that changes | 29 notes, 174 versions |

The flow is: Findings versions go into the week's mid-term memory; at the end of the week the weekly job seals it, looks at each relationship's daily labels for that week, and updates the long-term notes (creating one, changing a status or rewriting a text).

### Which relationships get a note

A note exists only for a relationship the Findings Engine used in a case. So **29 of the 63 tested relationships** have one. 29 is not "the 29 strongest": a strongly supported relationship whose factor never appeared near an alert has no note (two supported relationships, for example, have none).

### The weekly label and the lifecycle

Every week each relationship gets a **weekly label** from that week's daily Evidence labels. A week is `supported` or `not_supported` only if at least **5 of its 7 days** agree (scaled for a partial week, with at least 4 days). The status then follows fixed rules (placeholders from the spec, never tuned to produce statuses):

| From | To | When |
|---|---|---|
| (created) | candidate | the relationship first appears in a finding |
| candidate | supported | weekly label `supported` for 2 consecutive weeks |
| supported | weakened | `not_supported` for 2 consecutive weeks |
| weakened | supported | `supported` for 2 consecutive weeks |
| weakened | retracted | `not_supported` for 6 further weeks, or the `contrary` flag on at least 5 days a week for 4 consecutive weeks |
| retracted | candidate | `supported` for 2 consecutive weeks |

A count of consecutive weeks is the length of the current run of equal decisive labels; a decisive label of the other kind resets it. A relationship whose placebo fired on more than half the days cannot be promoted. **Back-fill:** when a note is created, PI replays the earlier weekly labels from the first week the relationship was tested, so one that has been supported for weeks starts as supported and is not shown as new. 15 of the 29 were created already `supported`.

### The numbers

| | Number |
|---|---|
| Weekly jobs | 51 |
| Entries (Findings versions) | 284, in 35 weeks |
| Mid-term memories | 51 (102 stored rows, open and sealed) |
| Long-term notes | 29 |
| Long-term note versions | 174 |
| Transitions | 26 candidate to supported, 1 supported to weakened, 1 weakened to retracted |
| Final status | 25 supported, 3 candidate, 1 retracted, 0 weakened |

### What a version is

A memory version is one saved snapshot of a long-term note at a moment when something about it changed. A new version is written when the note is **created** or when any of these changes: its status, its counters (days it appeared, weeks seen, first and last seen), the flags seen on it, the findings that feed it, or its text. A week in which none of these changed writes nothing, even though the job ran. Old versions are never edited.

So the 29 notes were created 29 times and changed 145 more times: 29 + 145 = **174 versions** (about 6 each on average, not 29 x 51 = about 1,500). The spread is uneven:

| Versions of a note | Notes |
|---|---|
| 20, 18, 17, 14 | one each (the busiest relationships) |
| 9 | 1 |
| 8 | 3 |
| 7 | 4 |
| 6 | 1 |
| 5 | 2 |
| 4 | 3 |
| 2 | 5 |
| 1 | 6 |

20 + 18 + 17 + 14 + 9 + 24 + 28 + 6 + 10 + 12 + 10 + 6 = 174. A note with many versions kept coming up in cases; a note with one version was created once and never changed (for example "missed doses on the same day or the day before → higher blood pressure readings", created on 17 Sep 2026). The version count shows how often a note changed, not how strong the relationship is. The note "short sleep the night before → higher heart rate over the day" has 20 versions: version 1 on 21 Dec 2025 (supported, 2 days of evidence) and version 20 on 17 Sep 2026 (38 days).

### What a note says

Two parts:
- **The association sentence** is built by code from a template per status ("has repeatedly moved together with … in her history", "may be linked to … This is an early observation"). The model never writes or edits it.
- **An optional situations line:** one sentence of at most 25 words, written by the model only from the mid-term entries' sentences that cite diary items only ("In the cases noted, the situations included a festival, a work deadline…"). Of the 174 versions: **126** got a line, **39** had no diary-only sentence so no call was made, **7** kept the previous line, **1** was dropped after failing its checks, and **1** retracted note uses the code text only (133 versions carry a situations line in all). The line is regenerated every 4 weeks.

### The "Cases PI received each week" chart on the dashboard

Each bar is one Monday-to-Sunday week: the number of cases in that week's mid-term memory (the latest version of each case). Amber bars are weeks in which a note changed status. The total across all weeks is **119**, not 116, because 3 cases ran across a week boundary and appear in two weeks. The busy weeks are in November, mid-March and September; May to August is almost empty; the amber bars cluster from December to March, when most notes were created and promoted. The chart does not show versions or alerts, and a tall bar means more cases, not stronger evidence.

### What reads PI

The Findings Engine reads PI's notes as of that moment (a strict "before this version" read), to add "this has come up before" wording (`seen_before`: this week, or in the last 28 days). It can cite a note's earlier conclusion. A PI status **never changes** a wording class, a mode or a group.

### Things to remember

- **"Supported" is persistence, not confirmation.** Notes exist only for relationships that findings used, and the Evidence labels already persist for months, so a status reports how steady the Evidence label was. It is not independent proof of a link, and the text stays weak ("has repeatedly moved together with").
- **One note was retracted:** steps in the previous hour → heart rate in that hour, weakened in 2026-W22 and retracted in W28, because the Evidence ordering rule excludes same-hour steps. A same-hour variant is parked.
- No note has the `contrary` flag.
- The version count and the chart are about how much PI wrote and received, not about how important a relationship is.

---

# How the numbers flowed, end to end

77,797 readings were checked and 44,469 got a status (section 1). 14,697 of the high or low glucose readings were linked to what was nearby, giving 138,118 pairings, and the store held 182,587 rows plus 45,952 context events (section 2). The Baseline Engine turned the status rows and context events into 710 windows (352 days, 346 weeks, 12 months), 590 with a model-written gist (section 3). The State Engine watched 10 measures at 33,792 ticks and opened 565 deviation items, 287 of them adverse and handed on as alerts (section 4). The Rulebook turned each alert into a packet, 287 packets with 1,899 selected factors (section 5). The Evidence Engine tested 63 relationships every day, 22,148 records, and wrote 287 alert evidence records (section 6). The Findings Engine grouped the 279 counted alerts into 116 cases with 284 versions, each with a structured layer and a checked text (section 7). PI put those into 51 weekly memories and kept 29 long-term notes with 174 versions, 25 supported at the end (section 8).







