# 5. Rulebook Lookup

You can read Part A without opening any code. Part B is the technical detail for engineers. Numbers come from `output/rulebook_lookup.db` (table `rulebook_packets`) and `understand/how_the_numbers_flow.md` §5, unless said otherwise.

---

# Part A. The idea in plain words

## A1. The problem it solves

The State Engine has just raised an alert: "her glucose is clearly above her usual." The next question any doctor would ask is: **"what might be behind it?"**

Before anyone can test that on her data, somebody has to decide **which factors are worth checking**. For a glucose high after a meal, the sensible checklist is the meal itself, a missed dose, short sleep, stress, low activity, illness. For a high heart rate, it is activity just before, stress, fever, dehydration. Testing everything on every alert would be noisy and slow, and many of those checks would be meaningless.

The Rulebook Lookup produces that checklist. It is a **lookup, not an analysis**: it reads no data from her, calculates nothing, and concludes nothing. It simply answers:

> **"For this kind of alert, which factors should be checked, in what order, where in time, and how many?"**

Think of a **triage handbook**. A nurse sees "chest pain, adult" and flips to the page for it: a fixed list of questions to ask, in a fixed order. She doesn't invent the list, and the page doesn't say what the patient has. The Rulebook Lookup is that page-finder.

## A2. A worked example: the glucose alert from 9 Sep 2026

**What comes in** (from the State Engine): glucose above her usual, "clearly", 143.1, opened at 22:30, last meal (dinner) 148 minutes earlier.

**Step 1: find the rule.** There are 10 rules in a fixed rulebook. Glucose-above is split in two by timing:
- a meal was logged within the last 180 minutes → rule `glucose_above_post_meal`
- no meal within 180 minutes → rule `glucose_above_no_recent_meal`

The dinner was 148 minutes ago, so this alert matches **`glucose_above_post_meal`**. Matching is mechanical: the same alert always gets the same rule.

**Step 2: look at that rule's candidate list.** The rule lists 10 candidate factors in a fixed order: meal composition (primary), then medication adherence, sleep, stress, activity, illness symptoms, meal timing (secondary), then other medications, cycle phase, alcohol (tertiary).

**Step 3: throw out candidates that can't apply to her.**

| Candidate | Result | Why |
|---|---|---|
| other medications | **skipped** | applies only if she takes a glucose-raising medicine (steroids and similar). She takes none |
| cycle phase | **skipped** | needs a menstrual-cycle data stream, and none is in the store |

**Step 4: apply the budget.** This rule allows all primary candidates, at most 5 secondary, at most 2 tertiary, at most 8 in total. She has 1 primary + 6 secondary + 1 tertiary left, and only 5 secondary fit, so the 6th secondary (**meal timing**) is cut.

**Step 5: for each survivor, write down what to check and where to look.** The packet that goes out holds 7 candidates, for example:

| # | Candidate | What would be compared | Where in time |
|---|---|---|---|
| 1 | meal composition | this meal's response vs her earlier meals of the same kind | the 240 minutes before the alert (18:30 to 22:30) |
| 2 | medication adherence | evenings after a missed dose vs evenings with all doses taken | the 2 days up to the alert (8 Sep 00:00 to 9 Sep 22:30) |
| 3 | sleep | days after short sleep vs normal sleep | the previous night's sleep record |
| 4 | stress / mood | strained days vs calm days | 9 Sep 00:00 to 22:30 |
| 5 | activity | low-activity days vs normal days | 9 Sep 00:00 to 22:30 |
| 6 | illness symptoms | days with a symptom entry vs none | the 3 days up to the alert |
| 10 | alcohol | days with an alcohol entry vs none | 9 Sep 00:00 to 22:30 |

The packet carries **no values**. It doesn't say "she missed levothyroxine" or "sleep was 6 hours". It says only "check these, in these windows". Whether any of them actually matters for her is decided by the next component (the Evidence Engine), on her own history.

## A3. A few things worth knowing

