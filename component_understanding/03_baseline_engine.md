# 3. Baseline Engine (cross-domain memory)

You can read this file without opening any code. Part A explains the idea in plain words with examples. Part B is the technical detail for engineers. Every number comes from the pipeline's own outputs (`output/personal_data_store.db`, table `memory_v2`) unless it says otherwise.

---

# Part A. The idea in plain words

## A1. The problem it solves

By the time data reaches this component, we have 44,469 readings that each carry a label (normal, high, low and so on) and 45,952 "context" records (heart rate, steps, meals, medicines, mood). That is a lot of rows and no story.

A doctor, or a later component, needs to answer questions like:

- "Was last Tuesday a normal day for her, or a strange one?"
- "Is this week better or worse than the week before?"
- "What is *normal for her*?" (A resting heart rate of 80 may be fine for one person and a warning for someone whose usual is 60.)

The Baseline Engine turns the raw rows into **one short summary per period** (a day, a week, a 30-day checkpoint), each compared with **her own past**, not with a textbook.

Think of it as a **diary clerk with a calculator**. Every night the clerk:
1. Tidies the day's numbers and throws out obviously broken ones.
2. Works out the day's totals (average glucose, steps, sleep...).
3. Looks back at her earlier days to know what "usual" looks like for her.
4. Writes down what is different from usual, and whether the difference is big enough to matter.
5. Asks a writer to put it into one plain sentence (the "gist"), using only the facts the clerk already settled.

The clerk never guesses causes. It says *what happened* and *what changed*, not *why*.

## A2. A worked example: one day, 9 December 2025

**What came in:** about 95 glucose readings, a 96-reading heart-rate stream, 1 sleep record, 3 medicine records, 3 mood records, 3 meals and so on.

**Step 1: clean the glucose first.** One reading that day says **599 mg/dL** at 10:00. It is under the plausibility filter's ceiling (600), so it got through component 1. But glucose can't jump from about 120 to 599 in 15 minutes. The Baseline Engine removes it before computing anything and notes: *"Reading removed: 599 mg/dL at 10:00, because it looks like a sensor error."* It keeps the raw value on record, so nothing is hidden.

**Step 2: boil the day down.**

| Measure | That day |
|---|---|
| Average glucose | 125 mg/dL |
| Time in range (70 to 180) | 100% |
| Sleep | 7 hours |
| Steps | 1,950 |
| Medicines | metformin missed, amlodipine missed, levothyroxine taken (33.3% taken) |
| Strained periods of the day (mood) | 0 |

**Step 3: compare with the day before.** Average glucose down 11.6 mg/dL, medication adherence down 33.4 points, screen time up 1.4 hours.

**Step 4: ask "is that big, for her?"** "Big" means relative to her own usual wobble. If her average glucose normally swings by about ±5 from day to day, a drop of 11.6 counts as *moderate*. If it normally swings by ±20, the same drop would count as *flat* (nothing to see). This is what the "flat band" is (see A4).

**Step 5: list what mattered.** Two missed doses, one removed reading. The engine does *not* mark this day "notable". "Notable" is reserved for when a configured threshold is crossed (A5).

**Step 6: the gist.** A language model is handed only the facts and asked for one headline and a few sentences. For this day it wrote:

> **She missed metformin and amlodipine.**
> Average glucose fell noticeably. Medication adherence fell noticeably alongside the lower average glucose. One questionable glucose reading was removed from the data.

The model decided none of this. The code had already decided *which* facts, *which* direction and *which* size. The model only chose words (A6).

## A3. The three window sizes

| Window | What it covers | How many | Compared with |
|---|---|---|---|
| **Day** | one calendar day (her time zone, IST) | 352 | the day before |
| **Week** | the 7 days ending on each day, from the 7th day on ("rolling") | 346 | the 7 days before that |
| **Month** | a checkpoint every 30 days, plus a last partial one: the last 30 days **and** the whole year so far | 12 | the previous checkpoint |

Total **710 windows**. Each one is a row in the table `memory_v2`, with an id like `day_2025-12-09`, `week_ENDING_2025-11-22`, `month_ENDING_2025-12-29`.

## A4. "Her usual": the most important idea

