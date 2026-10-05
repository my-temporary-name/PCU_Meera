# Findings Engine, stage F2: text layer, sample report

33 versions from `findings_text_sample_seed20260_3.jsonl`; model `openai/gpt-5-mini`, reasoning `low`, timeout 90 s, SDK retries 0, one retry with the failed checks, then the code line.

## Totals

- versions with a first-attempt failure: **8 of 33** (24%)
- retried: 8; passed on the retry: 6; **fallbacks to the code line: 2 of 33** (6%)
- model calls: 41; tokens in 52,933, out 45,033 (of which reasoning 36,992); call seconds 480 in total, mean 11.7, longest 20.2

## First-attempt failures by check

| check | versions failing at the first attempt | failure instances |
|---|---:|---:|
| 1 structure | 0 (0%) | 0 |
| 2 refs exist | 0 (0%) | 0 |
| 3 digits, dates, counting words | 2 (6%) | 2 |
| 4 causal wording | 0 (0%) | 0 |
| 5 copied diary text / internal words | 4 (12%) | 4 |
| 6 claim level | 1 (3%) | 1 |
| 7 required statements | 2 (6%) | 2 |
| 8 recurrence wording | 0 (0%) | 0 |

## Recurrence wording

Sentences using "come up before" or "early observation": 0; with a p ref: 0; without one: 0.

Sentences saying "an earlier summary": 23.


## Sentences against their wording classes (heuristic scan, for a human to read)

- none

## Every sampled version

### fnd_case_2025-11-18T08:17:00+05:30_v1 (named case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `c695e697ae`

**That morning her blood pressure was clearly above her usual.**

- That morning her blood pressure was clearly above her usual, and it is not known where the reading was taken. `['m1', 'n1']`
- That morning she recorded that her father was hospitalized with chest pain and weakness, a severe family crisis. `['d1']`
- Missed doses on the same day or the day before were present. `['f1']`
- Very short sleep the night before was present, among the very lowest she has had. `['f4']`
- An earlier summary says medication taking was markedly reduced and multiple medicines were missed. `['s1']`
- There is not enough history yet, so no link is claimed. `['h1']`

- attempt 1: pass
- usage: 1170/1593 tokens 18.03 s

### fnd_case_2025-11-18T08:17:00+05:30_v2 (named case)

source `llm`, status `ok`, attempts 2, mode describe_only, view `507d901b62`

**Morning blood pressure and glucose were clearly above her usual.**

- That morning her blood pressure and glucose were clearly above her usual. `['m1', 'm2']`
- Missed doses in the same day or the day before and a diary symptom note were present in her recent history. `['f1', 'f8', 'f9']`
- Short sleep the night before was present and was among the very lowest she has had. `['f4', 'f11']`
- A diary entry in the days before described her father as unusually tired with reduced appetite, and that day a morning entry noted her father was hospitalized with chest pain and weakness. `['d2', 'd1']`
- There is not enough history yet so no link is claimed, and it is not known yet where the reading was taken or what the day's mood record was. `['h1', 'n1']`

- attempt 1: check 7: no sentence says something is not known yet and cites n1

- attempt 2: pass
- usage: 1425/1550 tokens 17.89 s, 1479/1324 tokens 13.11 s

### fnd_case_2025-11-18T08:17:00+05:30_v3 (named case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `56fce0c5c5`

**Morning blood pressure and glucose were clearly above her usual after lunch**

- Her morning blood pressure and morning glucose were clearly above her usual. `['m1', 'm2']`
- The size of the rise after the lunch was among the very highest she has had within the couple of hours after lunches. `['f13']`
- Missed doses on the same day or the day before were present. `['f1', 'f8', 'f14']`
- Short sleep the night before was present and was among the very lowest she has had. `['f4', 'f11', 'f15']`
- A diary entry in the days before described her father as unusually tired with low appetite at a family lunch and concerned someone else, and a morning diary entry that day recorded her father hospitalized overnight with chest pain and weakness and a severe family crisis. `['d2', 'd1']`
- There is not enough history yet so no link is claimed, and it is not known where the reading was taken, the day's mood record, or the day's step total. `['h1', 'n1']`

- attempt 1: pass
- usage: 1659/1680 tokens 19.09 s

