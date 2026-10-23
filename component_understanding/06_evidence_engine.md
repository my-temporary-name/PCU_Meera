# 6. Evidence Engine

You can read Part A without opening any code. It explains the idea, the method and the labels in plain words, with real examples from this patient. Part B is the technical detail for engineers. Numbers come from `output/evidence_engine.db`, `docs/evidence_engine_stage_2a_report.md`, `docs/evidence_engine_stage_2b_report.md`, `task/evidence_engine_spec.md` (revision 3) and `understand/how_the_numbers_flow.md` §6, unless said otherwise.

---

# Part A. The idea in plain words

## A1. Where it sits, and the question it answers

By now the chain looks like this:

| Component | What it told us |
|---|---|
| Baseline Engine | what is **usual** for her |
| State Engine | **right now, something is off** (an alert, for example "glucose clearly above her usual at 22:30") |
| Rulebook Lookup | a **checklist** of factors that might be worth checking for that alert (sleep, a missed dose, stress, activity...) |
| **Evidence Engine** | **do those factors actually show up in her own data?** |

The Rulebook Lookup says "short sleep is a textbook candidate for a glucose high". That is general medicine. The Evidence Engine asks the personal question:

> **"In *her* own year of data, when she slept badly, did her glucose tend to be higher? Is that pattern strong enough to take seriously, or could it be luck?"**

It answers with **numbers and a label** for every factor on the checklist. It never says *why*, and it never says "this caused that".

## A2. The analogy: a careful fact-checker

Imagine a fact-checker handed a list of hunches about one patient: "maybe it's the sleep, maybe the stress, maybe a missed pill." The fact-checker does not argue about biology. They open the patient's own records and ask, for each hunch:

1. Is there **enough history** to say anything at all? (If not, they say "can't tell yet".)
2. Looking back over the year, does this hunch **line up** with the outcome more than you'd expect from coincidence?
3. If they **fake** the link on purpose, does the method still "find" it? (A test of the test.)
4. Since they are checking dozens of hunches, are they **fooling themselves** by taking the best-looking ones?

Then they write one line per hunch: *supported*, *suggestive*, *not supported* or *insufficient*, plus warnings. That is the Evidence Engine.

## A3. The key words

| Word | Plain meaning | Example |
|---|---|---|
| **Factor / exposure** | Something that happened *before* | she slept little last night; she missed a dose in the last 2 days |
| **Outcome** | The measured result we care about | the highest glucose after dinner; the day's resting heart rate |
| **Relationship** | One factor, over one look-back window, paired with one outcome | "sleep the previous night → glucose peak after dinner" |
| **Unit** | One row of the history: a meal, a day, an hour or a reading | each dinner of the year is one unit for the post-dinner peak |
| **History** | Everything *before* the date being judged | to judge 9 Sep, only 1 Oct to 7 Sep is used, never 9 Sep itself |
| **Label** | The verdict for one relationship on one day | supported, suggestive, not supported, insufficient |

**The list of relationships is fixed, not discovered.** The engine's library holds **69 entries**, one for each candidate in the rulebook. The Evidence Engine does not search for new factors. It only tests what the rulebook lists.

From those 69: 49 can be tested as a relationship, 11 are one-off checks about a single alert, 7 have no data definition yet (cycle phase, caffeine and so on), and 2 belong to the deferred screen-time rule. Seven of the 49 are glucose peaks after meals, and each is tested separately for breakfast, lunch and dinner. That gives **63 relationships** to re-test every day.

## A4. Two jobs on two clocks

