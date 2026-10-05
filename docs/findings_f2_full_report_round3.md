# Findings Engine, stage F2: text layer, full run report

284 versions from `findings_text_full_1.jsonl`; model `openai/gpt-5-mini`, reasoning `low`, one retry with the failed checks, then the code line. Checks version `ck-v3`.

## Totals

- first-attempt failures: **62 of 284 (21.8%)**
- retried: 62; passed on the retry: 35; **fallbacks to the code line: 27 (9.5%)**
- model calls 346; tokens in 447,400, out 468,562 (reasoning 401,856); call seconds 4689, mean 13.6, longest 30.2; wall time of the run 15.6 min (938.9 s)
- sentences per model-written version (headline included): mean 5.2, 3: 18, 4: 68, 5: 68, 6: 55, 7: 48

## First-attempt failures by check

| check | versions | share of all versions |
|---|---:|---:|
| 1 structure | 7 | 2.5% |
| 2 refs exist | 0 | 0.0% |
| 3 digits, dates, counting words, view ids | 4 | 1.4% |
| 4 causal wording | 5 | 1.8% |
| 5 copied diary text / internal words | 21 | 7.4% |
| 6 claim level | 10 | 3.5% |
| 7 required statements | 26 | 9.2% |
| 8 recurrence wording | 0 | 0.0% |
| 9 entangled bundle wording | 0 | 0.0% |
| 10 one summary sentence | 0 | 0.0% |

## By mode

| mode | versions | first-attempt failures | fallbacks |
|---|---:|---:|---:|
| describe_only | 165 | 30 (18.2%) | 12 |
| may_discuss_links | 119 | 32 (26.9%) | 15 |

## Fallbacks and why

