# Findings Engine: Definition Spec

## Amendments (master copy; decided after the Step 1 review)

These amendments resolve the 34 points of `docs/findings_pi_step1_report.md`. **Where the body of this document and an amendment differ, the amendment wins.** The repo copies of the specs are the master. Item numbers are the report's.

| # | Point | Resolution |
|---|---|---|
| 1 | File name | Renamed to `findings_engine_spec.md`; every cross-reference now resolves. |
| 2 | Deferred and unmatched hand-offs; the case count | A `deferred` or `unmatched` hand-off is **recorded in `case_handoffs` (flag `counted: false`) but never opens a case and never extends the gap clock.** One that arrives while no case is open is logged in `unattached_handoffs`. On the first patient at a 6-hour gap: **116 cases, 279 counted hand-offs** (the 8 deferred screen-time hand-offs are recorded only). At 3 hours: 176 cases; at 12 hours: 85. |
| 3 | Closing and immutability | Closing is recorded in the `cases` table: `closed_at` (= the last counted hand-off + `gap_hours`, a time on the replay clock) and `status`. **No closing version is written.** Stored versions keep `provisional: true` and `closed: false` as they were when written; a reader asks `cases` whether a version is the last one and whether the case is closed. 5.4 to 5.6, 9.1 and 13.9 read accordingly. |
| 4 | Versions for hand-offs without factors | A version is written for each counted hand-off (it opens or joins the case) and for each completion. A deferred hand-off writes none. On the first patient: 279 + 5 = **284 versions**. |
| 5 | Completions | A completion's time is `evaluated_from.end` of its `event_completions` row (= the event's `earliest_evaluation_time`); it is the `as_of` of the version it causes. `completion_id` = `<evidence_id>#<candidate>`. In replay, events are ordered by time; at equal times, hand-offs come before completions. |
| 6 | Factor identity | Relationship factors merge by `relationship_key`. Presence checks merge by candidate. Percentile, shape and pattern checks are one factor per hand-off. Factors without a key (reasons `no_definition`, `no_meal_kind`, `no_relationship`, ...) merge by candidate and reason. "A factor never appears twice" means once per key or per event. |
| 7 | Merging exposure states | `exposed` > `not_yet_available` > `not_exposed` > `no_data`. |
| 8 | Mode | `relationship` only if at least one **relationship** factor is usable (label `supported` or `suggestive`), `exposed` and carries a claim class (`asserted`, `asserted_same_day`, `hedged`, `hedged_same_day`). Otherwise `descriptive`. Event-level statements (`event_unusual`, `artifact_note`, `contrary_note`) are added in either mode. The "event-level only" template of Appendix C is the descriptive template when the only content is event-level. Example B gets the meal line. |
| 9 | Wording-class precedence | Applied in this order. (1) Exposure `not_yet_available` gives `not_known_yet`. (2) Exposure `not_exposed` or `no_data` gives `not_mentioned`. (3) Relationship factors: label `supported` or `suggestive` with `placebo_fired` gives `exposure_only`; `supported` gives `asserted` or (with `same_day_unverified`) `asserted_same_day`; `suggestive` gives `hedged` or `hedged_same_day`; `not_supported` with `contrary` and without `placebo_fired` gives `contrary_note`, otherwise `exposure_only`; `insufficient` with reason `history` or `small_group` gives `exposure_only_history`, with any other reason `not_mentioned`. (4) Event-level: percentile `supported` gives `event_unusual`; shape `supported` gives `artifact_note`; presence gives `exposure_only` only if present is true; pattern `supported` gives `exposure_only`; everything else gives `not_mentioned`. There are **11 wording classes**: asserted, asserted_same_day, hedged, hedged_same_day, exposure_only, exposure_only_history, contrary_note, not_mentioned, not_known_yet, event_unusual, artifact_note. |
| 10 | `contrary_note` sentence | Each outcome has a `contrary` sentence in the phrase book ("her glucose peaks after dinner have tended to be lower"). |
| 11 | Groups | Entangled groups are the connected components of the `entangled` overlap flags (union over the case's hand-offs; an overlap entry's `a` and `b` are matched to factors by the part of the key before `->`, within the same hand-off's record). Only relationship factors with a claim class can be members; `exposure_only` factors and event-level factors are not. The remaining claim-class, exposed factors form one `co_exposed` group if there are at least two. Group ids: entangled groups first (by first member), then the co-exposed group. |
| 12 | Position words | Lower band edge inclusive, upper exclusive, the last band closed at 100. The risk side comes from the **Evidence library** (an input of Findings, read only); event percentiles use the high side. Binarized exposures have no percentile and no position words. The event percentile's position carries a suffix from the phrase book ("within the hour or so after dinners"). |
| 13 | Repeat information | `seen_before` = the band of the latest `local_date` among the relationship's entries in all mid-term memories (the open week included, written at or before `as_of`) and its long-term `last_seen`, **excluding the current case**; rolling 7 and 28 days (`this_week`, `recent_weeks`, else `earlier`; `none` if never). With PI absent (F1) it is `none` and `pi_status` is null. |
| 14 | History note | Over the case's relationship factors that have a key: none are `insufficient(history)` gives `enough`; more than half give `not_enough_history_yet`; otherwise `enough_for_some`. No such factors gives `enough`. |
| 15 | Templates and vocabulary | The phrase book holds one clause template per wording class (`classes`), a noun phrase and number per hand-off measure (`measures`), words for the meal label (underscores to spaces, with an article), words for the minutes since the meal (`meal_ago_words`), words for the elapsed time of a percentile (`elapsed_words`), a `pending` phrase per exposure (for "not known yet"), and a `number` per exposure (has/have). |
| 16 | The view | The view carries explicit items `h1` (history note), `n1` (not known yet) and `p1`... (PI items). Diary text may contain digits; the model must not repeat them. The diary item carries `note` = the entry's `meta.note`. |
| 17 | Checks | Check 6 detects the stems "tended to move together" and "linked to". No window phrase contains a counting word, so check 3 needs no exception list (the `exact_window_phrases` setting is dropped). Check 5's internal-word list (including "class") is used in the check and in the prompt. |
| 18 | The record | `refs.diary` and `refs.state_memory` are lists of `{view_id, context_id}` / `{view_id, window_id}`. `status` is `ok` in the code-only mode (`text.source = code_line`). Every factor with label `insufficient` carries `insufficient_reason`. Stored versions have `provisional: true`, `closed: false` (item 3). |
| 19 | State memory | `yesterday_day` = `day_<yesterday>`, `last_week` = the rolling window `week_ENDING_<yesterday>`, `latest_month` = the checkpoint with the latest `end_date` before the local date of `as_of`. Windows whose `gist_status` is in `state_memory.skip_statuses` (`code_line_early`) are not used. |
| 20 | The event loop | F1 includes a minimal ordered loop: hand-offs by `opened_at` then `handoff_id`, completions by evaluation time, cases closed when a later event passes the gap. PI's stage extends it. |
| 23 | Candidate with no demotion path | Parked (PI). |
| 28 | Wording tables | This spec and the PI spec win over the overview's section 8. |
| 29 | Statuses | The PI spec wins over the overview. |
| 30 | Evidence reasons | Covered by item 9. |
| 31 | End-of-day outcomes | The case `local_date` is the day of `opened_at`; the Evidence `as_of_date` may be the day before; both are kept and not conflated. |
| 32 | The Evidence library is an input | Section 6 gains: **Evidence library** (config path): pairs, exposure risk side, outcome direction, check ordering. Read only. |
| 33 | Whose symptom | The diary note (`meta.note`) is passed to the view as `severity_or_note`; the entry about her father carries "concerning, not her own symptom". A structured `subject` field upstream stays parked. |
| 34 | `7d` window | Added to A.3. |
| P | Phrase book (Appendix A) edits | "higher glucose peaks after dinner"; `3d` = "on the same day or in the days before"; `720m` = "in the hours before"; `7d` = "in the week before"; elapsed words "half hour or so", "hour or so", "couple of hours"; `thyroid_status` = "her thyroid medicine", `other_medications` = "other medicines she takes", `hypoglycemic_agent` = "insulin or a similar medicine". |
| Q | Items 9, 11, 14, 15, 17 and all others not named | The Step 1 proposals are accepted as written. |
| R | Four changes after F1 | (1) Presence-check facts (static facts such as "her thyroid medicine") stay in the structured layer (class `exposure_only`) but are left out of the code line and of the text layer's view; the phrase book marks them `static: true`, checked against the library (exactly the presence checks). (2) The co-exposed group sentence is "<A> and <B> were both present." ("<A>, <B> and <C> were all present." for more). The entangled sentence is unchanged. (3) A `contrary_note` sentence names its exposure: "On days with <exposure phrase>, her <outcome phrase> has tended to be lower."; Appendix B rule 3 reads "on days with that factor". (4) The ", on the same day" suffix is unchanged (parked). A meal label's number is dropped from the words ("festive_snack_1" -> "a festive snack"). |
| S | Text layer (stage F2) decisions | The text layer never touches `findings` (versions stay as F1 wrote them). Its result is stored in `finding_text` (text, source, status) and `finding_llm` (raw answers, usage and check results, one list entry per attempt), keyed by version; `--rebuild` of the code layer leaves them. The cache key is the view hash plus the model, effort, prompts and retry setting, so a changed prompt is never served a stale answer. The view lists every factor except `not_mentioned`, `not_known_yet` (covered by `n1`) and static presence checks; `h1` and `p<k>` as in 8.1; `severity_or_note` is the entry's `meta.note`. Check 3 also rejects month names and clock words; check 5 compares runs of `copy_words` (5) words with each diary text and note; check 6: "has/have tended to move together with" and "may be linked to" are recognised in both forms, and a sentence that uses one must cite at least one factor of an allowed class; check 7: the history sentence says "not enough history" and cites `h1`, the not-known-yet sentence says "not known yet" and cites `n1`. A failed call (timeout, API error) counts as a failed attempt. |
| T | Text layer, second round | (1) A cited bundle id counts as citing all its members; the claim level is judged on the members (check 6; the "must cite all members" sentence is dropped). (2) The view's keys and values contain no internal word: `case` -> `situation`, `factors` -> `points`, `groups` -> `bundles` (item key `group` -> `bundle`), `class` -> `wording`, `state_memory` -> `earlier_summaries`, `pi` -> `earlier_conclusions`, the wording `exposure_only` -> `present_only` and `exposure_only_history` -> `present_only_history`, the mode `relationship` -> `may_discuss_links` and `descriptive` -> `describe_only`; `exposure` and `exposures` join the internal-word list (check 5 and the prompt). A test scans every view. (3) A diary entry that backs an exposed point whose exposure the Evidence library defines on a diary category (config `diary.library_source`) is always in the view, first, with `backs` (the point ids) and its `severity_or_note`; at most `diary.backing_per_point` (3) per point, from that exposure's own window up to `as_of`; they do not count against `max_entries`; the stored `refs` are not changed. (4) The phrase book gives each measure one clause per direction with a strength slot ("clearly fewer doses were taken than usual"), used by the view (`what`, no separate strength) and the code line (one sentence per measure). (5) Check 8: "this has come up before" / "an early observation" only in a sentence that cites an earlier conclusion (`p<k>`); a sentence citing an earlier summary (`s<k>`) has no claim-class point and no claim phrase, and does not cite an `artifact_note` point. (6) Two to six sentences. (7) Part of day comes from each measure's own `opened_at` (`situation.measures[].part_of_day`); the case-level part of day is dropped. (8) Parked: collapsing near-duplicate points, has/have agreement, the word "may" in check 3. |
| U | Text layer, third round | (1) The view's `earlier_summaries` holds only yesterday's day-window summary, and only if that window is notable (the stored notable flag; config `state_memory.view`); none in a version that has an `artifact_note` point; the week and month windows stay in the code layer and in the stored `refs`. Check 10: at most one sentence cites an earlier summary. (2) Check 9: a sentence that cites an entangled bundle must say the items often occur together and that their separate roles cannot be told apart. (3) Prompt rules 11 to 13: never write view ids in the text, use each point's phrase exactly as given, no "drink"/"drank"/"drinking" for fluid intake; a view id in the text is a check 3 failure (reported as such). (4) Fluid-intake clauses read "clearly less fluid was taken than usual" / "clearly more fluid was taken than usual". (5) The cache key is the view hash, the model and every setting that changes what is accepted (effort, retries, length limits, copy window), the prompt texts and `CHECKS_VERSION`. (6) The full run goes in waves, saves each finished version, is resumable from the store, and stops after 40 new versions if more than 45% failed their first attempt or more than 10% of calls ended in a call error. |
| V | Text layer, fourth round (prompt `p-v2`, checks `ck-v4`) | (1) Prompt rule 14: when one sentence cites points of different strengths, use "may be linked to" for the whole sentence, or put them in separate sentences. (2) Two to eight sentences, headline excluded (check 1; prompt). (3) Check 7 is completed by code, not enforced on the model: a missing not-known-yet sentence (citing `n1`) or not-enough-history sentence (citing `h1`) is appended with the phrase book's own sentence (`code_line.not_known_yet`, `code_line.history_short`); the appended sentences carry `appended: true` and the record has `text.appended` (the ids); check 7 triggers no retry. (4) The copy window of check 5 is seven words. (5) A cleanup step runs after parsing and before the checks: it capitalises the start of the headline and of each sentence, lower-cases the first letter of an earlier summary's content after "says", and strips quotes around the view's own phrases; `text` is the cleaned text, `text.raw` the model's own, `text.cleaned` the kinds of change. (6) Every stored text records its prompt version, checks version and model settings; an answer stored under `p-v1` is judged again under the current checks and accepted if it passes (`from_prompt: p-v1`), because `p-v2` only adds rule 14; one that fails, or was made under an unrelated prompt, is not reused. A new fallback never replaces an accepted older answer. |
| W | Text layer, closing round (prompt `p-v3`, checks `ck-v5.1`) | (1) Check 11: a clinical term from the phrase book's `clinical_terms` list (insulin, hypoglycemia / hypoglycaemia, hyperglycemia / hyperglycaemia, infection, diagnosis, diagnosed, ...) may appear in a sentence only if the term appears in the view's own text; "The person has diabetes" is removed from the prompt. (2) Check 12: a claim phrase ("has tended to move together with", "may be linked to") may not be followed by the name of another thing of the view (the whole name or its first three words); the object of a claim is an outcome phrase only, and never "each other" / "one another" (added when a read of the changed versions found "may be linked to each other"; this is why the checks version is `ck-v5.1`). (3) The internal-word list gains `entangled`, `bundle`, `pair` and `points` (check 5 also reads the plural); the view's words follow: `points` -> `things`, `bundles` -> `sets` (item key `bundle` -> `set`), reasons `entangled` -> `often_together` and `co_exposed` -> `present_together`; the stored record keeps its own names. Check 13: no phrase of the view appears more than once in one sentence (a phrase inside a longer one counts once). (4) p-v1 and p-v2 answers are judged again under ck-v5 and kept if they pass (`from_prompt`). PI's `earlier_conclusions` view follows the same rule (no internal word in a key or value). |
| X | Text layer, final touches (checks `ck-v5.2`, prompt unchanged) | Check 14: a claim phrase must be followed by an outcome phrase, not by a comma, "same day", "and", "or" or the end of the sentence. A text token containing an underscore is a check 5 failure. Position phrases ("among the very lowest she has had", the position words of a thing) may repeat in a sentence: they are exempt from check 13. |
| Y | Stage L1, Findings reads PI (the loop, code layer; decided from the L1 run) | (1) PI is read through its retrieval calls with each version's `as_of`, **strictly before it** (a write at the version's own instant is not seen), so a rerun over a database that already holds the write reads what the first run read; the weekly job at 23:59:59 is therefore invisible to an event at exactly that time. (2) `repeat` is filled as before (claim-class factors). `refs.pi_memories` lists, in order: the long-term memory of every usable relationship factor (`memory_id`, `relationship_key`, `version`, `status`, `written_at`, and `view_id` `p<n>` when the view shows it), the open week (`memory_id`, `finding_ids`; omitted when empty), the last `pi.mid_term_recent_weeks` sealed weeks (`memory_id`, `sealed_at`). (3) The view's `earlier_conclusions` are built from the exact versions the record names: `id`, `about` (the ids of the things in the view that carry the relationship), `state`, `text` (the association sentence(s)), `seen_before`, and `situations` only when the memory has one. State words (config `pi_state_words`): candidate = `early`, supported = `repeated`, weakened = `fading`; a retracted memory has no word, so it is listed in the refs but has no view id and no item. (4) A PI status never changes a wording class, mode or group (property test). The open-week entries and sealed weeks are references only in L1. |

