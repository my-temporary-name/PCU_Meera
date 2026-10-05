# Findings Engine, stage F2: text layer, fourth round report (p-v2, ck-v4)

284 versions from `findings_text_full_4.jsonl`; model `openai/gpt-5-mini`, reasoning `low`, one retry with the failed checks, then the code line. Checks version `ck-v4`.

## Totals

- first-attempt failures: **12 of 284 (4.2%)**
- retried: 12; passed on the retry: 12; **fallbacks to the code line: 0 (0.0%)**
- model stored attempts 296; tokens in 374,754, out 394,725 (reasoning 339,648); call seconds 3933, mean 13.3, longest 30.2; wall time of the run re-check 0.2 s; model re-run 57.7 s
- sentences per model-written version (headline included): mean 5.4, 3: 18, 4: 72, 5: 70, 6: 53, 7: 58, 8: 11, 9: 1, 10: 1

## Before and after this round

| | before (p-v1, ck-v3) | after (p-v2, ck-v4) |
|---|---:|---:|
| first-attempt failures | 62 (21.8%) | 12 (4.2%) |
| retried | 62 | 12 |
| fallbacks to the code line | 27 (9.5%) | 0 (0.0%) |
| versions with a code-appended sentence | 0 | 24 |
| versions the cleanup changed | 0 | 114 |

Model work of this round (no-model re-check first, then the model for 11 versions): **14 calls**, tokens in 21,312, out 23,388, call seconds 211; fallbacks among them 0.

Of the 27 earlier fallbacks, now accepted: 27; versions that were accepted before and are fallbacks now: 0.

## First-attempt failures by check

| check | versions | share of all versions |
|---|---:|---:|
| 1 structure | 0 | 0.0% |
| 2 refs exist | 0 | 0.0% |
| 3 digits, dates, counting words, view ids | 4 | 1.4% |
| 4 causal wording | 4 | 1.4% |
| 5 copied diary text / internal words | 2 | 0.7% |
| 6 claim level | 2 | 0.7% |
| 7 required statements | 0 | 0.0% |
| 8 recurrence wording | 0 | 0.0% |
| 9 entangled bundle wording | 0 | 0.0% |
| 10 one summary sentence | 0 | 0.0% |

## By mode

| mode | versions | first-attempt failures | fallbacks |
|---|---:|---:|---:|
| describe_only | 165 | 6 (3.6%) | 0 |
| may_discuss_links | 119 | 6 (5.0%) | 0 |

## Fallbacks and why

- none

## Scans over the model-written sentences

Sentences with "explanation", "reason", "why", "because of" or "result": **0**

Sentences linking a sensor artifact to anything other than the artifact statement (cited ids beyond the measure and the artifact point): **0**

Sentences that cite an earlier summary: **66** in 66 versions; versions with more than one: 0; versions whose view had an earlier summary: 78; artifact versions with one: 0.

Sentences with recurrence wording (come up before / early observation): 0.

## Sentences against their wording classes (heuristic scan)

- none

## Read list (35 versions)

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

- Her glucose was clearly above her usual in the evening and her heart rate was clearly above her usual in the evening. `['m1', 'm2']`
- An earlier summary says missed amlodipine and levothyroxine. `['s1']`
- The a stressed or low-mood period on the same day and the short sleep the night before often occur together and their separate roles cannot be told apart; both are described as higher heart rate over the day and the short sleep the night before is among the very lowest she has had. `['g1']`
- Missed doses on the same day or the day before were present, a stressed or low-mood period on the same day was present, and short sleep the night before was present. `['f1', 'f15', 'f3', 'f17', 'f4', 'f16']`
- That morning she described an extremely stressful deadline day and waking anxious before the alarm. `['d1']`
- It is not known yet the day's step total. `['n1']`

### fnd_case_2026-07-08T23:45:00+05:30_v1 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening heart rate was clearly above her usual.**

- Her heart rate was clearly above her usual in the evening. `['m1']`
- An entangled pair — a stressed or low-mood period on the same day and short sleep the night before, low for her — often occur together and their separate roles cannot be told apart; this has tended to move together with higher heart rate over the day same day. `['g1']`
- That afternoon a school call noted concern about slipping grades and reduced attentiveness, described as mild to moderate. `['d1']`
- That evening she had a difficult, defensive conversation with her daughter after dinner, described as tense. `['d2']`

### fnd_case_2026-09-16T18:45:00+05:30_v1 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Evening heart rate clearly above her usual after a pressured afternoon**

- Her heart rate was clearly above her usual that evening. `['m1']`
- A stressed or low-mood period on the same day and short sleep the night before have tended to move together with higher heart rate over the day; they often occur together and their separate roles cannot be told apart, and the short sleep was among the very lowest she has had. `['g1']`
- That afternoon she missed a proper lunch while facing overlapping work deadline and festival hosting pressure. `['d1']`

