# PI, stage P1 report (code layer and replay driver)

## Amendments section of task/pi_spec.md (as printed at this stage)
 (master copy; decided after the Step 1 review)

These amendments resolve the points of `docs/findings_pi_step1_report.md` that concern PI, and say which Findings amendments (`findings_engine_spec.md`, Amendments) PI relies on. **Where the body of this document and an amendment differ, the amendment wins.** The repo copies of the specs are the master. Item numbers are the report's.

| # | Point | Resolution |
|---|---|---|
| 1 | File name | `findings_engine_spec.md` (renamed); the references in this document now resolve. |
| 2 to 12, 14 to 20 | Findings internals | Findings only; see `findings_engine_spec.md` Amendments. PI receives the finding record as amended there (`provisional: true`, `closed: false` on every stored version; `refs` as lists of `{view_id, context_id}`). |
| 13 | `seen_before` | PI's `get_seen_before(relationship_key, as_of, exclude_case=None)` returns the band of the latest `local_date` among the relationship's entries in all mid-term memories (open week included, written at or before `as_of`) and its long-term `last_seen`, **excluding `exclude_case`**; rolling 7 and 28 days (`this_week`, `recent_weeks`, else `earlier`; `none` if never). |
| 21 | Partial weeks and the end of the data | Only days that exist count (the data span: first to last day with an evidence record). The threshold is scaled to the same share, rounded up: `needed = ceil(5/7 x days_present)` (7 days: 5; 5 days: 4; 4 days: 3). **A week with fewer than 4 days of data is `insufficient` (never decisive).** A relationship's days before it was first tested count as `insufficient`. **A final weekly job runs at the end of the data** (on the replay clock, at the last day 23:59:59). Config `week.partial_week: {min_days: 4, scale_threshold: true}`. |
| 22 | Back-fill | Follows the rule: a relationship supported for weeks is created as `supported`, with its earlier weekly labels from the first week it was tested. Section 13 is rewritten accordingly. |
| 23 | Candidate with no path to `weakened` | Parked. |
| 24 | `evidence_refs` and counters | `evidence_refs` holds, for each decisive week in `weekly_labels`, the id of the last day of that week that has an evidence record (`rel|<key>|<date>|ev-v0`). Counters come from the latest entry of each case; a case that runs from Sunday into Monday keeps its `local_date`, its late version lands in the next open week, and its date is counted by the job that sees the entry. |
| 25 | Regeneration | Every `regenerate_every_weeks` weeks counted from the memory's creation week. |
| 26 | Check 6 | Compares only phrases that are not part of the relationship's own exposure or outcome phrases. A `text` is always an object `{sentences, source}`. |
| 27 | Entries and weeks | An entry belongs to the week that contains its `as_of`; counters use `local_date`; a sealed memory never changes. |
| 28, 29 | Overview wording and statuses | This spec wins over the overview's section 8. |
| 31 | End-of-day outcomes | Case `local_date` and Evidence `as_of_date` are both kept; counters use `local_date`. |
| T | View vocabulary (follows Findings amendment T) | No key or value of PI's text-layer view may be an internal word, and `exposure` / `exposures` join the internal-word list of check 4. The view's keys are renamed: `relationship` -> `link` (`exposure` -> `present`, `outcome` unchanged), `status` -> `state`, `status_change` -> `state_change`; the state words are `early` (candidate), `repeated` (supported), `fading` (weakened). The same names are used for the `earlier_conclusions` items that Findings shows its text layer (`about`, `state`, `text`, `seen_before`). Statuses in the stored memories keep their names. |
| W | View vocabulary, closing round (follows Findings amendment W) | `entangled`, `bundle`, `pair` and `points` join the internal-word list of check 4 and may not be a key or value of PI's view; PI's view and checks otherwise stay as in amendment T. |
| 35 | Consecutive-week counts | A count of consecutive weeks is the length of the **current run of equal decisive weekly labels** (`supported` or `not_supported`). A decisive label of the other kind **resets** the run (the new label starts a run of 1). `suggestive` and `insufficient` weeks, including a week with fewer than `min_days` of data, neither extend nor reset it. Promotion, weakening and re-promotion read the run (2 weeks). Retraction by `not_supported` counts the unbroken `not_supported` weeks **after** the week in which the status became `weakened` (6 further weeks); a decisive `supported` week resets that count. Retraction by `contrary` needs `contrary_days_per_week` (scaled like the week label) on 4 consecutive calendar weeks that each have at least `min_days` of data, counted from the week of weakening. `candidate` never goes to `weakened` (item 23, parked). A status is a pure function of the weekly labels from the first tested week: the incremental job and the back-fill give the same result. |
| 36 | Decisive weeks and `evidence_refs` | A decisive week is a week labelled `supported` or `not_supported`. The worked example in section 13 lists a `suggestive` week's id among the `evidence_refs`; that contradicts item 24, which wins: only decisive weeks contribute a ref. |
| 37 | What is written, and when | A new version of a long-term memory is written when it is created or when its status, counters, `flags_seen`, `finding_ids` or text change; a week whose only effect is one more weekly label writes nothing. A written version holds `weekly_labels` up to its own week. Extra keys (not statistics): in `weekly_labels` the counts `placebo_days`, `contrary_days` and `days_with_record`; in the memory `status_history` (every transition with its week, the back-filled ones included) and `dates` (the date lists behind the counters, each date with the case ids that made it, so a date counts once and a case can be excluded). Entries carry `relationships` (key, exposed, label, flags of each usable factor) next to `relationship_keys`. |
| 38 | Mid-term memory rows | `pi_mid_memories` has one row per `(memory_id, status)`: `open` is written when the week opens (first entry or first job), `sealed` when the job seals it; reads as-of use the latest row at or before `as_of`. Entries are unique by `finding_id` and by `(memory_id, case_id, entry_version)`; an entry whose `as_of` falls in a sealed week is an error. |
| 39 | Code text (P1) | Built from the phrase book's `pi_text` templates (one per status, all four required at load): candidate "may be linked to ... in her history" plus "This is an early observation."; supported "has repeatedly moved together with ... in her history"; weakened "no longer clearly seen"; retracted the fixed sentence of 8.2. `same_day_only` adds "on the same day" when the exposure phrase does not already say it. `text.source` is `code_text`. |
| 40 | Replay driver (P1) | The driver replays the stored Findings versions in `as_of` order (ties by `finding_id`), with the stored cleaned F2 text in mode `full` (the code line where a version has none) and the code line in mode `code_only`; case closings from the Findings `cases` table are events too (counted, no PI effect). Weekly jobs run for every week end that lies strictly before the next event; the first week is the week of the first day of the data; a final job runs at the last day of the data, 23:59:59. A progress table records what is done; every step is idempotent, so a restart continues and a repeat writes nothing. |
| 32 | The Evidence library is an input | Section 5 gains: **Evidence library** (config path), read only: for `same_day_only` (the pair's ordering) and the phrase-book load check. |
| 34 | `7d` window | Added to the shared phrase book. |
| P | Phrase book edits | As in the Findings Amendments (row P). |
| Q | Items not named | The Step 1 proposals are accepted as written. |


Weeks run: **51** (2025-W40 to 2026-W38); last job at `2026-09-17T23:59:59+05:30`. Long-term memories: **29**, versions written: 174.

## Mid-term memories per week

| week | entries (latest per case) | case-days | long-term created |
|---|---:|---:|---|
| 2025-W40 | 0 | 0 |  |
| 2025-W41 | 0 | 0 |  |
| 2025-W42 | 5 | 4 |  |
| 2025-W43 | 4 | 4 |  |
| 2025-W44 | 3 | 3 |  |
| 2025-W45 | 4 | 3 |  |
| 2025-W46 | 3 | 3 |  |
| 2025-W47 | 7 | 4 |  |
| 2025-W48 | 0 | 0 |  |
| 2025-W49 | 1 | 1 |  |
| 2025-W50 | 1 | 1 |  |
| 2025-W51 | 2 | 2 | 2 |
| 2025-W52 | 3 | 2 | 2 |
| 2026-W01 | 1 | 1 |  |
| 2026-W02 | 4 | 3 | 3 |
| 2026-W03 | 4 | 3 | 6 |
| 2026-W04 | 3 | 3 | 3 |
| 2026-W05 | 4 | 3 |  |
| 2026-W06 | 4 | 3 |  |
| 2026-W07 | 7 | 5 | 3 |
| 2026-W08 | 3 | 2 |  |
| 2026-W09 | 6 | 3 |  |
| 2026-W10 | 3 | 2 |  |
| 2026-W11 | 8 | 5 |  |
| 2026-W12 | 5 | 4 |  |
| 2026-W13 | 1 | 1 |  |
| 2026-W14 | 1 | 1 |  |
| 2026-W15 | 4 | 3 |  |
| 2026-W16 | 2 | 1 |  |
| 2026-W17 | 0 | 0 |  |
| 2026-W18 | 1 | 1 | 1 |
| 2026-W19 | 0 | 0 |  |
| 2026-W20 | 0 | 0 |  |
| 2026-W21 | 0 | 0 |  |
| 2026-W22 | 0 | 0 |  |
| 2026-W23 | 0 | 0 |  |
| 2026-W24 | 1 | 1 | 1 |
| 2026-W25 | 2 | 2 | 3 |
| 2026-W26 | 0 | 0 |  |
| 2026-W27 | 0 | 0 |  |
| 2026-W28 | 3 | 1 |  |
| 2026-W29 | 1 | 1 |  |
| 2026-W30 | 0 | 0 |  |
| 2026-W31 | 2 | 2 |  |
| 2026-W32 | 0 | 0 |  |
| 2026-W33 | 0 | 0 |  |
| 2026-W34 | 2 | 2 |  |
| 2026-W35 | 0 | 0 |  |
| 2026-W36 | 0 | 0 |  |
| 2026-W37 | 6 | 4 | 2 |
| 2026-W38 | 8 | 5 | 3 |

Totals: 119 entries, 89 case-days, 29 long-term memories created.

## Status counts at the end of each week (weeks with a memory)

| week | candidate | supported | weakened | retracted |
|---|---:|---:|---:|---:|
| 2025-W51 | 0 | 2 | 0 | 0 |
| 2025-W52 | 1 | 3 | 0 | 0 |
| 2026-W01 | 1 | 3 | 0 | 0 |
| 2026-W02 | 3 | 4 | 0 | 0 |
| 2026-W03 | 7 | 6 | 0 | 0 |
| 2026-W04 | 8 | 8 | 0 | 0 |
| 2026-W05 | 7 | 9 | 0 | 0 |
| 2026-W06 | 5 | 11 | 0 | 0 |
| 2026-W07 | 5 | 14 | 0 | 0 |
| 2026-W08 | 4 | 15 | 0 | 0 |
| 2026-W09 | 4 | 15 | 0 | 0 |
| 2026-W10 | 4 | 15 | 0 | 0 |
| 2026-W11 | 4 | 15 | 0 | 0 |
| 2026-W12 | 4 | 15 | 0 | 0 |
| 2026-W13 | 4 | 15 | 0 | 0 |
| 2026-W14 | 4 | 15 | 0 | 0 |
| 2026-W15 | 4 | 15 | 0 | 0 |
| 2026-W16 | 4 | 15 | 0 | 0 |
| 2026-W17 | 4 | 15 | 0 | 0 |
| 2026-W18 | 3 | 17 | 0 | 0 |
| 2026-W19 | 3 | 17 | 0 | 0 |
| 2026-W20 | 3 | 17 | 0 | 0 |
| 2026-W21 | 3 | 17 | 0 | 0 |
| 2026-W22 | 3 | 16 | 1 | 0 |
| 2026-W23 | 3 | 16 | 1 | 0 |
| 2026-W24 | 4 | 16 | 1 | 0 |
| 2026-W25 | 6 | 17 | 1 | 0 |
| 2026-W26 | 4 | 19 | 1 | 0 |
| 2026-W27 | 4 | 19 | 1 | 0 |
| 2026-W28 | 4 | 19 | 0 | 1 |
| 2026-W29 | 4 | 19 | 0 | 1 |
| 2026-W30 | 4 | 19 | 0 | 1 |
| 2026-W31 | 4 | 19 | 0 | 1 |
| 2026-W32 | 4 | 19 | 0 | 1 |
| 2026-W33 | 3 | 20 | 0 | 1 |
| 2026-W34 | 2 | 21 | 0 | 1 |
| 2026-W35 | 2 | 21 | 0 | 1 |
| 2026-W36 | 2 | 21 | 0 | 1 |
| 2026-W37 | 2 | 23 | 0 | 1 |
| 2026-W38 | 3 | 25 | 0 | 1 |

## Every status transition (from each memory's stored history; back-filled ones were found when the memory was created)

| week | relationship | from | to | found |
|---|---|---|---|---|
| 2025-W51 | `prior_day_glucose_mean@prev_day->fluid_intake_day` | candidate | supported | back-filled |
| 2025-W51 | `sleep_hours@prev_night->hr_day_mean` | candidate | supported | live |
| 2025-W51 | `sleep_hours@prev_night->non_meal_mean` | candidate | supported | back-filled |
| 2025-W51 | `sleep_hours@prev_night->resting_hr_day` | candidate | supported | back-filled |
| 2025-W51 | `steps_window_hourly@60m->hr_hour_mean` | candidate | supported | live |
| 2025-W52 | `late_prior_dinner@prev_evening->sleep_hours_night` | candidate | supported | back-filled |
| 2025-W52 | `sleep_hours@prev_night->post_meal_peak:breakfast` | candidate | supported | back-filled |
| 2025-W52 | `sleep_hours@prev_night->post_meal_peak:lunch` | candidate | supported | live |
| 2026-W04 | `strained_period@1d->non_meal_mean` | candidate | supported | live |
| 2026-W04 | `strained_period@same_day->missed_doses_day` | candidate | supported | live |
| 2026-W04 | `strained_period@same_day->sleep_hours_night` | candidate | supported | back-filled |
| 2026-W04 | `symptom_entry@3d->resting_hr_day` | candidate | supported | back-filled |
| 2026-W05 | `high_steps_day@1d->day_min_glucose` | candidate | supported | live |
| 2026-W06 | `strained_period@prev_day->resting_hr_day` | candidate | supported | live |
| 2026-W06 | `strained_period@same_day->hr_day_mean` | candidate | supported | live |
| 2026-W08 | `steps_total@prev_day->non_meal_mean` | candidate | supported | live |
| 2026-W17 | `sleep_hours@prev_night->systolic_reading` | candidate | supported | back-filled |
| 2026-W18 | `steps_total@1d->post_meal_peak:breakfast` | candidate | supported | live |
| 2026-W18 | `steps_total@1d->post_meal_peak:lunch` | candidate | supported | live |
| 2026-W22 | `hydration_total@prev_day->resting_hr_day` | candidate | supported | back-filled |
| 2026-W22 | `steps_window_hourly@60m->hr_hour_mean` | supported | weakened | live |
| 2026-W26 | `missed_dose@2d->post_meal_peak:dinner` | candidate | supported | live |
| 2026-W26 | `symptom_entry@same_day->fluid_intake_day` | candidate | supported | live |
| 2026-W28 | `steps_window_hourly@60m->hr_hour_mean` | weakened | retracted | live |
| 2026-W32 | `missed_dose@2d->systolic_reading` | candidate | supported | back-filled |
| 2026-W33 | `missed_dose@2d->non_meal_mean` | candidate | supported | live |
| 2026-W34 | `symptom_entry@3d->hr_day_mean` | candidate | supported | live |
| 2026-W35 | `hydration_total@prev_day->hr_day_mean` | candidate | supported | back-filled |

## Which relationships reach supported, and when

26 of 29 reach `supported` at some point; **3 stay `candidate` all year**: `non_home_day@same_day->missed_doses_day`, `sleep_hours@prev_night->missed_doses_day`, `sleep_hours@prev_night->post_meal_peak:dinner`.

| first supported in week | relationship | created in week | created as |
|---|---|---|---|
| 2025-W51 | `prior_day_glucose_mean@prev_day->fluid_intake_day` | 2026-W25 | supported |
| 2025-W51 | `sleep_hours@prev_night->hr_day_mean` | 2025-W51 | supported |
| 2025-W51 | `sleep_hours@prev_night->non_meal_mean` | 2026-W03 | supported |
| 2025-W51 | `sleep_hours@prev_night->resting_hr_day` | 2026-W02 | supported |
| 2025-W51 | `steps_window_hourly@60m->hr_hour_mean` | 2025-W51 | supported |
| 2025-W52 | `late_prior_dinner@prev_evening->sleep_hours_night` | 2026-W07 | supported |
| 2025-W52 | `sleep_hours@prev_night->post_meal_peak:breakfast` | 2026-W03 | supported |
| 2025-W52 | `sleep_hours@prev_night->post_meal_peak:lunch` | 2025-W52 | supported |
| 2026-W04 | `strained_period@1d->non_meal_mean` | 2026-W04 | supported |
| 2026-W04 | `strained_period@same_day->missed_doses_day` | 2026-W03 | candidate |
| 2026-W04 | `strained_period@same_day->sleep_hours_night` | 2026-W07 | supported |
| 2026-W04 | `symptom_entry@3d->resting_hr_day` | 2026-W07 | supported |
| 2026-W05 | `high_steps_day@1d->day_min_glucose` | 2026-W04 | candidate |
| 2026-W06 | `strained_period@prev_day->resting_hr_day` | 2026-W02 | candidate |
| 2026-W06 | `strained_period@same_day->hr_day_mean` | 2026-W03 | candidate |
| 2026-W08 | `steps_total@prev_day->non_meal_mean` | 2026-W03 | candidate |
| 2026-W17 | `sleep_hours@prev_night->systolic_reading` | 2026-W38 | supported |
| 2026-W18 | `steps_total@1d->post_meal_peak:breakfast` | 2026-W03 | candidate |
| 2026-W18 | `steps_total@1d->post_meal_peak:lunch` | 2025-W52 | candidate |
| 2026-W22 | `hydration_total@prev_day->resting_hr_day` | 2026-W37 | supported |
| 2026-W26 | `missed_dose@2d->post_meal_peak:dinner` | 2026-W24 | candidate |
| 2026-W26 | `symptom_entry@same_day->fluid_intake_day` | 2026-W25 | candidate |
| 2026-W32 | `missed_dose@2d->systolic_reading` | 2026-W38 | supported |
| 2026-W33 | `missed_dose@2d->non_meal_mean` | 2026-W25 | candidate |
| 2026-W34 | `symptom_entry@3d->hr_day_mean` | 2026-W04 | candidate |
| 2026-W35 | `hydration_total@prev_day->hr_day_mean` | 2026-W37 | supported |

Weakened at some point: **1**; retracted at some point: **1**; status at the end: supported 25, candidate 3, retracted 1.

## The first and the last partial weeks

- **first week 2025-W40**: job at `2025-10-05T23:59:59+05:30`; weekly labels of the memories whose latest stored version reaches this week: 29 x insufficient on 5 days.
- **last week 2026-W38**: job at `2026-09-17T23:59:59+05:30`; weekly labels of the memories whose latest stored version reaches this week: 1 x not_supported on 4 days, 2 x suggestive on 4 days, 11 x supported on 4 days.

## Code text of 12 long-term memories (final version unless stated)

- **same-day only, supported** `high_steps_day@1d->day_min_glucose` (version 4, status supported since 2026-02-01, flags ['placebo_fired', 'same_day_unverified'], created 2026-W04):
  > A very active day has repeatedly moved together with a lower lowest glucose that day in her history, on the same day.
- **same-day only, supported** `symptom_entry@same_day->fluid_intake_day` (version 2, status supported since 2026-06-28, flags ['same_day_unverified'], created 2026-W25):
  > A symptom noted in the diary on the same day has repeatedly moved together with lower fluid intake that day in her history.
- **closest to a contrary relationship: no memory has the flag in flags_seen; most contrary days in a week: 7** `hydration_total@prev_day->hr_day_mean` (version 2, status supported since 2026-08-30, flags [], created 2026-W37):
  > Low fluid intake the day before has repeatedly moved together with higher heart rate over the day in her history.
- **back-filled: created as supported** `missed_dose@2d->systolic_reading` (version 1, status supported since 2026-08-09, flags ['same_day_unverified'], created 2026-W38):
  > Missed doses on the same day or the day before have repeatedly moved together with higher blood pressure readings in her history.
- **candidate all year** `non_home_day@same_day->missed_doses_day` (version 1, status candidate since None, flags ['same_day_unverified'], created 2026-W02):
  > A day away from home may be linked to more missed doses that day in her history, on the same day. This is an early observation.
- **candidate all year** `sleep_hours@prev_night->missed_doses_day` (version 1, status candidate since None, flags ['same_day_unverified'], created 2026-W18):
  > Short sleep the night before may be linked to more missed doses that day in her history, on the same day. This is an early observation.
- **weakened (the version written at the week of weakening)** `steps_window_hourly@60m->hr_hour_mean` (version 17, status weakened since 2026-05-31, flags [], created 2025-W51):
  > More activity in the hour before and higher heart rate in that hour are no longer clearly seen together in her history.
- **supported** `hydration_total@prev_day->resting_hr_day` (version 2, status supported since 2026-05-31, flags [], created 2026-W37):
  > Low fluid intake the day before has repeatedly moved together with a higher resting heart rate in her history.
- **supported** `late_prior_dinner@prev_evening->sleep_hours_night` (version 7, status supported since 2025-12-28, flags ['placebo_fired'], created 2026-W07):
  > A late dinner the evening before has repeatedly moved together with shorter sleep that night in her history.
- **supported** `missed_dose@2d->non_meal_mean` (version 2, status supported since 2026-08-16, flags ['same_day_unverified'], created 2026-W25):
  > Missed doses on the same day or the day before have repeatedly moved together with higher glucose between meals in her history.
- **supported** `missed_dose@2d->post_meal_peak:dinner` (version 4, status supported since 2026-06-28, flags ['placebo_fired', 'same_day_unverified'], created 2026-W24):
  > Missed doses on the same day or the day before have repeatedly moved together with higher glucose peaks after dinner in her history.
- **supported** `prior_day_glucose_mean@prev_day->fluid_intake_day` (version 1, status supported since 2025-12-21, flags [], created 2026-W25):
  > Higher glucose the day before has repeatedly moved together with lower fluid intake that day in her history.

## Sealed mid-term memory 2026-W38

```json
{
 "case_days": [
  "2026-09-13",
  "2026-09-14",
  "2026-09-15",
  "2026-09-16",
  "2026-09-17"
 ],
 "entries": [
  {
   "case_id": "case_2026-09-13T07:00:00+05:30",
   "entry_version": 5,
   "finding_id": "fnd_case_2026-09-13T07:00:00+05:30_v5",
   "headline": "Heart rate was far above her usual after a busy day of festival preparation.",
   "local_date": "2026-09-13",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "symptom_entry@3d->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean"
   ],
   "relationships": [
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "suggestive",
     "relationship_key": "symptom_entry@3d->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    }
   ],
   "sentences": [
    "More activity in the hour before was present and high for her.",
    "Short sleep the night before has tended to move together with higher heart rate over the day, same day.",
    "A diary entry says she spent the previous day preparing for a festival and was genuinely highly active.",
    "The day's mood record is not known yet.",
    "An earlier summary says missed diabetes and thyroid medicines during a full day of festival prep."
   ]
  },
  {
   "case_id": "case_2026-09-14T06:15:00+05:30",
   "entry_version": 3,
   "finding_id": "fnd_case_2026-09-14T06:15:00+05:30_v3",
   "headline": "Morning high heart rate after a short night's sleep during a festival day",
   "local_date": "2026-09-14",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "symptom_entry@3d->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean",
    "strained_period@same_day->sleep_hours_night",
    "late_prior_dinner@prev_evening->sleep_hours_night",
    "sleep_hours@prev_night->resting_hr_day",
    "symptom_entry@3d->resting_hr_day",
    "strained_period@prev_day->resting_hr_day",
    "hydration_total@prev_day->resting_hr_day"
   ],
   "relationships": [
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "suggestive",
     "relationship_key": "symptom_entry@3d->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "strained_period@same_day->sleep_hours_night"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "late_prior_dinner@prev_evening->sleep_hours_night"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->resting_hr_day"
    },
    {
     "exposed": false,
     "flags": [
      "placebo_fired",
      "same_day_unverified"
     ],
     "label": "suggestive",
     "relationship_key": "symptom_entry@3d->resting_hr_day"
    },
    {
     "exposed": false,
     "flags": [
      "placebo_fired"
     ],
     "label": "suggestive",
     "relationship_key": "strained_period@prev_day->resting_hr_day"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->resting_hr_day"
    }
   ],
   "sentences": [
    "That morning her heart rate was clearly above her usual and resting heart rate was clearly above her usual, and she slept clearly less than usual.",
    "Short sleep the night before has tended to move together with a higher resting heart rate, same day.",
    "The day's mood record and last night's sleep are not known yet.",
    "She recorded a morning festival ritual and that she took the day off work."
   ]
  },
  {
   "case_id": "case_2026-09-15T05:15:00+05:30",
   "entry_version": 3,
   "finding_id": "fnd_case_2026-09-15T05:15:00+05:30_v3",
   "headline": "Morning heart rate was clearly above her usual after recent activity and events",
   "local_date": "2026-09-15",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean"
   ],
   "relationships": [
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    }
   ],
   "sentences": [
    "More activity in the hour before was present and was high for her.",
    "Short sleep the night before has tended to move together with higher heart rate over the day same day.",
    "A diary entry notes a religious installation ritual, that she took time off, and peak festival activity.",
    "The day's mood record is not known yet."
   ]
  },
  {
   "case_id": "case_2026-09-15T22:30:00+05:30",
   "entry_version": 1,
   "finding_id": "fnd_case_2026-09-15T22:30:00+05:30_v1",
   "headline": "Evening heart rate clearly above her usual",
   "local_date": "2026-09-15",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean"
   ],
   "relationships": [
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    }
   ],
   "sentences": [
    "That evening her heart rate was clearly above her usual.",
    "More activity in the hour before was present and high for her.",
    "Short sleep the night before has tended to move together with higher heart rate over the day, same day, and was among the very lowest she has had.",
    "Her diary notes she took the day off for a religious installation ritual starting a festival and records peak festival activity."
   ]
  },
  {
   "case_id": "case_2026-09-16T07:00:00+05:30",
   "entry_version": 2,
   "finding_id": "fnd_case_2026-09-16T07:00:00+05:30_v2",
   "headline": "Morning heart rate and blood pressure were clearly above her usual after a festive dinner.",
   "local_date": "2026-09-16",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean",
    "missed_dose@2d->systolic_reading",
    "sleep_hours@prev_night->systolic_reading"
   ],
   "relationships": [
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "missed_dose@2d->systolic_reading"
    },
    {
     "exposed": true,
     "flags": [],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->systolic_reading"
    }
   ],
   "sentences": [
    "Heart rate was clearly above her usual and blood pressure was clearly above her usual that day.",
    "More activity in the hour before was present and high for her.",
    "Short sleep the night before and missed doses on the same day or the day before may be linked to higher heart rate over the day and higher blood pressure readings, same day.",
    "The day's mood record and where the reading was taken are not known yet."
   ]
  },
  {
   "case_id": "case_2026-09-16T18:45:00+05:30",
   "entry_version": 1,
   "finding_id": "fnd_case_2026-09-16T18:45:00+05:30_v1",
   "headline": "Evening heart rate clearly above her usual after a pressured afternoon",
   "local_date": "2026-09-16",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean"
   ],
   "relationships": [
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    }
   ],
   "sentences": [
    "Her heart rate was clearly above her usual that evening.",
    "A stressed or low-mood period on the same day and short sleep the night before have tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart, and the short sleep was among the very lowest she has had.",
    "That afternoon she missed a proper lunch while facing overlapping work deadline and festival hosting pressure."
   ]
  },
  {
   "case_id": "case_2026-09-17T06:15:00+05:30",
   "entry_version": 4,
   "finding_id": "fnd_case_2026-09-17T06:15:00+05:30_v4",
   "headline": "Morning heart rate and resting heart rate were clearly above her usual.",
   "local_date": "2026-09-17",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean",
    "sleep_hours@prev_night->resting_hr_day",
    "symptom_entry@3d->resting_hr_day",
    "strained_period@prev_day->resting_hr_day",
    "hydration_total@prev_day->resting_hr_day"
   ],
   "relationships": [
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->resting_hr_day"
    },
    {
     "exposed": false,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "symptom_entry@3d->resting_hr_day"
    },
    {
     "exposed": true,
     "flags": [],
     "label": "supported",
     "relationship_key": "strained_period@prev_day->resting_hr_day"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->resting_hr_day"
    }
   ],
   "sentences": [
    "Heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning.",
    "More activity in the hour before was present and was high for her.",
    "A stressed or low-mood period on the same day and short sleep the night before have tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart.",
    "Short sleep the night before and a stressed or low-mood period the day before may be linked to a higher resting heart rate; they often occur together and their separate roles cannot be told apart, same day."
   ]
  },
  {
   "case_id": "case_2026-09-17T21:45:00+05:30",
   "entry_version": 2,
   "finding_id": "fnd_case_2026-09-17T21:45:00+05:30_v2",
   "headline": "Evening heart rate and glucose were clearly above her usual after a festive dinner",
   "local_date": "2026-09-17",
   "mode": "relationship",
   "relationship_keys": [
    "strained_period@same_day->hr_day_mean",
    "hydration_total@prev_day->hr_day_mean",
    "sleep_hours@prev_night->hr_day_mean",
    "missed_dose@2d->post_meal_peak:dinner",
    "sleep_hours@prev_night->post_meal_peak:dinner"
   ],
   "relationships": [
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "strained_period@same_day->hr_day_mean"
    },
    {
     "exposed": false,
     "flags": [],
     "label": "supported",
     "relationship_key": "hydration_total@prev_day->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->hr_day_mean"
    },
    {
     "exposed": true,
     "flags": [
      "same_day_unverified"
     ],
     "label": "supported",
     "relationship_key": "missed_dose@2d->post_meal_peak:dinner"
    },
    {
     "exposed": true,
     "flags": [],
     "label": "supported",
     "relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner"
    }
   ],
   "sentences": [
    "Her heart rate was clearly above her usual and her glucose was clearly above her usual that evening.",
    "More activity in the hour before was present.",
    "A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart.",
    "Missed doses on the same day or the day before and short sleep the night before were noted together.",
    "The day's step total is not known yet."
   ]
  }
 ],
 "memory_id": "pi_mid_2026-W38",
 "relationship_keys_touched": [
  "strained_period@same_day->hr_day_mean",
  "symptom_entry@3d->hr_day_mean",
  "hydration_total@prev_day->hr_day_mean",
  "sleep_hours@prev_night->hr_day_mean",
  "strained_period@same_day->sleep_hours_night",
  "late_prior_dinner@prev_evening->sleep_hours_night",
  "sleep_hours@prev_night->resting_hr_day",
  "symptom_entry@3d->resting_hr_day",
  "strained_period@prev_day->resting_hr_day",
  "hydration_total@prev_day->resting_hr_day",
  "missed_dose@2d->systolic_reading",
  "sleep_hours@prev_night->systolic_reading",
  "missed_dose@2d->post_meal_peak:dinner",
  "sleep_hours@prev_night->post_meal_peak:dinner"
 ],
 "sealed_at": "2026-09-17T23:59:59+05:30",
 "status": "sealed",
 "tier": "mid_term",
 "week": {
  "end": "2026-09-20",
  "iso": "2026-W38",
  "start": "2026-09-14"
 }
}
```

## Sealed mid-term memory 2025-W47

```json
{
 "case_days": [
  "2025-11-17",
  "2025-11-18",
  "2025-11-19",
  "2025-11-20"
 ],
 "entries": [
  {
   "case_id": "case_2025-11-17T00:15:00+05:30",
   "entry_version": 1,
   "finding_id": "fnd_case_2025-11-17T00:15:00+05:30_v1",
   "headline": "Nighttime heart rate was clearly above her usual after a dinner that day.",
   "local_date": "2025-11-17",
   "mode": "descriptive",
   "relationship_keys": [],
   "relationships": [],
   "sentences": [
    "Her heart rate was clearly above her usual at night.",
    "A symptom was present in the diary recently and the entry says it concerned her father rather than her.",
    "There is not enough history yet and no link can be claimed.",
    "Not known yet: the day's mood record and last night's sleep."
   ]
  },
  {
   "case_id": "case_2025-11-17T07:00:00+05:30",
   "entry_version": 2,
   "finding_id": "fnd_case_2025-11-17T07:00:00+05:30_v2",
   "headline": "Short sleep and raised heart rate were recorded after breakfast.",
   "local_date": "2025-11-17",
   "mode": "descriptive",
   "relationship_keys": [],
   "relationships": [],
   "sentences": [
    "She slept clearly less than usual and heart rate was clearly above her usual after a breakfast a short while earlier.",
    "Short sleep the night before, among the very lowest she has had, was present.",
    "A diary entry says a family member was unusually tired with reduced appetite the evening before, and a symptom noted in the diary on the same day or in the days before was present.",
    "There is not enough history yet, so no link is claimed.",
    "The day's mood record is not known yet."
   ]
  },
  {
   "case_id": "case_2025-11-17T21:00:00+05:30",
   "entry_version": 3,
   "finding_id": "fnd_case_2025-11-17T21:00:00+05:30_v3",
   "headline": "Evening had clearly fewer doses taken than usual; heart rate clearly above her usual; glucose was clearly above her usual.",
   "local_date": "2025-11-17",
   "mode": "descriptive",
   "relationship_keys": [],
   "relationships": [],
   "sentences": [
    "Clearly fewer doses were taken than usual in the evening; heart rate was clearly above her usual in the evening; glucose was clearly above her usual at night.",
    "A stressed or low-mood period on the same day was present.",
    "Missed doses in the week before and missed doses on the same day or the day before were present.",
    "Short sleep the night before, among the very lowest she has had, was present.",
    "Her diary describes that her father seemed unusually tired with reduced appetite at a family meal earlier, and the entry concerned someone else rather than her.",
    "There is not enough history yet and no link is claimed; where she was that day, the day's mood record, and last night's sleep are not known yet."
   ]
  },
  {
   "case_id": "case_2025-11-18T08:17:00+05:30",
   "entry_version": 3,
   "finding_id": "fnd_case_2025-11-18T08:17:00+05:30_v3",
   "headline": "Morning blood pressure and glucose were clearly above her usual after a lunch earlier",
   "local_date": "2025-11-18",
   "mode": "descriptive",
   "relationship_keys": [],
   "relationships": [],
   "sentences": [
    "Morning blood pressure was clearly above her usual and morning glucose was clearly above her usual after a lunch a couple of hours earlier.",
    "The size of this meal's rise was among the very highest she has had within the couple of hours after lunches.",
    "That day her diary says father was hospitalized overnight with chest pain and weakness and that this was a severe family crisis.",
    "An earlier diary entry describes her father as unusually tired and with low appetite at a family lunch in the days before and notes this was concerning and not her own symptom.",
    "Missed doses on the same day or the day before were present, short sleep the night before was present and among the very lowest she has had, a symptom noted in the diary on the same day or in the days before was present, and a stressed or low-mood period on the same day was present.",
    "There is not enough history yet and where the reading was taken, the day's mood record and the day's step total are not known yet, so no link can be claimed."
   ]
  },
  {
   "case_id": "case_2025-11-18T22:15:00+05:30",
   "entry_version": 8,
   "finding_id": "fnd_case_2025-11-18T22:15:00+05:30_v8",
   "headline": "High heart rates and high glucose coincided with low fluid intake after a recent lunch.",
   "local_date": "2025-11-18",
   "mode": "descriptive",
   "relationship_keys": [],
   "relationships": [],
   "sentences": [
    "Her evening heart rate was clearly above her usual, her resting heart rate in the morning was far above her usual, glucose at night was clearly above her usual, and clearly less fluid was taken at night than usual.",
    "That morning she noted a hospital day coordinating care and family logistics.",
    "That morning there is a note that her father was hospitalized overnight with chest pain and weakness and the entry concerns her father.",
    "There is not enough history yet, so no link is claimed.",
    "The day's mood record is not known yet.",
    "An earlier summary says medication adherence was markedly down and some medicines were missed."
   ]
  },
  {
   "case_id": "case_2025-11-19T22:45:00+05:30",
   "entry_version": 4,
   "finding_id": "fnd_case_2025-11-19T22:45:00+05:30_v4",
   "headline": "Evening heart rate and glucose were clearly above her usual after a breakfast earlier.",
   "local_date": "2025-11-19",
   "mode": "descriptive",
   "relationship_keys": [],
   "relationships": [],
   "sentences": [
    "Her heart rate was clearly above her usual in the evening and her glucose was far above her usual in the evening.",
    "The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts.",
    "That morning she recorded coordinating hospital care and family logistics and the day before she recorded that her father was hospitalized with chest pain and weakness, noted as a severe family crisis and involving someone else.",
    "An earlier summary says father hospitalized overnight was the major life event as sleep dropped sharply.",
    "There is not enough history yet and no link is claimed, and the day's step total is not known yet."
   ]
  },
  {
   "case_id": "case_2025-11-20T23:00:00+05:30",
   "entry_version": 2,
   "finding_id": "fnd_case_2025-11-20T23:00:00+05:30_v2",
   "headline": "Evening glucose and heart rate were clearly above her usual.",
   "local_date": "2025-11-20",
   "mode": "descriptive",
   "relationship_keys": [],
   "relationships": [],
   "sentences": [
    "Glucose was clearly above her usual in the evening, and heart rate was clearly above her usual in the evening.",
    "Missed doses on the same day or the day before was present; short sleep the night before was present; a stressed or low-mood period on the same day was present; low fluid intake the day before was present.",
    "Her diary that evening records a hospital day concerning her father improving and his initial night home, and an entry from the day before records coordinating care and family logistics.",
    "An earlier summary says hospital stay focused on managing care and family arrangements.",
    "There is not enough history yet, so no link is claimed.",
    "The day's step total is not known yet."
   ]
  }
 ],
 "memory_id": "pi_mid_2025-W47",
 "relationship_keys_touched": [],
 "sealed_at": "2025-11-23T23:59:59+05:30",
 "status": "sealed",
 "tier": "mid_term",
 "week": {
  "end": "2025-11-23",
  "iso": "2025-W47",
  "start": "2025-11-17"
 }
}
```