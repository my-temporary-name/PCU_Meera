# PI, stage P2 report: situations line from diary-only sentences (pp-v3, pck-v4)

25 long-term versions from `pi_text_sample_seed20260_8.jsonl`. Model `openai/gpt-5-mini`, reasoning low, 90 s timeout, no SDK retries, one retry; prompt `pp-v3`, checks `pck-v5`. The view is built only from sentences of the mid-term entries whose refs (read from the Findings database) cite diary items only.

## Totals

- versions with a model call: **11** of 25; without a call: 14 (13 no diary-only sentence: no call, null, 1 retracted: code text only, no call)
- versions with a non-null situations line: **11**; with a null line: **14** (13: no diary-only sentence: no call, null; 1: retracted: code text only, no call)
- first-attempt failures: **1 of 11** (check 5 (no_time_relative_words) 1)
- retried: 1; dropped to a null line after two failures: **0**
- every failure, both attempts, by check: check 5 1
- model calls 12; tokens in 7,815, out 5,992 (reasoning 5,184); call seconds 63; wall 32.2s
- of the 13 versions with no diary-only sentence: 1 had no entry citing the relationship that week, 12 had entries but none with a diary-only sentence
- every version's association is the P1 code text unchanged: True

## Zero-call rerun

`pi_text_sample_seed20260_9.jsonl`: from cache 11 of 11 versions that had a call, model calls 0; texts identical to the first run: True.

## Structured layer against P1

- `pi_mid_memories`: identical
- `pi_mid_entries`: identical
- `pi_entry_keys`: identical
- `pi_long_memories`: identical
- `pi_weekly_runs`: identical

## Scans of the stored situations lines

- words in a line that are not in the used sentences or the previous line (strict: any word; the check tolerates a stray word or two): **0** lines
- time-relative words (the check list): **0**
- words of the link's own phrase (stem match): **1** lines
  - pi_long_late_prior_dinner@prev_evening->sleep_hours_night v1: short
- claim or causal words: **0**
- lines that use a word from any relationship's phrase (heuristic, read by eye): 9
  - pi_long_steps_window_hourly@60m->hr_hour_mean v2: alcohol
  - pi_long_steps_window_hourly@60m->hr_hour_mean v3: alcohol
  - pi_long_steps_window_hourly@60m->hr_hour_mean v4: dinner
  - pi_long_late_prior_dinner@prev_evening->sleep_hours_night v1: period, short
  - pi_long_symptom_entry@3d->hr_day_mean v2: dinner
  - pi_long_sleep_hours@prev_night->post_meal_peak:lunch v1: alcohol
  - pi_long_strained_period@same_day->missed_doses_day v11: hour
  - pi_long_steps_total@1d->post_meal_peak:lunch v2: dinner
  - pi_long_strained_period@same_day->missed_doses_day v8: evening

## Old lines (`pi_text_sample_seed20260_6.jsonl`) next to the new ones, for the versions that have a line

### pi_long_steps_window_hourly@60m->hr_hour_mean version 2
- old: In the cases noted, the situations included a social alcohol occasion, holiday preparations, shopping and cooking.
- new: In the cases noted, the situations included a social alcohol occasion with friends, holiday preparations with family, shopping and cooking.

### pi_long_steps_window_hourly@60m->hr_hour_mean version 3
- old: In the cases noted, the situations included a social alcohol occasion, holiday preparations, shopping and cooking, a family celebration.
- new: In the cases noted, the situations included a social alcohol occasion with friends, holiday preparations with family, shopping and cooking, a brief family celebration.

### pi_long_steps_window_hourly@60m->hr_hour_mean version 4
- old: In the cases noted, the situations included traveling, sesame sweets with children, client dinner with wine, work trip with afternoon flight.
- new: In the cases noted, the situations included festival, sesame sweets with children, client dinner with a glass of wine, work trip with an afternoon flight.

### pi_long_steps_window_hourly@60m->hr_hour_mean version 6
- old: In the cases noted, the situations included extended family shopping.
- new: In the cases noted, the situations included extended family shopping.

