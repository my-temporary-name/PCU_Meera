# Rulebook Lookup — Step 1 report (read-only)

Nothing was built, changed or committed. The four files in `task/evidence_engine/` are untouched. Scratch checks ran against `output/state_engine.db` and `output/personal_data_store.db` (opened for reading) and the CSVs.

## (c) CSV validation (spec section 10, property 14)

I ran every check in property 14 that can be run on the files as they are.

| Check | Result |
|---|---|
| ranks contiguous 1..n per rule | pass (10 rules) |
| tiers in order primary, secondary, tertiary | pass |
| secondary / tertiary ordered by evidence level A→D | pass |
| `primary_count` equals actual primaries | pass (1,2,2,3,2,1,2,2,2,0) |
| unknown source IDs (valid S1..S20) | pass; no unknown IDs |
| `rule_id` repeated | pass; none |
| rule without candidates (unless deferred) | pass; every rule has candidates |
| candidates pointing at an unknown rule | pass; none |
| `check_type`, `data_status_meera_code`, tier and evidence-level values in their allowed sets | pass |
| grammar terms parse (`requires_streams`, `applies_if_rule`, lookback kinds) | pass. All 8 `lookback_kind` values used are in section 3. All `applies_if_rule` terms are one of the 4 forms. |
| two rules able to match the same hand-off | pass for this file: the only shared (measure, direction) pair is glucose/above, and its two `context_match` values are disjoint (<=180 vs >180 or absent) |
| files carry different `rulebook_version` | **cannot be checked as written**: only the rules file has the column (`v0-draft-1` on all 10 rows). The candidates file has no such column, and `rulebook_v0.md` carries no machine-readable version. See A1. |

Other things in the files that do not fail validation, but that you should know about:

