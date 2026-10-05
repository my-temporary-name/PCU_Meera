# Evidence Engine, Stage 2a report (library, history table, daily refresh)

> **Superseded in part by `docs/evidence_engine_stage_2b_report.md`, section A:** the history minimum now needs 60 usable units AND 60 distinct outcome dates, so October and November have no tested relationships and no `supported` records; the label counts for 2025-12 onwards are in that report. The rest of this report stands.

Built and run: the library loader and its load check, the history-table builder (ordering, anchoring, availability, detrending), the daily refresh (effects, circular-shift permutation, placebo, Benjamini-Hochberg, labels) and `relationship_evidence`. The daily refresh ran for every day of the record (2025-10-01 to 2026-09-17). Stage 2b (event evidence) is not started. No LLM, nothing committed, the rulebook files are untouched. Per-relationship tables: `docs/evidence_engine_stage_2a_tables.md`.

## Run facts

| | |
|---|---|
| Days refreshed | 352 |
| Relationship records | **22,148** (one per relationship per day) |
| Records per day | 42 on day 1 (no meal kind has history yet), 56 on day 2, **63 on each of the other 350 days** (49 pairs, seven of them expanded over breakfast, lunch and dinner) |
| Runtime | **8.9 s** for the whole year (9.5 s with start-up); one day on its own takes under a second |
| Determinism | Run twice into two databases: **every table is identical, row for row** (22,148 relationship rows, 352 run rows) |
| Other databases | Store, `state_engine.db` and `rulebook_lookup.db` checksums unchanged; opened read-only |
| Tests | 715 pass (the evidence tests: stats, windows, library, refresh on a synthetic second patient, real-data checks) |
| Dependency | `numpy>=2.5.3` added to `pyproject.toml` (as decided) |

## Labels

All 22,148 records: supported 5,112, suggestive 1,128, not_supported 5,401, insufficient 10,507.

| month | supported | suggestive | not_supported | insufficient |
|---|---|---|---|---|
| 2025-10 | 13 | 0 | 5 | 1,907 |
| 2025-11 | 25 | 5 | 0 | 1,860 |
| 2025-12 | 200 | 56 | 273 | 1,424 |
| 2026-01 | 374 | 131 | 484 | 964 |
| 2026-02 | 394 | 132 | 528 | 710 |
| 2026-03 | 446 | 119 | 728 | 660 |
| 2026-04 | 527 | 110 | 649 | 604 |
| 2026-05 | 598 | 140 | 595 | 620 |
| 2026-06 | 638 | 91 | 616 | 545 |
| 2026-07 | 691 | 117 | 652 | 493 |
| 2026-08 | 794 | 134 | 560 | 465 |
| 2026-09 (17 days) | 412 | 93 | 311 | 255 |

October to November is almost all `insufficient`, as the spec says. The 13 and 25 `supported` records in those two months are one relationship, the hourly one (see "Points for you" 2).

On 2026-09-17: 63 relationships, 48 tested (the family), 28 supported, 2 suggestive, 18 not_supported, 15 insufficient (13 `small_group`, 2 `no_ordered_exposure`); one placebo fired.

**Fifteen relationship keys were never tested in the year** (always `insufficient`): all seven alcohol pairs (ten keys with the meal-kind expansion), `missed_dose@7d->missed_doses_day`, `clinic_reading@at_open->systolic_reading`, `symptom_entry@same_day->systolic_reading`, `environment_entry@same_day->fluid_intake_day`, and the two `no_ordered_exposure` relationships below. Section 14 lists ten pairs; the eleventh is `environment_entry` (4 exposed days, under the minimum of 15): see "Points for you" 3.

## Placebo fire rate

| | fired | tested | rate |
|---|---|---|---|
| **Year** | **999** | **11,641** | **8.6%** |

By month: Nov 16.7% (5 of 30), Dec 10.6%, Jan 13.3%, Feb 7.1%, Mar 13.8%, Apr 8.0%, May 5.1%, Jun 4.5%, Jul 9.3%, Aug 8.4%, Sep 7.2% (October had 18 tests and none fired). The monthly rates are a daily series of the same relationships, so they are strongly autocorrelated. The year rate sits slightly under the 10% a placebo p-value of at most 0.10 would give if the effect floor never bound, which is what one expects when the effect floor (0.10) also has to be met.