### pi_long_late_prior_dinner@prev_evening->sleep_hours_night version 1
- old: In the cases noted, the situations included a short work period and hands-on wedding preparation with her parents.
- new: In the cases noted, the situations included a short work period, hands-on wedding preparation.

### pi_long_symptom_entry@3d->hr_day_mean version 2
- old: In the cases noted, the situations included a school call about slipping grades and attentiveness, and a difficult defensive conversation with her daughter after dinner.
- new: In the cases noted, the situations included a call about slipping grades and attentiveness, and a difficult, defensive conversation after dinner.

### pi_long_sleep_hours@prev_night->post_meal_peak:lunch version 1
- old: In the cases noted, the situations included a social alcohol occasion with friends.
- new: In the cases noted, the situations included a social alcohol occasion.

### pi_long_strained_period@same_day->missed_doses_day version 11
- old: In the cases noted, the situations included a holiday, cooler hour walk, reflected with her husband, felt proud of change since a health scare.
- new: In the cases noted, the situations included a holiday, a cooler hour walk, a change, a health scare.

### pi_long_steps_total@1d->post_meal_peak:lunch version 2
- old: In the cases noted, the situations included client restaurant dinner, work trip and flight.
- new: In the cases noted, the situations included a client restaurant dinner, a work trip, a flight.

### pi_long_strained_period@same_day->missed_doses_day version 8
- old: In the cases noted, the situations included spent an evening with her husband, felt relieved.
- new: In the cases noted, the situations included an evening.

### pi_long_sleep_hours@prev_night->hr_day_mean version 3
- old: In the cases noted, the situations included a brief family celebration and stayed up late.
- new: In the cases noted, the situations included a brief family celebration.

## The exact user message sent for three versions

### pi_long_steps_window_hourly@60m->hr_hour_mean version 3 (chain: 2 of 3)

```
VIEW:
{
  "link": {
    "present": "more activity in the hour before",
    "outcome": "higher heart rate in that hour"
  },
  "previous_situations": "In the cases noted, the situations included a social alcohol occasion with friends, holiday preparations with family, shopping and cooking.",
  "sentences": [
    "She had a brief family celebration the evening before and stayed up late.",
    "A diary entry records a social alcohol occasion with friends that afternoon.",
    "That evening she noted holiday preparations with family, shopping and cooking."
  ]
}
```

### pi_long_late_prior_dinner@prev_evening->sleep_hours_night version 1 (back-filled supported)

```
VIEW:
{
  "link": {
    "present": "a late dinner the evening before",
    "outcome": "shorter sleep that night"
  },
  "previous_situations": null,
  "sentences": [
    "She noted a short work period and hands-on wedding preparation with her parents the day before."
  ]
}
```

### pi_long_steps_window_hourly@60m->hr_hour_mean version 2 (chain: 1 of 3)

```
VIEW:
{
  "link": {
    "present": "more activity in the hour before",
    "outcome": "higher heart rate in that hour"
  },
  "previous_situations": null,
  "sentences": [
    "A diary entry records a social alcohol occasion with friends that afternoon.",
    "That evening she noted holiday preparations with family, shopping and cooking."
  ]
}
```

## Every sampled version: diary-only sentences, association and situations line

### chain: 1 of 3: `steps_window_hourly@60m->hr_hour_mean` version 2, 2025-W52, status supported

link: more activity in the hour before -> higher heart rate in that hour; previous line: none; diary-only sentences used: 2

- sentence 1: A diary entry records a social alcohol occasion with friends that afternoon.
- sentence 2: That evening she noted holiday preparations with family, shopping and cooking.
- **association (code text):** More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a social alcohol occasion with friends, holiday preparations with family, shopping and cooking.
- attempt 1: all checks pass

### chain: 2 of 3: `steps_window_hourly@60m->hr_hour_mean` version 3, 2026-W01, status supported

link: more activity in the hour before -> higher heart rate in that hour; previous line: In the cases noted, the situations included a social alcohol occasion with friends, holiday preparations with family, shopping and cooking.; diary-only sentences used: 3

