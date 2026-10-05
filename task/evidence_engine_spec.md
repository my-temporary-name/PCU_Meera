# Evidence Engine: Definition Spec

## 0. How to read this document

This document says **what the Evidence Engine is**: its purpose, inputs, rules, outputs and the keys that appear in them. It does not say how to build it. Module layout, function names, data structures and code style are yours to decide.

Where this document is silent, state your assumption in your report. Do not invent behaviour silently.

Values marked **default** live in config, not in code. Statistical thresholds are **placeholders**: they are starting guesses, not clinical standards, and are meant to be tuned later against a ground-truth scoring step that is not part of this task. Items marked **[verify]** come from earlier reports; check them against the real code and database and say where they differ.

**Revision 2.** This revision resolves the 28 points of the Step 1 report (summarised in Appendix B). Where an earlier statement and Appendix B differ, the main text of this revision wins.

**Revision 3.** This revision resolves the points of the Stage 2a report (Appendix C): the history minimum needs both 60 usable units and 60 distinct outcome dates (7.2); two cross-references and two counts are corrected (7.1, property 14, section 14); the section 12 remark about the sleep relationship now cites the engine's own run. Where an earlier statement and Appendix C differ, the main text wins. Housekeeping after Stage 2b: the event-time anchor of the ordering rule and of availability (3.1 rule 5), the intentional `no_data` for `no_ordered_exposure` (7.4), and the fields added to the 9.2 record (after the 9.2 example and in 11.3).

**This document is the only source.** There are no separate data files. The V0 library (the outcomes, the exposures and the rule-by-rule pair table) is defined by the tables in section 6 and in Appendix A. The build turns those tables into a config file in the repository (the format is yours). That file is **static**: nothing generates it at run time. It changes only when the rulebook changes or when someone edits it on purpose, and the engine **checks it against the rulebook files when it loads** (section 13, property 16), so a mismatch fails loudly instead of silently giving wrong results.

The Rulebook Lookup files (`rulebook_v0_*.csv`) are already in the repository and used by the built Rulebook Lookup; the Evidence Engine reads the packets that component produces and does not read those files directly, except in the load check.

This is one of three components (Evidence Engine, Findings Engine, PI) that are specified together in `intelligence_layer_overview.md`. This spec covers Evidence Engine only. Read the overview first.

---

## 1. What the Evidence Engine is

> **The Evidence Engine tests, with statistics on this person's own history, whether each factor in a rulebook packet shows up in her data. It returns numbers and a label for each factor. It never explains.**

For one hand-off it returns an **evidence record** with one entry per factor in the packet. It also keeps a daily set of **relationship evidence** so that the same relationship is computed once a day and reused by every hand-off that day.

### 1.1 What it is not

- It does not write wording and does not use an LLM.
- It makes no causal claim. A label says how well a link shows up in her history, not what caused anything.
- It does not decide beliefs or statuses ("candidate", "supported", and so on). That is PI's job. The labels here are **evidence labels** for one moment.
- It does not read PI, the baseline memories (`memory_v2`) or free-text diary entries. It uses diary **category and timestamp** only.
- It does not group hand-offs into cases. That is the Findings Engine's job. Evidence is computed per hand-off.
- It does not use the rulebook's weight tiers or evidence levels when deciding a label. They pass through unchanged.
- It does not search for new factors. It tests only what the packet lists.

---

## 2. Where it sits

```
State Engine hand-off  ->  Rulebook Lookup packet (rules only)
                                   |
                           EVIDENCE ENGINE   reads: the packet, the hand-off, the store, State Engine and baseline config
                                   |
                           evidence store    (relationship evidence, event evidence, run summaries)
                              |        |        |
                      Findings Engine  PI (code, by ID)  Narrative Layer
```

- **Statistics live here and nowhere else.** Every other component holds `evidence_id` references and fetches numbers from this store when it needs them.
- **Read-only toward everything else.** It writes nothing to the Personal Data Store, `memory_v2`, the State Engine's database or the Rulebook Lookup log. It writes only its own database.

---

## 3. Two jobs, two clocks

| Job | When | What it produces |
|---|---|---|
| **Daily refresh** | Once per local day, as-of the start of the day. It may run at 00:00 or lazily at the first request of the day; the result is identical. | **Relationship evidence**: for every runnable relationship, statistics over her completed earlier days |
| **Event evidence** | When a packet arrives (real time, no waiting for the end of the day) | An **event evidence record**: for each factor in the packet, the relationship's label for today, whether the event itself was exposed, and any event-specific statistic |

### 3.1 Time rules

1. **The outcome date.** Every event has an outcome date, given by its outcome in section 6.1. It is the local date of `opened_at`, except for end-of-day outcomes (`fluid_intake_day`), whose value arrives at the end of the day and whose item opens at 00:00 of the next day; their outcome date is the day before `opened_at`.
2. **History** means completed local days strictly before the outcome date. The outcome date itself is never in the history table. `as_of_date` in every record is the outcome date. A unit with a forward window (a meal's 150-minute window) enters the history only when its **whole window** ended before the as-of start; a dinner after 21:30 therefore enters one day later.
3. **Event-time data** is limited to what was available at the hand-off's `opened_at`, using the same `available_at` rules as the State Engine (single source: the State Engine config). One exception: the hourly steps are not a State Engine stream, so the library config carries their rule (rule 8). A record that is not available yet is **not yet available**, never "missing" and never "not exposed".
4. **Nothing waits for the day to end.** The relationship evidence for today is built from earlier days, so it exists from 00:00. The event part uses only what is already available.
5. **Anchoring.** Every exposure window is anchored to the **outcome date** (day outcomes) or to the **unit start** (meal, hour and reading outcomes), never to `opened_at`. The packet's `resolved_window` is not used. For the **event-time exposure state** the ordering rule (rule 6) is anchored at the **unit start** (the event meal's start for a meal outcome, the start of the clock hour for an hour outcome, `opened_at` for a reading outcome, the outcome date for a day outcome) and **availability** is anchored at `opened_at` (a record counts only if it is available by then). Each exposure state records its anchor in the field `anchor` (`meal_start`, `hour_start`, `opened_at` or `outcome_date`).
6. **The ordering rule.**
   - For **meal, hour and reading units**, an exposure value counts only if it was recorded at or before the unit's start. Timestamped values (sleep records, diary entries, meal starts, hourly steps) are compared with the unit's start. A mood block counts if the block had ended by the unit's start (block end = the State Engine's `available_at` for that block). A unit with no such value is dropped; a relationship with no unit that has any ordered exposure is `insufficient` with reason `no_ordered_exposure`.
   - For **day-level units** (which start at 00:00), nothing on the outcome's own date can be shown to come first. Every exposure inside the window, whether timestamped, in a block or date-only, **counts as date-resolution** and the relationship carries the flag `same_day_unverified`.
   - **Date-only values** (medicine records, location, hydration, screen time, daily steps) count when their date is inside the window; the flag applies when the window includes the outcome's own date.
7. **Exposure shift.** For `sleep_hours_night` the outcome is the night that ended on the morning of its date, so windows of `same_day`, `1d`, `2d` and `3d` are counted back from the **day before** that date (6.1, "Exposure shift"). For day-level outcomes, the exposure `sleep_hours@prev_night` is the sleep record dated the outcome date (the night that ended that morning), flagged `same_day_unverified`, because the day-level outcome starts at 00:00.
8. **Hourly steps.** A row is stamped at the hour start and holds the steps during that hour. It is available at the end of the hour (library config `available_at: end_of_hour`). The exposure for the hour starting at H is the row stamped H minus 1 hour.
9. **Replay and live use the same rules.** In replay, "now" is the hand-off's `opened_at`.

---

## 4. Inputs

### 4.1 From the Rulebook Lookup packet

Fields used (names as in the packet of `rulebook_lookup_spec.md`, section 7.1):

| Key | Used for |
|---|---|
| `packet_id`, `handoff_id`, `status` | identity; a packet with status `deferred`, `unmatched` or `ambiguous` yields an evidence record with no factors |
| `matched_rule.rule_id` | which outcome applies |
| `selected[].candidate`, `rank`, `weight_tier`, `check_type` | what to test and the order; tier and rank are copied through and never used for labels |
| `selected[].lookback` (`kind`, `value`) | the **window of the exposure** (the "when") |
| `skipped`, `not_selected` | copied into `not_tested` |

### 4.2 From the hand-off record (State Engine)

`handoff_id`, `measure`, `direction`, `opened_at`, `context.last_meal` (label, time), and, for medicines, the missed medicines. Nothing else.

### 4.3 From the Personal Data Store