For every measure, the engine keeps a running picture of her own normal, built **only from days before the window being judged**:

- **median**: the typical value (for example resting heart rate 76 bpm)
- **spread** (standard deviation): how much it normally moves (about ±5 bpm)
- **flat band**: half that spread (about 2.6 bpm). A change smaller than the band is called **flat**: ordinary wobble, not news.

Example, resting heart rate, as of 10 Sep 2026 (344 earlier days): median 76, spread 5.2, flat band 2.6.

A change is then labelled by how many "flat bands" it is:

| Change vs previous window | Label |
|---|---|
| less than 1 band | flat (nothing to report) |
| 1 to under 2 bands | small |
| 2 to under 4 bands | moderate |
| 4 bands or more | large |

So "resting heart rate up 8 bpm" is *large* for her (3 bands) only if she normally stays within ±5. The same 8 bpm could be small for somebody else. That is the point of a personal baseline.

**Why "only earlier days"?** So the engine never uses the future. A day's usual is learned from days strictly before it. This is tested: the engine is rebuilt from a store with the later data cut off, and the earlier answers must not change. Until there are **14 days** of history, there is no usual yet and the engine says "not enough history" and compares nothing.

**A caution.** Her usual includes her bad stretches (the hospital week, months of missed medicine). It describes *how she has typically been so far*, not how she is when well. If she stays off her normal for a long time, her usual drifts toward the new level.

## A5. "Notable" versus "material change"

Two different ideas, easy to mix up:

| | Meaning | Example |
|---|---|---|
| **Material change** | Anything worth a line in the day's summary | a missed dose, a diary entry, a status worse than her usual, a big change, a data gap, a removed reading |
| **Notable** | A configured threshold ("anchor") was crossed, on cleaned values | sleep fell by more than 1.5 hours; resting heart rate rose by more than 8 bpm; time in range moved by more than 10 points |

A window can have several material changes and still not be notable (9 Dec 2025 above: two missed doses, not notable). A window with **no** material changes is called **quiet**. The model is never asked to decide notability: code does.

Real example, **week ending 22 Nov 2025**: notable, because three thresholds were crossed:

> GMI up 0.33 points (moderate); sleep down 1.82 hours (large); medication adherence down 33.4 percentage points (moderate).

The gist for that week: *"Father hospitalized overnight, a family crisis."* followed by sentences such as "Resting heart rate was sharply up alongside more strained periods of the day." and "She missed metformin on a few days and missed amlodipine and levothyroxine on most days." (The cause-free wording "alongside" is deliberate. See A7.)