- fnd_case_2025-10-19T19:15:00+05:30_v5: attempt 1: check 1 there must be 2 to 6 sentences | attempt 2: check 7 no sentence says something is not known yet and cites n1
- fnd_case_2025-11-17T00:15:00+05:30_v1: attempt 1: check 7 no sentence says something is not known yet and cites n1 | attempt 2: check 5 sentence 3 copies 5 or more words of a diary entry
- fnd_case_2025-11-17T21:00:00+05:30_v1: attempt 1: check 7 no sentence says something is not known yet and cites n1 | attempt 2: check 1 there must be 2 to 6 sentences
- fnd_case_2025-11-17T21:00:00+05:30_v2: attempt 1: check 1 there must be 2 to 6 sentences | attempt 2: check 5 sentence 2 copies 5 or more words of a diary entry
- fnd_case_2025-11-18T22:15:00+05:30_v5: attempt 1: check 7 no sentence says something is not known yet and cites n1 | attempt 2: check 1 there must be 2 to 6 sentences
- fnd_case_2025-11-18T22:15:00+05:30_v6: attempt 1: check 5 sentence 3 copies 5 or more words of a diary entry | attempt 2: check 1 there must be 2 to 6 sentences
- fnd_case_2025-11-20T23:00:00+05:30_v2: attempt 1: check 3 sentence 3 uses the counting word 'first'; check 5 sentence 4 copies 5 or more words of a diary entry; check 7 no sentence says something is not known yet and cites n1 | attempt 2: check 5 sentence 3 copies 5 or more words of a diary entry
- fnd_case_2025-12-24T16:15:00+05:30_v2: attempt 1: check 5 sentence 3 copies 5 or more words of a diary entry | attempt 2: check 7 no sentence says something is not known yet and cites n1
- fnd_case_2025-12-25T13:15:00+05:30_v3: attempt 1: check 1 there must be 2 to 6 sentences | attempt 2: check 5 sentence 3 copies 5 or more words of a diary entry
- fnd_case_2026-01-12T00:15:00+05:30_v3: attempt 1: check 6 sentence 2 says 'has tended to move together with' but cites asserted_same_day, hedged | attempt 2: check 6 sentence 2 says 'has tended to move together with' but cites asserted_same_day, hedged
- fnd_case_2026-01-12T00:15:00+05:30_v4: attempt 1: check 6 sentence 2 cites a same-day point but does not say 'same day' | attempt 2: check 6 sentence 1 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged
- fnd_case_2026-01-12T00:15:00+05:30_v5: attempt 1: check 6 sentence 1 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged | attempt 2: check 6 sentence 1 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged
- fnd_case_2026-01-12T00:15:00+05:30_v6: attempt 1: check 6 sentence 2 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged | attempt 2: check 6 sentence 2 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged
- fnd_case_2026-01-12T00:15:00+05:30_v7: attempt 1: check 6 sentence 3 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged | attempt 2: check 6 sentence 1 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged
- fnd_case_2026-01-12T00:15:00+05:30_v8: attempt 1: check 6 sentence 3 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged | attempt 2: check 6 sentence 1 says 'has tended to move together with' but cites asserted, asserted_same_day, hedged
- fnd_case_2026-01-13T21:00:00+05:30_v1: attempt 1: check 5 sentence 4 copies 5 or more words of a diary entry | attempt 2: check 5 sentence 4 copies 5 or more words of a diary entry
- fnd_case_2026-02-13T16:45:00+05:30_v1: attempt 1: check 5 sentence 3 copies 5 or more words of a diary entry; check 6 sentence 1 says 'has tended to move together with' but cites asserted, hedged_same_day | attempt 2: check 6 sentence 1 says 'has tended to move together with' but cites asserted, hedged_same_day
- fnd_case_2026-02-13T16:45:00+05:30_v2: attempt 1: check 5 sentence 3 copies 5 or more words of a diary entry; check 6 sentence 1 says 'has tended to move together with' but cites asserted, hedged_same_day | attempt 2: check 6 sentence 1 says 'has tended to move together with' but cites asserted, hedged_same_day
- fnd_case_2026-02-17T18:30:00+05:30_v2: attempt 1: check 7 no sentence says something is not known yet and cites n1 | attempt 2: check 1 there must be 2 to 6 sentences
- fnd_case_2026-03-14T01:00:00+05:30_v1: attempt 1: check 4 sentence 2 uses the causal word 'because' | attempt 2: check 5 sentence 2 copies 5 or more words of a diary entry
- fnd_case_2026-03-14T21:00:00+05:30_v2: attempt 1: check 4 sentence 5 uses the causal word 'because'; check 7 no sentence says something is not known yet and cites n1 | attempt 2: check 4 sentence 5 uses the causal word 'because'
- fnd_case_2026-03-14T21:00:00+05:30_v3: attempt 1: check 4 sentence 6 uses the causal word 'because'; check 7 no sentence says something is not known yet and cites n1 | attempt 2: check 1 there must be 2 to 6 sentences
- fnd_case_2026-03-16T01:15:00+05:30_v9: attempt 1: check 6 sentence 3 says 'has tended to move together with' but cites asserted, exposure_only | attempt 2: check 1 there must be 2 to 6 sentences
- fnd_case_2026-03-17T07:00:00+05:30_v4: attempt 1: check 5 sentence 4 copies 5 or more words of a diary entry | attempt 2: check 7 no sentence says something is not known yet and cites n1
- fnd_case_2026-03-17T18:15:00+05:30_v2: attempt 1: check 5 sentence 5 copies 5 or more words of a diary entry | attempt 2: check 1 there must be 2 to 6 sentences
- fnd_case_2026-09-11T21:00:00+05:30_v1: attempt 1: check 3 sentence 5 uses the counting word 'several' | attempt 2: check 5 sentence 4 copies 5 or more words of a diary entry
- fnd_case_2026-09-16T18:45:00+05:30_v1: attempt 1: check 5 sentence 3 copies 5 or more words of a diary entry | attempt 2: check 9 sentence 2 cites an entangled bundle but does not say the items often occur together and their separate roles 

## Scans over the model-written sentences

Sentences with "explanation", "reason", "why", "because of" or "result": **0**

Sentences linking a sensor artifact to anything other than the artifact statement (cited ids beyond the measure and the artifact point): **0**

Sentences that cite an earlier summary: **54** in 54 versions; versions with more than one: 0; versions whose view had an earlier summary: 78; artifact versions with one: 0.

Sentences with recurrence wording (come up before / early observation): 0.

## Sentences against their wording classes (heuristic scan)

- none

## Read list (70 versions)

### fnd_case_2025-10-19T19:15:00+05:30_v5 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Heart rate was clearly above her usual. Glucose was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (among the very lowest she has had), missed doses on the same day or the day before. `[]`
- Not known yet: the day's mood record and the day's step total. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-11-17T00:15:00+05:30_v1 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Heart rate was clearly above her usual.**

