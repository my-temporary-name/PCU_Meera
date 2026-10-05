# Evidence Engine, Stage 2b report (event evidence, completions) and the Stage 2a fix

Event evidence ran for all 287 packets (1.1 s with the relationship evidence already made; 3.7 s when it is made lazily). No LLM, nothing committed, the rulebook files untouched, the store / State Engine / Rulebook Lookup databases unchanged (checksums). 745 tests pass. Spec edits are in `task/evidence_engine_spec.md` (Revision 3, Appendix C).

## A. The history minimum (units AND distinct dates)

Fixed in code and config (`history.min_history_units: 60`, `history.min_history_days: 60`; records now carry `history.n_dates`). Tests: an hourly relationship is not tested before 60 distinct days; a relationship with plenty of units but fewer than 60 dates is `insufficient` (reason `history`). Re-run for the year: 22,148 records, two runs identical, placebo fire rate 8.57% (993 of 11,584). The hourly relationship is first tested on 2025-12-10 (60 dates).

| month | supported | suggestive | not_supported | insufficient |
|---|---|---|---|---|
| 2025-10 | 0 | 0 | 0 | 1,925 |
| 2025-11 | 0 | 0 | 0 | 1,890 |
| 2025-12 | 192 | 55 | 273 | 1,433 |
| 2026-01 | 374 | 131 | 484 | 964 |
| 2026-02 | 394 | 132 | 528 | 710 |
| 2026-03 | 446 | 119 | 728 | 660 |
| 2026-04 | 527 | 110 | 649 | 604 |
| 2026-05 | 598 | 140 | 595 | 620 |
| 2026-06 | 638 | 91 | 616 | 545 |
| 2026-07 | 691 | 117 | 652 | 493 |
| 2026-08 | 794 | 134 | 560 | 465 |
| 2026-09 (17 days) | 412 | 93 | 311 | 255 |

**October and November have no `supported` records (and no tested relationship at all).** Only 2025-12 changed from the first run (200 to 192 supported, 56 to 55 suggestive). `docs/evidence_engine_stage_2a_tables.md` is regenerated.

## B. Spec edits (all applied)

Revision 3 note at the top; "3.1 rule 5" changed to "rule 6" in 7.1 and property 14 (the one in Appendix B row A3 is correctly rule 5, anchoring, and was left); 7.2 minimums; section 14 row (11 pairs plus the two relationships with no ordered exposure); the section 12 sentence about sleep; Appendix C with six rows. One wording choice: your text for 7.2 read "fewer than 60 usable units AND fewer than min_history_days ... (both must be met)", which read literally means insufficient only when both are short. I wrote it as "fewer than 60 usable units, or fewer than min_history_days (60) distinct outcome dates (the history minimum is met only if both are ...)", which is what you asked the code to do.

## C. Stage 2b

**What was built** (`src/v0_code/evidence_engine/`): `events` (E1 to E6, exposure state, overlap, completions), `event_checks` (percentile, shape, pattern, presence), availability rules in `data` / `exposures` (a record that exists but is not available yet is `pending`, never `not_exposed`), event tables in `storage`, `--stage B` in `run`. Event records are written once (`written` / `same` / `differs`; a differing record never replaces the stored one).

### Labels across all factors (1,899 factors in 287 records)

supported 405, suggestive 91, not_supported 356, insufficient 882, not_applicable 160, not_yet_available 5.

