# 2. Short-Range Event Linker and Personal Data Store

Audience: engineers working on the UMC upstream pipeline.
Scope: graph nodes `short_range_linker` and `personal_data_store`, the SQLite layer in `data/store.py`, and the `context_events` ingest that fills the store's second table.
Spec: not in `task/`. Components 3 and 4 were specified in conversation, so the decisions below come from `CLAUDE.md` and the code. Source of the numbers: `understand/how_the_numbers_flow.md` §2, the pipeline's own outputs.

Both components are **deterministic**: no ML/LLM, no scoring, no ranking. The linker never makes a causal claim. A pairing only says "this happened nearby". The store only writes rows in and reads rows out.

---

## 1. What they do

| | Question it answers | Output |
|---|---|---|
| **Short-Range Event Linker** | "For this high or low glucose reading, what else was recorded close to it in time?" | `output/short_range_pairings.csv`, one row per match |
| **Personal Data Store** | "Where does everything that survived component 1 and 2 live, so later components can look it up?" | `output/personal_data_store.db`, table `raw_events` |

The store also has a second table, `context_events`, for streams that are never given a status. It is filled by the Baseline Engine node (§5.3), not by the `personal_data_store` node.

---

## 2. Position in the graph

```
… threshold_evaluator ──► short_range_linker ──► personal_data_store ──► baseline_engine ──► END
       (44,469 status rows)     (138,118 pairings)      (raw_events: 182,587 rows)
```

Defined in `src/v0_code/graph/builder.py`.

### Code layout

| File | Role |
|---|---|
| `logic/linker.py` | Pure matching logic, `find_pairings(...)`. No LangGraph imports |
| `nodes/short_range_linker.py` | Node 4: picks the glucose readings, builds the heart-rate index, calls `find_pairings`, writes the CSV |
| `data/store.py` | `PersonalDataStore`: schema and insert/select methods (also holds the later Baseline tables) |
| `nodes/personal_data_store.py` | Node 5: converts state into rows and writes `raw_events` |
| `data/context_ingest.py` | `build_context_rows`: reshapes already-parsed streams into `context_events` rows |
| `data/loaders.py` | Raw loaders for the linker's context data: `load_meals`, `load_adherence_by_date`, `load_context_events_by_date`, `load_sleep_by_date`, `load_mood_by_date_block`, `load_diary_by_date` |
| `graph/state.py` | `Pairing` record and the linker/store fields on `UMCState` |

The loaders for linker context keep fields that `Reading` does not have (food description, medication name, mood label), so they are separate from `load_readings`. `load_inputs` puts them into state once per run.

---

## 3. Short-Range Event Linker

### 3.1 Which readings are linked

`nodes/short_range_linker.py` keeps threshold rows where:

```
biomarker == "cgm_glucose_reading"  AND  status in {"high", "low"}
```

Borderline glucose and the separate `fasting_glucose` lab rows are **excluded on purpose** (instruction in conversation). On the real data:

| CGM glucose status (from component 1) | Readings | Linked |
|---|---|---|
| borderline high | 18,120 | no |
| high | 14,692 | yes |
| normal | 759 | no |
| low | 5 | yes |
| **Linked** | **14,697** | |

Scope is glucose only. No other biomarker produces pairings.

### 3.2 The `Pairing` record

```
glucose_event_id, glucose_timestamp, glucose_value, glucose_status,   # which reading
candidate_type, candidate_id, candidate_timestamp, lag_minutes,       # what was nearby and how far
candidate_summary                                                    # a templated one-liner
```

`lag_minutes = glucose time − candidate time`, in minutes rounded to 1 decimal. It is positive when the candidate came **before** the glucose reading. It is `null` when the candidate has no timestamp (medication, mood, diary).

### 3.3 Matching rules, per candidate type

For each qualifying reading, `find_pairings` checks eight candidate types. The time windows are fixed constants in `logic/linker.py`.

