# Findings Engine, stage F2: text layer, closing round report (p-v3, ck-v5.1)

284 versions from `findings_text_full_8.jsonl`; model `openai/gpt-5-mini`, reasoning `low`, one retry with the failed checks, then the code line. Checks version `ck-v5.1`.

## Totals

- first-attempt failures: **28 of 284 (9.9%)**
- retried: 28; passed on the retry: 21; **fallbacks to the code line: 7 (2.5%)**
- model stored attempts 312; tokens in 400,293, out 425,302 (reasoning 366,848); call seconds 4139, mean 13.3, longest 30.2; wall time of the run re-check 0.4 s; model re-runs 171.7 s + 15.5 s
- sentences per model-written version (headline included): mean 5.5, 3: 18, 4: 68, 5: 68, 6: 49, 7: 49, 8: 13, 9: 11, 10: 1

## Before and after this round

| | before this round | after this round |
|---|---:|---:|
| first-attempt failures | 12 (4.2%) | 28 (9.9%) |
| retried | 12 | 28 |
| fallbacks to the code line | 0 (0.0%) | 7 (2.5%) |
| versions with a code-appended sentence | 0 | 23 |
| versions the cleanup changed | 0 | 116 |

Model work of this round (no-model re-check first, then the model for 34 versions): **54 calls**, tokens in 80,450, out 89,265, call seconds 774; fallbacks among them 8.

Of the 0 earlier fallbacks, now accepted: 0; versions that were accepted before and are fallbacks now: 7.

## First-attempt failures by check

| check | versions | share of all versions |
|---|---:|---:|
| 1 structure | 0 | 0.0% |
| 2 refs exist | 0 | 0.0% |
| 3 digits, dates, counting words, view ids | 5 | 1.8% |
| 4 causal wording | 5 | 1.8% |
| 5 copied diary text / internal words | 4 | 1.4% |
| 6 claim level | 5 | 1.8% |
| 7 required statements | 0 | 0.0% |
| 8 recurrence wording | 0 | 0.0% |
| 9 often-together wording | 1 | 0.4% |
| 10 one summary sentence | 0 | 0.0% |
| 11 clinical term not in the view | 2 | 0.7% |
| 12 object of a claim | 4 | 1.4% |
| 13 repeated phrase | 11 | 3.9% |

## By mode

| mode | versions | first-attempt failures | fallbacks |
|---|---:|---:|---:|
| describe_only | 165 | 11 (6.7%) | 1 |
| may_discuss_links | 119 | 17 (14.3%) | 6 |

## Fallbacks and why

- fnd_case_2025-11-18T22:15:00+05:30_v3: attempt 1: check 13 sentence 4 uses the phrase 'among the very lowest she has had' more than once | attempt 2: check 1 there must be 2 to 8 sentences
- fnd_case_2025-12-24T16:15:00+05:30_v2: attempt 1: check 12 sentence 1 links something to another thing ('short sleep the night before'); the object of a claim must be an | attempt 2: check 6 sentence 2 cites a same-day point but does not say 'same day'; check 12 sentence 2 links something to another thing ('short sleep the night before'); the object of a claim must be an
- fnd_case_2025-12-24T16:15:00+05:30_v3: attempt 1: check 6 sentence 2 cites a same-day point but does not say 'same day'; check 12 sentence 2 links something to another thing ('short sleep the night before'); the object of a claim must be an | attempt 2: check 12 sentence 2 links something to another thing ('short sleep the night before'); the object of a claim must be an
- fnd_case_2026-01-30T01:15:00+05:30_v7: attempt 1: check 13 sentence 3 uses the phrase 'short sleep the night before' more than once | attempt 2: check 6 sentence 2 cites a same-day point but does not say 'same day'
- fnd_case_2026-03-04T01:15:00+05:30_v6: attempt 1: check 5 sentence 6 copies 7 or more words of a diary entry; check 6 sentence 1 cites a same-day point but does not say 'same day' | attempt 2: check 6 sentence 4 cites a same-day point but does not say 'same day'
- fnd_case_2026-03-04T18:30:00+05:30_v2: attempt 1: check 5 sentence 4 copies 7 or more words of a diary entry | attempt 2: check 13 sentence 3 uses the phrase 'more activity in the hour before' more than once; check 13 sentence 3 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-09-17T06:15:00+05:30_v2: attempt 1: check 5 sentence 3 copies 7 or more words of a diary entry; check 9 sentence 2 cites a set whose members often occur together but does not say the items often occur together and  | attempt 2: check 12 sentence 2 links something to another thing ('a stressed or low-mood period the day before'); the object of a 

## Scans over the model-written sentences

Sentences with "explanation", "reason", "why", "because of" or "result": **0**

Sentences linking a sensor artifact to anything other than the artifact statement (cited ids beyond the measure and the artifact point): **0**

Sentences that cite an earlier summary: **66** in 66 versions; versions with more than one: 0; versions whose view had an earlier summary: 78; artifact versions with one: 0.

Sentences with recurrence wording (come up before / early observation): 0.

## Sentences against their wording classes (heuristic scan)

- none

## Clinical terms not in the version's own view (all 284 versions)

**0**

## The re-check under ck-v5.1 (no model calls)

Saved answers judged again: 284; **34 have no saved answer that passes** and went back to the model.

| check | versions failing |
|---|---:|
| 5 copied diary text / internal words | 4 |
| 11 clinical term not in the view | 2 |
| 12 object of a claim | 6 |
| 13 repeated phrase | 24 |

The versions and why (last saved attempt):

- fnd_case_2025-10-31T05:15:00+05:30_v6: check 13 sentence 2 uses the phrase 'a stressed or low-mood period on the same day' more than once
- fnd_case_2025-11-13T21:00:00+05:30_v1: check 11 the headline uses the clinical term 'insulin', which is not in the view
- fnd_case_2025-11-18T22:15:00+05:30_v3: check 13 sentence 3 uses the phrase 'among the very lowest she has had' more than once
- fnd_case_2025-11-18T22:15:00+05:30_v4: check 13 sentence 3 uses the phrase 'among the very lowest she has had' more than once
- fnd_case_2025-11-18T22:15:00+05:30_v6: check 13 sentence 4 uses the phrase 'among the very lowest she has had' more than once; check 13 sentence 4 uses the phrase 'short sleep the night before' more than once
- fnd_case_2025-11-19T22:45:00+05:30_v1: check 13 sentence 3 uses the phrase 'among the very lowest she has had' more than once
- fnd_case_2025-11-19T22:45:00+05:30_v2: check 13 sentence 3 uses the phrase 'among the very lowest she has had' more than once
- fnd_case_2025-11-19T22:45:00+05:30_v3: check 13 sentence 2 uses the phrase 'among the very lowest she has had' more than once
- fnd_case_2025-12-24T16:15:00+05:30_v2: check 12 sentence 1 links something to another thing ('short sleep the night before'); the object of a claim 
- fnd_case_2025-12-24T16:15:00+05:30_v3: check 12 sentence 2 links something to another thing ('short sleep the night before'); the object of a claim 
- fnd_case_2026-01-06T21:00:00+05:30_v1: check 11 the headline uses the clinical term 'insulin', which is not in the view
- fnd_case_2026-01-12T00:15:00+05:30_v4: check 13 sentence 2 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-01-12T00:15:00+05:30_v5: check 13 sentence 1 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-01-12T00:15:00+05:30_v6: check 5 sentence 2 uses the internal word 'bundle'
- fnd_case_2026-01-12T00:15:00+05:30_v7: check 13 sentence 1 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-01-12T00:15:00+05:30_v8: check 13 sentence 2 uses the phrase 'short sleep the night before' more than once; check 5 sentence 2 uses the internal word 'points'
- fnd_case_2026-01-30T01:15:00+05:30_v4: check 13 sentence 1 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-01-30T01:15:00+05:30_v7: check 13 sentence 2 uses the phrase 'short sleep the night before' more than once; check 13 sentence 5 uses the phrase "the size of this meal's rise" more than once
- fnd_case_2026-02-14T06:00:00+05:30_v2: check 13 sentence 2 uses the phrase 'a higher resting heart rate' more than once
- fnd_case_2026-02-14T21:00:00+05:30_v1: check 12 sentence 1 links something to another thing ('a stressed or low-mood period on the same day'); the o
- fnd_case_2026-03-04T01:15:00+05:30_v6: check 12 sentence 1 links something to another thing ('short sleep the night before'); the object of a claim 
- fnd_case_2026-03-04T18:30:00+05:30_v2: check 13 sentence 2 uses the phrase 'more activity in the hour before' more than once; check 13 sentence 2 uses the phrase 'short sleep the night before' more than once; check 5 sentence 2 uses the internal word 'bundle'
- fnd_case_2026-03-17T07:00:00+05:30_v2: check 12 sentence 2 links something to another thing ('short sleep the night before'); the object of a claim 
- fnd_case_2026-03-17T07:00:00+05:30_v5: check 13 sentence 3 uses the phrase 'low activity the day before' more than once; check 13 sentence 3 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-03-17T18:15:00+05:30_v3: check 13 sentence 3 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-04-06T07:00:00+05:30_v3: check 13 sentence 1 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-04-06T07:00:00+05:30_v4: check 13 sentence 2 uses the phrase 'among the very lowest she has had' more than once; check 13 sentence 2 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-07-08T23:45:00+05:30_v1: check 5 sentence 2 uses the internal word 'entangled'; check 5 sentence 2 uses the internal word 'pair'
- fnd_case_2026-09-12T20:15:00+05:30_v1: check 12 sentence 3 links something to another thing ('low fluid intake the day before'); the object of a cla
- fnd_case_2026-09-12T20:15:00+05:30_v2: check 13 sentence 3 uses the phrase 'higher heart rate over the day' more than once
- fnd_case_2026-09-16T07:00:00+05:30_v2: check 13 sentence 2 uses the phrase 'higher blood pressure readings' more than once; check 13 sentence 2 uses the phrase 'missed doses on the same day or the day before' more than once; check 13 sentence 2 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-09-17T06:15:00+05:30_v2: check 13 sentence 2 uses the phrase 'a higher resting heart rate' more than once; check 13 sentence 2 uses the phrase 'a stressed or low-mood period the day before' more than once; check 13 sentence 2 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-09-17T06:15:00+05:30_v3: check 13 sentence 3 uses the phrase 'a higher resting heart rate' more than once; check 13 sentence 3 uses the phrase 'a stressed or low-mood period the day before' more than once; check 13 sentence 3 uses the phrase 'short sleep the night before' more than once
- fnd_case_2026-09-17T06:15:00+05:30_v4: check 13 sentence 4 uses the phrase 'a stressed or low-mood period on the same day' more than once; check 13 sentence 4 uses the phrase 'higher heart rate over the day' more than once; check 13 sentence 4 uses the phrase 'short sleep the night before' more than once; check 13 sentence 5 uses the phrase 'a higher resting heart rate' more than once; check 13 sentence 5 uses the phrase 'a stressed or low-mood period the day before' more than once; check 13 sentence 5 uses the phrase 'short sleep the night before' more than once