- Present: a symptom noted in the diary on the same day or in the days before. `[]`
- Not known yet: the day's mood record and last night's sleep. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-11-17T21:00:00+05:30_v1 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Clearly fewer doses were taken than usual.**

- Present: a stressed or low-mood period on the same day, missed doses in the week before, short sleep the night before (among the very lowest she has had). `[]`
- Not known yet: where she was that day. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-11-17T21:00:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Clearly fewer doses were taken than usual. Heart rate was clearly above her usual.**

- Present: a stressed or low-mood period on the same day, missed doses in the week before, short sleep the night before (among the very lowest she has had), a symptom noted in the diary on the same day or in the days before. `[]`
- Not known yet: where she was that day. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-11-18T22:15:00+05:30_v5 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Heart rate was clearly above her usual. Clearly less fluid was taken than usual. Glucose was clearly above her usual. Resting heart rate was far above her usual.**

- Present: a stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before (among the very lowest she has had), short sleep the night before (among the very lowest she has had), a day away from home, missed doses on the same day or the day before, low activity the day before (low for her), a stressed or low-mood period the day before. `[]`
- Not known yet: the day's mood record and last night's sleep. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-11-18T22:15:00+05:30_v6 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Heart rate was clearly above her usual. Clearly less fluid was taken than usual. Glucose was clearly above her usual. Resting heart rate was far above her usual.**

- Present: a stressed or low-mood period on the same day, a symptom noted in the diary on the same day or in the days before, low fluid intake the day before (among the very lowest she has had), short sleep the night before (among the very lowest she has had), a day away from home, missed doses on the same day or the day before, low activity the day before (low for her), a stressed or low-mood period the day before. `[]`
- Not known yet: the day's mood record. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-11-20T23:00:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: missed doses on the same day or the day before, short sleep the night before (low for her), a stressed or low-mood period on the same day, low fluid intake the day before (among the very lowest she has had). `[]`
- Not known yet: the day's step total. `[]`
- There is not enough history yet to say what usually goes with this. `[]`

### fnd_case_2025-12-24T16:15:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (high for her), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2025-12-25T13:15:00+05:30_v3 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual. Glucose was far above her usual.**

- Present: more activity in the hour before (among the very highest she has had). `[]`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Also present, with no link claimed: alcohol noted in the diary in the hours before. `[]`
- Not known yet: the day's mood record, the day's medicine record and the day's step total. `[]`

### fnd_case_2026-01-12T00:15:00+05:30_v3 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual.**

- Present: short sleep the night before (low for her), low activity the day before (low for her). `[]`
- Short sleep the night before and low activity the day before were both present. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Low activity the day before may be linked to higher glucose between meals in her history. `[]`
- Not known yet: the day's medicine record and the day's mood record. `[]`

### fnd_case_2026-01-12T00:15:00+05:30_v4 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual.**

- Present: short sleep the night before (low for her), low activity the day before (low for her). `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `[]`
- Short sleep the night before and low activity the day before were both present. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Low activity the day before may be linked to higher glucose between meals in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Not known yet: the day's medicine record, the day's mood record and the day's step total. `[]`

### fnd_case_2026-01-12T00:15:00+05:30_v5 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: short sleep the night before (low for her), low activity the day before (low for her). `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `[]`
- Short sleep the night before and low activity the day before were both present. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Low activity the day before may be linked to higher glucose between meals in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's medicine record, the day's mood record and the day's step total. `[]`

### fnd_case_2026-01-12T00:15:00+05:30_v6 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: short sleep the night before (low for her), low activity the day before (low for her). `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `[]`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `[]`
- Short sleep the night before and low activity the day before were both present. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Low activity the day before may be linked to higher glucose between meals in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after lunch in her history. `[]`
- Also present, with no link claimed: a stressed or low-mood period on the same day. `[]`
- Not known yet: the day's medicine record, the day's mood record and the day's step total. `[]`

### fnd_case_2026-01-12T00:15:00+05:30_v7 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: short sleep the night before (low for her), low activity the day before (low for her). `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `[]`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `[]`
- Short sleep the night before and low activity the day before were both present. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Low activity the day before may be linked to higher glucose between meals in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after lunch in her history. `[]`
- Also present, with no link claimed: a stressed or low-mood period on the same day. `[]`
- Not known yet: the day's medicine record, the day's mood record and the day's step total. `[]`