- **One packet per alert.** 287 alerts in, 287 packets out.
- **The rulebook is fixed and was written in advance** from published clinical-education sources (version `v0-draft-1`, marked unreviewed). It was not learned from her. Nothing in the rulebook changes by itself.
- **What differs between two packets of the same rule** is only which candidates survive the "can this apply to her?" checks, and the exact time windows, which are worked out from each alert's own opening time.
- **Some candidates are dropped for her specifically.** Caffeine (no caffeine data exists), "other medications" (she takes no glucose-raising one), cycle phase (no cycle stream in the store), the dawn effect (only if the alert opened between 04:00 and 09:00), insulin or sulfonylurea (she takes neither), blood-pressure-raising medicine (she takes none).
- **A "deferred" rule** (screen time above, no clinical evidence base) still gets a packet, but every candidate is listed as "not selected, rule deferred" and nothing is tested.
- **The raised bar.** When a packet selects more candidates than the evidence limit of 4 (here 5 to 8), the packet carries `evidence_bar_hint: raised`, a note telling the Evidence Engine to hold the results to a higher bar, because testing many things at once makes a chance finding likelier.

## A4. What it deliberately does NOT do

- It does not read any of her data and does not know whether a window contains any readings.
- It does not say whether a factor matters, or whether there is enough history to test it.
- It does not explain the alert. The checklist is a list of **candidates**, not causes.
- It does not use a language model. It is deterministic: same alert, same packet.
- It never edits the rulebook files.

## A5. Where its output goes

Each packet goes to the **Evidence Engine** (component 6), matched by the alert's id. For each selected candidate, the Evidence Engine looks at her own history and says whether the factor shows up in her data, with statistics.

---

# Part B. Technical detail

## B1. Position in the system

```
State Engine hand-offs (output/state_engine.db, read-only)
         │  287 hand-offs
         ▼
RULEBOOK LOOKUP  ◄── rulebook files (task/evidence_engine/*, never edited)
         ▲            config/rulebook_meera_iyer_v1.yaml (this patient: stream map, medicine classes, flags)
         │
         └──► output/rulebook_lookup.db (rulebook_packets) + output/rulebook_lookup_report.md
                    │  one packet per hand-off
                    ▼
              Evidence Engine
```

Not part of the LangGraph. Deterministic, **stateless**, no model, no data in the packet. Spec: `task/rulebook_lookup_spec.md` (Amendments on top win). The engine names no stream, medicine or patient (a test enforces it). Time zone and the medicine-id pattern come from the Baseline config, so the engines agree.

```bash
uv run python -m v0_code.rulebook_lookup.run --config config/rulebook_meera_iyer_v1.yaml            # packets -> output/rulebook_lookup.db (replaced by packet_id) + report
uv run python -m v0_code.rulebook_lookup.run --config ... --print <handoff_id>                       # one packet as JSON
uv run python -m v0_code.rulebook_lookup.run --config ... --rebuild                                  # drop the packet table first (explicit)
```

## B2. Modules (`src/v0_code/rulebook_lookup/`)

| Module | Role |
|---|---|
| `grammar.py` | The three small grammars of the rulebook files and the lookback kinds (parsing only) |
| `rulebook.py` | Loads rules and candidates, checks them, `Rule` / `Candidate` objects |
| `config.py` | Patient config: stream map, medication classes, flags; evaluates `applies_if` |
| `lookup.py` | `build_packet(handoff, book, cfg)`: a pure function |
| `windows.py` | Resolves a lookback kind into absolute times for one hand-off |
| `storage.py` | `PacketStore`: one table, replace by `packet_id` |
| `report.py`, `run.py` | Markdown report and CLI |

## B3. The rulebook (data, not code)

Files in `task/evidence_engine/`: `rulebook_v0_rules.csv` (10 rules), `rulebook_v0_candidates.csv` (69 candidates), `rulebook_v0.md` (the sources S1..S20). Version `v0-draft-1`, review status **unreviewed**.

**Rules** (a measure and a direction, with an optional `context_match`):