## The two relationships that cannot be ordered

Both are `insufficient` with reason `no_ordered_exposure` on **every one of the 351 days** (n_units 0, no effect, no p-value, no placebo, no flags):

| Relationship | Why |
|---|---|
| `strained_period@same_day->systolic_reading` (Appendix A `Ordering: no_ordered_exposure`) | Blood pressure is read at 08:00 to 08:30 and the first mood block ends at 12:00, so no block has ended by any reading |
| `strained_period@1d->post_meal_peak:breakfast` (Appendix A calls the pair `ordered`; only its breakfast scope has no ordered exposure) | Breakfasts start at about 08:00, before the first block ends at 12:00. The lunch and dinner scopes of the same pair run normally |

The spec's Ordering table names only the first; the second is the same reason code arising from the data (spec 3.1 rule 6, first bullet).

## The flagged pairs

- **`same_day_unverified`: 26 relationship keys = the 22 flagged pairs** (the 7 post-meal pairs expand over meal kinds: `missed_dose@2d` and `steps_total@1d` are flagged, each over three kinds). The set matches Appendix A exactly (the load check derives the ordering from the rules and compares).
- **`contrary`**: 7 relationships (731 relationship-days); **`placebo_fired`**: 47 relationships (999 days); **`small_group`**: 39 relationships (4,998 days; set only on an `insufficient` label caused by a small group).
- Lists with day counts for each flag, and the reason breakdown per relationship, are in the tables file.

## The record for `sleep_hours@prev_night->post_meal_peak:dinner`, as of 2026-09-17, next to the example in 9.1