Real example, **month ending 29 Dec 2025**: notable because of one monthly anchor: *"lab HbA1c and the glucose-based estimate differ by 1.12 points."* (The lab says her average over about 3 months was worse than what the glucose sensor suggests. Worth a doctor's look.)

## A6. What the language model does, and does not do

| The code does (always) | The model does (only) |
|---|---|
| computes every number, direction and size | picks words for a headline (at most 15 words) and 2 to 4 sentences |
| decides which facts are important and in what order | uses the facts in the order and strength the code gave |
| decides if the window is notable and why | never states notable or the reason |
| decides which glucose readings are artefacts | never sees the internals of the cleaning |

The model gets a **reduced view with no digits at all**: counts become words ("on most days", "a few days"); only measures that actually moved are shown, each with a direction and a size word ("fell noticeably"). A test confirms that no queued window's view contains a digit (the one allowed exception is the word "HbA1c").

Every answer is machine-checked before it is accepted:
1. direction and size match the facts (a "rose" where the code says "down" fails)
2. no causal words ("because", "caused", "led to", "triggered" and similar)
3. no digits, dates, quotes or internal words
4. correct structure (a headline of at most 15 words, 2 to 4 sentences, nothing else)

A failing answer gets one retry with the failures listed. A second failure gets a **code-written fallback line**, so the facts are never lost. In the final store there are **0 fallbacks**.

## A7. What it deliberately does NOT do

- It does not claim causes. "Moved together with glucose" is a note that two things changed in the same direction, not a link. Finding real relationships is the Evidence Engine's job, later.
- It does not read alerts, findings or PI notes. It only reads the store, so nothing downstream can change a baseline number.
- It does not use the 138,118 linker pairings or the 8,160 hourly steps (those serve the Rulebook).
- It does not judge heart-rate *readings* against a clinical range (the range is for rest; a day's heart rate feeds averages and trends only).

## A8. How this feeds the next components

- **State Engine** reads *her usual* (median and spread) from these records, to decide when the newest reading is off.
- **Findings Engine** reads the day and week gists as background context when it writes up a case.
- **Dashboard** ("Her baseline") shows numbers, usual, directions and gist.

---

# Part B. Technical detail

## B1. Two generations in this repo (important)

| | v1 | v2 (the one this document describes) |
|---|---|---|
| Where | `nodes/baseline_engine.py`, `logic/memory_records.py`, tables `numeric_summary`, `memory_records` | `src/v0_code/baseline_v2/`, table `memory_v2` |
| In the LangGraph | **Yes**, the last node (`baseline_engine`) | **No**, runs on its own after the graph |
| What the graph node does today | ingests non-threshold streams into `context_events` (`data/context_ingest.py`) and builds 710 numeric records with `llm_status='skipped'`; the legacy glucose caption is off unless `--glucose-caption` | reads only the finished store |
| Status | kept working and untouched | the current design; its output is what later components read |

So after `uv run v0-code`, the graph has already filled `raw_events` and `context_events`. v2 is then run separately and adds `memory_v2` to the same database file.

```bash
uv run python -m v0_code.baseline_v2.run --stage A              # day tier -> memory_v2 (upsert; never wipes)
uv run python -m v0_code.baseline_v2.run --stage B              # all three tiers
uv run python -m v0_code.baseline_v2.run --stage A --rebuild    # drop and recreate memory_v2 only (explicit)
uv run python -m v0_code.baseline_v2.run_gist --stage C         # model gist sample
uv run python -m v0_code.baseline_v2.stage_d                    # the full gist run (resumable)
```

Timing: Stage A about 1.5 s, Stage B about 2.1 s (all tiers and upsert). The gist run was about 22 minutes, 311 calls.

## B2. Inputs

Reads only the store, and only two tables (`StoreView` in `data.py`, grouped by local day in the configured time zone):

| Table | Rows | Use |
|---|---|---|
| `raw_events` where `source_type='reading'` | 44,469 | value, time and **status** of each evaluated reading |
| `context_events` | 45,952 | heart rate (33,792), medication, mood, meals, location, sleep quality, diary (and hourly steps 8,160, unused here) |

All patient-specific facts are in one YAML, `config/patient_meera_iyer_v1.yaml` (time zone, pronoun, strain categories, device range, jump limit, streams, anchors, windows, gist settings). The config is versioned by content hash and every row records `config_version`. A second synthetic patient runs through the engine with config alone (`tests/test_v2_fixture_patient.py`), so no name, unit or medicine id is in the code.

## B3. Modules

| Module | Role |
|---|---|
| `config.py` | YAML to `Config`; thresholds such as `min(2, n_meds)` |
| `data.py` | `StoreView`: store grouped by local day |
| `trust.py` | clean first (device range plus jump rule), glucose metrics, reliability, the "with them included" twin |
| `profile.py` | median, SD, flat band, usual status from history strictly before the window |
| `tags.py` | direction and size per stream; co-movement |
| `anchors.py` | the configured thresholds, evaluated on cleaned values |
| `material.py` | the typed list of material changes; `quiet` = empty |
| `render.py` | all text built by code: `deviation_text`, code lines |
| `engine.py` | `build_days`, `build_windows` |
| `windows.py` | week and month windows built from the day rows |
| `storage.py` | `MemoryV2Store`: upsert and retrieval |
| `gist_view.py`, `gist_check.py`, `gist.py`, `run_gist.py`, `stage_d.py`, `cleanup.py` | the gist (the only model step) |
| `report.py`, `run.py` | reports and CLI |

## B4. Pipeline per day (`engine.build_days`)

Days are processed in date order; **today becomes history only after it has been judged**.

1. **Clean glucose first** (`trust.clean_series`). Walk the whole series once. A reading is removed if outside the device range **[40, 400] mg/dL**, or if it differs from the last *kept* reading by more than **75 mg/dL per 15 minutes**, scaled by the gap (`gap_units = max(1, minutes/15)`). Only earlier readings are looked at. All later metrics use the kept readings. Result over the year: **3 readings** removed on 3 days, one of them the 599.0 spike on 9 Dec. Five isolated readings of exactly 65.0 pass both rules (reported, not patched).
2. **Day facts.** Glucose: mean, GMI, time in range 70 to 180, above 180 and 250, below 70 and 54, CV, min, max, completeness, by period of the day (overnight, morning, afternoon, evening), post-meal peaks (max glucose within 150 minutes of each meal). Other streams: sleep, steps, sedentary, hydration, screen time, resting heart rate, a daily mean of the 15-minute heart rate, adherence % and which medicine, mood blocks, blood pressure, diary, location, meals.
3. **Daily value per stream.** Each configured stream picks a generic aggregator through its `agg` key (`glucose_mean`, `value`, `mean`, `adherence_pct`, `strained_count`, `post_meal_peak`, ...). Mood counts only **strain** categories (tired low energy, mild stress, anxious, overwhelmed). Calm and uplifted do not count.
4. **Completeness and day status.** Completeness = readings / expected per day (96 for glucose and heart rate, 3 for mood, 1 for daily values). A day's status for a stream = the most common status among its readings (ties broken by name, so deterministic). A stream with `kind: continuous` gets **no** status. Glucose's per-reading statuses use the fasting cut-offs and are not used here.
5. **Her usual, as of today** (`profile.build_profile`) from earlier days only (needs `min_days_for_compare = 14`): median, population SD, `flat_band = 0.5 × SD`, usual status (most common earlier day status), share of non-normal days.
6. **Tags** (`tags.make_tag`): `delta = value − previous value`. `|delta| < band` gives `flat`; otherwise `up` or `down` with size by `|delta| / band`: under 2 small, under 4 moderate, 4 or more large. No band (too little history) or no previous value gives `not_enough_data`. A count of periods (mood) is always worded "N more / N fewer strained periods of the day", never "mood up/down".
7. **Co-movement** (`tags.co_movement`): only if glucose itself moved beyond its band. One entry per domain (the strongest mover in the domain), listed as same or opposite direction to glucose. Never flat versus flat. A note of two things moving together, not a link.
8. **Anchors on cleaned values** (`anchors.evaluate`), and the same anchors on **raw** values. A crossing that exists only on raw values is not counted, and is stored in `anchors_questionable`. `is_notable = len(crossed) > 0`.
9. **Trust flags**: removed reading (with an `affects` list of the metrics it would have changed), gap of more than 1 hour between kept glucose readings, streams under 70% complete. `reliable` = completeness at least 70% **and** at least 14 days of data so far. `confidence` = high (reliable and at least 90% complete), moderate (reliable), low.
10. **Material changes** (`material.build_material`), in this order: anchor crossed, missed dose, diary event, status worse than her usual, large change (not already reported by another item), data gap, low completeness, removed reading. A status counts only if it is **worse than that stream's usual** and at least the configured minimum (`min_material_status: abnormal`, i.e. low or high only). So steps "low" on 95% of days is not news. `quiet` = list is empty.
11. **Text** by code (`render.deviation_text`): the block the model never writes (see the example in A2).

## B5. Anchors (the notable thresholds)

Starting heuristics in the config, not clinical standards. Evaluated per tier. A threshold fires when the change is strictly greater, except where noted.

| Anchor | Day | Week | Month | Note |
|---|---|---|---|---|
| `glucose_TIR_change_points` | 10 | 10 | 10 | change in time in range, percentage points |
| `glucose_CV_change_points` | 8 | 8 | 8 | change in variability |
| `glucose_GMI_change` | none | 0.3 | 0.2 | |
| `severe_range_appeared_or_cleared` | on | on | on | glucose above 250 or below 54 appears or clears |
| `sleep_hours_change` | 1.5 | 1.5 | 1.5 | hours |
| `resting_hr_change_bpm` | 8 | 8 | 8 | uses the daily resting value |
| `adherence_meds_changed` | `min(2, n_meds)` | none | none | counts medicines that went taken to missed; `>=` |
| `adherence_pct_change` | none | 15 | 10 | **drop only**; a recovery is not a crossing |
| `steps_abs_change` | 3000 | 1500 (week mean) | none | absolute floors |
| `lab_cgm_discordance` | none | none | 0.5 | \|lab HbA1c − GMI over the 90 days before the lab\|, inclusive, lab drawn in the checkpoint's own last 30 days |

Fire counts on this patient: day notable 67/352 (19.0%), week 79/346 (22.8%), month 4/12 (33.3%). Dead anchors, never silently retuned: `severe_range_appeared_or_cleared` (its only 4 raw crossings were artefacts), week `glucose_TIR_change_points`, `glucose_CV_change_points`; month those plus `sleep_hours_change` and `resting_hr_change_bpm`.

## B6. Week and month windows (`windows.py`)

- **Week**: rolling 7 days for every day from the 7th (346), compared with the 7 days before. A window's value is the **mean of its daily values** (needs at least `min_days_in_window = 4` days with data). Glucose is pooled over the cleaned readings; adherence = taken / expected doses. Flat bands come from daily values strictly before the window starts.
- **Month**: cumulative from day 1 **plus** the last 30 days, a checkpoint every 30 days and a final partial one (12), compared with the previous checkpoint's last-30 window. This is why every month record's stored start date is 1 Oct.
- Week and month material changes are **aggregated from the day windows' own items**: missed doses become "7 of 30 days"; statuses worse than usual become "on N of 7 days".
- Blood pressure (`status_streams`) is judged reading by reading at window level (a reading takes the worse of its two components; usual = most common earlier reading status): "Blood pressure above the reference range on 3 of 5 readings".
- Month only: `chronic_findings` (streams non-normal on at least 50% of days so far) and `lab_link` (each lab next to the GMI over the prior 90 days, with the signed gap). The month tier lists diary entries only at `moderate` or worse (cap 8), and counts the rest ("7 other diary entries: 4 life events, 2 social interactions, 1 substance use").

## B7. Output: `memory_v2` (in `output/personal_data_store.db`)

One row per window, upsert keyed by `window_id` (re-runs are idempotent and **never drop** the table without `--rebuild`). 710 rows: 352 day, 346 week, 12 month.

| Column | Content |
|---|---|
| `window_id`, `tier`, `start_date`, `end_date` | e.g. `week_ENDING_2025-11-22` |
| `reliable`, `confidence` | computed in code |
| `facts_json` | all code-computed facts: glucose metrics, by-period stats, post-meal peaks, per-stream values, completeness, `profile_asof` (her usual as known on that date), `deltas` (clean and raw) |
| `tags_json` | direction tags with sizes, plus the co-movement block |
| `material_changes_json` | the typed list |
| `anchors_crossed`, `anchors_questionable`, `is_notable`, `notable_reason` | **code only** |
| `deviation_text` | the code-rendered text block (THINGS THAT DEVIATED / NUMBERS / WHAT CHANGED / MOVED TOGETHER / TRAJECTORY / CAVEATS / STEADY) |
| `data_quality_json` | removed readings, flags with `affects`, completeness, reliable |
| `gist_headline`, `gist_sentences`, `gist_status`, `llm_raw`, `usage_json` | the text layer |
| `config_version` | hash of the config used |

Retrieval (`MemoryV2Store`): `get_memory`, `get_memories_between`, `get_notable`, `get_profile_asof(stream, date)`. These return parsed objects. `facts` comes only with `full=True`.

## B8. The gist stage

**Which windows get a model gist.** Status `code_line_early` (under 14 days of history, or no previous window) and `code_line_quiet` (nothing material) get a code-written line instead. Everything else is queued.

| Tier | Windows | Code line (no model) | Sent to model | Passed first try | Passed after retry |
|---|---|---|---|---|---|
| Day | 352 | 105 (14 early + 91 quiet) | 247 | 225 | 22 |
| Week | 346 | 14 (early) | 332 | 295 | 37 |
| Month | 12 | 1 (early) | 11 | 8 | 3 |
| **Total** | **710** | **120** | **590** | **528** | **62** |

**Model and settings**: `openai/gpt-5-mini` through OpenRouter, reasoning low, 90 s timeout, no SDK retries, concurrency 6, batches of 4 days / 2 weeks / 1 month per call. The prompts are the spec's, verbatim (a test compares them with `task/baselineV2.md`).

**The view** (`gist_view.build_gist_view`) has no digits; frequencies are words; only moved measures appear; a `top_items` list comes first (serious diary theme, missed medicines, anchors and large changes by size, statuses worse than usual) and the headline must cover the first one. Places are named only if not among her two most frequent. The month adds long-standing patterns (non-normal on more than 50% of days) and a lab-versus-estimate line. An anchor-crossed measure is worded at least *moderate*.

**Checks and rules** (`gist_check.py`): direction and size per clause, causal words (including "affected / impacted / influenced / contributed" and "as a result"), digits, dates, quotes and internal words, structure. "Tentative / uncertain" is rejected unless the window is not reliable. A failed window after the retry gets `code_line_fallback`, built from the two most important material items.

**Measured**: first-attempt failure day 8.1%, week 14.5%, month 36.4% (4 of 11). Of 91 failure instances, 82 were the model (39 copied diary phrases, 25 "because"), 6 were check errors (later fixed), 2 timeouts. After the cleanup round, **590 model gists (528 `gist_ok`, 62 `gist_retry_ok`), 0 fallbacks**. An upsert keeps a gist written by the model, but does not yet detect that its facts changed (parked).

## B9. Gotchas and design decisions

1. **As-of everywhere.** Day D's profile uses days before D. `tests/test_v2_invariants.py` rebuilds from a truncated store (no look-ahead) and from a store with the removed readings deleted (a questionable reading moves nothing).
2. **Glucose bands differ from component 1.** Here: ADA management bands (70, 180, 250, 54). Component 1's status uses fasting cut-offs (70, 99, 125). The two disagree by design.
3. **"Resting" heart rate.** `resting_hr_change_bpm` uses the single daily resting value. The hourly-steps-based "resting period" mean from v1 is not rebuilt (v2 has no hourly steps). The v1 `resting_period_mean` and the daily `resting_heart_rate_daily` are different things. Never mix them.
4. **A missing value is unknown, not zero** (12 days have no step data; the hourly steps file covers 340 days).
5. **Questionable readings.** A flagged window records the metrics both with and without them. Anchors use the cleaned values only. A crossing that only existed because of a bad reading is stored as `anchors_questionable`.
6. **A day's status is a vote.** Most common reading status that day. A day's usual is the most common day status over her earlier history.
7. **Notable is code's decision.** Never let the model write `is_notable` or `notable_reason`.
8. **Quiet counts.** Day quiet 91/352; week quiet 0/346 (a diary entry or missed dose is nearly always in 7 days); month never quiet.
9. **No time-of-day or post-meal usual and no blood-pressure usual** in the baseline. The State Engine builds its own from earlier readings.
10. **Reported, not patched**: 5 isolated glucose readings of exactly 65.0 remain in the metrics (1 is removed by the jump rule); labs read above the CGM-derived GMI.
11. **Do not wipe the store.** `uv run v0-code` refuses to run if `output/personal_data_store.db` exists unless `--rebuild`. A rebuild wipes the v1 memory entries (472 model-written ones in `memory_records`): back them up first. `--rebuild` on the v2 run drops `memory_v2` only.
12. **Tests**: `tests/test_v2_*.py` (invariants, storage, stage B, gist, review rounds, fixture patient) and `tests/test_anchors.py`.

## B10. Quick checks (read-only)

```bash
sqlite3 -readonly output/personal_data_store.db \
  "select tier, count(*) from memory_v2 group by 1;"            # 352 day / 346 week / 12 month

sqlite3 -readonly output/personal_data_store.db \
  "select window_id, gist_headline from memory_v2 where is_notable=1 and tier='week' limit 5;"

sqlite3 -readonly output/personal_data_store.db \
  "select json_extract(facts_json,'$.profile_asof.resting_heart_rate') from memory_v2 where window_id='day_2026-09-10';"
```

The dashboard pages for this component are `#/stage/baseline` and `#/baselines` ("Her baseline").
