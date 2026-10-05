# Evidence Engine: Step 1 report (read-only)

Nothing was built, changed or committed. `task/evidence_engine_spec.md` and `task/intelligence_layer_overview.md` were already in `task/`, so there was nothing to copy; the rulebook files are untouched. All checks ran read-only against `output/personal_data_store.db`, `output/state_engine.db`, `output/rulebook_lookup.db` and the configs. Counts quoted below come from scratch scripts that apply the spec's rules as I read them (no detrending, global 75th percentile for the "late" exposures); they are for judging feasibility, not engine output.

## Summary

- **Appendix A matches the rulebook exactly.** All 69 rows pair up both ways with the same candidate, tier and check type; the status counts (49 / 11 / 7 / 2), 49 distinct keys, 18 `same_day_unverified` and 1 `excludes_outcome_day` are right; every lookback tag in a key equals the rulebook's own lookback. Nothing to fix in the tables themselves.
- **All 49 runnable pairs can be computed from the store today.** One new thing is needed beyond the spec: an availability rule for the hourly steps (they are not a State Engine measure).
- **But 8 of the 49 can never produce a result as the spec's ordering rule is written, and 10 more never reach the minimums on this patient.** The cause of the first group is a contradiction between section 3.1 rule 5 and the `same_day_unverified` rows (A1 below). It needs your decision before I build, because it changes which pairs run at all.
- **Hourly steps vs the State Engine config:** the State Engine config has no `available_at` for hourly steps, so "single source" cannot hold for that stream (A8).
- **Dependency:** `numpy` is installed (2.5.3, a transitive dependency) but is not in `pyproject.toml`; `scipy` is not installed. The permutation tests at this scale need numpy; it should be declared (A14).

---

## (a) Ambiguities and contradictions

Numbered A1..A28. "Proposal" is what I will do unless you say otherwise. Items marked **DECISION** need an answer.

### Ordering and windows (the big ones)

**A1. DECISION. Rule 5 (3.1) contradicts the `same_day_unverified` rows for timestamped and block exposures on day-level outcomes (3.1 rule 5, 6.1 "Unit start", 6.2, Appendix A).**
Rule 5 says timestamped values (diary, sleep, meal starts, hourly steps) count only if recorded at or before the unit's start, and mood blocks only if they ended by the unit's start; only *date-only* values count "when their date is inside the window". A day-level outcome starts at 00:00, so nothing on its own date can be before it. Taken literally, an entry or block on the outcome date is excluded, not flagged, and the 10 pairs below lose exactly the data the flag is meant to describe:

| Pair | Literal effect on this patient |
|---|---|
| `strained_period@1d->non_meal_mean`, `@same_day->hr_day_mean`, `@same_day->missed_doses_day` | no block has ended by 00:00: 0 usable units (dead) |
| `strained_period@same_day->systolic_reading` (Appendix says `ordered`) | all 141 readings are stamped 08:00 to 08:30 and the first block ends at 12:00: 0 usable units (dead) |
| `strained_period@1d->post_meal_peak:breakfast` | breakfasts start about 08:00, before the 12:00 morning block ends: 0 units (the lunch and dinner scopes work) |
| `symptom_entry@1d->day_min_glucose`, `@same_day->missed_doses_day`, `@same_day->fluid_intake_day`, `environment_entry@same_day->fluid_intake_day` | same-date entries dropped: 0 exposed units (dead) |
| `symptom_entry@3d->non_meal_mean`, `->hr_day_mean`, `->resting_hr_day` | work, but only from the two earlier days; the flag is then misleading |

Two readings are possible: (i) literal rule 5, so those 8 pairs are dead and the flag on the other 5 is meaningless; (ii) for a day-level unit, treat every exposure on a window date as date-resolution: count it and flag `same_day_unverified`, which is what the Appendix flag says. **Proposal: (ii)**, because the Appendix, the flag name and the example in section 12 ("symptom entry, last 3 days") all assume the data is used. Under (ii) the within-day ordering is unknown and the flag says so; timestamped entries still obey rule 5 for meal, reading and hour units. This is a change of one sentence in rule 5; please confirm.