### fnd_case_2026-01-12T00:15:00+05:30_v8 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: short sleep the night before (low for her), low activity the day before (low for her). `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `[]`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `[]`
- Short sleep the night before and low activity the day before were both present. `[]`
- Short sleep the night before has tended to move together with higher glucose between meals in her history, on the same day. `[]`
- Low activity the day before may be linked to higher glucose between meals in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after lunch in her history. `[]`
- Also present, with no link claimed: a stressed or low-mood period on the same day. `[]`
- Not known yet: the day's medicine record and the day's step total. `[]`

### fnd_case_2026-01-13T21:00:00+05:30_v1 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Clearly fewer doses were taken than usual.**

- Present: missed doses in the week before, short sleep the night before (low for her). `[]`
- Not known yet: where she was that day. `[]`

### fnd_case_2026-02-13T16:45:00+05:30_v1 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (among the very highest she has had), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before may be linked to higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-02-13T16:45:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (among the very highest she has had), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before may be linked to higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

### fnd_case_2026-02-17T18:30:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual.**

- Present: low activity the day before (among the very lowest she has had), a symptom noted in the diary on the same day or in the days before. `[]`
- Low activity the day before has tended to move together with higher glucose between meals in her history. `[]`
- On days with a symptom noted in the diary on the same day or in the days before, her glucose peaks after dinner have tended to be lower. `[]`
- Also present, with no link claimed: missed doses on the same day or the day before. `[]`
- Not known yet: the day's mood record and the day's step total. `[]`

### fnd_case_2026-03-14T01:00:00+05:30_v1 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Heart rate was clearly above her usual.**

- Not known yet: the day's mood record and last night's sleep. `[]`

### fnd_case_2026-03-14T21:00:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Clearly fewer doses were taken than usual. Heart rate was clearly above her usual.**

- Present: missed doses in the week before, short sleep the night before (low for her), low fluid intake the day before (low for her). `[]`
- Not known yet: where she was that day, the day's mood record and last night's sleep. `[]`

### fnd_case_2026-03-14T21:00:00+05:30_v3 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Clearly fewer doses were taken than usual. Heart rate was clearly above her usual.**

- Present: missed doses in the week before, short sleep the night before (low for her), low fluid intake the day before (low for her). `[]`
- Not known yet: where she was that day, the day's mood record and last night's sleep. `[]`

### fnd_case_2026-03-16T01:15:00+05:30_v9 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Heart rate was far above her usual. She slept clearly less than usual. Clearly fewer doses were taken than usual.**

- Present: low activity the day before (among the very lowest she has had). `[]`
- Low activity the day before has tended to move together with higher glucose between meals in her history. `[]`
- Also present, with no link claimed: short sleep the night before (among the very lowest she has had), low fluid intake the day before (low for her) and missed doses in the week before. `[]`
- Not known yet: the day's medicine record, the day's mood record, last night's sleep and where she was that day. `[]`

### fnd_case_2026-03-17T07:00:00+05:30_v4 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Resting heart rate was far above her usual. Heart rate was clearly above her usual.**

- Present: low activity the day before (low for her), short sleep the night before (among the very lowest she has had). `[]`
- The size of this meal's rise was among the very highest she has had within the half hour or so after breakfasts. `[]`
- Low activity the day before and short sleep the night before were both present. `[]`
- Low activity the day before has tended to move together with higher glucose between meals in her history. `[]`
- Short sleep the night before has tended to move together with a higher resting heart rate in her history, on the same day. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after breakfast in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Also present, with no link claimed: missed doses on the same day or the day before. `[]`
- Not known yet: the day's mood record and the day's step total. `[]`

### fnd_case_2026-03-17T18:15:00+05:30_v2 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Glucose was clearly above her usual. Heart rate was clearly above her usual.**

- Present: low activity the day before (low for her), a stressed or low-mood period on the same day, short sleep the night before (among the very lowest she has had). `[]`
- A stressed or low-mood period on the same day and short sleep the night before often occur together, so their separate roles cannot be told apart. `[]`
- Low activity the day before has tended to move together with higher glucose between meals in her history. `[]`
- A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Also present, with no link claimed: missed doses on the same day or the day before. `[]`