### fnd_case_2026-09-17T06:15:00+05:30_v2 (entangled bundle)

`llm` / `ok`, attempts 2, may_discuss_links

**Morning heart rate measures were clearly above her usual**

- Heart rate was clearly above her usual and resting heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- Short sleep the night before and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate same day and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g1']`
- An afternoon diary entry from the day before says she missed a proper midday meal amid overlapping work and festival pressures and notes layered stress. `['d1']`
- The day's mood record and last night's sleep are not known yet. `['n1']`
- There is enough history, and no link is claimed. `['h1']`

### fnd_case_2026-09-17T06:15:00+05:30_v3 (entangled bundle)

`llm` / `ok`, attempts 2, may_discuss_links

**Morning heart rate and resting heart rate were clearly above her usual.**

- Heart rate was clearly above her usual in the morning, and resting heart rate was clearly above her usual in the morning. `['m1', 'm2']`
- More activity in the hour before was present and was high for her. `['f1']`
- Short sleep the night before and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate same day, and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g1']`
- Diary entry describes that she missed a proper midday meal while under combined work and hosting pressure in the afternoon. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-09-17T06:15:00+05:30_v4 (entangled bundle)

`llm` / `ok`, attempts 1, may_discuss_links

**Morning heart rate and resting rate were clearly above her usual**

- Her heart rate was clearly above her usual and resting heart rate was clearly above her usual that morning. `['m1', 'm2']`
- She had a quarter-close deadline day with mostly deskbound work and minimal proper meals, and earlier she had skipped a proper lunch amid layered stress. `['d1', 'd2']`
- More activity in the hour before was present and high for her. `['f1']`
- A stressed or low-mood period on the same day and short sleep the night before often occur together and their separate roles cannot be told apart; a stressed or low-mood period on the same day has tended to move together with higher heart rate over the day and short sleep the night before has tended to move together with higher heart rate over the day. `['g1']`
- Short sleep the night before same day and a stressed or low-mood period the day before often occur together and their separate roles cannot be told apart; short sleep the night before has tended to move together with a higher resting heart rate and a stressed or low-mood period the day before has tended to move together with a higher resting heart rate. `['g2']`

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

### fnd_case_2025-11-13T21:00:00+05:30_v1 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Evening insulin dosing was far lower than usual after dinner**

- Far fewer doses were taken than usual in the evening after a dinner about an hour earlier. `['m1']`
- Missed doses in the week before were present, and there is not enough history yet so no link is claimed. `['f4', 'h1']`
- It is not known where she was that day. `['n1']`

### fnd_case_2025-10-31T05:15:00+05:30_v3 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Morning glucose and heart rate were clearly above her usual.**

- Her glucose was clearly above her usual that morning. `['m1']`
- Her heart rate was clearly above her usual that morning. `['m2']`
- A stressed or low-mood period on the same day was present, there is not enough history yet, and no link is claimed. `['f3', 'h1']`
- Not known yet: the day's medicine record, last night's sleep and the day's mood record. `['n1']`

### fnd_case_2025-10-15T00:15:00+05:30_v7 (seeded: early descriptive)

`llm` / `ok`, attempts 1, describe_only

**Nighttime heart rate and glucose were clearly above her usual; morning resting heart rate also elevated**

- At night her heart rate was clearly above her usual and her glucose was clearly above her usual. `['m1', 'm2']`
- In the morning her resting heart rate was clearly above her usual. `['m3']`
- A symptom noted in the diary on the same day or in the days before was present. `['f3', 'f10', 'f15']`
- That morning she recorded a moderate fever and that she missed work, the day before she noted a scratchy throat with low energy and body ache, and in prior days she noted a mild evening headache. `['d1', 'd2', 'd3']`
- There is not enough history yet, and no link is claimed. `['h1']`
- The day's mood record, last night's sleep, and the day's medicine record are not known yet. `['n1']`

### fnd_case_2025-11-20T23:00:00+05:30_v1 (seeded: early descriptive)

`llm` / `ok`, attempts 2, describe_only

**Evening glucose was clearly above her usual.**

- Her glucose was clearly above her usual in the evening. `['m1']`
- Missed doses on the same day or the day before, short sleep the night before, and a stressed or low-mood period on the same day were present. `['f2', 'f3', 'f4']`
- There is not enough history yet and no link is claimed. `['h1']`
- The day's step total is not known yet. `['n1']`
- An earlier summary says hospital stay focused on managing care and family arrangements. `['s1']`
- Diary notes mention a hospital stay with improving family situation that evening and coordination of care the day before. `['d1', 'd2']`

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

### fnd_case_2025-11-10T00:30:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Nighttime glucose clearly above her usual following a recent dinner**