| Type | Rule | Rows per reading | Window / key |
|---|---|---|---|
| **meal** | a meal with `window_start <= meal_time <= glucose_time` | 0, 1 or several | `MEAL_WINDOW_MIN = 150` min before |
| **medication** | every medication logged for that **calendar date**; `candidate_timestamp` and `lag_minutes` are always null | one per medicine (3 for her) | same date, no time filter |
| **activity** | the hourly step bucket(s) starting within 90 min before, with `steps > 0` | 0, 1 or 2 | `ACTIVITY_WINDOW_MIN = 90`; only the current and previous hour bucket can qualify |
| **heart_rate** | **one summary** over `continuous_heart_rate` readings within ±120 min: average, min, max, n | 0 or 1 | `HEART_RATE_WINDOW_MIN = 120`, found by `bisect` on a sorted timestamp array |
| **sleep** | the sleep row of that date (the source already aligns a night to its wake date) | 0 or 1 | same date |
| **context_event** | every context-log event on that date | 0, 1 or several | same date |
| **diary** | that date's diary entry (summary is its title, else its first line) | 0 or 1 | same date |
| **mood** | the mood record for the reading's time block | 0 or 1 | same date + block |

**Mood time block** (`_mood_block`): hour 5–11 → `morning`, 12–19 → `afternoon`, otherwise (20–04) → `evening`. This mirrors the diary's own 3-block scheme (the diary's "afternoon/evening" and "night" are merged into "evening" to match the 3 labels of the mood file). It is not a thirds-of-the-day split. The docstring in `_mood_block` says "morning 5-12 …"; the code (5–11 / 12–19) is what runs.

Why heart rate is one summary row and not one row per sample: the stream has a 15-minute cadence, so a ±2 h window holds about 17 samples of the same signal. One row per sample would be redundant oversampling. The `candidate_timestamp` is the sample nearest to the glucose reading (so its lag can be negative, when the nearest sample is after the reading). The `candidate_id` is `hr_window_<glucose_event_id>`.

Why medication has no time: the adherence file has no timestamp, and time was explicitly excluded from this check. `MEDICATION_WINDOW_MIN = 240` exists in the module but is **not applied**.

### 3.4 Example `candidate_summary` strings (templated)

```
meal         breakfast: dosa, chutney, coffee
medication   metformin taken
activity     107 steps that hour
heart_rate   avg 84.3 bpm (72-101, n=17)
sleep        6.5h (poor)
context_event  <category>: <description> — <note>
diary        <title, or first line>
mood         <label> (<category>)
```

### 3.5 Node behaviour (`nodes/short_range_linker.py`)

1. Filters the qualifying glucose readings (§3.1).
2. Builds the heart-rate index once: all `continuous_heart_rate` readings from `state.passed_readings` (**including active-period ones**, since the linker is not limited to resting readings), sorted, as parallel `hr_times` (epoch seconds) and `hr_values` lists.
3. Calls `find_pairings` for each reading and concatenates the results.
4. Writes `output/short_range_pairings.csv` (columns as in §3.2). Row order is processing order.
5. Writes to state: `pairings`, `linker_output`, `linker_counts` (per candidate type), `qualifying_glucose_events`, `glucose_events_with_pairings`.

`glucose_events_with_pairings` is counted over the distinct `(glucose_event_id, glucose_timestamp)` pairs, **not** over `glucose_event_id`, because ids repeat across months (§7.1).

### 3.6 What is fixed and what is dynamic

**Fixed:** which eight kinds are checked, and the window sizes. The same reading with the same surroundings always gets the same pairings. The linker does **not** choose kinds by glucose value (130 and 250 are checked the same way), does not rank pairings, and does not say which one mattered. Deciding what deserves attention is the job of later components (Rulebook Lookup picks candidate factors per alert; the Evidence Engine tests them on her own history).

**Dynamic:** whether a row is written depends on what exists near the reading.

| Behaviour | Types | Rows per reading |
|---|---|---|
| Exactly one, on this data | heart rate, mood, sleep, diary | 1 each (14,697 each) |
| Exactly three | medication (three medicines logged every day) | 3 (44,091 in all) |
| Zero, one or several | meal, activity, context event | one per match |

### 3.7 Pairing counts on the real data

| Type | Rows | How the number arises |
|---|---|---|
| medication | 44,091 | 14,697 × 3 |
| activity | 20,978 | one per matching hour bucket |
| diary | 14,697 | one per reading |
| heart rate | 14,697 | one per reading |
| mood | 14,697 | one per reading |
| sleep | 14,697 | one per reading |
| meal | 8,370 | one per matching meal (most readings have no meal in the previous 150 min) |
| context event | 5,891 | one per same-day event |
| **Total** | **138,118** | about 9.4 pairings per glucose reading |

---

## 4. Personal Data Store

A pure write-in/read-out SQLite layer. It does no computation and no filtering beyond plain `WHERE` clauses. File: `output/personal_data_store.db`.