### fnd_case_2026-09-11T21:00:00+05:30_v1 (fallback)

`code_line` / `code_line_fallback`, attempts 2, describe_only

**Clearly fewer doses were taken than usual.**

- Present: missed doses in the week before, short sleep the night before (low for her). `[]`
- Not known yet: where she was that day. `[]`

### fnd_case_2026-09-16T18:45:00+05:30_v1 (fallback)

`code_line` / `code_line_fallback`, attempts 2, may_discuss_links

**Heart rate was clearly above her usual.**

- Present: a stressed or low-mood period on the same day, short sleep the night before (among the very lowest she has had). `[]`
- A stressed or low-mood period on the same day and short sleep the night before often occur together, so their separate roles cannot be told apart. `[]`
- A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`

### fnd_case_2026-03-17T18:15:00+05:30_v3 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening glucose and heart rate were clearly above her usual.**

- Her glucose was clearly above her usual in the evening and her heart rate was clearly above her usual in the evening. `['m1', 'm2']`
- An earlier summary says Missed amlodipine and levothyroxine. `['s1']`
- The a stressed or low-mood period on the same day and the short sleep the night before often occur together and their separate roles cannot be told apart; both are described as higher heart rate over the day and the short sleep the night before is among the very lowest she has had. `['g1']`
- Missed doses on the same day or the day before were present, a stressed or low-mood period on the same day was present, and short sleep the night before was present. `['f1', 'f15', 'f3', 'f17', 'f4', 'f16']`
- That morning she described an extremely stressful deadline day and waking anxious before the alarm. `['d1']`
- It is not known yet the day's step total. `['n1']`

### fnd_case_2026-07-08T23:45:00+05:30_v1 (entangled bundle)

`llm` / `ok`, attempts 2, may_discuss_links

**Evening heart rate was clearly above her usual**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day, and short sleep the night before has tended to move together with higher heart rate over the day and was low for her; they often occur together and their separate roles cannot be told apart. `['g1']`

### fnd_case_2026-09-17T06:15:00+05:30_v2 (entangled bundle)

`llm` / `ok`, attempts 2, may_discuss_links

**Morning heart rate measures were clearly above her usual**

- heart rate was clearly above her usual and resting heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- short sleep the night before and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate same day and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g1']`
- An afternoon diary entry from the day before says she missed a proper midday meal amid overlapping work and festival pressures and notes layered stress. `['d1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`
- There is enough history, and no link is claimed. `['h1']`

### fnd_case_2026-09-17T06:15:00+05:30_v3 (entangled bundle)

`llm` / `ok`, attempts 2, may_discuss_links

**Her morning heart rates were clearly above her usual.**

- More activity in the hour before was present, high for her. `['f1']`
- Short sleep the night before and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; each has tended to move together with a higher resting heart rate, same day. `['g1']`
- A diary entry said she missed a proper midday meal while handling a deadline and hosting duties and noted layered stress. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-09-17T06:15:00+05:30_v4 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Morning heart rate and resting rate were clearly above her usual**

- Her heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- She had a quarter-close deadline day with mostly deskbound work and minimal proper meals, and earlier she had skipped a proper lunch amid layered stress. `['d1', 'd2']`
- more activity in the hour before was present and high for her. `['f1']`
- a stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; a stressed or low-mood period on the same day has tended to move together with higher heart rate over the day and short sleep the night before has tended to move together with higher heart rate over the day. `['g1']`
- short sleep the night before same day and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g2']`

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

- glucose was far below her usual in the morning after a breakfast a few hours earlier. `['m1']`
- This may be a sensor artifact. `['f1']`
- the day's step total is not known yet. `['n1']`
- not enough history yet, and no link can be claimed. `['h1']`

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

- blood pressure was clearly above her usual in the morning. `['m1']`
- missed doses on the same day or the day before were present. `['f1']`
- short sleep the night before, among the very lowest she has had, was present. `['f4']`
- An earlier summary says Medication adherence was markedly down and medicines were missed. `['s1']`
- There is not enough history yet to claim a link. `['h1']`
- It is not known yet where the reading was taken, and that morning she noted a severe family crisis with her father hospitalized for chest pain and weakness. `['n1', 'd1']`

### fnd_case_2025-11-18T08:17:00+05:30_v2 (named case)