- sentence 1: She had a brief family celebration the evening before and stayed up late.
- sentence 2: A diary entry records a social alcohol occasion with friends that afternoon.
- sentence 3: That evening she noted holiday preparations with family, shopping and cooking.
- **association (code text):** More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a social alcohol occasion with friends, holiday preparations with family, shopping and cooking, a brief family celebration.
- attempt 1: all checks pass

### chain: 3 of 3: `steps_window_hourly@60m->hr_hour_mean` version 4, 2026-W03, status supported

link: more activity in the hour before -> higher heart rate in that hour; previous line: none; diary-only sentences used: 3

- sentence 1: She observed a festival briefly while traveling and had sesame sweets with children on return.
- sentence 2: She had a client dinner with a glass of wine the day before in the evening.
- sentence 3: An entry says a work trip began that day with an afternoon flight.
- **association (code text):** More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included festival, sesame sweets with children, client dinner with a glass of wine, work trip with an afternoon flight.
- attempt 1: all checks pass

### same-day only: `sleep_hours@prev_night->non_meal_mean` version 3, 2026-W05, status supported

- no view: no diary-only sentence
- **association (code text):** Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### candidate: `non_home_day@same_day->missed_doses_day` version 1, 2026-W02, status candidate

- no view: no diary-only sentence
- **association (code text):** A day away from home may be linked to more missed doses that day in her history, on the same day. This is an early observation.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### supported: `steps_window_hourly@60m->hr_hour_mean` version 6, 2026-W06, status supported

link: more activity in the hour before -> higher heart rate in that hour; previous line: none; diary-only sentences used: 1

- sentence 1: She reports extended family shopping that morning.
- **association (code text):** More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included extended family shopping.
- attempt 1: all checks pass

### back-filled supported: `late_prior_dinner@prev_evening->sleep_hours_night` version 1, 2026-W07, status supported

link: a late dinner the evening before -> shorter sleep that night; previous line: none; diary-only sentences used: 1

- sentence 1: She noted a short work period and hands-on wedding preparation with her parents the day before.
- **association (code text):** A late dinner the evening before has repeatedly moved together with shorter sleep that night in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a short work period, hands-on wedding preparation.
- raw: In the cases noted, the situations included a short work period, hands-on wedding preparation (cleanup: full_stop_added)
- attempt 1: all checks pass

### weakened: `steps_window_hourly@60m->hr_hour_mean` version 17, 2026-W22, status weakened

- no view: no diary-only sentence
- **association (code text):** More activity in the hour before and higher heart rate in that hour are no longer clearly seen together in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### regenerated: `symptom_entry@3d->hr_day_mean` version 2, 2026-W28, status candidate

link: a symptom noted in the diary on the same day or in the days before -> higher heart rate over the day; previous line: none; diary-only sentences used: 2

- sentence 1: That afternoon she noted a school call about slipping grades and attentiveness.
- sentence 2: That evening she recorded a difficult, defensive conversation with her daughter after dinner.
- **association (code text):** A symptom noted in the diary on the same day or in the days before may be linked to higher heart rate over the day in her history. This is an early observation.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a call about slipping grades and attentiveness, and a difficult, defensive conversation after dinner.
- attempt 1: all checks pass

### placebo_fired: `strained_period@1d->non_meal_mean` version 5, 2026-W09, status supported

- no view: no diary-only sentence
- **association (code text):** A stressed or low-mood period on the same day has repeatedly moved together with higher glucose between meals in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### retracted: `steps_window_hourly@60m->hr_hour_mean` version 18, 2026-W28, status retracted

- retracted: no view
- **association (code text):** This link, once suspected, is no longer supported by her history.
- **situations line** (`code_text_retracted`; retracted: code text only, no call): null

### seeded: `strained_period@1d->non_meal_mean` version 3, 2026-W06, status supported

- no view: no diary-only sentence
- **association (code text):** A stressed or low-mood period on the same day has repeatedly moved together with higher glucose between meals in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `sleep_hours@prev_night->post_meal_peak:lunch` version 1, 2025-W52, status supported

