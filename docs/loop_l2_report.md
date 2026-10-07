# Stage L2 report: the loop with the models

Loop config `meera_iyer_v1-loop-bbb4550f6531`. Findings texts `p-v4` / checks `ck-v6`, PI situations lines `pp-v4` / `pck-v6`; model `openai/gpt-5-mini` (reasoning low, retries 1). Databases `output/findings_loop_full.db` and `output/pi_loop_full.db`.

## Totals

- versions: **284** in 116 cases; texts: 271 written by a model or kept (106 written in this run, 178 answers kept from F2 for unchanged views), **13 code-line fallbacks (4.6%, acceptance: at most 11 = 4%)**
- first-attempt failures (texts written in this run): **29 of 106** (structure 5, no_digits_dates_counts 1, no_causal_wording 2, no_copied_diary_or_internal_words 7, claim_level 4, no_repeated_phrase 14)
- PI situations lines: 174 memory versions; by status {'no_diary_sentences': 41, 'ok': 121, 'kept_previous_line': 11, 'code_text_retracted': 1}; model calls for 121 of them; first-attempt failures 5 (check 8 2, check 11 3)
- model calls: Findings 135, PI 126; tokens in 317,883, out 300,493 (reasoning 261,120); call seconds 2811; run time 13.5 min (wall 13 min)

## Fallbacks and their reasons

- `fnd_case_2026-01-12T00:15:00+05:30_v5`: attempt 1: no_repeated_phrase (sentence 1 uses the phrase 'short sleep the night before' more than once); no_repeated_phrase (sentence 1 uses the phrase 'higher glucose between meals' more than once) | attempt 2: claim_level (sentence 1 cites a same-day point but does not say 'same day')
- `fnd_case_2026-01-12T00:15:00+05:30_v7`: attempt 1: structure (there must be 2 to 8 sentences) | attempt 2: claim_level (sentence 1 cites a same-day point but does not say 'same day')
- `fnd_case_2026-01-30T01:15:00+05:30_v4`: attempt 1: no_repeated_phrase (sentence 4 uses the phrase 'short sleep the night before' more than once) | attempt 2: claim_level (sentence 2 cites a same-day point but does not say 'same day')
- `fnd_case_2026-02-14T06:00:00+05:30_v2`: attempt 1: no_copied_diary_or_internal_words (sentence 4 copies 7 or more words of a diary entry); no_repeated_phrase (sentence 2 uses the phrase 'a stressed or low-mood period the day before' more than once); no_repeated_phrase (sentence 2 uses the phrase 'short sleep the night before' more than once); no_repeated_phrase (sentence 2 uses the phrase 'a higher resting heart rate' more than once) | attempt 2: claim_level (sentence 1 cites a same-day point but does not say 'same day')
- `fnd_case_2026-03-04T01:15:00+05:30_v5`: attempt 1: claim_level (sentence 1 cites a same-day point but does not say 'same day') | attempt 2: no_repeated_phrase (sentence 1 uses the phrase 'more activity in the hour before' more than once); no_repeated_phrase (sentence 1 uses the phrase 'short sleep the night before' more than once)
- `fnd_case_2026-03-10T07:00:00+05:30_v2`: attempt 1: claim_level (sentence 3 cites a same-day point but does not say 'same day') | attempt 2: no_digits_dates_counts (the headline uses the counting word 'several'); no_repeated_phrase (sentence 1 uses the phrase 'a higher resting heart rate' more than once)
- `fnd_case_2026-03-17T07:00:00+05:30_v3`: attempt 1: claim_level (sentence 2 cites a same-day point but does not say 'same day') | attempt 2: claim_level (sentence 2 cites a same-day point but does not say 'same day')
- `fnd_case_2026-03-17T07:00:00+05:30_v5`: attempt 1: structure (there must be 2 to 8 sentences) | attempt 2: claim_level (sentence 3 cites a same-day point but does not say 'same day')
- `fnd_case_2026-04-06T07:00:00+05:30_v3`: attempt 1: no_causal_wording (sentence 3 uses the causal word 'cause') | attempt 2: no_causal_wording (sentence 5 uses the causal word 'cause'); claim_level (sentence 7 says 'has tended to move together with' (or 'moved together') but cites no point); claim_level (sentence 8 says 'has tended to move together with' (or 'moved together') but cites no point)
- `fnd_case_2026-09-12T20:15:00+05:30_v2`: attempt 1: no_repeated_phrase (sentence 2 uses the phrase 'a stressed or low-mood period on the same day' more than once); no_repeated_phrase (sentence 2 uses the phrase 'low fluid intake the day before' more than once); no_repeated_phrase (sentence 2 uses the phrase 'higher heart rate over the day' more than once) | attempt 2: no_copied_diary_or_internal_words (sentence 4 copies 7 or more words of a diary entry)
- `fnd_case_2026-09-17T06:15:00+05:30_v2`: attempt 1: no_repeated_phrase (sentence 3 uses the phrase 'a stressed or low-mood period the day before' more than once); no_repeated_phrase (sentence 3 uses the phrase 'short sleep the night before' more than once); no_repeated_phrase (sentence 3 uses the phrase 'a higher resting heart rate' more than once) | attempt 2: claim_level (sentence 2 cites a same-day point but does not say 'same day')
- `fnd_case_2026-09-17T06:15:00+05:30_v3`: attempt 1: no_copied_diary_or_internal_words (sentence 6 copies 7 or more words of a diary entry) | attempt 2: often_together_wording (sentence 3 cites a set whose members often occur together but does not say the items often occur together and their separate roles cannot be told apart)
- `fnd_case_2026-09-17T06:15:00+05:30_v4`: attempt 1: no_copied_diary_or_internal_words (sentence 6 copies 7 or more words of a diary entry); no_repeated_phrase (sentence 4 uses the phrase 'short sleep the night before' more than once) | attempt 2: no_repeated_phrase (sentence 3 uses the phrase 'a stressed or low-mood period on the same day' more than once); no_repeated_phrase (sentence 3 uses the phrase 'higher heart rate over the day' more than once); no_repeated_phrase (sentence 3 uses the phrase 'short sleep the night before' more than once)

## Texts that changed from F2

- 105 of 284 versions have a different text from F2: 105 of them have a view with earlier conclusions (106 such views in all). Of the 105, the p items in the view: 1 items: 59, 2 items: 29, 3 items: 10, 4 items: 3, 5 items: 3, 6 items: 1; p items cited in the text: 0 cited: 28, 1 cited: 54, 2 cited: 19, 3 cited: 4
- versions whose text cites at least one p item: 77; versions whose view has p items but whose text cites none: 29

## Regression

- against F1 (labels, flags, exposure states, wording classes, groups, factor ids, mode, measures, case and version ids): versions that differ outside `repeat` and `refs.pi_memories`: **0 of 284**
- structured layer (`findings` rows) identical to L1: **284 of 284**
- PI against L1: `pi_mid_memories` 35 rows differ; `pi_mid_entries` 271 rows differ; `pi_entry_keys` identical; `pi_long_memories` identical; `pi_weekly_runs` identical; final statuses identical: True; status transitions identical: True

## Scans of the final Findings texts

- a headline or sentence containing "repeatedly" or "moved together": **0**
- sentences stronger than their class or with claim wording and no claim-class point (heuristic scan): **0**
- "this has come up before" or "an early observation" without a p ref: **0**
- explanation or reason words: **0**
- artifact sentences linked to a claim, an earlier summary or an earlier conclusion: **0**
- clinical terms not in the view: **0**

## Audits

- as-of audits (evidence, diary, state memory, PI labels, strict PI reads): **clean** {"findings": {"evidence": 738, "relationship": 2719, "completions": 6, "diary": 241, "state_memory": 734}, "pi": {"entries": 284, "versions": 174, "labels": 4948, "evidence_days_read": 34246, "evidence_refs": 2336, "runs": 51, "statuses": 174, "counters": 174}, "pi_reads": {"versions": 284, "repeat": 191, "long_term": 644, "open_week": 249, "sealed": 568}}
- model-call ordering (barriers in order, a text written after the memory it cites and after its situations line, lines built only from entries written by their barrier, entry text equals the Findings text): **clean** {"barriers": 51, "findings_texts": 284, "pi_lines": 174, "p_refs": 182, "unlogged": 0, "entries": 284}

## READ LIST

### (a) The cases of 2025-11-17 to 2025-11-20 (the hospitalization week)

#### fnd_case_2025-11-17T00:15:00+05:30_v1  (as_of 2025-11-17T00:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Nighttime heart rate was clearly above her usual after a dinner that day.**