### fnd_case_2026-09-17T21:45:00+05:30_v1 (named case)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `d1a165d03f`

**Evening heart rate was clearly above her usual after a festive dinner.**

- Her evening heart rate was clearly above her usual. `['m1']`
- More activity in the hour before was present and high for her. `['f1']`
- A stressed or low mood period and short sleep on the same day have tended to move together with higher heart rate over the day. `['g1']`
- She reported a heavy work day with much desk work and few proper meals, and earlier noted skipping a main meal amid work and festival hosting pressure. `['d1', 'd2']`
- An earlier summary says she missed multiple medicines during a stressful festival and work day. `['s1']`

- attempt 1: pass
- usage: 1365/962 tokens 11.66 s

### fnd_case_2026-09-17T21:45:00+05:30_v2 (named case)

source `code_line`, status `code_line_fallback`, attempts 2, mode may_discuss_links, view `84dc5b1a90`

**Heart rate was clearly above her usual. Glucose was clearly above her usual.**

- Present: a stressed or low-mood period on the same day, short sleep the night before (among the very lowest she has had), missed doses on the same day or the day before. `[]`
- The size of this meal's rise was among the very highest she has had within the hour or so after dinners. `[]`
- A stressed or low-mood period on the same day and short sleep the night before often occur together, so their separate roles cannot be told apart. `[]`
- Missed doses on the same day or the day before and short sleep the night before were both present. `[]`
- A stressed or low-mood period on the same day has tended to move together with higher heart rate over the day in her history. `[]`
- Short sleep the night before has tended to move together with higher heart rate over the day in her history, on the same day. `[]`
- Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner in her history. `[]`
- Short sleep the night before has tended to move together with higher glucose peaks after dinner in her history. `[]`
- Also present, with no link claimed: more activity in the hour before (high for her). `[]`
- Not known yet: the day's step total. `[]`

- attempt 1: check 3: sentence 3 uses the counting word 'two'

- attempt 2: check 3: sentence 2 contains a digit; check 3: sentence 3 contains a digit; check 3: sentence 3 uses the counting word 'one'
- usage: 1795/1236 tokens 14.8 s, 1847/1405 tokens 15.42 s

### fnd_case_2025-10-19T07:00:00+05:30_v3 (monthly case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `3f15b32aa4`

**Short sleep and high morning heart rate during festival preparations**

- She slept clearly less than usual and her heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- A day away from home, more activity in the hour before, and very short sleep the night before were present. `['f5', 'f7', 'f11']`
- She had festival preparation that day in the morning and the day before involved crowded market shopping. `['d1', 'd2']`
- An earlier summary says she earlier missed a thyroid pill during shopping outings. `['s1']`
- Her mood record for that day is not known yet. `['n1']`
- There is not enough history yet, so no link is claimed. `['h1']`

- attempt 1: pass
- usage: 1250/990 tokens 11.19 s

### fnd_case_2025-11-17T21:00:00+05:30_v3 (monthly case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `4e10c0930a`

**Evening missed doses, higher heart rate, and night higher glucose were recorded.**

- That evening she took clearly fewer doses than usual, her heart rate was clearly above her usual, and that night her glucose was clearly above her usual. `['m1', 'm2', 'm3']`
- A diary entry described her father as unusually tired with low appetite at a family lunch and noted this as concerning and not her own symptom. `['d1']`
- A number of present items were recorded: a stressed or low-mood period on the same day was present, missed doses in the week before were present, short sleep the night before was present and among the very lowest she has had, a symptom noted in the diary on the same day or in the days before was present, and missed doses on the same day or the day before were present. `['f2', 'f4', 'f5', 'f9', 'f11', 'f16', 'f15', 'f8']`
- There is not enough history yet, so no link is claimed. `['h1']`
- It is not known where she was that day, the day's mood record, or last night's sleep. `['n1']`

- attempt 1: pass
- usage: 1519/1128 tokens 12.52 s

### fnd_case_2025-12-25T13:15:00+05:30_v3 (monthly case)

source `llm`, status `ok`, attempts 2, mode may_discuss_links, view `d3c4067e26`

**High heart rate and high glucose followed a festive meal.**

- More activity in the hour before has tended to move together with higher heart rate in that hour and this was among the very highest she has had. `['f1']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f9']`
- Alcohol noted in the diary in the hours before was present, and there is not enough history yet. `['f6']`
- The day's mood record, the day's medicine record, and the day's step total are not known yet. `['n1']`

