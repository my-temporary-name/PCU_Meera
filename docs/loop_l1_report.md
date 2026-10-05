# Stage L1 report: Findings reads PI as-of (the loop, code layer only)

Loop config `meera_iyer_v1-loop-f87efdcabd2d`. 284 versions in 116 cases, written by Findings running live in time order with PI; PI wrote to `output/pi_loop.db`, Findings to `output/findings_loop.db`. No model was called. PI reads are strict (a version sees only what was written strictly before its own time).

## As-of audits

- **clean**: {"findings": {"evidence": 738, "relationship": 2719, "completions": 6, "diary": 241, "state_memory": 734}, "pi": {"entries": 284, "versions": 174, "labels": 4948, "evidence_days_read": 34246, "evidence_refs": 2336, "runs": 51, "statuses": 174, "counters": 174}, "pi_reads": {"versions": 284, "repeat": 191, "long_term": 644, "open_week": 249, "sealed": 568}}


## Regression against F1 and P1

- **3b, all versions**: 284 F1 versions, 284 loop versions, same ids: True; versions that differ outside `repeat` and `refs.pi_memories`: **0** (labels, flags, exposure states, wording classes, groups, factor ids, mode, measures, case and version ids, text, diary and state-memory refs are identical)
- versions changed versus F1, by field: `repeat.pi_status` 153 entries, `repeat.seen_before` 160 entries, `refs.pi_memories` 284 versions; **284 of 284 versions differ in at least one of them**
- **3a, before the first long-term memory** (written 2025-12-21T23:59:59+05:30): 85 versions; structure outside `repeat` / `refs.pi_memories` identical to F1: yes; `pi_status` null everywhere: True; long-term refs: 0; `repeat` identical to F1 in 82 of them, `seen_before` changed in 3 (each explained by an entry of another case with that relationship in the open week: unexplained 0): fnd_case_2025-12-20T09:15:00+05:30_v2, fnd_case_2025-12-20T09:15:00+05:30_v3, fnd_case_2025-12-20T09:15:00+05:30_v4. `refs.pi_memories` is not empty in all of them (the open week and the sealed weeks are listed), so a strict byte comparison of the whole record differs only there
- **3c, PI against a P1 code-only run**: `pi_mid_memories` 102 / 102 rows identical; `pi_mid_entries` 284 / 284 rows identical; `pi_entry_keys` 729 / 729 rows identical; `pi_long_memories` 174 / 174 rows identical; `pi_weekly_runs` 51 / 51 rows identical
- statuses at the end, loop against P1: identical (29 memories): Counter({'supported': 25, 'candidate': 3, 'retracted': 1})

## What Findings now reads

- `repeat` entries by (PI status, seen_before): candidate / recent_weeks: 4, candidate / this_week: 2, supported / earlier: 7, supported / recent_weeks: 34, supported / this_week: 106, no memory / none: 31, no memory / this_week: 7
- views holding `earlier_conclusions`: **106 of 284** (items per view: 0: 178, 1: 59, 2: 30, 3: 10, 4: 3, 5: 3, 6: 1)
- views whose hash changed (current view code, with PI items against without): **106**: Findings texts L2 needs to write again. The other 178 views are unchanged, so their F2 texts stand (the cache key is the view hash plus prompt and checks)
- PI situations-line calls L2 would need (estimate from the P1 full run's 174 long-term versions, 173 not retracted): **85 versions have a diary-only sentence**, 85 distinct views (the cache sends identical views once). The sentences will change when L2 rewrites the Findings texts, and the chain of previous lines is not modelled

## Where the specs were ambiguous when Findings reads PI (decisions taken, to be written into the specs)

1. **Events at the same instant.** The specs say PI returns what was written "at or before `as_of`", but a version and PI's own writes can share a time (an entry is stamped with its version's `as_of`; the weekly job is stamped 23:59:59). A resume test showed that an inclusive read depends on whether the write already exists, so a rerun read something the first run did not. The loop reads strictly before (`PiReader(strict=True)`); the stored results of the other components are unchanged.
2. **State words.** Findings spec 8.1 names `early`, `repeated` and `fading` but not how they follow PI's statuses, and 7.6 says a retracted memory is mentioned only if today's label is usable, without a word for it. Config `pi_state_words`: candidate to early, supported to repeated, weakened to fading; a retracted memory has no word, so it is listed in `refs.pi_memories` but has no view id and no earlier conclusion (0 such references).
3. **Which relationships.** `repeat` (F1) covers claim-class factors only; 7.6 says "each usable factor". The long-term read covers every usable relationship factor in the version; an earlier conclusion is made for any of them the view shows. 29 earlier conclusions are about a shown factor that has no `repeat` entry; their `seen_before` band is read from PI when the view is built (as-of the version, its own case left out).
4. **`refs.pi_memories` has no specified shape.** Chosen: long-term entries (`memory_id`, `relationship_key`, `version`, `status`, `written_at`, and `view_id` when the view shows it), the open week (`memory_id`, the finding ids of its entries, only when it has any) and the last two sealed weeks (`memory_id`, `sealed_at`). The view is rebuilt from these exact versions.
5. **Seen before counts the open week** (Findings spec 13), so a version can have `seen_before` other than `none` before the first long-term memory exists (3 versions here), and the mid-term references are never empty after the first week. "Byte-identical before the first memory" therefore holds for everything except those.
6. **The situations line.** In L1 it is null, so the key is left out of the item (not `null`). The item's `text` is the association sentence(s) only.
7. **The mid-term reads** (open week, last two sealed weeks) are recorded as references but no L1 view shows them. Whether the text layer should show their headlines is open (the Findings spec table says "text and status only").
8. **Order of versions at the same time.** P1's replay driver orders entries by `(as_of, finding_id)`; the live loop uses the event order (hand-offs before completions). PI's tables come out identical anyway.