| rule | packets | supported | suggestive | not_supported | insufficient | not_applicable | not_yet_available |
|---|---|---|---|---|---|---|---|
| heart_rate_above | 124 | 233 | 34 | 157 | 444 | 124 | 0 |
| glucose_above_no_recent_meal | 59 | 72 | 38 | 57 | 128 | 0 | 0 |
| glucose_above_post_meal | 40 | 36 | 8 | 70 | 166 | 0 | 0 |
| medication_adherence_below | 24 | 15 | 4 | 41 | 60 | 24 | 0 |
| resting_heart_rate_above | 12 | 27 | 5 | 7 | 21 | 12 | 0 |
| sleep_below | 10 | 15 | 1 | 16 | 28 | 0 | 0 |
| glucose_below | 5 | 3 | 1 | 7 | 9 | 0 | 5 |
| blood_pressure_above | 3 | 2 | 0 | 0 | 19 | 0 | 0 |
| hydration_below | 2 | 2 | 0 | 1 | 7 | 0 | 0 |
| screen_time_above (deferred) | 8 | no factors | | | | | |

Why 882 are `insufficient`: `history` 445 (the event is before the relationship had 60 units and 60 dates, mostly October to early December), `small_group` 276, `no_definition` 137, `no_ordered_exposure` 12, `no_meal_kind` 12. Not tested: 373 skipped by the packet, 137 cut by the budget, 16 `rule_deferred`. Event exposure states: exposed 434, not_exposed 798, **not_yet_available 334** (daily totals at end of day, medicine records at 21:00, mood blocks, a sleep record from 07:00), no_data 12 (the 12 `no_ordered_exposure` factors, below), none 321 (event-level checks and `no_definition`). Completeness holds for all 287 (no candidate missing or twice). Overlap: 434 pairs reported, 156 flagged `entangled` (36%).

### Packets with completions

Five, all `glucose_below` hand-offs; each was written `not_yet_available` with `earliest_evaluation_time` = opened_at + 60 minutes and completed afterwards (the event record unchanged):

| hand-off | event reading | previous / next | isolated | rebound | steep drop | completion |
|---|---|---|---|---|---|---|
| 2025-11-08T11:00 | 65.0 | 125.1 / 113.1 | yes | yes | yes | **supported** |
| 2026-01-20T16:00 | 65.0 | 136.3 / 114.1 | yes | no (22 > 20) | yes | not_supported |
| 2026-03-22T11:00 | 65.0 | 130.3 / 125.2 | yes | yes | yes | **supported** |
| 2026-08-19T15:00 | 65.0 | 136.0 / 114.4 | yes | no (21.6 > 20) | yes | not_supported |
| 2026-08-22T10:30 | 76.3 | 132.1 / 119.6 | yes | yes | yes | **supported** |

None of the five is overnight and none was removed by the cleaning rule. The two `not_supported` results fail only on the rebound tolerance (a placeholder of 20 mg/dL) by 1.6 and 2 mg/dL: the next reading is about 22 below the earlier level.

### Label flip rate

Changes of `support` between consecutive days, per relationship (63 relationships, 351 transitions each). Mean **0.28 changes a week**, median 0.18, maximum 1.41; 15 relationships never change (the never-tested ones), one flips at least once a week. The five that flip most (weekly average, excluding transitions to or from `insufficient` in brackets):

| relationship | changes | per week |
|---|---|---|
| `late_prior_dinner@prev_evening->non_meal_mean` | 71 | 1.41 (1.39) |
| `late_meal@same_day->post_meal_peak:lunch` | 46 | 0.92 (0.90) |
| `late_prior_dinner@prev_evening->sleep_hours_night` | 43 | 0.86 (0.84) |
| `symptom_entry@3d->non_meal_mean` | 36 | 0.72 (0.70) |
| `high_steps_day@1d->day_min_glucose` | 35 | 0.70 (0.68) |

Three of the five are exposures binarized at a daily-moving 75th percentile of her start times or steps; the threshold itself moves a little every day, so units near it change group.

### Share of supported records carrying `same_day_unverified`

Relationship records: **2,614 of 5,066 = 51.6%**. In event factors: 237 of 405 = 58.5%.

### The event evidence for `handoff_glucose_2026-09-17T22:30`, next to section 9.2