## Changed versions: previous text and new text (34)

### fnd_case_2025-10-31T05:15:00+05:30_v6 (previous; `llm`)

**Morning glucose and heart rate were clearly above her usual after an earlier dinner**

- Glucose was clearly above her usual that morning and heart rate was clearly above her usual that morning. `['m1', 'm2']`
- A stressed or low-mood period on the same day and a stressed or low-mood period on the same day and missed doses on the same day or the day before were present, and there is not enough history yet so no link is claimed. `['f3', 'f17', 'f15', 'h1']`
- It is not known yet the day's medicine record, last night's sleep, the day's mood record, or the day's step total. `['n1']`

### fnd_case_2025-10-31T05:15:00+05:30_v6 (new; `llm`)

**Higher than usual morning glucose and heart rate after a recent dinner**

- That morning glucose was clearly above her usual and heart rate was clearly above her usual, with a dinner about an hour earlier. `['m1', 'm2']`
- A stressed or low-mood period on the same day and missed doses on the same day or the day before were present, and there is not enough history yet so no link is claimed. `['f3', 'f17', 'f15', 'h1']`
- Not known yet: the day's medicine record, last night's sleep, the day's mood record and the day's step total. `['n1']`

### fnd_case_2025-11-13T21:00:00+05:30_v1 (previous; `llm`)

**Evening insulin dosing was far lower than usual after dinner**

- Far fewer doses were taken than usual in the evening after a dinner about an hour earlier. `['m1']`
- Missed doses in the week before were present, and there is not enough history yet so no link is claimed. `['f4', 'h1']`
- It is not known where she was that day. `['n1']`

### fnd_case_2025-11-13T21:00:00+05:30_v1 (new; `llm`)

**Far fewer evening doses were taken after a dinner about an hour earlier**

- Far fewer doses were taken than usual in the evening after a dinner about an hour earlier. `['m1']`
- Missed doses in the week before were present, and there is not enough history yet so no link is claimed. `['f4', 'h1']`
- Where she was that day is not known yet. `['n1']`

### fnd_case_2025-11-18T22:15:00+05:30_v3 (previous; `llm`)

**Evening high heart rate and reduced night fluids after a difficult day**

- Her heart rate was clearly above her usual in the evening, and clearly less fluid was taken than usual at night. `['m1', 'm2']`
- That morning she recorded that her father had been hospitalized with chest pain and weakness, described as a severe family crisis. `['d1']`
- A stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before among the very lowest she has had, short sleep the night before among the very lowest she has had, and a day away from home were present, and there is not enough history yet and no link is claimed. `['f2', 'f3', 'f4', 'f5', 'f10', 'h1']`
- An earlier summary says medication adherence was markedly down and some medicines were missed. `['s1']`

### fnd_case_2025-11-18T22:15:00+05:30_v3 (new; `code_line`)

**Heart rate was clearly above her usual. Clearly less fluid was taken than usual.**

- Present: a stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before (among the very lowest she has had), short sleep the night before (among the very lowest she has had), a day away from home. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-11-18T22:15:00+05:30_v4 (previous; `llm`)

**Evening heart rate high with low night fluids and high night glucose**

- Her heart rate was clearly above her usual in the evening, clearly less fluid was taken than usual at night, and glucose was clearly above her usual at night. `['m1', 'm2', 'm3']`
- That morning she noted her father was hospitalized with chest pain and weakness, a severe family crisis. `['d1']`
- A stressed or low-mood period on the same day was present; a symptom noted in the diary on the same day or in the days before was present; low fluid intake the day before was present and was among the very lowest she has had; short sleep the night before was present and was among the very lowest she has had; a day away from home was present; missed doses on the same day or the day before were present; low activity the day before was present and was low for her. `['f2', 'f3', 'f4', 'f5', 'f10', 'f14', 'f18']`
- There is not enough history yet, and no link is claimed. `['h1']`
- An earlier summary says medication adherence was markedly down and some medicines were missed. `['s1']`
- Not known yet: the day's mood record and last night's sleep. `['n1']`

### fnd_case_2025-11-18T22:15:00+05:30_v4 (new; `llm`)

**Heart rate and glucose were clearly above her usual while less fluid was taken than usual.**

- Heart rate was clearly above her usual in the evening. `['m1']`
- Clearly less fluid was taken than usual that night and glucose was clearly above her usual that night. `['m2', 'm3']`
- Her diary notes her father was hospitalized with chest pain and weakness and that this was severe and a family crisis. `['d1']`
- A stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before, short sleep the night before, a day away from home, missed doses on the same day or the day before, and low activity the day before were present, and there is not enough history yet so no link is claimed. `['f2', 'f3', 'f4', 'f5', 'f10', 'f14', 'f18', 'h1']`
- Not known yet: the day's mood record and last night's sleep. `['n1']`

### fnd_case_2025-11-18T22:15:00+05:30_v6 (previous; `llm`)

**Evening and night readings were above her usual while fluid intake was lower.**