---


## 0. How to read this document

This document says **what the Findings Engine is**: its purpose, inputs, rules, outputs and the keys that appear in them. It does not say how to build it. Module layout, function names, data structures and code style are yours to decide.

Where this document is silent, state your assumption in your report. Do not invent behaviour silently.

Values marked **default** live in config, not in code. Thresholds and word lists are **placeholders** unless stated. Items marked **[verify]** come from earlier reports; check them against the real code and database and say where they differ.

It works with, and must be read together with: `intelligence_layer_overview.md` (the three-component picture), `evidence_engine_spec.md` (the labels, flags and ids it consumes) and `pi_spec.md` (the memory it writes to and reads from). The two specs are written together; their contracts are defined once, here and in the PI spec, and must not be changed on one side only.

---

## 1. What the Findings Engine is

> **The Findings Engine turns the evidence for a deviation into a short, hedged, plain-language account of what happened and what was present alongside it, and hands that account to PI to remember.**

It runs in real time. When a deviation item opens and the chain has produced its evidence, Findings writes a first, provisional finding at once, then revises it (as new versions) when more hand-offs or late evidence arrive.

A finding has **two layers**:
- a **structured layer**, set by code: the case, the measures, the factors with their evidence labels and flags, the groups, the wording class of each factor;
- a **text layer**, written by an LLM from a numberless view of the structured layer and the surrounding context: a headline and a few short sentences.