Streams by their generic names through the stream registry [verify against `raw_events` and `context_events`]: cleaned glucose, continuous heart rate, hourly steps (`step_count_hourly`), daily steps, sleep, resting heart rate, medicine records, mood, meals, diary categories, location, hydration, screen time, blood pressure. Glucose readings are cleaned with **the Baseline Engine's cleaning rule** (device range and jump rule); questionable readings never enter any statistic.

If a pair needs a stream the patient does not have, the factor is `insufficient` with reason `no_stream`. The rulebook's fallback token `step_count_hourly|step_count` is **not** followed: a different stream is a different exposure.

**Stream tokens.** Each exposure and outcome in section 6 names a generic source token (for example `sleep_duration`, `meal_events`, `cgm_glucose_reading`, `step_count_hourly`, `diary_context`). The patient's evidence config holds a `stream_map` that maps tokens to the store's names, in the same shape as the Rulebook Lookup config. A token with no mapping gives `insufficient` with reason `no_stream`.

### 4.4 From other configs (read only)

| From | Used for |
|---|---|
| State Engine config | `available_at` per stream and per mood block, meal-kind matching, meal bucket minutes, timezone |
| Baseline config | `strain_mood_categories`, the glucose cleaning rule |
| Evidence config (patient block) | `stream_map`, `location.home_types`, `location.clinic_types`, `presence_flags`, `resting_heart_rate_pick` (section 10) |

---

## 5. Concepts