- Her glucose was clearly above her usual that night. `['m1']`
- There is not enough history yet, and no link is claimed. `['h1']`
- The day's medicine record, the day's mood record, and last night's sleep are not yet known. `['n1']`

### fnd_case_2025-12-20T09:15:00+05:30_v2 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Morning heart rate was clearly above her usual after breakfast.**

- Her heart rate was clearly above her usual that morning after a breakfast a few hours earlier. `['m1']`
- More activity in the hour before has tended to move together with higher heart rate in that hour, high for her. `['f1']`
- A diary entry notes that a school winter break began earlier and was recorded the day before in the morning. `['d1']`
- There is enough history, and the day's mood record is not known yet. `['h1', 'n1']`

### fnd_case_2026-01-24T03:15:00+05:30_v5 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Nighttime glucose was clearly above her usual and her afternoon heart rate was high**

- More activity in the hour before has tended to move together with higher heart rate in that hour. `['f13', 'm2']`
- Glucose was clearly above her usual that night after a lunch a few hours earlier. `['m1']`
- Low fluid intake the day before was present. `['f16']`
- It is not known yet whether the day's medicine record, the day's mood record, last night's sleep, or the day's step total are available. `['n1']`

### fnd_case_2026-02-07T11:15:00+05:30_v3 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Far above usual morning heart rate after extended family shopping**

- Her heart rate was far above her usual in the morning. `['m1']`
- More activity in the hour before has tended to move together with higher heart rate in that hour and was high for her. `['f1', 'm1']`
- She reports extended family shopping that morning. `['d1']`
- The day's mood record is not known yet. `['n1']`

### fnd_case_2026-03-17T07:00:00+05:30_v5 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Higher than usual morning glucose and heart rate after a large breakfast rise.**

- Her glucose was clearly above her usual that morning, and her resting heart rate was far above her usual that morning. `['m1', 'm2', 'm3']`
- Missed doses on the same day or the day before were present. `['f1', 'f13']`
- Low activity the day before, short sleep the night before, short sleep the night before, and short sleep the night before often occur together and their separate roles cannot be told apart; low activity the day before has tended to move together with higher glucose between meals; short sleep the night before has tended to move together with higher glucose peaks after breakfast; short sleep the night before has tended to move together with a higher resting heart rate same day; short sleep the night before has tended to move together with higher heart rate over the day same day. `['g1']`
- Her diary noted a critical deadline day with peak stress and waking anxious before the alarm. `['d1']`
- An earlier summary says missed amlodipine and levothyroxine. `['s1']`
- Not known yet: the day's step total and the day's mood record. `['n1']`

### fnd_case_2026-04-11T10:15:00+05:30_v2 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Morning heart rate clearly above her usual after breakfast and activity**

- More activity in the hour before has tended to move together with higher heart rate in that hour. `['f1']`
- Her heart rate was clearly above her usual in the morning. `['m1']`
- A morning diary entry says she went on a longer family walk and that it was positive. `['d1']`
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

### fnd_case_2026-09-13T07:00:00+05:30_v5 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Heart rate was far above her usual after a busy day of festival preparation.**

- More activity in the hour before was present and high for her. `['f1']`
- Short sleep the night before has tended to move together with higher heart rate over the day, same day. `['f5', 'm1']`
- A diary entry says she spent the previous day preparing for a festival and was genuinely highly active. `['d1']`
- The day's mood record is not known yet. `['n1']`
- An earlier summary says missed diabetes and thyroid medicines during a full day of festival prep. `['s1']`

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

### fnd_case_2025-11-08T11:00:00+05:30_v1 (seeded: across months)

`llm` / `ok`, attempts 1, describe_only

**Very low morning glucose after a recent breakfast.**

- Her glucose was far below her usual that morning after a breakfast earlier. `['m1']`
- The readings that follow and the day's step total are not known yet. `['n1']`
- There is not enough history yet, and no link is claimed. `['h1']`

### fnd_case_2025-12-25T13:15:00+05:30_v3 (seeded: across months)

`llm` / `ok`, attempts 1, may_discuss_links

**Afternoon heart rate and glucose were clearly above her usual.**

- That afternoon her heart rate was clearly above her usual and her glucose was far above her usual. `['m1', 'm2']`
- An earlier summary says sharply more steps during holiday preparations. `['s1']`
- More activity in the hour before has tended to move together with higher heart rate in that hour and was among the very highest she has had. `['f1']`
- Alcohol was noted in the diary in the hours before and there is not enough history yet. `['f6']`
- A diary entry records a social alcohol occasion with friends that afternoon. `['d1']`
- The size of this meal's rise was among the very highest she has had within the hour or so after lunches. `['f9']`
- The day's mood record, the day's medicine record, and the day's step total are not yet known. `['n1']`
