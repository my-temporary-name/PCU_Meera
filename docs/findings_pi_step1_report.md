# Findings Engine and PI: Step 1 report (read-only)

Nothing was built, changed or committed. The Evidence Engine, Rulebook and State Engine are untouched; every database was opened read-only. The specs are `task/finding_engine_spec.md` (note the file name: the overview and the PI spec refer to `findings_engine_spec.md`), `task/pi_spec.md` and the updated `task/intelligence_layer_overview.md`; all three are already in `task/`, so there was nothing to copy.

## Summary

- **The case count does not match the spec's rule.** The spec says 119 cases at a 6-hour gap. That number counts the 8 deferred screen-time hand-offs as ordinary hand-offs. The spec's own rule 5.1 (a deferred hand-off never opens a case) gives **116**. At 3 and 12 hours the same two readings give 181 / 176 and 85 / 84. See (f).
- **Four things in the specs contradict each other or the data** and need your decision before F1: the mode rule against the hospitalization example (7.2 vs example B); "the closing version is marked final" against append-only versions (5.4 / 5.6 vs 13.9); the 119 above; and the PI worked example (a Sunday 20 September weekly label, back-fill) against data that ends on 17 September and against the back-fill rule (PI 6.3 vs 13).
- **The `[verify]` items mostly hold**, with different names: the gist headline is the column `gist_headline` (the parsed key is `gist.headline`); the diary description is `value_text` and the severity note is `meta_json.note`; there is no timezone key in either new config, it comes from `patient.timezone` of the baseline config. 25 of the 29 early state-memory headlines contain digits, dates and quoted diary text, so they cannot go into a numberless view as they are.
- **A full phrase book is drafted** (c): 16 exposures, 10 outcomes, 11 window tags (one is missing from the spec's A.3), 8 event-level candidates, plus three tables the spec uses but never defines (hand-off measures, meal-label wording, elapsed-time wording). All 49 pairs render to plain sentences; the one automatic problem is the spec's own `3d` window phrase, which contains the counting word "two".
- **The code-only stages (F1, P1, the driver, the text-layer checks) can all be tested without a model.** The second synthetic patient needs its own phrase book; details in (e).
- **F1 needs a small event-ordering loop** although the spec puts the replay driver in P1. I propose a minimal one inside F1 that P1 later replaces.

## (a) Ambiguities and contradictions

"FE" = `finding_engine_spec.md`, "PI" = `pi_spec.md`, "EV" = `evidence_engine_spec.md`, "OV" = the overview. **DECISION** marks the ones I cannot choose for you; the rest carry a proposal I will follow unless you say otherwise.

### Findings Engine, internal

1. **File name (FE header, PI 0, OV 0).** The files are `finding_engine_spec.md`; every cross-reference says `findings_engine_spec.md`. Proposal: leave the file, treat the reference as the same document, fix the references when convenient.
2. **DECISION. Deferred hand-offs and the 119 (FE 5.1, 5).** Rule 5.1 says a `deferred` or `unmatched` hand-off never opens a case but joins an open one. On the real data that gives **116** cases at a 6-hour gap; 119 is what you get if the 8 deferred screen-time hand-offs (all at 00:00 on their day) are ordinary hand-offs (three of them open cases of their own with no factors). 181 and 85 reproduce the same way. Also unstated: does a deferred hand-off that joins a case extend its last-hand-off time (116 either way here). Proposal: follow rule 5.1 (116) and record the deferred hand-offs in `case_handoffs` without extending the gap clock; change the "119" in FE 5 and OV 15 to 116. The alternative (119) creates three cases that can only say "nothing to report".
3. **DECISION. Closing and immutability (FE 5.4, 5.5, 5.6, 9.1, 13.9).** "Every version is provisional until the case closes; the closing version, or the last version marked closed, is final" cannot hold with "a version never changes after it is written": the closing is known only when the next event is processed, after the last version was written. Proposal: stored versions keep `provisional`/`closed` as they were at writing time; the close is recorded in `cases.closed_at`/`status`; a reader asks the `cases` table whether a version is the final one. A closing version is written only if something in the record changes at close (nothing does in the code layer). The alternative is one extra "closing" version per case (+116 versions).
4. **Versions for hand-offs without factors (FE 5.4).** A joining hand-off whose packet is deferred, or an event record with no factors, would write an identical version. Proposal: no new version unless the structured layer changes.
5. **Completions: time and ids (FE 5.4, 6, 9.1).** The completion table has no time; the evaluation time is `evaluated_from.end` (= the event's `earliest_evaluation_time`), and `completion_ids` has no defined format. Proposal: version `as_of` = that time; `completion_id` = `<evidence_id>#<candidate>`. In replay completions are ordered with hand-offs by time (ties: hand-offs first).
6. **Factor identity for event-level checks (FE 7.1).** A factor is "candidate plus relationship_key (null for event-level)". Two glucose hand-offs of one case each carry a `meal_composition` (different meals, different positions); heart-rate and resting-heart-rate packets each carry `thyroid_status`. Merging them loses a meal. Proposal: relationship factors merge by key; presence checks merge by candidate; percentile, shape and pattern checks stay one factor per hand-off (the factor then lists its hand-off, and "a factor never appears twice" means "per key or per event").
7. **Merging exposure states (FE 7.1).** Order is given for `exposed`, `not_yet_available`, `not_exposed`; `no_data` "stays no_data" is ambiguous when another hand-off says `not_exposed`. Proposal: exposed > not_yet_available > not_exposed > no_data.
8. **DECISION. Mode and event-level checks (FE 7.2 vs example B vs Appendix C).** 7.2 counts a supported, exposed event-level check as usable, so a case whose only usable item is a meal percentile is `relationship` mode. Example B (the hospitalization case) says `descriptive` and lists no `meal_composition`, but the real 15:15 glucose hand-off of 2025-11-18 has `meal_composition` `supported` and `exposed`. Appendix C also has a third template, "event-level only", which neither mode uses. Proposal: `relationship` requires at least one usable **relationship** factor that is exposed and carries a claim class; an event-level statement is added in either mode; the "event-level only" template is the descriptive template when the only content is event-level. Example B then needs the meal line.
9. **Wording-class table gaps and precedence (FE 7.3).** The rows overlap (the `placebo_fired` row says "any exposure", which also covers `not_exposed` and `not_yet_available`), and some cases have no row: `not_supported` with `not_exposed`; label `not_applicable` (presence and pattern checks, including a presence fact that is false); event-level `not_supported` and `insufficient`; `dawn_effect` supported; `insufficient` with the reasons `no_stream`, `no_variation`, `no_ordered_exposure`, `no_definition`, `no_meal_kind`, `no_meal`, `no_readings`, `no_relationship`. Proposal (to be written into the config and the load check): apply, in this order: (1) exposure `not_yet_available` gives `not_known_yet`; (2) `not_exposed` or `no_data` gives `not_mentioned`; (3) relationship factors by label as in the table, with `placebo_fired` before `contrary` before the plain rows; (4) event-level: percentile `supported` gives `event_unusual`, shape `supported` gives `artifact_note`, presence gives `exposure_only` only if present is true, pattern `supported` gives `exposure_only`, everything else gives `not_mentioned`. The library's `reason` field decides `exposure_only_history` (reasons `history`, `small_group`).
10. **`contrary_note` needs a sentence per outcome (FE 7.3, A.2).** "On days like this her X has tended to be lower" needs the outcome's base noun, not the "higher ..." phrase of A.2. The draft in (c) adds a `contrary` phrase to every outcome.
11. **Groups (FE 7.4).** (a) Several entangled sets can exist; proposal: connected components, each a group. (b) Overlap entries name `a`/`b` as `exposure@window` (EV 7.2) and are per hand-off record; mapping to factors is by that prefix within the same hand-off's record. (c) "Usable, exposed" would include the event-level meal percentile, but example A leaves it out of `g1`. Proposal: groups contain only relationship factors whose class carries a claim (asserted, asserted_same_day, hedged, hedged_same_day); `exposure_only` factors with a usable label (placebo fired) are not members. (d) Groups across several hand-offs of a case: overlap flags are the union.
12. **Position words (FE 7.5).** Band edges are not closed on both sides (0 to 5 and 5 to 25). Proposal: lower edge inclusive, upper exclusive, the last band closed at 100. The risk side comes from the Evidence library (`risk_side`; the percentile checks use `worse`), so the library must be an input of Findings (FE 6 does not list it). Binarized exposures (very active day, late meal) carry no percentile and get no position words. The event percentile's position needs a suffix ("in the first hour after dinners", example A) that the phrase book does not supply; the draft adds one built from the elapsed bucket in words.
13. **DECISION. Repeat information (FE 7.6, PI 9).** (a) `this_week` is "last seen within 7 days" (a rolling 7), while PI calls its mid-term memory "this week" (a calendar week). (b) `get_seen_before` must see the open week, because a relationship first used on Tuesday has no long-term memory until Sunday; PI 9 does not say how the band is derived. (c) Example A's version 2 shows `seen_before: none` although version 1 of the **same** case was recorded in the open week, so the current case must be excluded. Proposal: last seen = the latest `local_date` among the relationship's entries in all mid-term memories (open week included, written at or before `as_of`) and its long-term `last_seen`, **excluding the current case**; bands use the rolling 7 and 28 days.
14. **History note (FE 7.7).** "Enough", "enough_for_some", "not_enough_history_yet" do not partition (every / some / most). Proposal over the case's relationship factors: none are `insufficient(history)` gives `enough`; more than half give `not_enough_history_yet`; otherwise `enough_for_some`; no relationship factors gives `enough`. On the real data this gives example B correctly (4 of 4 insufficient).
15. **Templates and vocabulary missing (FE 7.8, Appendix C, 10 load check).** The load check asks for a template per wording class, but Appendix C gives one per mode. And the text needs words the phrase book does not contain: a noun per hand-off measure and the above/below wording, the meal label ("a festive dinner"), the time since the meal in words, the elapsed-time words for the percentile. Proposal: per-class clause templates plus the extra tables in (c); verb agreement (has/have) from a `number` field on each exposure.
16. **The numberless view (FE 8.1).** `h1`, `n1` and the PI item ids (`p1`...) are cited in the output format but the example view does not show them. Diary text may contain digits (the view is "numberless" except for it). Proposal: the view carries explicit `h1`, `n1`, `p<k>` items.
17. **Checks (FE 8.3).** (a) Check 6 looks for "has tended to move together with"; the spec's own example sentence says "have each tended to move together with". Proposal: detect the stems "tended to move together" and "linked to". (b) The window phrase for `3d` contains "two" and the `720m` one "twelve": check 3 allows window phrases only as supplied, which needs an exception list; "twelve" is not in the counting-word list, "two" is. (c) The internal-word list in check 5 contains "class"; the prompt's list (Appendix B rule 9) does not. Proposal: use check 5's list in both.
18. **The record (FE 9.1).** (a) `refs.diary` holds view ids ("d1"), which are meaningless after the run; OV shows stable ids (`ctx:...`). Proposal: store `[{"view_id": "d1", "context_id": "ctx_106"}]`. (b) `status` values other than `ok` and `code_line_fallback` for the code-only mode (proposal: `ok` with `text.source = code_line`). (c) `insufficient_reason` appears in example B but not A; proposal: always present for `insufficient` factors.
19. **State memory "last completed week" (FE 6).** `memory_v2` weeks are rolling seven-day windows ending on every day, not calendar weeks. "Last completed week window" is therefore the window ending yesterday, which overlaps the day window. Proposal: use `week_ENDING_<yesterday>` and `day_<yesterday>`, and the month checkpoint with the latest `end_date` before the case's local date.
20. **F1 needs an event loop (FE 3, PI 11, OV 14).** The spec puts the replay driver in P1, but F1 "over the full replay" must order hand-offs and completions and close cases. Proposal: F1 includes a minimal ordered loop (hand-offs by `opened_at` then `handoff_id`, completions by evaluation time, cases closed on the next event); P1 adds weeks and PI calls to it rather than replacing it.

### PI, internal

21. **DECISION. Partial weeks and the end of the data (PI 4, 6.3, 7, 13).** The record starts on Wednesday 1 October 2025 and ends on Thursday 17 September 2026. A week label needs 5 of 7 days, "a day with no record counts as `insufficient`". The last week (14 to 20 September) has only four days with records, so it can never be `supported`; yet example 13 shows 6 of 7 days supported in that week and a job at Sunday 20 September, three days after the data ends. Proposal: count only days up to the end of the data (days after it are not "missing", they do not exist), and scale the threshold for a partial week (5 of 7 becomes the same share of the days that exist, rounded up; config).
22. **DECISION. Back-fill against the example (PI 6.3, 13).** With `backfill_on_create: true`, the sleep and missed-dose relationships of example 13 (supported on most days since December) would be created as `supported`, with many weekly labels, not as `candidate` with one label. The example is labelled illustrative, but its first timeline contradicts the rule. Proposal: follow the rule; the example needs rewriting.
23. **Lifecycle gaps (PI 6.3).** A `candidate` has no path to `weakened` or `retracted`, so a candidate that is never promoted stays a candidate forever. Whether an opposite decisive week resets a count (a supported week between two not-supported ones) is not stated. "Consecutive" and "suggestive and insufficient weeks do not reset a count" are read together as "consecutive decisive weeks". Proposal: a count is a run of equal decisive labels, reset by the opposite decisive label; the missing candidate path is left as specified and put on the parked list.
24. **`evidence_refs` and counters (PI 6.2, 14.9).** The example's reference is for the Sunday of the week, a day that may have no record; the list's length is not defined. `case_days` counts "distinct local dates on which the relationship was a usable factor in a case": from the latest version of each case or from any version? Proposal: the id of the last day with a record in each decisive week; counters from the latest entry of each case. A case that runs from Sunday into Monday keeps its `local_date`; its late version lands in the next open week.
25. **Regeneration schedule (PI 8.6).** "Every 4 weeks" counted from creation or from a global week number is not stated. Proposal: from the memory's creation week.
26. **Checks (PI 8.4).** Check 6 ("does not mention any other relationship's exposure or outcome phrase") fails when two relationships share a phrase (sleep before dinner peaks and before lunch peaks share the exposure phrase). Proposal: test only the phrases that are not part of the relationship's own phrases. The example shapes of `text` differ (object in 13, a string in the next-week example).
27. **Entries and the mid-term memory (PI 6.1, 4).** "Which week an entry belongs to" is by `as_of`; counters use `local_date`. A late version in week N+1 of a case dated in week N is counted by the job of week N+1 against week N's date; no change to a sealed memory. Stated here so it is tested.

### Across the specs

28. **Wording tables differ (OV 8, FE 7.3, PI 8.3).** OV allows "tends to" and "has been linked to" for `supported`; FE and PI use "has tended to move together with" and "has repeatedly moved together with". Proposal: FE and PI win; OV 8 is out of date.
29. **Statuses differ (OV 8, PI 6.3).** OV has no placebo condition on promotion, no `retracted` to `candidate` path, and says `contrary` "for four weeks" (PI: on 5 days a week for four weeks). PI wins.
30. **Reasons not covered (EV 9.2 addition, FE 7.3).** EV's factors carry `reason` (`no_stream`, `history`, `small_group`, `no_variation`, `no_ordered_exposure`, `no_definition`, `no_meal_kind`, `no_meal`, `no_readings`, `no_relationship`, `not_in_library`); FE handles two. Covered by item 9.
31. **End-of-day outcomes (EV 3.1 rule 1, FE 4, PI 6.2).** The hydration hand-off opens at 00:00 and its evidence `as_of_date` is the day before. The case `local_date` is the day of `opened_at`, the evidence date is a day earlier. Proposal: keep both; PI counts the case's `local_date`; the evidence reference is by id.
32. **The Evidence library is an input for both (FE 6, PI 5).** Neither lists it, yet both need the pair list, `ordering` (for PI's `same_day_only`), the exposure risk side and the outcome direction. Proposal: add it to both input tables (read-only).
33. **"Whose symptom" (FE 12B, 14) has a partial data fix.** The 16 November diary entry about her father carries the note "concerning, not her own symptom" in `meta_json.note` (the only entry of its kind). If the note is passed to the model as `severity_or_note`, the text layer can use it; no structured subject field exists upstream.
34. **Phrase book load check (FE 10, PI 14.17).** Both specs ask that every key in the Evidence library have a phrase. The library has a `7d` window (`missed_dose@7d`) that A.3 lacks; added in the draft.

## (b) `[verify]` items against the real store and code

| Item | Found | Differs from the spec? |
|---|---|---|
| Gist headline in `memory_v2` | Column `gist_headline` (text) and `gist_sentences` (JSON list), status in `gist_status`; the parsed object from `MemoryV2Store.get_memory(tier, date)` has `gist.headline`, `gist.sentences`, `gist.status`. FE 11.1 says `gist_headline`, which is the column name. All 710 windows have a headline (528 `gist_ok`, 62 `gist_retry_ok`, 91 `code_line_quiet`, 29 `code_line_early`). | The key to configure is `gist_headline` (column) or `gist.headline` (parsed). **25 of the 29 `code_line_early` headlines contain digits, dates or quoted diary text** (for example `Diary, 2025-10-01 [life event]: "Maha Navami puja hosting..."`); they cannot go into a numberless view. The first 29 days are affected. Proposal: do not use `code_line_early` headlines (config `skip_statuses`). |
| How `memory_v2` windows read as-of a date | Window ids `day_<date>`, `week_ENDING_<date>` (rolling seven days, one per day from the 7th), `month_ENDING_<date>` (cumulative from day 1, a checkpoint every 30 days and a final partial one on 2026-09-17). `get_memory(tier, end_date)` and `get_memories_between(start, end, tier)` select by `end_date`. A window's content uses only data up to its end (the profile for day D uses days before D, tested), so a read as-of date D needs `end_date < D`: yesterday's day window, `week_ENDING_<yesterday>`, the month checkpoint with the largest `end_date` before D. | "Last completed week window" is the rolling window ending yesterday (item 19). The gist **text** was written later by the model, but only from the window's own facts. Before the 7th day and before the first checkpoint there is no such window; the reader returns none. |
| Diary fields in `context_events` | Stream `diary_context`: `category` (life_event 69, social_interaction 22, symptom 17, substance_use 6, healthcare_interaction 5, environment 4, allergy 2, habits 2, travel 2), `value_text` = the description, `timestamp` (all 129 entries have one), `meta_json` = `{"id": "ctx_106", "note": "severe, family crisis"}`. | The spec's `description` is `value_text`; `severity_or_note` is `meta_json.note`; there is also a stable id `meta_json.id`. Notes in use: empty 33, mild 21, positive 13, moderate 3, resolving 3, high 2, severe 1 and others. Only "moderate or worse" words exist as `moderate`, `high`, `severe`, so the severity ordering has few entries to rank (FE 14 fallback applies). The baseline config has `diary.severity_order`. |
| Hand-off field names | `handoff_id`, `item_id`, `measure`, `direction`, `size` (`clearly` or `far`), `trigger`, `opened_at` (+05:30), `context.last_meal` `{label, time, minutes_ago}` (never null in this data). | No. |
| Packet field names | `packet_id`, `handoff_id`, `status` (absent when normal; `deferred` for 8), `matched_rule.rule_id`, `selected[]` `{rank, weight_tier, candidate, check_type, ...}`, `skipped`, `not_selected`. | No. |
| Evidence field names | Event record: `evidence_id` (`ev_<handoff_id>`), `packet_id`, `handoff_id`, `rule_id`, `event_time`, `as_of_date`, `factors[]` (`rank, weight_tier, candidate, check_type, relationship_evidence_id, support, flags, reason, event_exposure {state, anchor, tail_percentile, available_at}, event_specific`), `overlap[]` `{a, b, a_view, b_view, share_given_a, share_overall, ratio, flag}`, `not_tested`, `counts`. Relationship record: `relationship_key`, `exposure_id`, `outcome_id`, `outcome_scope`, `support`, `flags`, `insufficient_reason`, `as_of_date`. | `overlap` uses `flag` (boolean) not `entangled`; the label for event-level presence and pattern checks is `not_applicable`; factors carry a `reason` when insufficient. FE 6 lists none of `reason`, `anchor`. |
| Stored `event_completions` | 5 rows, all `sensor_artifact` of the `glucose_below` hand-offs: columns `evidence_id`, `candidate`, `support` (3 `supported`, 2 `not_supported`), `result_json` (target, previous, next, isolated, rebound, steep_drop, overnight, target_removed_by_cleaning), `evaluated_from` `{start, end}` (end = opened_at + 60 minutes). | No completion id and no separate time column (item 5). |
| The timezone key | The baseline config: `patient.timezone: "Asia/Kolkata"`. The State and Evidence configs read it from there (`StateConfig.timezone`, `EvidenceConfig.tz`). PI 10 says `timezone_from: baseline_config`; FE 10 has no timezone key at all although it needs one for `local_date` and part of day. | Add the same `baseline_config` path to the Findings config. |
| Other facts the code layer relies on | 287 hand-offs, 287 packets, 287 event records (279 normal, 8 deferred with no factors); 22,148 relationship records (63 a day); the hospitalization-week case of example B (`case_2025-11-18T08:17`: BP 08:17, glucose 11:15 and 15:15) exists as described at a 6-hour gap; so does the evening case of example A (heart rate 21:45, glucose 22:30). The 15:15 glucose record has `meal_composition` `supported` and `exposed` (item 8). | The ids and the case membership of examples A and B match the data. |

## (c) Draft phrase book (for your review)

Everything the Evidence library needs: **16 exposures, 10 outcomes, 11 window tags, 8 event-level candidates**, and every one of the library's 49 runnable pairs (63 keys with the meal kinds) renders to a sentence. Additions to the spec's Appendix A are marked ADDED in the file: the `7d` window, the hand-off measures, the meal-ago and elapsed-time words, a `number` field (has/have), a `contrary` sentence per outcome, and a position suffix for the event percentiles. Changes of wording against the spec are marked in comments (post-meal outcome, lowest glucose). I ran the draft through the checks the engine will use (no digits, no internal words, no counting words, "same day" present for every `same_day_unverified` pair): **the only hit is the spec's own `3d` phrase ("in the two days before")**, which needs the exact-phrase exception of FE check 3, or the wording "in the few days before".

```yaml
# DRAFT phrase book (patient-independent). Review copy: not a repository config yet.
version: pb-draft-1
windows:                       # lookback tag -> phrase. includes_unit_date tags must contain "same day"
  same_day:  "on the same day"
  1d:        "on the same day"
  2d:        "on the same day or the day before"
  3d:        "on the same day or in the two days before"      # spec text: contains a counting word ("two"); allowed only as supplied (check 3 exception)
  7d:        "in the week before, not counting that day"        # ADDED: the Evidence library has missed_dose@7d (not in spec A.3)
  prev_night:   "the night before"
  prev_day:     "the day before"
  prev_evening: "the evening before"
  60m:   "in the hour before"
  720m:  "in the previous twelve hours"
  at_open: "at that reading"
exposures:                     # phrase: {window} slot optional; number drives has/have
  missed_dose:            {phrase: "missed doses {window}", number: plural}
  sleep_hours:            {phrase: "short sleep {window}", number: singular}
  strained_period:        {phrase: "a stressed or low-mood period {window}", number: singular}
  steps_total:            {phrase: "low activity {window}", number: singular}
  steps_window_hourly:    {phrase: "more activity in the hour before", number: singular}
  high_steps_day:         {phrase: "a very active day", number: singular}
  symptom_entry:          {phrase: "a symptom noted in the diary {window}", number: singular}
  alcohol_entry:          {phrase: "alcohol noted in the diary {window}", number: singular}
  environment_entry:      {phrase: "a weather or environment note {window}", number: singular}
  hydration_total:        {phrase: "low fluid intake {window}", number: singular}
  screen_hours:           {phrase: "long screen time {window}", number: singular}
  late_meal:              {phrase: "a late meal", number: singular}
  late_prior_dinner:      {phrase: "a late dinner the evening before", number: singular}
  non_home_day:           {phrase: "a day away from home", number: singular}
  prior_day_glucose_mean: {phrase: "higher glucose the day before", number: singular}
  clinic_reading:         {phrase: "a reading taken at a clinic", number: singular}
outcomes:                      # phrase = used after "has tended to move together with"; contrary = the sentence for the `contrary_note` class (the outcome tended to be LOWER on such days)
  post_meal_peak:    {phrase: "higher glucose peaks after {kind}",  contrary: "her glucose peaks after {kind} have tended to be lower"}   # spec A.2: "higher glucose after meals"; spec examples say "higher dinner peaks"
  non_meal_mean:     {phrase: "higher glucose between meals",       contrary: "her glucose between meals has tended to be lower"}
  day_min_glucose:   {phrase: "a lower lowest glucose that day",    contrary: "her lowest glucose that day has tended to be higher"}      # spec A.2: "lower lowest-glucose of the day" (awkward)
  hr_hour_mean:      {phrase: "higher heart rate in that hour",     contrary: "her heart rate in that hour has tended to be lower"}
  hr_day_mean:       {phrase: "higher heart rate over the day",     contrary: "her heart rate over the day has tended to be lower"}
  resting_hr_day:    {phrase: "a higher resting heart rate",        contrary: "her resting heart rate has tended to be lower"}
  sleep_hours_night: {phrase: "shorter sleep that night",           contrary: "her sleep that night has tended to be longer"}
  missed_doses_day:  {phrase: "more missed doses that day",         contrary: "her missed doses that day have tended to be fewer"}
  systolic_reading:  {phrase: "higher blood pressure readings",     contrary: "her blood pressure readings have tended to be lower"}
  fluid_intake_day:  {phrase: "lower fluid intake that day",        contrary: "her fluid intake that day has tended to be higher"}
event_checks:                  # candidate -> noun phrase; percentile checks also say how unusual
  meal_composition:        {phrase: "the size of this meal's rise", position_suffix: "in the first {elapsed} after {kind}s"}
  meal_skipped_or_delayed: {phrase: "the time since the last meal", position_suffix: "at this time of day"}
  sensor_artifact:         {phrase: "a possible sensor artifact"}
  dawn_effect:             {phrase: "an early-morning rise"}
  regimen_factors:         {phrase: "which medicine is missed most"}
  other_medications:       {phrase: "a medicine she takes that is relevant here"}
  thyroid_status:          {phrase: "a medicine she takes that is relevant here"}
  hypoglycemic_agent:      {phrase: "a medicine she takes that is relevant here"}
elapsed_words:                 # ADDED: the bucket of minutes since the meal -> words with no number (digits and counting words are not allowed in text)
  - {up_to: 45,  words: "part of the hour"}
  - {up_to: 90,  words: "hour or so"}
  - {up_to: 999, words: "couple of hours"}
meal_ago_words:                # ADDED: minutes since the last meal -> words, for "a festive dinner about an hour earlier"
  - {up_to: 30,  words: "a short while earlier"}
  - {up_to: 90,  words: "about an hour earlier"}
  - {up_to: 150, words: "a couple of hours earlier"}
  - {up_to: 99999, words: "a few hours earlier"}
measures:                      # ADDED (not in the spec's Appendix A): hand-off measure -> noun phrase; direction gives "above"/"below"
  glucose: "glucose"
  heart_rate: "heart rate"
  resting_heart_rate: "resting heart rate"
  sleep_duration: "sleep"
  medication_adherence: "doses taken"
  blood_pressure: "blood pressure"
  hydration: "fluid intake"
  screen_time: "screen time"
strength_words: {clearly: "clearly", far: "far"}
position_bands: {low_side: [[0, 5, "among the very lowest she has had"], [5, 25, "low for her"]], high_side: [[95, 100, "among the very highest she has had"], [75, 95, "high for her"]]}
```

### Every pair, rendered (meal kind shown as `dinner`; the `has`/`have` agreement, the window and the "same day" rule applied)

| Relationship key | Ordering | Sentence for the `asserted` class |
|---|---|---|
| `missed_dose@2d->post_meal_peak:{meal_kind}` | same_day_unverified | Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner in her history. |
| `sleep_hours@prev_night->post_meal_peak:{meal_kind}` | ordered | Short sleep the night before has tended to move together with higher glucose peaks after dinner in her history. |
| `strained_period@1d->post_meal_peak:{meal_kind}` | ordered | A stressed or low-mood period on the same day has tended to move together with higher glucose peaks after dinner in her history. |
| `steps_total@1d->post_meal_peak:{meal_kind}` | same_day_unverified | Low activity on the same day has tended to move together with higher glucose peaks after dinner in her history. |
| `symptom_entry@3d->post_meal_peak:{meal_kind}` | ordered | A symptom noted in the diary on the same day or in the two days before has tended to move together with higher glucose peaks after dinner in her history. |
| `late_meal@same_day->post_meal_peak:{meal_kind}` | ordered | A late meal has tended to move together with higher glucose peaks after dinner in her history. |
| `alcohol_entry@1d->post_meal_peak:{meal_kind}` | ordered | Alcohol noted in the diary on the same day has tended to move together with higher glucose peaks after dinner in her history. |
| `missed_dose@2d->non_meal_mean` | same_day_unverified | Missed doses on the same day or the day before have tended to move together with higher glucose between meals in her history. |
| `symptom_entry@3d->non_meal_mean` | same_day_unverified | A symptom noted in the diary on the same day or in the two days before has tended to move together with higher glucose between meals in her history. |
| `strained_period@1d->non_meal_mean` | same_day_unverified | A stressed or low-mood period on the same day has tended to move together with higher glucose between meals in her history. |
| `sleep_hours@prev_night->non_meal_mean` | same_day_unverified | Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. |
| `steps_total@prev_day->non_meal_mean` | ordered | Low activity the day before has tended to move together with higher glucose between meals in her history. |
| `late_prior_dinner@prev_evening->non_meal_mean` | ordered | A late dinner the evening before has tended to move together with higher glucose between meals in her history. |
| `high_steps_day@1d->day_min_glucose` | same_day_unverified | A very active day has tended to move together with a lower lowest glucose that day in her history, on the same day. |
| `alcohol_entry@720m->day_min_glucose` | ordered | Alcohol noted in the diary in the previous twelve hours has tended to move together with a lower lowest glucose that day in her history. |
| `symptom_entry@1d->day_min_glucose` | same_day_unverified | A symptom noted in the diary on the same day has tended to move together with a lower lowest glucose that day in her history. |
| `steps_window_hourly@60m->hr_hour_mean` | ordered | More activity in the hour before has tended to move together with higher heart rate in that hour in her history. |
| `strained_period@same_day->hr_day_mean` | same_day_unverified | A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history. |
| `symptom_entry@3d->hr_day_mean` | same_day_unverified | A symptom noted in the diary on the same day or in the two days before has tended to move together with higher heart rate over the day in her history. |
| `hydration_total@prev_day->hr_day_mean` | ordered | Low fluid intake the day before has tended to move together with higher heart rate over the day in her history. |
| `sleep_hours@prev_night->hr_day_mean` | same_day_unverified | Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. |
| `alcohol_entry@720m->hr_day_mean` | ordered | Alcohol noted in the diary in the previous twelve hours has tended to move together with higher heart rate over the day in her history. |
| `sleep_hours@prev_night->resting_hr_day` | same_day_unverified | Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day. |
| `symptom_entry@3d->resting_hr_day` | same_day_unverified | A symptom noted in the diary on the same day or in the two days before has tended to move together with a higher resting heart rate in her history. |
| `strained_period@prev_day->resting_hr_day` | ordered | A stressed or low-mood period the day before has tended to move together with a higher resting heart rate in her history. |
| `hydration_total@prev_day->resting_hr_day` | ordered | Low fluid intake the day before has tended to move together with a higher resting heart rate in her history. |
| `alcohol_entry@prev_evening->resting_hr_day` | ordered | Alcohol noted in the diary the evening before has tended to move together with a higher resting heart rate in her history. |
| `strained_period@same_day->sleep_hours_night` | ordered | A stressed or low-mood period on the same day has tended to move together with shorter sleep that night in her history. |
| `late_prior_dinner@prev_evening->sleep_hours_night` | ordered | A late dinner the evening before has tended to move together with shorter sleep that night in her history. |
| `alcohol_entry@prev_evening->sleep_hours_night` | ordered | Alcohol noted in the diary the evening before has tended to move together with shorter sleep that night in her history. |
| `screen_hours@prev_evening->sleep_hours_night` | ordered | Long screen time the evening before has tended to move together with shorter sleep that night in her history. |
| `symptom_entry@same_day->sleep_hours_night` | ordered | A symptom noted in the diary on the same day has tended to move together with shorter sleep that night in her history. |
| `non_home_day@same_day->sleep_hours_night` | ordered | A day away from home has tended to move together with shorter sleep that night in her history. |
| `non_home_day@same_day->missed_doses_day` | same_day_unverified | A day away from home has tended to move together with more missed doses that day in her history, on the same day. |
| `strained_period@same_day->missed_doses_day` | same_day_unverified | A stressed or low-mood period on the same day has tended to move together with more missed doses that day in her history. |
| `symptom_entry@same_day->missed_doses_day` | same_day_unverified | A symptom noted in the diary on the same day has tended to move together with more missed doses that day in her history. |
| `missed_dose@7d->missed_doses_day` | excludes_outcome_day | Missed doses in the week before, not counting that day have tended to move together with more missed doses that day in her history. |
| `sleep_hours@prev_night->missed_doses_day` | same_day_unverified | Short sleep the night before has tended to move together with more missed doses that day in her history, on the same day. |
| `missed_dose@2d->systolic_reading` | same_day_unverified | Missed doses on the same day or the day before have tended to move together with higher blood pressure readings in her history. |
| `clinic_reading@at_open->systolic_reading` | same_day_unverified | A reading taken at a clinic has tended to move together with higher blood pressure readings in her history, on the same day. |
| `strained_period@same_day->systolic_reading` | no_ordered_exposure | A stressed or low-mood period on the same day has tended to move together with higher blood pressure readings in her history. |
| `sleep_hours@prev_night->systolic_reading` | ordered | Short sleep the night before has tended to move together with higher blood pressure readings in her history. |
| `alcohol_entry@720m->systolic_reading` | ordered | Alcohol noted in the diary in the previous twelve hours has tended to move together with higher blood pressure readings in her history. |
| `symptom_entry@same_day->systolic_reading` | ordered | A symptom noted in the diary on the same day has tended to move together with higher blood pressure readings in her history. |
| `symptom_entry@same_day->fluid_intake_day` | same_day_unverified | A symptom noted in the diary on the same day has tended to move together with lower fluid intake that day in her history. |
| `non_home_day@same_day->fluid_intake_day` | same_day_unverified | A day away from home has tended to move together with lower fluid intake that day in her history, on the same day. |
| `prior_day_glucose_mean@prev_day->fluid_intake_day` | ordered | Higher glucose the day before has tended to move together with lower fluid intake that day in her history. |
| `environment_entry@same_day->fluid_intake_day` | same_day_unverified | A weather or environment note on the same day has tended to move together with lower fluid intake that day in her history. |
| `alcohol_entry@prev_evening->fluid_intake_day` | ordered | Alcohol noted in the diary the evening before has tended to move together with lower fluid intake that day in her history. |

Things to look at in these sentences: `sleep_hours@prev_night` on day-level outcomes reads "...the night before ... on the same day" (the sleep record is dated that day); `missed_dose@7d` has a clumsy window; slot-less exposures (late meal, very active day, day away from home, a reading taken at a clinic) get "on the same day" appended only for the pairs marked `same_day_unverified`.

## (d) Proposed config files

Three files; the phrase book is shared, as the specs require, and is checked at load against the Evidence library by **both** components. No stream, measure, medicine or patient name appears in either engine: measures, meal labels, diary fields and table names are config.

**1. `config/findings_phrasebook_v0.yaml`** (patient-independent, shared; the draft in (c)). Load check (FE 10, PI 14.17): every exposure, outcome, window tag, event candidate and hand-off measure that the Evidence library or the rulebook can produce has a phrase; every wording class has a clause template; every position band is defined.

**2. `config/findings_meera_iyer_v1.yaml`**
```yaml
findings:
  method_version: fe-v0
  mode: code_only                        # code_only (F1) | full (F2: text layer on)
  paths:
    baseline_config: config/patient_meera_iyer_v1.yaml     # patient.timezone, diary severity words (read only)
    evidence_config: config/evidence_meera_iyer_v1.yaml    # -> evidence DB, library (pairs, ordering, risk side, outcome direction)
    evidence_db: output/evidence_engine.db                 # read only
    packets_db: output/rulebook_lookup.db                  # read only
    handoffs_db: output/state_engine.db                    # read only
    store_db: output/personal_data_store.db                # read only: diary and memory_v2
    phrasebook: config/findings_phrasebook_v0.yaml
    db_path: output/findings_engine.db                     # the only file this engine writes
  case: {gap_hours: 6, max_span_hours: 36, deferred_opens_case: false, deferred_extends_gap: false}
  diary:
    source: {table: context, name: diary_context}
    fields: {category: category, description: value_text, note: meta.note, id: meta.id, timestamp: timestamp}
    max_entries: 6
    start: previous_local_day
    order: [severity_moderate_or_worse, most_recent]       # severity words from the baseline config; fallback most recent
  state_memory:
    table: memory_v2
    headline: gist_headline
    use: [yesterday_day, last_week, latest_month]          # week = the rolling window ending yesterday (item 19)
    skip_statuses: [code_line_early]                       # these headlines contain digits and quoted diary text
  pi: {mid_term_recent_weeks: 2, include_open_week: true}
  seen_before_bands: {this_week_days: 7, recent_weeks_days: 28}
  part_of_day: {night: [0, 5], morning: [5, 12], afternoon: [12, 18], evening: [18, 24]}
  history_note: {not_enough_share: 0.5}
  text:                                                    # used from F2 on
    enabled: false
    model: "openai/gpt-5-mini"
    reasoning_effort: low
    timeout_seconds: 90
    sdk_retries: 0
    retries: 1
    concurrency: 6
    headline_max_words: 20
    sentences: {min: 2, max: 5}
    cache: true
    exact_window_phrases: true                             # window phrases may contain words check 3 forbids elsewhere
```

**3. `config/pi_meera_iyer_v1.yaml`**
```yaml
pi:
  method_version: pi-v0
  paths:
    baseline_config: config/patient_meera_iyer_v1.yaml     # timezone
    evidence_config: config/evidence_meera_iyer_v1.yaml    # evidence DB and library (read only)
    phrasebook: config/findings_phrasebook_v0.yaml
    db_path: output/pi.db                                  # the only file PI writes
  week: {start_day: monday, close_at: "23:59:59", partial_week: {scale_threshold: true}}     # item 21
  week_label: {days_needed: 5, of: 7}
  lifecycle: {promote_after_weeks: 2, weaken_after_weeks: 2, retract_after_weeks: 6,
              retract_on_contrary: {days_per_week: 5, weeks: 4}, repromote_after_weeks: 2,
              placebo_fired_max_share: 0.5, backfill_on_create: true}
  seen_before_bands: {this_week_days: 7, recent_weeks_days: 28}
  text: {enabled: false, model: "openai/gpt-5-mini", reasoning_effort: low, timeout_seconds: 90,
         sdk_retries: 0, retries: 1, max_words: 60, regenerate_every_weeks: 4, cache: true}
```

**Code layout (proposal).** `src/v0_code/intel_common/` (phrase book loader and load check, as-of helpers, local-time helpers: shared by both), `src/v0_code/findings_engine/` (`config`, `cases`, `factors`, `wording`, `groups`, `repeat`, `view`, `codeline`, `storage`, `run`, later `text`), `src/v0_code/pi/` (`config`, `memories`, `weeks`, `lifecycle`, `retrieval`, `storage`, `driver`, later `text`). Each writes only its own database.

## (e) Testing without a model, and the second synthetic patient

**Everything except the model call is testable offline.**

- **F1 (code layer):** pure functions of (hand-offs, packets, event records, completions, diary rows, memory rows, PI answers). Tests: case opening, joining, the gap and span rules (including a hand-off exactly at the gap), deferred handling, ids and dates across midnight and across a daylight-saving-free zone and a non-IST zone; factor merging (labels from the latest outcome date, flags union, exposure precedence); the full wording-class table row by row; mode; groups (components, event-level excluded); position bands at their edges; repeat information with a fake PI; history note; the code line for each template; idempotence and determinism (run twice, identical rows); as-of reads (a store cut at the case's `as_of` gives the same record); no digits or dates in any code line; labels and flags equal the evidence record's.
- **P1:** week boundaries (Monday start, a case across Sunday and Monday), sealing, week labels at 4/5 days, every transition including the reset rules, back-fill, counters counting a date once, as-of retrieval (a memory written after `as_of` is invisible), idempotent `record_finding`, determinism.
- **The driver:** event ordering and ties, resumability (stop and restart gives identical rows).
- **The text layers (F2, P2) without a model:** the checks are pure functions, tested with canned good and bad outputs; the retry and fallback logic with a fake client that returns scripted answers; the cache with a fake client that must not be called on the second run. Only the quality of the real wording needs the model.

**The second synthetic patient needs, beyond the Evidence fixture (`tests/evidence_synth.py`):**
1. its own **phrase book** (patient-independent in principle, but the synthetic library has its own exposures and outcomes such as `pill_skip` and `night_len`; the test file supplies phrases for them, which is the "config changes only" case) and its own measure words and meal label;
2. **hand-offs and packets** for its rules (hand-crafted dicts, as in `test_evidence_events.py`) with other measure keys, and a deferred packet;
3. **event evidence, completions and daily relationship evidence**: produced by running the real Evidence Engine on the synthetic store, so labels and flags are real (this exercises the real ids);
4. a **diary stream with other field names** (the synthetic `notes` table: category `unwell`/`party`, a note column) to test the field mapping and the severity ordering;
5. **`memory_v2` rows** for a few days, weeks and a month (hand-written rows with the same columns), including an early code-line headline with digits, to test skipping;
6. a different **timezone** (the synthetic patient is UTC+9) and different **part-of-day bands**;
7. for PI: a synthetic evidence database spanning more than ten weeks, with relationships that are supported for 2 weeks, not supported for 2 weeks, contrary, placebo-fired, plus a partial first and last week.

## (f) Case counts for the 287 hand-offs

Hand-offs sorted by `opened_at` (ties by `handoff_id`); a hand-off joins when the time since the case's last hand-off is at most the gap; the 36-hour span cap is applied where stated. 93 calendar days have a hand-off.

| gap | all 287 count (deferred treated as ordinary) | rule 5.1: deferred never opens a case | longest case | 36 h cap |
|---|---|---|---|---|
| 3 hours | **181** | 176 | 10.5 h | no effect |
| **6 hours** | **119** | **116** | 27.8 h | no effect |
| 12 hours | **85** | 84 (85 if a joined deferred hand-off does not extend the gap) | 60.5 h | 5 chains exceed 36 h; with the cap 89 |

**The 119 is reproduced only if the 8 deferred hand-offs count as ordinary hand-offs; the rule as written gives 116** (item 2). Other figures at 6 hours (rule 5.1): 279 hand-offs in cases, hand-offs per case 1: 58, 2: 21, 3: 13, 4: 11, 5: 2, 6: 4, 8: 4, 9: 1, 10: 1, 11: 1; largest cases 11 hand-offs (2025-10-15 00:15) and 10 (2026-03-16 01:15); at most 3 cases start on a day; cases start on 86 of the 93 days (on the other days the hand-offs belong to a case that began earlier, or are deferred); 27 cases begin before 10 December (descriptive mode expected). Expected stored versions with proposal 4: 279 (one per hand-off) + 5 (completions) = **284**. The two example cases are as described: `case_2026-09-17T21:45` (heart rate 21:45, glucose 22:30) and `case_2025-11-18T08:17` (blood pressure 08:17, glucose 11:15 and 15:15); the earlier morning case of 17 September holds four hand-offs from 06:15.

## Decisions I need before F1

1. **Item 2:** 116 (follow rule 5.1; recommended) or 119 (deferred hand-offs count as ordinary).
2. **Item 3:** closing recorded in the `cases` table, no extra version (recommended), or a closing version per case.
3. **Item 8:** mode needs a usable **relationship** factor; event-level statements are added in either mode (recommended), or keep 7.2 literally.
4. **Item 13:** the `seen_before` derivation (latest date among mid-term entries and long-term `last_seen`, excluding the current case, rolling 7 and 28 days).
5. **Items 21 and 22 (for P1, not F1):** partial first and last weeks; back-fill against the example.
6. **Items 9, 11, 14, 15 and 17:** accept the proposals as written, or name the ones to change; also the phrase book in (c): the post-meal outcome wording ("higher glucose peaks after dinner" against the spec's "higher dinner peaks"), the `3d` phrase (keep "two" with an exception, or "in the few days before"), the `7d` phrase.
7. **Item 20:** a minimal event loop inside F1.
8. **Item 1:** the file name; if you want the references to resolve I can rename the file or the references (I have done neither).

Parked, not acted on: the candidate with no demotion path (item 23), the structured `subject` field upstream for diary entries, the overview wording table (item 28), correcting the Evidence library rulebook lookbacks.