| | Engine | 9.2 example |
|---|---|---|
| `evidence_id`, `packet_id`, `rule_id`, `event_time`, `as_of_date` | same | same |
| factors (rank, candidate, support) | 1 meal_composition supported; 2 medication_adherence supported; 3 sleep supported; 4 stress_mood not_supported; 5 activity not_supported; 6 illness_symptoms not_supported; 10 alcohol insufficient | identical |
| flags | rank 2 and 5 `same_day_unverified`; rank 6 `contrary`, `placebo_fired`; rank 10 `small_group` (the example has none on rank 10) | same, apart from `small_group` |
| event exposure | exposed / exposed / exposed (tail 0.6) / exposed / not_yet_available (`end_of_day`) / not_exposed / not_exposed | identical |
| meal_composition | elapsed 62, bucket 60, bucket_size 15, observed 185.0, **history_n 347**, median **150.1**, p90 **167.4**, percentile **99** | same except history_n 346 (the prototype's label count, see the 2a report) |
| overlap | sleep vs missed dose: share_given_a 0.78, share_overall 0.71, ratio 1.10, flag false | 0.82 / 0.72 / 1.14 / false |
| not_tested | meal_timing `not_selected_budget`; other_medications and cycle_phase `skipped_by_packet` with packet reason and detail | identical |
| counts | factors 7, supported 3, suggestive 0, not_supported 3, insufficient 1, not_tested 3 | identical |

Additions to the example's shape: `anchor` in each exposure state (`meal_start`, `hour_start`, `opened_at` or `outcome_date`), `reason` on an insufficient factor, `b_view` in overlap entries, and the counts also carry `not_applicable` and `not_yet_available`.

### The hospitalization week, 2025-11-17 to 2025-11-20

23 hand-offs (heart rate 10, glucose 8, sleep, medication adherence, blood pressure, hydration, resting heart rate one each). Of 158 factors: **142 `insufficient`** (128 `history`, 12 `no_definition`, 2 `no_ordered_exposure`), 12 `not_applicable`, 2 `supported` and 2 `not_supported` (all four are the `meal_composition` percentile, which has no 60-day minimum). Every daily refresh in these four days has zero tested relationships (it is before the history minimum). So the Evidence Engine can say nothing about why, from relationships. What the event exposure states do show, for the factors of those 23 events (exposed 58, not_exposed 55, not_yet_available 19, no_data 2):

- sleep exposed in the very low tail on 17 to 20 Nov (tail percentile 0.0 to 6.1), hydration at the 0.0th percentile on 19 to 20 Nov, a missed dose exposed on every glucose and blood pressure event, illness (symptom entry) exposed on 17 and 18 Nov and not exposed on 19 and 20 Nov, a strained mood block exposed on most;
- the 17 Nov 23:45 and 18 Nov 22:15 heart rate events: activity not exposed (tail 27 and 51), stress, illness and sleep exposed.

The complete per-hand-off listing (every factor label and exposure state) is in the run output; it can be regenerated from `event_evidence`.

## Points for you

1. **Structural `no_data` / `no_ordered_exposure`.** 12 factors (the blood pressure mood pair on 3 events, the breakfast scope of the mood pair on 9) are `insufficient` with exposure state `no_data`: no mood block can have ended before a morning reading. By 7.4 `no_data` means "no value"; if you would rather call it `not_yet_available`, say so.
2. **Event exposure anchor.** I used the unit start (the event meal's start, the hour's start) for the ordering rule and `opened_at` for availability, and report the anchor in each state; section 3.1 rule 5 can be read as "anchored at opened_at" only. The 22:30 example agrees either way.
3. **The shape check and the rebound tolerance.** Two of the five lows fail the rebound test by under 2 mg/dL; the tolerance is a placeholder, so I did not touch it.
4. **Flip rate.** One relationship flips more than once a week; the binarized "late" exposures flip most. This is the day-to-day instability of a threshold that moves each day, not of the data.
5. **Hospitalization week.** Nothing relationship-based can be said before December; this is the 60-day minimum doing what it should.