- attempt 1: check 5: sentence 1 copies 5 or more words of a diary entry

- attempt 2: pass
- usage: 1438/1268 tokens 14.19 s, 1499/1302 tokens 11.49 s

### fnd_case_2026-01-13T09:15:00+05:30_v2 (monthly case)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `4930c7e2e2`

**Morning glucose was clearly above her usual after a meal the hour before.**

- Her glucose that morning was clearly above her usual. `['m1']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f8']`
- Short sleep the night before was present. `['f10']`
- Short sleep has tended to move together with higher glucose peaks after breakfast. `['f3']`
- Her diary the day before notes a richer restaurant dinner in the evening and that a work trip began in the afternoon. `['d1', 'd2']`
- It is not yet known what her medicines were that day and what her step total was. `['n1']`

- attempt 1: pass
- usage: 1382/1181 tokens 12.24 s

### fnd_case_2026-02-07T11:15:00+05:30_v4 (monthly case)

source `llm`, status `ok`, attempts 2, mode may_discuss_links, view `7a35a83fb9`

**Morning heart rate was well above her usual after wedding shopping morning**

- Her heart rate that morning was far above her usual. `['m1']`
- More activity in the hour before has tended to move together with higher heart rate in that hour. `['f1']`
- She spent the morning shopping for a wedding with extended family. `['d1']`
- That day's mood record is not known yet. `['n1']`

- attempt 1: check 5: sentence 2 copies 5 or more words of a diary entry

- attempt 2: pass
- usage: 1153/1139 tokens 11.45 s, 1214/777 tokens 7.44 s

### fnd_case_2026-03-14T01:00:00+05:30_v3 (monthly case)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `cb84af2b41`

**Elevated heart rates observed overnight and the following morning.**

- Her heart rate was clearly above her usual at night, and her resting heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- A short sleep the night before has tended to move together with a higher resting heart rate, same day. `['f9', 'm2']`
- A stressed or low mood period the day before was present. `['f11']`
- She tried an evening walk and abandoned it halfway, feeling drained and guilty. `['d1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`

- attempt 1: pass
- usage: 1253/1288 tokens 11.38 s

### fnd_case_2026-04-02T19:15:00+05:30_v2 (monthly case)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `2d52432add`

**Evening heart rate was higher than usual after dinner.**

- More activity in the hour before has tended to move together with higher heart rate in that hour. `['f1', 'm1']`
- Missed doses in the week before was present and there is not enough history yet. `['f12']`
- Her mood that day and where she was are not known yet. `['n1']`

- attempt 1: pass
- usage: 1166/905 tokens 8.54 s

### fnd_case_2026-06-12T22:30:00+05:30_v1 (monthly case)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `5fcd991065`

**Evening glucose was higher than her usual after dinner.**

- The meal's rise was unusually high for her within the hours after dinners. `['f1']`
- Missed doses on the same day has tended to move together with higher glucose peaks after dinner same day. `['f2']`
- Her diary notes she substituted her usual walk for indoor activity the day before evening. `['d1']`
- The day's step total is not known yet. `['n1']`
- An earlier summary says she missed amlodipine while replacing her walk with indoor exercise. `['s1']`

- attempt 1: pass
- usage: 1211/1141 tokens 10.12 s

### fnd_case_2026-07-08T23:45:00+05:30_v1 (monthly case)

source `llm`, status `ok`, attempts 2, mode may_discuss_links, view `5412e96b9c`

**Evening heart rate was clearly above her usual.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- A stressed or low-mood period and short sleep the night before on the same day have tended to move together with higher heart rate over the day, and they often occur together so their separate roles cannot be told apart. `['g1']`
- That afternoon there was a school contact noting slipping attention and grades, and that evening she had a tense, defensive conversation with her daughter after dinner. `['d1', 'd2']`

- attempt 1: check 5: sentence 3 copies 5 or more words of a diary entry

- attempt 2: pass
- usage: 1306/1132 tokens 10.08 s, 1367/886 tokens 7.65 s

### fnd_case_2026-09-12T06:15:00+05:30_v3 (monthly case)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `f056106bbd`

**Heart rate and resting rate were above her usual that morning.**