`llm` / `ok`, attempts 1, describe_only

**Higher morning blood pressure and glucose with recent missed doses and very short sleep**

- blood pressure was clearly above her usual that morning and glucose was clearly above her usual that morning. `['m1', 'm2']`
- missed doses on the same day or the day before was present. `['f1', 'f8']`
- short sleep the night before, among the very lowest she has had, was present. `['f4', 'f11']`
- a diary entry noted someone else as unusually tired and with reduced appetite in the days before, and a symptom noted in the diary on the same day or in the days before was present. `['d2', 'f9']`
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

### fnd_case_2025-10-15T00:15:00+05:30_v10 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Nighttime heart rate and glucose were clearly above her usual; evening doses were fewer**

- At night her heart rate was clearly above her usual and glucose was clearly above her usual, and in the morning resting heart rate was clearly above her usual. `['m1', 'm2', 'm3']`
- In the evening clearly fewer doses were taken than usual. `['m4']`
- That morning she recorded a mild fever and that she stayed home from work, and earlier she noted a scratchy throat with low energy and a mild evening headache in prior days. `['d1', 'd2', 'd3']`
- There is not enough history yet, and no link is claimed. `['h1']`
- The day's mood record, last night's sleep, the day's medicine record and where she was that day are not known yet. `['n1']`

### fnd_case_2025-11-19T22:45:00+05:30_v1 (seeded: early descriptive)

`llm` / `ok`, attempts 2, describe_only

**Evening heart rate was clearly above her usual amid recent family hospital events and low sleep.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- That morning she recorded severe family care coordination during an ongoing hospital stay, and the day before she recorded a severe family crisis when her father had an overnight hospital stay with chest symptoms. `['d1', 'd2']`
- A stressed or low-mood period on the same day was present, low fluid intake the day before was present and was among the very lowest she has had, and short sleep the night before was present and was among the very lowest she has had. `['f2', 'f4', 'f5']`
- There is not enough history yet, so no link can be claimed. `['h1']`
- An earlier summary says Father hospitalized overnight was the major life event as sleep dropped sharply. `['s1']`

### fnd_case_2025-11-20T23:00:00+05:30_v1 (seeded: early descriptive)

`llm` / `ok`, attempts 2, describe_only

**Evening glucose was clearly above her usual.**

- Her glucose was clearly above her usual in the evening. `['m1']`
- Missed doses on the same day or the day before, short sleep the night before, and a stressed or low-mood period on the same day were present. `['f2', 'f3', 'f4']`
- There is not enough history yet and no link is claimed. `['h1']`
- The day's step total is not known yet. `['n1']`
- An earlier summary says Hospital stay focused on managing care and family arrangements. `['s1']`
- Diary notes mention a hospital stay with improving family situation that evening and coordination of care the day before. `['d1', 'd2']`

### fnd_case_2025-10-15T00:15:00+05:30_v3 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**High nighttime heart rate and glucose after a light dinner**

- Her heart rate and glucose were clearly above her usual that night. `['m1', 'm2']`
- A mild scratchy throat with low energy and achiness was present the day before, and a mild evening headache was present in the days before. `['d1', 'd2', 'f3', 'f10']`
- Low fluid intake the day before and low activity the day before were present for her. `['f4', 'f13']`
- There is not enough history yet and no link is claimed, and the day's mood record, last night's sleep, and the day's medicine record are not known yet. `['h1', 'n1']`

### fnd_case_2025-10-31T05:15:00+05:30_v5 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Morning glucose and heart rate were clearly above her usual**

- Glucose was clearly above her usual in the morning. `['m1']`
- Heart rate was clearly above her usual in the morning. `['m2']`
- A stressed or low-mood period on the same day was present, and there is not enough history yet so no link is claimed. `['f3', 'h1']`
- The day's medicine record, last night's sleep, and the day's mood record are not known yet. `['n1']`

### fnd_case_2025-10-19T19:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening heart rate clearly above her usual after festival morning**

- Her heart rate was clearly above her usual that evening. `['m1']`
- 'more activity in the hour before' was present and high for her. `['f1']`
- 'short sleep the night before' was present and among the very lowest she has had. `['f5']`
- She reported festival preparations that morning. `['d1']`
- An earlier summary says Missed levothyroxine during festival shopping at a mall. `['s1']`
- There is not enough history yet and the day's mood record is not known yet, so no link is claimed. `['h1', 'n1']`