1. Her heart rate was clearly above her usual at night.  `['m1']`
2. A symptom was present in the diary recently and the entry says it concerned her father rather than her.  `['f3', 'd1', 'h1']`
3. There is not enough history yet and no link can be claimed.  `['h1']`
4. Not known yet: the day's mood record and last night's sleep.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-17T07:00:00+05:30_v1  (as_of 2025-11-17T07:00:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**She slept clearly less than usual that morning after an evening meal.**

1. She slept clearly less than usual in the morning.  `['m1']`
2. A stressed or low-mood period on the same day and a late dinner the evening before were present, and there is not enough history yet so no link is claimed.  `['f1', 'f2', 'h1']`
3. A diary entry noted her father seemed unusually tired with low appetite at a family lunch and the entry concerns someone else.  `['d1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-17T07:00:00+05:30_v2  (as_of 2025-11-17T08:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Short sleep and raised heart rate were recorded after breakfast.**

1. She slept clearly less than usual and heart rate was clearly above her usual after a breakfast a short while earlier.  `['m1', 'm2']`
2. Short sleep the night before, among the very lowest she has had, was present.  `['f11']`
3. A diary entry says a family member was unusually tired with reduced appetite the evening before, and a symptom noted in the diary on the same day or in the days before was present.  `['d1', 'f9']`
4. There is not enough history yet, so no link is claimed.  `['h1']`
5. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-17T21:00:00+05:30_v1  (as_of 2025-11-17T21:00:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening dose shortfall after a light dinner, with recent stress, missed doses, and poor sleep noted**

1. Clearly fewer doses were taken than usual in the evening after a light dinner a short while earlier.  `['m1']`
2. A stressed or low-mood period on the same day was present, missed doses in the week before was present, and short sleep the night before was present; there is not enough history yet so no link is claimed.  `['f2', 'f4', 'f5', 'h1']`
3. A diary entry says that at family lunch she noticed her father unusually tired and with low appetite, and that note concerns someone else.  `['d1']`
4. Not known yet: where she was that day.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-17T21:00:00+05:30_v2  (as_of 2025-11-17T23:45:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening saw missed doses and a higher than usual heart rate with other notes present**

1. In the evening clearly fewer doses were taken than usual and heart rate was clearly above her usual.  `['m1', 'm2']`
2. A stressed or low-mood period on the same day was present.  `['f2']`
3. A stressed or low-mood period on the same day was present.  `['f8']`
4. Short sleep the night before, among the very lowest she has had, was present.  `['f5']`
5. Short sleep the night before, among the very lowest she has had, was present.  `['f11']`
6. A symptom noted in the diary on the same day or in the days before was present.  `['f9']`
7. The diary entry described her father being unusually tired and low-appetite and concerned someone else.  `['d1']`
8. There is not enough history yet and no link is claimed.  `['h1']`
9. Not known yet: where she was that day.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-17T21:00:00+05:30_v3  (as_of 2025-11-18T00:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening had clearly fewer doses taken than usual; heart rate clearly above her usual; glucose was clearly above her usual.**

1. Clearly fewer doses were taken than usual in the evening; heart rate was clearly above her usual in the evening; glucose was clearly above her usual at night.  `['m1', 'm2', 'm3']`
2. A stressed or low-mood period on the same day was present.  `['f2', 'f8']`
3. Missed doses in the week before and missed doses on the same day or the day before were present.  `['f4', 'f15']`
4. Short sleep the night before, among the very lowest she has had, was present.  `['f5', 'f11']`
5. Her diary describes that her father seemed unusually tired with reduced appetite at a family meal earlier, and the entry concerned someone else rather than her.  `['d1', 'f9', 'f16']`
6. There is not enough history yet and no link is claimed; where she was that day, the day's mood record, and last night's sleep are not known yet.  `['h1', 'n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T08:17:00+05:30_v1  (as_of 2025-11-18T08:17:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Morning blood pressure reading was clearly above her usual**

1. Blood pressure was clearly above her usual in the morning.  `['m1']`
2. Missed doses on the same day or the day before were present.  `['f1']`
3. Short sleep the night before, among the very lowest she has had, was present.  `['f4']`
4. An earlier summary says medication adherence was markedly down and medicines were missed.  `['s1']`
5. There is not enough history yet to claim a link.  `['h1']`
6. It is not known yet where the reading was taken, and that morning she noted a severe family crisis with her father hospitalized for chest pain and weakness.  `['n1', 'd1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T08:17:00+05:30_v2  (as_of 2025-11-18T11:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Higher morning blood pressure and glucose with recent missed doses and very short sleep**

1. Blood pressure was clearly above her usual that morning and glucose was clearly above her usual that morning.  `['m1', 'm2']`
2. Missed doses on the same day or the day before was present.  `['f1', 'f8']`
3. Short sleep the night before, among the very lowest she has had, was present.  `['f4', 'f11']`
4. A diary entry noted someone else as unusually tired and with reduced appetite in the days before, and a symptom noted in the diary on the same day or in the days before was present.  `['d2', 'f9']`
5. Her father was admitted overnight for chest symptoms and marked weakness that day.  `['d1']`
6. There is not enough history yet so no link can be claimed, and it is not yet known where the reading was taken or the day's mood record.  `['h1', 'n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T08:17:00+05:30_v3  (as_of 2025-11-18T15:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Morning blood pressure and glucose were clearly above her usual after a lunch earlier**

1. Morning blood pressure was clearly above her usual and morning glucose was clearly above her usual after a lunch a couple of hours earlier.  `['m1', 'm2']`
2. The size of this meal's rise was among the very highest she has had within the couple of hours after lunches.  `['f13', 'm2']`
3. That day her diary says father was hospitalized overnight with chest pain and weakness and that this was a severe family crisis.  `['d1']`
4. An earlier diary entry describes her father as unusually tired and with low appetite at a family lunch in the days before and notes this was concerning and not her own symptom.  `['d2', 'f9', 'f18']`
5. Missed doses on the same day or the day before were present, short sleep the night before was present and among the very lowest she has had, a symptom noted in the diary on the same day or in the days before was present, and a stressed or low-mood period on the same day was present.  `['f1', 'f4', 'f8', 'f11', 'f14', 'f15', 'f9', 'f18', 'f16']`
6. There is not enough history yet and where the reading was taken, the day's mood record and the day's step total are not known yet, so no link can be claimed.  `['h1', 'n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v1  (as_of 2025-11-18T22:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening heart rate was clearly above her usual after a light dinner.**

1. Her heart rate was clearly above her usual in the evening.  `['m1']`
2. A stressed or low-mood period on the same day was present.  `['f2']`
3. A symptom noted in the diary on the same day or in the days before was present, and the diary entry described her father unusually tired with low appetite at a family lunch and concerned someone else.  `['f3', 'd2']`
4. Short sleep the night before was present, among the very lowest she has had.  `['f5']`
5. An earlier summary says medication adherence was markedly down and multiple medicines were missed.  `['s1']`
6. There is not enough history yet, so no link can be claimed.  `['h1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v2  (as_of 2025-11-19T00:00:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening heart rate was high and night fluid intake was lower after a light dinner.**

1. Her heart rate was clearly above her usual in the evening and clearly less fluid was taken than usual at night after a light dinner earlier.  `['m1', 'm2']`
2. Short sleep the night before, among the very lowest she has had, was present.  `['f5']`
3. A stressed or low-mood period on the same day was present.  `['f2']`
4. A symptom noted in the diary on the same day or in the days before was present, and the diary describes her father as unusually tired with low appetite rather than her being unwell.  `['f3', 'd2']`
5. A day away from home was present.  `['f10']`
6. There is not enough history yet, so no link is claimed.  `['h1']`
7. An earlier summary says medication adherence was markedly down and some medicines were missed.  `['s1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v3  (as_of 2025-11-19T04:00:00+05:30, mode descriptive, text `llm`, from prompt p-v3)

**Evening heart rate rise with low night fluid intake after a difficult day**

1. Her heart rate was clearly above her usual in the evening and clearly less fluid was taken than usual at night.  `['m1', 'm2']`
2. Her morning diary reports a severe family crisis when her father was admitted overnight with chest pain and weakness.  `['d1']`
3. A stressed or low-mood period on the same day and a symptom noted in the diary on the same day or in the days before were present.  `['f2', 'f3']`
4. Low fluid intake the day before, among the very lowest she has had, and short sleep the night before, among the very lowest she has had, were present.  `['f4', 'f5']`
5. A day away from home was present.  `['f10']`
6. There is not enough history yet, so no link can be claimed.  `['h1']`
7. An earlier summary says medication adherence was markedly down and some medicines were missed.  `['s1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v4  (as_of 2025-11-19T04:30:00+05:30, mode descriptive, text `llm`, from prompt p-v3)

**Heart rate and glucose were clearly above her usual while less fluid was taken than usual.**

1. Heart rate was clearly above her usual in the evening.  `['m1']`
2. Clearly less fluid was taken than usual that night and glucose was clearly above her usual that night.  `['m2', 'm3']`
3. Her diary notes her father was hospitalized with chest pain and weakness and that this was severe and a family crisis.  `['d1']`
4. A stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before, short sleep the night before, a day away from home, missed doses on the same day or the day before, and low activity the day before were present, and there is not enough history yet so no link is claimed.  `['f2', 'f3', 'f4', 'f5', 'f10', 'f14', 'f18', 'h1']`
5. Not known yet: the day's mood record and last night's sleep.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v5  (as_of 2025-11-19T07:04:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening and night readings were notably off compared with her usual.**

1. Heart rate was clearly above her usual in the evening and resting heart rate was far above her usual in the morning.  `['m1', 'm4']`
2. Clearly less fluid was taken than usual at night and glucose was clearly above her usual at night.  `['m2', 'm3']`
3. That morning her diary notes a family crisis: her father was taken to hospital with chest pain and weakness.  `['d1']`
4. A stressed or low-mood period on the same day was present.  `['f2']`
5. A symptom noted in the diary on the same day or in the days before was present.  `['f3']`
6. An earlier summary says medication adherence was markedly down and medicines were missed, and there is not enough history yet so no link is claimed.  `['s1', 'h1']`
7. Not known yet: the day's mood record and last night's sleep.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v6  (as_of 2025-11-19T11:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening and night measures were clearly above her usual after a light dinner.**

1. Heart rate was clearly above her usual in the evening and resting heart rate was far above her usual in the morning.  `['m1', 'm4']`
2. Glucose was clearly above her usual at night and clearly less fluid was taken than usual at night.  `['m3', 'm2']`
3. That morning she had a hospital day coordinating care and family logistics.  `['d1']`
4. That morning her father was hospitalized overnight with chest pain and weakness, a severe family crisis concerning him.  `['d2']`
5. An earlier summary says medication adherence was markedly down and medicines were missed.  `['s1']`
6. There is not enough history yet and no link can be claimed.  `['h1']`
7. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v7  (as_of 2025-11-19T12:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening and night measures were clearly above her usual after a light dinner.**

1. Heart rate was clearly above her usual in the evening and resting heart rate was far above her usual in the morning.  `['m1', 'm4']`
2. Glucose was clearly above her usual at night and clearly less fluid was taken than usual at night.  `['m3', 'm2']`
3. That morning she had a hospital day coordinating care and family logistics.  `['d1']`
4. That morning her father was hospitalized overnight with chest pain and weakness, a severe family crisis concerning him.  `['d2']`
5. An earlier summary says medication adherence was markedly down and medicines were missed.  `['s1']`
6. There is not enough history yet and no link can be claimed.  `['h1']`
7. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-18T22:15:00+05:30_v8  (as_of 2025-11-19T13:45:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**High heart rates and high glucose coincided with low fluid intake after a recent lunch.**

1. Her evening heart rate was clearly above her usual, her resting heart rate in the morning was far above her usual, glucose at night was clearly above her usual, and clearly less fluid was taken at night than usual.  `['m1', 'm4', 'm3', 'm2']`
2. That morning she noted a hospital day coordinating care and family logistics.  `['d1']`
3. That morning there is a note that her father was hospitalized overnight with chest pain and weakness and the entry concerns her father.  `['d2']`
4. There is not enough history yet, so no link is claimed.  `['h1']`
5. The day's mood record is not known yet.  `['n1']`
6. An earlier summary says medication adherence was markedly down and some medicines were missed.  `['s1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-19T22:45:00+05:30_v1  (as_of 2025-11-19T22:45:00+05:30, mode descriptive, text `llm`, from prompt p-v3)

**Evening heart rate clearly above her usual after a light dinner.**

1. Her heart rate was clearly above her usual in the evening.  `['m1']`
2. A stressed or low-mood period on the same day was present.  `['f2']`
3. Low fluid intake the day before was present, and it was among the very lowest she has had.  `['f4']`
4. Short sleep the night before was present, and it was among the very lowest she has had.  `['f5']`
5. There is not enough history yet, so no link can be claimed.  `['h1']`
6. A morning diary entry that day says she was managing hospital care and family logistics and marks it severe.  `['d1']`
7. A morning diary entry the day before reports her father was hospitalized overnight with chest pain and weakness and marks it a severe family crisis.  `['d2']`
8. An earlier summary says father hospitalized overnight was the major life event as sleep dropped sharply.  `['s1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-19T22:45:00+05:30_v2  (as_of 2025-11-19T23:15:00+05:30, mode descriptive, text `llm`, from prompt p-v3)

**Evening heart rate and glucose were above her usual after a light dinner**

1. Heart rate was clearly above her usual and glucose was far above her usual in the evening.  `['m1', 'm2']`
2. That morning she was at the hospital coordinating family logistics and care, noted severe.  `['d1']`
3. The day before her father was hospitalized overnight for chest pain and weakness, noted severe family crisis and concerning for family members.  `['d2']`
4. A stressed or low-mood period on the same day, low fluid intake the day before among the very lowest she has had, short sleep the night before among the very lowest she has had, and missed doses on the same day or the day before were present; there is not enough history yet, so no link is claimed.  `['f2', 'f12', 'f4', 'f5', 'f11', 'f10', 'h1']`
5. The day's step total is not known yet.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-19T22:45:00+05:30_v3  (as_of 2025-11-20T03:15:00+05:30, mode descriptive, text `llm`, from prompt p-v3)

**Evening heart rate and glucose were above her usual after a light dinner**

1. Heart rate was clearly above her usual and glucose was far above her usual in the evening.  `['m1', 'm2']`
2. That morning she was at the hospital coordinating family logistics and care, noted severe.  `['d1']`
3. The day before her father was hospitalized overnight for chest pain and weakness, noted severe family crisis and concerning for family members.  `['d2']`
4. A stressed or low-mood period on the same day, low fluid intake the day before among the very lowest she has had, short sleep the night before among the very lowest she has had, and missed doses on the same day or the day before were present; there is not enough history yet, so no link is claimed.  `['f2', 'f12', 'f4', 'f5', 'f11', 'f10', 'h1']`
5. The day's step total is not known yet.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-19T22:45:00+05:30_v4  (as_of 2025-11-20T08:45:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening heart rate and glucose were clearly above her usual after a breakfast earlier.**

1. Her heart rate was clearly above her usual in the evening and her glucose was far above her usual in the evening.  `['m1', 'm2']`
2. The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts.  `['f16']`
3. That morning she recorded coordinating hospital care and family logistics and the day before she recorded that her father was hospitalized with chest pain and weakness, noted as a severe family crisis and involving someone else.  `['d1', 'd2']`
4. An earlier summary says father hospitalized overnight was the major life event as sleep dropped sharply.  `['s1']`
5. There is not enough history yet and no link is claimed, and the day's step total is not known yet.  `['h1', 'n1']`

- view's earlier conclusions: none

#### fnd_case_2025-11-20T23:00:00+05:30_v1  (as_of 2025-11-20T23:00:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening glucose was clearly above her usual.**

1. Her glucose was clearly above her usual in the evening.  `['m1']`
2. Missed doses on the same day or the day before, short sleep the night before, and a stressed or low-mood period on the same day were present.  `['f2', 'f3', 'f4']`
3. There is not enough history yet and no link is claimed.  `['h1']`
4. The day's step total is not known yet.  `['n1']`
5. An earlier summary says hospital stay focused on managing care and family arrangements.  `['s1']`
6. Diary notes mention a hospital stay with improving family situation that evening and coordination of care the day before.  `['d1', 'd2']`

- view's earlier conclusions: none

#### fnd_case_2025-11-20T23:00:00+05:30_v2  (as_of 2025-11-20T23:45:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Evening glucose and heart rate were clearly above her usual.**

1. Glucose was clearly above her usual in the evening, and heart rate was clearly above her usual in the evening.  `['m1', 'm2']`
2. Missed doses on the same day or the day before was present; short sleep the night before was present; a stressed or low-mood period on the same day was present; low fluid intake the day before was present.  `['f2', 'f3', 'f4', 'f11', 'f9', 'f12']`
3. Her diary that evening records a hospital day concerning her father improving and his initial night home, and an entry from the day before records coordinating care and family logistics.  `['d1', 'd2']`
4. An earlier summary says hospital stay focused on managing care and family arrangements.  `['s1']`
5. There is not enough history yet, so no link is claimed.  `['h1']`
6. The day's step total is not known yet.  `['n1']`

- view's earlier conclusions: none

### (b) The cases of 2026-09-14 to 2026-09-17

#### fnd_case_2026-09-14T06:15:00+05:30_v1  (as_of 2026-09-14T06:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Morning heart rate clearly above her usual after an earlier dinner**

1. Heart rate was clearly above her usual in the morning.  `['m1']`
2. She noted a ritual installation and that she had the day off, with peak festival activity mentioned.  `['d1']`
3. The day's mood record and last night's sleep are not yet known.  `['n1']`
4. There is enough history.  `['h1']`

- view's earlier conclusions: none

#### fnd_case_2026-09-14T06:15:00+05:30_v2  (as_of 2026-09-14T07:00:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**That morning she had higher heart rate and less sleep during a festival day**

1. That morning heart rate was clearly above her usual and she slept clearly less than usual.  `['m1', 'm2']`
2. She notes a morning religious installation ritual and that she took the day off for peak festival activity.  `['d1']`
3. The day's mood record and last night's sleep are not known yet.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2026-09-14T06:15:00+05:30_v3  (as_of 2026-09-14T07:22:00+05:30, mode relationship, text `llm`)

**Short sleep and high morning heart rates were recorded**

1. Heart rate was clearly above her usual, she slept clearly less than usual, and resting heart rate was clearly above her usual.  `['m1', 'm2', 'm3']`
2. Short sleep the night before has tended to move together with a higher resting heart rate same day.  `['f15']`
3. The day's mood record and last night's sleep are not known yet.  `['n1']`
4. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f15'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day." / situations: "a social day, a colorful day, an active day, a community ritual"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->resting_hr_day` v7 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Morning high heart rate after a short night's sleep during a festival day

#### fnd_case_2026-09-15T05:15:00+05:30_v1  (as_of 2026-09-15T05:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Heart rate clearly above her usual that morning.**

1. That morning, heart rate was clearly above her usual.  `['m1']`
2. The day before she had taken the day off for an idol installation and festival activity described as peak.  `['d1']`
3. The day's mood record and last night's sleep are not known yet.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2026-09-15T05:15:00+05:30_v2  (as_of 2026-09-15T06:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Morning heart rate clearly above her usual after a festive dinner**

1. That morning her heart rate was clearly above her usual.  `['m1']`
2. A diary entry from the day before says a religious installation ritual began and she took the day off for peak festival activity.  `['d1']`
3. The day's mood record and last night's sleep are not yet known.  `['n1']`

- view's earlier conclusions: none

#### fnd_case_2026-09-15T05:15:00+05:30_v3  (as_of 2026-09-15T09:15:00+05:30, mode relationship, text `llm`)

**Her morning heart rate was clearly above her usual.**

1. Heart rate was clearly above her usual in the morning.  `['m1']`
2. More activity in the hour before was present and high for her.  `['f1']`
3. Same day, short sleep the night before has tended to move together with higher heart rate over the day.  `['f5']`
4. This has come up before.  `['p1']`
5. The day's mood record is not known yet.  `['n1']`
6. A diary entry describes a Ganesh idol installation and the festival starting, and that she took the day off with peak festival activity.  `['d1']`

- view's earlier conclusions: 
  - `p1` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Morning heart rate was clearly above her usual after recent activity and events

#### fnd_case_2026-09-15T22:30:00+05:30_v1  (as_of 2026-09-15T22:30:00+05:30, mode relationship, text `llm`)

**Evening heart rate clearly above her usual after a festive dinner**

1. Heart rate was clearly above her usual in the evening.  `['m1']`
2. More activity in the hour before was present and was high for her.  `['f1']`
3. Short sleep the night before has tended to move together with higher heart rate over the day on the same day.  `['f5']`
4. A diary note said she spent the morning involved in a religious idol setup and took the day off for a festival, noting that day had peak activity.  `['d1']`
5. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Evening heart rate clearly above her usual

#### fnd_case_2026-09-16T07:00:00+05:30_v1  (as_of 2026-09-16T07:00:00+05:30, mode relationship, text `llm`)

**Higher than usual morning heart rate after a festive dinner that day.**

1. More activity in the hour before was present and high for her.  `['f1']`
2. Her heart rate was clearly above her usual in the morning that day.  `['m1']`
3. Same day, short sleep the night before has tended to move together with higher heart rate over the day.  `['f5']`
4. The day's mood record is not known yet.  `['n1']`
5. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Her morning heart rate was clearly above her usual.

#### fnd_case_2026-09-16T07:00:00+05:30_v2  (as_of 2026-09-16T08:13:00+05:30, mode relationship, text `llm`)

**Heart rate and blood pressure were above her usual that day.**

1. Heart rate was clearly above her usual that day.  `['m1']`
2. Blood pressure was clearly above her usual that day.  `['m2']`
3. More activity in the hour before was present that day.  `['f1']`
4. Short sleep the night before and missed doses on the same day or the day before often occur together and their separate roles cannot be told apart, same day.  `['g1']`
5. This has come up before.  `['p1']`
6. The day's mood record and where the reading was taken are not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Morning heart rate and blood pressure were clearly above her usual after a festive dinner.

#### fnd_case_2026-09-16T18:45:00+05:30_v1  (as_of 2026-09-16T18:45:00+05:30, mode relationship, text `llm`)

**Evening heart rate was clearly above her usual**

1. A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; same day each has tended to move together with higher heart rate over the day  `['g1']`
2. That day in the afternoon she noted missing a proper midday meal while facing deadline pressure and festival hosting, with layered stress  `['d1']`
3. This has come up before  `['p1', 'p2']`

- view's earlier conclusions: 
  - `p1` about ['f2'], state **repeated**, seen before: this_week: "A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history." / situations: "a longer family walk, a school call, a difficult defensive conversation with daughter, preparing for a festival"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
- PI notes drawn on: `pi_long_strained_period@same_day->hr_day_mean` v16 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Evening heart rate clearly above her usual after a pressured afternoon

#### fnd_case_2026-09-17T06:15:00+05:30_v1  (as_of 2026-09-17T06:15:00+05:30, mode descriptive, text `llm`, from prompt p-v1)

**Morning heart rate clearly above her usual after a light dinner and skipped midday meal**

1. That morning the heart rate was clearly above her usual.  `['m1']`
2. The day before she skipped a proper midday meal and experienced layered stress from work and hosting.  `['d1']`
3. It is not yet known what the day's mood record was or what last night's sleep was like.  `['n1']`
4. There is enough history recorded for her.  `['h1']`

- view's earlier conclusions: none

#### fnd_case_2026-09-17T06:15:00+05:30_v2  (as_of 2026-09-17T07:08:00+05:30, mode relationship, text `code_line`)

**Heart rate was clearly above her usual. Resting heart rate was clearly above her usual.**

1. Present: short sleep the night before (among the very lowest she has had), a stressed or low-mood period the day before.  `[]`
2. Short sleep the night before and a stressed or low-mood period the day before often occur together, so their separate roles cannot be told apart.  `[]`
3. Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day.  `[]`
4. A stressed or low-mood period the day before has tended to move together with a higher resting heart rate in her history.  `[]`
5. Not known yet: the day's mood record and last night's sleep.  `[]`

- view's earlier conclusions: 
  - `p1` about ['f9'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day." / situations: "a social day, a colorful day, an active day, a community ritual"
  - `p2` about ['f11'], state **repeated**, seen before: this_week: "A stressed or low-mood period the day before has repeatedly moved together with a higher resting heart rate in her history." / situations: "a social, a community ritual, an evening walk"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->resting_hr_day` v7 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_strained_period@prev_day->resting_hr_day` v8 (supported, written 2026-09-13T23:59:59+05:30)

#### fnd_case_2026-09-17T06:15:00+05:30_v3  (as_of 2026-09-17T08:45:00+05:30, mode relationship, text `code_line`)

**Heart rate was clearly above her usual. Resting heart rate was clearly above her usual.**

1. Present: short sleep the night before (among the very lowest she has had), a stressed or low-mood period the day before.  `[]`
2. Short sleep the night before and a stressed or low-mood period the day before often occur together, so their separate roles cannot be told apart.  `[]`
3. Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day.  `[]`
4. Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day.  `[]`
5. A stressed or low-mood period the day before has tended to move together with a higher resting heart rate in her history.  `[]`
6. Also present, with no link claimed: more activity in the hour before (high for her).  `[]`
7. Not known yet: the day's mood record.  `[]`

- view's earlier conclusions: 
  - `p1` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
  - `p2` about ['f9'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day." / situations: "a social day, a colorful day, an active day, a community ritual"
  - `p3` about ['f11'], state **repeated**, seen before: this_week: "A stressed or low-mood period the day before has repeatedly moved together with a higher resting heart rate in her history." / situations: "a social, a community ritual, an evening walk"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_sleep_hours@prev_night->resting_hr_day` v7 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_strained_period@prev_day->resting_hr_day` v8 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Higher than usual heart rate and resting heart rate that morning.

#### fnd_case_2026-09-17T06:15:00+05:30_v4  (as_of 2026-09-17T12:15:00+05:30, mode relationship, text `code_line`)

**Heart rate was clearly above her usual. Resting heart rate was clearly above her usual.**

1. Present: a stressed or low-mood period on the same day, short sleep the night before (among the very lowest she has had), a stressed or low-mood period the day before.  `[]`
2. A stressed or low-mood period on the same day and short sleep the night before often occur together, so their separate roles cannot be told apart.  `[]`
3. Short sleep the night before and a stressed or low-mood period the day before often occur together, so their separate roles cannot be told apart.  `[]`
4. A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history.  `[]`
5. Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day.  `[]`
6. Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day.  `[]`
7. A stressed or low-mood period the day before has tended to move together with a higher resting heart rate in her history.  `[]`
8. Also present, with no link claimed: more activity in the hour before (high for her).  `[]`

- view's earlier conclusions: 
  - `p1` about ['f2'], state **repeated**, seen before: this_week: "A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history." / situations: "a longer family walk, a school call, a difficult defensive conversation with daughter, preparing for a festival"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
  - `p3` about ['f9'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day." / situations: "a social day, a colorful day, an active day, a community ritual"
  - `p4` about ['f11'], state **repeated**, seen before: this_week: "A stressed or low-mood period the day before has repeatedly moved together with a higher resting heart rate in her history." / situations: "a social, a community ritual, an evening walk"
- PI notes drawn on: `pi_long_strained_period@same_day->hr_day_mean` v16 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_sleep_hours@prev_night->resting_hr_day` v7 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_strained_period@prev_day->resting_hr_day` v8 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Morning heart rate and resting heart rate were clearly above her usual.

#### fnd_case_2026-09-17T21:45:00+05:30_v1  (as_of 2026-09-17T21:45:00+05:30, mode relationship, text `llm`)

**Elevated evening heart rate after a festive dinner**

1. A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; they have tended to move together with higher heart rate over the day.  `['g1']`
2. That evening her heart rate was clearly above her usual.  `['m1']`
3. More activity in the hour before was present and high for her.  `['f1']`
4. Her diary notes a heavy deadline day with mostly desk work and few proper meals.  `['d1']`
5. She also notes skipping a proper lunch amid combined work and festival hosting pressure.  `['d2']`
6. This has come up before.  `['p1', 'p2']`

- view's earlier conclusions: 
  - `p1` about ['f2'], state **repeated**, seen before: this_week: "A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history." / situations: "a longer family walk, a school call, a difficult defensive conversation with daughter, preparing for a festival"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
- PI notes drawn on: `pi_long_strained_period@same_day->hr_day_mean` v16 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Evening heart rate clearly above her usual after a busy period.

#### fnd_case_2026-09-17T21:45:00+05:30_v2  (as_of 2026-09-17T22:30:00+05:30, mode relationship, text `llm`)

**Evening heart rate and glucose were clearly above her usual after a festive dinner**

1. Heart rate was clearly above her usual and glucose was clearly above her usual in the evening that day.  `['m1', 'm2']`
2. A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; same day they have tended to move together with higher heart rate over the day.  `['g1']`
3. The size of this meal's rise was among the very highest she has had within the hour or so after dinners.  `['f9']`
4. Missed doses on the same day or the day before and short sleep the night before may be linked to higher glucose peaks after dinner.  `['g2']`
5. More activity in the hour before was present and was high for her.  `['f1']`
6. A stressed or low-mood period on the same day was present.  `['f12']`
7. The day's step total is not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f2'], state **repeated**, seen before: this_week: "A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history." / situations: "a longer family walk, a school call, a difficult defensive conversation with daughter, preparing for a festival"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
  - `p3` about ['f10'], state **repeated**, seen before: recent_weeks: "Missed doses on the same day or the day before have repeatedly moved together with higher glucose peaks after dinner in her history."
- PI notes drawn on: `pi_long_strained_period@same_day->hr_day_mean` v16 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30); `pi_long_missed_dose@2d->post_meal_peak:dinner` v3 (supported, written 2026-09-13T23:59:59+05:30)

### (c) Cases in 2026-W22 that cite `steps_window_hourly@60m->hr_hour_mean`

0 cases: none

The long-term note of `steps_window_hourly@60m->hr_hour_mean` written by the job of 2026-W22:

- version 17, 2026-05-31T23:59:59+05:30, **weakened**: More activity in the hour before and higher heart rate in that hour are no longer clearly seen together in her history. **Situations:** In the cases noted, the situations included a local outdoor family event, lots of walking, a longer family walk.

### (c) Cases in 2026-W28 that cite `steps_window_hourly@60m->hr_hour_mean`

0 cases: none

The long-term note of `steps_window_hourly@60m->hr_hour_mean` written by the job of 2026-W28:

- version 18, 2026-07-12T23:59:59+05:30, **retracted**: This link, once suspected, is no longer supported by her history. (no situations line)

### (d) A week with no findings and the mid-term memory of the following week

Week 2025-W48 had no entries (16 such weeks: 2025-W40, 2025-W41, 2025-W48, 2026-W17, 2026-W19, 2026-W20, 2026-W21, 2026-W22, 2026-W23, 2026-W26, 2026-W27, 2026-W30, 2026-W32, 2026-W33, 2026-W35, 2026-W36). The mid-term memory of the following week, 2025-W49:

`pi_mid_2025-W49` sealed 2025-12-07T23:59:59+05:30, relationships touched: [], case days ['2025-12-02']

- `fnd_case_2025-12-02T19:15:00+05:30_v1` (descriptive): **Evening heart rate was clearly above her usual after a lunch earlier.** Heart rate was clearly above her usual in the evening. More activity in the hour before was present and was among the very highest she has had. Low fluid intake the day before was present and was low for her. The day's mood record is not yet known. There is not enough history yet, so no link can be claimed.

### (e) 20 versions with earlier conclusions, chosen by seed 20260 across months (8 months)

#### fnd_case_2025-12-24T09:15:00+05:30_v1  (as_of 2025-12-24T09:15:00+05:30, mode relationship, text `llm`)

**Higher than usual morning heart rate was noted that day.**

1. Heart rate was clearly above her usual in the morning that day.  `['m1']`
2. Short sleep the night before has tended to move together with higher heart rate over the day same day.  `['f5']`
3. This has come up before.  `['p1']`
4. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "a winter school break"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->hr_day_mean` v1 (supported, written 2025-12-21T23:59:59+05:30)
- F2 headline was: Short sleep and a clearly higher morning heart rate were recorded that day.

#### fnd_case_2025-12-24T16:15:00+05:30_v2  (as_of 2025-12-24T20:15:00+05:30, mode relationship, text `llm`)

**Afternoon heart rate was clearly above her usual.**

1. On the same day, more activity in the hour before may be linked to higher heart rate in that hour, and short sleep the night before may be linked to higher heart rate over the day.  `['g1']`
2. The day's mood record is not known yet.  `['n1']`
3. A diary entry that day in the evening described holiday preparations with family shopping and cooking.  `['d1']`
4. This has come up before.  `['p1', 'p2']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "a winter school break"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "a winter school break"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v1 (supported, written 2025-12-21T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v1 (supported, written 2025-12-21T23:59:59+05:30)
- F2 headline was: Heart rate was clearly above her usual.

#### fnd_case_2025-12-25T13:15:00+05:30_v2  (as_of 2025-12-25T15:00:00+05:30, mode relationship, text `llm`)

**Afternoon heart rate and glucose were clearly above her usual after lunch that day**

1. Heart rate was clearly above her usual in the afternoon and glucose was far above her usual in the afternoon.  `['m1', 'm2']`
2. More activity in the hour before has tended to move together with higher heart rate in that hour.  `['f1']`
3. The size of this meal's rise was among the very highest she has had within the hour or so after lunches.  `['f9']`
4. A diary entry in the afternoon records a mild social substance use occasion with friends during a Christmas gathering.  `['d1']`
5. A diary entry in the afternoon describes visiting friends and a festive indulgent meal.  `['d2']`
6. A diary entry from the day before in the evening describes Christmas Eve preparations including family shopping and cooking.  `['d3']`
7. An earlier summary says sharply more steps during holiday preparations.  `['s1']`
8. The day's mood record, the day's medicine record and the day's step total are not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "a winter school break"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v1 (supported, written 2025-12-21T23:59:59+05:30)
- F2 headline was: Afternoon high heart rate and large postlunch glucose rise during holiday lunch.

#### fnd_case_2026-01-20T16:00:00+05:30_v3  (as_of 2026-01-20T19:15:00+05:30, mode relationship, text `llm`)

**Glucose far below usual and heart rate clearly above usual were recorded that day.**

1. More activity in the hour before has tended to move together with higher heart rate in that hour.  `['f6']`
2. Glucose was far below her usual in the afternoon that day.  `['m1']`
3. Heart rate was clearly above her usual in the evening that day.  `['m2']`
4. It is not known yet the day's step total and the day's mood record.  `['n1']`
5. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f6'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "a festival, traveling, sesame sweets, a client dinner"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v4 (supported, written 2026-01-18T23:59:59+05:30)
- F2 headline was: Glucose was far below her usual that afternoon while heart rate was clearly above her usual that evening.

#### fnd_case_2026-01-30T01:15:00+05:30_v4  (as_of 2026-01-30T11:00:00+05:30, mode relationship, text `code_line`)

**Glucose was clearly above her usual.**

1. Present: short sleep the night before (low for her).  `[]`
2. The size of this meal's rise was high for her within the couple of hours after breakfasts.  `[]`
3. Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day.  `[]`
4. Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history.  `[]`
5. Also present, with no link claimed: missed doses on the same day or the day before and low activity the day before (low for her).  `[]`
6. Not known yet: the day's mood record and the day's step total.  `[]`

- view's earlier conclusions: 
  - `p1` about ['f4'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day."
  - `p2` about ['f8'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher glucose peaks after breakfast in her history." / situations: "a client dinner, richer restaurant food"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->non_meal_mean` v2 (supported, written 2026-01-25T23:59:59+05:30); `pi_long_sleep_hours@prev_night->post_meal_peak:breakfast` v2 (supported, written 2026-01-25T23:59:59+05:30)
- F2 headline was: Glucose was clearly above her usual night after a breakfast a few hours earlier

#### fnd_case_2026-01-30T01:15:00+05:30_v6  (as_of 2026-01-30T16:45:00+05:30, mode relationship, text `llm`)

**Nighttime glucose was clearly above her usual that day.**

1. Glucose was clearly above her usual that day at night.  `['m1']`
2. Short sleep the night before has tended to move together with higher glucose between meals same day; higher glucose peaks after breakfast; higher glucose peaks after lunch, and they often occur together and their separate roles cannot be told apart.  `['g1']`
3. There is enough history and no link is claimed for missed doses on the same day or the day before.  `['h1', 'f1', 'f7', 'f14']`
4. The day's mood record and the day's step total are not known yet.  `['n1']`
5. This has come up before.  `['p1', 'p2', 'p3']`

- view's earlier conclusions: 
  - `p1` about ['f4'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day."
  - `p2` about ['f8'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher glucose peaks after breakfast in her history." / situations: "a client dinner, richer restaurant food"
  - `p3` about ['f15'], state **repeated**, seen before: recent_weeks: "Short sleep the night before has repeatedly moved together with higher glucose peaks after lunch in her history." / situations: "mild social use of alcohol, a festive gathering, a client dinner, richer restaurant food"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->non_meal_mean` v2 (supported, written 2026-01-25T23:59:59+05:30); `pi_long_sleep_hours@prev_night->post_meal_peak:breakfast` v2 (supported, written 2026-01-25T23:59:59+05:30); `pi_long_sleep_hours@prev_night->post_meal_peak:lunch` v2 (supported, written 2026-01-18T23:59:59+05:30)
- F2 headline was: Nighttime glucose clearly above her usual after a midday meal.

#### fnd_case_2026-02-07T11:15:00+05:30_v4  (as_of 2026-02-07T21:15:00+05:30, mode relationship, text `llm`)

**Heart rate far above her usual that morning**

1. Her heart rate was far above her usual that morning.  `['m1']`
2. More activity in the hour before has tended to move together with higher heart rate in that hour.  `['f1']`
3. That morning she took part in wedding shopping with extended family.  `['d1']`
4. The day's mood record is not known yet.  `['n1']`
5. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "a festival, traveling, sesame sweets, a client dinner"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v5 (supported, written 2026-01-25T23:59:59+05:30)
- F2 headline was: Far above usual morning heart rate after extended family shopping

#### fnd_case_2026-02-13T16:45:00+05:30_v1  (as_of 2026-02-13T16:45:00+05:30, mode relationship, text `llm`)

**Afternoon heart rate was clearly above her usual**

1. More activity in the hour before and short sleep the night before may be linked to higher heart rate in that hour and higher heart rate over the day, same day.  `['g1']`
2. That morning she noted wedding week starting with pre-wedding rituals and hosting described as high activity and joyful.  `['d1']`
3. The day before she recorded a half-day of work and hands-on wedding preparation at her parents' place.  `['d2']`
4. An earlier summary says time in range fell sharply during wedding preparation.  `['s1']`
5. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "wedding shopping with extended family, a festival, sesame sweets, a client dinner"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "a festival, sesame sweets, children, a client dinner"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v6 (supported, written 2026-02-08T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v6 (supported, written 2026-02-08T23:59:59+05:30)
- F2 headline was: Afternoon heart rate clearly above her usual during busy wedding week preparations

#### fnd_case_2026-02-13T16:45:00+05:30_v2  (as_of 2026-02-13T20:15:00+05:30, mode relationship, text `llm`)

**Heart rate clearly above her usual in the afternoon after a busy period.**

1. Her heart rate was clearly above her usual that day in the afternoon.  `['m1']`
2. More activity in the hour before and short sleep the night before often occur together and may be linked to higher heart rate in that hour and may be linked to higher heart rate over the day on the same day.  `['g1']`
3. A morning diary note that day describes pre-wedding rituals and hosting with high activity and joy, and a prior afternoon diary note describes hands-on wedding preparation at her parents' place.  `['d1', 'd2']`
4. An earlier summary says time in range fell sharply during wedding preparation.  `['s1']`
5. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "wedding shopping with extended family, a festival, sesame sweets, a client dinner"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "a festival, sesame sweets, children, a client dinner"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v6 (supported, written 2026-02-08T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v6 (supported, written 2026-02-08T23:59:59+05:30)
- F2 headline was: Activity and short sleep may be linked to an unusually high afternoon heart rate

#### fnd_case_2026-03-16T01:15:00+05:30_v9  (as_of 2026-03-17T00:00:00+05:30, mode relationship, text `llm`)

**Night measures were clearly above usual with less sleep and fewer evening doses.**

1. Glucose was clearly above her usual at night, heart rate was far above her usual at night, she slept clearly less than usual in the morning, and clearly fewer doses were taken than usual in the evening.  `['m1', 'm2', 'm3', 'm4']`
2. Short sleep the night before was present, among the very lowest she has had.  `['f4', 'f24']`
3. Low fluid intake the day before was present, low for her.  `['f9']`
4. Missed doses in the week before was present.  `['f23']`
5. Low activity the day before has tended to move together with higher glucose between meals.  `['f5']`
6. This has come up before.  `['p1', 'p2']`
7. It is not known yet the day's medicine record, the day's mood record, last night's sleep, and where she was that day.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f4'], state **repeated**, seen before: recent_weeks: "Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day." / situations: "time off to recover"
  - `p2` about ['f5'], state **repeated**, seen before: recent_weeks: "Low activity the day before has repeatedly moved together with higher glucose between meals in her history." / situations: "time off"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->non_meal_mean` v6 (supported, written 2026-03-01T23:59:59+05:30); `pi_long_steps_total@prev_day->non_meal_mean` v6 (supported, written 2026-03-01T23:59:59+05:30)
- F2 headline was: Nighttime glucose and heart rate were clearly above her usual after a light dinner and fewer evening doses

#### fnd_case_2026-03-16T01:15:00+05:30_v10  (as_of 2026-03-17T00:30:00+05:30, mode relationship, text `llm`)

**Night high glucose and heart rate after fewer evening doses and short sleep**

1. Glucose was clearly above her usual, heart rate was far above her usual, she slept clearly less than usual, and clearly fewer doses were taken than usual.  `['m1', 'm2', 'm3', 'm4']`
2. Short sleep the night before was present.  `['f4', 'f24']`
3. Missed doses on the same day or the day before was present, and missed doses in the week before was present.  `['f1', 'f23']`
4. Low activity the day before has tended to move together with higher glucose between meals.  `['f5']`
5. Low fluid intake the day before was present.  `['f9']`
6. This has come up before.  `['p1', 'p2']`
7. The day's mood record, last night's sleep, and where she was that day are not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f4'], state **repeated**, seen before: recent_weeks: "Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day." / situations: "time off to recover"
  - `p2` about ['f5'], state **repeated**, seen before: recent_weeks: "Low activity the day before has repeatedly moved together with higher glucose between meals in her history." / situations: "time off"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->non_meal_mean` v6 (supported, written 2026-03-01T23:59:59+05:30); `pi_long_steps_total@prev_day->non_meal_mean` v6 (supported, written 2026-03-01T23:59:59+05:30)
- F2 headline was: Night high glucose and heart rate with fewer evening doses and short sleep noted

#### fnd_case_2026-03-17T07:00:00+05:30_v3  (as_of 2026-03-17T08:45:00+05:30, mode relationship, text `code_line`)

**Glucose was clearly above her usual. Resting heart rate was far above her usual.**

1. Present: low activity the day before (low for her), short sleep the night before (among the very lowest she has had).  `[]`
2. The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts.  `[]`
3. Low activity the day before and short sleep the night before were both present.  `[]`
4. Low activity the day before has tended to move together with higher glucose between meals in her history.  `[]`
5. Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day.  `[]`
6. Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history.  `[]`
7. Also present, with no link claimed: missed doses on the same day or the day before.  `[]`
8. Not known yet: the day's mood record and the day's step total.  `[]`

- view's earlier conclusions: 
  - `p1` about ['f4'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day." / situations: "time off to recover"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Low activity the day before has repeatedly moved together with higher glucose between meals in her history." / situations: "time off"
  - `p3` about ['f6'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day." / situations: "a social day, a colorful day, an active day, a community ritual"
  - `p4` about ['f14'], state **repeated**, seen before: earlier: "Short sleep the night before has repeatedly moved together with higher glucose peaks after breakfast in her history." / situations: "a client dinner, richer restaurant food"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->non_meal_mean` v6 (supported, written 2026-03-01T23:59:59+05:30); `pi_long_steps_total@prev_day->non_meal_mean` v6 (supported, written 2026-03-01T23:59:59+05:30); `pi_long_sleep_hours@prev_night->resting_hr_day` v4 (supported, written 2026-03-15T23:59:59+05:30); `pi_long_sleep_hours@prev_night->post_meal_peak:breakfast` v4 (supported, written 2026-02-15T23:59:59+05:30)
- F2 headline was: High morning glucose and high resting heart rate after breakfast.

#### fnd_case_2026-04-11T10:15:00+05:30_v3  (as_of 2026-04-11T14:15:00+05:30, mode relationship, text `llm`)

**Morning heart rate clearly above her usual that day**

1. That day in the morning her heart rate was clearly above her usual.  `['m1']`
2. More activity in the hour before has tended to move together with higher heart rate in that hour.  `['f1']`
3. A longer family walk was logged in the morning and described as positive.  `['d1']`
4. The day's mood record is not known yet.  `['n1']`
5. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "an evening walk, auditors, intense audit preparation, a peak stress deadline morning"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v14 (supported, written 2026-04-05T23:59:59+05:30)
- F2 headline was: Morning heart rate was clearly above her usual after a recent lunch.

#### fnd_case_2026-04-11T10:15:00+05:30_v6  (as_of 2026-04-11T19:30:00+05:30, mode relationship, text `llm`)

**Higher morning heart rate after a family walk**

1. More activity in the hour before has tended to move together with higher heart rate in that hour.  `['f1']`
2. Heart rate was clearly above her usual in the morning.  `['m1']`
3. That day in the morning she went on a longer family walk and the note is positive.  `['d1']`
4. This has come up before.  `['p1']`
5. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "an evening walk, auditors, intense audit preparation, a peak stress deadline morning"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v14 (supported, written 2026-04-05T23:59:59+05:30)
- F2 headline was: Morning heart rate was clearly above her usual after a family walk

#### fnd_case_2026-04-18T17:15:00+05:30_v2  (as_of 2026-04-18T20:15:00+05:30, mode relationship, text `llm`)

**Higher afternoon heart rate after a dinner and preceding activity**

1. Heart rate was clearly above her usual in the afternoon after a dinner a short while earlier.  `['m1']`
2. More activity in the hour before has tended to move together with higher heart rate in that hour.  `['f1']`
3. She had a local outdoor family event with lots of walking in the morning that day and it was positive.  `['d1']`
4. The day's mood record is not known yet.  `['n1']`
5. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: this_week: "More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history." / situations: "a longer family walk"
- PI notes drawn on: `pi_long_steps_window_hourly@60m->hr_hour_mean` v15 (supported, written 2026-04-12T23:59:59+05:30)
- F2 headline was: Higher afternoon heart rate after an active morning at a family outdoor event

#### fnd_case_2026-06-17T20:00:00+05:30_v1  (as_of 2026-06-17T20:00:00+05:30, mode relationship, text `llm`)

**Evening glucose was far above her usual.**

1. That evening glucose was far above her usual.  `['m1']`
2. Her diary that morning described mild upper respiratory symptoms and working from home.  `['d1', 'f2']`
3. A stressed or low-mood period on the same day was present.  `['f3']`
4. This has come up before.  `['p1']`
5. Low activity the day before has tended to move together with higher glucose between meals.  `['f5']`
6. That low activity was among the very lowest she has had.  `['f5']`
7. This has come up before.  `['p2']`
8. The day's medicine record is not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f3'], state **repeated**, seen before: earlier: "A stressed or low-mood period on the same day has repeatedly moved together with higher glucose between meals in her history." / situations: "a deadline morning"
  - `p2` about ['f5'], state **repeated**, seen before: earlier: "Low activity the day before has repeatedly moved together with higher glucose between meals in her history." / situations: "time off, a peak stress deadline morning"
- PI notes drawn on: `pi_long_strained_period@1d->non_meal_mean` v6 (supported, written 2026-03-22T23:59:59+05:30); `pi_long_steps_total@prev_day->non_meal_mean` v7 (supported, written 2026-03-22T23:59:59+05:30)
- F2 headline was: Glucose was far above her usual in the evening after a lunch a few hours earlier.

#### fnd_case_2026-07-08T23:45:00+05:30_v1  (as_of 2026-07-08T23:45:00+05:30, mode relationship, text `llm`)

**Evening heart rate was clearly above her usual.**

1. That evening, heart rate was clearly above her usual.  `['m1']`
2. A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; each has tended to move together with higher heart rate over the day.  `['g1']`
3. That afternoon there was a school call raising concern about falling grades and attentiveness, noted mild-moderate.  `['d1']`
4. That evening there was a difficult, defensive conversation with her daughter after dinner, noted tense.  `['d2']`
5. This has come up before.  `['p1', 'p2']`

- view's earlier conclusions: 
  - `p1` about ['f2'], state **repeated**, seen before: this_week: "A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history." / situations: "a longer family walk and a local outdoor family event with lots of walking in the morning"
  - `p2` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "a longer family walk, a local outdoor family event with lots of walking in the morning"
- PI notes drawn on: `pi_long_strained_period@same_day->hr_day_mean` v13 (supported, written 2026-04-19T23:59:59+05:30); `pi_long_sleep_hours@prev_night->hr_day_mean` v16 (supported, written 2026-04-19T23:59:59+05:30)
- F2 headline was: Evening heart rate clearly above her usual after a tense day

#### fnd_case_2026-09-11T07:00:00+05:30_v1  (as_of 2026-09-11T07:00:00+05:30, mode relationship, text `llm`)

**Shorter sleep that night with a stressed or low-mood day, long evening screen time, and a day away**

1. A stressed or low-mood period on the same day has tended to move together with shorter sleep that night.  `['f1']`
2. Long screen time the evening before was present and was among the very highest she has had.  `['f4']`
3. A day away from home was present.  `['f5']`
4. That day she wrote that she had missed walks recently and felt aware but lacked bandwidth to address it.  `['d1']`
5. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f1'], state **repeated**, seen before: earlier: "A stressed or low-mood period on the same day has repeatedly moved together with shorter sleep that night in her history." / situations: "a short work period and hands-on wedding preparation"
- PI notes drawn on: `pi_long_strained_period@same_day->sleep_hours_night` v5 (supported, written 2026-07-12T23:59:59+05:30)
- F2 headline was: Shorter than usual sleep after an evening with heavy screen time and being away

#### fnd_case_2026-09-13T07:00:00+05:30_v5  (as_of 2026-09-14T00:00:00+05:30, mode relationship, text `llm`)

**Far above usual morning heart rate after festival preparation**

1. Heart rate was far above her usual in the morning.  `['m1']`
2. More activity in the hour before was present.  `['f1']`
3. Short sleep the night before has tended to move together with higher heart rate over the day same day.  `['f5']`
4. A diary entry describes festival preparation the day before with high activity despite tiredness.  `['d1']`
5. An earlier summary says missed diabetes and thyroid medicines during a full day of festival prep.  `['s1']`
6. This has come up before.  `['p1']`
7. The day's mood record is not known yet.  `['n1']`

- view's earlier conclusions: 
  - `p1` about ['f5'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." / situations: "preparing for a festival, a school call, a difficult conversation with her daughter, a local outdoor family event"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->hr_day_mean` v19 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Heart rate was far above her usual after a busy day of festival preparation.

#### fnd_case_2026-09-14T06:15:00+05:30_v3  (as_of 2026-09-14T07:22:00+05:30, mode relationship, text `llm`)

**Short sleep and high morning heart rates were recorded**

1. Heart rate was clearly above her usual, she slept clearly less than usual, and resting heart rate was clearly above her usual.  `['m1', 'm2', 'm3']`
2. Short sleep the night before has tended to move together with a higher resting heart rate same day.  `['f15']`
3. The day's mood record and last night's sleep are not known yet.  `['n1']`
4. This has come up before.  `['p1']`

- view's earlier conclusions: 
  - `p1` about ['f15'], state **repeated**, seen before: this_week: "Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day." / situations: "a social day, a colorful day, an active day, a community ritual"
- PI notes drawn on: `pi_long_sleep_hours@prev_night->resting_hr_day` v7 (supported, written 2026-09-13T23:59:59+05:30)
- F2 headline was: Morning high heart rate after a short night's sleep during a festival day

### (f) The long-term note of 12 relationships at three points in time

**`sleep_hours@prev_night->hr_day_mean`** (20 versions)

- version 1, 2025-12-21T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day. **Situations:** In the cases noted, the situations included a winter school break.
- version 11, 2026-03-15T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day. **Situations:** In the cases noted, the situations included an evening walk, auditors present, intense audit preparation.
- version 20, 2026-09-17T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day. **Situations:** In the cases noted, the situations included preparing for a festival, a school call, a religious idol setup, a ganesh idol installation.

**`steps_window_hourly@60m->hr_hour_mean`** (18 versions)

- version 1, 2025-12-21T23:59:59+05:30, supported: More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history. **Situations:** In the cases noted, the situations included a winter school break.
- version 10, 2026-03-08T23:59:59+05:30, supported: More activity in the hour before has repeatedly moved together with higher heart rate in that hour in her history. **Situations:** In the cases noted, the situations included hosting, hands-on wedding preparation, short work period, pre-wedding rituals.
- version 18, 2026-07-12T23:59:59+05:30, retracted: This link, once suspected, is no longer supported by her history. (no situations line)

**`strained_period@same_day->hr_day_mean`** (17 versions)

- version 1, 2026-01-18T23:59:59+05:30, candidate: A stressed or low-mood period on the same day may be linked to higher heart rate over the day in her history. This is an early observation. **Situations:** In the cases noted, the situations included a festival, sesame sweets with children, a client dinner, a glass of wine.
- version 9, 2026-03-22T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history. **Situations:** In the cases noted, the situations included an evening walk, auditors present, intense audit preparation, a peak stress deadline morning.
- version 17, 2026-09-17T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with higher heart rate over the day in her history. **Situations:** In the cases noted, the situations included a school call, festival preparation, religious idol setup, a day off.

**`strained_period@same_day->missed_doses_day`** (14 versions)

- version 1, 2026-01-18T23:59:59+05:30, candidate: A stressed or low-mood period on the same day may be linked to more missed doses that day in her history. This is an early observation. (no situations line)
- version 8, 2026-03-22T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with more missed doses that day in her history. **Situations:** In the cases noted, the situations included an evening walk, auditors present, an evening with her husband.
- version 14, 2026-09-13T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with more missed doses that day in her history. **Situations:** In the cases noted, the situations included a diary entry, a small family observance, festival preparations, walks.

**`strained_period@prev_day->resting_hr_day`** (9 versions)

- version 1, 2026-01-11T23:59:59+05:30, candidate: A stressed or low-mood period the day before may be linked to a higher resting heart rate in her history. This is an early observation. (no situations line)
- version 5, 2026-03-15T23:59:59+05:30, supported: A stressed or low-mood period the day before has repeatedly moved together with a higher resting heart rate in her history. **Situations:** In the cases noted, the situations included a social, a community ritual, an evening walk.
- version 9, 2026-09-17T23:59:59+05:30, supported: A stressed or low-mood period the day before has repeatedly moved together with a higher resting heart rate in her history. **Situations:** In the cases noted, the situations included a social, a community ritual, an evening walk.

**`sleep_hours@prev_night->non_meal_mean`** (8 versions)

- version 1, 2026-01-18T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day. (no situations line)
- version 5, 2026-02-22T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day. **Situations:** In the cases noted, the situations included time off to recover.
- version 8, 2026-06-21T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with higher glucose between meals in her history, on the same day. **Situations:** In the cases noted, the situations included time off to recover, a peak stress deadline morning.

**`sleep_hours@prev_night->resting_hr_day`** (8 versions)

- version 1, 2026-01-11T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day. (no situations line)
- version 5, 2026-03-22T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day. **Situations:** In the cases noted, the situations included a social day, a colorful day, an active day, a community ritual.
- version 8, 2026-09-17T23:59:59+05:30, supported: Short sleep the night before has repeatedly moved together with a higher resting heart rate in her history, on the same day. **Situations:** In the cases noted, the situations included a social day, a colorful day, an active day, a community ritual.

**`steps_total@prev_day->non_meal_mean`** (8 versions)

- version 1, 2026-01-18T23:59:59+05:30, candidate: Low activity the day before may be linked to higher glucose between meals in her history. This is an early observation. (no situations line)
- version 5, 2026-02-22T23:59:59+05:30, supported: Low activity the day before has repeatedly moved together with higher glucose between meals in her history. **Situations:** In the cases noted, the situations included time off.
- version 8, 2026-06-21T23:59:59+05:30, supported: Low activity the day before has repeatedly moved together with higher glucose between meals in her history. **Situations:** In the cases noted, the situations included time off, a peak stress deadline morning.

**`late_prior_dinner@prev_evening->sleep_hours_night`** (7 versions)

- version 1, 2026-02-15T23:59:59+05:30, supported: A late dinner the evening before has repeatedly moved together with shorter sleep that night in her history. **Situations:** In the cases noted, the situations included short work period and hands-on wedding preparation.
- version 4, 2026-04-12T23:59:59+05:30, supported: A late dinner the evening before has repeatedly moved together with shorter sleep that night in her history. **Situations:** In the cases noted, the situations included short work period and hands-on wedding preparation.
- version 7, 2026-09-17T23:59:59+05:30, supported: A late dinner the evening before has repeatedly moved together with shorter sleep that night in her history. **Situations:** In the cases noted, the situations included short work period, hands-on wedding preparation, walks.

**`strained_period@1d->non_meal_mean`** (7 versions)

- version 1, 2026-01-25T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with higher glucose between meals in her history. (no situations line)
- version 4, 2026-02-22T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with higher glucose between meals in her history. **Situations:** In the cases noted, the situations included time off to recover.
- version 7, 2026-06-21T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with higher glucose between meals in her history. **Situations:** In the cases noted, the situations included a deadline morning.

**`strained_period@same_day->sleep_hours_night`** (7 versions)

- version 1, 2026-02-15T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with shorter sleep that night in her history. **Situations:** In the cases noted, the situations included a short work period and hands-on wedding preparation.
- version 4, 2026-04-12T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with shorter sleep that night in her history. **Situations:** In the cases noted, the situations included a short work period and hands-on wedding preparation.
- version 7, 2026-09-17T23:59:59+05:30, supported: A stressed or low-mood period on the same day has repeatedly moved together with shorter sleep that night in her history. **Situations:** In the cases noted, the situations included a short work period, hands-on wedding preparation, and walks.

**`symptom_entry@3d->resting_hr_day`** (7 versions)

- version 1, 2026-02-15T23:59:59+05:30, supported: A symptom noted in the diary on the same day or in the days before has repeatedly moved together with a higher resting heart rate in her history. (no situations line)
- version 4, 2026-03-22T23:59:59+05:30, supported: A symptom noted in the diary on the same day or in the days before has repeatedly moved together with a higher resting heart rate in her history. **Situations:** In the cases noted, the situations included an evening walk.
- version 7, 2026-09-17T23:59:59+05:30, supported: A symptom noted in the diary on the same day or in the days before has repeatedly moved together with a higher resting heart rate in her history. **Situations:** In the cases noted, the situations included an evening walk.