- Her heart rate was clearly above her usual and her resting heart rate was clearly above her usual that morning, and more activity in the hour before was present. `['m1', 'm2', 'f1']`
- Low fluid intake the day before has tended to move together with higher heart rate over the day and a higher resting heart rate. `['g1']`
- Her mood record for the day and last night's sleep are not known yet. `['n1']`

- attempt 1: pass
- usage: 1360/1064 tokens 10.75 s

### fnd_case_2026-01-01T20:15:00+05:30_v1 (rare class)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `afa6b45785`

**Evening heart rate was clearly above her usual.**

- More activity in the hour before has tended to move together with higher heart rate in that hour. `['f1']`
- On days with low fluid intake the day before her heart rate over the day has tended to be lower. `['f4']`
- The diary notes a mild celebratory drink the day before and that she stayed up late at a family celebration. `['d1', 'd2']`
- It is not yet known what the day's mood record shows. `['n1']`

- attempt 1: pass
- usage: 1288/687 tokens 6.12 s

### fnd_case_2026-02-13T16:45:00+05:30_v2 (rare class)

source `code_line`, status `code_line_fallback`, attempts 2, mode may_discuss_links, view `da89305477`

**Heart rate was clearly above her usual.**

- Present: more activity in the hour before (among the very highest she has had), short sleep the night before (low for her). `[]`
- More activity in the hour before and short sleep the night before were both present. `[]`
- More activity in the hour before has tended to move together with higher heart rate in that hour in her history. `[]`
- Short sleep the night before may be linked to higher heart rate over the day in her history, on the same day. `[]`
- Not known yet: the day's mood record. `[]`

- attempt 1: check 5: sentence 3 copies 5 or more words of a diary entry; check 6: sentence 1 says 'has tended to move together with' but cites asserted, hedged_same_day

- attempt 2: check 6: sentence 1 says 'has tended to move together with' but cites asserted, hedged_same_day
- usage: 1337/1631 tokens 14.88 s, 1426/1339 tokens 20.23 s

### fnd_case_2026-02-17T18:30:00+05:30_v2 (rare class)

source `llm`, status `ok`, attempts 2, mode may_discuss_links, view `4b1e31df57`

**Evening glucose was clearly above her usual.**

- Her evening glucose was clearly above her usual. `['m1']`
- Missed doses on the same day or the day before were present, and there is not enough history yet. `['f1', 'f7']`
- A diary entry described moderate physical and emotional exhaustion and resting that day, and that symptom was present. `['d1', 'f2']`
- On days with that diary symptom her peaks after dinner have tended to be lower. `['f11']`
- The day's mood record and step total are not known yet. `['n1']`

- attempt 1: check 7: no sentence says something is not known yet and cites n1

- attempt 2: pass
- usage: 1364/1110 tokens 9.36 s, 1418/905 tokens 7.66 s

### fnd_case_2025-11-08T11:00:00+05:30_v2 (rare class)

source `llm`, status `ok`, attempts 1, mode describe_only, view `17be5038ea`

**Morning glucose far below her usual after breakfast.**

- Her glucose was far below her usual in the morning after a breakfast a few hours earlier. `['m1']`
- This may be a sensor artifact. `['f1']`
- There is not enough history yet, so no link can be claimed. `['h1']`
- The day's step total is not known yet. `['n1']`
- An earlier summary says she missed levothyroxine that day, and an earlier summary says she missed metformin and levothyroxine during a midweek holiday rest. `['s1', 's2']`

- attempt 1: pass
- usage: 1040/720 tokens 6.89 s

### fnd_case_2026-03-22T11:00:00+05:30_v2 (artifact case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `7edd7ab12b`

**Marked low morning glucose after a breakfast a few hours earlier**

- That morning her glucose was far below her usual. `['m1']`
- This may be a sensor artifact. `['f1']`
- Her step total for the day is not known yet. `['n1']`
- An earlier summary says she missed blood pressure and thyroid pills. `['s1']`
- An earlier summary says she missed those pills during a stressful deadline week. `['s2']`
- An earlier summary says the latest month included a recovery day for physical and emotional exhaustion. `['s3']`

- attempt 1: pass
- usage: 1071/1123 tokens 9.39 s

### fnd_case_2025-11-08T19:15:00+05:30_v1 (early descriptive case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `cb5a05792f`