### 1.1 What it is not

- It computes no statistics and shows no numbers. All numbers stay in the evidence store.
- It never changes an evidence label or flag, and never decides a relationship's status (PI does).
- It makes no causal claim. The strongest thing it may say is that two things "have tended to move together" in her history.
- It does not read raw readings or the rulebook files. It reads the evidence, the hand-offs, the diary, the state memory and PI.
- It does not search for new factors. A cause that appears only in the diary can be mentioned as context; it cannot become a relationship.
- It does not reorder or rewrite the rulebook.
- It writes only its own database and calls PI's record interface.

---

## 2. Where it sits

```
State Engine hand-off -> Rulebook packet -> Evidence (event record, completions)
                                                   |
                                          FINDINGS ENGINE   <---- reads: diary, state memory (memory_v2), PI memories (as-of)
                                                   |
                          findings store (versioned)  --record_finding-->  PI (mid-term, then long-term)
                                                                              |
                                                          PI memories are read back by Findings next time (the loop)
```

- **Real time.** A finding is produced when a hand-off arrives. Nothing waits for the end of the day or the week.
- **The loop.** PI memories are an input to Findings, but only as context and as "seen before" information. They never change a label, and Evidence never reads PI.
- **Two kinds of memory are read, with different names.** *State memory* (`memory_v2`) says what happened to her numbers. *Findings memory* (PI) says what has been concluded about why. Findings never restates facts the state memory holds.

---

## 3. Two layers, built and tested separately

| Layer | What it does | LLM? | Stage |
|---|---|---|---|
| **Code layer** | Opens and extends cases, builds the factor table, mode, wording classes, groups, repeat information, history note, the code-written text line, and the PI hand-over | No | F1 |
| **Text layer** | Writes the headline and sentences from the numberless view, checks them, retries once, falls back to the code line | Yes | F2 |

The code layer is complete without the text layer: with the text layer off, every finding carries the code-written line (`text.source = code_line`). The text layer must never change the structured layer.

---

## 4. Time model

| Term | Meaning |
|---|---|
| **Event time** | The `opened_at` of the hand-off being processed. In replay this is "now". |
| **as_of** (of a finding version) | The event time of the hand-off or completion that caused the version. |
| **Reads are as-of.** | Diary entries with a timestamp at or before `as_of`; state memory windows that ended before the local date of `as_of`; PI memories with `written_at` at or before `as_of`; evidence records for the outcome date of the event. Nothing later is read. |
| **No wall clock.** | No field holds the real time of a run, so re-running produces identical records. |

Findings does not decide when the week ends. PI's weekly job does.

---

## 5. Cases

A **case** groups the hand-offs of one situation.

1. **Opening.** A hand-off opens a case if there is no open case it can join. A hand-off whose packet is `deferred` or `unmatched` never opens a case; it joins an open case if one exists, otherwise it is logged and ignored.
2. **Joining.** A hand-off joins the open case if the time since the case's last hand-off is at most `case.gap_hours` (default 6), and the case would not exceed `case.max_span_hours` (default 36). Otherwise it opens a new case.
3. **Id and date.** `case_<opened_at of the first hand-off>`. The case's `local_date` is the local date of that first hand-off, in the patient's timezone. A case can run past midnight; it still counts as one case-day, on its `local_date`.
4. **Versions.** Version 1 is written when the case opens. A new version is written when a hand-off joins, when an evidence completion arrives, and when the case closes with a change. Versions are append-only.
5. **Closing.** A case closes when `gap_hours` have passed since its last hand-off. In replay this is decided when the next event is processed, or at the end of the data.
6. **Provisional.** Every version is `provisional: true` until the case closes; the closing version (or the last version, marked closed) is final.

On the first patient's 287 hand-offs (279 counted, 8 deferred and only recorded), a 6-hour gap gives **116 cases** (at most three start on a day; the longest case spans 28 hours). A 12-hour gap gives 85 cases but chains of up to 60 hours; a 3-hour gap gives 176 cases. The setting is config; the replay reports the case counts.

---

## 6. Inputs

| Input | From | Keys used | Rule |
|---|---|---|---|
| Hand-offs | State Engine | `handoff_id`, `measure`, `direction`, `size`, `trigger`, `opened_at`, `context.last_meal` (label, minutes ago) | |
| Packets | Rulebook Lookup | `matched_rule.rule_id`, `selected[]` (candidate, rank, weight_tier), `status` | Weight tiers are copied for display only |
| Event evidence | Evidence Engine | `evidence_id`, `factors[]` (candidate, relationship_evidence_id, support, flags, event_exposure, event_specific), `overlap`, `not_tested`, `counts` | Labels and flags are used unchanged |
| Completions | Evidence Engine | `evidence_id`, `candidate`, `support`, `result_json` | A completion starts a new version |
| Relationship evidence | Evidence Engine | `relationship_key`, `exposure_id`, `outcome_id`, `support`, `flags` | By id, for the key and phrase only. **No statistic is read into the view.** |
| Diary | Personal Data Store | `category`, `description`, `severity_or_note`, `timestamp` **[verify the names in `context_events`; the source file uses these]** | Entries from the start of the previous local day up to `as_of`; at most `diary.max_entries` (default 6), moderate or worse first, then the most recent |
| State memory | `memory_v2` | the gist headline of: yesterday's day window, the last completed week window, the latest month checkpoint **[verify the field name in the stored gist JSON]** | Headlines only |
| PI memories | PI retrieval (as-of) | long-term memories of the relationships in the factor table; the open week's entries; the last `pi.mid_term_recent_weeks` (default 2) sealed weeks | Text and status only |
| Phrase book | Config (Appendix A) | phrases for exposures, outcomes, windows, positions | Patient-independent |
| Config | | the `findings:` block in section 10 | |