### 4.1 What the `personal_data_store` node writes

Node 5 converts state into rows and inserts them into one table, `raw_events`:

| `source_type` | Rows | Origin |
|---|---|---|
| `reading` | 44,469 | every Threshold Evaluator row, **every** status including `normal` |
| `pairing` | 138,118 | every linker pairing |
| **Total** | **182,587** | 44,469 + 138,118 |

Rejected readings (component 1) and untouched source files never reach `raw_events`.

### 4.2 `raw_events` schema

```
id              INTEGER PRIMARY KEY AUTOINCREMENT     surrogate key
event_id        TEXT        reading id, or the GLUCOSE reading's id for a pairing
timestamp       TEXT        reading timestamp (for a pairing: the glucose reading's)
biomarker       TEXT        for a pairing: always cgm_glucose_reading
value           REAL        for a pairing: the glucose value
status          TEXT        for a pairing: the glucose status
source_type     TEXT        'reading' | 'pairing'
paired_to       TEXT        pairing only: candidate_id
candidate_type  TEXT        pairing only: meal, medication, sleep, ...
lag_minutes     REAL        pairing only
```

Indexes: `(biomarker, timestamp)` and `(source_type, event_id, timestamp)`.

A pairing row is **self-contained**: it carries the glucose reading's timestamp, value and status, so you can tell which reading it is about without a join.

**Deviation from the original spec.** The spec's literal schema was `event_id TEXT PRIMARY KEY`. That cannot work: `event_id` repeats across the year, and one glucose reading has several pairings that share the same `event_id`. The fix (confirmed in conversation) is the surrogate `id` plus `event_id` as an ordinary column.

### 4.3 API (`PersonalDataStore`)

| Method | Purpose |
|---|---|
| `insert_readings(rows)` / `insert_reading(...)` | Reading rows `(event_id, timestamp, biomarker, value, status)` |
| `insert_pairings(rows)` / `insert_pairing(...)` | Pairing rows `(glucose_event_id, timestamp, biomarker, value, status, paired_to, candidate_type, lag_minutes)` |
| `get_events(biomarker, start_date, end_date)` | Reading rows for one biomarker; `end_date` covers the whole day (`+ "T23:59:59"`) |
| `get_pairings(glucose_event_id, timestamp)` | All pairings of one reading. Takes **both** keys: `event_id` alone is ambiguous |
| `insert_context_events` / `get_context_events(stream, start_date, end_date)` | The `context_events` table (§5) |

The class also exposes methods for the Baseline Engine tables (`numeric_summary`, `memory_records`). They are outside this component.

### 4.4 `reset` semantics (do not change casually)

`PersonalDataStore(path, reset=True)` is passed **only** by the pipeline node. It drops `raw_events`, `numeric_summary`, `context_events` and `memory_records`, then recreates all tables, which rebuilds everything fresh each run, like the CSVs. A plain `PersonalDataStore(path)` (the default `reset=False`) opens the existing store and never touches it. This exists because the first version dropped the table in `__init__` and wiped the database the first time it was opened just to read it. Do not reintroduce an unconditional drop in `__init__`.

Operational consequence: `uv run v0-code` refuses to run if `output/personal_data_store.db` already exists unless you pass `--rebuild`. A rebuild drops `memory_records`, which holds the 472 v1 model-written entries, so back those up and restore them by `window_id` afterwards.

---

## 5. `context_events`: the store's second table

### 5.1 What goes in

Streams that were recorded but are **never given a status**: they do not pass through the Threshold Evaluator. They are written verbatim, with no computation, so that the linker's neighbours and later components have a durable, queryable table.

Schema: `id, stream, timestamp, date, value_text, value_num, category, meta_json`, with an index on `(stream, date)`.

45,952 rows in all:

| Stream | Rows | Notes |
|---|---|---|
| `continuous_heart_rate` | 33,792 | every plausibility-passed 15-min reading, including active-period ones that never got a status |
| `step_count_hourly` | 8,160 | ingest-only (below), 340 days |
| `medication_adherence` | 1,056 | 3 medicines × 352 days; `value_text` taken/missed, `value_num` 1.0/0.0 |
| `mood_state` | 1,056 | 3 time blocks × 352 days |
| `meal_events` | 1,055 | `meta_json` holds the meal id |
| `location` | 352 | daily |
| `sleep_quality` | 352 | |
| `diary_context` | 129 | the context log |
| **Total** | **45,952** | |