**Evening heart rate was clearly above her usual.**

- Her heart rate was clearly above her usual that evening. `['m1']`
- Low fluid intake the day before was present, and there is not enough history yet. `['f4', 'h1']`
- The day's mood record is not known yet. `['n1']`
- An earlier summary says she missed levothyroxine that day. `['s1']`
- An earlier summary says she missed metformin and levothyroxine during a midweek holiday rest. `['s2']`

- attempt 1: pass
- usage: 1052/936 tokens 8.55 s

### fnd_case_2025-10-31T05:15:00+05:30_v6 (early descriptive case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `b470f5d83f`

**Morning glucose and heart rate were clearly above her usual.**

- Her morning glucose and morning heart rate were clearly above her usual. `['m1', 'm2']`
- A stressed or low‑mood period that day was present and missed doses on that day or the prior day were present. `['f3', 'f17', 'f15']`
- There is not enough history yet, so no link is claimed. `['h1']`
- The day's medicine record, last night's sleep, that day's mood record and the day's step total are not yet known. `['n1']`
- An earlier summary says missed blood pressure and thyroid medicines during school meetings and outings. `['s2']`

- attempt 1: pass
- usage: 1174/960 tokens 9.31 s

### fnd_case_2025-10-19T19:15:00+05:30_v9 (early descriptive case)

source `llm`, status `ok`, attempts 1, mode describe_only, view `2fec828392`

**Evening heart rate and glucose were clearly above her usual.**

- Her evening heart rate was clearly above her usual and her evening glucose was clearly above her usual. `['m1', 'm2']`
- Short sleep the night before was present and was among the very lowest she has had. `['f5', 'f11', 'f18']`
- More activity in the hour before was present and a stressed or low-mood period the same day was present. `['f1', 'f2', 'f12']`
- Missed doses on the same day or the day before was present. `['f10']`
- There is not enough history yet, so no link is claimed. `['h1']`
- The day's step total and the day's medicine record are not known yet. `['n1']`

- attempt 1: pass
- usage: 1493/927 tokens 8.55 s

### fnd_case_2025-12-24T09:15:00+05:30_v1 (seeded pick)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `635fcc19e6`

**Morning heart rate clearly above her usual after breakfast**

- Her heart rate was clearly above her usual in the morning after a breakfast earlier. `['m1']`
- Short sleep the night before has tended to move together with higher heart rate on the same day. `['f5']`
- The day's mood record is not yet known. `['n1']`
- An earlier summary says nothing deviated from her usual, and other summaries note missed medication during a break and a severe family crisis. `['s1', 's2', 's3']`

- attempt 1: pass
- usage: 1091/1053 tokens 10.14 s

### fnd_case_2026-08-22T10:30:00+05:30_v2 (seeded pick)

source `llm`, status `ok`, attempts 1, mode describe_only, view `9b8ebc04cc`

**Morning glucose far below her usual**

- Her morning glucose was far below her usual after a breakfast earlier. `['m1']`
- This may be a sensor artifact. `['f1']`
- The day's step total is not known yet. `['n1']`
- An earlier summary says nothing deviated from her usual yesterday. `['s1']`

- attempt 1: pass
- usage: 1069/886 tokens 8.98 s

### fnd_case_2026-01-22T05:15:00+05:30_v2 (seeded pick)

source `llm`, status `ok`, attempts 1, mode describe_only, view `9aefe8d9fd`

**Elevated morning heart rate with low fluid intake noted.**

- Her heart rate that morning was clearly above her usual. `['m1']`
- Low fluid intake the day before was present for her. `['f4']`
- The day's mood record and last night's sleep are not known yet. `['n1']`
- An earlier summary for yesterday says nothing deviated from her usual, and earlier summaries note missed medicines and a mild skin allergy this week and missed metformin and amlodipine on a few days amid life and social notes. `['s1', 's2', 's3']`

- attempt 1: pass
- usage: 1091/744 tokens 7.48 s

### fnd_case_2026-04-06T00:00:00+05:30_v1 (seeded pick)

source `llm`, status `ok`, attempts 2, mode describe_only, view `53c7187a88`

**Nighttime heart rate far above her usual after dinner**