### fnd_case_2025-11-08T11:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Very low morning glucose after a recent breakfast.**

- Her glucose was far below her usual that morning after a breakfast earlier. `['m1']`
- The readings that follow and the day's step total are not known yet. `['n1']`
- There is not enough history yet, and no link is claimed. `['h1']`

### fnd_case_2025-12-20T09:15:00+05:30_v3 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Higher than usual morning heart rate with recent lunch and activity**

- more activity in the hour before has tended to move together with higher heart rate in that hour, high for her. `['f1', 'm1']`
- The day's mood record is not known yet. `['n1']`
- Her diary notes school winter break begins the day before in the morning. `['d1']`

### fnd_case_2026-01-24T03:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Nighttime glucose clearly above her usual**

- Her glucose was clearly above her usual that night. `['m1']`
- It is not known yet whether the day's medicine record, the day's mood record, or last night's sleep were recorded. `['n1']`

### fnd_case_2026-02-14T06:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Far above usual morning heart rate after an evening wedding event.**

- Her heart rate was far above her usual in the morning. `['m1']`
- Alcohol noted in the diary in the hours before was present. `['f6']`
- She recorded social alcohol use with relatives during an evening wedding event and marked it mild. `['d1', 'f6']`
- An earlier summary says Missed levothyroxine at the start of wedding week. `['s1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`

### fnd_case_2026-03-01T22:45:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening glucose was clearly above her usual after dinner.**