- Heart rate was clearly above her usual in the evening and resting heart rate was far above her usual in the morning. `['m1', 'm4']`
- Glucose was clearly above her usual at night and clearly less fluid was taken than usual at night. `['m3', 'm2']`
- That morning she recorded being in hospital coordinating care and family logistics, and another entry describes her father being hospitalized overnight with chest pain and weakness and so concerns someone else. `['d1', 'd2']`
- A stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before among the very lowest she has had, short sleep the night before among the very lowest she has had, a day away from home, missed doses on the same day or the day before, short sleep the night before among the very lowest she has had, low activity the day before low for her, short sleep the night before among the very lowest she has had, and a stressed or low-mood period the day before were present. `['f2', 'f3', 'f4', 'f5', 'f10', 'f14', 'f17', 'f18', 'f19', 'f21', 'f22']`
- There is not enough history yet and no link is claimed. `['h1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2025-11-18T22:15:00+05:30_v6 (new; `llm`)

**Evening and night measures were clearly above her usual after a light dinner.**

- Heart rate was clearly above her usual in the evening and resting heart rate was far above her usual in the morning. `['m1', 'm4']`
- Glucose was clearly above her usual at night and clearly less fluid was taken than usual at night. `['m3', 'm2']`
- That morning she had a hospital day coordinating care and family logistics. `['d1']`
- That morning her father was hospitalized overnight with chest pain and weakness, a severe family crisis concerning him. `['d2']`
- An earlier summary says medication adherence was markedly down and medicines were missed. `['s1']`
- There is not enough history yet and no link can be claimed. `['h1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2025-11-19T22:45:00+05:30_v1 (previous; `llm`)

**Evening heart rate clearly above her usual after a light dinner**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- That morning she recorded a severe hospital day coordinating care and family logistics, and the day before she recorded that her father was hospitalized with chest pain and weakness and marked it severe as a family crisis. `['d1', 'd2']`
- A stressed or low-mood period on the same day, low fluid intake the day before among the very lowest she has had, and short sleep the night before among the very lowest she has had were present, and there is not enough history yet so no link is claimed. `['f2', 'f4', 'f5', 'h1']`

### fnd_case_2025-11-19T22:45:00+05:30_v1 (new; `llm`)

**Evening heart rate clearly above her usual after a light dinner.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- A stressed or low-mood period on the same day was present. `['f2']`
- Low fluid intake the day before was present, and it was among the very lowest she has had. `['f4']`
- Short sleep the night before was present, and it was among the very lowest she has had. `['f5']`
- There is not enough history yet, so no link can be claimed. `['h1']`
- A morning diary entry that day says she was managing hospital care and family logistics and marks it severe. `['d1']`
- A morning diary entry the day before reports her father was hospitalized overnight with chest pain and weakness and marks it a severe family crisis. `['d2']`
- An earlier summary says father hospitalized overnight was the major life event as sleep dropped sharply. `['s1']`

### fnd_case_2025-11-19T22:45:00+05:30_v2 (previous; `llm`)

**That evening her heart rate and glucose were clearly above her usual.**

- That evening heart rate was clearly above her usual and glucose was far above her usual. `['m1', 'm2']`
- A stressed or low-mood period on the same day was present. `['f2', 'f12']`
- Low fluid intake the day before, among the very lowest she has had, short sleep the night before, among the very lowest she has had, and missed doses on the same day or the day before were present. `['f4', 'f5', 'f11', 'f10']`
- That morning she recorded being in hospital coordinating family care and marked it severe, and the day before she recorded her father was taken to hospital overnight with chest pain and weakness and marked it severe and a family crisis. `['d1', 'd2']`
- There is not enough history yet, so no link is claimed. `['h1']`
- An earlier summary says father hospitalized overnight was the major life event as sleep dropped sharply, and the day's step total is not known yet. `['s1', 'n1']`

### fnd_case_2025-11-19T22:45:00+05:30_v2 (new; `llm`)

**Evening heart rate and glucose were clearly above her usual.**

- Heart rate was clearly above her usual in the evening, and glucose was far above her usual in the evening. `['m1', 'm2']`
- A stressed or low-mood period on the same day and missed doses on the same day or the day before were present. `['f2', 'f12', 'f10']`
- Low fluid intake the day before, among the very lowest she has had, was present. `['f4']`
- Short sleep the night before, among the very lowest she has had, was present. `['f5', 'f11']`
- She recorded that she was in hospital coordinating care and family logistics that morning, marked severe, and an entry about her father says he was hospitalized overnight with chest pain and weakness the day before and is marked a severe family crisis; that entry concerns someone else. `['d1', 'd2']`
- An earlier summary says her father's overnight hospitalization was the major life event and sleep dropped sharply. `['s1']`
- There is not enough history yet, so no link is claimed. `['h1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2025-11-19T22:45:00+05:30_v3 (previous; `llm`)

**Evening heart rate and glucose were clearly above her usual.**

- Her heart rate was clearly above her usual that evening and glucose was far above her usual that evening. `['m1', 'm2']`
- A stressed or low-mood period on the same day was present; low fluid intake the day before, among the very lowest she has had, was present; short sleep the night before, among the very lowest she has had, was present; missed doses on the same day or the day before was present. `['f2', 'f12', 'f4', 'f5', 'f11', 'f10']`
- A diary entry that morning describes her coordinating hospital care and family logistics and notes severity, and a diary entry the day before records that her father was hospitalized overnight with chest pain and weakness and notes a severe family crisis. `['d1', 'd2']`
- There is not enough history yet, so no link is claimed; the day's step total is not known yet. `['h1', 'n1']`
- An earlier summary says yesterday: Father hospitalized overnight was the major life event as sleep dropped sharply. `['s1']`

### fnd_case_2025-11-19T22:45:00+05:30_v3 (new; `llm`)

**Evening heart rate and glucose were clearly above her usual.**

- Heart rate was clearly above her usual in the evening, and glucose was far above her usual in the evening. `['m1', 'm2']`
- A stressed or low-mood period on the same day and missed doses on the same day or the day before were present. `['f2', 'f12', 'f10']`
- Low fluid intake the day before, among the very lowest she has had, was present. `['f4']`
- Short sleep the night before, among the very lowest she has had, was present. `['f5', 'f11']`
- She recorded that she was in hospital coordinating care and family logistics that morning, marked severe, and an entry about her father says he was hospitalized overnight with chest pain and weakness the day before and is marked a severe family crisis; that entry concerns someone else. `['d1', 'd2']`
- An earlier summary says her father's overnight hospitalization was the major life event and sleep dropped sharply. `['s1']`
- There is not enough history yet, so no link is claimed. `['h1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2025-12-24T16:15:00+05:30_v2 (previous; `llm`)

**Afternoon heart rate above her usual after a busy day**

- More activity in the hour before has tended to move together with short sleep the night before, same day; they often occur together and their separate roles cannot be told apart. `['g1']`
- Heart rate was clearly above her usual in the afternoon. `['m1']`
- An evening diary entry describes holiday preparations, family shopping and cooking. `['d1']`
- The day's mood record is not known yet. `['n1']`
- There is enough history. `['h1']`

### fnd_case_2025-12-24T16:15:00+05:30_v2 (new; `code_line`)

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2025-12-24T16:15:00+05:30_v3 (previous; `llm`)

**Her afternoon heart rate was clearly above her usual.**

- That afternoon her heart rate was clearly above her usual. `['m1']`
- More activity in the hour before has tended to move together with short sleep the night before; they often occur together and their separate roles cannot be told apart, same day. `['g1']`
- She wrote that evening about preparing for the holiday and doing shopping and cooking with family. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2025-12-24T16:15:00+05:30_v3 (new; `code_line`)

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-01-06T21:00:00+05:30_v1 (previous; `llm`)

**Evening insulin doses were clearly fewer than usual after a dinner that day**

- Clearly fewer doses were taken than usual in the evening after a dinner about an hour earlier. `['m1']`
- A symptom noted in the diary on the same day was present; that morning she reported mild throat soreness she attributed to the weather. `['f3', 'd1']`
- A stressed or low-mood period on the same day was present, and missed doses in the week before were present. `['f2', 'f4']`
- It is not known yet where she was that day. `['n1']`

### fnd_case_2026-01-06T21:00:00+05:30_v1 (new; `llm`)

**Evening doses were clearly fewer than usual after dinner.**

- Clearly fewer doses were taken than usual in the evening. `['m1']`
- A stressed or low-mood period on the same day was present. `['f2']`
- A symptom noted in the diary on the same day was present; the diary records a mild sore throat that morning which she dismissed as weather. `['f3', 'd1']`
- Missed doses in the week before were present. `['f4']`
- It is not known where she was that day. `['n1']`

### fnd_case_2026-01-12T00:15:00+05:30_v4 (previous; `llm`)

**Nighttime glucose was clearly above her usual after a recent breakfast**

- Glucose was clearly above her usual that night after a breakfast a short while earlier. `['m1']`
- The short sleep the night before, low activity the day before, and short sleep the night before often occur together and their separate roles cannot be told apart; they may be linked to higher glucose between meals and higher glucose peaks after breakfast, same day. `['g1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The day's medicine record, the day's mood record, and the day's step total are not known yet. `['n1']`
- There is enough history and no link is claimed. `['h1']`

### fnd_case_2026-01-12T00:15:00+05:30_v4 (new; `llm`)

**Higher than usual night glucose after a recent breakfast.**

- Short sleep the night before and low activity the day before often occur together and their separate roles cannot be told apart and may be linked to higher glucose between meals and higher glucose peaks after breakfast, same day. `['g1']`
- Glucose was clearly above her usual, at night. `['m1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The day's medicine record, the day's mood record, and the day's step total are not known yet. `['n1']`

### fnd_case_2026-01-12T00:15:00+05:30_v5 (previous; `llm`)

**Night glucose was high and morning heart rate was high around breakfast**

- Short sleep the night before, low activity the day before, short sleep the night before, short sleep the night before often occur together and their separate roles cannot be told apart and may be linked to higher glucose between meals, higher glucose peaks after breakfast and higher heart rate over the day same day. `['g1']`
- Glucose was clearly above her usual that night. `['m1']`
- Heart rate was clearly above her usual that morning after a breakfast about an hour earlier. `['m2']`
- The day's medicine record, the day's mood record, the day's step total are not known yet. `['n1']`

### fnd_case_2026-01-12T00:15:00+05:30_v5 (new; `llm`)

**Night glucose and morning heart rate were clearly above her usual after a large breakfast rise**

- Glucose was clearly above her usual that night. `['m1']`
- Heart rate was clearly above her usual that morning. `['m2']`
- These present_together items may be linked to higher glucose between meals, higher glucose peaks after breakfast, and higher heart rate over the day; they often occur together and their separate roles cannot be told apart, same day. `['g1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The day's medicine record, the day's mood record, and the day's step total are not known yet. `['n1']`

### fnd_case_2026-01-12T00:15:00+05:30_v6 (previous; `llm`)

**Higher night glucose and higher morning heart rate after a large lunch rise.**

- Glucose was clearly above her usual at night and heart rate was clearly above her usual in the morning after a lunch about an hour earlier. `['m1', 'm2']`
- The bundle of short sleep the night before and low activity the day before often occur together and their separate roles cannot be told apart and may be linked to higher glucose between meals, higher glucose peaks after breakfast, higher heart rate over the day, and higher glucose peaks after lunch on the same day. `['g1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f21']`
- Her diary notes a work trip to Chennai beginning with an afternoon flight that day. `['d1']`
- It is not yet known the day's medicine record, the day's mood record, or the day's step total. `['n1']`

### fnd_case_2026-01-12T00:15:00+05:30_v6 (new; `llm`)

**Night glucose and morning heart rate were clearly above her usual.**

- Her glucose was clearly above her usual at night and her heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- Short sleep the night before and low activity the day before often occur together and their separate roles cannot be told apart, same day. `['g1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f21']`
- A stressed or low-mood period on the same day was present, and there is not enough history yet. `['f24']`
- There is enough history, and no link is claimed. `['h1']`
- The day's medicine record, the day's mood record, and the day's step total are not known yet. `['n1']`
- A diary entry says a work trip to Chennai began that day with an afternoon flight. `['d1']`

### fnd_case_2026-01-12T00:15:00+05:30_v7 (previous; `llm`)

**Short sleep, low activity and unusually large meal rises that day with higher readings**

- Short sleep the night before, low activity the day before, short sleep the night before, short sleep the night before, short sleep the night before often occur together and their separate roles cannot be told apart and may be linked to higher glucose between meals and higher glucose peaks after breakfast and higher heart rate over the day and higher glucose peaks after lunch same day. `['g1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f21']`
- A stressed or low-mood period on the same day was present, and there is not enough history yet. `['f14', 'f24']`
- The day's medicine record, the day's mood record, and the day's step total are not known yet. `['n1']`
- A diary entry notes a work trip to Chennai begins with an afternoon flight that day. `['d1']`

### fnd_case_2026-01-12T00:15:00+05:30_v7 (new; `llm`)

**Higher than usual night glucose and higher than usual morning heart rate were recorded.**

- Short sleep the night before and low activity the day before often occur together and their separate roles cannot be told apart, and may be linked to higher glucose between meals, higher glucose peaks after breakfast, higher heart rate over the day same day, and higher glucose peaks after lunch. `['g1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f21']`
- A stressed or low-mood period on the same day was present, and there is not enough history yet. `['f14', 'f24']`
- The day's medicine record, the day's mood record, and the day's step total are not known yet. `['n1']`
- A diary entry notes a work trip began that day in the afternoon. `['d1']`

### fnd_case_2026-01-12T00:15:00+05:30_v8 (previous; `llm`)

**Nighttime glucose and morning heart rate were above her usual.**

- Glucose was clearly above her usual at night and heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- The points short sleep the night before, low activity the day before, short sleep the night before, short sleep the night before and short sleep the night before often occur together and their separate roles cannot be told apart and may be linked to higher glucose between meals, higher glucose peaks after breakfast, higher heart rate over the day and higher glucose peaks after lunch on the same day. `['g1']`
- A stressed or low-mood period on the same day was present. `['f3', 'f14', 'f24']`
- The day's medicine record and the day's step total are not known yet. `['n1']`
- A travel diary entry notes her work trip began with an afternoon flight. `['d1']`

### fnd_case_2026-01-12T00:15:00+05:30_v8 (new; `llm`)

**Nighttime glucose was clearly above her usual and morning heart rate was clearly above her usual.**

- Glucose was clearly above her usual at night. `['m1']`
- Heart rate was clearly above her usual in the morning. `['m2']`
- Short sleep the night before and low activity the day before often occur together and their separate roles cannot be told apart; they may be linked to higher glucose between meals same day, higher glucose peaks after breakfast, higher glucose peaks after lunch, and higher heart rate over the day same day. `['g1']`
- A stressed or low-mood period on the same day was present and there is not enough history yet. `['f3', 'f14', 'f24']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f6']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f21']`
- An entry says a work trip began that day with an afternoon flight. `['d1']`
- The day's medicine record and the day's step total are not known yet. `['n1']`

### fnd_case_2026-01-30T01:15:00+05:30_v4 (previous; `llm`)

**Night glucose was clearly above her usual after a breakfast a few hours earlier**

- Short sleep the night before and short sleep the night before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with higher glucose between meals same day. `['g1']`
- Missed doses on the same day or the day before was present and there is not enough history yet. `['f1', 'f7']`
- Low activity the day before was present. `['f5']`
- The size of this meal's rise was high for her within the couple of hours after breakfasts and was an unusual event. `['f6']`
- Not known yet: the day's mood record and the day's step total. `['n1']`

### fnd_case_2026-01-30T01:15:00+05:30_v4 (new; `llm`)

**Glucose was clearly above her usual night after a breakfast a few hours earlier**

- Glucose was clearly above her usual night after a breakfast a few hours earlier. `['m1']`
- Short sleep the night before may be linked to higher glucose between meals and higher glucose peaks after breakfast; same day. `['g1']`
- The size of this meal's rise was high for her within the couple of hours after breakfasts. `['f6']`
- Low activity the day before was present. `['f5']`
- Missed doses on the same day or the day before was present and there is not enough history yet. `['f1', 'f7']`
- The day's mood record and the day's step total are not known yet. `['n1']`

### fnd_case_2026-01-30T01:15:00+05:30_v7 (previous; `llm`)

**Nighttime glucose was clearly above her usual after an evening meal**

- Glucose was clearly above her usual at night after a dinner about an hour earlier. `['m1']`
- Short sleep the night before has tended to move together with higher glucose between meals same day; short sleep the night before has tended to move together with higher glucose peaks after breakfast; short sleep the night before has tended to move together with higher glucose peaks after lunch; they often occur together and their separate roles cannot be told apart. `['g1']`
- Missed doses on the same day or the day before were present and there is not enough history yet. `['f1', 'f7', 'f14', 'f21']`
- Low activity the day before was present with no link, and short sleep the night before was present with no link. `['f5', 'f22']`
- The size of this meal's rise was high for her within the couple of hours after breakfasts, and the size of this meal's rise was among the very highest she has had within the half hour or so after lunches, and the size of this meal's rise was among the very highest she has had within the half hour or so after dinners. `['f6', 'f13', 'f20']`
- The day's mood record and the day's step total are not known yet. `['n1']`

### fnd_case_2026-01-30T01:15:00+05:30_v7 (new; `code_line`)

**Glucose was clearly above her usual.**

- Present: short sleep the night before (low for her). `[]`
- The size of this meal's rise was high for her within the couple of hours after breakfasts. `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after lunches. `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after dinners. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after lunch in her history. `[]`
- Also present, with no link claimed: missed doses on the same day or the day before and low activity the day before (low for her). `[]`
- Not known yet: the day's mood record and the day's step total. `[]`

### fnd_case_2026-02-14T06:00:00+05:30_v2 (previous; `llm`)

**Her resting and overall heart rate were higher than usual that morning.**

- Her heart rate was far above her usual and her resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- Short sleep the night before has tended to move together with a higher resting heart rate same day, and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate; they often occur together and their separate roles cannot be told apart. `['g1']`
- Alcohol noted in the diary in the hours before and alcohol noted in the diary the evening before were present, and there is not enough history yet. `['f6', 'f13']`
- A diary entry describes social alcohol use with relatives during wedding festivities in the evening the day before. `['d1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`

### fnd_case_2026-02-14T06:00:00+05:30_v2 (new; `llm`)

**Morning heart rate readings were above her usual after a wedding evening.**

- The heart rate was far above her usual that morning. `['m1']`
- The resting heart rate was clearly above her usual that morning. `['m2']`
- The short sleep the night before and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; same day they may be linked to a higher resting heart rate. `['g1']`
- Alcohol noted in the diary in the hours before was present, and there is not enough history yet. `['f6']`
- Alcohol noted in the diary the evening before was present, and there is not enough history yet. `['f13']`
- A diary entry says she had mild evening social alcohol use with relatives during wedding festivities. `['d1']`
- An earlier summary says missed levothyroxine at the start of wedding week. `['s1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`

### fnd_case_2026-02-14T21:00:00+05:30_v1 (previous; `llm`)

**Clearly fewer evening doses were taken than usual following a joyful, high activity morning.**

- Clearly fewer doses were taken than usual has tended to move together with a stressed or low-mood period on the same day. `['m1', 'f2']`
- Missed doses in the week before were present and there is not enough history yet. `['f4', 'h1']`
- Short sleep the night before was present, among the very lowest she has had. `['f5']`
- That morning she had a joyful, high activity celebration with dancing and standing. `['d1']`
- It is not known yet where she was that day. `['n1']`
- An earlier summary says missed levothyroxine at the start of wedding week. `['s1']`

### fnd_case_2026-02-14T21:00:00+05:30_v1 (new; `llm`)

**Evening doses were clearly fewer than usual during wedding activities**

- Clearly fewer doses were taken than usual in the evening. `['m1']`
- A stressed or low-mood period on the same day has tended to move together with more missed doses that day. `['f2']`
- Missed doses in the week before were present, and there is not enough history yet. `['f4']`
- Short sleep the night before was present, among the very lowest she has had. `['f5']`
- That morning she reported a joyful Sangeet-style celebration with high activity and dancing. `['d1']`
- An entry the evening before notes social alcohol use with relatives during wedding festivities, mild. `['d2']`
- Where she was that day is not known yet. `['n1']`
- An earlier summary says missed levothyroxine at the start of wedding week. `['s1']`

### fnd_case_2026-03-04T01:15:00+05:30_v6 (previous; `llm`)

**Night and morning readings were well above her usual after a festive snack**

- More activity in the hour before has tended to move together with short sleep the night before same day; they often occur together and their separate roles cannot be told apart. `['g1']`
- Short sleep the night before was present. `['f9']`
- That night heart rate was far above her usual, that morning resting heart rate was clearly above her usual, and that morning glucose was far above her usual after a festive snack. `['m1', 'm2', 'm3']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-03-04T01:15:00+05:30_v6 (new; `code_line`)

**Heart rate was far above her usual. Resting heart rate was clearly above her usual. Glucose was far above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-03-04T18:30:00+05:30_v2 (previous; `llm`)

**Evening glucose and heart rate were clearly above her usual.**

- Glucose was clearly above her usual and heart rate was clearly above her usual that evening. `['m1', 'm2']`
- The bundle of more activity in the hour before and short sleep the night before often occur together and their separate roles cannot be told apart; more activity in the hour before has tended to move together with higher heart rate in that hour, and short sleep the night before has tended to move together with higher heart rate over the day same day. `['g1']`
- Her diary notes social, active celebrations with colors and water that morning and an earlier evening family celebration the day before; the day's mood record is not known yet. `['d1', 'd2', 'n1']`

### fnd_case_2026-03-04T18:30:00+05:30_v2 (new; `code_line`)

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-03-17T07:00:00+05:30_v2 (previous; `llm`)

**Morning glucose and resting heart rate were clearly above her usual.**

- That morning glucose was clearly above her usual and resting heart rate was far above her usual. `['m1', 'm2']`
- Low activity the day before has tended to move together with short sleep the night before same day; they often occur together and their separate roles cannot be told apart. `['g1']`
- Missed doses on the same day or the day before were present, and short sleep the night before was present and among the very lowest she has had. `['f1', 'f4']`
- The day's mood record is not known yet. `['n1']`
- A diary entry that morning described an intense deadline day and that she woke anxious before the alarm. `['d1']`
- An earlier summary says missed amlodipine and levothyroxine. `['s1']`

### fnd_case_2026-03-17T07:00:00+05:30_v2 (new; `llm`)

**Morning glucose and resting heart rate were above her usual.**

- Glucose was clearly above her usual in the morning, and resting heart rate was far above her usual in the morning. `['m1', 'm2']`
- Low activity the day before and short sleep the night before have tended to move together with higher glucose between meals and have tended to move together with a higher resting heart rate on the same day. `['g1']`
- Missed doses on the same day or the day before were present. `['f1']`
- Short sleep the night before was present, among the very lowest she has had. `['f4']`
- A diary entry that morning described a peak stress deadline day and waking anxious before the alarm. `['d1']`
- An earlier summary says yesterday: Missed amlodipine and levothyroxine. `['s1']`
- There is enough history. `['h1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-03-17T07:00:00+05:30_v5 (previous; `llm`)

**Higher than usual morning glucose and heart rate after a large breakfast rise.**

- Her glucose was clearly above her usual that morning, and her resting heart rate was far above her usual that morning. `['m1', 'm2', 'm3']`
- Missed doses on the same day or the day before were present. `['f1', 'f13']`
- Low activity the day before, short sleep the night before, short sleep the night before, and short sleep the night before often occur together and their separate roles cannot be told apart; low activity the day before has tended to move together with higher glucose between meals; short sleep the night before has tended to move together with higher glucose peaks after breakfast; short sleep the night before has tended to move together with a higher resting heart rate same day; short sleep the night before has tended to move together with higher heart rate over the day same day. `['g1']`
- Her diary noted a critical deadline day with peak stress and waking anxious before the alarm. `['d1']`
- An earlier summary says missed amlodipine and levothyroxine. `['s1']`
- Not known yet: the day's step total and the day's mood record. `['n1']`

### fnd_case_2026-03-17T07:00:00+05:30_v5 (new; `llm`)

**High morning glucose and raised heart rate after a very large breakfast rise**

- In the morning glucose was clearly above her usual, resting heart rate was far above her usual, and heart rate was clearly above her usual. `['m1', 'm2', 'm3']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f12']`
- Missed doses on the same day or the day before were present. `['f1', 'f13']`
- A diary entry that morning describes a critical year end deadline, intense stress, and waking up anxious before the alarm, with peak stress noted. `['d1']`
- Low activity the day before and short sleep the night before often occur together and their separate roles cannot be told apart, and may be linked to higher glucose between meals, a higher resting heart rate same day, higher glucose peaks after breakfast, and higher heart rate over the day same day. `['g1']`
- The day's step total and the day's mood record are not known yet. `['n1']`
- An earlier summary says missed amlodipine and levothyroxine. `['s1']`

### fnd_case_2026-03-17T18:15:00+05:30_v3 (previous; `llm`)

**Evening glucose and heart rate were clearly above her usual.**

- Her glucose was clearly above her usual in the evening and her heart rate was clearly above her usual in the evening. `['m1', 'm2']`
- An earlier summary says missed amlodipine and levothyroxine. `['s1']`
- The a stressed or low-mood period on the same day and the short sleep the night before often occur together and their separate roles cannot be told apart; both are described as higher heart rate over the day and the short sleep the night before is among the very lowest she has had. `['g1']`
- Missed doses on the same day or the day before were present, a stressed or low-mood period on the same day was present, and short sleep the night before was present. `['f1', 'f15', 'f3', 'f17', 'f4', 'f16']`
- That morning she described an extremely stressful deadline day and waking anxious before the alarm. `['d1']`
- It is not known yet the day's step total. `['n1']`

### fnd_case_2026-03-17T18:15:00+05:30_v3 (new; `llm`)

**Evening glucose and heart rate were clearly above her usual.**

- Glucose was clearly above her usual in the evening and heart rate was clearly above her usual in the evening. `['m1', 'm2']`
- A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; they have tended to move together with higher heart rate over the day, same day. `['g1']`
- Low activity the day before has tended to move together with higher glucose between meals and was low for her. `['f5']`
- Missed doses on the same day or the day before was present. `['f1', 'f15']`
- A stressed or low-mood period on the same day was present. `['f3', 'f17']`
- Short sleep the night before was present and was among the very lowest she has had. `['f4', 'f16']`
- A diary entry that morning describes a major deadline day, waking anxious, and is marked as peak stress. `['d1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2026-04-06T07:00:00+05:30_v3 (previous; `llm`)

**Short sleep and raised heart rates occurred together that day.**

- Short sleep the night before has tended to move together with a higher resting heart rate, and short sleep the night before has tended to move together with higher heart rate over the day, same day; they often occur together and their separate roles cannot be told apart. `['g1']`
- A morning diary entry that day described unfamiliar chest tightness and mild breathlessness on exertion and was present. `['d1', 'f15']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-04-06T07:00:00+05:30_v3 (new; `llm`)

**Short sleep and high heart rate occurred the same morning.**

- Short sleep the night before has tended to move together with a higher resting heart rate same day and was among the very lowest she has had. `['g1']`
- She slept clearly less than usual. `['m1']`
- Resting heart rate was far above her usual. `['m2']`
- Heart rate was clearly above her usual. `['m3']`
- A diary entry says she noted new chest tightness and mild breathlessness on climbing stairs, and it was described as concerning and unclear. `['d1', 'f15']`
- A symptom noted in the diary on the same day or in the days before was present. `['f15']`
- The day's mood record is not yet known. `['n1']`
- There is enough history. `['h1']`

### fnd_case_2026-04-06T07:00:00+05:30_v4 (previous; `llm`)

**Short sleep with raised heart rates that morning and a diary symptom**

- That morning she slept clearly less than usual, resting heart rate was far above her usual, and heart rate was clearly above her usual. `['m1', 'm2', 'm3']`
- Short sleep the night before has tended to move together with a higher resting heart rate among the very lowest she has had same day, and short sleep the night before has tended to move together with higher heart rate over the day among the very lowest she has had; they often occur together and their separate roles cannot be told apart. `['g1']`
- Her diary describes unfamiliar tightness in the chest and mild breathlessness on stairs, which she initially brushed off. `['d1']`
- A symptom noted in the diary on the same day or in the days before was present. `['f15']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-04-06T07:00:00+05:30_v4 (new; `llm`)

**Short sleep occurred with higher heart rates that morning**

- Short sleep the night before has tended to move together with a higher resting heart rate and higher heart rate over the day, same day, and was among the very lowest she has had. `['g1']`
- That morning she slept clearly less than usual, resting heart rate was far above her usual, and heart rate was clearly above her usual. `['m1', 'm2', 'm3']`
- That morning she described unfamiliar chest tightness and mild breathlessness when climbing stairs, initially brushed off. `['d1']`
- A symptom noted in the diary on the same day or in the days before was present. `['f15']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-07-08T23:45:00+05:30_v1 (previous; `llm`)

**Evening heart rate was clearly above her usual.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- An entangled pair — a stressed or low-mood period on the same day and short sleep the night before, low for her — often occur together and their separate roles cannot be told apart; this has tended to move together with higher heart rate over the day same day. `['g1']`
- That afternoon a school call noted concern about slipping grades and reduced attentiveness, described as mild to moderate. `['d1']`
- That evening she had a difficult, defensive conversation with her daughter after dinner, described as tense. `['d2']`

### fnd_case_2026-07-08T23:45:00+05:30_v1 (new; `llm`)

**Evening heart rate clearly above her usual after a tense day**

- Heart rate was clearly above her usual in the evening. `['m1']`
- A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart. `['g1']`
- That afternoon she noted a school call about slipping grades and attentiveness. `['d1']`
- That evening she recorded a difficult, defensive conversation with her daughter after dinner. `['d2']`

### fnd_case_2026-09-12T20:15:00+05:30_v1 (previous; `llm`)

**Heart rate was clearly above her usual in the evening that day.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- More activity in the hour before was present. `['f1']`
- A stressed or low-mood period on the same day has tended to move together with low fluid intake the day before. `['g1']`
- Her morning diary entry describes festival preparation with high activity despite tiredness, and an earlier evening entry reports preparations starting to occupy her attention. `['d1', 'd2']`
- An earlier summary says missed medicines amid festival preparations. `['s1']`

### fnd_case_2026-09-12T20:15:00+05:30_v1 (new; `llm`)

**Evening heart rate clearly above her usual after a festival prep day**

- Heart rate was clearly above her usual in the evening. `['m1']`
- More activity in the hour before was present that day and high for her. `['f1']`
- A stressed or low-mood period on the same day and low fluid intake the day before may be linked to higher heart rate over the day. `['g1']`
- She describes festival preparation that day with cleaning, decorating and cooking and high activity despite tiredness. `['d1']`
- An earlier summary says missed medicines amid festival preparations. `['s1']`

### fnd_case_2026-09-12T20:15:00+05:30_v2 (previous; `llm`)

**Evening heart rate was clearly above her usual.**

- Heart rate was clearly above her usual in the evening. `['m1']`
- More activity in the hour before was present and high for her. `['f1']`
- A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day, and low fluid intake the day before has tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart. `['g1']`
- Her morning diary describes being very active preparing for a festival and genuinely active despite tiredness. `['d1']`
- Her evening diary from the day before notes festival preparations beginning and divided attention with ongoing work. `['d2']`
- An earlier summary says missed medicines amid festival preparations. `['s1']`

### fnd_case_2026-09-12T20:15:00+05:30_v2 (new; `llm`)

**Evening heart rate was clearly above her usual after a busy festival day**

- That evening heart rate was clearly above her usual. `['m1']`
- More activity in the hour before was present, high for her. `['f1']`
- A stressed or low-mood period on the same day and low fluid intake the day before often occur together and their separate roles cannot be told apart and has tended to move together with higher heart rate over the day. `['g1']`
- A diary note describes full day festival preparation with high activity despite tiredness that day. `['d1']`
- An earlier summary says missed medicines amid festival preparations. `['s1']`

### fnd_case_2026-09-16T07:00:00+05:30_v2 (previous; `llm`)

**Morning heart rate and blood pressure were clearly above her usual.**

- More activity in the hour before was present. `['f1']`
- Short sleep the night before and missed doses on the same day or the day before often occur together and their separate roles cannot be told apart; short sleep the night before same day has tended to move together with higher heart rate over the day, missed doses on the same day or the day before same day has tended to move together with higher blood pressure readings, and short sleep the night before has tended to move together with higher blood pressure readings. `['g1']`
- The day's mood record and where the reading was taken are not known yet. `['n1']`

### fnd_case_2026-09-16T07:00:00+05:30_v2 (new; `llm`)

**Morning heart rate and blood pressure were clearly above her usual.**

- Heart rate was clearly above her usual and blood pressure was clearly above her usual that morning. `['m1', 'm2']`
- More activity in the hour before was present. `['f1']`
- Short sleep the night before and missed doses on the same day or the day before has tended to move together with, same day, and their separate roles cannot be told apart. `['g1']`
- The day's mood record and where the reading was taken are not known yet. `['n1']`

### fnd_case_2026-09-17T06:15:00+05:30_v2 (previous; `llm`)

**Morning heart rate measures were clearly above her usual**

- Heart rate was clearly above her usual and resting heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- Short sleep the night before and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate same day and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g1']`
- An afternoon diary entry from the day before says she missed a proper midday meal amid overlapping work and festival pressures and notes layered stress. `['d1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`
- There is enough history, and no link is claimed. `['h1']`

### fnd_case_2026-09-17T06:15:00+05:30_v2 (new; `code_line`)

**Heart rate was clearly above her usual. Resting heart rate was clearly above her usual.**

- Present: short sleep the night before (among the very lowest she has had), a stressed or low-mood period the day before. `[]`
- Short sleep the night before and a stressed or low-mood period the day before often occur together, so their separate roles cannot be told apart. `[]`
- Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day. `[]`
- A stressed or low-mood period the day before has tended to move together with a higher resting heart rate in her history. `[]`
- Not known yet: the day's mood record and last night's sleep. `[]`

### fnd_case_2026-09-17T06:15:00+05:30_v3 (previous; `llm`)

**Morning heart rate and resting heart rate were clearly above her usual.**

- Heart rate was clearly above her usual in the morning, and resting heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- More activity in the hour before was present and was high for her. `['f1']`
- Short sleep the night before and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate same day, and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g1']`
- Diary entry describes that she missed a proper midday meal while under combined work and hosting pressure in the afternoon. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-09-17T06:15:00+05:30_v3 (new; `llm`)

**Higher than usual heart rate and resting heart rate that morning.**

- Heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- More activity in the hour before was present. `['f1']`
- Short sleep the night before same day and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart. `['g1']`
- A diary entry says she missed a main meal while juggling a work deadline and festival hosting, and notes layered stress. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-09-17T06:15:00+05:30_v4 (previous; `llm`)

**Morning heart rate and resting rate were clearly above her usual**

- Her heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- She had a quarter-close deadline day with mostly deskbound work and minimal proper meals, and earlier she had skipped a proper lunch amid layered stress. `['d1', 'd2']`
- More activity in the hour before was present and high for her. `['f1']`
- A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; a stressed or low-mood period on the same day has tended to move together with higher heart rate over the day and short sleep the night before has tended to move together with higher heart rate over the day. `['g1']`
- Short sleep the night before same day and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g2']`

### fnd_case_2026-09-17T06:15:00+05:30_v4 (new; `llm`)

**Morning heart rate and resting heart rate were clearly above her usual.**

- Heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- More activity in the hour before was present and was high for her. `['f1']`
- A stressed or low-mood period on the same day and short sleep the night before have tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart. `['g1']`
- Short sleep the night before and a stressed or low-mood period the day before may be linked to a higher resting heart rate; they often occur together and their separate roles cannot be told apart, same day. `['g2']`


## Read list (41 versions)

### fnd_case_2025-11-18T22:15:00+05:30_v3 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Heart rate was clearly above her usual. Clearly less fluid was taken than usual.**

- Present: a stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before (among the very lowest she has had), short sleep the night before (among the very lowest she has had), a day away from home. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-12-24T16:15:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2025-12-24T16:15:00+05:30_v3 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-01-30T01:15:00+05:30_v7 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual.**

- Present: short sleep the night before (low for her). `[]`
- The size of this meal's rise was high for her within the couple of hours after breakfasts. `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after lunches. `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after dinners. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after lunch in her history. `[]`
- Also present, with no link claimed: missed doses on the same day or the day before and low activity the day before (low for her). `[]`
- Not known yet: the day's mood record and the day's step total. `[]`

### fnd_case_2026-03-04T01:15:00+05:30_v6 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was far above her usual. Resting heart rate was clearly above her usual. Glucose was far above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-03-04T18:30:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-09-17T06:15:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual. Resting heart rate was clearly above her usual.**

- Present: short sleep the night before (among the very lowest she has had), a stressed or low-mood period the day before. `[]`
- Short sleep the night before and a stressed or low-mood period the day before often occur together, so their separate roles cannot be told apart. `[]`
- Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day. `[]`
- A stressed or low-mood period the day before has tended to move together with a higher resting heart rate in her history. `[]`
- Not known yet: the day's mood record and last night's sleep. `[]`

### fnd_case_2026-03-17T18:15:00+05:30_v2 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening glucose and heart rate were clearly above her usual.**

- Glucose was clearly above her usual and heart rate was clearly above her usual that evening. `['m1', 'm2']`
- Low activity the day before has tended to move together with higher glucose between meals. `['f5', 'm1']`
- Short sleep the night before, among the very lowest she has had, and a stressed or low-mood period on the same day often occur together and their separate roles cannot be told apart; they have tended to move together with higher heart rate over the day same day. `['g1', 'm2']`
- Missed doses on the same day or the day before, a stressed or low-mood period on the same day, and short sleep the night before were present. `['f1', 'f3', 'f4']`
- A diary entry says it was a critical year-end deadline day and that she woke up anxious before the alarm with peak stress. `['d1']`
- An earlier summary says missed amlodipine and levothyroxine yesterday. `['s1']`

### fnd_case_2026-03-17T18:15:00+05:30_v3 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening glucose and heart rate were clearly above her usual.**

- Glucose was clearly above her usual in the evening and heart rate was clearly above her usual in the evening. `['m1', 'm2']`
- A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; they have tended to move together with higher heart rate over the day, same day. `['g1']`
- Low activity the day before has tended to move together with higher glucose between meals and was low for her. `['f5']`
- Missed doses on the same day or the day before was present. `['f1', 'f15']`
- A stressed or low-mood period on the same day was present. `['f3', 'f17']`
- Short sleep the night before was present and was among the very lowest she has had. `['f4', 'f16']`
- A diary entry that morning describes a major deadline day, waking anxious, and is marked as peak stress. `['d1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2026-07-08T23:45:00+05:30_v1 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening heart rate clearly above her usual after a tense day**

- Heart rate was clearly above her usual in the evening. `['m1']`
- A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart. `['g1']`
- That afternoon she noted a school call about slipping grades and attentiveness. `['d1']`
- That evening she recorded a difficult, defensive conversation with her daughter after dinner. `['d2']`

### fnd_case_2026-09-16T18:45:00+05:30_v1 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening heart rate clearly above her usual after a pressured afternoon**

- Her heart rate was clearly above her usual that evening. `['m1']`
- A stressed or low-mood period on the same day and short sleep the night before have tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart, and the short sleep was among the very lowest she has had. `['g1']`
- That afternoon she missed a proper lunch while facing overlapping work deadline and festival hosting pressure. `['d1']`

### fnd_case_2026-09-17T06:15:00+05:30_v3 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Higher than usual heart rate and resting heart rate that morning.**

- Heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- More activity in the hour before was present. `['f1']`
- Short sleep the night before same day and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart. `['g1']`
- A diary entry says she missed a main meal while juggling a work deadline and festival hosting, and notes layered stress. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-09-17T06:15:00+05:30_v4 (entangled bundle)

`llm` / `ok`, attempts 2, may_discuss_links

**Morning heart rate and resting heart rate were clearly above her usual.**

- Heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- More activity in the hour before was present and was high for her. `['f1']`
- A stressed or low-mood period on the same day and short sleep the night before have tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart. `['g1']`
- Short sleep the night before and a stressed or low-mood period the day before may be linked to a higher resting heart rate; they often occur together and their separate roles cannot be told apart, same day. `['g2']`

### fnd_case_2026-09-17T21:45:00+05:30_v1 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening heart rate clearly above her usual after a busy period.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- Her record shows that more activity in the hour before was present, high for her. `['f1']`
- A stressed or low-mood period on the same day and short sleep the night before has tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart. `['g1']`

### fnd_case_2026-09-17T21:45:00+05:30_v2 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening heart rate and glucose were clearly above her usual after a festive dinner**

- Her heart rate was clearly above her usual and her glucose was clearly above her usual that evening. `['m1', 'm2']`
- More activity in the hour before was present. `['f1']`
- A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart. `['g1']`
- Missed doses on the same day or the day before and short sleep the night before were noted together. `['g2']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2025-11-08T11:00:00+05:30_v2 (artifact case)

`llm` / `ok`, attempts 1, describe_only

**Morning glucose far below her usual after breakfast**

- Glucose was far below her usual in the morning after a breakfast a few hours earlier. `['m1']`
- This may be a sensor artifact. `['f1']`
- The day's step total is not known yet. `['n1']`
- Not enough history yet, and no link can be claimed. `['h1']`

### fnd_case_2026-03-22T11:00:00+05:30_v2 (artifact case)

`llm` / `ok`, attempts 1, describe_only

**Unusually low morning glucose after a recent breakfast**

- Her glucose was far below her usual in the morning after a breakfast a few hours earlier. `['m1']`
- This may be a sensor artifact. `['f1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2026-08-22T10:30:00+05:30_v2 (artifact case)

`llm` / `ok`, attempts 1, describe_only

**Morning glucose was far below her usual after a recent breakfast**

- Her glucose was far below her usual in the morning after a breakfast earlier. `['m1']`
- That may be a sensor artifact. `['f1']`
- That day's step total is not known yet. `['n1']`

### fnd_case_2025-11-18T08:17:00+05:30_v1 (named case)

`llm` / `ok`, attempts 1, describe_only

**Morning blood pressure reading was clearly above her usual**

- Blood pressure was clearly above her usual in the morning. `['m1']`
- Missed doses on the same day or the day before were present. `['f1']`
- Short sleep the night before, among the very lowest she has had, was present. `['f4']`
- An earlier summary says medication adherence was markedly down and medicines were missed. `['s1']`
- There is not enough history yet to claim a link. `['h1']`
- It is not known yet where the reading was taken, and that morning she noted a severe family crisis with her father hospitalized for chest pain and weakness. `['n1', 'd1']`

### fnd_case_2025-11-18T08:17:00+05:30_v2 (named case)

`llm` / `ok`, attempts 1, describe_only

**Higher morning blood pressure and glucose with recent missed doses and very short sleep**

- Blood pressure was clearly above her usual that morning and glucose was clearly above her usual that morning. `['m1', 'm2']`
- Missed doses on the same day or the day before was present. `['f1', 'f8']`
- Short sleep the night before, among the very lowest she has had, was present. `['f4', 'f11']`
- A diary entry noted someone else as unusually tired and with reduced appetite in the days before, and a symptom noted in the diary on the same day or in the days before was present. `['d2', 'f9']`
- Her father was admitted overnight for chest symptoms and marked weakness that day. `['d1']`
- There is not enough history yet so no link can be claimed, and it is not yet known where the reading was taken or the day's mood record. `['h1', 'n1']`

### fnd_case_2025-11-18T08:17:00+05:30_v3 (named case)

`llm` / `ok`, attempts 1, describe_only

**Morning blood pressure and glucose were clearly above her usual after a lunch earlier**

- Morning blood pressure was clearly above her usual and morning glucose was clearly above her usual after a lunch a couple of hours earlier. `['m1', 'm2']`
- The size of this meal's rise was among the very highest she has had within the couple of hours after lunches. `['f13', 'm2']`
- That day her diary says father was hospitalized overnight with chest pain and weakness and that this was a severe family crisis. `['d1']`
- An earlier diary entry describes her father as unusually tired and with low appetite at a family lunch in the days before and notes this was concerning and not her own symptom. `['d2', 'f9', 'f18']`
- Missed doses on the same day or the day before were present, short sleep the night before was present and among the very lowest she has had, a symptom noted in the diary on the same day or in the days before was present, and a stressed or low-mood period on the same day was present. `['f1', 'f4', 'f8', 'f11', 'f14', 'f15', 'f9', 'f18', 'f16']`
- There is not enough history yet and where the reading was taken, the day's mood record and the day's step total are not known yet, so no link can be claimed. `['h1', 'n1']`

### fnd_case_2025-10-23T21:45:00+05:30_v1 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Evening glucose was clearly above her usual after dinner.**

- Glucose was clearly above her usual in the evening after a dinner about an hour earlier. `['m1']`
- Missed doses on the same day or the day before were present and there is not enough history yet with no link claimed. `['f2', 'h1']`
- That morning she visited her brother's family for Bhai Dooj. `['d1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2025-11-11T06:45:00+05:30_v1 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Morning heart rate clearly above her usual**

- She had heart rate was clearly above her usual morning. `['m1']`
- There is not enough history yet, so no link is claimed. `['h1']`
- An earlier summary says yesterday A large drop in sleep. `['s1']`
- Not known yet: the day's mood record and last night's sleep. `['n1']`

### fnd_case_2025-11-17T21:00:00+05:30_v1 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Evening dose shortfall after a light dinner, with recent stress, missed doses, and poor sleep noted**

- Clearly fewer doses were taken than usual in the evening after a light dinner a short while earlier. `['m1']`
- A stressed or low-mood period on the same day was present, missed doses in the week before was present, and short sleep the night before was present; there is not enough history yet so no link is claimed. `['f2', 'f4', 'f5', 'h1']`
- A diary entry says that at family lunch she noticed her father unusually tired and with low appetite, and that note concerns someone else. `['d1']`
- Not known yet: where she was that day. `['n1']`

### fnd_case_2025-10-15T00:15:00+05:30_v7 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Nighttime heart rate and glucose were clearly above her usual; morning resting heart rate also elevated**

- At night her heart rate was clearly above her usual and her glucose was clearly above her usual. `['m1', 'm2']`
- In the morning her resting heart rate was clearly above her usual. `['m3']`
- A symptom noted in the diary on the same day or in the days before was present. `['f3', 'f10', 'f15']`
- That morning she recorded a moderate fever and that she missed work, the day before she noted a scratchy throat with low energy and body ache, and in prior days she noted a mild evening headache. `['d1', 'd2', 'd3']`
- There is not enough history yet, and no link is claimed. `['h1']`
- The day's mood record, last night's sleep, and the day's medicine record are not known yet. `['n1']`

### fnd_case_2025-11-19T22:45:00+05:30_v2 (seeded: early descriptive)

`llm` / `ok`, attempts 2, describe_only

**Evening heart rate and glucose were clearly above her usual.**

- Heart rate was clearly above her usual in the evening, and glucose was far above her usual in the evening. `['m1', 'm2']`
- A stressed or low-mood period on the same day and missed doses on the same day or the day before were present. `['f2', 'f12', 'f10']`
- Low fluid intake the day before, among the very lowest she has had, was present. `['f4']`
- Short sleep the night before, among the very lowest she has had, was present. `['f5', 'f11']`
- She recorded that she was in hospital coordinating care and family logistics that morning, marked severe, and an entry about her father says he was hospitalized overnight with chest pain and weakness the day before and is marked a severe family crisis; that entry concerns someone else. `['d1', 'd2']`
- An earlier summary says her father's overnight hospitalization was the major life event and sleep dropped sharply. `['s1']`
- There is not enough history yet, so no link is claimed. `['h1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2025-10-19T19:15:00+05:30_v5 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening heart rate and glucose were clearly above her usual during a festival day**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- Her glucose was clearly above her usual in the evening. `['m2']`
- She hosted guests and prepared for a festival that day, and she had been shopping in crowded markets the day before. `['d1', 'd2', 'd3']`
- More activity in the hour before was present in her history. `['f1']`
- Short sleep the night before was present in her history, among the very lowest she has had. `['f5', 'f11']`
- Missed doses on the same day or the day before was present in her history. `['f10']`
- There is not enough history yet, so no link can be claimed. `['h1']`
- The day's mood record and the day's step total are not known yet. `['n1']`

### fnd_case_2025-11-19T22:45:00+05:30_v4 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening heart rate and glucose were clearly above her usual after a breakfast earlier.**

- Her heart rate was clearly above her usual in the evening and her glucose was far above her usual in the evening. `['m1', 'm2']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `['f16']`
- That morning she recorded coordinating hospital care and family logistics and the day before she recorded that her father was hospitalized with chest pain and weakness, noted as a severe family crisis and involving someone else. `['d1', 'd2']`
- An earlier summary says father hospitalized overnight was the major life event as sleep dropped sharply. `['s1']`
- There is not enough history yet and no link is claimed, and the day's step total is not known yet. `['h1', 'n1']`

### fnd_case_2025-12-24T16:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Afternoon heart rate was clearly above her usual after activity and short sleep**

- More activity in the hour before has tended to move together with higher heart rate in that hour, and short sleep the night before has tended to move together with higher heart rate over the day same day; they often occur together and their separate roles cannot be told apart. `['g1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-01-28T16:45:00+05:30_v3 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Afternoon glucose was clearly above her usual after dinner**

- Glucose was clearly above her usual in the afternoon after a dinner about an hour earlier. `['m1']`
- The size of this meal's rise was among the very highest she has had within the half hour or so after dinners. `['f6']`
- It is not yet known whether the day's medicine record, the day's mood record, or the day's step total are available. `['n1']`

### fnd_case_2026-02-17T18:30:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening glucose higher than usual after lunch**

- Glucose was clearly above her usual in the evening after a lunch a few hours earlier. `['m1']`
- Missed doses on the same day or the day before were present and there is not enough history yet. `['f1']`
- A symptom noted in the diary on the same day or in the days before described physical and emotional exhaustion and taking a day off to recover. `['f2', 'd1']`
- Low activity the day before has tended to move together with higher glucose between meals and was among the very lowest she has had. `['f5']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-03-16T01:15:00+05:30_v8 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Nighttime glucose and heart rate were clearly above her usual.**

- Glucose was clearly above her usual and heart rate was clearly above her usual that night. `['m1', 'm2']`
- She slept clearly less than usual that morning. `['m3']`
- Short sleep the night before was present and was among the very lowest she has had. `['f4', 'f24']`
- Low activity the day before has tended to move together with higher glucose between meals and was among the very lowest she has had. `['f5']`
- Clearly fewer doses were taken than usual that evening and missed doses in the week before was present and there is not enough history yet. `['m4', 'f23']`
- The day's medicine record, the day's mood record, last night's sleep, and where she was that day are not known yet. `['n1']`

### fnd_case_2026-04-02T19:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Heart rate higher than her usual that evening after a lunch earlier**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- More activity in the hour before has tended to move together with higher heart rate in that hour and was high for her. `['f1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-05-01T21:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening medication clearly showed fewer doses than usual after a dinner earlier that evening.**

- Her evening clearly fewer doses were taken than usual after a dinner about an hour earlier. `['m1']`
- Missed doses in the week before was present and there is not enough history yet. `['f4']`
- It is not known where she was that day. `['n1']`
- That morning she noted a holiday and a cooler hour walk. `['d1']`
- The evening before she reflected with her husband and felt genuinely proud of change since an earlier health scare. `['d2']`

### fnd_case_2026-06-12T22:30:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 2, may_discuss_links

**Evening glucose was clearly above her usual after dinner.**

- Glucose was clearly above her usual in the evening, and the size of this meal's rise was high for her within the couple of hours after dinners. `['m1', 'f1']`
- Missed doses on the same day or the day before has tended to move together with higher glucose peaks after dinner same day. `['f2']`
- She reported replacing her usual walk with indoor activity the day before in the evening, and her day's step total is not known yet. `['d1', 'n1']`

### fnd_case_2026-07-29T17:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Afternoon heart rate clearly above her usual after a lunch**

- Heart rate was clearly above her usual in the afternoon. `['m1']`
- More activity in the hour before was present. `['f1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-08-19T15:00:00+05:30_v2 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Afternoon glucose was far below her usual.**

- Her glucose was far below her usual in the afternoon. `['m1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2026-09-16T07:00:00+05:30_v2 (seeded: across months)

`llm` / `ok`, attempts 2, may_discuss_links

**Morning heart rate and blood pressure were clearly above her usual.**

- Heart rate was clearly above her usual and blood pressure was clearly above her usual that morning. `['m1', 'm2']`
- More activity in the hour before was present. `['f1']`
- Short sleep the night before and missed doses on the same day or the day before has tended to move together with, same day, and their separate roles cannot be told apart. `['g1']`
- The day's mood record and where the reading was taken are not known yet. `['n1']`

### fnd_case_2025-10-18T10:15:00+05:30_v4 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Morning heart rate clearly above her usual.**

- Heart rate was clearly above her usual in the morning. `['m1']`
- More activity in the hour before was present. `['f1']`
- A symptom noted in the diary on the same day or in the days before was present. `['f3']`
- Short sleep the night before was present. `['f5']`
- A diary entry in the days before said a recent fever had settled but she felt weak and mentally foggy. `['d2', 'f3']`
- There is not enough history yet and no link can be claimed. `['h1', 'n1']`
- Not known yet: the day's mood record. `['n1']`

### fnd_case_2025-11-03T02:00:00+05:30_v4 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Glucose was clearly above her usual at night.**

- At night, glucose was clearly above her usual. `['m1']`
- There is not enough history yet and no link is claimed; the day's medicine record, the day's mood record, last night's sleep and the day's step total are not known yet. `['h1', 'n1']`

### fnd_case_2025-12-15T08:45:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Morning heart rate clearly above her usual after breakfast and recent short sleep**

- Heart rate was clearly above her usual in the morning. `['m1']`
- Short sleep the night before has tended to move together with higher heart rate over the day, same day. `['f5']`
- Low fluid intake the day before was present. `['f4']`
- The day's mood record is not known yet. `['n1']`