**A2. DECISION. `sleep_hours@prev_night` on day-level outcomes is labelled `ordered`, but the sleep record is stamped 07:00 (6.2, Appendix A).**
Four pairs (`->non_meal_mean`, `->hr_day_mean`, `->resting_hr_day`, `->missed_doses_day`) have unit start 00:00. Every sleep record in the store is stamped 07:00 (352 rows), so the night that ended that morning is after the unit start. Literally the record that qualifies is the one two nights back, which is not "previous night" for the event. Sleep is also the example of a continuous exposure in the section 12 prose. **Proposal:** for day-level outcomes `prev_night` means the record dated the outcome date (the night that ended that morning), and the pair is flagged `same_day_unverified` (the day's outcome cannot be shown to follow a 07:00 record, because the outcome unit starts at 00:00). This changes the Appendix `Ordering` for those four rows from `ordered` to `same_day_unverified` (22 flagged pairs instead of 18). The alternative is literal (two nights back), which I think nobody intends.

**A3. DECISION. Every exposure window is anchored to the outcome date or unit start, never to `opened_at`, but the spec states this only for sleep (3.1 rule 6, 6.1 "Exposure shift", 14).**
`hydration_below` items open at 00:00 of the next day. The rulebook resolves their windows from `opened_at`: `same_calendar_day` is then an empty window at 00:00 and `previous_calendar_day` is the outcome day itself (circular: previous-day glucose against the same day's fluid). Section 14 warns about this for three sleep rows only. The same defect affects the five `hydration_below` rows. **Proposal:** all windows are anchored to the outcome date (day outcomes), the unit start (meal, hour, reading outcomes), and the Evidence Engine never uses `resolved_window` from the packet. 6.1 says "Exposure shift 0" for `fluid_intake_day`: that is right only under this anchoring. For event-time exposure state, the window is anchored at `opened_at` for non-shifted outcomes.

**A4. Anchor of minute windows in the history rows (5, 6.2).** `alcohol_entry@720m->day_min_glucose` (unit start 00:00) has a different window in the history (12:00 to 24:00 the day before) than at event time (12 hours before `opened_at`). **Proposal:** history rows use the unit start; the event record uses `opened_at`; both are stated in `event_exposure`.

**A5. Stamp meaning of the hourly step rows (6.2 `steps_window_hourly`).** Rows are stamped at the hour start (`...T09:00:00`); nothing says whether the value is steps *during* 09:00 to 09:59 or *before* 09:00. The hourly pattern is zero from 00:00 to 05:59 and active from 06:00 to 22:00, which fits "during". If it is "during", a row stamped H:00 is only known at H+1:00, so the ordering rule "recorded at or before unit start" would let a row leak from the unit's own hour. **Proposal:** a row stamped H:00 is available at H+60 min (config `available_at: end_of_hour`), and `steps_window_hourly@60m` for the hour starting at H uses the row stamped H-1:00.

**A6. Meal-unit ordering at unit start (6.1).** `post_meal_peak`'s unit start is "the meal's start". An entry stamped exactly at the start counts ("at or before"). Same for BP. Stated for completeness; no change.

**A7. Look-ahead in late history rows (3.1 rule 2, 7.1).** A dinner at 22:30 on day D-1 has its 150-minute outcome window running to 01:00 on day D, after the as-of start of D. The spec says the refresh gives the same result at 00:00 or lazily. **Proposal:** a meal enters the history only if its whole 150-minute window ended before the as-of start (so a dinner after 21:30 is excluded until the next day). This delays about 20 dinners in the year (those starting after 21:30; they enter the history one day later, none is lost). Same rule for any outcome with a forward window.

### Statistics

**A8. DECISION. Availability of the hourly steps (4.4, 3.1 rule 3).** "Same `available_at` rules as the State Engine (single source: the State Engine config)", but `step_count_hourly` is not a State Engine stream (parked). **Proposal:** the Evidence library config carries its own `available_at: end_of_hour` for this stream; everything else is read from the State Engine config.

**A9. Detrending hour-level and reading-level outcomes (7.1).** "Median of its own previous 30 days, at least 10 values" is clear for day and meal units. For `hr_hour_mean` (8,159 hourly units, strong time-of-day pattern) a 30-day median over all hours leaves the daily cycle in the residual, so any hourly exposure (steps) will correlate with it by the clock alone. **Proposal (a statistical choice, please confirm):** the baseline is the median of the **same clock hour** over the previous 30 days (30 values, at least 10). For `systolic_reading` (141 readings, about one per 2.5 days) the 30-day window holds about 12 values, so the minimum of 10 drops some early rows; no change, noted. For meal units the baseline is the earlier meals **of the same kind** within 30 days.

**A10. Placebo (7.2).** "Rotated by a fixed share (about 30%, derived from the seed)": fixed or seed-jittered? And does the placebo get its own 2,000 rotations? The null distribution of a rotated exposure is the same for the real and the placebo exposure, so the placebo's p-value can be read from the same null. **Proposal:** shift = exactly 30% of the series length (config), placebo p taken from the same null, `placebo.fired` if its unadjusted p is at most 0.10 and its effect is at least the floor (the `suggestive` rule; placebos are not in the family, so "or better" cannot apply).

**A11. Family for Benjamini-Hochberg (7.2).** "All relationships refreshed that day": does the family include relationships that are `insufficient` (they have no p-value)? The section 12 example (5 tests, the 6th is insufficient) says no. **Proposal:** the family is the relationships that passed the minimums; `family_size` records it.

**A12. Overlap (7.2).** Defined per pair (a, b) with an asymmetric `share_given_a`; the example shows one entry for two factors. For n factors: n(n-1)/2 unordered pairs, or n(n-1) ordered? "Days" is not defined for meal, hour and reading units. **Proposal:** both directions are reported only when the flag would differ; the minimum is one entry per unordered pair using the direction with the larger `share_given_a`. "Days" are the outcome dates in the history; a date counts as exposed if any of its units is. Overlap uses the exposure@window only (as in the example's `sleep_hours@prev_night`), not the outcome.

**A13. `small_group` flag (11.3).** Listed among the flags but no rule sets it. **Proposal:** set `small_group` on an `insufficient` label caused by `n_exposed` or `n_reference` below the minimum, so the reason is visible; never on other labels.

**A14. Dependency and determinism of the permutation test (7.2, 13.1).** 63 relationships a day (49 pairs, with the 7 post-meal pairs expanded over three meal kinds) times 352 days times 2,000 shifts, with up to 8,159 units, is far too slow in pure Python. **Proposal:** numpy (declared in `pyproject.toml`), and the shifted effects computed together from ranks. Seeds come from a stable hash (SHA-256 of key, date and version), not Python's salted `hash`. Comparisons "at least as large as the real one" use a small tolerance so float noise cannot change a p-value. Please confirm that adding numpy is acceptable.

**A15. Zero variance and degenerate groups (7.2).** A binary exposure with no spread in the outcome, or a continuous exposure with no spread, has no effect. **Proposal:** label `insufficient`, reason `no_variation`. (The minimums already cover empty groups.)

### Event-level behaviour

**A16. DECISION. The shape check needs data after the event but the event record is written once (7.3, E6, 13.7).** `sensor_artifact` uses a `pm60m` window, so its label is `not_yet_available` until 60 minutes after `opened_at`; "writing the same packet again produces the same record" forbids the record from changing later. In a replay all the data exists already. **Proposal:** the event record is written at `opened_at` with `not_yet_available` and `earliest_evaluation_time`; a `completion` step (a second table row `event_completions`, keyed by `ev_<handoff_id>`) fills the label when the data exists. In the replay the driver calls it right after. Alternative: none (keep `not_yet_available` forever). Five hand-offs are affected on this patient.

**A17. Deferred, unmatched and ambiguous packets (4.1, E1, E3, 13.8).** E1 says a non-normal packet gives "an event record with no factors", but property 8 needs every candidate in `factors` or `not_tested`, and E3 has a `rule_deferred` outcome that E1 makes unreachable. The packets of a deferred rule list their two candidates in `not_selected` with `rule_deferred`. **Proposal:** E1 writes `factors: []` and copies the packet's `skipped` and `not_selected` into `not_tested` (reason copied: `rule_deferred`), so completeness holds; the `rule_deferred` Appendix rows are used only by the load check. An `ambiguous` packet is treated as normal (it has candidates); `unmatched` has none.

**A18. `not_tested` reasons (9.2 vs the packet).** The example shows `not_selected_budget` and `skipped_by_packet`; the packet's reasons are `budget`, `applies_if_not_met`, `no_stream` and `rule_deferred`. **Proposal:** `not_selected` + `budget` becomes `not_selected_budget`; any `skipped` entry becomes `skipped_by_packet` with the packet's own `reason` and `detail` kept; `rule_deferred` stays.

**A19. `rank` in the 9.2 example.** Alcohol is shown as rank 7; the packet's rank is 10 (the example numbers positions). **Proposal:** copy the packet's `rank`, as 4.1 says.

**A20. `event_exposure` for event-level checks (7.4, 9.2).** The example gives `exposed` for `meal_composition`; presence, shape and pattern checks have no stated state. **Proposal:** `percentile_vs_history`: `exposed` if the value is in the worse tail (percentile at least 75, the exposure tail quantile), else `not_exposed`; the other event-level checks have no `event_exposure` (`null`).

**A21. `percentile_vs_history` details (7.3, 9.2).** (1) "Rounded to the meal bucket": the State Engine bucket is 15 minutes, so 62 minutes is bucket 60; the example's field `bucket_minutes: 60` is the rounded elapsed time, not the bucket size. **Proposal:** the field is named `bucket_minutes` as shown but holds the rounded elapsed time, plus `bucket_size` 15. (2) `meal_skipped_or_delayed` compares hours since the last meal with "her history of gaps between meals". A low-glucose event at 04:00 is 8 hours after dinner, which is above almost every meal-to-meal gap, so it would be `supported` for every overnight event; the comparison is not like for like. **Proposal:** compare with her history of "hours since the last meal" sampled at the same clock hour (nearest 15-minute bucket, from the State Engine's usual), mirroring the first check. Please confirm; otherwise I implement the spec literally and report how many of the five lows it labels `supported` merely by being overnight.

**A22. `pattern_repeat` (7.3).** "A glucose rise between 04:00 and 09:00" with `dawn_min_rise` 20: rise = maximum minus minimum in the window, or last minus first? Labels for `dawn_effect` other than `supported`: `insufficient` below 14 days, else `not_supported`. **Proposal:** rise = the highest reading in the window minus the lowest reading before it (a rise, not a drop); labels as stated.

**A23. `presence_check` facts (7.3, 10).** `presence_flags` lives in the evidence config, but the same facts exist in the rulebook config (`medication_classes`, `has_thyroid_condition`). A candidate has several flags (insulin, sulfonylurea). **Proposal:** present = any flag true; the values are copied once into the evidence config, and a load check compares them with the rulebook config's classes (they are static, as the library is). On this patient only `thyroid_status` ever reaches this check (the other three presence candidates are always skipped by the packet).

**A24. Event exposure with partly available windows (6.2, 7.4).** For `missed_dose@2d` at 20:00 today's record is not available until 21:00 while yesterday's is. Not stated whether that is `not_yet_available` or `not_exposed`. **Proposal:** `exposed` if any available record in the window shows a miss; `not_yet_available` if none shows a miss and some record in the window is not yet available; `not_exposed` only if all are available and none missed (this keeps property 13). Same rule for mood blocks.

**A25. Event meal with no meal kind (5, 6.1, 8 D1).** Meal kinds come from the State Engine's label text match (`breakfast`, `lunch`, `dinner`, first contained). 8 of 1,055 meals match none (`snack_1..3`, `festive_snack_1/2`, `pre_dawn_meal`, `moonrise_meal`, `late_night_function_meal`). If a post-meal hand-off's last meal is one of them, no relationship exists. **Proposal:** every relationship factor in that packet is `insufficient` with reason `no_meal_kind`; the event percentile still runs against all meals. Also note `snack_lunch` matches `lunch`.

### Contracts and edge cases

**A26. Where the library's stream names come from (6.2, 4.3).** 6.2 has no "stream" column: which generic stream does each exposure and outcome use, and how do generic names map to this patient's stream names ("through the stream registry" refers to three different registries: the Baseline registry, the Baseline v2 config and the State Engine config)? **Proposal:** the library config carries a generic `source` token per exposure and outcome; a patient config block `stream_map` maps tokens to store names (same shape as the Rulebook Lookup's), and a stream absent from it gives `insufficient` / `no_stream` (4.3).

**A27. Duplicate resting heart rate (6.1).** `resting_heart_rate` has 353 rows for 352 days; 2026-04-06 has two. Which is "the day's resting heart rate value"? **Proposal:** the last one of the day (config: `first|last`), reported.

**A28. Smaller points.** (a) Property 16 does not check the key's lookback tag against the rulebook's lookback kind and value. All 49 match today; I will add that check (with the two documented deviations: the sleep shift and `excludes_outcome_day`). (b) 4.4 says the home and clinic location types come from a "patient location config" but section 10 puts them in the evidence config; they go in the evidence config (no other file has them). (c) The example's `history_n: 346` for dinners is the count of `dinner` plus `light_dinner` labels; the State Engine's text match also takes `festive_dinner` and `late_dinner` (350 in the year), so my history_n will differ slightly. (d) 4.2 lists "the missed medicines" from the hand-off; the hand-off holds them twice (`value.missed` as ids, `context.medication.missed` as names) and the store holds the records. **Proposal:** the event state is computed from the store under the availability rules; the hand-off is used only for `last_meal`, `measure`, `direction` and `opened_at`.

---

## (b) [verify] items against the real store and code

| Item | Found | Differs from the spec? |
|---|---|---|
| Glucose | `raw_events.biomarker = cgm_glucose_reading`, 15-minute rows. The Baseline cleaning is `baseline_v2.trust.clean_series(series, cfg)` (device range 40 to 400, jump rule scaled by the gap); the State Engine already reuses it. | No |
| Continuous heart rate | `context_events.stream = continuous_heart_rate`, 33,792 rows | No (it is in `context_events`, not `raw_events`) |
| Hourly steps | `context_events.stream = step_count_hourly`, 8,160 rows, 340 days, `value_num`, stamped at the hour start, zero from 00:00 to 05:59; 12 days have no rows | New: stamp meaning and availability are not defined anywhere (A5, A8) |
| Daily steps | `raw_events.step_count`, date-only (10-character timestamps), 340 rows | No |
| Sleep | `raw_events.sleep_duration`, 352 rows, always stamped 07:00 (the wake time) | The 07:00 stamp conflicts with `ordered` on day outcomes (A2) |
| Resting heart rate | `raw_events.resting_heart_rate`, 353 rows, stamped 07:00 to 18:30 | One duplicate day (A27) |
| Medicine records | `context_events.medication_adherence`, 1,056 rows, **date-only**, `value_text` taken/missed, `category` = medicine id (`med_002_metformin`, `med_003_amlodipine`, `med_004_levothyroxine`; the Baseline regex strips the prefix to the names) | No |
| Mood | `context_events.mood_state`, `category` = the mood category, block in `meta_json.time_block` (morning, afternoon, evening) | No |
| **State Engine `available_at`** | `mood_state`: `{morning: "12:00", afternoon: "18:00", evening: "21:00"}`; `medication_adherence`: `"21:00"`; `diary_context`: `"21:00"` only as the fallback for untimed entries (all 129 have a timestamp); `sleep_duration`, `resting_heart_rate`, `blood_pressure`: `timestamp`; `step_count`, `hydration`, `screen_time`: `end_of_day` | Hourly steps absent (A8). The morning block ends at 12:00, so no breakfast (about 08:00) and no BP reading (08:00 to 08:30) can ever see a block of its own day |
| **Meal-kind matching** | State Engine `meal_kinds: [breakfast, lunch, dinner]`, first one contained in the label text. Of 1,055 meals: breakfast 347, lunch 350, dinner 350 (including `light_dinner` 30, `festive_dinner` 3, `late_dinner` 1), 8 match none. `meal_bucket_minutes` 15, `meal_window_minutes` 180 | The 9.2 example's 346 dinners is exact `dinner` plus `light_dinner` only (A28c); 8 kind-less meals (A25) |
| Meals | `context_events.meal_events`, timestamped, kind text in `category`, food text in `value_text` | No |
| Diary | `context_events.diary_context`, 129 entries, **all timestamped** (05:00 to 23:45). Categories: life_event 69, social_interaction 22, symptom 17, healthcare_interaction 5, substance_use 6, environment 4, allergy 2, habits 2, travel 2 | Text is never read, as required. Alcohol 6, environment 4, travel 2 are tiny (section 14 agrees) |
| Location | `context_events.location`, date-only `value_text`: home 84, home_wfh 123, office 95, mall 19, hospital 9, clinic 8, school 4, wedding_venue 3, airport_travel 2, other_city 2, family_home 1, cafe 1, public_event 1 | Config types `home, home_wfh, family_home` and `clinic, hospital` all exist. 17 clinic-type days only |
| Hydration, screen time | `raw_events`, date-only, 352 rows each | No |
| Blood pressure | `raw_events.blood_pressure_systolic`, 141 readings, stamped 08:00 to 08:30 | Readings are always in the morning (A1) |
| Hand-off fields | `handoff_id, measure, direction, opened_at, context.last_meal {label, time, minutes_ago}` as the spec uses; `last_meal` is never null in this data | No |
| Packet fields | `packet_id, handoff_id, status` (absent on a normal packet; `deferred`, `unmatched`, `ambiguous` otherwise), `matched_rule.rule_id`, `selected[].{candidate, rank, weight_tier, check_type, lookback.{kind,value}}`, `skipped[].{candidate, reason, detail}`, `not_selected[].{candidate, weight_tier, reason}` | No (reasons differ from 9.2: A18) |
| Medicine names | As above; the rulebook config also lists `metformin`, `amlodipine`, `levothyroxine` | No |
| Where config lives | strain categories `tired_low_energy, mild_stress, anxious, overwhelmed_high_distress` and the medicine pattern are in the Baseline config `patient:` block; timezone `Asia/Kolkata` there too | No |
| numpy / scipy | numpy 2.5.3 installed, not in `pyproject.toml`; scipy absent | A14 |

---

## (c) Appendix A against the rulebook candidates CSV

Run mechanically over the 69 rows of Appendix A and the 69 rows of `rulebook_v0_candidates.csv`:

- Every rulebook row has a pair row and every pair row has a rulebook row (matched on rule and rank): **0 missing either way.**
- Same candidate name, same tier and same check type on all 69: **0 mismatches.**
- Rows per rule agree. The only deferred rule is `screen_time_above`, and exactly its two rows are `rule_deferred`.
- Status counts: runnable 49, event_level 11, no_definition 7, rule_deferred 2. All 49 runnable keys are distinct templates and none is missing; no non-runnable row has a key. `Ordering`: 30 ordered, 18 `same_day_unverified`, 1 `excludes_outcome_day`, as stated.
- Key consistency: for every runnable row the exposure and outcome in the key equal the columns, `{meal_kind}` appears exactly on the `post_meal_peak` rows, and **the lookback tag in the key equals the rulebook's own lookback on all 49** (`2d`, `1d`, `3d`, `7d`, `720m`, `60m`, `prev_night`, `prev_day`, `prev_evening`, `same_day`, `at_open`).
- Every exposure in 6.2 (16) and every outcome in 6.1 (10) is used by at least one runnable pair; nothing is orphaned.

Things I think are wrong or cannot be defined as the library stands (details in section (a)):

1. The ordering labels in four `sleep_hours@prev_night` rows on day outcomes, and ten mood-block / diary rows on day outcomes (A1, A2).
2. `strained_period@same_day->systolic_reading` is `ordered` in the Appendix, but no block of the day has ended by a morning BP reading (A1).
3. The five `hydration_below` rows and the three `sleep_below` rows have rulebook windows anchored to an `opened_at` that is on the wrong day (A3). Rulebook rows should be corrected later, as section 14 says for sleep; Evidence ignores them.
4. `late_meal` and `late_prior_dinner` use a 75th percentile of start times of the same kind. All kind-matched meals start between 05:00 and 23:00, so no overnight rule is needed; the one meal after 23:00 (`late_night_function_meal`, 23:22) has no kind and is not used.
5. Exposure definitions that cannot be computed meaningfully on this patient (not wrong, but they will never reach the minimums): see the table in (d).
6. `prior_day_glucose_mean` in `hydration_below`: the "previous day" must be the day before the outcome date, i.e. two days before `opened_at` (A3).

---

## (d) The 49 runnable pairs: can each be computed today?

**Computable today from the store:** all 49 (every stream exists; hourly steps need the availability rule of A8). No pair needs a stream the store lacks.

"Usable" is the number of history units with an exposure value at year end (not detrended; the detrending drops the first 10 or so). `exp|ref` are exposed and reference units for binary exposures. "Minimums first met" is the first date with at least 60 usable units, 15 exposed and 30 reference units (continuous: 60 usable). Post-meal rows show breakfast/lunch/dinner. The literal reading of rule 5 (A1) is used, so the "dead" rows are the ones decision A1 would revive.

| Rule rank | Candidate | Key | Ordering | Usable | exp|ref (binary) | Minimums first met | Note |
|---|---|---|---|---|---|---|---|
| `glucose_above_post_meal` 2 | medication_adherence | `missed_dose@2d->post_meal_peak:{kind}` | same_day_unverified | 347/350/350 | 250|97/252|98/252|98 | 2026-02-19/2026-02-19/2026-02-19 |  |
| `glucose_above_post_meal` 3 | sleep | `sleep_hours@prev_night->post_meal_peak:{kind}` | ordered | 347/350/350 | continuous | 2025-12-02/2025-11-30/2025-11-30 |  |
| `glucose_above_post_meal` 4 | stress_mood | `strained_period@1d->post_meal_peak:{kind}` | ordered | 0/350/350 | 0|0/33|317/45|305 | never/2026-03-09/2026-01-06 | breakfast scope dead (no mood block has ended before breakfast) |
| `glucose_above_post_meal` 5 | activity | `steps_total@1d->post_meal_peak:{kind}` | same_day_unverified | 335/338/338 | continuous | 2025-12-04/2025-12-02/2025-12-02 |  |
| `glucose_above_post_meal` 6 | illness_symptoms | `symptom_entry@3d->post_meal_peak:{kind}` | ordered | 347/350/350 | 30|317/34|316/36|314 | 2026-02-10/2026-02-08/2026-01-09 |  |
| `glucose_above_post_meal` 7 | meal_timing | `late_meal@same_day->post_meal_peak:{kind}` | ordered | 347/350/350 | 93|254/92|258/96|254 | 2025-12-02/2025-11-30/2025-11-30 |  |
| `glucose_above_post_meal` 10 | alcohol | `alcohol_entry@1d->post_meal_peak:{kind}` | ordered | 347/350/350 | 0|347/0|350/3|347 | never/never/never | never meets minimums on this patient |
| `glucose_above_no_recent_meal` 1 | medication_adherence | `missed_dose@2d->non_meal_mean` | same_day_unverified | 352 | 254|98 | 2026-02-19 |  |
| `glucose_above_no_recent_meal` 2 | illness_symptoms | `symptom_entry@3d->non_meal_mean` | same_day_unverified | 352 | 28|324 | 2026-02-10 |  |
| `glucose_above_no_recent_meal` 3 | stress_mood | `strained_period@1d->non_meal_mean` | same_day_unverified | 0 | 0|0 | never | DEAD: no unit has a block ended before its start |
| `glucose_above_no_recent_meal` 4 | sleep | `sleep_hours@prev_night->non_meal_mean` | ordered | 351 | continuous | 2025-11-30 | sleep stamp 07:00 is after the 00:00 unit start: literal rule uses the record two nights back |
| `glucose_above_no_recent_meal` 5 | activity | `steps_total@prev_day->non_meal_mean` | ordered | 339 | continuous | 2025-12-02 |  |
| `glucose_above_no_recent_meal` 6 | prior_evening_meal | `late_prior_dinner@prev_evening->non_meal_mean` | ordered | 349 | 95|254 | 2025-12-01 |  |
| `glucose_below` 3 | unusual_activity | `high_steps_day@1d->day_min_glucose` | same_day_unverified | 340 | 85|255 | 2025-12-01 |  |
| `glucose_below` 4 | alcohol | `alcohol_entry@720m->day_min_glucose` | ordered | 352 | 6|346 | never | never meets minimums on this patient |
| `glucose_below` 6 | illness_poor_intake | `symptom_entry@1d->day_min_glucose` | same_day_unverified | 352 | 0|352 | never | DEAD: zero exposed units (same-date entries excluded by rule 5) |
| `heart_rate_above` 1 | activity | `steps_window_hourly@60m->hr_hour_mean` | ordered | 8159 | continuous | 2025-10-03 |  |
| `heart_rate_above` 2 | stress_mood | `strained_period@same_day->hr_day_mean` | same_day_unverified | 0 | 0|0 | never | DEAD: no unit has a block ended before its start |
| `heart_rate_above` 3 | illness_fever | `symptom_entry@3d->hr_day_mean` | same_day_unverified | 352 | 28|324 | 2026-02-10 |  |
| `heart_rate_above` 4 | hydration | `hydration_total@prev_day->hr_day_mean` | ordered | 351 | continuous | 2025-11-30 |  |
| `heart_rate_above` 6 | sleep | `sleep_hours@prev_night->hr_day_mean` | ordered | 351 | continuous | 2025-11-30 | sleep stamp 07:00 is after the 00:00 unit start: literal rule uses the record two nights back |
| `heart_rate_above` 7 | alcohol | `alcohol_entry@720m->hr_day_mean` | ordered | 352 | 6|346 | never | never meets minimums on this patient |
| `resting_heart_rate_above` 1 | sleep | `sleep_hours@prev_night->resting_hr_day` | ordered | 351 | continuous | 2025-11-30 | sleep stamp 07:00 is after the 00:00 unit start: literal rule uses the record two nights back |
| `resting_heart_rate_above` 2 | illness_fever | `symptom_entry@3d->resting_hr_day` | same_day_unverified | 352 | 28|324 | 2026-02-10 |  |
| `resting_heart_rate_above` 3 | stress_mood | `strained_period@prev_day->resting_hr_day` | ordered | 351 | 47|304 | 2025-11-30 |  |
| `resting_heart_rate_above` 4 | hydration | `hydration_total@prev_day->resting_hr_day` | ordered | 351 | continuous | 2025-11-30 |  |
| `resting_heart_rate_above` 5 | alcohol | `alcohol_entry@prev_evening->resting_hr_day` | ordered | 352 | 5|347 | never | never meets minimums on this patient |
| `sleep_below` 1 | stress_mood | `strained_period@same_day->sleep_hours_night` | ordered | 351 | 47|304 | 2025-11-30 |  |
| `sleep_below` 2 | meal_timing | `late_prior_dinner@prev_evening->sleep_hours_night` | ordered | 349 | 95|254 | 2025-12-01 |  |
| `sleep_below` 3 | alcohol_caffeine | `alcohol_entry@prev_evening->sleep_hours_night` | ordered | 352 | 5|347 | never | never meets minimums on this patient |
| `sleep_below` 4 | screen_time | `screen_hours@prev_evening->sleep_hours_night` | ordered | 351 | continuous | 2025-11-30 |  |
| `sleep_below` 5 | illness_symptoms | `symptom_entry@same_day->sleep_hours_night` | ordered | 352 | 17|335 | 2026-06-17 |  |
| `sleep_below` 6 | travel_environment | `non_home_day@same_day->sleep_hours_night` | ordered | 351 | 143|208 | 2025-11-30 |  |
| `medication_adherence_below` 1 | routine_disruption | `non_home_day@same_day->missed_doses_day` | same_day_unverified | 352 | 144|208 | 2025-11-29 |  |
| `medication_adherence_below` 2 | stress_mood | `strained_period@same_day->missed_doses_day` | same_day_unverified | 0 | 0|0 | never | DEAD: no unit has a block ended before its start |
| `medication_adherence_below` 3 | illness_symptoms | `symptom_entry@same_day->missed_doses_day` | same_day_unverified | 352 | 0|352 | never | DEAD: zero exposed units (same-date entries excluded by rule 5) |
| `medication_adherence_below` 4 | recent_adherence_pattern | `missed_dose@7d->missed_doses_day` | excludes_outcome_day | 352 | 347|5 | never | never meets minimums on this patient |
| `medication_adherence_below` 5 | sleep_prior_night | `sleep_hours@prev_night->missed_doses_day` | ordered | 351 | continuous | 2025-11-30 | sleep stamp 07:00 is after the 00:00 unit start: literal rule uses the record two nights back |
| `blood_pressure_above` 1 | medication_adherence | `missed_dose@2d->systolic_reading` | same_day_unverified | 141 | 102|39 | 2026-07-01 |  |
| `blood_pressure_above` 2 | measurement_context | `clinic_reading@at_open->systolic_reading` | same_day_unverified | 141 | 11|130 | never | never meets minimums on this patient |
| `blood_pressure_above` 3 | stress_mood | `strained_period@same_day->systolic_reading` | ordered | 0 | 0|0 | never | DEAD: no unit has a block ended before its start |
| `blood_pressure_above` 4 | sleep | `sleep_hours@prev_night->systolic_reading` | ordered | 141 | continuous | 2026-03-01 |  |
| `blood_pressure_above` 6 | alcohol_caffeine | `alcohol_entry@720m->systolic_reading` | ordered | 141 | 4|137 | never | never meets minimums on this patient |
| `blood_pressure_above` 7 | pain_or_illness | `symptom_entry@same_day->systolic_reading` | ordered | 141 | 4|137 | never | never meets minimums on this patient |
| `hydration_below` 1 | illness_symptoms | `symptom_entry@same_day->fluid_intake_day` | same_day_unverified | 351 | 0|351 | never | DEAD: zero exposed units (same-date entries excluded by rule 5) |
| `hydration_below` 2 | busy_routine | `non_home_day@same_day->fluid_intake_day` | same_day_unverified | 351 | 143|208 | 2025-11-29 |  |
| `hydration_below` 3 | high_prior_glucose | `prior_day_glucose_mean@prev_day->fluid_intake_day` | ordered | 350 | continuous | 2025-11-30 |  |
| `hydration_below` 4 | weather_environment | `environment_entry@same_day->fluid_intake_day` | same_day_unverified | 351 | 0|351 | never | DEAD: zero exposed units (same-date entries excluded by rule 5) |
| `hydration_below` 5 | alcohol | `alcohol_entry@prev_evening->fluid_intake_day` | ordered | 351 | 5|346 | never | never meets minimums on this patient |
Counts of "dead" and "never meets minimums" (literal rule 5):

- **Dead as written (8 pairs, 0 usable or 0 exposed units): `strained_period@1d->non_meal_mean`, `strained_period@same_day->hr_day_mean`, `strained_period@same_day->missed_doses_day`, `strained_period@same_day->systolic_reading`, `symptom_entry@1d->day_min_glucose`, `symptom_entry@same_day->missed_doses_day`, `symptom_entry@same_day->fluid_intake_day`, `environment_entry@same_day->fluid_intake_day`.** All are the A1 problem. Under proposal A1(ii) they run; whether they ever reach the minimums I will report in Step 3 (for example `strained_period` has 33 to 47 exposed units, so most would; `symptom_entry@same_day` for fluid and glucose has at most 17 exposed days, so they would reach 15 only late).
- **Never reach the minimums on this patient (10 pairs, as expected from section 14):** all seven `alcohol_entry` pairs (at most 6 exposed days in the year), `missed_dose@7d->missed_doses_day` (only 5 reference days with no miss in the preceding week), `clinic_reading@at_open->systolic_reading` (11 exposed readings), `symptom_entry@same_day->systolic_reading` (4). They will be `insufficient` all year, which is a result of the data.
- **Late to mature:** `missed_dose@2d->*` needs until February (its reference group of days with no miss in two days is small, 97 to 98 units of 350); `missed_dose@2d->systolic_reading` only reaches the minimums in July; `symptom_entry@same_day->sleep_hours_night` (17 exposed days) in mid-June; most others in December to February. October to November is `insufficient` almost everywhere (60 usable units after detrending take about two months).

## Other facts the build will rely on

- All 8,159 hourly heart-rate units have a hourly step row for the previous hour; 12 days have none and drop out.
- `post_meal_peak` units: breakfast 347, lunch 350, dinner 350 (State Engine kind matching).
- BP has 141 readings, so with the 60-unit minimum and the detrending the BP pairs only start in March at the earliest.

---

## (e) Proposed config format for the library

Two files, because the library is the same for every patient and only the patient settings differ:

1. **`config/evidence_library_v0.yaml`** (static, patient-independent, derived from sections 6.1, 6.2 and Appendix A; carries its own `library_version`; changes only when the rulebook changes or someone edits it on purpose).
2. **`config/evidence_meera_iyer_v1.yaml`** (patient config: the `evidence:` block of section 10, plus `rulebook_dir`, paths, `stream_map`, location types, presence facts; it names the State Engine and Baseline configs it reads, as the Rulebook Lookup config does).

The engine contains a fixed set of **generic primitives** (named below); the library chooses one per exposure and outcome and passes parameters. No stream, measure or medicine name is in the engine. Streams are generic tokens in the library and are mapped to the patient's store names by `stream_map` in the patient config.

```yaml
# config/evidence_library_v0.yaml
library_version: lib-v0
lookback_tags:                      # rulebook lookback kind -> tag used in keys
  minutes_before_open: "{value}m"
  days_ending_at_open: "{value}d"
  previous_night: prev_night
  previous_calendar_day: prev_day
  previous_evening: prev_evening
  same_calendar_day: same_day
  at_open: at_open
  minutes_around_open: "pm{value}m"

outcomes:                           # section 6.1, one entry each
  post_meal_peak:
    unit: meal
    unit_start: meal_start
    source: glucose                 # generic token; cleaned glucose
    primitive: max_in_window_after_event    # a generic primitive of the engine
    params: {window_minutes: 150}
    scope: meal_kind                # relationship key gets ":<kind>"
    worse_is: higher
    outcome_date: opened_date
    exposure_shift_days: 0
  sleep_hours_night:
    unit: day
    unit_start: day_start
    source: sleep
    primitive: value_of_dated_record
    worse_is: lower
    outcome_date: opened_date
    exposure_shift_days: -1         # applies to same_day, 1d, 2d, 3d
  fluid_intake_day:
    unit: day
    unit_start: day_start
    source: hydration
    primitive: value_of_dated_record
    worse_is: lower
    outcome_date: opened_date_minus_1
    exposure_shift_days: 0
  # non_meal_mean, day_min_glucose, hr_hour_mean, hr_day_mean, resting_hr_day, missed_doses_day, systolic_reading ...

exposures:                          # section 6.2, one entry each
  missed_dose:
    form: binary
    risk_side: exposed
    resolution: date                # date | timestamp | block
    source: medication_adherence
    primitive: any_in_window        # binary: at least one matching record in the window
    params: {value_equals: missed}
    event_state: {availability: [date_record_available_at]}
  sleep_hours:
    form: continuous
    risk_side: low
    resolution: timestamp
    source: sleep
    primitive: value_in_window
  strained_period:
    form: binary
    risk_side: exposed
    resolution: block
    source: mood_state
    primitive: any_in_window
    params: {category_in: patient.strain_categories, block_ends_by_unit_start: true}
  symptom_entry:
    form: binary
    risk_side: exposed
    resolution: timestamp
    source: {token: diary_context, category: symptom}
    primitive: any_in_window
  late_meal:
    form: binary
    risk_side: exposed
    resolution: timestamp
    source: meal_events
    primitive: start_time_at_or_above_quantile
    params: {quantile: 0.75, same_kind: true, event: meal | previous_evening_dinner}
  # ... 16 exposures in all

event_checks:                       # section 7.3: the generic check types and what each measures
  meal_composition:   {type: percentile_vs_history, measure: peak_after_event_at_elapsed, source: glucose}
  meal_skipped_or_delayed: {type: percentile_vs_history, measure: hours_since_last_meal, source: meal_events}
  sensor_artifact:    {type: shape_check, source: glucose, window: pm60m}
  dawn_effect:        {type: pattern_repeat, measure: morning_rise, source: glucose}
  regimen_factors:    {type: pattern_repeat, measure: miss_rate_per_medicine, source: medication_adherence}
  thyroid_status:     {type: presence_check, facts: thyroid_status}     # facts come from the patient config
  # other_medications, hypoglycemic_agent

pairs:                              # Appendix A, one entry per rulebook candidate (69), in Appendix order
  - {rule: glucose_above_post_meal, rank: 1, tier: primary,   candidate: meal_composition,      check_type: percentile_vs_history, status: event_level, event_check: meal_composition}
  - {rule: glucose_above_post_meal, rank: 2, tier: secondary, candidate: medication_adherence,  check_type: group_comparison, status: runnable,
     exposure: missed_dose, outcome: post_meal_peak, key: "missed_dose@2d->post_meal_peak:{meal_kind}", ordering: same_day_unverified}
  - {rule: glucose_above_post_meal, rank: 9, tier: tertiary,  candidate: cycle_phase,           check_type: group_comparison, status: no_definition, reason: no_stream}
  - {rule: screen_time_above,       rank: 1, tier: secondary, candidate: workload_events,       check_type: group_comparison, status: rule_deferred}
  # ... 69 rows
```

```yaml
# config/evidence_meera_iyer_v1.yaml
evidence:
  state_config: config/state_meera_iyer_v1.yaml        # available_at per stream and block, meal kinds, bucket minutes, timezone
  baseline_config: config/patient_meera_iyer_v1.yaml   # strain categories, glucose cleaning rule
  rulebook_dir: task/evidence_engine                   # read only for the load check (property 16)
  library: config/evidence_library_v0.yaml
  db_path: output/evidence_engine.db
  packets_db: output/rulebook_lookup.db
  handoffs_db: output/state_engine.db
  store_db: output/personal_data_store.db
  stream_map:                                          # generic token -> store stream; null = no stream (insufficient / no_stream)
    glucose: {table: raw, name: cgm_glucose_reading}
    heart_rate: {table: context, name: continuous_heart_rate}
    steps_hourly: {table: context, name: step_count_hourly, available_at: end_of_hour}   # not a State Engine measure (A8)
    steps_daily: {table: raw, name: step_count}
    sleep: {table: raw, name: sleep_duration}
    medication_adherence: {table: context, name: medication_adherence}
    mood_state: {table: context, name: mood_state, block_key: time_block}
    meal_events: {table: context, name: meal_events}
    diary_context: {table: context, name: diary_context}
    location: {table: context, name: location}
    hydration: {table: raw, name: hydration}
    screen_time: {table: raw, name: screen_time}
    blood_pressure_systolic: {table: raw, name: blood_pressure_systolic}
    resting_heart_rate: {table: raw, name: resting_heart_rate, duplicate_day: last}
    caffeine_intake: null
    menstrual_cycle: null
  # method_version, history, min_exposed, min_reference, permutation, multiplicity, labels, placebo, overlap,
  # event_exposure, percentile_check, shape_check, pattern_repeat, location, presence_flags: exactly as in section 10
```

**The generic primitives** the engine implements (a fixed list, named by function, never by stream): `value_of_dated_record`, `value_in_window`, `any_in_window`, `mean_in_window`, `min_in_window`, `max_in_window_after_event`, `mean_of_readings_outside_event_windows`, `count_of_matching_records`, `start_time_at_or_above_quantile`, `value_at_or_above_quantile`. An outcome or exposure that needs something not in this list is a code change, not a config change; the 10 outcomes and 16 exposures need these 10.

**What the load check (property 16) covers**, in addition to the spec's list: every `primitive` exists; every `source` token is in the map or declared null; every `scope` and `{meal_kind}` use agrees; each key's lookback tag equals the tag derived from the rulebook's lookback (except the documented shift and `excludes_outcome_day`); the `presence_flags` agree with the rulebook config's medicine classes; the `Ordering` of every row is consistent with the rule that derives it from the exposure's `resolution`, the unit start and the window (so A1 and A2 cannot drift silently).

---

## Decisions I need before Step 2

1. **A1** Same-date timestamped entries and mood blocks on day-level outcomes: count them and flag `same_day_unverified` (my proposal), or exclude them (literal rule 5, which kills 8 pairs)?
2. **A2** `sleep_hours@prev_night` on day-level outcomes: the record dated the outcome date, flagged `same_day_unverified` (my proposal, so the Appendix `Ordering` of 4 rows changes from `ordered`), or literally two nights back?
3. **A3** Windows anchored to the outcome date / unit start, never `opened_at`, for all rules (my proposal).
4. **A8** Hourly steps: a library-level `available_at: end_of_hour`, and the row stamped H-1:00 is the exposure for the hour starting H.
5. **A9** Hourly outcome detrended against the same clock hour of the previous 30 days.
6. **A14** Add numpy to `pyproject.toml`.
7. **A16** Shape-check completion as a separate completion row written when the data exists (my proposal), or never completed.
8. **A21** `meal_skipped_or_delayed`: compare with hours-since-last-meal at the same clock hour (my proposal) or the spec's literal history of gaps.
9. Everything else listed as "Proposal" (A4-A7, A10-A13, A15, A17-A20, A22-A28): accept as written, or name the ones to change.

Parked, not acted on: correcting the rulebook's sleep and hydration lookbacks, ingesting the cycle file and TSH, the ground-truth manifest.