- Glucose was clearly above her usual in the evening. `['m1']`
- Missed doses on the same day or the day before were present. `['f2']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2026-04-18T17:15:00+05:30_v2 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Higher afternoon heart rate after an active morning at a family outdoor event**

- 'more activity in the hour before' has tended to move together with 'higher heart rate in that hour'. `['f1', 'm1']`
- She attended a local outdoor family event with much walking that morning. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-05-01T21:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 2, describe_only

**Evening medication count was clearly lower than usual after dinner**

- That evening, clearly fewer doses were taken than usual after a dinner about an hour earlier. `['m1']`
- She recorded a morning festival and a cooler-hour walk. `['d1']`
- She noted that the evening before she reflected with her husband and felt proud of change. `['d2']`
- Missed doses in the week before was present, and there is not enough history yet. `['f4']`
- It is not known yet where she was that day. `['n1']`

### fnd_case_2026-06-12T22:30:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 2, may_discuss_links

**Evening glucose was clearly above her usual after dinner.**

- Glucose was clearly above her usual in the evening, and the size of this meal's rise was high for her within the couple of hours after dinners. `['m1', 'f1']`
- Missed doses on the same day or the day before has tended to move together with higher glucose peaks after dinner same day. `['f2']`
- She reported replacing her usual walk with indoor activity the day before in the evening, and her day's step total is not known yet. `['d1', 'n1']`

### fnd_case_2026-07-08T00:45:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Elevated night heart rate noted after an evening meal.**

- heart rate was clearly above her usual that night. `['m1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`

### fnd_case_2026-08-19T15:00:00+05:30_v2 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Afternoon glucose was far below her usual.**

- Her glucose was far below her usual in the afternoon. `['m1']`
- The day's step total is not known yet. `['n1']`

### fnd_case_2026-09-13T07:00:00+05:30_v5 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Heart rate was far above her usual after a busy day of festival preparation.**

- More activity in the hour before was present and high for her. `['f1']`
- 'short sleep the night before' has tended to move together with higher heart rate over the day, same day. `['f5', 'm1']`
- A diary entry says she spent the previous day preparing for a festival and was genuinely highly active. `['d1']`
- The day's mood record is not known yet. `['n1']`
- An earlier summary says Missed diabetes and thyroid medicines during a full day of festival prep. `['s1']`

### fnd_case_2025-10-27T20:30:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening heart rate was clearly above her usual.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- There is not enough history yet, so no link is claimed. `['h1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2025-11-03T02:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Glucose was clearly above her usual at night.**

- glucose was clearly above her usual at night. `['m1']`
- There is not enough history yet, so no link is claimed. `['h1']`
- the day's medicine record, the day's mood record, and last night's sleep are not known yet. `['n1']`

### fnd_case_2025-12-20T09:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Morning heart rate clearly above her usual after breakfast**

- Her heart rate was clearly above her usual in the morning after a breakfast earlier. `['m1']`
- There is enough history to compare, and no link is claimed. `['h1']`
- The day's mood record is not known yet. `['n1']`
- A diary entry from the day before in the morning notes that school winter break started. `['d1']`

### fnd_case_2026-01-24T03:15:00+05:30_v2 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Nighttime glucose was clearly above her usual.**

- glucose was clearly above her usual at night after a dinner a few hours earlier. `['m1']`
- The day's medicine record, the day's mood record, and last night's sleep are not known yet. `['n1']`

### fnd_case_2026-02-04T22:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening glucose was clearly above her usual after dinner**

- Her glucose was clearly above her usual in the evening. `['m1']`
- Missed doses on the same day or the day before were present in her record. `['f2']`
- That evening she had calls with relatives about a cousin's wedding and family excitement was noted. `['d1']`
- The day's step total is not yet known. `['n1']`

### fnd_case_2026-03-14T21:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening medication doses were clearly fewer than usual after a recent dinner.**

- Her evening medication doses were clearly fewer than usual. `['m1']`
- missed doses in the week before were present. `['f4']`
- short sleep the night before was present and was low for her. `['f5']`
- The day before she began an intentional evening walk to cope with stress, abandoned it partway and felt guilty, noted as psychosocial - behavior style demonstration. `['d1']`
- It is not known where she was that day. `['n1']`

### fnd_case_2026-04-11T10:15:00+05:30_v4 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Heart rate clearly above her usual after a longer family walk**

- Her heart rate was clearly above her usual that morning. `['m1']`
- More activity in the hour before has tended to move together with higher heart rate in that hour. `['f1']`
- She reported a longer family walk that morning and described it as positive. `['d1']`
- The day's mood record is not yet known and no link can be claimed. `['n1']`

### fnd_case_2026-06-17T20:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Glucose was far above her usual in the evening after a lunch a few hours earlier.**

- Glucose was far above her usual in the evening after a lunch a few hours earlier. `['m1']`
- A symptom noted in the diary on the same day or in the days before was present. `['f2']`
- A stressed or low-mood period on the same day was present. `['f3']`
- Low activity the day before has tended to move together with higher glucose between meals, among the very lowest she has had. `['f5']`
- The day's medicine record is not known yet. `['n1']`

### fnd_case_2026-07-16T21:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Evening dose count fell noticeably after dinner.**

- That evening clearly fewer doses were taken than usual after a dinner earlier. `['m1']`
- missed doses in the week before was present and there is not enough history yet. `['f4']`
- That evening she gave extra time to support homework and noted it as positive. `['d1']`
- It is not known where she was that day. `['n1']`

### fnd_case_2026-08-19T15:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Glucose was far below her usual in the afternoon.**

- Glucose was far below her usual in the afternoon. `['m1']`
- The readings that follow and the day's step total are not known yet. `['n1']`

### fnd_case_2026-09-12T06:15:00+05:30_v3 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Morning heart rate and resting heart rate were clearly above her usual.**

- Heart rate was clearly above her usual and resting heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- More activity in the hour before was present. `['f1']`
- Low fluid intake the day before has tended to move together with higher heart rate over the day and has tended to move together with a higher resting heart rate; they often occur together and their separate roles cannot be told apart. `['g1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`
- An earlier summary says Missed medicines amid festival preparations. `['s1']`

### fnd_case_2025-10-31T05:15:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Glucose was clearly above her usual that morning.**

- Glucose was clearly above her usual that morning. `['m1']`
- There is not enough history yet, so no link can be claimed. `['h1']`
- It is not yet known what the day's medicine record, the day's mood record, and last night's sleep were. `['n1']`

### fnd_case_2025-11-10T00:30:00+05:30_v3 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Higher than usual night glucose and morning blood pressure after a breakfast a short while earlier**

- Glucose was clearly above her usual at night. `['m1']`
- Blood pressure was clearly above her usual in the morning after a breakfast a short while earlier. `['m2']`
- Short sleep the night before was present and there is not enough history yet. `['f9']`
- There is not enough history yet and no link can be claimed. `['h1']`
- The day's medicine record, the day's mood record, last night's sleep, and where the reading was taken are not known yet. `['n1']`