| Field | Engine | 9.1 example (the spec's own prototype) |
|---|---|---|
| `history.first_day` / `last_day` | 2025-10-12 / 2026-09-16 | 2025-10-01 / 2026-09-16 |
| `history.n_units` | 337 | 335 |
| `history.n_dropped_by_detrend` | 10 | 10 |
| `n_exposed` / `n_reference` | 337 / null | 335 / null |
| `effect_kind`, `effect` | `spearman_rho`, 0.113 | `spearman_rho`, 0.12 |
| permutation `p` / `p_contrary` | 0.0580 / 0.9425 | 0.033 / 0.9675 |
| adjustment | BH, family 48, adjusted p 0.0960 | BH, family 5 (illustration), 0.086 |
| `support`, `flags` | `supported`, [] | `supported`, [] |
| placebo | effect 0.083, p 0.110, fired false | effect -0.03, p 0.65, fired false |
| `orientation`, `detrend` | high is worse / low sleep is riskier; trailing median 30 days, 10 prior | same |
| `evidence_id` | `rel|sleep_hours@prev_night->post_meal_peak:dinner|2026-09-17|ev-v0` | same |

Why the numbers differ a little: the prototype counted 346 `dinner` plus `light_dinner` labels, the engine's meal-kind matching also takes `festive_dinner` and `late_dinner` (spec 12 says so); `first_day` is the first day of a **used** unit after detrending, not of the first dinner; the p-values come from different random shifts. With the real family of 48 the adjusted p (0.096) is just under 0.10, so the record is `supported`, where the spec expects "likely suggestive". The same record also carries one field the example does not: `insufficient_reason` (null here).

The other dinner relationships agree closely with section 12: `missed_dose@2d` effect 0.253 (spec 0.24), 239 exposed and 98 reference (238, 97), flagged `same_day_unverified`; `steps_total@1d` 0.026 (0.03), flagged; `symptom_entry@3d` effect **-0.524** (spec -0.53) with flags `contrary` and `placebo_fired`, `not_supported`; `strained_period@1d` 41 exposed, effect 0.124 (spec 39 and 0.16); `alcohol_entry@1d` 3 exposed, `insufficient`, `small_group`.

## What was built (all in `src/v0_code/evidence_engine/`)

`library` (loader and the load check), `config`, `data` (read-only store access through the stream map, the Baseline cleaning rule, State Engine availability), `windows`, `units` (outcome units, detrending), `exposures` (generic primitives), `history`, `stats` (numpy: all shifted effects from one FFT), `refresh`, `storage`, `run`. Config: `config/evidence_library_v0.yaml` (static, 69 pairs, 10 outcomes, 16 exposures, 8 event checks) and `config/evidence_meera_iyer_v1.yaml`. The engine contains no stream, medicine, measure or patient name (a test scans for 25 such words); a second synthetic patient (other stream names, time zone, meal kinds, block names, its own rulebook and library) runs on config alone.

The load check (property 16) fails with a plain message if: a pair names an unknown exposure or outcome; a runnable pair has no key; a rulebook candidate has no pair or a pair no candidate; a form is not binary or continuous; a lookback kind is unknown; check type or weight tier disagree; the key's lookback tag differs from the rulebook's; an Ordering value is not one of the four; the Ordering differs from the one the rules derive (an addition I made); the presence flags differ from the Rulebook Lookup config. Run on the real library: all 49 key tags equal the rulebook's, so the two documented exceptions are not needed.

## Assumptions I made where the spec is silent

1. **As-of thresholds.** `high_steps_day`, `late_meal` and `late_prior_dinner` use the 75th percentile of the earlier values of the **history units** as of the date (the same threshold for every history row and, in Stage 2b, for the event).
2. **Outcome definitions.** `post_meal_peak`: the highest cleaned reading from the meal's start up to 150 minutes after it, at least one reading. `non_meal_mean`: readings more than 180 minutes after the last logged meal of any kind, including readings before the first meal. Day and hour outcomes need at least one reading. A day with fewer readings is not treated specially.
3. **Evaluability of an exposure.** A date-only exposure needs at least one record in the window (a window of 2 or 3 days is evaluable with one day present); a timestamped entry exposure is always evaluable (none = not exposed); a block exposure needs a block that has ended (else the unit is dropped, reason `unordered`).
4. **Library additions.** `sources.<token>.label_field` (where the meal label lives), `sources.<token>.clean: baseline`, `span_minutes` and `available_at: end_of_hour` for the hourly stream (spec 3.1 rule 8 puts the rule in the library config; spec 10 shows it in the patient block).
5. **Config.** `presence_flag_sources` maps each presence flag to a medication class or patient flag in the Rulebook Lookup config (needed for the presence check of the load check); `<name>_pick` keys and lists-of-strings blocks are read generically (the spec's `resting_heart_rate_pick` and `location`).
6. **Storage.** `relationship_evidence` has a surrogate `id` and a unique pair (`evidence_id`, `inputs_hash`), because a superseded record and its replacement share the same `evidence_id`.
7. **Extra record field.** `insufficient_reason` (`no_stream`, `history`, `small_group`, `no_variation`, `no_ordered_exposure`) on every record.

## Points for you (the spec or the data is inconsistent; I did not choose silently, and none of them blocks Stage 2b)

1. **Cross-reference.** 7.1 and property 14 cite "the ordering rule (3.1 rule 5)". In revision 2 the ordering rule is rule 6 (rule 5 is anchoring). Cosmetic.
2. **The 60-unit minimum, days or units.** The text of 7.2 says "fewer than 60 **usable units**"; the config key is `min_history_days: 60`. I applied the text. The consequence: the hourly relationship (about 17 units a day) reaches 60 usable units in the second week and is **tested from 2025-10-03**, which is why October and November contain `supported` records. If the key means a span of 60 days, the hourly relationship would start in December like the others. **Decision needed.**
3. **Section 14 counts.** "Never reaches the minimums (10 pairs)" omits `environment_entry@same_day->fluid_intake_day` (4 exposed days), which is also never tested; the same section's "Small groups" row does mention 4 weather days.
4. **A high share of `supported`.** 23% of all relationship-days (5,112) and 28 of 63 relationships on the last day are `supported`. Many exposure-outcome pairs on this patient have very small p-values because the data was generated with them (spec 14, "Synthetic data"), so the Benjamini-Hochberg family clears easily; the effect sizes of the same-day mood and symptom pairs are very large (for example `strained_period@same_day->hr_day_mean`, effect 1.6). The spec warned of few `supported`. I did not tune anything.
5. **The `supported` records on the borderline** (adjusted p between 0.09 and 0.10, like the sleep example above) flip between `supported` and `suggestive` from day to day because each day uses a new seed and a new family.
6. **Hourly units and the circular shift.** The hourly relationship has 7,920 units but only about 330 independent days; its p-value comes from circular shifts of the whole series, which keeps the daily rhythm but not the day-to-day structure of the steps. Its effect (0.086) is below the 0.10 floor, so it is `not_supported` on 2026-09-17 despite p = 0.0015.