- Nine candidates have an empty `sources`. Seven are evidence level C, two (screen time) are D. All nine are labelled "none" in the md. Two other C rows do cite S18 (`sleep_below` #7, `hydration_below` #2). No A or B row has an empty source.
- For every rule, `max_total` equals primary_count + `secondary_max` + `tertiary_max` exactly. So `max_total` can never bind on this rulebook. It is a redundant constraint, not an error (A9).
- `budget_reason` for `glucose_above_post_meal` says "9 candidates exist"; the table and CSV have 10. Words only.
- I reproduced the section 9.3 numbers with a scratch script (same logic as R1–R5, config from 4.3). The selected count per packet matches for all ten rules (8, 5, 7, 6, 6, 6, 0, 5, 7, 5). All 287 hand-offs match a rule. "14 of 69 never selected" reconciles: 3 (post-meal) + 4 (no-recent-meal) + 1 + 1 + 1 + 1 (sleep) + 1 (BP) + 2 (screen time, deferred) = 14. Of the 7 "always skipped": cycle_phase ×2, other_medications ×3, hypoglycemic_agent, caffeine_stimulants. The 16 and 43 dawn_effect figures match (opening in 04:00–09:00: 16; the end time inclusive or exclusive gives 16 either way on this data).

## (b) [verify] items against the real store and code

### Hand-off fields (`state_handoffs.record_json`, 287 rows, all unique ids)

Keys present: `handoff_id, item_id, written_at, measure, direction, size, trigger, value, clinical_status, usual_basis, position_z, opened_at, context{last_meal, medication, sleep_last_night, other_open_items, diary_today_count}, snapshot_as_of`. Every field named in 4.1 exists. Differences and facts:

- `last_meal` is always present as a key, either an object or `null`. It is **never null in this data** (0 of 287), because the State Engine looks back 1440 min. So "last_meal absent" in the grammar means null/missing. On this data it never occurs. All 59 no-recent-meal hand-offs have a last meal more than 180 min ago. `minutes_ago` is an int. No hand-off has exactly 180 (neighbours: 179 and 181).
- `size` is only `clearly` (264) or `far` (23); `trigger` is `persistence` (264) or `severe` (23).
- `clinical_status` is null for all 117 hand-offs of measures with no status (heart rate and others), so it must be copied as null. Values seen: high, normal, low, borderline_low.
- `position_z` is null for 27 hand-offs. `usual_basis` is one of clock_time, meal_relative, profile, history_percentile.
- `value` is a float for most measures, but a **dict** for `blood_pressure` (`{systolic, diastolic}`) and `medication_adherence` (`{taken, expected, missed:[...]}`).
- Medicine naming is inconsistent inside one hand-off: `value.missed` carries raw ids (`med_002_metformin`), while `context.medication.missed` carries names (`metformin`). The rulebook needs neither. Only matters if `value` is copied into the packet (A13).
- All 9 (measure, direction) pairs in the hand-offs have a rule: heart_rate/above 124, glucose/above 99, medication_adherence/below 24, resting_heart_rate/above 12, sleep_duration/below 10, screen_time/above 8, glucose/below 5, blood_pressure/above 3, hydration/below 2. Measure keys match the rules file exactly, so no mapping is needed.
- All `opened_at` are `+05:30` strings, and `written_at == opened_at` on all 287.
- The 5 glucose-below hand-offs: four are 65.0 `low`/`severe`, one is 76.3 `normal`/`severe` (far). The rule text says "clinical status low, or position far", which holds for all five.
- The 2026-09-17T22:30 hand-off in the 7.1 example exists and agrees with the example (185.0, high, clearly, persistence, last meal 62 min). The real hand-off has `usual_basis: meal_relative` and `position_z: 2.21`.

### Stream names (`stream_map`)

| Token | Real place | Result |
|---|---|---|
| `meal_events`, `medication_adherence`, `mood_state`, `diary_context`, `location` | `context_events.stream` | exist as named |
| `sleep_duration`, `step_count`, `hydration`, `screen_time`, `cgm_glucose_reading` | `raw_events.biomarker` | exist as named (step_count has 340 daily rows, not 352) |
| `food_content` | **not in the store** | `final/food_content_full_year.csv` exists (1,055 rows) but is not loaded. The same description is already in `context_events` as `meal_events.value_text` ("Dosa, chutney, coffee"), meta has `meal_id`. So the config claim `food_content: food_content` names a stream that does not exist. Decision D1. |
| `medication_list` | **not a stream** | There is no medication config file. Medicine names come only from `medication_adherence.category` (`med_002_metformin`, `med_003_amlodipine`, `med_004_levothyroxine`) through `medication_id_regex`. Decision D2. |
| `step_count_hourly` | not in the store | `final/steps_hourly_yearly.csv` exists (8,160 rows) and is read by the pipeline, but only the daily sum is stored. Null is correct for the store; see D3. |
| `menstrual_cycle` | not in the store | `final/menstrual_cycle_full_year.csv` exists (352 days: `cycle_phase`, `cycle_day`, `menopause_status` = `peri`). It is not loaded anywhere. The spec says "not confirmed to be in the store"; confirmed: **not in the store, but the data exists in the source files**. Decision D3. |
| `lab_tsh` | not in the store | TSH rows exist in `final/lab_panels_yearly.csv` (4 rows) but the pipeline does not evaluate them. |
| `caffeine_intake` | no data anywhere | null is right |
| `time_of_day` | derived | fine |

Also in the store but not in the map: `sleep_quality` (context stream), `continuous_heart_rate`, `resting_heart_rate`, BP. Not an issue.

### Medicine names

The baseline config's `medication_id_regex: "^med_\d+_"` gives `metformin`, `amlodipine`, `levothyroxine`. All three exist in the store (352 rows each). The spec's `medication_classes` keys match. Confirmed.

### Where patient flags can come from

- Derived flags (`takes_glucose_lowering_medication`, `takes_bp_medication`): derivable from `medication_classes`, as the spec says.
- `has_thyroid_condition: true`: **no data source anywhere.** I searched the final/ CSVs and markdown; "thyroid" appears nowhere, and the allergies file has no conditions. It can only be an explicit config assertion. The spec says "condition known". It is only implied by levothyroxine, and `medication_class_present:thyroid` is already true on that basis, so the flag adds nothing for this patient. Decision D4.
- No flag for the other classes in `applies_if_rule` (`insulin`, `sulfonylurea`, `glucose_raising`, `bp_raising`) exists in config; the spec says unknown means false. That is what gives the 9.3 result.

## (a) Ambiguities and contradictions in the spec

Numbered A1..A20. "Proposed" is what I will do unless you say otherwise.

**A1. Version check (4.2, 10.14).** Property 14 asks for a check across files, but only the rules file has `rulebook_version`. Proposed: take the version from the rules file; check every row in it is the same; for the other two files, require a `rulebook_version` column only if present. Alternative: you add the column to the candidates CSV (you said not to change rulebook files, so I won't).

**A2. "Two rules could match the same hand-off" (10.14).** The grammar is tiny but "could match" is not defined for a generic check. Proposed: group by (measure, direction). If a group has more than one rule, evaluate the contexts on a probe set (last meal absent, 0, every number in the grammar and ±1, a large value); two rules that both match a probe fail the load. Two rules with an empty `context_match` in one group fail immediately.

**A3. `context_match` grammar (5.1).** Only two literal forms are given. "or" has no precedence or general parse. Also the number 180 is "a rulebook value, not config", while the State Engine config has its own `meal_window_minutes: 180`. Nothing links them; if one is changed the rules disagree silently. Proposed: parse a minimal grammar (`last_meal_minutes_ago<op>N`, `last_meal absent`, joined by `or`, `and`), nothing else, and report an unparseable string at load. Note the coupling in the docs.

**A4. Fallback tokens in `streams` (5.2, 7.1).** The example shows one object per `;` token. For `a|b` (only `step_count_hourly|step_count`, heart-rate activity) the format is not defined: one object per alternative? which one was used? Proposed: one object per alternative, in order, each with `available`, and a `used: true` flag on the first available one. Add that key for every stream object (false for non-fallback), or only on fallback groups; I need your choice (D5).

**A5. Mixed `;` and `|` in `requires_streams` (5.2).** Only separate uses occur in the file. The precedence is unstated. Proposed: `;` splits groups, `|` splits alternatives inside a group; runnable when any group has an available alternative (matches "any-of").

**A6. "patient's medicines" (5.3, 4.3).** `medication_class_present` says "any of the patient's medicines". Where is that list? Proposed: the keys of `rulebook.medication_classes` (config only, no store read). The engine then never reads the store. The alternative (read the medicines from `context_events`) would make the engine depend on data, against "no data lookup".

**A7. `open_time_between` (5.3).** Not stated: whether the end is inclusive, and what a range that crosses midnight means (e.g. 22:00-04:00). Proposed: start inclusive, end exclusive; crossing midnight allowed (matches if t >= start or t < end). "Local time" needs a time zone, see A12.

**A8. Skip `detail` for OR groups (R3).** When a term like `patient_flag:x|medication_class_present:y` fails, "the failing term" is the whole OR group, or each alternative? Proposed: the whole term as written in the file. When a flag name is in both `patient_flags` and `derived_flags`, precedence is unstated; proposed: explicit `patient_flags` wins.

**A9. Budget details (R5).** `max_total` never binds on this file (equals the sum of the three caps everywhere) and nothing says what happens if the primary count alone exceeds `max_total`. Proposed: primaries are always selected (property 7), so `max_total` can only stop secondary/tertiary; add a load check `max_total >= primary_count`. Also do I validate `max_total <= primary + secondary_max + tertiary_max`? Spec silent; I will not fail on it.

**A10. Evidence bar hint (R8) for packets with no selection.** Not stated for deferred, unmatched. Proposed: `standard` (0 selected is not more than 4).

**A11. Deferred packets vs completeness (R2 vs property 6 and 7.1 `counts`).** R2 says a deferred packet has "no candidates". Property 6 says every candidate of the matched rule appears once in `selected`, `skipped` or `not_selected`. The deferred rule has 2 candidates, so the two cannot both hold. Proposed: property 6 applies to `ok` packets; for deferred, the three lists are empty and `counts.candidates_in_rule` is 2 with selected, skipped and not_selected all 0, so the two sums differ visibly by design (D6). `matched_rule` holds the rule (status `deferred`). For `unmatched`, `matched_rule` is null and `counts` are all 0.

**A12. Time zone (3).** "Local time of the patient" — the `rulebook:` block has no time-zone key. Hand-offs carry a `+05:30` offset; the Baseline v2 config has the patient time zone. Proposed: use the offset in the hand-off's own `opened_at` string for all windows (no new config, and generic). An IANA-zone key in the `rulebook:` block would only matter for DST.

**A13. Packet `handoff_summary` (4.1 vs 7.1).** 4.1 says `size, trigger, position_z, usual_basis, value, clinical_status` are "copied into the packet summary"; the 7.1 key list and example omit `position_z` and `usual_basis` (and `item_id`). Also `value` is a dict for two measures, with raw medicine ids in `missed`. Proposed: copy exactly the 7.1 key list; `value` copied as is (float or dict, no id rewrite); `clinical_status` and `last_meal_minutes_ago` are null when absent. Please say if `position_z` and `usual_basis` should be added.

**A14. Where the packet log lives and how a re-run behaves (2, 7.2, R9).** Not stated which file. It must not be `state_engine.db` or the store. Proposed: its own file `output/rulebook_lookup.db`, one table `rulebook_packets` with the 7.2 columns; the State Engine DB opened read-only (`StateStore(..., readonly=True)` exists). R9 says no duplicate row; if the rulebook or config changed since, the same hand-off gives a different packet. Proposed: upsert by `packet_id` (replace), so the log always holds the packet for the current rulebook; never wiped by default, `--rebuild` drops the table only. Entry point: a CLI like the other v2 engines (`uv run python -m v0_code.rulebook_lookup.run`), not a graph node.

**A15. Resolving `previous_evening` (3).** "The most recent 18:00 to 24:00 window that started before `opened_at`" means that for a hand-off opened at 22:30 the "previous evening" is the *same* evening (18:00–22:30), and for one opened at 03:00 it is yesterday's. For daily measures (sleep, resting heart rate, hydration, written at wake time) it is the evening before, which is plainly the intent. For the glucose candidate `prior_evening_meal` ("heavy or late previous dinner → overnight glucose") a 22:30 opening gets the current evening, not the previous one. Proposed: implement the sentence in section 3 literally and list this in the report; it does not change any count (that candidate is always cut by the budget).

**A16. `previous_night` is a record, not a window (3).** For a hand-off opened at 05:00 (before the 07:00 sleep record is written) "the latest sleep record at or before `opened_at`" is the night before last. For `sleep_below` `overnight_glucose` ("glucose overnight") the kind is `previous_night` too, so the glucose window has to be derived from the sleep record by Evidence Engine. Proposed: emit `{"record": "latest_sleep_record_at_or_before_open"}` exactly as in the example, plus nothing else.

**A17. Structured lookback vs the text (CSV, 3).** The structured column wins, but a few differ in meaning from the text: `dawn_effect` "same morning" is `same_calendar_day` (midnight to open, not 04:00–09:00); `sleep_below` `stress_mood` "same evening and day" is `same_calendar_day` (the evening after the opening is not included); `blood_pressure_above` `measurement_context` "same reading" is `at_open`. No action unless you want those changed.

**A18. `minutes_around_open` — only one candidate.** `glucose_below` #1 (60 min). `earliest_evaluation_time` = `opened_at + 60 min`. As specified, and in 9.3 that candidate is always selected, so all 5 low packets carry a `includes_after_open: true` window.

**A19. `data_status_code` is documentation only, but a few values disagree with the engine outcome (4.2).** E.g. `hypoglycemic_agent` and `other_medications` have `data_status_meera_code` of `skipped_by_rule`/`none`, which agree with the skips. `thyroid_status` is `partial`, and runs because `medication_list` is available while `lab_tsh` is null (the any-of rule in section 11 and the "partial" code agree). No conflict found, noted so nobody reads the code as a skip signal.

**A20. Spec text says the stream map "uses the same registry as the Baseline and State Engines" (4.3).** That registry is one config row per stream in the YAML, with `source: raw|context` and no `food_content`, `medication_list`, `menstrual_cycle` or `step_count_hourly` rows. Proposed: `stream_map` is the only authority for availability; I will not look the names up in the store registry at run time (a static consistency check can be a test, not an engine step).

## Decisions I need from you (before Step 2)

- **D1. `food_content`.** Keep `food_content: food_content` as in the spec (available per config, but there is no such stream in the store), or map it to `meal_events` (where the food description is stored)? It does not change any selection (`meal_composition` is selected either way); it only matters when Evidence Engine resolves the stream name. Recommended: map to `meal_events`.
- **D2. `medication_list`.** Keep it as a pseudo-stream that is "available" (config-derived), as the spec says? Recommended: yes, and the medicine set is the `medication_classes` keys (A6).
- **D3. `menstrual_cycle` and `step_count_hourly`.** The source files have data, the store does not. Keep both null (this reproduces 9.3 exactly), or turn them on? If `menstrual_cycle` is set, `cycle_phase` becomes selectable: glucose-above packets go to 8 selected (post-meal) and 6 (no-recent-meal, if it fits `max_total`); if `step_count_hourly` is set, the HR activity candidate would claim an hourly check the store cannot support. Recommended: keep both null for this run (they would need the store to change, and the store is frozen) and list "load cycle and hourly steps into the store" as a parked item.
- **D4. `has_thyroid_condition`.** Keep `true` as in the spec (an explicit assertion with no data behind it; changes nothing here because levothyroxine already gives `medication_class_present:thyroid`), or drop it? Recommended: keep as spec'd, document that it is asserted.
- **D5. Fallback `streams` format (A4).** One object per alternative with a `used` flag, or something else?
- **D6. Deferred packet shape (A11).** Empty lists plus `counts.candidates_in_rule: 2`, or all counts 0?
- **D7. Proposals for A1, A2, A6, A7, A12, A13, A14.** Accept as written, or tell me which to change. In particular A13 (should `position_z` and `usual_basis` be in `handoff_summary`) and A14 (packet log in `output/rulebook_lookup.db`, upsert on re-run).

Parked, not acted on: loading `food_content`, `menstrual_cycle`, hourly steps and TSH into the store; a rulebook-file column for the version in the candidates CSV; the duplicated 180-minute constant (State Engine config vs rulebook rule).