**Job 1, the daily refresh (the relationships).** Once a day, for every day of the year, the engine re-tests all 63 relationships using **only her history up to that day**. 63 relationships × 352 days gives 22,148 daily records (fewer in the first two days, when some can't be built). The result for a day never depends on later days.

**Job 2, the alert evidence (one record per alert).** When the State Engine raises an alert, the Rulebook Lookup supplies its checklist. For each factor on that checklist the engine writes:
- the factor's label **for that day** (taken from the daily refresh),
- whether the factor was **actually present** around this alert (exposed / not exposed),
- and a few one-off checks about the alert itself.

So the daily refresh says "in general, does sleep matter for her dinner glucose?" and the alert record says "and was she short on sleep *this* time?"

## A5. How one relationship is tested, step by step

Worked example: **"how long she slept the previous night" → "the highest glucose after dinner"**, judged as of 9 Sep 2026. All numbers are real, from the stored record.

**Step 1. Build the history table.** One row per earlier dinner: the sleep that preceded it, and the glucose peak within 150 minutes after it. For 9 Sep there are **328 earlier dinners** (from 12 Oct 2025 to 7 Sep 2026). Rules that keep it honest:
- The factor must have **happened before** the meal began. A reading logged after the meal can't count as "the cause".
- A meal only enters the history **once its 150-minute window has fully ended**.
- Glucose is first cleaned with the Baseline Engine's rule, so sensor errors never enter a statistic.

**Step 2. Remove the slow trend ("detrending").** Her glucose changed a lot through the year (in the spec's worked example, from a prototype run, her dinner peaks fell from about 171 in October to about 142 in August, then rose again in September). Her sleep and other habits also drifted over the year. If both drift, they move together *by themselves* and look related, which is false evidence. So each outcome is replaced by its **difference from her own recent normal** (the median of her previous 30 days, of the same meal kind). On the first patient this roughly halved the effect sizes. The engine needs at least 10 earlier values to do it, so the first rows are dropped (10 were dropped here).

**Step 3. Measure the link ("effect").** For a yes/no factor (missed a dose: yes or no), the effect is how many standard deviations higher the outcome is when the factor is present. For a numeric factor like sleep hours, it is a rank correlation (Spearman). Both are oriented so that "worse sleep" and "worse glucose" point the same way. Here: **effect = 0.084**. That is small. The floor to count as a real effect is 0.10.

**Step 4. Ask "could this be luck?" ("circular-shift permutation").** Picture two calendars laid side by side: her sleep for every day and her post-dinner glucose for every day. Now **slide the sleep calendar forward by a random number of days**, wrapping around the end of the year, and measure the link again. Sliding breaks any real day-to-day pairing but **keeps the sleep calendar's own rhythm** (a bad week tends to follow a bad week). Do that 2,000 times. If the real alignment has a stronger link than almost every slide, it is unlikely to be chance. The p-value is the share of slides that did as well as the real one. Here: **p = 0.122**, meaning about 12% of random slides were at least as strong. Not impressive.

**Step 5. Correct for testing many things ("Benjamini-Hochberg").** On that day 48 relationships were tested. Test enough of anything and some will look good by luck. So the p-values are adjusted as a group. Here the adjusted p is **0.183**. The bar is 0.10.

**Step 6. The placebo (a test of the test).** The engine repeats the test once with the sleep calendar slid by a fixed 30% of the year. That pairing is meaningless by design. If even *that* "passes" as suggestive, the method is firing on noise for this relationship, so it gets the flag **`placebo_fired`** and is **not allowed to be labelled supported**. For sleep → dinner peak on 9 Sep the placebo did fire (placebo effect 0.102, p 0.073). Across the whole year about **8.6%** of placebos fired (993 of 11,584), which is an estimate of the engine's false-alarm rate.

> **What "placebo" means here (a plain-words box)**
>
> - **Not a medical term.** It is a *dummy test of the test*, borrowed from clinical trials, where a placebo group shows what happens when there is no real treatment.
> - **How it works.** Take the factor's calendar (for example her sleep) and slide it by exactly 30% of the history, wrapping the end back to the start, so sleep is deliberately paired with the *wrong* days. By construction there is no real link between those days. Then run the same test again.
> - **It never looks into the future.** The slide happens *inside the history table*, which holds only days **before** the day being judged (for 9 Sep 2026: 12 Oct 2025 to 7 Sep 2026). Both columns are old data re-paired with each other. Nothing after the as-of date is used, in the real test or in the placebo. A test (`tests/test_evidence_refresh.py`) cuts the store at the as-of date and checks the records come out identical.
> - **When it "fires".** If the dummy pairing also looks like a link (effect at least 0.10 and p at most 0.10), the method can produce a convincing-looking link from nothing for this relationship. It gets the flag `placebo_fired` and **cannot be labelled supported**.
> - **What it is not.** It is not proof that the real link is false. It is a caution flag that caps the strongest label. The placebo is also not part of the group of tests that p-values are corrected across.
> - **Real example.** Sleep → dinner glucose peak on 9 Sep 2026: real effect 0.084, placebo effect 0.102 (p 0.073). The fake pairing looked as strong as the real one, so the flag fired.

**Step 7. Give it a label.**

| Label | Plain meaning | Rule |
|---|---|---|
| **supported** | the link shows up in her history more than chance would explain | enough data; adjusted p ≤ 0.10; effect ≥ 0.10 in the expected direction; placebo did not fire |
| **suggestive** | looks like something, not strong enough after correcting for many tests | enough data; plain p ≤ 0.10 and effect ≥ 0.10, but adjusted p > 0.10, or the placebo fired |
| **not supported** | enough data, and the link did not show up | neither of the above |
| **insufficient** | can't tell | a minimum was not met |

**Result for 9 Sep:** effect 0.084 (below the 0.10 floor), p 0.122, adjusted p 0.183, placebo fired → **not supported**, flag `placebo_fired`.

**A telling detail.** On **17 Sep**, the same relationship came out **supported** (effect 0.113, adjusted p 0.096): barely over the line. The effect is small, so a relationship near the line flips between labels from day to day. A label is one moment's answer, not a belief. (A relationship changes label on average 0.28 times a week.) The Evidence Engine does not decide what to believe over time. That is PI's job.

## A6. "Enough history" and why it starts in December

A relationship is testable only with **at least 60 usable units and 60 different outcome dates**. For a yes/no factor, also at least 15 days exposed and 30 not exposed. Both the factor and the outcome must vary.

Consequence: although the data begins on 1 Oct 2025, **the first non-"insufficient" label appeared on 10 Dec 2025** (9 relationships that day, 19 the next). **October and November have no tested relationship at all.** Over the year, 48 of the 63 relationships were tested at some point. **15 never reached the minimums** (mainly alcohol pairs, where only a handful of days have an alcohol entry), and that is a legitimate result, not a defect.

## A7. The alert record, with a real example

Real alert: **glucose above her usual, 9 Sep 2026, 22:30**, last meal (dinner) 148 minutes before. The checklist from the Rulebook Lookup has 7 factors. The Evidence Engine's record for it:

| # | Factor (what the rulebook asked) | Label today | Flags | Was it present at this alert? |
|---|---|---|---|---|
| 1 | meal composition (how big was this meal's glucose response vs her earlier dinners?) | **not supported** | none | exposed. Glucose reached 171.8 at 148 minutes; her usual for that moment is a median of 162.4 and a 90th percentile of 180.5, so this is at the **77th percentile** of 339 earlier dinners. High-ish but not extreme; "supported" needs the 90th |
| 2 | medication adherence (missed dose in the last 2 days) | **suggestive** | `placebo_fired`, `same_day_unverified` | exposed: she missed levothyroxine that day |
| 3 | sleep (previous night) | not supported | `placebo_fired` | exposed: her sleep was in the worst 13% of her history |
| 4 | stress / mood | not supported | none | not exposed |
| 5 | activity (daily steps) | not supported | `same_day_unverified` | **not yet available**: the day's steps total only arrives at the end of the day |
| 6 | illness symptoms | not supported | `contrary` | not exposed |
| 10 | alcohol | **insufficient** | `small_group` | not exposed |

Also recorded: three candidates that were **not tested**, with their reasons (meal timing: cut by the budget; other medications and cycle phase: skipped by the packet).

How to read this as a person: *"For this alert, no factor is strongly backed by her own history. The nearest is the missed dose (suggestive only, and the test of the test fired). Sleep and the missed dose were both present, but the relationship in general isn't established. The steps total is still unknown."* The engine states exactly this much and no more.

## A8. The flags: warnings that limit what may be said later

| Flag | Meaning |
|---|---|
| `placebo_fired` | the fake test also "passed": treat as possible noise; can't be called supported |
| `same_day_unverified` | the factor and the outcome are on the same day and we can't prove which came first (for example a daily step total vs the day's glucose). 22 pairs carry this, so any later wording must say "on the same day", never "before" |
| `contrary` | the link points the **opposite** way (for example, on days with a symptom entry her dinner peak was *lower*) |
| `small_group` | too few exposed (or unexposed) days to test |
| entangled (in the alert's overlap list) | two supported factors nearly always occur together, so they can't be treated as two separate pieces of evidence |

## A9. What guards against fooling ourselves

1. **No look-ahead.** Every test uses only data that existed at that time. For the alert, a record that exists but hasn't arrived by 22:30 is "not yet available", never "not exposed".
2. **Ordering.** A factor counts only if it was recorded **before** the outcome's unit began. If no factor can come before it (no mood block ends before a morning blood-pressure reading), the relationship is `insufficient` on purpose.
3. **Detrending**, so a shared slow drift doesn't masquerade as a link.
4. **Sliding, not shuffling**, so day-to-day rhythms don't create fake significance.
5. **Correcting for many tests** as a group.
6. **The placebo** as a running estimate of the false-alarm rate.
7. **Fixed seeds** (derived from the relationship, the date and the method version), so a re-run gives identical numbers.
8. **Minimums**: a small sample can never produce a verdict.

## A10. What it deliberately does NOT do

- It does **not** say why, and it makes **no causal claim**. A label says how well a link shows up in her history.
- It does **not** decide what to believe over time ("candidate", "supported long-term" is PI's job).
- It does **not** group alerts into cases (Findings does that).
- It does **not** write wording and uses **no language model**. It is numbers only.
- It does **not** search for new factors, and it does **not** read PI, the baseline gists or the free text of diary entries (only the diary entry's category and time).
- It does **not** choose by the rulebook's priority tiers. Tiers and evidence levels pass through unchanged.

## A11. Honest caveats to keep in mind

- **The thresholds are placeholders** (0.10 effect floor, p 0.10, 60 units, 2,000 slides and so on). They are starting guesses, not clinical standards, and are meant to be tuned later against a scoring step against known ground truth. Do not tune them to produce findings.
- **Expect few strong labels.** After detrending, effects are small and a family of about 50 tests needs strong evidence. Many relationships being suggestive or not supported is a result, not a defect.
- **The data is synthetic.** Some of this patient's relationships were partly **built in** when her data was generated (for example heart rate from steps, sleep and mood; see `docs/hourly_steps_and_heart_rate_note.md`). The engine finds what was put there, so a supported label here is not proof that it "learned her". A ground-truth scoring step is needed to say how accurate the engine really is.
- **Same-day relationships are weak on order.** They are marked, and downstream wording must respect it.
- **A label is one moment.** It can change from day to day near the line. Stability over time is PI's concern.

## A12. Where its output goes

- The 287 alert records go to the **Findings Engine** (matched by `ev_<hand-off id>`), which groups alerts into cases and decides what may be said.
- The daily relationship labels go to **PI** (read by date), which turns them into weekly labels and long-term notes.

---

# Part B. Technical detail

## B1. Position in the system

```
Rulebook Lookup packets (output/rulebook_lookup.db, read-only)  ┐
State Engine hand-offs (output/state_engine.db, read-only)      ├─► EVIDENCE ENGINE ─► output/evidence_engine.db
Personal Data Store (raw_events, context_events, read-only)     │      relationship_evidence · event_evidence
config/evidence_library_v0.yaml (static, patient-independent)   │      event_completions · evidence_runs
config/evidence_meera_iyer_v1.yaml (this patient)               ┘
```

Not part of the LangGraph. Deterministic, uses **numpy** (declared), no LLM, no network. **Statistics live here and nowhere else.** Every downstream component holds `evidence_id` references. Read-only toward everything else. It writes only its own database.

```bash
uv run python -m v0_code.evidence_engine.run --config config/evidence_meera_iyer_v1.yaml --stage A     # daily refresh for every day, ~9 s, idempotent
uv run python -m v0_code.evidence_engine.run --config ... --stage B                                      # event evidence for every packet (287, ~1 s) + completions
uv run python -m v0_code.evidence_engine.run --config ... --stage A --from 2026-09-17 --to 2026-09-17   # one day
uv run python -m v0_code.evidence_engine.run --config ... --stage A --rebuild                            # drop the engine's own tables first (explicit)
```

Spec: `task/evidence_engine_spec.md` revision 3. Reports: `docs/evidence_engine_step1_report.md`, `_stage_2a_report.md`, `_stage_2b_report.md`. A synthetic second patient (`tests/evidence_synth.py`) runs on config alone, and a test scans the code for stream, measure, medicine and patient names (none allowed).

## B2. Modules (`src/v0_code/evidence_engine/`)

| Module | Role |
|---|---|
| `library.py` | Loads the static library and runs the **load check** (property 16) against the rulebook files |
| `config.py` | Patient config; also reads (never writes) the State and Baseline configs |
| `data.py` | Read-only store access through the patient's `stream_map`; cleans glucose with the Baseline rule; applies availability rules in one place |
| `windows.py` | Exposure windows, anchored to the outcome date or unit start, never to `opened_at` |
| `units.py` | Builds outcome units (meal, day, hour, reading) and detrends the outcome |
| `exposures.py` | Exposure values per unit, with the ordering rule |
| `history.py` | The history table of one relationship (`at(D)`), orients both sides, hashes the rows |
| `stats.py` | Effects, circular-shift permutation, placebo, Benjamini-Hochberg, labels |
| `refresh.py` | The daily refresh (D1–D5) |
| `events.py`, `event_checks.py` | Event evidence (E1–E6) and the event-level checks |
| `storage.py`, `loader.py`, `run.py` | Own database, load, CLI |

## B3. The library (static)

`config/evidence_library_v0.yaml` is static and patient-independent. It changes only when the rulebook changes or someone edits it on purpose. **At load, the engine checks it against the rulebook files** and fails with a plain message on any mismatch (unknown exposure or outcome, a rulebook candidate without a pair row, a `check_type` or `weight_tier` disagreement, a lookback tag that doesn't match, an unknown `Ordering` value, presence flags that differ from the Rulebook Lookup config).

**Pair table** (one row per rulebook candidate, 69 rows):

| V0 status | Meaning | Rows |
|---|---|---|
| `runnable` | a relationship with a history table and statistics | 49 (distinct keys) |
| `event_level` | a check about this event only | 11 |
| `no_definition` | no exposure defined in V0; reported `insufficient`, reason `no_definition` | 7 |
| `rule_deferred` | screen-time rule deferred; nothing tested | 2 |

49 runnable − 7 post-meal pairs + 7 × 3 meal kinds = **63 relationships**.

**Relationship key**: `<exposure_id>@<lookback_tag>-><outcome_id>[:<scope>]`, for example `sleep_hours@prev_night->post_meal_peak:dinner`. Lookback tags: `Nm`, `Nd`, `prev_night`, `prev_day`, `prev_evening`, `same_day`, `at_open`, `pmNm`.

**Outcomes** (every outcome is oriented so that **higher means worse**):

| Outcome | Unit | Definition | Worse is | Used by |
|---|---|---|---|---|
| `post_meal_peak` | meal | highest cleaned glucose within 150 min after a logged meal (scope: meal kind) | higher | glucose above, post-meal |
| `non_meal_mean` | day | mean cleaned glucose more than 180 min after any meal | higher | glucose above, no recent meal |
| `day_min_glucose` | day | lowest cleaned glucose of the day | lower | glucose below |
| `hr_hour_mean` | hour | mean continuous heart rate in the clock hour | higher | heart rate above (hourly exposure) |
| `hr_day_mean` | day | mean continuous heart rate over the day | higher | heart rate above (other exposures) |
| `resting_hr_day` | day | the day's resting heart rate (last value if two) | higher | resting heart rate above |
| `sleep_hours_night` | day | duration of the sleep record dated that day | lower | sleep below |
| `missed_doses_day` | day | number of missed doses | higher | medication adherence below |
| `systolic_reading` | reading | systolic value of each BP reading (diastolic unused in V0) | higher | blood pressure above |
| `fluid_intake_day` | day | the day's logged fluid in mL (outcome date = opened date − 1, since the value arrives at end of day) | lower | hydration below |

**Exposures** (each oriented so that higher means riskier; binary or continuous): `missed_dose`, `sleep_hours` (low is risky), `strained_period` (mood block in the strain list, counted only if the block ended before the unit's start), `steps_total` (low), `steps_window_hourly` (high, from the hourly stream, no fallback to daily), `high_steps_day` (≥ her 75th percentile), `symptom_entry`, `alcohol_entry`, `environment_entry` (diary category and time only), `hydration_total` (low), `screen_hours` (high), `late_meal`, `late_prior_dinner` (≥ 75th percentile of her start times), `non_home_day`, `prior_day_glucose_mean` (high), `clinic_reading`.

## B4. Time rules (spec 3.1)

1. **Outcome date** = local date of `opened_at`, except end-of-day outcomes (`fluid_intake_day`), whose date is the day before.
2. **History** = completed local days strictly before the outcome date. A unit with a forward window enters only when its whole window ended before the as-of start (so a dinner after 21:30 enters one day later).
3. **Event-time data** is limited to what was available at `opened_at`, using the State Engine's `available_at` rules (single source). Hourly steps carry their own rule in the library (`end_of_hour`).
4. **Anchoring.** Every window is anchored to the outcome date (day outcomes) or the unit start (meal, hour, reading). The packet's `resolved_window` is **not used**. The event-time exposure state records its `anchor` (`meal_start`, `hour_start`, `opened_at`, `outcome_date`).
5. **Ordering rule.** For meal, hour and reading units an exposure counts only if recorded at or before the unit's start (a mood block counts if it ended by then). Units with no such value are dropped, and a relationship with no unit that has any ordered exposure is `insufficient` (`no_ordered_exposure`). For **day-level units** nothing on the outcome's own date can be shown to come first, so everything in the window counts as **date-resolution** and the relationship carries `same_day_unverified`.
6. **Exposure shift.** For `sleep_hours_night` the night belongs to the day before, so windows are counted back from the day before.
7. **Replay and live use the same rules**: "now" is the hand-off's `opened_at`.

Ordering values across the 49 runnable pairs: `ordered` 25, `same_day_unverified` 22, `excludes_outcome_day` 1, `no_ordered_exposure` 1 (`strained_period@same_day->systolic_reading`, because BP is read around 08:00 and no mood block has ended by then).

## B5. The statistics (`stats.py`, `refresh.py`)

**History table (`history.py`).** One row per unit before the outcome date in time order; for meal units only meals of the event's kind. Exposure passes the ordering rule. A **trailing-median detrend** replaces the outcome by its difference from a baseline built only from earlier values, at least 10 required: day units use the previous 30 days; meal units the earlier meals of the same kind in the previous 30 days; hour units the same clock hour over the previous 30 days; reading units the previous 30 days' readings. Rows without enough earlier values are dropped. A meal with no meal kind has no relationship (`no_meal_kind`). Everything is hashed into `inputs_hash`.

**Effects.** Binary: standardized mean difference of the oriented outcome (exposed minus reference, pooled SD), plus the raw difference in the outcome's unit. Continuous: Spearman rank correlation. Effect floors: 0.10 for both forms.

**Circular-shift permutation.** The exposure series is rotated by a random offset (at least 5% of the series) 2,000 times. One-sided p = (1 + count of rotations at least as large as the real effect) / 2,001, so the smallest possible p is 1/2001. `p_contrary` is the same for the opposite direction; a negative effect with `p_contrary` ≤ 0.10 gets the `contrary` flag. All rotated effects come from **one FFT** (circular cross-correlation), not 2,000 recomputations. Seeds are **SHA-256 of key, as-of date and method version**, never Python's salted `hash`. Float tolerance (1e-9) so noise can't change a p.

**Multiplicity.** Benjamini-Hochberg at q = 0.10 across the **family**: all relationships refreshed that day that passed the minimums (`family_size` recorded; 48 on 17 Sep).

**Minimums** (`insufficient` unless all hold): at least **60 usable units AND 60 distinct outcome dates**; for binary, `n_exposed ≥ 15` and `n_reference ≥ 30`; the outcome (and a continuous exposure) must vary (`no_variation`). The `small_group` flag is set on an insufficient label caused by a small group, and on nothing else. The "30" in the detrend window delays the true start slightly.

**Placebo.** One run per tested relationship with the exposure rotated by exactly 30% of the series, its p read from the same null. If it meets the suggestive rule (p ≤ 0.10 and effect ≥ floor), the relationship gets `placebo_fired` and cannot be `supported`. Placebos are not part of the family. The daily run records the share fired.

**Labels** (`label_relationship`): `suggestive` if p ≤ 0.10 and effect ≥ floor; `supported` if also adjusted p ≤ 0.10 and the placebo did not fire; otherwise `not_supported`. `insufficient` is set earlier by the minimums.

**Overlap (event level).** Among `supported` / `suggestive` factors of one packet, one entry per unordered pair using the direction with the larger `share_given_a`. Binary exposures as they are, continuous ones as their worse quartile. Flag `entangled` if `share_given_a ≥ 0.25` and `ratio ≥ 2.0`.

## B6. Event evidence (`events.py`, `event_checks.py`; E1–E6)

1. **E1.** A packet with status `deferred` or `unmatched` gives a record with `factors: []`, and every candidate goes into `not_tested`. `ambiguous` is treated as normal.
2. **E2.** Work out the outcome date and make sure the relationship records for it exist (the engine can compute lazily).
3. **E3.** For each selected candidate in rank order, look it up by V0 status:
   - `runnable`: fetch the relationship record for the outcome date (its `support` and `flags`) and compute the **event exposure state** from data available at `opened_at`.
   - `event_level`: run the event-level check.
   - `no_definition`: `insufficient`, reason `no_definition`.
4. **E4.** Overlap among supported / suggestive factors.
5. **E5.** Copy the packet's `skipped` and `not_selected` into `not_tested` (`not_selected_budget`, `skipped_by_packet` with `packet_reason` / `packet_detail`, `rule_deferred`). Completeness: every candidate appears exactly once, in `factors` or `not_tested`.
6. **E6.** Write once. The record is **never changed afterwards**; late labels go into `event_completions`.

**Event-level checks:**

| Check | Candidates | What it does |
|---|---|---|
| `percentile_vs_history` | meal composition, meal skipped or delayed | compares this event with her history like for like. Meal composition: the highest glucose so far after the event meal, over the elapsed minutes (nearest 15-minute bucket), against the same elapsed-minutes peak after her earlier meals of the same kind. `supported` if percentile ≥ 90 and `history_n ≥ 30`; `insufficient` if `history_n < 30` |
| `shape_check` | sensor artifact (glucose low) | isolated reading, steep drop from steady values, rebound on the next reading. Needs readings after the event, so the record is `not_yet_available` and **completed later** (5 completions on this patient: 3 supported, 2 not supported) |
| `pattern_repeat` | dawn effect, regimen factors | descriptive frequencies over earlier days; dawn supported if share ≥ 0.5 over ≥ 14 days |
| `presence_check` | other medications, thyroid status, hypoglycemic agent | a fact from config; label `not_applicable`, result carries `present` |

**Event exposure state:** `exposed` (present, or in the worse quartile of her history for a continuous value), `not_exposed` (relevant records available and the factor absent), `not_yet_available` (record exists but hasn't arrived by `opened_at`; carries `available_at`), `no_data` (stream missing or no value; also the intentional `no_ordered_exposure` case). A window with some records available and one pending is `exposed` if any available record shows it, `not_yet_available` if none shows it and one is pending, `not_exposed` only if all are available and none shows it.

## B7. Output tables (`output/evidence_engine.db`)

| Table | Key | Holds |
|---|---|---|
| `relationship_evidence` | `evidence_id` = `rel\|<key>\|<as-of date>\|<method version>` (+ `inputs_hash`) | the daily record: history (`first_day`, `last_day`, `n_units`, `n_dates`, `n_dropped_by_detrend`), orientation, detrend, `n_exposed`, `n_reference`, `effect_kind`, `effect`, `raw_difference`, `permutation{p, p_contrary}`, `adjustment{family_size, p_adjusted}`, `support`, `insufficient_reason`, `flags`, `placebo{effect, p, fired}`, `method_version`, `config_version`, `inputs_hash`, `status` (current or superseded) |
| `event_evidence` | `ev_<handoff_id>` | `packet_id`, `rule_id`, `event_time`, `as_of_date`, `factors[]` (support, flags, `relationship_evidence_id`, `event_exposure`, `event_specific`), `overlap[]`, `not_tested[]`, `counts` |
| `event_completions` | `(evidence_id, candidate)` | late label of a check that needs later data; never alters the event record |
| `evidence_runs` | `(as_of_date, method_version)` | counts per label, tested, `family_size`, `placebo_tested`, `placebo_fired`, summary |

No table holds a wall-clock timestamp, so a re-run produces identical rows. A relationship record is **reused** for the same key, date, method version and `inputs_hash`; a changed hash marks the old record `superseded` and writes a new one. Reason codes on `insufficient`: `no_stream`, `history`, `small_group`, `no_variation`, `no_ordered_exposure`, `no_definition`, `no_meal_kind`, `no_meal`, `no_readings`, `no_relationship`, `not_in_library`.

## B8. Results on this patient

**Daily records:** 22,148 (63 relationships a day; 42 on day 1, 56 on day 2, 63 on each of the other 350 days). Two runs are identical row for row. Placebo fire rate **8.57%** (993 of 11,584).

| Label | Records |
|---|---|
| supported | 5,066 |
| suggestive | 1,122 |
| not supported | 5,396 |
| insufficient | 10,564 |

By month: supported grows from 0 in October and November to 192 in December and 794 in August. The first tested label is dated **2025-12-10**. On 17 Sep 2026: 63 relationships, 48 tested (family size 48), **28 supported, 2 suggestive, 18 not supported, 15 insufficient**. 48 of the 63 were tested at some point; 15 never reached the minimums.

**Alert evidence records:** 287 (covering 1,899 factors) plus 5 completions.

| Label | Factors |
|---|---|
| supported | 405 |
| suggestive | 91 |
| not supported | 356 |
| insufficient | 882 (no history 445, group too small 276, no definition 137, no ordered exposure 12, no meal kind 12) |
| not applicable (presence checks) | 160 |
| not yet available | 5 |

The 373 candidates skipped upstream by the packets never reach the Evidence Engine.

## B9. Gotchas and decisions to check before changing anything

1. **Do not tune thresholds to produce findings.** They are placeholders. Tune only against a scoring step with ground truth.
2. **The library is static and checked at load.** A mismatch with the rulebook fails loudly. Edit the library and the rulebook together.
3. **Both minimums apply**: 60 usable units **and** 60 distinct outcome dates. An hourly relationship has plenty of units within a week but still needs 60 days.
4. **Labels near the line flip.** `supported` and `suggestive` can alternate day to day (the effects are small). Never treat one day's label as a belief.
5. **`same_day_unverified`** (22 pairs) must flow into wording: "on the same day", never "before".
6. **The packet's `resolved_window` is not used.** Three `sleep_below` rows, five `hydration_below` rows and one `blood_pressure_above` row have lookbacks written for an item that opens at a different time of day. The Evidence Engine is unaffected, but the rulebook rows should be corrected later.
7. **A relationship with no ordered exposure** (the BP mood pair, and the breakfast scope of the mood pair) is intentionally `insufficient`.
8. **Event records are immutable.** Late labels go to `event_completions`.
9. **Meal-composition percentiles use her whole earlier history**, which is a limit for a patient whose level drifts.
10. **The 5 isolated 65.0 glucose readings** are not caught by the generic cleaning rule and stay in. Known upstream limit, reported and not patched.
11. **Synthetic-data caveat.** Part of the first patient's relationships was built in at data generation, so supported labels are not proof of learning. A ground-truth scoring step is needed (`docs/evidence_engine_scoring_report.md`).
12. **Tests**: `tests/test_evidence_library.py`, `test_evidence_stats.py`, `test_evidence_windows.py`, `test_evidence_refresh.py`, `test_evidence_events.py`, `test_evidence_real.py`.

## B10. Quick checks (read-only)

```bash
sqlite3 -readonly output/evidence_engine.db \
  "select json_extract(record_json,'$.support'), count(*) from relationship_evidence group by 1;"        # 5,066 / 1,122 / 5,396 / 10,564

sqlite3 -readonly output/evidence_engine.db \
  "select counts_json, family_size, placebo_fired from evidence_runs where as_of_date='2026-09-17';"

sqlite3 -readonly output/evidence_engine.db \
  "select record_json from event_evidence where evidence_id='ev_handoff_glucose_2026-09-09T22:30';"
```

Dashboard page: `#/stage/evidence`. Further reading: `docs/evidence_engine_stage_2a_tables.md` (per-month and per-relationship tables) and `docs/evidence_engine_scoring_report.md`.