### 5.2 Ingest-only streams

`config/ingest_streams.yaml` lets a stream be written to `context_events` by config (`kind`, `source.biomarker`, required `used_by`). Currently one: `step_count_hourly`, `used_by: [rulebook]`. Rows are appended after every other context row, so no existing id moves. These streams are not in the Baseline registry, the Baseline v2 config or the State Engine config, so those engines never aggregate or flag them.

### 5.3 Who writes it

`build_context_rows(state, ingest_streams)` in `data/context_ingest.py` reshapes data **already parsed** by `load_inputs` (no second CSV read). It is called from `nodes/baseline_engine.py`, which is why the store's second table is written by the Baseline node and not by the `personal_data_store` node.

---

## 6. Data flow summary

```
threshold_results (44,469) ──────────────────────────────────────────────┐
   │ keep cgm_glucose_reading with status high/low                       │
   ▼  (14,697 readings)                                                  │
short_range_linker  ◄── meals, adherence, steps_by_hour, HR index,       │
   │                    sleep, context events, diary, mood               │
   ▼                                                                     ▼
short_range_pairings.csv (138,118)  ──────────►  personal_data_store ─► raw_events (182,587)
                                                                          │
baseline_engine node: build_context_rows ─────────────────────────────► context_events (45,952)
```

The store (`raw_events` and `context_events`) is what the Baseline Engine reads to build its day, week and month windows. The pairings are kept for later lookup; the Baseline Engine does not use them. The hourly steps sit in `context_events` only so that Rulebook Lookup can resolve heart-rate "activity" candidates by the hour.

---

## 7. Gotchas and decisions to check before changing anything

1. **Ids repeat across the year.** `event_id` is not unique in the source files, and candidate ids (`adherence_id`, sleep `event_id`, and so on) are not unique either. Always key a pairing by `(glucose_event_id, glucose_timestamp)`. Never by `glucose_event_id` alone (the node already counts this way). 14,697 distinct readings produce the 138,118 pairings.
2. **A pairing is not a cause.** Wording, tests and downstream code must not read it as one.
3. **One row per match, except heart rate.** Meal, activity, context event and medication produce one row per item. Heart rate is a summary. Do not "fix" either for consistency without checking the counts above (the Baseline and later layers depend on them).
4. **Activity buckets are hourly and can include later minutes.** A reading at 08:15 can pair with the 08:00 bucket, which covers steps recorded after 08:15. `lag_minutes` for activity is measured to the **bucket start**, not to the steps themselves. Treat it as "an active hour near the reading", not as a precise sequence.
5. **Medication is date-level only.** Every medication logged that day pairs with every qualifying glucose reading of that day, with null time and lag. It carries no ordering information. A "missed" medicine pairs the same way as a "taken" one (the summary says which).
6. **Heart-rate lag can be negative** (nearest sample after the reading), while meal lag is always 0–150.
7. **Context sets differ in granularity:** meal by minutes, activity by hour bucket, heart rate by ±2 h, everything else by calendar date or time block.
8. **Do not wipe the store by opening it.** Only the pipeline node passes `reset=True` (§4.4).
9. **Glucose `status` here is the diagnostic one** (fasting limits 70 / 99 / 125, from component 1), so "high" means above 125 or at the 126 cut-point. It differs by design from the CGM management targets used by the Baseline Engine (70–180, 54 / 250).
10. **Output order** of the pairing CSV is processing order of the glucose readings (loader order), not time order.

## 8. Running and inspecting

```bash
uv run v0-code            # whole graph; writes the CSVs and output/personal_data_store.db
```

Quick checks (read-only):

```bash
# pairings by type
cut -d, -f5 output/short_range_pairings.csv | sort | uniq -c

# raw_events by source type and context_events by stream
sqlite3 -readonly output/personal_data_store.db \
  "select source_type, count(*) from raw_events group by 1;"
sqlite3 -readonly output/personal_data_store.db \
  "select stream, count(*) from context_events group by 1 order by 2 desc;"

# all pairings for one specific glucose reading (both keys!)
sqlite3 -readonly output/personal_data_store.db \
  "select candidate_type, paired_to, lag_minutes from raw_events
   where source_type='pairing' and event_id='<id>' and timestamp='<timestamp>';"
```

The doctor dashboard shows this component on `#/stage/linker`.