## Five examples of a view's `earlier_conclusions`

### fnd_case_2025-12-24T09:15:00+05:30_v1

```json
[
  {
    "id": "p1",
    "about": [
      "f5"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day.",
    "seen_before": "this_week"
  }
]
```

### fnd_case_2025-12-24T16:15:00+05:30_v1

```json
[
  {
    "id": "p1",
    "about": [
      "f1"
    ],
    "state": "repeated",
    "text": "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history.",
    "seen_before": "this_week"
  },
  {
    "id": "p2",
    "about": [
      "f5"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day.",
    "seen_before": "this_week"
  }
]
```

### fnd_case_2026-01-12T00:15:00+05:30_v5

```json
[
  {
    "id": "p1",
    "about": [
      "f17"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day.",
    "seen_before": "recent_weeks"
  }
]
```

### fnd_case_2026-01-12T00:15:00+05:30_v6

```json
[
  {
    "id": "p1",
    "about": [
      "f17"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day.",
    "seen_before": "recent_weeks"
  },
  {
    "id": "p2",
    "about": [
      "f23"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher glucose peaks after lunch in her history.",
    "seen_before": "recent_weeks"
  }
]
```

### fnd_case_2026-01-30T01:15:00+05:30_v5

```json
[
  {
    "id": "p1",
    "about": [
      "f4"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day.",
    "seen_before": "this_week"
  },
  {
    "id": "p2",
    "about": [
      "f8"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher glucose peaks after breakfast in her history.",
    "seen_before": "this_week"
  },
  {
    "id": "p3",
    "about": [
      "f15"
    ],
    "state": "repeated",
    "text": "Short sleep the night before has repeatedly moved together with higher glucose peaks after lunch in her history.",
    "seen_before": "recent_weeks"
  }
]
```

## Final statuses (loop, equal to P1 code-only)

| relationship | status |
|---|---|
| `high_steps_day@1d->day_min_glucose` | supported |
| `hydration_total@prev_day->hr_day_mean` | supported |
| `hydration_total@prev_day->resting_hr_day` | supported |
| `late_prior_dinner@prev_evening->sleep_hours_night` | supported |
| `missed_dose@2d->non_meal_mean` | supported |
| `missed_dose@2d->post_meal_peak:dinner` | supported |
| `missed_dose@2d->systolic_reading` | supported |
| `non_home_day@same_day->missed_doses_day` | candidate |
| `prior_day_glucose_mean@prev_day->fluid_intake_day` | supported |
| `sleep_hours@prev_night->hr_day_mean` | supported |
| `sleep_hours@prev_night->missed_doses_day` | candidate |
| `sleep_hours@prev_night->non_meal_mean` | supported |
| `sleep_hours@prev_night->post_meal_peak:breakfast` | supported |
| `sleep_hours@prev_night->post_meal_peak:dinner` | candidate |
| `sleep_hours@prev_night->post_meal_peak:lunch` | supported |
| `sleep_hours@prev_night->resting_hr_day` | supported |
| `sleep_hours@prev_night->systolic_reading` | supported |
| `steps_total@1d->post_meal_peak:breakfast` | supported |
| `steps_total@1d->post_meal_peak:lunch` | supported |
| `steps_total@prev_day->non_meal_mean` | supported |
| `steps_window_hourly@60m->hr_hour_mean` | retracted |
| `strained_period@1d->non_meal_mean` | supported |
| `strained_period@prev_day->resting_hr_day` | supported |
| `strained_period@same_day->hr_day_mean` | supported |
| `strained_period@same_day->missed_doses_day` | supported |
| `strained_period@same_day->sleep_hours_night` | supported |
| `symptom_entry@3d->hr_day_mean` | supported |
| `symptom_entry@3d->resting_hr_day` | supported |
| `symptom_entry@same_day->fluid_intake_day` | supported |
