# PI (Findings Memory): Definition Spec

## Amendments (master copy; decided after the Step 1 review)

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
| 41 | Section 15 rewritten after P1 | The row "Few promotions expected" is replaced (see section 15): 26 of 29 memories reach `supported` because memories exist only for relationships that findings used, the Evidence labels already persist for months and 15 were created `supported` by back-fill, so the status reports persistence of the Evidence label and is not independent confirmation. Known limit added: the one built formula (steps in the previous hour to heart rate in that hour) was weakened and retracted because the Evidence ordering rule excludes same-hour steps; Evidence v1.1 (a same-hour variant) is parked. |
| 42 | Text layer, stage P2, first design (prompt `pp-v1`, checks `pck-v1`; superseded by 43) | The model text is stored beside the version (`pi_text`, `pi_llm`), never in it; a P1 `--rebuild` keeps those tables. The Appendix A prompt uses the view's words (`link`, `state`, `early` / `repeated` / `fading`), drops "The person has diabetes", and adds: phrases used exactly as given, no field names or underscore words, the outcome (never the other thing) after a claim phrase, no "drink". The checks of 8.4 become: 1 structure (1 to 3 sentences, at most 60 words), 2 digits, dates, times and counting words, 3 causal words, 4 internal words (the shared list including entangled, bundle, pair, points, plus `status`) and underscore tokens, 5 the wording the state allows **and nothing stronger** (early: no "repeatedly"; repeated: no "may be linked", no "early observation"; fading: no "repeatedly", no "early observation"), `same day` for a same-day-only memory, 6 no other relationship's exposure or outcome phrase (phrases that are part of the memory's own are not tested), 7 clinical terms only if the view has them, 8 no phrase of the link twice in a sentence, 9 a claim phrase is followed by the outcome, never by the exposure, a comma, "same day", "and" or "or". Cleanup before the checks: capitalise, strip quotes around the link's phrases; raw and cleaned text are stored. After two failures the previous note is kept **only if it still passes the checks for the current state** (a note that says "early" is not kept for a memory that is now repeated), else the code text. A retracted memory takes the code text and never goes to a model. Regeneration (every `regenerate_every_weeks` from the creation week) rewrites without the previous note. In the sample the previous note is the previous version's code text; the full run will chain model texts. |
| 43 | Text layer redesigned (prompt `pp-v2`, checks `pck-v2` then `pck-v3`; supersedes 42) | The long-term note has two parts: the association (code text, never written or edited by the model) and an optional situations line (one sentence of at most 25 words in the frame "In the cases noted, the situations included ...", written from the mid-term entries that cite the relationship: this week's plus the earlier ones the previous line was built from, at most six). Reason: the P2 sample showed that a model rewrite of a one-sentence association adds nothing (it restated the code text) and let "this week" into a stored note that is false once read later. Checks: the Findings checks that apply (digits, dates, counting words, causal words, internal words and underscore tokens, clinical terms in the entries, repeated phrases) plus time-relative words, no claim words (moved together, linked, tended), no association or other relationship's phrase, one frame sentence, a stem-overlap check against the entries (a stray word or two tolerated) and no names. One retry, then the line is dropped (null) and the association stays. A retracted memory has no model call; regeneration rewrites the line without the previous line. The model result is stored beside the version (`pi_text`), never in it. |
| 44 | Situations line: source and prompt changed (prompt `pp-v3`, checks `pck-v4`; supersedes the source and prompt of 43) | The situations line is built only from sentences of the mid-term entries whose refs (read from the Findings database by `finding_id`, read only) cite only diary items; sentences that cite a factor, a measure, a history or not-known-yet note, an earlier summary or conclusion, or any mix, are skipped; at most six, most recent first; none means no call and a null line. Reason: Findings' sentences mix measures, factors and diary context, so the model listed factors and measures as situations ("short sleep", "missed doses"); the prompt now also defines what a situation is and is not, allows null as a good answer, caps the list at four situations and bans words not in the sentences. Checks `pck-v4` change word lists only: `recent`, `recently`, `earlier`, `previous`, `prior` join the time-relative words, and `unknown`, `unspecified`, `unclear` are banned (check 4); the rest is `pck-v3` (phrase-level repeat check 8, softer overlap check 9). Status `no_entries` is renamed `no_diary_sentences`. |
| 45 | Situations line tightened (prompt `pp-v4`, checks `pck-v5`) | The sample under `pp-v3` listed feelings and habits as situations ("felt relieved", "stayed up late") and broke the grammar after the frame ("included spent an evening ..."). `pp-v4` adds a rule: list noun phrases only (an event, outing, occasion, activity or piece of news), no verbs and no past tense, never feelings, states or habits. `pck-v5` bans, in check 4, felt, feel, feeling, proud, relieved, tired, stressed, anxious, happy, sad, guilty, drained, exhausted and "stayed up". No other change; P2 is not tuned further. |
| 46 | Retrieval reads for the loop (stage L1) | `PiReader(strict=True)` returns only what was written strictly before `as_of` (the loop's reader); the default reader keeps "at or before". Reason: a version's entry is stamped with its own `as_of`, and the weekly job with the end of the week, so an inclusive read depends on whether that write already exists; the loop must read the same on a first run and on a rerun. `PiStore.long_version(memory_id, version)` reads one stored version by id (the version a Findings record names in `refs.pi_memories`). The loop writes only its own databases (`output/findings_loop.db`, `output/pi_loop.db`); its PI tables are identical to a P1 code-only replay of the same Findings versions. |
| 47 | Situations line, check 11 (checks `pck-v6`, prompt `pp-v4` unchanged) | The `pp-v4` sample produced items such as "an evening" and "a change". `pck-v6` adds check 11: an item of the list that is only a generic word (change, evening, day, night, morning, afternoon, time, thing) fails; after the one retry the line is dropped to null. |
| 48 | The loop with the models (stage L2) | The loop writes each version into PI's open week at once with the Findings code line and puts the final text into the entry at the week's barrier (`replace_entry_text`: only the text changes, never in a sealed week), so the structured reads of later versions are the same as in L1. Barrier order per week: the Findings texts of the week's versions (concurrency 6), the entry texts, the weekly job, then the situations lines of the memory versions the job wrote (diary-only sentences of the week's entries and the previous line; the situations line is stored in the overlay `pi_text` beside the version). A Findings view shows an earlier conclusion's situations line as the list only, without its frame. `PiStore.long_written_at`, `text_of`, `situations_line`, `update_entry_text` are the new reads and the one text update. |
| 32 | The Evidence library is an input | Section 5 gains: **Evidence library** (config path), read only: for `same_day_only` (the pair's ordering) and the phrase-book load check. |
| 34 | `7d` window | Added to the shared phrase book. |
| P | Phrase book edits | As in the Findings Amendments (row P). |
| Q | Items not named | The Step 1 proposals are accepted as written. |

---


## 0. How to read this document

This document says **what PI is**: its purpose, inputs, rules, outputs and the keys that appear in them. It does not say how to build it. Module layout, function names, data structures and code style are yours to decide.

Where this document is silent, state your assumption in your report. Do not invent behaviour silently.

Values marked **default** live in config, not in code. Thresholds, week rules and word lists are **placeholders** unless stated. Items marked **[verify]** are assumptions to check against the real code and database.

Read it together with `intelligence_layer_overview.md`, `findings_engine_spec.md` (the findings PI receives and the retrieval it serves) and `evidence_engine_spec.md` (the labels PI reads by id). The Findings Engine and PI specs were written together; their contracts are defined once and must not be changed on one side only.

---

## 1. What PI is

> **PI keeps the findings memory: what the system has concluded about this patient, week by week and relationship by relationship. In V0 it creates, updates and retrieves memories. It does nothing else.**

There are two kinds of memory:
- **Mid-term memory**: the findings of one calendar week, accumulated as they arrive.
- **Long-term memory**: one memory per relationship (an exposure paired with an outcome, as in the Evidence Engine), carrying a status and a short text. It is updated once a week by an LLM that reads the week's mid-term memory.

PI is in a loop with the Findings Engine: every finding is recorded into PI, and PI's memories are read back by Findings the next time.

### 1.1 What it is not

- It does not reorder, add to, or rewrite the rulebook. (That is the later "personalised rulebook" step; it is not part of V0.)
- It computes no statistics. It reads the **labels** the Evidence Engine already assigned, by id, to decide statuses.
- Its LLM writes wording only. It sees no numbers and decides no status.
- It never feeds back into the Evidence Engine. Evidence does not read PI.
- It reads no raw data, no diary and no state memory.
- It does not discover new relationships. A relationship gets a memory only if the rulebook and the Evidence Engine already test it and a finding used it.
- It is not a substitute for the state memory (`memory_v2`), which holds what happened to her numbers. PI holds what was concluded about why, and never restates the state memory's facts.

---

## 2. Where it sits

```
Evidence Engine --labels by id--> PI (code reads them for statuses)
Findings Engine --record_finding--> PI mid-term memory (open week) --week end--> sealed
                                          |                                      |
                                          +---- weekly job ----> long-term memory (status by code, wording by LLM)
                                          |
Findings Engine <------ retrieval (as-of) ---- PI
```

- **Single place for beliefs.** Nothing else keeps its own copy of what the system believes about her.
- **Only Findings writes findings into PI.** PI's own writes are the weekly job.
- **Real-time reads, weekly writes.** Findings can read the current week's entries as they arrive. Long-term memories change once a week.

---

## 3. Two layers, built and tested separately

| Layer | What it does | LLM? | Stage |
|---|---|---|---|
| **Code layer** | Stores mid-term entries, seals weeks, builds long-term memories, counts, week labels, status transitions, retrieval as-of, and a code-written text for each long-term memory | No | P1 |
| **Text layer** | Writes the long-term wording each week from a numberless view, checks it, falls back to the code text | Yes | P2 |

With the text layer off, every long-term memory carries the code-written text (`text.source = code_text`).

---

## 4. Time model

| Term | Meaning |
|---|---|
| **Replay clock** | "Now". Every PI write is stamped `written_at` on this clock. There is no wall clock in any record. |
| **Calendar week** | Monday 00:00 to Sunday 23:59:59 in the patient's timezone (config); named by ISO week, for example `2026-W38`. |
| **Weekly job** | Runs at the week's end, on the replay clock, before any event after that time is processed. |
| **As-of read** | Every retrieval takes a time and returns only what was written at or before it. Memories are append-only versions, so a read can reconstruct any past moment. |
| **Which week an entry belongs to** | The week that contains the finding version's `as_of`, not its `local_date`. A late version of a case from a sealed week lands in the next open week; the entry still carries its `local_date`. |

---

## 5. Inputs

| Input | From | Rule |
|---|---|---|
| `record_finding(finding)` | Findings Engine | The finding record of `findings_engine_spec.md` 9.1: case, version, mode, factors (with relationship keys, labels, flags, exposure, wording class), text, ids. Idempotent by `finding_id`. |
| Daily labels | Evidence store (read-only, by id) | `support` and `flags` of the relationship's records for each day of the week. The numbers in those records are never copied or shown. |
| Phrase book | Config (`findings_engine_spec.md` Appendix A) | Shared, so a relationship is described the same way by Findings and PI |
| Config | | the `pi:` block in section 10 |

**Not read:** raw readings, the diary, state memory, the rulebook CSVs, Evidence statistics.

---

## 6. The memories

### 6.1 Mid-term memory (one per calendar week)

- `open` while the week runs; `sealed` at the week's end. A sealed memory never changes.
- Its **entries** are the findings of the week: for each case, the latest version received so far. A new version of a case adds a new entry version (append-only; the latest wins in reads).
- It holds, for each entry: the case, `local_date`, mode, the relationship keys of the usable factors, and the headline and sentences. It holds no statistics and no copy of the evidence.
- It also lists the week's `case_days` (distinct local dates with a case) and the `relationship_keys_touched`.

### 6.2 Long-term memory (one per relationship)

- Created at the first weekly job after the relationship appears as a **usable factor** (label `supported` or `suggestive`) in any finding, exposed or not.
- Event-level checks (such as the meal percentile) have no relationship key and no long-term memory in V0.
- Fields: `relationship_key`, `status`, `status_since`, `same_day_only`, `story_coupling` (always `unknown` in V0; reserved for a later control), `weekly_labels`, `counters`, `flags_seen`, `evidence_refs`, `finding_ids`, `text`, `text_version`, `version`, `written_at`.
- `text` is an object with two parts (section 8): `sentences` (the association, always the code text, `source: code_text`) and `situations` (one sentence written by the model, or null) with the finding ids of the entries it was built from. P1 wrote the association only.
- `same_day_only` is true if the relationship's pair is marked `same_day_unverified` in the Evidence library (Appendix A there). Its text must say "same day".
- **Counters are bookkeeping, not statistics**: `case_days` (distinct local dates on which the relationship was a usable factor in a case), `exposed_case_days` (those where it was exposed), `first_seen`, `last_seen`, `weeks_seen`. A date counts once, however many cases or versions it has.
- A memory is never edited in place. Each weekly change writes a new version.

### 6.3 Status (decided by code)

Statuses: `candidate`, `supported`, `weakened`, `retracted`. They describe what is believed about the relationship over time, not one day's label. A status is a statement about **association in her history**, never a mechanism.

**Week label.** For each calendar week, from the seven daily labels in the Evidence store (a day with no record counts as `insufficient`):
- `supported` if at least 5 of the 7 days are `supported`;
- else `suggestive` if at least 5 days are `supported` or `suggestive`;
- else `insufficient` if at least 5 days are `insufficient`;
- else `not_supported`.

**Transitions** (defaults, config):

| From | To | Rule |
|---|---|---|
| (new) | `candidate` | on creation, before any back-fill |
| `candidate` | `supported` | week label `supported` for 2 consecutive weeks, and the flag `placebo_fired` on fewer than half of the days of those weeks |
| `supported` | `weakened` | week label `not_supported` for 2 consecutive weeks |
| `weakened` | `supported` | week label `supported` for 2 consecutive weeks |
| `weakened` | `retracted` | `not_supported` for 6 further weeks, or the flag `contrary` on at least 5 days a week for 4 consecutive weeks |
| `retracted` | `candidate` | week label `supported` for 2 consecutive weeks |
| any | unchanged | `suggestive` and `insufficient` weeks neither promote nor demote and do not reset a count |

**Back-fill on creation.** When a memory is created, run these transitions over the relationship's earlier weekly labels (from the first week it was tested), as-of the creation time, so a relationship that has been supported for weeks is not shown as brand new. The back-filled labels are stored in `weekly_labels`. Config `backfill_on_create` (default true).

Example timeline (illustrative):

| Week | Daily labels in the week | Week label | Status at the end of the week | Why |
|---|---|---|---|---|
| W38 | supported on 6 of 7 days | supported | candidate | a new memory; one supported week is not enough |
| W39 | supported on 5 of 7 days | supported | **supported** | two supported weeks in a row |
| W40 | suggestive on most days | suggestive | supported | a suggestive week neither promotes nor demotes |
| W41 | not supported on 5 of 7 days | not_supported | supported | one not-supported week; the count starts |
| W42 | not supported on 6 of 7 days | not_supported | **weakened** | two not-supported weeks in a row |
| W43 to W48 | not supported | not_supported | weakened | six further not-supported weeks are needed |
| W48 | not supported | not_supported | **retracted** | six further not-supported weeks (or four weeks with the flag `contrary`) |

---

## 7. The weekly job

Runs once per calendar week at its end, in this order. Each step is deterministic except step 6.

1. **Seal** the open mid-term memory (an empty one is still sealed).
2. **Week labels** for every relationship that already has a long-term memory.
3. **Create** long-term memories for relationships that appeared as usable factors in the week and have none (with back-fill).
4. **Counters** from the week's entries.
5. **Status transitions** (6.3).
6. **Wording update** (section 8) for each relationship that was touched this week, whose status changed, that was just created, or that is due for regeneration.
7. **Validate and write** new versions (append-only). Relationships that need no change are not rewritten.
8. **Run record**: counts of memories created, statuses changed, texts updated, texts kept after a failed check, and LLM usage.

---

## 8. The text layer (long-term note)

A long-term note has **two parts**. The **association** (one or two sentences: the status wording, "same day", has/have agreement, "This is an early observation." for a candidate) is **written by code**, exactly the code text of 8.5; the model never writes or edits it. The **situations line** is optional and is the only thing the model writes, from the mid-term entries. A memory never loses its association.

*Why (amendment 43):* a model rewrite of a one-sentence association adds nothing, and it let "this week" into a stored note that is read later.

### 8.1 The view of the situations line (numberless; source: diary-only sentences)

- `link`: the relationship in words, `present` and `outcome` (phrase book), for context only;
- `previous_situations`: the previous situations line, or null (null also when the line is regenerated);
- `sentences`: sentences of the mid-term entries that cite this relationship (this week's, plus the earlier weeks' entries that the previous line was built from) **whose refs cite only diary items** (view ids `d1`, `d2`, ...; config `text.diary_ref_prefix`). The refs of each sentence are read, by `finding_id`, from the Findings database (read only; `finding_text`); the P1 tables are not changed. A sentence that cites a factor (`f`), a measure (`m`), a history note, a not-known-yet note, an earlier summary or an earlier conclusion, or any mix, or has no refs, is skipped. At most six sentences, most recent entry first (this week's entries newest first, then the earlier ones newest first), none twice. If there is none, there is no view, no call, and the line is null (a previous line stands only when the week has no diary sentence and the line is not being regenerated).

No state, no association sentence, no digits, dates or counts. Retracted memories have no view. Example:

```json
{
  "link": {"present": "short sleep the night before", "outcome": "higher dinner peaks"},
  "previous_situations": null,
  "sentences": ["The diary describes a deadline day with minimal proper meals.", "A family festival that evening is noted in the diary."]
}
```

### 8.2 The output

```json
{"situations": "In the cases noted, the situations included a festival and a deadline day."}
```
or `{"situations": null}`. One sentence of at most 25 words in the frame "In the cases noted, the situations included ...". The stored note is the association sentence(s) followed by the situations line. Retracted memories: the code sentence of 8.5 only, no model call.

### 8.3 What the association says (code)

| Status | Association |
|---|---|
| `candidate` | "may be linked to ... in her history" and "This is an early observation." |
| `supported` | "has repeatedly moved together with ... in her history" |
| `weakened` | "no longer clearly seen" |
| `retracted` | the fixed sentence of 8.2 |
| `same_day_only` true | "on the same day" (unless the exposure phrase already says it) |

### 8.4 Checks of the situations line (checks version `pck-v6`; these only)

1. One sentence in the frame, at most 25 words (valid JSON of the form above).
2. No digits, dates or times, and no counting words (one, two, once, twice, first, second, several).
3. No causal wording (the Findings stems) and none of: moved together, linked, tended.
4. No internal words (the Findings list including entangled, bundle, pair, points, plus `status`), none of the banned words (unknown, unspecified, unclear; and the feelings, states and habits felt, feel, feeling, proud, relieved, tired, stressed, anxious, happy, sad, guilty, drained, exhausted, "stayed up") and no underscore token; the frame's own "cases" is exempt.
5. No time-relative word: this week, last week, recently, recent, today, yesterday, tonight, now, currently, lately, so far, again, earlier, previous, prior.
6. The line repeats neither the link's phrases nor any other relationship's phrase.
7. A clinical term only if the sentences have it.
8. No phrase repeated (a run of content words between other words or punctuation; a word may come back inside a different phrase, e.g. "work trip" and "work festival").
9. The situation words come from the sentences (stem overlap, with plurals, -ing, -ed and a final e ignored); the check fails only when at least two words are strays and they are at least a quarter of the line's content words.
10. No names (no capitalised word besides the start of the sentence).
11. No item of the list is only a generic word: change, evening, day, night, morning, afternoon, time, thing (with or without an article, singular or plural). An item such as "an evening with a family emergency" passes; "an evening" fails.

On failure, retry once with the failed checks added. If it fails again, **drop the line** (store null): the association stays. A previous line is kept (no call) when no diary sentence is available this week.

### 8.5 Code text (the association)

Built from the phrase book and the status: the exposure phrase, the verb for the status (8.3), the outcome phrase, "in her history", "on the same day" where required, and "This is an early observation." for a candidate. For a retracted memory: "This link, once suspected, is no longer supported by her history."

### 8.6 Regeneration, caching and storage

- Every `regenerate_every_weeks` (default 4) counted from the creation week, the situations line is rewritten **without** the previous line, from this week's sentences only, so wording cannot drift.
- The model result is stored beside the memory version (`pi_text`, `pi_llm`: raw and cleaned line, view hash, prompt version `pp-v4`, checks version `pck-v6`, the finding ids of the entries whose sentences were used), never in it. The cache key covers the view, the prompt texts, the model, the settings and the checks version; a refresh flag recomputes.
- Model, reasoning effort, timeout and retries are config (section 10).

---

## 9. Retrieval (what Findings reads)

All calls take `as_of` and return only versions with `written_at` at or before it. Return values are plain parsed objects.

| Call | Returns |
|---|---|
| `get_long_term(relationship_key, as_of)` | the latest version, or null |
| `get_long_term_many(keys, as_of)` | a map of key to latest version |
| `list_long_term(status=None, as_of)` | the latest versions, optionally filtered by status |
| `get_open_week(as_of)` | the entries received so far in the week that contains `as_of` |
| `get_sealed_weeks(n, as_of)` | the `n` most recent sealed weeks |
| `get_case_entry(case_id, as_of)` | the latest entry for a case |
| `get_seen_before(relationship_key, as_of)` | the band: `none`, `this_week`, `recent_weeks`, `earlier` |
| `record_finding(finding)` | idempotent write into the open week (section 5) |

---

## 10. Config (all values are defaults)

```yaml
pi:
  method_version: pi-v0
  week: {start_day: monday, close_at: "23:59:59", timezone_from: baseline_config, partial_week: {min_days: 4, scale_threshold: true}}
  week_label: {days_needed: 5, of: 7}
  lifecycle:
    promote_after_weeks: 2
    weaken_after_weeks: 2
    retract_after_weeks: 6
    retract_on_contrary: {days_per_week: 5, weeks: 4}
    repromote_after_weeks: 2
    placebo_fired_max_share: 0.5
    backfill_on_create: true
  seen_before_bands: {this_week_days: 7, recent_weeks_days: 28}
  text:
    enabled: true
    model: "openai/gpt-5-mini"
    reasoning_effort: low
    timeout_seconds: 90
    sdk_retries: 0
    retries: 1
    max_words: 25                 # the situations line
    regenerate_every_weeks: 4
    cache: true
  phrasebook: shared with the Findings Engine (findings_engine_spec.md, Appendix A)
```

---

## 11. The replay driver (shared contract)

Meera's data is historical, so a small deterministic driver steps through time and wires the components in order. It is built with PI's code layer (stage P1). It is not a new component; it is this contract.

1. **Clock.** The driver owns "now". It sorts the events of the year: hand-offs by `opened_at` (ties by `handoff_id`), evidence completions by their evaluation time, and week ends.
2. **Before each event**, if a week end lies between the previous event and this one, run PI's weekly job for it. Then close any case whose gap has passed.
3. **For each hand-off:** read its packet and event evidence (already computed; their relationship evidence is keyed by outcome date, so reads are naturally as-of); open or extend the case; the Findings Engine writes a version; `record_finding` into PI.
4. **For each completion:** the Findings Engine writes a new version of the case and calls `record_finding`.
5. **At the end of the data,** close open cases and run the final weekly job.
6. **Idempotent and resumable.** Re-running writes nothing new. A progress marker allows a stop and restart.
7. **Modes.** `code_only` (both text layers off) and `full`. The reads of `memory_v2` and the diary are filtered by `as_of`.
8. **Report.** Cases per day, versions per case, weeks run, statuses by week, text sources, checks failed.

---

## 12. Key dictionary

### 12.1 Input keys
Finding record keys (`findings_engine_spec.md` 11.3); evidence daily record keys `relationship_key`, `as_of_date`, `support`, `flags`; config `pi:` block.

### 12.2 Working keys
`open_week`, `week_label`, `days_supported`, `status_change`, `view`, `view_hash`, `backfill_labels`.

### 12.3 Output keys
Mid-term memory: `memory_id`, `tier`, `week` (`iso`, `start`, `end`), `status` (`open` or `sealed`), `sealed_at`, `entries` (`case_id`, `local_date`, `finding_id`, `entry_version`, `mode`, `relationship_keys`, `headline`, `sentences`), `relationship_keys_touched`, `case_days`.
Long-term memory: `memory_id`, `relationship_key`, `version`, `written_at`, `status`, `status_since`, `same_day_only`, `story_coupling`, `weekly_labels` (`week`, `label`, `days_supported`, `days_in_week`), `counters` (`case_days`, `exposed_case_days`, `first_seen`, `last_seen`, `weeks_seen`), `flags_seen`, `evidence_refs`, `finding_ids`, `text` (`sentences`, `source`), `text_version`.
Weekly run: `week`, `memories_created`, `statuses_changed`, `texts_updated`, `texts_kept`, `usage_json`.

### 12.4 Storage

Its own database (suggested name `output/pi.db`). Names are suggestions. All tables are append-only; no table holds a wall-clock time.

| Table | Key | Holds |
|---|---|---|
| `pi_mid_memories` | `memory_id` | week bounds, `status`, `sealed_at` |
| `pi_mid_entries` | `memory_id`, `case_id`, `entry_version` | the entry, `written_at` |
| `pi_long_memories` | `memory_id`, `version` | the memory, `written_at` |
| `pi_weekly_runs` | `week` | the run record |
| `pi_llm` | `memory_id`, `version` | `view_hash`, `llm_raw`, `usage_json`, `checks_json` |

---

## 13. Worked example: the final week, 2026-09-14 to 2026-09-17 (illustrative)

The data ends on Thursday 17 September, so the last calendar week has four days and the final weekly job runs at the end of the data (17 September, 23:59:59). The evening case of 17 September (`findings_engine_spec.md`, example A) is recorded into the open week as the case's version 2. The numbers in the labels are illustrative; the texts are what a model might write.

**The sealed mid-term memory** (one entry shown):

```json
{
  "memory_id": "pi_mid_2026-W38",
  "tier": "mid_term",
  "week": {"iso": "2026-W38", "start": "2026-09-14", "end": "2026-09-20"},
  "status": "sealed",
  "sealed_at": "2026-09-17T23:59:59+05:30",
  "entries": [
    {"case_id": "case_2026-09-17T21:45", "local_date": "2026-09-17", "finding_id": "fnd_case_2026-09-17T21:45_v2", "entry_version": 2, "mode": "relationship", "relationship_keys": ["missed_dose@2d->post_meal_peak:dinner", "sleep_hours@prev_night->post_meal_peak:dinner"], "headline": "Glucose rose well above her usual after a late festive dinner, on a day with missed doses and a very short night.", "sentences": ["The rise in the hour or so after this dinner was among the highest she has had after dinners.", "Short sleep the night before and missed doses on the same day or the day before have each tended to move together with higher glucose peaks after dinner in her history, and both were present today.", "The diary describes a deadline day with minimal proper meals.", "Her heart rate was also clearly above her usual earlier in the evening."]}
  ],
  "relationship_keys_touched": ["missed_dose@2d->post_meal_peak:dinner", "sleep_hours@prev_night->post_meal_peak:dinner"],
  "case_days": ["2026-09-17"]
}
```

**Two long-term memories are created at this job**, because both relationships were usable factors in the case. Both have been tested since December and supported on most days of most weeks, so the back-fill (6.3) runs the transitions over their earlier weekly labels and they are created as **`supported`**, not as `candidate`. The final week has four days of data: the scaled threshold is 3 of 4 days, and both relationships are supported on at least that many. The missed-dose relationship is `same_day_only` (its pair is marked `same_day_unverified`), so its text says "same day". Only the last weeks of the stored `weekly_labels` are shown; the earlier ones, from the first week each was tested, are stored the same way.

```json
{
  "memory_id": "pi_long_sleep_hours@prev_night->post_meal_peak:dinner",
  "relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner",
  "version": 1,
  "written_at": "2026-09-17T23:59:59+05:30",
  "status": "supported",
  "status_since": "2025-12-28",
  "same_day_only": false,
  "story_coupling": "unknown",
  "weekly_labels": [
    {"week": "2026-W35", "label": "supported", "days_supported": 7, "days_in_week": 7},
    {"week": "2026-W36", "label": "supported", "days_supported": 6, "days_in_week": 7},
    {"week": "2026-W37", "label": "suggestive", "days_supported": 4, "days_in_week": 7},
    {"week": "2026-W38", "label": "supported", "days_supported": 4, "days_in_week": 4}
  ],
  "counters": {"case_days": 1, "exposed_case_days": 1, "first_seen": "2026-09-17", "last_seen": "2026-09-17", "weeks_seen": 1},
  "flags_seen": [],
  "evidence_refs": [
    "rel|sleep_hours@prev_night->post_meal_peak:dinner|2026-09-06|ev-v0",
    "rel|sleep_hours@prev_night->post_meal_peak:dinner|2026-09-13|ev-v0",
    "rel|sleep_hours@prev_night->post_meal_peak:dinner|2026-09-17|ev-v0"
  ],
  "finding_ids": ["fnd_case_2026-09-17T21:45_v2"],
  "text": {"sentences": ["Short sleep the night before has repeatedly moved together with higher glucose peaks after dinner in her history."], "source": "llm"},
  "text_version": 1
}
```

```json
{
  "memory_id": "pi_long_missed_dose@2d->post_meal_peak:dinner",
  "relationship_key": "missed_dose@2d->post_meal_peak:dinner",
  "version": 1,
  "written_at": "2026-09-17T23:59:59+05:30",
  "status": "supported",
  "status_since": "2026-03-01",
  "same_day_only": true,
  "story_coupling": "unknown",
  "weekly_labels": [
    {"week": "2026-W36", "label": "supported", "days_supported": 6, "days_in_week": 7},
    {"week": "2026-W37", "label": "supported", "days_supported": 5, "days_in_week": 7},
    {"week": "2026-W38", "label": "supported", "days_supported": 3, "days_in_week": 4}
  ],
  "counters": {"case_days": 1, "exposed_case_days": 1, "first_seen": "2026-09-17", "last_seen": "2026-09-17", "weeks_seen": 1},
  "flags_seen": ["same_day_unverified"],
  "evidence_refs": [
    "rel|missed_dose@2d->post_meal_peak:dinner|2026-09-13|ev-v0",
    "rel|missed_dose@2d->post_meal_peak:dinner|2026-09-17|ev-v0"
  ],
  "finding_ids": ["fnd_case_2026-09-17T21:45_v2"],
  "text": {"sentences": ["Missed doses on the same day or the day before have repeatedly moved together with higher glucose peaks after dinner in her history, on the same day."], "source": "llm"},
  "text_version": 1
}
```

**What Findings sees the next time** a similar glucose rise occurs: `get_long_term_many` returns these memories, so it can say the observation has come up before. The wording of a sentence still follows today's evidence label and class, not PI's status. A relationship that is first used later in the year, after weeks of being supported, is created the same way, with a status that reflects its history.

---

## 14. Properties that must hold

1. **Only Findings writes findings into PI.** PI's own writes are the weekly job.
2. **Append-only.** No version is changed after it is written; sealed weeks never change.
3. **As-of reads.** No call returns anything written after its `as_of`.
4. **No wall clock.** Identical re-runs give identical records.
5. **Statuses are decided by code,** from the Evidence store's daily labels, never by an LLM, never by one event, and never by Findings' text.
6. **The LLM sees no numbers and writes only wording.** No digits appear in any PI text.
7. **Status wording is respected;** `same_day_only` texts say "same day"; no sentence is stronger than the status allows.
8. **A failed check never loses a good text.** The previous text is kept; the code text is the last fallback.
9. **Counters count dates, not versions or cases.** A relationship counts at most once per local date.
10. **No statistics are copied into PI.** Evidence is referenced by id.
11. **Evidence does not read PI.** Beliefs never feed back into the statistics.
12. **Relationship memories only.** No memory exists for a relationship that no finding used.
13. **No reordering or rewriting of the rulebook.**
14. **Idempotent.** Recording the same finding twice, or running the same week twice, writes nothing new.
15. **Regeneration happens on schedule** and rewrites from structured data only.
16. **Generic.** No stream, measure, medicine or patient name in the engine; phrases live in config. A second patient runs with config changes only.
17. **Load check.** Loading fails with a plain message if a relationship key in the Evidence library has no phrase, or a status has no wording rule.

---

## 15. Limits, assumptions and open items

| Item | What I assumed | Where it matters |
|---|---|---|
| Placeholders | The week rule (5 of 7), the promotion and demotion lengths, the retraction length and the regeneration interval are starting guesses. | Tune against reviewed output and the scoring report, not to produce statuses. |
| Association, not mechanism | `supported` is "has repeatedly moved together". On the first patient most supported links sit on story days; `story_coupling` is `unknown` for every memory. | Wording stays weak. A later ordinary-day control may fill the field. |
| Status is persistence, not confirmation | On the first patient 26 of 29 memories reach `supported`: memories exist only for relationships that findings used, the Evidence labels already persist for months, and 15 of the 29 were created `supported` by back-fill. A status therefore reports the persistence of the Evidence label; it is **not** independent confirmation of a link. | Wording stays weak ("has repeatedly moved together with"); do not read a `supported` memory as evidence beyond the Evidence labels it summarises. |
| Known limit: same-hour steps | The one built formula, steps in the previous hour to heart rate in that hour (`steps_window_hourly@60m->hr_hour_mean`), was `weakened` (2026-W22) and `retracted` (2026-W28) because the Evidence ordering rule excludes same-hour steps. Evidence v1.1, a same-hour variant, is parked. | Its memory is a result of the ordering rule, not of her data. |
| Weekly delay | A relationship first used in week N has its memory from the end of week N. | Findings in week N read only the open week's entries. |
| Back-fill | On creation the status reflects earlier weeks, so a memory can start as `supported`. | Intended; the stored weekly labels show why. |
| Relationship memories only | Event-level patterns (for example repeated unusual meals), recurring story themes and other non-relationship knowledge have no memory in V0. | Findings can mention them only for the current case. |
| Text drift | Repeated LLM rewriting can drift. | Regeneration from structured data every four weeks; versions kept. |
| Time zone and weeks | Weeks follow the patient's timezone and ISO numbering. | A week that crosses a daylight-saving change is still seven calendar days. |
| Same-day links | More than half of supported evidence records are same-day. | `same_day_only` memories say "same day" and are never described as preceding. |
| Early history | Before about 10 December nothing is tested, so no long-term memory exists. | The hospitalization week is in the first mid-term memories only. |

---

## 16. Out of scope

Reordering or rewriting the rulebook, discovery of new relationships, theme memories, embeddings and similarity search, the cross-patient aggregator, the Narrative Layer, and any user-facing formatting.

## 17. Glossary

| Term | Meaning |
|---|---|
| Findings memory | PI's memory: what was concluded about why. Distinct from the state memory (`memory_v2`). |
| Mid-term memory | The findings of one calendar week, open until the week ends, then sealed |
| Long-term memory | One memory per relationship, with a status and a text, rewritten weekly |
| Relationship | An exposure with its window, paired with an outcome (the Evidence library's key) |
| Week label | The label of a relationship for one week, from its seven daily labels |
| Status | `candidate`, `supported`, `weakened`, `retracted` |
| As-of | A read that returns only what was written at or before a given time |
| Back-fill | Running the status rules over earlier weeks when a memory is created |
| Code text | Wording built from the phrase book and the status, used when the text layer is off or fails |

---

## Appendix A. Prompt for the situations line (prompt version `pp-v4`)

The association is code text and is not in the prompt. `pp-v1` (which asked the model to rewrite the association) is withdrawn; `pp-v2` (entries as the source) was replaced by `pp-v3` (diary-only sentences, and the prompt says what a situation is not); `pp-v4` adds the noun-phrase rule.

**System prompt**

```
You add one short line to a note in a person's health record. The note (which you do not write or change) says how two things have moved together in her history. Your line says what was going on in her life in the cases where it was recorded.

You receive a VIEW: the two things in words (for context only), the previous line (or null), and sentences taken from her diary context. All numbers were removed on purpose.

Write {"situations": "one sentence"} or {"situations": null}.

A situation is something that happened or was going on in her life: an event, an activity, an outing, a social occasion, a piece of news. Readings, doses, sleep, activity levels, fluid intake, moods, meals and anything about her numbers are NOT situations.

RULES. Follow all of them.
1. One sentence of at most 25 words, starting with "In the cases noted, the situations included" followed by a plain list of at most four situations.
2. Name only situations that the sentences state, in plain words, with no names of people, places or events. Use no words that are not in the sentences, except plain grammar words.
3. List noun phrases only (an event, outing, occasion, activity or piece of news), with no verbs and no past tense; never list feelings, states or habits.
4. If the sentences state no situation, return {"situations": null}. Null is a good answer.
5. Do not link anything and do not explain: no "moved together", "linked", "tended", "because", "led to", no advice, no prediction. Do not mention the two things of the note.
6. No words about time relative to now: this week, last week, recently, today, yesterday, tonight, currently, lately, so far, again, earlier, previous, prior, recent.
7. No digits, dates or times, and no counting words (once, twice, first, second, one, two, several).
8. If a previous line is given, keep the situations the sentences still state and add new ones, up to four in all.
9. Do not use the words: evidence, label, relationship, factor, supported, suggestive, statistic, engine, memory, hand-off, group, class, exposure, entangled, bundle, pair, points, status. The word "cases" is allowed only in the opening phrase.
10. Do not write view field names or any word with an underscore, and use no capital letters except at the start of the sentence.
11. Use only what is in the sentences. Do not invent.
Return only JSON.
```

**User template**

```
VIEW:
{view_json}
```

**Retry addendum (appended once):**
```
Your previous answer failed these checks: {failed_checks}. Rewrite it using only the sentences, in the frame, as one short sentence, or return null.
```