- Her heart rate was far above her usual at night, noted after a dinner earlier that day. `['m1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`
- An earlier summary says she missed metformin. `['s1']`
- An earlier summary says she missed medicines during a week of fiscal year-end wrap-up. `['s2']`
- An earlier summary says she missed routine medicines on some days in the latest month. `['s3']`

- attempt 1: check 3: sentence 3 uses the counting word 'several'

- attempt 2: pass
- usage: 1037/1094 tokens 12.19 s, 1090/923 tokens 10.66 s

### fnd_case_2026-09-14T06:15:00+05:30_v3 (seeded pick)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `3d61bf0c1b`

**Short sleep and higher morning resting heart rate on a festival day**

- Short sleep has tended to move together with a higher resting heart rate same day. `['f15']`
- That morning her heart rate and resting heart rate were clearly above her usual and she slept clearly less than usual. `['m1', 'm3', 'm2']`
- Her diary describes a festival ritual, that she took the day off, and peak festival activity. `['d1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`

- attempt 1: pass
- usage: 1255/1033 tokens 14.84 s

### fnd_case_2026-07-08T00:45:00+05:30_v1 (seeded pick)

source `llm`, status `ok`, attempts 1, mode describe_only, view `29f282fa49`

**Nighttime heart rate was clearly above her usual.**

- That night her heart rate was clearly above her usual. `['m1']`
- Her day's mood record and last night's sleep are not known yet, so no link can be claimed. `['n1']`
- There is enough history available. `['h1']`
- An earlier summary says she missed amlodipine, an earlier summary says she missed metformin and amlodipine while average glucose trended down, and an earlier summary notes work performance review discussions at her job. `['s1', 's2', 's3']`

- attempt 1: pass
- usage: 1041/1024 tokens 11.03 s

### fnd_case_2026-03-16T01:15:00+05:30_v10 (seeded pick)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `c505f5283a`

**Nighttime high glucose and heart rate after fewer evening doses and very short sleep.**

- Missed doses on the same day or the day before were present. `['f1', 'm4']`
- Short sleep the night before was present and was among the very lowest she has had. `['f4', 'f24', 'm3']`
- Low activity the day before has tended to move together with higher glucose between meals. `['f5', 'm1']`
- It is not known yet what her mood record, last night's full sleep details, or where she was that day were. `['n1']`
- An earlier summary says markedly higher medication adherence yesterday. `['s1']`

- attempt 1: pass
- usage: 1409/1080 tokens 14.07 s

### fnd_case_2026-06-19T00:00:00+05:30_v1 (seeded pick)

source `llm`, status `ok`, attempts 1, mode may_discuss_links, view `55d1cd10a8`

**Less drinking at night after an evening meal while away from home.**

- She drank clearly less than usual that night. `['m1']`
- Higher glucose the day before has tended to move together with lower fluid intake that day. `['f3']`
- A day away from home was present. `['f2']`
- An earlier summary says there were fewer strained periods that day. `['s1']`
- An earlier summary says there were missed medicines during a mild seasonal cold. `['s2']`
- An earlier summary says there were missed daily medicines on a few days in the latest month. `['s3']`

- attempt 1: pass
- usage: 1085/1041 tokens 13.58 s

### fnd_case_2026-02-19T20:30:00+05:30_v1 (seeded pick)

source `llm`, status `ok`, attempts 1, mode describe_only, view `cb595d52fa`

**Heart rate was clearly above her usual that evening**

- Her heart rate was clearly above her usual that evening. `['m1']`
- The day's mood record is not yet known. `['n1']`
- An earlier summary says average glucose fell sharply, another notes post wedding physical and emotional exhaustion, and another notes some missed medicines with minor diary events. `['s1', 's2', 's3']`

- attempt 1: pass
- usage: 1026/915 tokens 12.96 s

### fnd_case_2026-05-01T21:00:00+05:30_v1 (seeded pick)

source `llm`, status `ok`, attempts 1, mode describe_only, view `2f16779869`

**Evening doses were clearly fewer than usual.**

- That evening she took clearly fewer doses than usual. `['m1']`
- Missed doses in the prior week were present, and there is not enough history yet. `['f4']`
- That morning she noted a festival and a cooler walk. `['d1']`
- Where she was that day is not known yet. `['n1']`

- attempt 1: pass
- usage: 1218/951 tokens 13.9 s