| Term | Meaning |
|---|---|
| **Relationship** | One exposure measured over one window, paired with one outcome, for one patient. Key format: `<exposure_id>@<lookback_tag>-><outcome_id>[:<scope>]`, for example `sleep_hours@prev_night->post_meal_peak:dinner`. |
| **Exposure** | The factor (the "what"). The window (the "when") comes from the pair's lookback in the rulebook. |
| **Outcome** | The measured result, one value per unit. One per rulebook rule (the heart-rate rule uses an hourly outcome for hourly exposures). |
| **Unit** | The row of the history table: `meal`, `day`, `hour` or `reading`. |
| **Orientation** | Every outcome is turned so that **higher means worse**, and every exposure so that **higher means riskier** (using the exposure's risk side). All tests are one-sided for a **positive** association after this. A negative association is reported, and flagged `contrary` if strong. |
| **History table** | For one relationship and one outcome date: one row per unit before that date, with oriented exposure and oriented outcome. |
| **Event-level check** | A check about this event only (percentile, shape, pattern, presence). It has no relationship record. |

Lookback tags: `minutes_before_open N` is `Nm`, `days_ending_at_open N` is `Nd`, `previous_night` is `prev_night`, `previous_calendar_day` is `prev_day`, `previous_evening` is `prev_evening`, `same_calendar_day` is `same_day`, `at_open` is `at_open`, `minutes_around_open N` is `pmNm`. For `post_meal_peak` the scope is the meal kind (from the State Engine's meal-kind matching), so `post_meal_peak:dinner` and `post_meal_peak:lunch` are separate relationships.

---

## 6. The V0 library

### 6.1 Outcomes

| Outcome | Unit | Unit start | Definition | Worse is | Outcome date | Exposure shift | Used by |
|---|---|---|---|---|---|---|---|
| post_meal_peak | meal | the meal's start | Highest cleaned glucose within 150 minutes after a logged meal. Scope: the meal kind of the event meal (from the State Engine's meal-kind matching). | higher | date of the meal | 0 | glucose_above_post_meal |
| non_meal_mean | day | 00:00 | Mean of the day's cleaned glucose readings taken more than 180 minutes after any logged meal | higher | date of opened_at | 0 | glucose_above_no_recent_meal |
| day_min_glucose | day | 00:00 | Lowest cleaned glucose of the day | lower | date of opened_at | 0 | glucose_below |
| hr_hour_mean | hour | the hour's start | Mean continuous heart rate in the clock hour | higher | date of opened_at | 0 | heart_rate_above (hourly exposure) |
| hr_day_mean | day | 00:00 | Mean continuous heart rate over the day's readings | higher | date of opened_at | 0 | heart_rate_above (other exposures) |
| resting_hr_day | day | 00:00 | The day's resting heart rate value | higher | date of opened_at | 0 | resting_heart_rate_above |
| sleep_hours_night | day | 00:00 | Duration of the sleep record dated that day (the night that ended that morning) | lower | date of opened_at | -1 day: the night belongs to the day before, so windows of same_day, 1d, 2d, 3d are counted back from the day before | sleep_below |
| missed_doses_day | day | 00:00 | Number of doses logged as missed on the day | higher | date of opened_at | 0 | medication_adherence_below |
| systolic_reading | reading | the reading's time | Systolic value of each blood pressure reading (diastolic is not used in V0) | higher | date of opened_at | 0 | blood_pressure_above |
| fluid_intake_day | day | 00:00 | The day's logged fluid intake in mL | lower | date of opened_at minus 1 day: the daily value arrives at the end of the day, so the item opens at 00:00 of the next day | 0 | hydration_below |

Blood pressure uses systolic only in V0. Glucose is always cleaned first.

### 6.2 Exposures

| Exposure | Form | Risk side | Time resolution | Definition | Event-time state |
|---|---|---|---|---|---|
| missed_dose | binary | exposed = 1 | date | At least one dose logged as missed inside the window | exposed if a missed dose is available at the event time; not_exposed if the records are available and none was missed; not_yet_available if the day's record is not available yet |
| sleep_hours | continuous | low | timestamp | Duration of the sleep record for the window (the night ending on the morning of the date; the record is stamped at its wake time) | position of the value in her history; exposed if inside the worse tail |
| strained_period | binary | exposed = 1 | block | At least one mood block in the window whose category is in the strain list (the same list the baseline uses). A block counts for an outcome unit only if the block has ended by the unit's start; the block end is the State Engine's `available_at` for that block. | exposed if an available block in the window is a strain category; blocks not yet available are ignored and the state says so |
| steps_total | continuous | low | date | Daily step total for the window (daily stream) | as sleep_hours; not_yet_available while the day's total is not available (end of day) |
| steps_window_hourly | continuous | high | timestamp | Steps in the hour(s) just before the outcome hour, from the hourly stream (`step_count_hourly`). No fallback to daily steps. | as sleep_hours (worse tail = high) |
| high_steps_day | binary | exposed = 1 | date | Daily total at or above her 75th percentile of earlier days (as-of) | exposed if the available total is at or above that percentile; otherwise as steps_total |
| symptom_entry | binary | exposed = 1 | timestamp | At least one diary entry with category symptom inside the window (category and timestamp only; text is not read). Entries after the outcome unit's start do not count. | exposed if such an entry is available in the window; not_exposed if the diary is available and has none |
| alcohol_entry | binary | exposed = 1 | timestamp | At least one diary entry with category substance_use inside the window (same ordering rule) | as symptom_entry |
| environment_entry | binary | exposed = 1 | timestamp | At least one diary entry with category environment inside the window (same ordering rule) | as symptom_entry |
| hydration_total | continuous | low | date | Logged fluid intake for the window's day | as sleep_hours |
| screen_hours | continuous | high | date | Logged screen time for the window's day | as sleep_hours (worse tail = high) |
| late_meal | binary | exposed = 1 | timestamp | The meal started at or after the 75th percentile of start times of her earlier meals of the same kind (as-of) | exposed if the event meal is that late |
| late_prior_dinner | binary | exposed = 1 | timestamp | The previous evening's dinner started at or after the 75th percentile of her earlier dinner start times | as late_meal, for the previous evening |
| non_home_day | binary | exposed = 1 | date | The day's location type is not in the patient's home location types (config) | exposed if the location is available and not home |
| prior_day_glucose_mean | continuous | high | timestamp | Mean cleaned glucose of the previous day | as sleep_hours (worse tail = high) |
| clinic_reading | binary | exposed = 1 | date | The location type on the reading's date is in the patient's clinic location types (config) | exposed if the location is available and is a clinic type |

### 6.3 Pairs

Appendix A lists one row per rulebook candidate (69 rows). Its columns: `Rule`, `#` (rank), `Tier`, `Candidate`, `Check type`, `Exposure`, `Outcome`, `Relationship key`, `V0 status`, `Ordering`.

| V0 status | Meaning | Rows |
|---|---|---|
| `runnable` | A relationship with a history table and statistics | 49 (49 distinct keys; post-meal keys expand per meal kind) |
| `event_level` | A check about this event only | 11 |
| `no_definition` | No exposure is defined in V0. The factor is reported as `insufficient` with reason `no_definition`. | 7 |
| `rule_deferred` | The rule is deferred (screen time). Nothing is tested. | 2 |

`no_definition` rows: `glucose_above_post_meal` / cycle_phase; `glucose_above_no_recent_meal` / cycle_phase; `heart_rate_above` / caffeine_stimulants; `heart_rate_above` / meal_digestive; `resting_heart_rate_above` / unusual_activity_prior_day; `sleep_below` / overnight_glucose; `blood_pressure_above` / salt_in_meals. Reasons: no stream (cycle, caffeine), no meaningful definition yet (salt, digestive effect, prior-day activity extremes) or the exposure shares the night with the outcome (overnight glucose).

`event_level` rows: `glucose_above_post_meal` / meal_composition (percentile_vs_history); `glucose_above_post_meal` / other_medications (presence_check); `glucose_above_no_recent_meal` / dawn_effect (pattern_repeat); `glucose_above_no_recent_meal` / other_medications (presence_check); `glucose_below` / sensor_artifact (shape_check); `glucose_below` / meal_skipped_or_delayed (percentile_vs_history); `glucose_below` / hypoglycemic_agent (presence_check); `heart_rate_above` / thyroid_status (presence_check); `resting_heart_rate_above` / thyroid_status (presence_check); `medication_adherence_below` / regimen_factors (pattern_repeat); `blood_pressure_above` / other_medications (presence_check).

`Ordering` values: `ordered` (the exposure can be shown to come before the outcome unit; 25 runnable pairs), `same_day_unverified` (a day-level outcome, or a date-only exposure inside the outcome's own date; see 3.1 rule 6; 22 pairs), `excludes_outcome_day` (the window stops the day before the outcome day; 1 pair) and `no_ordered_exposure` (no exposure can come before the outcome unit: `strained_period@same_day->systolic_reading`, because blood pressure is read at about 08:00 and no mood block has ended by then; the relationship is `insufficient` with reason `no_ordered_exposure`; 1 pair).

---

## 7. The statistics (V0)

### 7.1 The history table

- One row per unit before the outcome date, in time order. For `meal` units only meals of the event's kind count.
- An exposure value counts only if it passes the ordering rule (3.1 rule 6). A unit whose exposure cannot be evaluated (for example no mood block has ended before a breakfast) is dropped.
- **Detrending (default on).** The outcome is replaced by its difference from a baseline built only from earlier values, at least 10 required; rows without enough are dropped. The baseline is: for **day** units, the median of the previous 30 days; for **meal** units, the median of her earlier meals **of the same kind** in the previous 30 days; for **hour** units, the median of **the same clock hour** over the previous 30 days (so the daily cycle does not correlate with every hourly exposure by itself); for **reading** units, the median of the readings in the previous 30 days. Reason: slow trends such as her improvement through the year make exposures and outcomes move together by themselves. On the first patient this roughly halved the effect sizes (section 12).
- Missing values drop the row. `n_exposed` and `n_reference` count the rows used.
- A **meal with no meal kind** (the State Engine's label matching finds none; 8 meals in the first patient's year) has no relationship: every relationship factor in that packet is `insufficient` with reason `no_meal_kind`. Its event-level percentile still runs against all meals.
- Where the resting heart rate has two values on a day, the **last** one is used (config `resting_heart_rate_pick`).

### 7.2 Group comparison (`check_type = group_comparison`)

| Exposure form | Statistic |
|---|---|
| binary | **Effect** = standardized mean difference of the oriented outcome (exposed minus reference, pooled standard deviation). Also report the raw difference in the outcome's unit. |
| continuous | **Effect** = Spearman rank correlation between oriented exposure and oriented outcome. |

**Significance: circular-shift permutation.** The exposure series is rotated by a random offset (at least 5% of the series length) 2,000 times; the one-sided p-value is the share of rotations whose effect is at least as large as the real one (with the usual +1 correction, so the smallest possible p is 1/2001). Rotation keeps the exposure's autocorrelation, which her series have (about 0.45 to 0.50 day to day). The random seed is derived from the relationship key, the as-of date and the method version, so results repeat exactly.

**Contrary.** The same permutation gives `p_contrary`, the one-sided p-value for the opposite direction. If the effect is negative and `p_contrary` is at most 0.10, the relationship gets the flag `contrary`.

**Multiple testing.** Benjamini-Hochberg at q = 0.10 across the **family**: all relationships refreshed that day that passed the minimums (those with a p-value; `family_size` is recorded). The packet does not change a label; the family does.

**Minimums.** `insufficient` if `n_exposed` is below 15, or `n_reference` is below 30 (binary), or the history has fewer than 60 usable units, or fewer than `min_history_days` (60) distinct outcome dates (the history minimum is met only if both are; hourly units, for example, reach 60 usable units within a week but need 60 days). The flag `small_group` is set on an `insufficient` label caused by a group below its minimum, and on no other label. A binary exposure with no spread in the outcome, or a continuous exposure with no spread, is `insufficient` with reason `no_variation`.

**Labels** (placeholders):

| Label | Rule |
|---|---|
| `supported` | not insufficient; adjusted p at most 0.10; effect at least the floor in the expected direction |
| `suggestive` | not insufficient; unadjusted p at most 0.10 and effect at least the floor, but the adjusted p is above 0.10 |
| `not_supported` | enough data, but neither rule holds |
| `insufficient` | a minimum is not met; no p-value is shown as evidence |

Effect floors: 0.10 for both forms (placeholders; small on purpose, because detrended effects on the first patient are small).

**Placebo.** For every tested relationship, one placebo run repeats the test with the exposure rotated by exactly 30% of the series length (config). The placebo's p-value is read from the same null distribution as the real test. If the placebo's unadjusted p is at most 0.10 and its effect is at least the floor (the `suggestive` rule), the flag `placebo_fired` is set, and the relationship cannot be labelled `supported`. Placebos are not part of the family. The daily run also records the share of placebos that fired, which estimates the false-positive rate.

**Overlap.** Among factors labelled `supported` or `suggestive` in the packet, report one entry per unordered pair, using the direction with the larger `share_given_a`. "Days" are the outcome dates in the history; a date counts as exposed if any of its units is. Overlap uses the exposure and its window only, not the outcome. Binary exposures are used as they are; continuous ones are turned into their worse quartile. For a pair (a, b): `share_given_a` is the share of a-days that are also b-days, `share_overall` is b's share over all days, `ratio` is their quotient. Flag the pair `entangled` if `share_given_a` is at least 0.25 and `ratio` is at least 2.0 (placeholders).

**Numerics.** numpy is allowed and must be declared as a dependency; the shifted effects are computed together. Random seeds come from a stable hash (SHA-256 of key, date and method version), not Python's salted `hash`. Comparisons "at least as large as the real one" use a small tolerance so float noise cannot change a p-value.

### 7.3 Event-level checks

**`percentile_vs_history`** (`meal_composition`, `meal_skipped_or_delayed`). Compare this event's value with her history **like for like**:
- `meal_composition`: the highest glucose so far after the event meal, over the minutes elapsed at `opened_at` (rounded to the meal bucket), against the same elapsed-minutes peak after her earlier meals of the same kind. Report `elapsed_minutes`, `bucket_minutes` (the elapsed time rounded to the meal bucket), `bucket_size` (15), `observed`, `history_n`, `history_median`, `history_p90` and `percentile`. Label `supported` if the percentile on the worse side is at least 90 and `history_n` is at least 30; `insufficient` if `history_n` is below 30; otherwise `not_supported`.
- `meal_skipped_or_delayed`: hours since the last meal at `opened_at` against her history of hours since the last meal **at the same clock hour** (nearest 15-minute bucket); same rule. A comparison with plain meal-to-meal gaps is not like for like and would mark every overnight event as supported.

**`shape_check`** (`sensor_artifact`). Features of the cleaned glucose around the event: a steep drop from steady values, an isolated reading that differs from both neighbours, a rebound on the next reading, and the overnight window. Report the features and label `supported` ("consistent with an artifact") if the reading is isolated and rebounds; thresholds in config (placeholders). The check needs readings after the event (`pmNm` window). The event record is written at `opened_at` with the label `not_yet_available` and an `earliest_evaluation_time`; a **completion** (section 9.3, table `event_completions`) fills the label once the readings exist. In a replay the driver calls it right after. The event record itself is never changed.

**`pattern_repeat`** (`dawn_effect`, `regimen_factors`). Descriptive frequencies over earlier days: for `dawn_effect`, the share of earlier mornings with a glucose rise (the highest reading in the window minus the lowest reading before it) between 04:00 and 09:00; for `regimen_factors`, the miss rate per medicine. Label `supported` for `dawn_effect` if the share is at least 0.5 over at least 14 days; `regimen_factors` is `not_applicable` and returns the rates.

**`presence_check`** (`other_medications`, `thyroid_status`, `hypoglycemic_agent`). A fact from config: present if any of its flags is true, otherwise absent. Label `not_applicable`; the result carries `present`. The flag values are copied into the evidence config once, and the load check compares them with the Rulebook Lookup config.

### 7.4 Event exposure state

For each factor, at `opened_at`:

| State | Meaning |
|---|---|
| `exposed` | The factor is present (binary) or the value is in the worse tail of her history (continuous, worst quartile) |
| `not_exposed` | The relevant records are available and the factor is absent |
| `not_yet_available` | The relevant record is not available at `opened_at` (for example a daily total that arrives at the end of the day) |
| `no_data` | The stream does not exist for the patient or has no value |

A continuous value also reports its percentile in her history (`tail_percentile`, 0 to 100). Every state carries `anchor` (3.1 rule 5); `not_yet_available` also carries `available_at`, the availability rule of the record that is still missing (for example `end_of_day`, `21:00`, `block_end`, `timestamp`).

**`no_data` with the reason `no_ordered_exposure` is intentional.** When no record can have come before the unit's start (for example no mood block has ended before a breakfast or before a morning blood pressure reading), the relationship is `insufficient` with reason `no_ordered_exposure` and the event's exposure state is `no_data`, not `not_yet_available`: waiting would not change it, because the records that will arrive later also come after the unit's start.

**Partly available windows.** The state is `exposed` if any available record in the window shows the factor. It is `not_yet_available` if none shows it and some record in the window is not available yet (for example today's medicine record at 20:00, while yesterday's is available). It is `not_exposed` only if every record in the window is available and none shows the factor. The same rule applies to mood blocks.

**Event-level checks.** For `percentile_vs_history` the state is `exposed` if the value is in the worse tail (percentile at least 75, config `event_exposure.tail_quantile`), otherwise `not_exposed`. The other event-level checks have no event exposure (`null`).

---

## 8. What happens (the rules)

### Daily refresh (for an outcome date D)

**D1.** List the runnable relationships from Appendix A, expanding `{meal_kind}` for every meal kind that occurs in her history.
**D2.** For each, build the history table from days before D (7.1) and compute the statistic, the permutation p-values, the placebo and the minimum checks.
**D3.** Apply Benjamini-Hochberg across the whole family and assign each relationship its label and flags.
**D4.** Write one `relationship_evidence` record per relationship (9.1). If a current record already exists for the same key, date, method version and inputs hash, do nothing. If the inputs hash differs, mark the old record `superseded` and write the new one.
**D5.** Write the run summary.

### Event evidence (one packet)

**E1.** If the packet status is `deferred` or `unmatched`, write an event record with `factors: []` and copy the packet's `skipped` and `not_selected` into `not_tested` (the reason is copied, for example `rule_deferred`), so completeness holds, and stop. A packet with status `ambiguous` has candidates and is treated as normal.
**E2.** Work out the outcome date (3.1 rule 1). Make sure the relationship evidence for that date exists (run D1 to D5 lazily if not).
**E3.** For each selected candidate in rank order, look up its row in Appendix A. By `V0 status`:
- `runnable`: fetch the relationship record for the outcome date; take its `support` and `flags`; evaluate the **event exposure state** (7.4) from data available at `opened_at`.
- `event_level`: run the event-level check (7.3) and set its label.
- `no_definition`: label `insufficient`, reason `no_definition`.
- `rule_deferred`: not reached through a packet (E1 handles deferred packets); the rows are used by the load check only.
**E4.** Compute the overlap among `supported` and `suggestive` factors.
**E5.** Copy the packet's `skipped` and `not_selected` into `not_tested`: `not_selected` with reason `budget` becomes `not_selected_budget`; every `skipped` entry becomes `skipped_by_packet`, keeping the packet's own `reason` and `detail` (`packet_reason`, `packet_detail`); `rule_deferred` stays.
**E6.** Write the event record. Writing the same packet again produces the same record. Labels that need later data (the shape check) are written as `not_yet_available` and filled by a completion (9.3).

---

## 9. Outputs

### 9.1 Relationship evidence (one per relationship per outcome date)

Example: the sleep relationship, as-of 2026-09-17. Numbers are from my own prototype run on Meera's data, not from the engine. The adjustment family of 5 is for illustration only: the real family is every relationship refreshed that day (about 50 or more).

```json
{
  "evidence_id": "rel|sleep_hours@prev_night->post_meal_peak:dinner|2026-09-17|ev-v0",
  "relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner",
  "exposure_id": "sleep_hours",
  "outcome_id": "post_meal_peak",
  "outcome_scope": {
    "meal_kind": "dinner"
  },
  "unit": "meal",
  "form": "continuous",
  "check_type": "group_comparison",
  "as_of_date": "2026-09-17",
  "history": {
    "first_day": "2025-10-01",
    "last_day": "2026-09-16",
    "n_units": 335,
    "n_dropped_by_detrend": 10
  },
  "orientation": {
    "outcome_worse_is": "higher",
    "exposure_risk_side": "low"
  },
  "detrend": {
    "method": "trailing_median",
    "window_days": 30,
    "min_prior_values": 10
  },
  "n_exposed": 335,
  "n_reference": null,
  "effect_kind": "spearman_rho",
  "effect": 0.12,
  "raw_difference": null,
  "permutation": {
    "method": "circular_shift",
    "n": 2000,
    "p": 0.033,
    "p_contrary": 0.9675
  },
  "adjustment": {
    "method": "benjamini_hochberg",
    "family_size": 5,
    "p_adjusted": 0.086,
    "note": "family of 5 is for illustration only"
  },
  "support": "supported",
  "flags": [],
  "placebo": {
    "effect": -0.03,
    "p": 0.6507,
    "fired": false
  },
  "method_version": "ev-v0",
  "config_version": "<hash of the evidence config>",
  "inputs_hash": "<hash of the history rows used>",
  "status": "current"
}
```

### 9.2 Event evidence (one per hand-off)

The same example, for Meera's 2026-09-17 22:30 glucose hand-off. It holds **no statistics**: each factor points to its relationship record by `relationship_evidence_id`. Only the event-specific statistic (the meal percentile) is stored here.

```json
{
  "evidence_id": "ev_handoff_glucose_2026-09-17T22:30",
  "packet_id": "packet_handoff_glucose_2026-09-17T22:30",
  "handoff_id": "handoff_glucose_2026-09-17T22:30",
  "rule_id": "glucose_above_post_meal",
  "event_time": "2026-09-17T22:30:00+05:30",
  "as_of_date": "2026-09-17",
  "method_version": "ev-v0",
  "config_version": "<hash of the evidence config>",
  "factors": [
    {"rank": 1, "weight_tier": "primary", "candidate": "meal_composition", "check_type": "percentile_vs_history", "relationship_evidence_id": null, "support": "supported", "flags": [], "event_exposure": {"state": "exposed"}, "event_specific": {"elapsed_minutes": 62, "bucket_minutes": 60, "bucket_size": 15, "observed": 185.0, "history_n": 346, "history_median": 150.1, "history_p90": 167.4, "percentile": 99}},
    {"rank": 2, "weight_tier": "secondary", "candidate": "medication_adherence", "check_type": "group_comparison", "relationship_evidence_id": "rel|missed_dose@2d->post_meal_peak:dinner|2026-09-17|ev-v0", "support": "supported", "flags": ["same_day_unverified"], "event_exposure": {"state": "exposed"}},
    {"rank": 3, "weight_tier": "secondary", "candidate": "sleep", "check_type": "group_comparison", "relationship_evidence_id": "rel|sleep_hours@prev_night->post_meal_peak:dinner|2026-09-17|ev-v0", "support": "supported", "flags": [], "event_exposure": {"state": "exposed", "tail_percentile": 0.6}},
    {"rank": 4, "weight_tier": "secondary", "candidate": "stress_mood", "check_type": "group_comparison", "relationship_evidence_id": "rel|strained_period@1d->post_meal_peak:dinner|2026-09-17|ev-v0", "support": "not_supported", "flags": [], "event_exposure": {"state": "exposed"}},
    {"rank": 5, "weight_tier": "secondary", "candidate": "activity", "check_type": "group_comparison", "relationship_evidence_id": "rel|steps_total@1d->post_meal_peak:dinner|2026-09-17|ev-v0", "support": "not_supported", "flags": ["same_day_unverified"], "event_exposure": {"state": "not_yet_available", "available_at": "end_of_day"}},
    {"rank": 6, "weight_tier": "secondary", "candidate": "illness_symptoms", "check_type": "group_comparison", "relationship_evidence_id": "rel|symptom_entry@3d->post_meal_peak:dinner|2026-09-17|ev-v0", "support": "not_supported", "flags": ["contrary", "placebo_fired"], "event_exposure": {"state": "not_exposed"}},
    {"rank": 10, "weight_tier": "tertiary", "candidate": "alcohol", "check_type": "group_comparison", "relationship_evidence_id": "rel|alcohol_entry@1d->post_meal_peak:dinner|2026-09-17|ev-v0", "support": "insufficient", "flags": [], "event_exposure": {"state": "not_exposed"}}
  ],
  "overlap": [
    {"a": "sleep_hours@prev_night", "b": "missed_dose@2d", "a_view": "worst_quartile", "share_given_a": 0.82, "share_overall": 0.72, "ratio": 1.14, "flag": false}
  ],
  "not_tested": [
    {"candidate": "meal_timing", "reason": "not_selected_budget"},
    {"candidate": "other_medications", "reason": "skipped_by_packet", "packet_reason": "applies_if_not_met", "packet_detail": "medication_class_present:glucose_raising"},
    {"candidate": "cycle_phase", "reason": "skipped_by_packet", "packet_reason": "applies_if_not_met", "packet_detail": "stream_present:menstrual_cycle"}
  ],
  "counts": {"factors": 7, "supported": 3, "suggestive": 0, "not_supported": 3, "insufficient": 1, "not_tested": 3}
}
```

Fields added to the 9.2 record by the build (they are part of the format):

- `factors[].event_exposure.anchor`: where the ordering rule was anchored (`meal_start`, `hour_start`, `opened_at` or `outcome_date`; 3.1 rule 5). Absent for event-level checks, whose exposure is `null` or the percentile state.
- `factors[].reason`: present when the factor's `support` is `insufficient` (or `not_applicable` for a rule that is deferred): `no_stream`, `history`, `small_group`, `no_variation`, `no_ordered_exposure`, `no_definition`, `no_meal_kind`, `no_meal`, `no_readings`, `no_relationship`, `not_in_library`.
- `overlap[].b_view`: how the second factor was viewed (`binary` or `worst_quartile`), next to `a_view`.
- `counts`: besides `factors`, `supported`, `suggestive`, `not_supported`, `insufficient` and `not_tested`, also `not_applicable` and `not_yet_available`.

### 9.3 Storage

Its own database (suggested name `output/evidence_engine.db`), like the State Engine and Rulebook Lookup. Names are suggestions.

| Table | Key | Holds |
|---|---|---|
| `relationship_evidence` | `evidence_id` (the word `rel`, the key, the as-of date and the method version, joined by vertical bars) | the record in 9.1; columns for `relationship_key`, `as_of_date`, `method_version`, `config_version`, `inputs_hash`, `status` (`current` or `superseded`), `record_json` |
| `event_evidence` | `evidence_id` (`ev_<handoff_id>`) | the record in 9.2; columns for `packet_id`, `handoff_id`, `rule_id`, `event_time`, `as_of_date`, `record_json` |
| `event_completions` | `evidence_id` | the late label of an event-level check that needs later data (the shape check): `evidence_id`, `candidate`, `support`, `result_json`, `evaluated_from` (the data window used). One row per factor; never changes the event record. |
| `evidence_runs` | `as_of_date` + `method_version` | counts per label, number tested, `placebo_tested`, `placebo_fired`, `summary_json` |

No table holds a wall-clock timestamp, so that a re-run produces identical rows. **Reuse rule:** a relationship record is reused for the same key, date, method version and inputs hash. The history table's rows are hashed into `inputs_hash`, so a change in the underlying data produces a new record and supersedes the old one.

---

## 10. Config (all values are defaults)

```yaml
evidence:
  method_version: ev-v0
  history:
    min_history_days: 60
    detrend: {method: trailing_median, window_days: 30, min_prior_values: 10}
  min_exposed: 15
  min_reference: 30
  permutation: {n: 2000, min_shift_fraction: 0.05}   # seed = hash(relationship_key, as_of_date, method_version)
  multiplicity: {method: benjamini_hochberg, q: 0.10, family: all_relationships_refreshed_on_the_day}
  labels:
    p_suggestive: 0.10
    effect_floor_binary: 0.10
    effect_floor_continuous: 0.10
    contrary_p: 0.10
  placebo: {shift_fraction: 0.30}
  overlap: {tail_quantile: 0.25, min_share_given_a: 0.25, min_ratio: 2.0, among: [supported, suggestive]}
  event_exposure: {tail_quantile: 0.25}
  percentile_check: {history_min: 30, supported_min_percentile: 90}
  shape_check: {isolated_min_step: 30, rebound_tolerance: 20, steep_drop_min: 30}   # mg/dL, placeholders
  pattern_repeat: {dawn_window: "04:00-09:00", dawn_min_rise: 20, min_share: 0.5, min_days: 14}
  location: {home_types: [home, home_wfh, family_home], clinic_types: [clinic, hospital]}
  presence_flags:                       # facts for presence_check, filled from the patient config
    other_medications: {glucose_raising: false, bp_raising: false}
    thyroid_status: {thyroid_medication: true}
    hypoglycemic_agent: {insulin: false, sulfonylurea: false}
  resting_heart_rate_pick: last           # first | last, when a day has two values
  hourly_steps: {available_at: end_of_hour, exposure_row: previous_hour}
  stream_map:                             # generic token -> this patient's store name; null = not available
    sleep_duration: sleep_duration
    cgm_glucose_reading: cgm_glucose_reading
    step_count_hourly: step_count_hourly
    # ... one entry per token used in sections 6.1 and 6.2
  dependencies: [numpy]                  # declared in the project, not installed implicitly
  library: derived from sections 6.1, 6.2 and Appendix A; static; checked against the rulebook at load
```

---

## 11. Key dictionary

### 11.1 Input keys
- Packet: `packet_id`, `handoff_id`, `status`, `matched_rule.rule_id`, `selected[].candidate`, `rank`, `weight_tier`, `check_type`, `lookback`, `skipped`, `not_selected`
- Hand-off: `handoff_id`, `measure`, `direction`, `opened_at`, `context.last_meal`
- Library: the tables in 6.1, 6.2 and Appendix A
- Store: the streams in 4.3; config: the `evidence:` block above and the State Engine and baseline keys in 4.4

### 11.2 Working keys
`history_table`, `oriented_exposure`, `oriented_outcome`, `detrended_outcome`, `null_distribution`, `family`, `outcome_date`, `elapsed_minutes`, `event_exposure.state`.

### 11.3 Output keys
Relationship record (9.1): `evidence_id`, `relationship_key`, `exposure_id`, `outcome_id`, `outcome_scope`, `unit`, `form`, `check_type`, `as_of_date`, `history`, `orientation`, `detrend`, `n_exposed`, `n_reference`, `effect_kind`, `effect`, `raw_difference`, `permutation`, `adjustment`, `support`, `flags`, `placebo`, `method_version`, `config_version`, `inputs_hash`, `status`.
Event record (9.2): `evidence_id`, `packet_id`, `handoff_id`, `rule_id`, `event_time`, `as_of_date`, `method_version`, `config_version`, `factors` (`rank`, `weight_tier`, `candidate`, `check_type`, `relationship_evidence_id`, `support`, `flags`, `reason`, `event_exposure` (`state`, `anchor`, `tail_percentile`, `available_at`), `event_specific`), `overlap` (`a`, `b`, `a_view`, `b_view`, `share_given_a`, `share_overall`, `ratio`, `flag`), `not_tested` (`candidate`, `reason`, `packet_reason`, `packet_detail`), `counts` (`factors`, `supported`, `suggestive`, `not_supported`, `insufficient`, `not_applicable`, `not_yet_available`, `not_tested`).
Flags: `same_day_unverified`, `contrary`, `placebo_fired`, `entangled`, `small_group`.

---

## 12. Worked example: Meera, 2026-09-17, 22:30

The hand-off is the glucose item that opened at 22:30 (rule `glucose_above_post_meal`, last meal 62 minutes earlier at 21:28). The packet selected seven factors. The numbers below are from my own prototype run on her real data with the settings in section 10, detrending on and the ordering rule applied. They are **illustrations of the method, not engine output**.

| Candidate | Exposure and window | Exposed | Reference | Effect | p (perm.) | p (adj., 5 tests) | Label | Flags |
|---|---|---|---|---|---|---|---|---|
| medication_adherence | missed dose in the last 2 days | 238 | 97 | 0.24 | 0.0345 | 0.086 | supported | same_day_unverified |
| sleep | sleep hours, previous night | 335 | - | 0.12 | 0.033 | 0.086 | supported | - |
| stress_mood | strained mood block before the meal, same day | 39 | 296 | 0.16 | 0.2444 | 0.407 | not_supported | - |
| activity | steps, daily total | 324 | - | 0.03 | 0.3958 | 0.495 | not_supported | same_day_unverified |
| illness_symptoms | symptom diary entry, last 3 days, before the meal | 34 | 301 | -0.53 | 0.9955 | 0.996 | not_supported | contrary, placebo_fired |
| alcohol | alcohol diary entry, same day, before the meal | 2 | 333 | 1.83 | 0.0255 | - | insufficient | - |

- **Meal.** Her glucose peak in the first 62 minutes after this dinner (185.0) is at the **99th percentile** of 346 earlier dinners' first-hour peaks (my prototype counts the labels `dinner` and `light_dinner`; the engine's meal-kind matching also includes festive and late dinners, so its count will be slightly higher) (median 150.1, 90th percentile 167.4). Label `supported`.
- **Missed dose and sleep** are labelled `supported` here only because the illustration corrects for five tests. In the engine's own run, with a family of 48 tested relationships, the sleep relationship had an adjusted p of 0.096, just under 0.10, so relationships near the line flip between `supported` and `suggestive` from day to day. The effects are small (0.24 and 0.12).
- **Event exposure.** Missed dose: `exposed` (1 of 3 doses taken; the record is available from 21:00). Sleep: `exposed`, 3.8 hours is at the 0.6th percentile of her history. Strained period: `exposed` (all three mood blocks of the day were strain categories, and each had ended before the 21:28 meal). Steps: `not_yet_available` (the daily total arrives at the end of the day). Illness and alcohol: `not_exposed` (no such diary entries up to 22:30).
- **Illness** carries `contrary`: on days with a symptom entry her dinner peak was lower by 7.2 mg/dL (a possible reason is lighter dinners on those days; this was not checked), and the placebo also fired, so it is flagged for caution. It is `not_supported` either way.
- **Alcohol** is `insufficient`: only 2 days in her year had an alcohol entry before that day's dinner.
- **Overlap.** Among supported factors, 82% of her worst-sleep-quartile days also had a missed dose in the last 2 days, against 72% overall (ratio 1.14). No flag.
- **Flags.** `same_day_unverified` marks the two relationships whose exposure is a date-only record from the same date as the outcome (medicine record, daily steps).

**Why detrending is the default.** On the same data without detrending, the missed-dose effect was 0.27 instead of 0.15 (using a same-day definition I tried first), and sleep was 0.23 instead of 0.12. Her dinner peaks fell from about 171 in October to 142 in August and rose again to 171 in September, while the share of days with a missed dose moved the same way (0.71, 0.26, 0.69). Part of the apparent link was the shared slow trend.

---

## 13. Properties that must hold

1. **Deterministic.** The same inputs, config and method version always give the same records, including the random seeds.
2. **No look-ahead.** Relationship evidence for an outcome date uses only days before it. Event evidence uses only records available at `opened_at`.
3. **Read-only.** Nothing is written outside the Evidence Engine's own database.
4. **No LLM, no network.**
5. **Does not read PI, `memory_v2` or diary text.** Only diary category and timestamp.
6. **Statistics live only here.** Event records hold references, plus the event-specific statistic.
7. **Idempotent.** Re-running a date or a packet gives the same record and no duplicate. A relationship record is superseded only when its `inputs_hash` changes. An event record is never changed after it is written; late labels go into `event_completions`.
8. **Completeness.** Every candidate of the packet appears exactly once, in `factors` or in `not_tested`. No factor is invented. A deferred packet has no factors and every candidate in `not_tested`.
9. **Labels never use weight tiers or evidence levels.**
10. **Insufficient is not support.** A relationship below the minimums is `insufficient` and never carries a supported or suggestive label.
11. **Orientation is applied consistently** and every test is one-sided for a positive association, with the opposite direction reported separately.
12. **Multiplicity and placebo** are applied on every refresh, and their counts are recorded in `evidence_runs`.
13. **Event exposure uses availability.** `not_yet_available` is never reported as `not_exposed`.
14. **Detrending uses only earlier values. The ordering rule (3.1 rule 6) is applied to every exposure.**
15. **Generic.** No stream, medicine, measure or patient name appears in the engine. The library and config define everything; a second patient with different streams runs with config changes only.
16. **Library check at load.** Loading fails with a plain message if: a library pair refers to an unknown exposure or outcome; a `runnable` pair has no relationship key; a rulebook candidate (read from the rulebook files) has no pair row, or a pair row has no rulebook candidate; an exposure form is not binary or continuous; a lookback kind is unknown; the pair table and the rulebook disagree on `check_type` or `weight_tier`; the lookback tag in a relationship key differs from the rulebook's lookback kind and value (with two documented exceptions: the sleep shift and `excludes_outcome_day`); an `Ordering` value is not one of the four allowed; the presence flags differ from the Rulebook Lookup config.

---

## 14. Limits, assumptions and open items

| Item | What I assumed | Where it matters |
|---|---|---|
| Thresholds | All statistical thresholds are placeholders. | Which labels appear. Do not tune them to produce findings; tune only against a scoring step. |
| Expect few `supported` labels | Effects on the first patient are small after detrending, and a family of about 50 tests needs strong evidence. | Many relationships will be `suggestive` or `not_supported`. That is a result, not a defect. |
| Small groups | Alcohol, weather and travel entries have 6, 4 and 2 days in the first patient's year, so they are always `insufficient`. Sleep under 5 hours has 17 days. | Some relationships can never be learned on this patient. |
| Early history | Almost nothing is testable in the first weeks (the minimums need weeks of data). | Evidence for Oct to Dec will be mostly `insufficient`. |
| Date-only records and day-level outcomes | Same-day ordering cannot be verified (22 runnable pairs carry `same_day_unverified`). | Any claim of "before" for those pairs is weak; downstream wording must say "on the same day". |
| Rulebook lookbacks | Three `sleep_below` rows, five `hydration_below` rows and one `blood_pressure_above` row (`stress_mood`, same day, against a morning reading) have lookbacks written for an item that opens at a different time of day. The Evidence Engine anchors every window to the outcome date or unit start and never uses the packet's `resolved_window`, so it is not affected. | The rulebook rows should still be corrected later, because the packet's windows are misleading to anyone who reads them. |
| Maturity | Most relationships first reach the minimums between December and February; blood pressure pairs from March; `missed_dose@2d` pairs only in February (its reference group is small); some only later in the year. October and November are `insufficient` almost everywhere. | Early months of any replay |
| Low-contrast exposures | `missed_dose@2d` is exposed on about 72% of days, so the comparison is "any miss in two days" against "none". | Effects are small by construction |
| Never reaches the minimums on the first patient | The seven alcohol pairs, `missed_dose@7d`, `clinic_reading`, the blood pressure symptom pair and `environment_entry` for fluid intake (11 pairs), plus two relationships with no ordered exposure (the blood pressure mood pair, and the breakfast scope of the mood pair for post-meal peaks) | `insufficient` all year, which is a result |
| Detrending | A 30-day trailing median is a simple choice. It removes slow trends, and it can also remove real slow effects. | Effect sizes |
| Synthetic data | The first patient's relationships were partly built in when the data was generated (for example heart rate from steps, sleep and mood). The engine will find what was put there. | Any claim of "it learned her". A ground-truth scoring step is needed. |
| One outcome per rule | Blood pressure uses systolic only; heart rate uses a day mean or an hour mean. | Coverage |
| Hand-offs of one moment | Each hand-off gets its own record, even if several open together. | Findings groups them |
| Whole-history percentile | Event percentiles use her whole earlier history. | A patient whose level drifts |

Known data issues carried from earlier components (report, do not patch): five isolated 65.0 glucose readings are not caught by the generic cleaning rule; labs sit above the glucose-based estimate.

---

## 15. Out of scope

Statuses and beliefs (PI), wording (Findings, Narrative), cases, factor discovery, any change to the rulebook, the ground-truth manifest and scoring (a separate task), and hourly steps as a State Engine measure.

## 16. Glossary

| Term | Meaning |
|---|---|
| Relationship | One exposure over one window paired with one outcome for this patient |
| Relationship evidence | The daily, cached statistics for a relationship |
| Event evidence | The record for one hand-off: each factor's label, whether the event was exposed, and event-specific statistics |
| Evidence label | `supported`, `suggestive`, `not_supported`, `insufficient` (or `not_applicable`). Not a belief. |
| Outcome date | The local date an outcome belongs to; history is the completed days before it |
| Detrending | Replacing an outcome by its difference from its own recent median |
| Circular shift | Rotating a series to break its alignment with another while keeping its own structure |
| Placebo | A repeat of a test with a deliberately misaligned exposure; it should find nothing |
| Family | All relationships tested on one refresh, used for the multiple-testing correction |

---

## Appendix A. The pair table (one row per rulebook candidate)

| Rule | # | Tier | Candidate | Check type | Exposure | Outcome | Relationship key | V0 status | Ordering |
|---|---|---|---|---|---|---|---|---|---|
| `glucose_above_post_meal` | 1 | primary | meal_composition | percentile_vs_history | - | post_meal_peak | - | event_level | - |
| `glucose_above_post_meal` | 2 | secondary | medication_adherence | group_comparison | missed_dose | post_meal_peak | `missed_dose@2d->post_meal_peak:{meal_kind}` | runnable | same_day_unverified |
| `glucose_above_post_meal` | 3 | secondary | sleep | group_comparison | sleep_hours | post_meal_peak | `sleep_hours@prev_night->post_meal_peak:{meal_kind}` | runnable | ordered |
| `glucose_above_post_meal` | 4 | secondary | stress_mood | group_comparison | strained_period | post_meal_peak | `strained_period@1d->post_meal_peak:{meal_kind}` | runnable | ordered |
| `glucose_above_post_meal` | 5 | secondary | activity | group_comparison | steps_total | post_meal_peak | `steps_total@1d->post_meal_peak:{meal_kind}` | runnable | same_day_unverified |
| `glucose_above_post_meal` | 6 | secondary | illness_symptoms | group_comparison | symptom_entry | post_meal_peak | `symptom_entry@3d->post_meal_peak:{meal_kind}` | runnable | ordered |
| `glucose_above_post_meal` | 7 | secondary | meal_timing | group_comparison | late_meal | post_meal_peak | `late_meal@same_day->post_meal_peak:{meal_kind}` | runnable | ordered |
| `glucose_above_post_meal` | 8 | tertiary | other_medications | presence_check | - | - | - | event_level | - |
| `glucose_above_post_meal` | 9 | tertiary | cycle_phase | group_comparison | - | - | - | no_definition | - |
| `glucose_above_post_meal` | 10 | tertiary | alcohol | group_comparison | alcohol_entry | post_meal_peak | `alcohol_entry@1d->post_meal_peak:{meal_kind}` | runnable | ordered |
| `glucose_above_no_recent_meal` | 1 | primary | medication_adherence | group_comparison | missed_dose | non_meal_mean | `missed_dose@2d->non_meal_mean` | runnable | same_day_unverified |
| `glucose_above_no_recent_meal` | 2 | primary | illness_symptoms | group_comparison | symptom_entry | non_meal_mean | `symptom_entry@3d->non_meal_mean` | runnable | same_day_unverified |
| `glucose_above_no_recent_meal` | 3 | secondary | stress_mood | group_comparison | strained_period | non_meal_mean | `strained_period@1d->non_meal_mean` | runnable | same_day_unverified |
| `glucose_above_no_recent_meal` | 4 | secondary | sleep | group_comparison | sleep_hours | non_meal_mean | `sleep_hours@prev_night->non_meal_mean` | runnable | same_day_unverified |
| `glucose_above_no_recent_meal` | 5 | secondary | activity | group_comparison | steps_total | non_meal_mean | `steps_total@prev_day->non_meal_mean` | runnable | ordered |
| `glucose_above_no_recent_meal` | 6 | secondary | prior_evening_meal | group_comparison | late_prior_dinner | non_meal_mean | `late_prior_dinner@prev_evening->non_meal_mean` | runnable | ordered |
| `glucose_above_no_recent_meal` | 7 | secondary | dawn_effect | pattern_repeat | - | - | - | event_level | - |
| `glucose_above_no_recent_meal` | 8 | tertiary | other_medications | presence_check | - | - | - | event_level | - |
| `glucose_above_no_recent_meal` | 9 | tertiary | cycle_phase | group_comparison | - | - | - | no_definition | - |
| `glucose_below` | 1 | primary | sensor_artifact | shape_check | - | - | - | event_level | - |
| `glucose_below` | 2 | primary | meal_skipped_or_delayed | percentile_vs_history | - | - | - | event_level | - |
| `glucose_below` | 3 | secondary | unusual_activity | group_comparison | high_steps_day | day_min_glucose | `high_steps_day@1d->day_min_glucose` | runnable | same_day_unverified |
| `glucose_below` | 4 | secondary | alcohol | group_comparison | alcohol_entry | day_min_glucose | `alcohol_entry@720m->day_min_glucose` | runnable | ordered |
| `glucose_below` | 5 | secondary | hypoglycemic_agent | presence_check | - | - | - | event_level | - |
| `glucose_below` | 6 | tertiary | illness_poor_intake | group_comparison | symptom_entry | day_min_glucose | `symptom_entry@1d->day_min_glucose` | runnable | same_day_unverified |
| `heart_rate_above` | 1 | primary | activity | group_comparison | steps_window_hourly | hr_hour_mean | `steps_window_hourly@60m->hr_hour_mean` | runnable | ordered |
| `heart_rate_above` | 2 | primary | stress_mood | group_comparison | strained_period | hr_day_mean | `strained_period@same_day->hr_day_mean` | runnable | same_day_unverified |
| `heart_rate_above` | 3 | primary | illness_fever | group_comparison | symptom_entry | hr_day_mean | `symptom_entry@3d->hr_day_mean` | runnable | same_day_unverified |
| `heart_rate_above` | 4 | secondary | hydration | group_comparison | hydration_total | hr_day_mean | `hydration_total@prev_day->hr_day_mean` | runnable | ordered |
| `heart_rate_above` | 5 | secondary | caffeine_stimulants | group_comparison | - | - | - | no_definition | - |
| `heart_rate_above` | 6 | secondary | sleep | group_comparison | sleep_hours | hr_day_mean | `sleep_hours@prev_night->hr_day_mean` | runnable | same_day_unverified |
| `heart_rate_above` | 7 | secondary | alcohol | group_comparison | alcohol_entry | hr_day_mean | `alcohol_entry@720m->hr_day_mean` | runnable | ordered |
| `heart_rate_above` | 8 | tertiary | thyroid_status | presence_check | - | - | - | event_level | - |
| `heart_rate_above` | 9 | tertiary | meal_digestive | group_comparison | - | - | - | no_definition | - |
| `resting_heart_rate_above` | 1 | primary | sleep | group_comparison | sleep_hours | resting_hr_day | `sleep_hours@prev_night->resting_hr_day` | runnable | same_day_unverified |
| `resting_heart_rate_above` | 2 | primary | illness_fever | group_comparison | symptom_entry | resting_hr_day | `symptom_entry@3d->resting_hr_day` | runnable | same_day_unverified |
| `resting_heart_rate_above` | 3 | secondary | stress_mood | group_comparison | strained_period | resting_hr_day | `strained_period@prev_day->resting_hr_day` | runnable | ordered |
| `resting_heart_rate_above` | 4 | secondary | hydration | group_comparison | hydration_total | resting_hr_day | `hydration_total@prev_day->resting_hr_day` | runnable | ordered |
| `resting_heart_rate_above` | 5 | secondary | alcohol | group_comparison | alcohol_entry | resting_hr_day | `alcohol_entry@prev_evening->resting_hr_day` | runnable | ordered |
| `resting_heart_rate_above` | 6 | tertiary | thyroid_status | presence_check | - | - | - | event_level | - |
| `resting_heart_rate_above` | 7 | tertiary | unusual_activity_prior_day | group_comparison | - | - | - | no_definition | - |
| `sleep_below` | 1 | primary | stress_mood | group_comparison | strained_period | sleep_hours_night | `strained_period@same_day->sleep_hours_night` | runnable | ordered |
| `sleep_below` | 2 | secondary | meal_timing | group_comparison | late_prior_dinner | sleep_hours_night | `late_prior_dinner@prev_evening->sleep_hours_night` | runnable | ordered |
| `sleep_below` | 3 | secondary | alcohol_caffeine | group_comparison | alcohol_entry | sleep_hours_night | `alcohol_entry@prev_evening->sleep_hours_night` | runnable | ordered |
| `sleep_below` | 4 | secondary | screen_time | group_comparison | screen_hours | sleep_hours_night | `screen_hours@prev_evening->sleep_hours_night` | runnable | ordered |
| `sleep_below` | 5 | secondary | illness_symptoms | group_comparison | symptom_entry | sleep_hours_night | `symptom_entry@same_day->sleep_hours_night` | runnable | ordered |
| `sleep_below` | 6 | tertiary | travel_environment | group_comparison | non_home_day | sleep_hours_night | `non_home_day@same_day->sleep_hours_night` | runnable | ordered |
| `sleep_below` | 7 | tertiary | overnight_glucose | group_comparison | - | - | - | no_definition | - |
| `medication_adherence_below` | 1 | primary | routine_disruption | group_comparison | non_home_day | missed_doses_day | `non_home_day@same_day->missed_doses_day` | runnable | same_day_unverified |
| `medication_adherence_below` | 2 | primary | stress_mood | group_comparison | strained_period | missed_doses_day | `strained_period@same_day->missed_doses_day` | runnable | same_day_unverified |
| `medication_adherence_below` | 3 | secondary | illness_symptoms | group_comparison | symptom_entry | missed_doses_day | `symptom_entry@same_day->missed_doses_day` | runnable | same_day_unverified |
| `medication_adherence_below` | 4 | secondary | recent_adherence_pattern | group_comparison | missed_dose | missed_doses_day | `missed_dose@7d->missed_doses_day` | runnable | excludes_outcome_day |
| `medication_adherence_below` | 5 | secondary | sleep_prior_night | group_comparison | sleep_hours | missed_doses_day | `sleep_hours@prev_night->missed_doses_day` | runnable | same_day_unverified |
| `medication_adherence_below` | 6 | tertiary | regimen_factors | pattern_repeat | - | - | - | event_level | - |
| `blood_pressure_above` | 1 | primary | medication_adherence | group_comparison | missed_dose | systolic_reading | `missed_dose@2d->systolic_reading` | runnable | same_day_unverified |
| `blood_pressure_above` | 2 | primary | measurement_context | group_comparison | clinic_reading | systolic_reading | `clinic_reading@at_open->systolic_reading` | runnable | same_day_unverified |
| `blood_pressure_above` | 3 | secondary | stress_mood | group_comparison | strained_period | systolic_reading | `strained_period@same_day->systolic_reading` | runnable | no_ordered_exposure |
| `blood_pressure_above` | 4 | secondary | sleep | group_comparison | sleep_hours | systolic_reading | `sleep_hours@prev_night->systolic_reading` | runnable | ordered |
| `blood_pressure_above` | 5 | secondary | salt_in_meals | group_comparison | - | - | - | no_definition | - |
| `blood_pressure_above` | 6 | tertiary | alcohol_caffeine | group_comparison | alcohol_entry | systolic_reading | `alcohol_entry@720m->systolic_reading` | runnable | ordered |
| `blood_pressure_above` | 7 | tertiary | pain_or_illness | group_comparison | symptom_entry | systolic_reading | `symptom_entry@same_day->systolic_reading` | runnable | ordered |
| `blood_pressure_above` | 8 | tertiary | other_medications | presence_check | - | - | - | event_level | - |
| `hydration_below` | 1 | primary | illness_symptoms | group_comparison | symptom_entry | fluid_intake_day | `symptom_entry@same_day->fluid_intake_day` | runnable | same_day_unverified |
| `hydration_below` | 2 | primary | busy_routine | group_comparison | non_home_day | fluid_intake_day | `non_home_day@same_day->fluid_intake_day` | runnable | same_day_unverified |
| `hydration_below` | 3 | secondary | high_prior_glucose | group_comparison | prior_day_glucose_mean | fluid_intake_day | `prior_day_glucose_mean@prev_day->fluid_intake_day` | runnable | ordered |
| `hydration_below` | 4 | secondary | weather_environment | group_comparison | environment_entry | fluid_intake_day | `environment_entry@same_day->fluid_intake_day` | runnable | same_day_unverified |
| `hydration_below` | 5 | tertiary | alcohol | group_comparison | alcohol_entry | fluid_intake_day | `alcohol_entry@prev_evening->fluid_intake_day` | runnable | ordered |
| `screen_time_above` | 1 | secondary | workload_events | group_comparison | - | - | - | rule_deferred | - |
| `screen_time_above` | 2 | secondary | illness_bedrest | group_comparison | - | - | - | rule_deferred | - |

---

## Appendix B. Resolutions of the Step 1 report

Each row says how the point was resolved in this revision. "Decided" means the owner decided; "Accepted" means the proposal in the Step 1 report was accepted as written.

| # | Point | Resolution |
|---|---|---|
| A1 | Ordering rule vs `same_day_unverified` for blocks and entries on day-level outcomes | **Decided:** on day-level units they count as date-resolution and are flagged (3.1 rule 6). Meal, hour and reading units keep the literal ordering rule. |
| A2 | `sleep_hours@prev_night` on day-level outcomes | **Decided:** the record dated the outcome date, flagged `same_day_unverified`. 22 runnable pairs now carry the flag. |
| A3 | Windows anchored to `opened_at` | **Decided:** all windows are anchored to the outcome date or unit start; `resolved_window` is never used (3.1 rule 5). |
| A4 | Minute windows in history rows | **Accepted:** history rows use the unit start; the event record uses `opened_at`, and says which. |
| A5, A8 | Hourly steps stamp and availability | **Decided:** the row holds the steps during the hour, is available at the end of the hour (library config), and the exposure for the hour starting at H is the row stamped H-1 (3.1 rule 8). |
| A6 | Meal-unit ordering at unit start | No change: a value at the start counts. |
| A7 | Look-ahead in late history rows | **Accepted:** a unit enters the history only after its whole forward window has ended (3.1 rule 2). |
| A9 | Detrending hour and reading units | **Decided:** same clock hour for hour units; same meal kind for meal units; previous 30 days for day and reading units (7.1). |
| A10 | Placebo | **Accepted:** shift exactly 30%, p from the same null, fired if p at most 0.10 and effect at least the floor; not in the family (7.2). |
| A11 | Family for the correction | **Accepted:** relationships that passed the minimums; `family_size` recorded. |
| A12 | Overlap | **Accepted:** one entry per unordered pair, larger `share_given_a`; days are outcome dates (7.2). |
| A13 | `small_group` flag | **Accepted:** only on an `insufficient` label caused by a small group. |
| A14 | Dependency and determinism | **Decided:** numpy may be added to the project; stable hashed seeds; comparison tolerance (7.2, 10). |
| A15 | Zero variance | **Accepted:** `insufficient` with reason `no_variation`. |
| A16 | Shape check needs later data | **Decided:** the event record is immutable; a completion row fills the label later (7.3, 9.3). |
| A17 | Deferred and unmatched packets | **Accepted:** `factors: []` and every candidate in `not_tested` (E1). |
| A18 | `not_tested` reasons | **Accepted:** `not_selected_budget` and `skipped_by_packet` with the packet's own reason and detail kept (E5). |
| A19 | `rank` in the example | **Accepted:** the packet's rank is copied. |
| A20 | Event exposure for event-level checks | **Accepted:** percentile at least 75 is `exposed`; other event-level checks have none (7.4). |
| A21 | Percentile details | **Decided:** `bucket_minutes` holds the rounded elapsed time and `bucket_size` is 15; `meal_skipped_or_delayed` compares at the same clock hour (7.3). |
| A22 | Dawn rise | **Accepted:** the highest reading in the window minus the lowest reading before it. |
| A23 | Presence flags | **Accepted:** present if any flag is true; copied into the evidence config and checked against the rulebook config at load. |
| A24 | Partly available windows | **Accepted:** the rule in 7.4. |
| A25 | Meal with no kind | **Accepted:** `insufficient` with reason `no_meal_kind` for relationship factors; the percentile still runs. |
| A26 | Stream tokens | **Accepted:** generic tokens in the library, a `stream_map` in the patient evidence config (4.3). |
| A27 | Duplicate resting heart rate | **Accepted:** the last value of the day (config). |
| A28 | Smaller points | **Accepted:** the key's lookback tag is checked at load; location types live in the evidence config; the example's dinner count is noted; the missed medicines come from the store's records. |

---

## Appendix C. Resolutions of the Stage 2a report

| # | Point | Resolution |
|---|---|---|
| 1 | Cross-reference "3.1 rule 5" for the ordering rule | **Fixed:** 7.1 and property 14 now cite rule 6. |
| 2 | The 60-unit minimum, days or units | **Decided:** both are required: at least 60 usable units and at least `min_history_days` (60) distinct outcome dates. The hourly relationship is first tested on 2025-12-10; October and November have no `supported` records. A test checks that an hourly relationship is not tested before 60 distinct days. |
| 3 | Section 14 count of pairs that never reach the minimums | **Fixed:** 11 pairs (adds `environment_entry` for fluid intake) plus the two relationships with no ordered exposure. |
| 4 | High share of `supported` records | **Explained, not tuned:** many day-level conditions in the generated data are built to move together with their outcomes, and the placebo fire rate of 8.6% shows the false-positive rate is near the nominal level. The share of `supported` records that carry `same_day_unverified` is reported in Stage 2b. |
| 5 | Borderline relationships flip between `supported` and `suggestive` | **Accepted:** the flip rate per relationship is reported in Stage 2b (section 12 now says so). |
| 6 | Circular shift on hourly units keeps the daily rhythm but not the day-to-day structure | **Unchanged** in V0. |