| Rule | Alerts | Candidates | Budget: primary + secondary max + tertiary max (total max) |
|---|---|---|---|
| `heart_rate_above` | 124 | 9 | 3 + 3 + 2 (8) |
| `glucose_above_no_recent_meal` | 59 | 9 | 2 + 3 + 2 (7) |
| `glucose_above_post_meal` | 40 | 10 | 1 + 5 + 2 (8) |
| `medication_adherence_below` | 24 | 6 | 2 + 3 + 1 (6) |
| `resting_heart_rate_above` | 12 | 7 | 2 + 3 + 1 (6) |
| `sleep_below` | 10 | 7 | 1 + 3 + 2 (6) |
| `glucose_below` | 5 | 6 | 2 + 3 + 1 (6) |
| `blood_pressure_above` | 3 | 8 | 2 + 3 + 2 (7) |
| `hydration_below` | 2 | 5 | 2 + 2 + 1 (5) |
| `screen_time_above` (**deferred**) | 8 | 2 | rule not switched on |
| **Total** | **287** | **69** | |

**Candidates** carry: `rule_id`, `rank`, `weight_tier` (primary, secondary, tertiary), `candidate`, `requires_streams`, `lookback_kind` and `lookback_value`, `applies_if_rule`, `check_type`, `check_text`, `outcome_compared_text`, `evidence_level` (A 36, B 22, C 9, D 2), `sources`, a data-status code and a note. Check types: `group_comparison` (58), `presence_check` (6), `percentile_vs_history` (2), `pattern_repeat` (2), `shape_check` (1).

## B4. The three small grammars (`grammar.py`)

**`context_match`** (on a rule): an `or` of `and`s of conditions on `last_meal_minutes_ago` (`<=`, `>=`, `==`, `<`, `>`) or `last_meal absent` / `present`. A comparison needs a logged meal; no meal means `minutes = None`. Empty means no extra condition.

Example: `last_meal_minutes_ago<=180` (post-meal) versus `last_meal_minutes_ago>180 or last_meal absent` (no recent meal).

**`requires_streams`** (on a candidate): `;` separates **groups** (all needed), `|` separates the **alternatives** inside a group (fallbacks, in order). A token can be `name` or `name[category]` (for example `diary_context[symptom]`).

**`applies_if_rule`** (on a candidate): terms separated by `;` are **all required**; inside a term `|` means **any of**. Four kinds:

| Kind | Example | Decided by |
|---|---|---|
| `patient_flag:<flag>` | `takes_glucose_lowering_medication` | the config (explicit flag wins over a derived one) |
| `medication_class_present:<class>` | `glucose_raising`, `insulin`, `thyroid` | the config's `medication_classes` |
| `stream_present:<stream>` | `menstrual_cycle` | whether the config maps a stream for it |
| `open_time_between:HH:MM-HH:MM` | `04:00-09:00` | the alert's own `opened_at`, in the patient's zone |

A rule file that does not parse is refused at load.

## B5. Lookback kinds (`windows.py`)

A candidate's lookback becomes an absolute window for one hand-off. Everything is relative to `opened_at`, in the patient's time zone. The Lookup **never checks whether data exists** in the window.