**Not read:** raw readings, statistics, the rulebook CSVs, PI's internal tables.

---

## 7. The code layer

### 7.1 The factor table

For each case version, merge the factors of all its hand-offs. A factor is identified by `candidate` plus `relationship_key` (null for event-level checks).
- **Label and flags** come from the evidence record of the hand-off whose outcome date is latest (they are the same within one date). Flags are the union.
- **Exposure state** is `exposed` if any hand-off's event shows `exposed`; otherwise `not_yet_available` if any shows it; otherwise `not_exposed`; `no_data` stays `no_data`.
- Each factor gets a `factor_id` (`f1`, `f2`, ...) in rank order of the first hand-off. Measures get `m1`, `m2`.
- A factor never appears twice. `rank` and `weight_tier` are copied through and **never affect any rule below**.

### 7.2 Mode

- `relationship`: at least one factor is **usable** (label `supported` or `suggestive`, or an event-level check labelled `supported`) and is `exposed`.
- `descriptive`: otherwise. The finding describes what was unusual and says there is not enough history to link it.

### 7.3 Wording class

Code assigns each factor exactly one wording class. The text layer may use only the language of that class.

| Label | Flags | Exposure | Wording class | What may be said |
|---|---|---|---|---|
| `supported` | none | `exposed` | `asserted` | "has tended to move together with" |
| `supported` | `same_day_unverified` | `exposed` | `asserted_same_day` | the same, and the sentence must say it was **on the same day** |
| `suggestive` | none | `exposed` | `hedged` | "may be linked to" |
| `suggestive` | `same_day_unverified` | `exposed` | `hedged_same_day` | the same, same-day wording required |
| `supported` or `suggestive` | `placebo_fired` | any | `exposure_only` | present, no link |
| `not_supported` | `contrary`, no `placebo_fired` | `exposed` | `contrary_note` | "on days like this her X has tended to be lower" (association only) |
| `not_supported` | otherwise | `exposed` | `exposure_only` | may be said to be present; no link |
| `supported`, `suggestive` | any | `not_exposed` | `not_mentioned` | |
| any | any | `not_yet_available` | `not_known_yet` | listed as "not known yet" |
| `insufficient` (reason `history` or `small_group`) | any | `exposed` | `exposure_only_history` | present; "not enough history yet" |
| `insufficient` (other reasons), any `no_data` | any | any | `not_mentioned` | |
| event-level `percentile_vs_history`, `supported` | | `exposed` | `event_unusual` | how unusual this event was, by position words; no link |
| event-level `shape_check`, `supported` | | | `artifact_note` | "may be a sensor artifact" |
| event-level `shape_check`, `not_yet_available` | | | `not_known_yet` | |
| `presence_check`, `pattern_repeat` | | | `exposure_only` | a fact, no link |

A `supported` or `suggestive` label never makes a stronger sentence than its class allows. A PI status never upgrades a class (section 7.6).

### 7.4 Groups

- **Entangled group.** Usable, exposed factors joined by an `entangled` overlap flag in the evidence form one group (`reason: entangled`). The text must say they often occur together and that their separate roles cannot be told apart.
- **Co-exposed group.** The remaining usable, exposed factors form one group (`reason: co_exposed`) if there are at least two. Members must be described together, never as separate explanations.
- Groups are what stop the finding from reading like a list of independent causes. On the first patient 36% of overlap pairs are entangled, and more than half of the `supported` records are same-day.

### 7.5 Position words and descriptive facts

For every `exposed` factor with a tail percentile (continuous exposures and event-level percentiles), code turns the percentile into **position words** using `findings.position_bands`:

| Side of risk | Percentile band | Words |
|---|---|---|
| risk is the low side (sleep, hydration, steps) | 0 to 5 | among the very lowest she has had |
| | 5 to 25 | low for her |
| risk is the high side (screen time, heart-rate steps) and event percentiles | 95 to 100 | among the very highest she has had |
| | 75 to 95 | high for her |

No percentile or number is shown in text. In descriptive mode these words, with the exposure phrases of the phrase book, are the content of the finding.

### 7.6 Repeat information from PI

