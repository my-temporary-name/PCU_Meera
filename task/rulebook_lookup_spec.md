# Amendments (decided after the Step 1 review; they replace the body of this spec wherever they differ)

Where the spec body and this section disagree, **this section wins**. The rulebook files (`rulebook_v0_rules.csv`, `rulebook_v0_candidates.csv`, `rulebook_v0.md`) are unchanged and stay in `task/evidence_engine/`; this spec now lives in `task/`. Step 1 findings are in `docs/rulebook_lookup_step1_report.md` (A1..A20, D1..D7 below refer to it).

## Decided by the product owner

1. **`food_content` (D1).** In the config `food_content` maps to the stream `meal_events` (the food description is stored there). No rulebook change. In a packet both generic tokens (`meal_events`, `food_content`) appear with `patient_stream: "meal_events"`.
2. **`medication_list` (D2).** Available if `medication_classes` is non-empty. The patient's medicines are the keys of `medication_classes`. Medicine names are normalised with the Baseline config's `medication_id_regex` before matching, so `med_002_metformin` and `metformin` are the same medicine. In `stream_map` the value `derived:medication_classes` means "available if `medication_classes` is non-empty"; `derived` means always available (`time_of_day`).
3. **`menstrual_cycle`, `step_count_hourly`, `lab_tsh` (D3).** All three stay `null` in the config. The config carries a comment: the cycle file has `menopause_status = peri`, and the evidence for the `cycle_phase` candidate is not established for that case. **Parked, as separate upstream tasks:** ingest hourly steps, the cycle file and TSH into the Personal Data Store.
4. **`has_thyroid_condition` (D4).** Stays `true`, with a config comment: asserted from the persona document, not derived from data.
5. **Fallback streams (D5, replaces 5.2's silence and the `streams` shape in 7.1).** `streams` has one object per alternative, in order. Every object has `generic`, `patient_stream`, `available` and `used`. Only the first available alternative has `used: true` (a token with a single alternative has `used` equal to `available`). Every alternative after the first carries `fallback_for`, the `generic` of the first alternative. A group with no available alternative has `used: false` throughout. `patient_stream` is `null` when the token is unavailable. (The 7.1 example predates this: add `"used": true` to its stream objects.)
6. **Deferred packets (D6, replaces R2).** A deferred packet has `status: deferred`, `matched_rule` set, `selected: []`, `skipped: []`, and **every candidate of the rule** in `not_selected` with `reason: "rule_deferred"` (`candidate` and `weight_tier` as for any `not_selected` entry). `counts`: `candidates_in_rule` = number of candidates, `selected` 0, `skipped` 0, `not_selected` = number of candidates. Property 6 therefore holds for every matched packet. `evidence_bar_hint` is `standard`.
7. **Time zone (A12, replaces the "local time" wording in 3).** The patient time zone is read from the same Baseline config setting the State Engine uses (`patient.timezone`, reached through `rulebook.baseline_config`). The UTC offset in the hand-off's `opened_at` is used only as a fallback when no time zone is configured. All windows and `open_time_between` use that zone.
8. **Version (A1, replaces the last item of property 14).** `rulebook_version` is taken from the rules file. The cross-file version check is dropped (the candidates file has no version column). The rows of the rules file must agree with each other.
9. **`handoff_summary` (A13, replaces its key list in 7.1).** `measure`, `direction`, `size`, `trigger`, `position_z`, `usual_basis`, `value`, `clinical_status`, `opened_at`, `last_meal_minutes_ago`. `value` and `clinical_status` are copied exactly as given, including objects (blood pressure, medication adherence) and `null`; `position_z` and `usual_basis` likewise. `last_meal_minutes_ago` is `null` when no meal is logged.
10. **`previous_evening` (A15, adds to 3).** The definition is unchanged: the most recent 18:00 to 24:00 window that **started before `opened_at`**, cut off at `opened_at`. It is therefore the *current* evening when the item opens after 18:00. Example: opened 2026-09-17 22:30 → 2026-09-17 18:00 to 22:30; opened 2026-09-17 03:00 → 2026-09-16 18:00 to 24:00; opened exactly 18:00 → the evening before (the window must have started *before* `opened_at`).
11. **Packet log (A14).** Its own file `output/rulebook_lookup.db`, one table `rulebook_packets` with the columns of 7.2. A re-run **replaces** rows by `packet_id` (so the log always holds the packet for the current rulebook and config). The table is dropped only by an explicit `--rebuild`. The State Engine database is opened read-only; the Personal Data Store is not opened. It is a CLI (`uv run python -m v0_code.rulebook_lookup.run`), not a graph node.
12. **Other proposals accepted as written:** A2 (overlap check on a probe set of last-meal values: absent, 0, a large value, and every number in the grammar and ±1; two rules with an empty `context_match` for the same measure and direction fail at once), A6 (see 2), A7 (`open_time_between`: start inclusive, end exclusive, a range may cross midnight).

## My handling of the ambiguities not decided above (the rest of A1..A20)

| # | Section | Handling |
|---|---|---|
| A3 | 5.1 | Minimal grammar: `last_meal_minutes_ago <op> N` (op: `<=`, `<`, `>=`, `>`, `==`), `last_meal absent` / `last_meal present`, joined by `or` and `and` (`and` binds tighter). An unparseable string fails the load. 180 minutes stays a rulebook value; the State Engine's own `meal_window_minutes: 180` is a separate copy (noted, not linked). |
| A5 | 5.2 | `;` splits groups, `|` splits alternatives inside a group. A group is available if any alternative is; a candidate is runnable if any group is available. |
| A8 | R3 | For a failing OR group, `detail` is the whole term as written in the file. If a flag is in both `patient_flags` and `derived_flags`, the explicit `patient_flags` value wins. |
| A9 | R5 | Primary candidates are always selected; `max_total` can only stop secondary and tertiary ones. A load check requires `max_total >= primary_count`. No check that `max_total` is at most the sum of the three caps. |
| A10 | R8 | A packet with nothing selected (deferred, unmatched) has `evidence_bar_hint: standard`. |
| A16 | 3 | `previous_night` resolves to `{"record": "latest_sleep_record_at_or_before_open", "includes_after_open": false}`, as in the example. Nothing else. |
| A17 | CSV | The structured lookback wins over the text, even where they differ in meaning (`dawn_effect`, `sleep_below` stress, `measurement_context`). No change. |
| A18 | 3 | `minutes_around_open` is as specified (only `glucose_below` #1); all five low packets carry `includes_after_open: true` and an `earliest_evaluation_time`. No change. |
| A19 | 4.2 | `data_status_meera_code` is copied as `data_status_code` and never used to select or skip. No change. |
| A20 | 4.3 | `stream_map` is the only authority for availability. The engine never looks the names up in the store registry. |

Note: Step 1 listed 20 ambiguities (A1..A20). The decisions above cover 10 of them directly (A1, A2, A4, A6, A7, A11, A12, A13, A14, A15), so the table has **10** rows, not 13.

## Load checks added by these amendments

`max_total >= primary_count` (A9); every candidate row names a rule that exists; `check_type`, `weight_tier`, `evidence_level`, `status` values are in their allowed sets; the rows of the rules file carry one `rulebook_version`.

---

# Rulebook Lookup (General Intelligence): Definition Spec

## 0. How to read this document

This document says **what Rulebook Lookup is**: its purpose, inputs, rules, outputs and the keys that appear in them. It does not say how to build it. Module layout, function names, data structures and code style are yours to decide.

Where this document is silent, state your assumption in your report. Do not invent behaviour silently.

Values marked **default** live in config, not in code. Items marked **[verify]** come from earlier reports; check them against the real code and database and say where they differ.

The rulebook itself is **data**, delivered as three files next to this spec:
- `rulebook_v0_rules.csv`: one row per condition (10 rows)
- `rulebook_v0_candidates.csv`: one row per checklist item (69 rows)
- `rulebook_v0.md`: the same content for people, with sources and a review checklist

If the CSV files and `rulebook_v0.md` disagree, the CSV files win. Within the candidates file the structured columns win over the `*_text` columns.

---

## 1. What Rulebook Lookup is

> **Rulebook Lookup is a fixed, clinically-grounded checklist of what to check when a metric deviates. It is the same for everyone at first.**

For one State Engine hand-off, it returns one **packet**: an ordered, weighted list of candidate factors to test, the data each needs, how far back to look, and a budget on how many to test. That is all.

### 1.1 What it is not

- It does not fetch readings, run statistics or decide whether a factor mattered. Evidence Engine does that.
- It carries no readings and no results. A packet holds rules only.
- It does not use an LLM, and it does not learn. Personalisation and cross-patient learning are later components.
- It makes no causal claim. A weight is a **prior** about what to test first. It is never evidence and never becomes a confidence in a Finding.
- It is not clinically reviewed. Every row says `review_status = unreviewed`, and the packet repeats that.

---

## 2. Where it sits

```
State Engine: deviation item opens -> hand-off record (written once per item)
        |
RULEBOOK LOOKUP   (reads: the hand-off, the rulebook files, patient config)
        |
packet (rules only) -> rulebook packet log
        |
Evidence Engine (later): fetches data from the store, runs the checks, reports each result separately
```

- **One packet per hand-off.** A hand-off is one event. A packet is its checklist.
- **Stateless and deterministic.** The same hand-off, rulebook and config always give the same packet.
- **Read-only.** It writes nothing to the Personal Data Store, to `memory_v2` or to the State Engine's tables. It writes only its own packet log.

---

## 3. Time model

Rulebook Lookup has no clock of its own. Everything is relative to the hand-off's `opened_at`.

Lookback windows are resolved to absolute times for the packet, so that Evidence Engine does not have to interpret them. Rules for resolving:

| `lookback_kind` | `lookback_value` | Resolved window (local time of the patient) |
|---|---|---|
| `minutes_before_open` | minutes | `opened_at - value` to `opened_at` |
| `days_ending_at_open` | N days | local midnight of the day N-1 days before the opening date, to `opened_at` |
| `same_calendar_day` | none | local midnight of the opening date, to `opened_at` |
| `previous_calendar_day` | none | the whole local day before the opening date |
| `previous_night` | none | not a window: the latest sleep record at or before `opened_at` |
| `previous_evening` | none | the most recent 18:00 to 24:00 window that started before `opened_at`, cut off at `opened_at` |
| `at_open` | none | the instant `opened_at` |
| `minutes_around_open` | minutes | `opened_at - value` to `opened_at + value`; flagged `includes_after_open: true` |

**No look-ahead.** Every window ends at or before `opened_at`, except `minutes_around_open`. For that kind the packet states `earliest_evaluation_time` (`opened_at + value`): the check cannot be run before then, because it needs readings after the opening.

Rulebook Lookup does not check whether data exists inside a window. That is Evidence Engine's job.

---

## 4. Inputs

### 4.1 The hand-off record (from the State Engine)

Fields used [verify against `state_handoffs`; names below are from the State Engine's reference examples]:

| Key | Meaning | Used for |
|---|---|---|
| `handoff_id`, `item_id` | identifiers | packet identity |
| `measure` | measure key, e.g. `glucose`, `heart_rate`, `sleep_duration` | rule matching |
| `direction` | `above` or `below` | rule matching |
| `size`, `trigger`, `position_z`, `usual_basis` | how far off, how it opened | copied into the packet summary |
| `value`, `clinical_status` | value and Threshold Evaluator status at opening | copied into the packet summary |
| `opened_at` | when the item opened | resolving lookbacks; `open_time_between` |
| `context.last_meal.minutes_ago` | minutes since the last logged meal, or absent | rule matching (`context_match`) |

Other context fields (medicines today, sleep last night, other open items, diary count) are not used for matching. They are not copied into the packet. Evidence Engine reads the hand-off record itself when it needs them.

### 4.2 The rulebook files

**`rulebook_v0_rules.csv`**

| Column | Meaning |
|---|---|
| `rule_id` | unique key |
| `measure`, `direction` | what the rule matches (a State Engine measure key and `above`/`below`) |
| `context_match` | extra matching condition (grammar in 5.1); empty means none |
| `context_condition` | the same in words |
| `meera_handoffs_in_year` | documentation only; never used by the engine |
| `status` | `active` or `deferred` |
| `primary_count` | number of primary candidates in the rule (all of them are always tested) |
| `secondary_max`, `tertiary_max` | most secondary and tertiary candidates tested |
| `max_total` | most candidates tested in all |
| `budget_reason` | words only |
| `basis`, `review_status`, `rulebook_version` | provenance |

**`rulebook_v0_candidates.csv`**

| Column | Meaning |
|---|---|
| `rule_id`, `rank` | the rule and the position inside it (1 to n, contiguous) |
| `weight_tier` | `primary`, `secondary` or `tertiary` |
| `candidate` | name of the factor to test |
| `requires_streams` | generic stream tokens (grammar in 5.2) |
| `lookback_kind`, `lookback_value` | structured lookback (table in section 3) |
| `applies_if_rule` | structured applicability condition (grammar in 5.3); empty means always |
| `check_type` | one of `group_comparison`, `percentile_vs_history`, `shape_check`, `presence_check`, `pattern_repeat` (a label for Evidence Engine; Rulebook Lookup only passes it through) |
| `data_status_meera_code` | `available`, `partial`, `none`, `skipped_by_rule` or `unverified`. Documentation for the first patient only. **Never used to skip a candidate.** |
| `data_kinds_text`, `lookback_text`, `applies_if_text`, `check_text`, `outcome_compared_text`, `meera_data_status_text` | the same content in words, for people; `check_text` and `outcome_compared_text` are passed through to the packet |
| `evidence_level` | `A` to `D` (scale in `rulebook_v0.md`) |
| `sources` | source IDs (`S1` to `S20`, listed in `rulebook_v0.md`) |
| `note`, `review_status` | words; `unreviewed` |

### 4.3 Patient config (the `rulebook` block)

Everything patient-specific lives here. No stream name, medicine or patient flag appears in the engine.

```yaml
rulebook:
  rulebook_dir: rulebook_v0
  raised_bar_above: 4            # more selected candidates than this -> evidence_bar_hint = raised
  stream_map:                    # generic token -> this patient's stream name; null = not available
    meal_events: meal_events
    food_content: food_content
    medication_adherence: medication_adherence
    medication_list: medication_list      # from the patient's medication config
    sleep_duration: sleep_duration
    step_count: step_count
    step_count_hourly: null               # hourly steps are not in the store
    mood_state: mood_state
    diary_context: diary_context
    hydration: hydration
    screen_time: screen_time
    location: location
    cgm_glucose_reading: cgm_glucose_reading
    time_of_day: derived                  # always available; comes from timestamps
    menstrual_cycle: null                 # not confirmed to be in the store
    caffeine_intake: null
    lab_tsh: null
  medication_classes:            # medicine name -> classes
    metformin: [glucose_lowering]
    amlodipine: [antihypertensive]
    levothyroxine: [thyroid]
  patient_flags:                 # explicit flags that cannot be derived from medicines
    has_thyroid_condition: true
  derived_flags:                 # flags derived from medication classes
    takes_glucose_lowering_medication: glucose_lowering
    takes_bp_medication: antihypertensive
```

Streams are described by the same registry the Baseline Engine and State Engine use [verify the stream names against `context_events` and `raw_events`].

---

## 5. Grammars

### 5.1 `context_match` (rules file)

A condition on the hand-off. Currently two forms are used:

- `last_meal_minutes_ago<=180`: a last meal is logged and it is 180 minutes ago or less
- `last_meal_minutes_ago>180 or last_meal absent`: the opposite, including hand-offs with no logged meal

Empty means no extra condition. The number 180 is a rulebook value, not config.

### 5.2 `requires_streams` (candidates file)

- Tokens are separated by `;`. A token may carry a category filter: `diary_context[symptom]`, `diary_context[substance_use]`, `diary_context[environment]`.
- `a|b` means fallback in order: use `a` if available, otherwise `b` (for example `step_count_hourly|step_count`).
- **A candidate is runnable if at least one of its tokens is available** for the patient (a non-null `stream_map` entry, or `derived`). Tokens that are not available are listed as unavailable in the packet.
- Availability is decided from `stream_map` only. The engine does not look at data.
- The category filter does not affect availability. Whether a category occurs in the data is Evidence Engine's concern.

### 5.3 `applies_if_rule` (candidates file)

Terms separated by `;` are all required (AND). Inside a term, `|` means any of (OR). Term types:

| Term | True when |
|---|---|
| `patient_flag:<name>` | the flag is true in `patient_flags` or `derived_flags` |
| `medication_class_present:<class>` | any of the patient's medicines has that class in `medication_classes` |
| `stream_present:<token>` | `stream_map` has a non-null entry for the token |
| `open_time_between:HH:MM-HH:MM` | the local time of `opened_at` falls inside the range |

An unknown flag or class is false, never an error.

---

## 6. What happens for one hand-off (the rules)

**R1. Match a rule.** Take the rules whose `measure` and `direction` equal the hand-off's. Of those, keep the ones whose `context_match` is true. Exactly one rule must remain.
- None remains: the packet has `status: unmatched`, no candidates, and the case is counted and logged. This is not an error.
- More than one remains: a rulebook error. Log it, take the first in file order, and mark the packet `status: ambiguous`.

**R2. Deferred rules.** If the matched rule has `status: deferred`, the packet has `status: deferred`, the rule id, and no candidates. The hand-off is recorded and nothing is offered to test.

**R3. Applicability.** For each candidate in rank order, evaluate `applies_if_rule`. If false, the candidate goes to `skipped` with `reason: applies_if_not_met` and the failing term in `detail`.

**R4. Availability.** For each remaining candidate, evaluate `requires_streams` (5.2). If no token is available, the candidate goes to `skipped` with `reason: no_stream` and the unavailable tokens in `detail`.

**R5. Budget.** Among the remaining (runnable) candidates, in rank order:
- every `primary` candidate is selected;
- `secondary` candidates are selected until `secondary_max` is reached;
- `tertiary` candidates are selected until `tertiary_max` is reached;
- stop when `max_total` selected candidates are reached.

Runnable candidates that are not selected go to `not_selected` with `reason: budget`. **Skipped candidates do not use any budget.** The budget is static and comes from the rule.

**R6. Resolve lookbacks** for selected candidates (section 3).

**R7. Copy provenance.** Each selected candidate carries its `weight_tier`, `evidence_level`, `sources`, `data_status_meera_code`, `review_status` and `note` unchanged. Weights are never turned into numbers.

**R8. Evidence bar hint.** `evidence_bar_hint = "raised"` if the number of selected candidates is greater than `raised_bar_above`, otherwise `"standard"`. It is a hint. The bars themselves are defined in `rulebook_v0.md` and are placeholders.

**R9. Write.** Write the packet to the packet log. A hand-off that already has a packet produces the same packet again, with no duplicate row.

Every candidate of the matched rule appears exactly once, in one of `selected`, `skipped` or `not_selected`.

---

## 7. Outputs

### 7.1 The packet

One JSON object per hand-off. Every key is listed below. The example is real: it was produced by applying the rulebook to Meera's 2026-09-17 22:30 glucose hand-off (my own quick calculation with the config in 4.3, not an engine run).

```json
{
  "packet_id": "packet_handoff_glucose_2026-09-17T22:30",
  "handoff_id": "handoff_glucose_2026-09-17T22:30",
  "rulebook_version": "v0-draft-1",
  "rulebook_review_status": "unreviewed",
  "matched_rule": {"rule_id": "glucose_above_post_meal", "status": "active", "context_match": "last_meal_minutes_ago<=180", "budget": {"primary": "all", "primary_count": 1, "secondary_max": 5, "tertiary_max": 2, "max_total": 8}, "review_status": "unreviewed"},
  "handoff_summary": {"measure": "glucose", "direction": "above", "size": "clearly", "trigger": "persistence", "value": 185.0, "clinical_status": "high", "opened_at": "2026-09-17T22:30:00+05:30", "last_meal_minutes_ago": 62},
  "selected": [
    {
      "rank": 1,
      "weight_tier": "primary",
      "candidate": "meal_composition",
      "check_type": "percentile_vs_history",
      "check_text": "this meal's response vs her earlier meals of the same kind",
      "outcome_compared_text": "peak glucose within 150 min of the meal",
      "streams": [
        {"generic": "meal_events", "patient_stream": "meal_events", "category": null, "available": true},
        {"generic": "food_content", "patient_stream": "food_content", "category": null, "available": true}
      ],
      "lookback": {"kind": "minutes_before_open", "value": 240, "text": "240 minutes"},
      "resolved_window": {"start": "2026-09-17T18:30:00+05:30", "end": "2026-09-17T22:30:00+05:30", "includes_after_open": false},
      "evidence_level": "A",
      "sources": ["S1", "S2", "S3", "S4"],
      "data_status_code": "available",
      "review_status": "unreviewed",
      "note": "Food and carbohydrate load are the first-listed causes of highs."
    },
    {
      "rank": 2,
      "weight_tier": "secondary",
      "candidate": "medication_adherence",
      "check_type": "group_comparison",
      "check_text": "evenings after a missed dose vs evenings with all doses taken",
      "outcome_compared_text": "post-meal peak",
      "streams": [
        {"generic": "medication_adherence", "patient_stream": "medication_adherence", "category": null, "available": true}
      ],
      "lookback": {"kind": "days_ending_at_open", "value": 2, "text": "2 days"},
      "resolved_window": {"start": "2026-09-16T00:00:00+05:30", "end": "2026-09-17T22:30:00+05:30", "includes_after_open": false},
      "evidence_level": "A",
      "sources": ["S1", "S2", "S3", "S4"],
      "data_status_code": "available",
      "review_status": "unreviewed",
      "note": null
    },
    {
      "rank": 3,
      "weight_tier": "secondary",
      "candidate": "sleep",
      "check_type": "group_comparison",
      "check_text": "days after short sleep vs normal sleep",
      "outcome_compared_text": "post-meal peak",
      "streams": [
        {"generic": "sleep_duration", "patient_stream": "sleep_duration", "category": null, "available": true}
      ],
      "lookback": {"kind": "previous_night", "value": null, "text": "previous night"},
      "resolved_window": {"record": "latest_sleep_record_at_or_before_open", "includes_after_open": false},
      "evidence_level": "A",
      "sources": ["S2", "S3"],
      "data_status_code": "available",
      "review_status": "unreviewed",
      "note": "Poor or short sleep is listed as a cause of highs."
    },
    {
      "rank": 4,
      "weight_tier": "secondary",
      "candidate": "stress_mood",
      "check_type": "group_comparison",
      "check_text": "strained days vs calm days",
      "outcome_compared_text": "post-meal peak",
      "streams": [
        {"generic": "mood_state", "patient_stream": "mood_state", "category": null, "available": true},
        {"generic": "diary_context", "patient_stream": "diary_context", "category": null, "available": true}
      ],
      "lookback": {"kind": "days_ending_at_open", "value": 1, "text": "1 day"},
      "resolved_window": {"start": "2026-09-17T00:00:00+05:30", "end": "2026-09-17T22:30:00+05:30", "includes_after_open": false},
      "evidence_level": "A",
      "sources": ["S1", "S2", "S3"],
      "data_status_code": "available",
      "review_status": "unreviewed",
      "note": "Stress hormones raise glucose."
    },
    {
      "rank": 5,
      "weight_tier": "secondary",
      "candidate": "activity",
      "check_type": "group_comparison",
      "check_text": "low-activity days vs normal days",
      "outcome_compared_text": "post-meal peak",
      "streams": [
        {"generic": "step_count", "patient_stream": "step_count", "category": null, "available": true}
      ],
      "lookback": {"kind": "days_ending_at_open", "value": 1, "text": "1 day"},
      "resolved_window": {"start": "2026-09-17T00:00:00+05:30", "end": "2026-09-17T22:30:00+05:30", "includes_after_open": false},
      "evidence_level": "A",
      "sources": ["S1", "S2", "S3", "S4"],
      "data_status_code": "partial",
      "review_status": "unreviewed",
      "note": null
    },
    {
      "rank": 6,
      "weight_tier": "secondary",
      "candidate": "illness_symptoms",
      "check_type": "group_comparison",
      "check_text": "days with a symptom entry vs none",
      "outcome_compared_text": "post-meal peak",
      "streams": [
        {"generic": "diary_context[symptom]", "patient_stream": "diary_context", "category": "symptom", "available": true}
      ],
      "lookback": {"kind": "days_ending_at_open", "value": 3, "text": "3 days"},
      "resolved_window": {"start": "2026-09-15T00:00:00+05:30", "end": "2026-09-17T22:30:00+05:30", "includes_after_open": false},
      "evidence_level": "A",
      "sources": ["S1", "S3"],
      "data_status_code": "available",
      "review_status": "unreviewed",
      "note": "Illness or infection is a leading listed cause."
    },
    {
      "rank": 10,
      "weight_tier": "tertiary",
      "candidate": "alcohol",
      "check_type": "group_comparison",
      "check_text": "days with an alcohol entry vs none",
      "outcome_compared_text": "post-meal peak",
      "streams": [
        {"generic": "diary_context[substance_use]", "patient_stream": "diary_context", "category": "substance_use", "available": true}
      ],
      "lookback": {"kind": "days_ending_at_open", "value": 1, "text": "1 day"},
      "resolved_window": {"start": "2026-09-17T00:00:00+05:30", "end": "2026-09-17T22:30:00+05:30", "includes_after_open": false},
      "evidence_level": "C",
      "sources": [],
      "data_status_code": "partial",
      "review_status": "unreviewed",
      "note": "Effect direction on glucose is mixed."
    }
  ],
  "skipped": [
    {"candidate": "other_medications", "reason": "applies_if_not_met", "detail": "medication_class_present:glucose_raising"},
    {"candidate": "cycle_phase", "reason": "applies_if_not_met", "detail": "stream_present:menstrual_cycle"}
  ],
  "not_selected": [
    {"candidate": "meal_timing", "weight_tier": "secondary", "reason": "budget"}
  ],
  "counts": {"candidates_in_rule": 10, "selected": 7, "skipped": 2, "not_selected": 1},
  "evidence_bar_hint": "raised"
}
```

Notes on the example:
- The hand-off matched `glucose_above_post_meal` because the last meal was 62 minutes before the opening.
- `other_medications` was skipped because no medicine of the patient has the class `glucose_raising`. `cycle_phase` was skipped because `menstrual_cycle` is null in the config.
- `meal_timing` was runnable but cut by the budget (secondary maximum 5). `alcohol` was selected as the only tertiary candidate.
- Seven candidates were selected, which is more than 4, so `evidence_bar_hint` is `raised`.
- `sleep` resolves to a record, not a window. `minutes_around_open` does not occur in this packet; for such a candidate the window carries `"includes_after_open": true` and an `"earliest_evaluation_time"`.
- The packet contains no readings or results.

Packet keys:

| Key | Type | Meaning |
|---|---|---|
| `packet_id` | string | `packet_<handoff_id>` |
| `handoff_id` | string | the hand-off this packet answers |
| `status` | string, optional | `deferred`, `unmatched` or `ambiguous`. Absent for a normal packet. |
| `rulebook_version`, `rulebook_review_status` | string | provenance; `unreviewed` until a doctor reviews |
| `matched_rule` | object or null | `rule_id`, `status`, `context_match`, `budget` (`primary`, `primary_count`, `secondary_max`, `tertiary_max`, `max_total`), `review_status` |
| `handoff_summary` | object | `measure`, `direction`, `size`, `trigger`, `value`, `clinical_status`, `opened_at`, `last_meal_minutes_ago` |
| `selected` | array | candidate objects (below), in rank order |
| `skipped` | array | `candidate`, `reason` (`applies_if_not_met` or `no_stream`), `detail` |
| `not_selected` | array | `candidate`, `weight_tier`, `reason` (`budget`) |
| `counts` | object | `candidates_in_rule`, `selected`, `skipped`, `not_selected` |
| `evidence_bar_hint` | string | `standard` or `raised` |

Candidate object keys: `rank`, `weight_tier`, `candidate`, `check_type`, `check_text`, `outcome_compared_text`, `streams` (array of `generic`, `patient_stream`, `category`, `available`), `lookback` (`kind`, `value`, `text`), `resolved_window` (`start`, `end`, `includes_after_open`, and for around-open windows `earliest_evaluation_time`; or `record`, or `at`), `evidence_level`, `sources`, `data_status_code`, `review_status`, `note`.

### 7.2 The packet log

Each packet is stored once. Names are a suggestion.

| Key | Meaning |
|---|---|
| `packet_id` | key |
| `handoff_id` | the hand-off |
| `rule_id` | null when unmatched |
| `status` | `ok`, `deferred`, `unmatched` or `ambiguous` |
| `rulebook_version` | version used |
| `n_selected`, `n_skipped`, `n_not_selected` | quick-query columns |
| `packet_json` | the whole packet |

The log holds no timestamp of its own, so that a re-run produces identical rows.

---

## 8. Key dictionary

### 8.1 Input keys

- Hand-off: `handoff_id`, `item_id`, `measure`, `direction`, `size`, `trigger`, `position_z`, `usual_basis`, `value`, `clinical_status`, `opened_at`, `context.last_meal.minutes_ago`
- Rules file: all columns in 4.2
- Candidates file: all columns in 4.2
- Config: the `rulebook` block in 4.3

### 8.2 Working keys (exist during one lookup)

`matched_rules` (list), `runnable` (list), `skipped` (list), `selected_count_by_tier`, `resolved_window`, `evidence_bar_hint`.

### 8.3 Output keys

The packet (7.1) and the packet log (7.2).

---

## 9. The rulebook as it stands

### 9.1 The conditions

| Rule | Condition | Meera hand-offs in the year | Candidates | Budget: primary / secondary max / tertiary max / total |
|---|---|---|---|---|
| `glucose_above_post_meal` | a meal logged within 180 min | 40 | 10 | all (1) / 5 / 2 / 8 |
| `glucose_above_no_recent_meal` | no meal within 180 min | 59 | 9 | all (2) / 3 / 2 / 7 |
| `glucose_below` | adverse only | 5 | 6 | all (2) / 3 / 1 / 6 |
| `heart_rate_above` | continuous heart rate | 124 | 9 | all (3) / 3 / 2 / 8 |
| `resting_heart_rate_above` | daily resting heart rate | 12 | 7 | all (2) / 3 / 1 / 6 |
| `sleep_below` | last night below usual | 10 | 7 | all (1) / 3 / 2 / 6 |
| `medication_adherence_below` | missed doses worse than usual | 24 | 6 | all (2) / 3 / 1 / 6 |
| `blood_pressure_above` | systolic or diastolic above usual | 3 | 8 | all (2) / 3 / 2 / 7 |
| `hydration_below` | daily intake below usual | 2 | 5 | all (2) / 2 / 1 / 5 |
| `screen_time_above` | daily screen time above usual (**deferred**) | 8 | 2 | 0 / 2 / 0 / 2 |

The hand-off counts are Meera's 287 hand-offs (the State Engine's final run) and add up to 287.

### 9.2 Ordering rule

Inside the secondary and tertiary tiers, candidates are ordered by evidence level (A before B before C before D), so the budget cuts the weakest-evidenced candidates first. Primary candidates are all tested, so their order is only for reading.

### 9.3 Expected behaviour on the first patient

I applied the rulebook to the 287 real hand-offs with the config in 4.3, using a quick script of my own on the State Engine's hand-off export. This is a reference for your build to reproduce or to explain differences from, not an engine result.

| Rule | Hand-offs | Candidates selected per packet |
|---|---|---|
| `heart_rate_above` | 124 | 8 |
| `glucose_above_no_recent_meal` | 59 | 5 |
| `glucose_above_post_meal` | 40 | 7 |
| `medication_adherence_below` | 24 | 6 |
| `resting_heart_rate_above` | 12 | 6 |
| `sleep_below` | 10 | 6 |
| `screen_time_above` (deferred) | 8 | 0 |
| `glucose_below` | 5 | 5 |
| `blood_pressure_above` | 3 | 7 |
| `hydration_below` | 2 | 5 |

- All 287 hand-offs matched a rule. None was unmatched.
- **Skipped for every packet of their rule:** `cycle_phase` (no cycle stream), `other_medications` (no such medicine), `caffeine_stimulants` (no stream), `hypoglycemic_agent` (the patient takes no insulin or sulfonylurea). `dawn_effect` is skipped when the item opens outside 04:00 to 09:00 (43 of 59 packets) and `other_medications` for blood pressure is skipped (3 of 3).
- **Cut by the budget for every packet of their rule:** `meal_timing` (post-meal, 40), `prior_evening_meal` (no recent meal, 59), `unusual_activity_prior_day` (resting heart rate, 12) and `illness_symptoms` (sleep, 10). `dawn_effect` is cut in the 16 packets where it applies.
- So 14 of the 69 candidates are never selected for this patient: seven are always skipped by `applies_if` or by a missing stream, five are cut by the budget (`dawn_effect` is partly skipped and partly cut), and two belong to the deferred screen-time rule.

---

## 10. Properties that must hold

1. **Deterministic and stateless.** The same hand-off, rulebook and config always give the same packet.
2. **Read-only.** Nothing is written to the Personal Data Store, `memory_v2` or the State Engine's database. Only the packet log is written.
3. **No data in the packet.** No reading, value of a stream or result appears, apart from the copied hand-off summary.
4. **No LLM and no network call.**
5. **One packet per hand-off,** and re-running a hand-off gives the same packet without a duplicate row.
6. **Completeness.** Every candidate of the matched rule appears exactly once across `selected`, `skipped` and `not_selected`.
7. **Budget respected.** Selected counts never exceed `secondary_max`, `tertiary_max` or `max_total`. All runnable primary candidates are selected.
8. **Skipped candidates use no budget.**
9. **Ranks are preserved** and `selected` is in rank order.
10. **Weights are never numbers** and never appear as a confidence.
11. **No look-ahead** in resolved windows, except `minutes_around_open`, which carries `includes_after_open: true` and an `earliest_evaluation_time`.
12. **Provenance on every packet:** `rulebook_version` and review status. Nothing is presented as reviewed unless the rulebook says so.
13. **Unmatched and deferred hand-offs** produce a packet with an empty checklist and are counted. Neither is an error.
14. **Rulebook validation at load.** Loading fails, with a plain message, if: ranks are not contiguous per rule; tiers are not in the order primary, secondary, tertiary; secondary or tertiary candidates are not ordered by evidence level; `primary_count` differs from the actual number of primary candidates; a source ID is unknown; a grammar term cannot be parsed; a rule has no candidates (unless deferred); a `rule_id` is repeated; two rules could match the same hand-off; or the files carry different `rulebook_version` values.
15. **Generic.** No measure, stream, medicine, flag or patient name appears in the engine. A second patient with different streams and medicines runs with config changes only.

---

## 11. Limits, assumptions and open items

| Item | What I assumed | Where it matters |
|---|---|---|
| The rulebook is a draft | Built from published clinical-education sources in one search pass. Not read from guideline texts; not doctor-reviewed. | Everything downstream. The sources and weak spots are in `rulebook_v0.md`. |
| No source ranks the causes | The tier of each candidate is my judgment from how prominently sources list it. | Which candidates are always tested |
| Static budgets | One budget per rule, in the file | Some candidates are never reached for this patient (9.3). Raising a budget is a file change. |
| Missing hourly steps | Hourly steps are not in the store, so the activity candidate for heart rate has only daily steps | Heart rate above is the largest group (124) |
| Cycle stream | Not confirmed to be in the store, so `menstrual_cycle` is null in the config | `cycle_phase` candidates are skipped |
| `any-of` stream rule | A candidate runs if at least one listed stream exists | A candidate can run with a missing supporting stream; the packet shows which tokens are unavailable |
| Medicine names | `medication_classes` is keyed by the medicine names as the baseline config extracts them [verify] | Applicability terms |
| Screen time | Deferred: no clinical basis | 8 hand-offs get an empty checklist |
| Hand-offs of one moment | Each hand-off gets its own packet, even if several open together | Evidence Engine may share work across them later |
| `check_type` | A label only. How each check is computed is Evidence Engine's design. | Next component |

---

## 12. Glossary

| Term | Meaning |
|---|---|
| Hand-off | The record the State Engine writes once when a deviation item opens |
| Rule | One condition (measure, direction, optional context) with its checklist and budget |
| Candidate | One factor to test, inside a rule |
| Packet | The checklist for one hand-off: selected, skipped and not-selected candidates |
| Weight tier | `primary`, `secondary` or `tertiary`. A prior about what to test first, not evidence. |
| Budget | How many candidates are tested for a rule |
| Runnable | A candidate whose `applies_if` is true and which has at least one available stream |
| Evidence level | `A` to `D`: how well the sources support listing the factor |
| Resolved window | A lookback turned into absolute times for this hand-off |