| Kind | Resolves to |
|---|---|
| `minutes_before_open` (n) | `[opened_at − n min, opened_at]` (elapsed-time arithmetic) |
| `days_ending_at_open` (n) | from local midnight n−1 days earlier, to `opened_at` |
| `same_calendar_day` | local midnight of that day, to `opened_at` |
| `previous_calendar_day` | the whole previous local day |
| `previous_night` | `{record: latest_sleep_record_at_or_before_open}` (a record, not a time range) |
| `previous_evening` | the most recent 18:00–24:00 window that started before `opened_at` (so the current evening after 18:00, cut at `opened_at`; otherwise yesterday's) |
| `at_open` | the single instant `opened_at` |
| `minutes_around_open` (n) | `[opened_at − n, opened_at + n]`; marks `includes_after_open: true` and an `earliest_evaluation_time` |

Only `minutes_around_open` reaches past the alert (used by the glucose-below sensor-artifact shape check, which needs the readings after the low).

## B6. Building a packet (`lookup.build_packet`)

A **pure function** of (hand-off, rulebook, config). Steps:

1. **R1: match the rule.** Rules with the hand-off's measure and direction whose `context_match` is true, in file order. None gives status `unmatched` (counted and logged, not an error). More than one gives `ambiguous` (the first is used). The `last_meal_minutes_ago` comes from the hand-off's `context.last_meal.minutes_ago`.
2. **R2: deferred rules.** A deferred rule's packet lists every candidate under `not_selected` with reason `rule_deferred`, so completeness holds. Hint `standard`.
3. **R3: applicability.** A candidate whose `applies_if` fails is **skipped**, reason `applies_if_not_met`, with the failing term as detail.
4. **R4: availability.** For each `requires_streams` group, the first available alternative is `used`; later ones carry `fallback_for`. A candidate with **no** available stream is skipped, reason `no_stream`.
5. **R5: budget.** Walk the runnable candidates in rank order. Primary candidates are always taken. Others are taken while the total is under `max_total` and that tier is under its cap. The rest become `not_selected`, reason `budget`. A skipped candidate used none of the budget.
6. **R6/R7: lookback and provenance.** Each selected candidate gets its resolved window, evidence level, sources, data-status code, review status and note.
7. **R8: evidence bar.** `evidence_bar_hint = raised` if more than `raised_bar_above` (4) candidates were selected, otherwise `standard`.

**Packet shape** (real, abridged):

```
packet_id, handoff_id, status (omitted when ok; deferred | unmatched | ambiguous otherwise), rulebook_version, rulebook_review_status
matched_rule     {rule_id, status, context_match, budget{primary_count, secondary_max, tertiary_max, max_total}, review_status}
handoff_summary  {measure, direction, size, trigger, position_z, usual_basis, value, clinical_status, opened_at, last_meal_minutes_ago}
selected[]       {rank, weight_tier, candidate, check_type, check_text, outcome_compared_text,
                  streams[{generic, patient_stream, category, available, used, fallback_for?}],
                  lookback{kind, value, text}, resolved_window, evidence_level, sources, data_status_code, note}
skipped[]        {candidate, reason, detail}
not_selected[]   {candidate, weight_tier, reason}
counts           {candidates_in_rule, selected, skipped, not_selected}
evidence_bar_hint
```

Stored in `rulebook_packets` (`packet_id` PK, `handoff_id`, `rule_id`, `status`, `rulebook_version`, `n_selected`, `n_skipped`, `n_not_selected`, `packet_json`). It has **no timestamp**, so a re-run gives identical rows. A write replaces the row of the same `packet_id`. Dropped only with `--rebuild`.

## B7. Patient config (`config/rulebook_meera_iyer_v1.yaml`)

- **`stream_map`**: generic token → this patient's stream, or `null` when not available. Notable decisions:
  - `food_content` → `meal_events` (the food text lives there)
  - `medication_list` → `derived:medication_classes` (available if the class map is non-empty)
  - `step_count_hourly` → the ingest-only stream (used by the heart-rate "activity" candidate, with the daily `step_count` as the second alternative)
  - `time_of_day` → derived (always available)
  - `menstrual_cycle`, `caffeine_intake`, `lab_tsh` → **null** (see B9)
- **`medication_classes`**: metformin → `glucose_lowering`, amlodipine → `antihypertensive`, levothyroxine → `thyroid`. The keys are her medicines.
- **`patient_flags`**: `has_thyroid_condition: true` is **asserted from the persona document**, not derived (the data has no condition list).
- **`derived_flags`**: `takes_glucose_lowering_medication` ← class `glucose_lowering`; `takes_bp_medication` ← `antihypertensive`.
- **`raised_bar_above: 4`**.

## B8. Results on this patient (287 hand-offs)

| Packet status | Packets | Selected | Skipped | Not selected |
|---|---|---|---|---|
| `ok` | 279 | 1,899 | 373 | 137 |
| `deferred` (screen time) | 8 | 0 | 0 | 16 (`rule_deferred`) |
| `unmatched` / `ambiguous` | 0 | | | |

- Selected by tier: 632 primary, 910 secondary, 357 tertiary. Each active packet has 5–8 selected: 5 in 66 packets, 6 in 46, 7 in 43, 8 in 124. Every active packet has `evidence_bar_hint: raised`; the 8 deferred packets have `standard`.
- 153 not selected in all: 137 cut by the budget plus the 16 from deferred packets.
- 14 of the 69 candidates are never selected for any alert.

**The 373 skips:**

| Skipped candidate | Packets | Reason |
|---|---|---|
| caffeine (stimulants) | 124 (every heart-rate packet) | `no_stream`: no caffeine data anywhere |
| other medications (glucose-raising) | 99 (every glucose-above packet) | `applies_if_not_met`: she takes none |
| cycle phase | 99 (every glucose-above packet) | `applies_if_not_met`: no cycle stream in the store |
| dawn effect | 43 of the 59 no-recent-meal packets | `applies_if_not_met`: alert not opened 04:00–09:00 (the other 16 kept it) |
| insulin or sulfonylurea | 5 (every glucose-below packet) | she takes neither |
| blood-pressure-raising medicine | 3 (every BP packet) | she takes none |

124 + 99 + 99 + 43 + 5 + 3 = 373.

## B9. Gotchas and decisions to check before changing anything

1. **A lookup, never an analysis.** The packet holds no data and no result. Do not add a value to it.
2. **The rulebook is read-only** to the engine. All changes happen in the CSVs (with a version bump) or in config. The code contains no stream, measure, medicine or patient name.
3. **Passing here is not "enough data to test."** The check does not ask whether there is enough history. That is the Evidence Engine's job, which is why a candidate can pass here and later be labelled "insufficient".
4. **The cycle data is not in the store.** `final/menstrual_cycle_full_year.csv` exists (352 daily rows) but the context ingest has no cycle stream, so the config maps it to `null` and the Lookup treats it as unavailable. Ingesting it is a parked upstream task. The file also says `menopause_status = peri`, so evidence for a cycle-phase candidate is not established for her case. TSH lab rows are in the same position.
5. **`has_thyroid_condition` is asserted**, not derived from data. Levothyroxine would trigger the thyroid candidate on its own.
6. **Hourly steps are ingest-only.** They sit in `context_events` for the Rulebook only. The Baseline and State engines do not use them. The hourly steps and the continuous heart rate were generated together, so an activity-to-heart-rate relationship is built in by construction (`docs/hourly_steps_and_heart_rate_note.md`).
7. **A fallback stream lists every alternative** with `used` / `fallback_for`. Only the first available one is `used`.
8. **`previous_evening`** is the most recent 18:00–24:00 window that started before `opened_at`: after 18:00 it is the *current* evening, cut at `opened_at`.
9. **The budget is mechanical.** The same 14 candidates are never picked for any alert because of rank order and caps. Changing the budget needs a rulebook edit, not a code change.
10. **The rulebook is `unreviewed`.** It was drafted from published clinical-education sources and has had no clinician review (every rule and candidate carries `review_status: unreviewed`).
11. **Tests**: `tests/test_rulebook_lookup.py`.

## B10. Quick checks (read-only)

```bash
sqlite3 -readonly output/rulebook_lookup.db \
  "select status, count(*), sum(n_selected), sum(n_skipped), sum(n_not_selected) from rulebook_packets group by 1;"

sqlite3 -readonly output/rulebook_lookup.db \
  "select rule_id, count(*) from rulebook_packets group by 1 order by 2 desc;"

uv run python -m v0_code.rulebook_lookup.run --config config/rulebook_meera_iyer_v1.yaml --print handoff_glucose_2026-09-09T22:30
```

Dashboard page: `#/stage/rulebook`. Longer reference: `docs/rulebook_lookup_step1_report.md` and the generated `output/rulebook_lookup_report.md`.