link: short sleep the night before -> higher glucose peaks after lunch; previous line: none; diary-only sentences used: 1

- sentence 1: A diary entry records a social alcohol occasion with friends that afternoon.
- **association (code text):** Short sleep the night before has repeatedly moved together with higher glucose peaks after lunch in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a social alcohol occasion.
- attempt 1: all checks pass

### seeded: `strained_period@same_day->missed_doses_day` version 11, 2026-W18, status supported

link: a stressed or low-mood period on the same day -> more missed doses that day; previous line: none; diary-only sentences used: 2

- sentence 1: That morning she noted a holiday and a cooler hour walk.
- sentence 2: The evening before she reflected with her husband and felt genuinely proud of change since an earlier health scare.
- **association (code text):** A stressed or low-mood period on the same day has repeatedly moved together with more missed doses that day in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a holiday, a cooler hour walk, a change, a health scare.
- attempt 1: check 5: the line uses the time-relative word 'earlier'
- attempt 2: all checks pass

### seeded: `sleep_hours@prev_night->post_meal_peak:lunch` version 3, 2026-W05, status supported

- no view: no diary-only sentence
- **association (code text):** Short sleep the night before has repeatedly moved together with higher glucose peaks after lunch in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `sleep_hours@prev_night->hr_day_mean` version 13, 2026-W13, status supported

- no view: no diary-only sentence
- **association (code text):** Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `steps_total@1d->post_meal_peak:lunch` version 2, 2026-W03, status candidate

link: low activity on the same day -> higher glucose peaks after lunch; previous line: none; diary-only sentences used: 1

- sentence 1: A client restaurant dinner the evening before was recorded as mild, and a work trip began the afternoon before with a flight.
- **association (code text):** Low activity on the same day may be linked to higher glucose peaks after lunch in her history. This is an early observation.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a client restaurant dinner, a work trip, a flight.
- attempt 1: all checks pass

### seeded: `missed_dose@2d->post_meal_peak:dinner` version 1, 2026-W24, status candidate

- no view: no diary-only sentence
- **association (code text):** Missed doses on the same day or the day before may be linked to higher glucose peaks after dinner in her history. This is an early observation.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `strained_period@same_day->missed_doses_day` version 8, 2026-W12, status supported

link: a stressed or low-mood period on the same day -> more missed doses that day; previous line: none; diary-only sentences used: 1

- sentence 1: The day before she spent an evening with her husband and felt relieved.
- **association (code text):** A stressed or low-mood period on the same day has repeatedly moved together with more missed doses that day in her history.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included an evening.
- attempt 1: all checks pass

### seeded: `strained_period@prev_day->resting_hr_day` version 1, 2026-W02, status candidate

- no view: no diary-only sentence
- **association (code text):** A stressed or low-mood period the day before may be linked to a higher resting heart rate in her history. This is an early observation.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `strained_period@same_day->hr_day_mean` version 15, 2026-W31, status supported

- no view: no diary-only sentence
- **association (code text):** A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `symptom_entry@3d->resting_hr_day` version 2, 2026-W10, status supported

- no view: no diary-only sentence
- **association (code text):** A symptom noted in the diary on the same day or in the days before has repeatedly moved together with a higher resting heart rate in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `strained_period@same_day->hr_day_mean` version 11, 2026-W14, status supported

- no view: no diary-only sentence
- **association (code text):** A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null

### seeded: `sleep_hours@prev_night->hr_day_mean` version 3, 2026-W01, status supported

link: short sleep the night before -> higher heart rate over the day; previous line: none; diary-only sentences used: 1

- sentence 1: She had a brief family celebration the evening before and stayed up late.
- **association (code text):** Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day.
- **situations line** (`ok`; model line, all checks passed): In the cases noted, the situations included a brief family celebration.
- attempt 1: all checks pass

### seeded: `steps_total@prev_day->non_meal_mean` version 5, 2026-W08, status supported

- no view: no diary-only sentence
- **association (code text):** Low activity the day before has repeatedly moved together with higher glucose between meals in her history.
- **situations line** (`no_diary_sentences`; no diary-only sentence: no call, null): null