For each usable factor with a `relationship_key`, ask PI (as-of) for its long-term memory.
- `pi_status`: the memory's status, or null.
- `seen_before`: `none`, `this_week` (last seen within 7 days), `recent_weeks` (within 28 days) or `earlier`. Bands only.
- This information lets the text say "this has come up before" or call a relationship an "early observation". It **never** changes a wording class: the wording comes from the evidence label of today. A relationship that is `weakened` or `retracted` in PI is described by its class today, with the PI status as context only (a `retracted` memory is not mentioned unless today's label is usable).

### 7.7 History note and "not known yet"

- `history_note`: `enough` if every usable-or-tested factor has a label other than `insufficient(history)`; `enough_for_some` if some do; `not_enough_history_yet` if most factors are `insufficient(history)`.
- `not_known_yet`: plain-words list of the exposures whose state is `not_yet_available` (for example "the day's step total").

### 7.8 The code line

The code layer always builds a text line from the structured layer (templates in Appendix C). It is the text of the finding when the text layer is off, fails its checks twice, or has no model. It uses the same phrases and wording classes.

---

## 8. The text layer

### 8.1 The view (numberless)

Built from the structured layer and the context, with **no digits, dates, times of day, counts, ids of the engine's internal tables or statistics**:
- `situation`: mode (`may_discuss_links` or `describe_only`), the measures (`what`: one clause per direction with its strength, from the phrase book, and the part of day of the measure's own `opened_at`) and the meal context in words;
- `things`: for each factor not classed `not_mentioned`, `not_known_yet` or static: id, `name` (phrase book), `outcome` phrase, `wording` (the wording class, with `exposure_only` shown as `present_only`), position words, bundle id;
- `sets`; `not_known_yet` (`n1`); `history` (`h1`);
- `diary`: id, category, when (that day, the day before, in the days before), part of day, text, `severity_or_note` (the entry's `meta.note`), and for an entry that backs a point, `backs`; entries that back a point come first (the text may contain digits; the model must not repeat them);
- `earlier_summaries`: ids and headlines;
- `earlier_conclusions`: for each relationship, `about` (point ids), its state word (`early`, `repeated`, `fading`), long-term text and the `seen_before` band.

The example below is the earlier illustration; its keys follow the first draft (`case`, `factors`, `class`, `groups`, `state_memory`, `pi`) and are renamed as above.

```json
{
  "case": {
    "mode": "relationship",
    "part_of_day": "evening",
    "measures": [
      {
        "id": "m1",
        "what": "heart rate above her usual",
        "strength": "clearly"
      },
      {
        "id": "m2",
        "what": "glucose above her usual",
        "strength": "clearly"
      }
    ],
    "meal_context": "a festive dinner about an hour earlier"
  },
  "factors": [
    {
      "id": "f1",
      "name": "the size of this meal's rise",
      "class": "event_unusual",
      "position": "among the very highest she has had within the hour or so after dinners"
    },
    {
      "id": "f2",
      "name": "missed doses on the same day or the day before",
      "outcome": "higher dinner peaks",
      "class": "asserted_same_day",
      "group": "g1"
    },
    {
      "id": "f3",
      "name": "short sleep the night before",
      "outcome": "higher dinner peaks",
      "class": "asserted",
      "position": "among the very lowest she has had",
      "group": "g1"
    },
    {
      "id": "f4",
      "name": "a stressed or low-mood period",
      "class": "exposure_only"
    }
  ],
  "groups": [
    {
      "id": "g1",
      "reason": "co_exposed",
      "members": [
        "f2",
        "f3"
      ]
    }
  ],
  "not_known_yet": [
    "the day's step total"
  ],
  "history": "enough_for_some",
  "diary": [
    {
      "id": "d1",
      "category": "life_event",
      "part_of_day": "evening",
      "text": "Quarter-close deadline day, delivered the numbers, largely deskbound, minimal proper meals"
    },
    {
      "id": "d2",
      "category": "social_interaction",
      "part_of_day": "evening",
      "text": "Reflected with husband on the layered month - tired, foggy, aware of slipped walks and medication timing"
    }
  ],
  "state_memory": [
    {
      "id": "s1",
      "window": "yesterday",
      "headline": "Missed multiple medicines during a stressful festival and work day."
    }
  ],
  "pi": []
}
```

### 8.2 The output

```json
{"headline": "one sentence, at most 20 words",
 "sentences": [{"text": "one short sentence", "refs": ["f1", "g1", "d1", "m1", "s1", "p1", "h1"]}]}
```
Two to eight sentences. Each cites at least one id from the view; a bundle id counts as citing all its members. `h1` is the history note and `n1` the not-known-yet list.

### 8.3 Checks (these only)

1. **Structure.** Valid JSON; headline at most 20 words; two to eight sentences; each with at least one ref.
2. **Refs exist.** Every ref is an id in the view.
3. **No digits, dates or times**, and no counting words (one, two, once, twice, first, second, several as a count).
4. **No causal wording.** Stems: caus*, trigger*, led to, result*, due to, because, explains, attributable, driven by, responsible, affect*, impact*, influenc*, contribut*, as a result, thanks to.
5. **No copied diary text** of five or more words, and no internal words (evidence, label, relationship, factor, supported, suggestive, statistic, case, engine, memory, hand-off, group, class, exposure, exposures).
6. **Claim level matches the refs.** A sentence may use "has tended to move together with" only if every relationship factor it cites is `asserted` or `asserted_same_day`; "may be linked to" only if every cited factor is `hedged`, `hedged_same_day`, `asserted` or `asserted_same_day`; neither if it cites any other class. If a cited factor is a `_same_day` class, the sentence must contain "same day". A cited group id counts as citing all its members, and the rule is evaluated on the members.
7. **Required statements.** If `history_note` is `not_enough_history_yet`, one sentence must say there is not enough history and cite `h1`. If `not_known_yet` is not empty, one sentence must say so and cite `n1`. **Completed by code** (amendment V): a missing one is appended from the phrase book, not a failure.
8. **Recurrence wording.** "This has come up before" and "an early observation" appear only in a sentence that cites an earlier conclusion (`p<k>`). A sentence that cites an earlier summary (`s<k>`) cites no claim-class point, uses no claim phrase, and does not cite an `artifact_note` point.

9. **Often-together set.** A sentence that cites a set whose members often occur together says the items often occur together and that their separate roles cannot be told apart.
10. **One summary sentence.** At most one sentence cites an earlier summary.
11. **Clinical terms.** A term of the phrase book's `clinical_terms` list appears only if the view's text has it.
12. **Object of a claim.** A claim phrase is not followed by the name of another thing of the view.
13. **No repeated phrase.** No phrase of the view appears more than once in one sentence (position phrases excepted).
14. **A claim has an outcome.** A claim phrase is followed by an outcome phrase, not by a comma, "same day", "and", "or" or the end of the sentence.

Do not add other checks.

### 8.4 Retry, fallback, caching

- On a failed check, retry once, appending the failed checks to the prompt. If it fails again, store the code line (`text.source = code_line`, `status = code_line_fallback`).
- The structured layer is never changed by the text layer.
- **Cache.** The model output is stored with a hash of the view. Re-running with the same view reuses the stored output, so a replay is repeatable. A refresh flag recomputes.
- Model, reasoning effort, timeout, retries and concurrency are config (section 10). One window per call.

---

## 9. Outputs

### 9.1 The finding record (one per case version)

It holds **no statistics**: evidence is referenced by id. Illustrative example, for the evening case of 2026-09-17 after the glucose hand-off joined (version 2). Only the glucose packet's factors are shown; the heart-rate packet's factors would appear in the same table. The texts are what a model might write, not engine output.

```json
{
  "finding_id": "fnd_case_2026-09-17T21:45_v2",
  "case_id": "case_2026-09-17T21:45",
  "version": 2,
  "provisional": true,
  "closed": false,
  "as_of": "2026-09-17T22:30:00+05:30",
  "local_date": "2026-09-17",
  "handoff_ids": ["handoff_heart_rate_2026-09-17T21:45", "handoff_glucose_2026-09-17T22:30"],
  "evidence_ids": ["ev_handoff_heart_rate_2026-09-17T21:45", "ev_handoff_glucose_2026-09-17T22:30"],
  "completion_ids": [],
  "mode": "relationship",
  "measures": [
    {"measure_id": "m1", "measure": "heart_rate", "direction": "above", "strength": "clearly", "opened_at": "2026-09-17T21:45:00+05:30"},
    {"measure_id": "m2", "measure": "glucose", "direction": "above", "strength": "clearly", "opened_at": "2026-09-17T22:30:00+05:30"}
  ],
  "factors": [
    {"factor_id": "f1", "candidate": "meal_composition", "kind": "event", "relationship_key": null, "label": "supported", "flags": [], "exposure": "exposed", "position": "among the very highest she has had within the hour or so after dinners", "wording_class": "event_unusual", "group": null, "handoff_ids": ["handoff_glucose_2026-09-17T22:30"]},
    {"factor_id": "f2", "candidate": "medication_adherence", "kind": "relationship", "relationship_key": "missed_dose@2d->post_meal_peak:dinner", "label": "supported", "flags": ["same_day_unverified"], "exposure": "exposed", "position": null, "wording_class": "asserted_same_day", "group": "g1", "handoff_ids": ["handoff_glucose_2026-09-17T22:30"]},
    {"factor_id": "f3", "candidate": "sleep", "kind": "relationship", "relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner", "label": "supported", "flags": [], "exposure": "exposed", "position": "among the very lowest she has had", "wording_class": "asserted", "group": "g1", "handoff_ids": ["handoff_glucose_2026-09-17T22:30"]},
    {"factor_id": "f4", "candidate": "stress_mood", "kind": "relationship", "relationship_key": "strained_period@1d->post_meal_peak:dinner", "label": "not_supported", "flags": [], "exposure": "exposed", "position": null, "wording_class": "exposure_only", "group": null, "handoff_ids": ["handoff_glucose_2026-09-17T22:30"]},
    {"factor_id": "f5", "candidate": "activity", "kind": "relationship", "relationship_key": "steps_total@1d->post_meal_peak:dinner", "label": "not_supported", "flags": ["same_day_unverified"], "exposure": "not_yet_available", "position": null, "wording_class": "not_known_yet", "group": null, "handoff_ids": ["handoff_glucose_2026-09-17T22:30"]},
    {"factor_id": "f6", "candidate": "illness_symptoms", "kind": "relationship", "relationship_key": "symptom_entry@3d->post_meal_peak:dinner", "label": "not_supported", "flags": ["contrary", "placebo_fired"], "exposure": "not_exposed", "position": null, "wording_class": "not_mentioned", "group": null, "handoff_ids": ["handoff_glucose_2026-09-17T22:30"]},
    {"factor_id": "f7", "candidate": "alcohol", "kind": "relationship", "relationship_key": "alcohol_entry@1d->post_meal_peak:dinner", "label": "insufficient", "flags": ["small_group"], "exposure": "not_exposed", "position": null, "wording_class": "not_mentioned", "group": null, "handoff_ids": ["handoff_glucose_2026-09-17T22:30"]}
  ],
  "groups": [
    {"group_id": "g1", "reason": "co_exposed", "members": ["f2", "f3"]}
  ],
  "history_note": "enough",
  "not_known_yet": ["the day's step total"],
  "repeat": [
    {"relationship_key": "missed_dose@2d->post_meal_peak:dinner", "pi_status": null, "seen_before": "none"},
    {"relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner", "pi_status": null, "seen_before": "none"}
  ],
  "refs": {"diary": ["d1", "d2"], "state_memory": ["s1"], "pi_memories": []},
  "text": {"headline": "Glucose rose well above her usual after a late festive dinner, on a day with missed doses and a very short night.", "sentences": [{"text": "The rise in the hour or so after this dinner was among the highest she has had after dinners.", "refs": ["f1"]}, {"text": "Short sleep the night before and missed doses on the same day or the day before have each tended to move together with higher dinner peaks in her history, and both were present today.", "refs": ["f3", "f2", "g1"]}, {"text": "The diary describes a deadline day with minimal proper meals.", "refs": ["d1"]}, {"text": "Her heart rate was also clearly above her usual earlier in the evening.", "refs": ["m1"]}], "source": "llm"},
  "checks": {"passed": true, "failed": []},
  "status": "ok"
}
```

Mode, measures, factors, groups and the wording classes come from code. `text` comes from the text layer (or the code line).

### 9.2 Storage

Its own database (suggested name `output/findings_engine.db`). Names are suggestions.

| Table | Key | Holds |
|---|---|---|
| `cases` | `case_id` | `local_date`, `opened_at`, `last_handoff_at`, `closed_at`, `status` |
| `case_handoffs` | `case_id`, `handoff_id` | `joined_at` (the hand-off's `opened_at`) |
| `findings` | `finding_id` (`fnd_<case_id>_v<n>`) | the record in 9.1 as `record_json`; columns for `case_id`, `version`, `as_of`, `mode`, `provisional`, `closed`, `text_source`, `status` |
| `finding_llm` | `finding_id` | `view_hash`, `llm_raw`, `usage_json`, `checks_json` |

No table holds a wall-clock time. Versions are never changed after they are written.

### 9.3 Hand-over to PI

For every new version, call PI's `record_finding(finding)` with the record in 9.1. PI keeps a copy of the structured keys and the text; the findings store remains the version history. The call is idempotent by `finding_id`. If PI is not present (stage F1 and F2), the call is a no-op and PI memories read as empty.

---

## 10. Config (all values are defaults)

```yaml
findings:
  method_version: fe-v0
  case: {gap_hours: 6, max_span_hours: 36}
  diary: {max_entries: 6, start: previous_local_day, order: [severity_moderate_or_worse, most_recent]}
  state_memory: {use: [yesterday_day, last_week, latest_month]}
  pi: {mid_term_recent_weeks: 2, include_open_week: true}
  seen_before_bands: {this_week_days: 7, recent_weeks_days: 28}
  position_bands: {low_side: [[0, 5, "among the very lowest she has had"], [5, 25, "low for her"]],
                   high_side: [[95, 100, "among the very highest she has had"], [75, 95, "high for her"]]}
  strength_words: {clearly: "clearly", far: "far"}
  part_of_day: {night: [0, 5], morning: [5, 12], afternoon: [12, 18], evening: [18, 24]}
  text:
    enabled: true
    model: "openai/gpt-5-mini"
    reasoning_effort: low
    timeout_seconds: 90
    sdk_retries: 0
    retries: 1
    concurrency: 6
    headline_max_words: 20
    sentences: {min: 2, max: 8}
    cache: true
  phrasebook: derived from Appendix A; patient-independent; checked at load
```

Load check: every exposure, outcome, window tag and event-level candidate in the Evidence library has a phrase; every wording class in 7.3 has a template in Appendix C; loading fails with a plain message otherwise.

---

## 11. Key dictionary

### 11.1 Input keys
Hand-off, packet, event evidence and completion keys as in section 6; diary: `category`, `description`, `severity_or_note`, `timestamp`; state memory: `window_id`, `gist_headline`; PI: `memory_id`, `relationship_key`, `status`, `text`, `counters.last_seen`; config: the `findings:` block.

### 11.2 Working keys
`factor_table`, `mode`, `wording_class`, `group`, `position_words`, `part_of_day`, `view`, `view_hash`, `checks`.

### 11.3 Output keys
Finding record: `finding_id`, `case_id`, `version`, `provisional`, `closed`, `as_of`, `local_date`, `handoff_ids`, `evidence_ids`, `completion_ids`, `mode`, `measures` (`measure_id`, `measure`, `direction`, `strength`, `opened_at`), `factors` (`factor_id`, `candidate`, `kind`, `relationship_key`, `label`, `flags`, `exposure`, `position`, `wording_class`, `group`, `handoff_ids`, `insufficient_reason`), `groups` (`group_id`, `reason`, `members`), `history_note`, `not_known_yet`, `repeat`, `refs`, `text` (`headline`, `sentences`, `source`), `checks`, `status`.

---

## 12. Worked examples

### A. Relationship mode: Meera, 2026-09-17, evening

The first hand-off of the evening is the heart-rate item at 21:45; the glucose item at 22:30 joins it, so the case is `case_2026-09-17T21:45` (the morning's heart-rate and resting-heart-rate hand-offs form an earlier case; the gap between them is more than six hours). The record in 9.1 is version 2.

- **Mode** is `relationship`: the meal check is `supported` and `exposed`, and so are the missed-dose and sleep relationships.
- **Wording.** The meal check is `event_unusual`. Sleep is `asserted`. Missed doses are `asserted_same_day` (the 2-day window includes the outcome day), so a sentence about them must say "same day"; the phrase book gives "on the same day or the day before". Mood is `exposure_only`. Steps are `not_known_yet`. Illness carries `contrary` and `placebo_fired` and was not present, so it is `not_mentioned`. Alcohol is `insufficient` and absent.
- **Group.** Sleep and missed doses are both usable and exposed and are not entangled, so they form a `co_exposed` group: the text describes them together.
- **PI** is empty at this point, so `repeat` shows `seen_before: none`.
- **Text.** The first sentence is about the meal rise, the second about the group, the third about the diary, and the last about the heart rate. No number, date or time appears; the strength of the heart-rate deviation is "clearly".

### B. Descriptive mode: Meera, 2025-11-18 (hospitalization), illustrative

Before about 10 December the evidence has no tested relationships, so every relationship factor is `insufficient(history)`. The case `case_2025-11-18T08:17` holds the blood pressure hand-off at 08:17 and the glucose hand-offs at 11:15 and 15:15. The factors and exposure states below follow the Stage 2b evidence report; I have not seen these exact records, so the record is illustrative.

```json
{
  "finding_id": "fnd_case_2025-11-18T08:17_v3",
  "case_id": "case_2025-11-18T08:17",
  "version": 3,
  "provisional": true,
  "closed": false,
  "as_of": "2025-11-18T15:15:00+05:30",
  "local_date": "2025-11-18",
  "handoff_ids": ["handoff_blood_pressure_2025-11-18T08:17", "handoff_glucose_2025-11-18T11:15", "handoff_glucose_2025-11-18T15:15"],
  "mode": "descriptive",
  "measures": [
    {"measure_id": "m1", "measure": "blood_pressure", "direction": "above", "strength": "clearly"},
    {"measure_id": "m2", "measure": "glucose", "direction": "above", "strength": "clearly"}
  ],
  "factors": [
    {"factor_id": "f1", "candidate": "sleep", "kind": "relationship", "relationship_key": "sleep_hours@prev_night->systolic_reading", "label": "insufficient", "insufficient_reason": "history", "exposure": "exposed", "position": "among the very lowest she has had", "wording_class": "exposure_only_history"},
    {"factor_id": "f2", "candidate": "medication_adherence", "kind": "relationship", "relationship_key": "missed_dose@2d->systolic_reading", "label": "insufficient", "insufficient_reason": "history", "exposure": "exposed", "position": null, "wording_class": "exposure_only_history"},
    {"factor_id": "f3", "candidate": "stress_mood", "kind": "relationship", "relationship_key": "strained_period@1d->non_meal_mean", "label": "insufficient", "insufficient_reason": "history", "exposure": "exposed", "position": null, "wording_class": "exposure_only_history"},
    {"factor_id": "f4", "candidate": "illness_symptoms", "kind": "relationship", "relationship_key": "symptom_entry@3d->non_meal_mean", "label": "insufficient", "insufficient_reason": "history", "exposure": "exposed", "position": null, "wording_class": "exposure_only_history"},
    {"factor_id": "f5", "candidate": "meal_composition", "kind": "event", "relationship_key": null, "label": "supported", "exposure": "exposed", "position": "among the very highest she has had within the hour or so after lunches", "wording_class": "event_unusual", "handoff_ids": ["handoff_glucose_2025-11-18T15:15"]}
  ],
  "groups": [],
  "history_note": "not_enough_history_yet",
  "not_known_yet": ["the day's step total"],
  "refs": {"diary": ["d1", "d2"], "state_memory": [], "pi_memories": []},
  "text": {"headline": "A family emergency, with very little sleep and missed doses, while glucose and blood pressure ran above her usual.", "sentences": [{"text": "The diary says her father was taken to hospital overnight.", "refs": ["d1"]}, {"text": "Her sleep the night before was among the very lowest she has had, doses were missed, and her mood was strained.", "refs": ["f1", "f2", "f3"]}, {"text": "There is not enough history yet to say what usually goes with a rise in glucose or blood pressure for her, so no link is claimed.", "refs": ["h1"]}, {"text": "The rise in glucose after her meal that afternoon was among the highest she has had after lunches.", "refs": ["f5"]}, {"text": "An earlier diary note about symptoms is about her father, not about her.", "refs": ["d2", "f4"]}], "source": "llm"},
  "checks": {"passed": true, "failed": []},
  "status": "ok"
}
```

- **Mode** is `descriptive`: no relationship factor is usable (all four are `insufficient(history)`); the meal percentile (`event_unusual`) does not make a case `relationship` mode but its statement is added. The content is: the diary line about the hospitalization, the position words for sleep, the missed doses and the strained mood, the meal line, and the plain statement that there is not enough history yet. (The real 15:15 glucose hand-off of 2025-11-18 is a lunch, with `meal_composition` supported and exposed.)
- **A trap the diary text avoids.** The evidence counts a diary entry of category *symptom* as an illness exposure. The entry on 16 November ("Noticed father unusually tired and low-appetite at family lunch") is about her father. The text layer reads the entry and says so; it must not describe her as ill. The category alone cannot tell the difference. This is a known limit (section 14).

---

## 13. Properties that must hold

1. **Code layer deterministic.** The same inputs and config give the same structured layer, case ids, version numbers and factor ids.
2. **Text layer repeatable.** The same view gives the same stored text (cache).
3. **No look-ahead.** Every read is as-of the finding's `as_of`.
4. **No statistics and no digits in any text.** Numbers appear nowhere in a finding record.
5. **Labels and flags are never altered.** A finding's label and flags equal the evidence record's.
6. **Wording follows the class.** No sentence is stronger than the weakest class it cites; same-day classes say "same day".
7. **Weights and PI status never change a wording class.**
8. **Groups are described together.**
9. **Versions are append-only,** and a version never changes after it is written.
10. **Every finding has a text.** If the text layer fails, the code line is stored; no case is left without text.
11. **Idempotent.** Re-running a hand-off or completion produces no duplicate case, version or PI record.
12. **Read-only toward other components,** except the call to PI's `record_finding`.
13. **No LLM in the code layer.**
14. **Generic.** No stream, measure, medicine or patient name in the engine; phrases live in config. A second patient runs with config changes only.
15. **Load check.** Loading fails with a plain message if a phrase, a wording-class template or a position band is missing.

---

## 14. Limits, assumptions and open items

| Item | What I assumed | Where it matters |
|---|---|---|
| Placeholders | The case gap, the position bands, the word lists and the check rules are placeholders. | Tune only against reviewed output. |
| Association, not mechanism | A `supported` label means "moved together in her history". On the first patient most `supported` links sit on story days, and the control that tests this depended on how story days were defined. | Wording is deliberately weak. |
| Same-day links | More than half of `supported` records are same-day. | Text says "same day" and never "before". |
| Entangled factors | 36% of overlap pairs are entangled. | Findings reports a group, not independent causes. |
| Early history | Before about 10 December no relationship is tested. | Findings uses descriptive mode for those weeks. |
| Whose symptom | The diary category does not say whose symptom it is. The Evidence Engine counts a symptom note about her father as an illness exposure. | The text layer must read the entry; a structured `subject` field upstream is the proper fix. |
| Diary severity | Ordering diary entries by severity depends on severity words that may not exist in a patient's diary. | Fallback: most recent first. |
| Case boundaries | A 6-hour gap splits a long crisis into several cases. | Case counts are reported in the replay. |
| LLM variability | The text can differ between model versions. | The cache makes a replay repeatable. |
| Heart rate | 43% of hand-offs are heart rate, and its activity link is weak in the evidence. | Many heart-rate findings will be descriptive. |
| One text per case version | No per-measure text. | A long case has one account. |

---

### 14.1 Parked for stage L (decided after the PI P2 prompt review; nothing here is changed yet: Findings prompt p-v3 and checks ck-v5.2 stay as they are)

1. Prompt rule 1: drop "recently" and "earlier" from the words offered ("Use 'that day', 'recently', 'earlier'"); they are time-relative and a stored text is read later.
2. Prompt rules 3 and 6: make rule 6 win over rule 3 for history. A `present_only_history` thing says "there is not enough history yet" once, in one sentence that cites `h1`, not once per thing.
3. Retry addendum: remove the word "class" ("no statement stronger than the class allows"); it is an internal word the prompt itself forbids.
4. Prompt: state the checks that exist but are not in it: clinical terms only if the view has them (check 11), no view phrase twice in a sentence (check 13), a claim phrase is followed by an outcome, never by another thing (checks 12 and 14), and no word with an underscore.
5. View: collapse near-duplicate things (the same exposure phrase listed several times from different relationships, for example three "short sleep the night before" things).
6. View: remove counting words from the earlier summaries it carries (for example "two medicines were missed"), since rule 1 forbids counting.

## 15. Out of scope

Statistics and labels (Evidence), statuses and memory (PI), reordering or rewriting the rulebook, discovery of new factors, the Narrative Layer, embeddings, and any user-facing formatting.

## 16. Glossary

| Term | Meaning |
|---|---|
| Case | The hand-offs of one situation, grouped by time |
| Version | One state of a finding for a case; a new version is written when more arrives |
| Factor | One item checked for an event, with its evidence label, flags and exposure |
| Usable factor | A factor labelled `supported` or `suggestive` (or a supported event-level check) |
| Wording class | The kind of sentence a factor allows |
| Group | Factors that must be described together |
| Descriptive mode | A finding that says what was unusual, with no link claimed, because there is not enough history |
| Code line | The text built from the structured layer, used when the text layer is off or fails |
| View | The numberless input given to the text layer |
| State memory / findings memory | `memory_v2` (what happened to her numbers) and PI (what was concluded about why) |

---

## Appendix A. Phrase book (patient-independent; the build drafts the full table for review)

Phrases are noun phrases with an optional `{window}` slot filled from the window table. A relationship is described as "<exposure phrase> and <outcome phrase>".

### A.1 Exposures

| Exposure | Phrase |
|---|---|
| `missed_dose` | missed doses {window} |
| `sleep_hours` | short sleep {window} |
| `strained_period` | a stressed or low-mood period {window} |
| `steps_total` | low activity {window} |
| `steps_window_hourly` | more activity in the hour before |
| `high_steps_day` | a very active day |
| `symptom_entry` | a symptom noted in the diary {window} |
| `alcohol_entry` | alcohol noted in the diary {window} |
| `environment_entry` | a weather or environment note {window} |
| `hydration_total` | low fluid intake {window} |
| `screen_hours` | long screen time {window} |
| `late_meal` | a late meal |
| `late_prior_dinner` | a late dinner the evening before |
| `non_home_day` | a day away from home |
| `prior_day_glucose_mean` | higher glucose the day before |
| `clinic_reading` | a reading taken at a clinic |

### A.2 Outcomes

| Outcome | Phrase |
|---|---|
| `post_meal_peak` | higher glucose peaks after {kind} (scope: the meal kind, for example "higher glucose peaks after dinner") |
| `non_meal_mean` | higher glucose between meals |
| `day_min_glucose` | lower lowest-glucose of the day |
| `hr_hour_mean` | higher heart rate in that hour |
| `hr_day_mean` | higher heart rate over the day |
| `resting_hr_day` | a higher resting heart rate |
| `sleep_hours_night` | shorter sleep that night |
| `missed_doses_day` | more missed doses that day |
| `systolic_reading` | higher blood pressure readings |
| `fluid_intake_day` | lower fluid intake that day |

### A.3 Windows

The window phrase for a window that includes the outcome's own date always contains the words "same day", because the wording check requires them for same-day classes.

| Window tag | Phrase |
|---|---|
| `same_day`, `1d` | on the same day |
| `2d` | on the same day or the day before |
| `3d` | on the same day or in the days before |
| `prev_night` | the night before |
| `prev_day` | the day before |
| `prev_evening` | the evening before |
| `60m` | in the hour before |
| `720m` | in the hours before |
| `at_open` | at that reading |
| `7d` | in the week before |

### A.4 Event-level candidates

`meal_composition`: "the size of this meal's rise". `meal_skipped_or_delayed`: "the time since the last meal". `sensor_artifact`: "a possible sensor artifact". `dawn_effect`: "an early-morning rise". `regimen_factors`: "which medicine is missed most". `other_medications`: "other medicines she takes". `thyroid_status`: "her thyroid medicine". `hypoglycemic_agent`: "insulin or a similar medicine".

---

## Appendix B. Prompt for the text layer

**System prompt** (prompt version `p-v3`; `p-v2` called the view's items points and bundles and opened with "The person has diabetes"; `p-v1` lacked rule 14)

```
You write a short plain-language account of one situation in a person's health record.

You receive a VIEW: what happened (measures that were off her usual), the things that were present with the kind of statement each allows, sets of things that must be described together, what is not known yet, whether there is enough history, diary entries, earlier summaries of her numbers, and earlier conclusions about her. All numbers were removed on purpose.

Write:
1. headline: one sentence, at most 20 words.
2. sentences: two to eight short sentences. Each sentence lists the ids of the view items it relies on. A set id counts as citing all the things in that set.

RULES. Follow all of them.
1. Write no digits, dates or times, and do not count ("once", "twice", "first", "second", "one", "two"). Use "that day", "recently", "earlier".
2. Use only what is in the VIEW. Do not invent causes, places, settings or details.
3. Each thing has a wording. Say only what its wording allows:
   - asserted: "has tended to move together with"
   - asserted_same_day: the same, and the sentence must contain "same day"
   - hedged, hedged_same_day: "may be linked to" (and "same day" for the second)
   - present_only, present_only_history: say it was present, with no link. For present_only_history, add that there is not enough history yet.
   - event_unusual: say how unusual this event was, using the position words given
   - artifact_note: "may be a sensor artifact"
   - contrary_note: say that on days with that thing the outcome has tended to be lower
4. Never write that something caused, triggered, explains, affects or led to anything.
5. Things in the same set must be described together in one sentence and cite the set id. For an often_together set, say they often occur together and their separate roles cannot be told apart.
6. If the history note says there is not enough history, say so in one sentence, cite "h1", and claim no link. If something is not known yet, say so and cite "n1".
7. Describe a diary entry only as it describes itself. Paraphrase; do not copy five or more words. Do not repeat numbers from it. If its note says it concerns someone else, say so, and do not describe her as unwell or as having a symptom because of it. An entry with "backs" is the entry behind the things it lists.
8. Earlier conclusions (the p items) may be mentioned as "this has come up before" or "an early observation", only in a sentence that cites that item. They never make a statement stronger than the thing's wording. Earlier summaries (the s items) are described as "an earlier summary says ..."; never say "this has come up before" or "an early observation" about them, never combine one with a claim about a thing in the same sentence, never cite one in a sentence about an artifact_note thing, and cite earlier summaries in at most one sentence.
9. Do not give advice, diagnoses or predictions. Do not use the words: evidence, label, relationship, factor, supported, suggestive, statistic, case, engine, memory, hand-off, group, class, exposure, exposures, entangled, bundle, pair, points.
10. Refer to the person with "she" and "her".
11. Never write view ids (f1, g1, m1, d1, s1, p1, h1, n1) in the text of a sentence or the headline; they go only in refs.
12. Use each thing's phrase exactly as given, including its window phrase; do not shorten or merge phrases.
13. Do not use "drink", "drank" or "drinking" for fluid intake.
14. When one sentence cites things of different strengths, use "may be linked to" for the whole sentence, or put them in separate sentences.

Return only JSON: {"headline": "...", "sentences": [{"text": "...", "refs": ["f1"]}]}
```

**User template**

```
VIEW:
{view_json}
```

**Retry addendum (appended once):**
```
Your previous answer failed these checks: {failed_checks}. Rewrite it using only the VIEW, with no digits or dates, no causal words, and no statement stronger than the class allows.
```

---

## Appendix C. Code-line templates

One template per mode. Slots are filled from the structured layer and the phrase book; no numbers appear.

- **Relationship mode:** "<Measures in words> <strength> her usual. Present: <exposed usable factor phrases>. <For each asserted class: '<phrase> has tended to move together with <outcome phrase> in her history.' (add 'on the same day' for same-day classes) >. <If not-known-yet: 'Not known yet: <list>.'>"
- **Descriptive mode:** "<Measures in words> <strength> her usual. Present: <exposed factor phrases with position words>. There is not enough history yet to say what usually goes with this."
- **Event-level only:** "<Measures in words> <strength> her usual. <Event-level statement>."

Example (relationship mode): "Heart rate and glucose were clearly above her usual. Present: short sleep the night before, missed doses on the same day or the day before. Short sleep the night before has tended to move together with higher dinner peaks in her history. Missed doses on the same day or the day before have tended to move together with higher dinner peaks in her history. Not known yet: the day's step total."

The templates need only the verb agreement ("has" or "have") to be taken from the phrase; this is cosmetic.