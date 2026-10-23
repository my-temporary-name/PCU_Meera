# 8. PI (Findings memory)

You can read Part A without opening any code. It explains what PI remembers, how a memory moves from "early idea" to "repeatedly seen" to "no longer supported", and where the model comes in, using real memories from this patient. Part B is the technical detail for engineers.

Numbers come from the final database `output/pi_loop_polish.db` (read directly), `task/pi_spec.md` (with its Amendments, which win over the body), `docs/pi_p1_report.md` and `config/pi_meera_iyer_v1.yaml`. Nothing was rerun to write this file.

---

# Part A. The idea in plain words

## A1. Where it sits, and what problem it solves

The Findings Engine writes one careful account per alert. That account is a snapshot: it only knows about today. But a doctor, and the system itself, also needs to know: **"has this come up before? how often? is this link holding up over weeks, or was it a one-off?"**

PI is the **memory of conclusions**. It does not store her numbers (the Baseline and State engines do that). It stores *what the system has concluded about why things happen*, week by week and link by link.

> **One line:** PI keeps a weekly notebook of findings, and one long-running file per "link" (for example "short sleep → higher heart rate") that says how strongly her own history supports it.

It does three jobs and nothing else: **create** memories, **update** them, and **hand them back** when Findings asks.

## A2. The analogy: a clinic's case notebook and a patient file

Picture two things on a clinic shelf:

- **A weekly notebook.** Each week the nurse jots down every finding of that week. At the end of the week the notebook is sealed and never edited again.
- **One folder per suspected link.** The folder for "short sleep → higher heart rate" has a cover sheet: *"early idea"*, *"seen repeatedly"*, *"not holding up any more"*, or *"withdrawn"*. Each Sunday night someone reads the week's evidence and decides whether the cover sheet should change. Old cover sheets are kept, never thrown away.

PI is that shelf. The decision about the cover sheet is **made by code from a counting rule**. The only thing a model ever writes is one optional sentence listing the *situations* mentioned in the diary when the link showed up.

## A3. Four words: mid-term memory, long-term memory, relationship, status

| Word | Plain meaning | Example |
|---|---|---|
| **Mid-term memory** | The notebook for one calendar week (Monday to Sunday). Holds that week's findings. Open while the week runs, sealed at the end. | Week 2026-W37 holds the glucose case of 9 Sep and others. |
| **Relationship** | An exposure paired with an outcome, the same "pairs" the Evidence Engine tests. | `sleep_hours@prev_night->hr_day_mean` = "short sleep the night before → heart rate over the day". |
| **Long-term memory** | The folder for one relationship: status, counters, week-by-week labels, a short text. New versions are added, old ones are kept. | 29 folders on this patient. |
| **Status** | What is believed about the link over time: `candidate`, `supported`, `weakened`, `retracted`. | See A4. |

A status is always a statement about **association in her history**, never about a cause.

## A4. How a status is decided (the counting rule)

PI never uses one day, and never reads the numbers. It reads only the **daily labels the Evidence Engine already gave** (supported / suggestive / not supported / insufficient) and turns each calendar week into one label:

- **supported week:** at least 5 of the 7 days were `supported`
- else **suggestive week:** at least 5 days were `supported` or `suggestive`
- else **insufficient week:** at least 5 days were `insufficient`
- else **not-supported week**

Then the status moves like this:

| From | To | When |
|---|---|---|
| (new) | `candidate` | the first time a finding uses the link |
| `candidate` | `supported` | **2 supported weeks in a row**, and the placebo flag fired on under half of those days |
| `supported` | `weakened` | **2 not-supported weeks in a row** |
| `weakened` | `supported` | 2 supported weeks in a row again |
| `weakened` | `retracted` | 6 further not-supported weeks (or the `contrary` flag on 5+ days a week for 4 weeks) |
| `retracted` | `candidate` | 2 supported weeks in a row |

Suggestive and insufficient weeks neither promote nor demote, and do not reset a count. An opposite decisive week (supported vs not supported) **does** reset it.

These numbers (5 of 7, 2, 6, 4) are placeholders from the spec. They are not tuned to produce a nice-looking result.

## A5. A real example, step by step: "more activity in the hour before → higher heart rate"

This is `steps_window_hourly@60m->hr_hour_mean`, the only link on this patient that went all the way to *retracted*.

1. **Created, 21 Dec 2025 (week 2025-W51).** A finding on 15 Dec used the link, so the weekly job made a folder. It started as `candidate`.
2. **Back-fill.** The folder does not start blank. Code replays the link's weekly labels from the week it was first tested: W50 supported, W51 supported. Two supported weeks in a row → **`supported` immediately**, so a link that has held for weeks is not shown as brand new.
3. **Weeks 2025-W50 to 2026-W20: supported every week.** Each of those weeks had 7 of 7 days `supported`, and the placebo flag never fired. Status stayed `supported`.
4. **Week 2026-W21: not supported** (only 3 supported days). The count starts at 1.
5. **Week 2026-W22: not supported again** (0 supported days). Two in a row → **`weakened`** (version 17, written 31 May 2026).
6. **Weeks 2026-W23 to W28: all not supported.** Six further weeks → **`retracted`** (version 18, written 12 Jul 2026). Its note is now the fixed sentence: *"This link, once suspected, is no longer supported by her history."*

Why did a link that held for 20 weeks collapse? The Evidence Engine has an ordering rule: same-hour steps cannot be said to *precede* heart rate. The memory records that evidence honestly; the spec lists this as a known limit (a later Evidence variant may handle same-hour effects).

Its counters at the end: 30 case-days (distinct dates it was a usable factor), 14 of them "exposed" (the activity was actually present), first seen 15 Dec 2025, last seen 18 Apr 2026, seen in 16 weeks.

## A6. What the note says (and who writes it)

A long-term note has **two parts**:

1. **The association (always written by code).** Short, fixed templates, one per status:

   | Status | Example, real |
   |---|---|
   | `candidate` | "A day away from home may be linked to more missed doses that day in her history, on the same day. This is an early observation." |
   | `supported` | "Short sleep the night before has repeatedly moved together with higher heart rate over the day in her history, on the same day." |
   | `weakened` | says the link is "no longer clearly seen" |
   | `retracted` | "This link, once suspected, is no longer supported by her history." |

   If the link is `same_day_only` (the Evidence Engine could not tell which came first), the text says "on the same day" so it is never described as something that *preceded* the outcome.

2. **The situations line (optional, written by a model).** One sentence, at most 25 words, in a fixed frame. Real example:

   > *In the cases noted, the situations included a winter school break, socializing with friends, holiday preparations, family shopping.*

   It lists the **situations from the diary** that were present when the link appeared. It tells a reader the *kind of days* involved, without claiming anything.

The model never writes or edits the association, never decides a status, and never sees a number.

## A7. How the situations line is made safe

Code first picks what the model may read. Only **diary-only sentences** from this week's findings count, i.e. sentences whose references point only to diary items. A sentence that mixes in a factor, a measure or an earlier summary is skipped. At most 6 sentences are shown, most recent first. **If there are none, the model is not called and the line is empty.** That is allowed: an empty line is a good answer.

Then the model's answer must pass checks:

- one sentence in the frame, at most 25 words
- no digits, dates, or counting words (one, twice, first, several)
- no causal words ("because", "caused") and none of "moved together" / "linked" (those belong to the association)
- no feelings or habits ("felt relieved", "stayed up late"): a situation is something that happened, not how she felt
- no time-relative words ("this week", "recently", "earlier", "again"), since the note is read much later
- no repeated phrase, no names, no phrase from the association or another relationship
- no item that is only a generic word ("an evening")

One retry with the failures spelled out. If it fails again, **the line is dropped** and the association stays. A good earlier line is never lost to a bad new one.

To stop wording from drifting, every 4 weeks the line is rewritten from scratch (without the previous line).

## A8. What happened on this patient

| What | Count |
|---|---:|
| Weeks processed | 51 (2025-W40 to 2026-W38) |
| Weekly entries stored (latest version per case) | 284 version-entries from 116 cases |
| Long-term memories (relationships) | 29 |
| Versions written across all memories | 174 |
| Final status | 25 `supported`, 3 `candidate`, 1 `retracted` |
| Reached `supported` at some point | 26 (15 of the 29 were created as `supported` through back-fill) |
| Ever `weakened` | 1 (2026-W22), then `retracted` (2026-W28) |
| Memories with the `contrary` flag | 0 |

No memory exists before **21 Dec 2025**: the Evidence Engine tests nothing before about 10 December, so there are no labels to count. The first mid-term memories (October to early December) hold findings but no long-term folders.

Situations-line outcomes across the 174 versions:

| Outcome | Versions |
|---|---:|
| Line written by the model and accepted | 126 |
| No diary-only sentence, so no call, empty line | 39 |
| Previous line kept (nothing new to say) | 7 |
| Dropped after two failed attempts | 1 |
| Retracted memory (code text only, no call) | 1 |

## A9. An honest caveat: "supported" means "persistent", not "proven"

26 of 29 memories ended up `supported`. That is not because everything is true. Memories only exist for links that findings already used; the Evidence labels already persist for months; and 15 were created `supported` by back-fill. So `supported` reports **persistence in her history**, nothing more. `story_coupling` (is the link only seen on "story days"?) is `unknown` for every memory.

Other limits: same-day links cannot be ordered in time; a link first used in week N has its folder only from the end of week N; and the checks cannot tell a "situation" from a "feeling" in every case.

## A10. What PI deliberately does NOT do

- It does not compute statistics. It reads labels the Evidence Engine already produced.
- It does not change the rulebook or add new relationships.
- It does not read raw data, the diary directly, or the state memory.
- It does not decide a status with a model, or from one event.
- It never feeds back into the Evidence Engine.
- It does not restate her numbers.

## A11. Where its output goes

- **Back into Findings.** When Findings writes a new version, it asks PI: "has this link come up before?" PI answers with a band (`none`, `this_week`, `recent_weeks`, `earlier`) and, for long-term memories, the status in plain words (`candidate` = early, `supported` = repeated, `weakened` = fading). Findings may then say "this has come up before". **A PI status never upgrades how strongly Findings may word something** (a tested property).
- **The doctor-facing text.** The long-term notes are the ready-to-read "what we know about her" list.

---

# Part B. Technical detail

## B1. Position in the system

```
Findings versions (read) ─┐
Evidence daily labels  ───┼─► PI weekly job ─► pi_mid_* / pi_long_* / pi_text
Findings DB (diary refs) ─┘                              │
                                                         └─► retrieval (as-of) ─► Findings (loop)
```

- Writes only its own file (`output/pi.db` standalone; `output/pi_loop*.db` in the loop). Findings, Evidence and the other databases are opened read-only (checksums unchanged).
- Evidence does not read PI. Only Findings writes findings into PI.
- Stages: **P1** (code layer + replay driver), **P2** (situations-line text layer), then the loop stages **L1/L2/polish** (`src/v0_code/loop_engine/`), which run PI live beside Findings.

## B2. Modules (`src/v0_code/pi_engine/`)

| File | Role |
|---|---|
| `weeks.py` | Monday to Sunday weeks in the patient's zone, ISO names; first week = week of the first data day; partial last week. |
| `labels.py` | `week_label`, `needed_days = ceil(5/7 x days)`, `EvidenceLabels` (read-only view of Evidence daily records: only `support` and `flags`). |
| `lifecycle.py` | Pure functions: `Wk`, `State`, `step`, `run`. No database. |
| `engine.py` | The weekly job (seal, labels, create, counters, transitions, write). |
| `driver.py` | Replays stored Findings versions in time order, calls the engine; `full` or `code_only` mode. |
| `storage.py` | SQLite tables and as-of reads (strict mode for the loop). |
| `codetext.py` | The association text from the phrase book's `pi_text` templates. |
| `text_view.py`, `text_layer.py`, `text_check.py` | P2: the view, the model call (prompt `pp-v4`), the checks (`pck-v6`). |
| `audit.py` | Independent as-of re-read (4,948 weekly labels, 34,246 evidence days, none after its job). |
| `report.py`, `report_text.py`, `run.py`, `run_text.py` | Reports and CLIs. |

Shared: `intel_common/phrasebook.py` (phrases for exposures, outcomes and `pi_text`), `timeutil.py`. Config: `config/pi_meera_iyer_v1.yaml`; phrase book `config/findings_phrasebook_v0.yaml`. No stream, measure, medicine or patient name in the engine (a test enforces it; `tests/pi_synth.py` runs a second synthetic patient on config alone).

## B3. Inputs

1. **Findings versions** (with `case_id`, `local_date`, `mode`, relationship factors, the text). Entry = the latest version per case, **in the week of its `as_of`**, not of its `local_date`.
2. **Evidence daily records** by `relationship_key` and date: only `support` and `flags`. A day with no record counts as `insufficient`.
3. **Evidence library** (config path), read-only: for `same_day_only` and the phrase-book load check.
4. **Findings database** (read-only, by `finding_id`) for the refs of sentences (P2 diary filter).

## B4. Weeks and the weekly job

- The job runs for every week end strictly before the next event; the last job runs at the last data day, 23:59:59 (partial week).
- Partial week: counts only days that exist; threshold `ceil(5/7 x days)` (7 days: 5, 5 days: 4, 4 days: 3); fewer than 4 days gives `insufficient`.
- Order: (1) seal the open mid-term memory; (2) week labels for every existing memory; (3) create memories for relationships that became usable factors that week (usable = label `supported` or `suggestive`, exposed or not), with back-fill; (4) counters; (5) status transitions; (6) text update (touched, changed, new or due for regeneration); (7) write new versions; (8) run record in `pi_weekly_runs`.
- Event-level checks (no relationship key) have no long-term memory in V0.

## B5. The lifecycle (`lifecycle.py`)

- `Wk`: week iso, end, label, `days_in_week`, `placebo_days`, `contrary_days`, `days_with_record`, `days_supported`.
- A count of consecutive weeks is the **current run of equal decisive labels** (`supported` / `not_supported`); the opposite decisive label resets it (amendment 35). Therefore **back-fill on creation equals stepping week by week**.
- One transition at most per week. `candidate → supported` also needs `_placebo_ok`: `placebo_days / days < placebo_fired_max_share (0.5)` over the weeks of the run.
- `weakened` tracks `ns_after` (unbroken not-supported weeks after weakening) and `contrary_run` (weeks with `contrary` flag on at least 5 of 7 days); either reaching its limit gives `retracted`.
- `retracted → candidate` after 2 supported weeks (`repromote_after_weeks`).
- Config (`lifecycle`): `promote_after_weeks 2`, `weaken_after_weeks 2`, `retract_after_weeks 6`, `retract_on_contrary {5, 4}`, `repromote_after_weeks 2`, `placebo_fired_max_share 0.5`, `backfill_on_create true`.

## B6. The long-term memory record

Keys: `memory_id` (`pi_long_<relationship_key>`), `relationship_key`, `version`, `status`, `status_since`, `status_history`, `created_week`, `same_day_only`, `story_coupling` (`unknown`), `weekly_labels` (all weeks from first tested, each with counts), `counters`, `dates` (case ids per date), `flags_seen`, `evidence_refs`, `finding_ids`, `text` (`{sentences, source}`; plus `situations` and entry ids via the overlay), `text_version`, `written_at`.

- **Counters count dates, not versions or cases:** `case_days`, `exposed_case_days`, `first_seen`, `last_seen`, `weeks_seen`. Each date keeps the case ids that made it, so one date counts once and a current case can be excluded from `seen_before`. Counters use `local_date`.
- **`evidence_refs`:** the id (`rel|<key>|<date>|ev-v0`) of the last day with a record in each *decisive* week.
- **Append-only.** A new version is written only when it is created or its status, counters, `flags_seen`, `finding_ids` or text change (amendment 37). A week whose only effect is one more weekly label writes nothing. Sealed mid-term memories never change.
- **Mid-term memory** (`pi_mid_memories`): one row per `(memory_id, status)` where status is `open` or `sealed`; holds `case_days`, `entries`, `relationship_keys_touched`. Entries (`pi_mid_entries`) are unique by `(memory_id, case_id, entry_version)`, and carry the headline, sentences, mode and relationship factors, no statistics.

## B7. The text layer (stage P2)

- **View** (`text_view.py`): `link` (`present`, `outcome` phrases), `previous_situations`, `sentences` (diary-only: every ref starts with `d`, config `text.diary_ref_prefix`; at most 6, most recent first, none twice; refs read from the Findings database by `finding_id`). Numberless; no state, no association sentence.
- **Model:** `openai/gpt-5-mini`, reasoning low, 90 s timeout, SDK retries 0, one retry, concurrency 6. Output `{"situations": "In the cases noted, the situations included ..."}` or `{"situations": null}`.
- **Checks `pck-v6`:** structure and 25 words; digits and counting words; causal and claim words; internal and banned words (`unknown`, feelings, habits); time-relative words; no repeated phrase; stem overlap with the sentences (fails only with 2+ stray words and at least a quarter of the line); no names; clinical terms only if in the sentences; no generic-only item.
- **Outcome statuses** in `pi_text`: `ok`, `kept_previous_line`, `no_diary_sentences`, `dropped`, `code_text_retracted`.
- **Regeneration:** every `regenerate_every_weeks` (4) from the creation week, rewritten without the previous line.
- **Cache key:** view + prompt texts (`pp-v4`) + model + settings + checks version. Overlay tables `pi_text` and `pi_llm` (PK memory_id, version) survive a P1 `--rebuild` and never touch P1 tables (byte-identity checked).
- Retracted memories: code text, no call.

## B8. Retrieval (what Findings reads), all as-of

`get_long_term`, `get_long_term_many`, `list_long_term`, `get_open_week`, `get_sealed_weeks`, `get_case_entry`, `get_seen_before`, `record_finding` (idempotent). In the loop, `PiLive` uses a **strict** reader (`PiReader(strict=True)`: only what was written strictly before the version's time), because an entry is stamped with its own version's `as_of` and an inclusive read made a rerun see something the first run did not.

`get_seen_before(key, as_of, exclude_case)` returns a band from the latest `local_date` among the relationship's entries: `this_week` (within 7 days), `recent_weeks` (within 28), `earlier`, or `none` (`seen_before_bands: {this_week_days 7, recent_weeks_days 28}`).

## B9. The loop (stages L1, L2, polish; `src/v0_code/loop_engine/`)

- **L1 (code layer).** Findings runs live in time order with PI hooks: weekly jobs fire before each event past a week end; `record_finding` after each version. Every version equals the F1 version except `repeat` and `refs.pi_memories`. PI's five tables are byte-identical to a P1 code-only replay. 85 versions precede the first long-term memory.
- **L2 (with models).** Each version enters PI's open week at once with its **code line**; at each **week barrier** the week's Findings texts are written, entry texts are replaced by the final text (open weeks only, text only), PI's weekly job runs, then the situations lines of the new memory versions are written.
- **Polish round** (Findings `p-v5` / `ck-v7`): final databases `output/findings_loop_polish.db` + `output/pi_loop_polish.db`. PI situations lines: 97 regenerated, 30 reused, 47 without a call, 1 dropped. PI long-term tables, statuses and transitions identical to L2.
- A PI status never changes a Findings wording class, mode or group (property test).

## B10. Storage (`output/pi_loop_polish.db`)

`pi_mid_memories`, `pi_mid_entries`, `pi_entry_keys` (finding_id × relationship_key, exposed), `pi_long_memories` (PK memory_id, version), `pi_weekly_runs`, `pi_text`, `pi_llm`, `pi_progress`, `pi_meta`.

## B11. Results on this patient

| Check | Result |
|---|---|
| Weeks / entries / memories / versions | 51 / 284 / 29 / 174 |
| Final statuses | 25 supported, 3 candidate, 1 retracted |
| Weakened → retracted | `steps_window_hourly@60m->hr_hour_mean` (W22, then W28) |
| Created as `supported` by back-fill | 15 of 29 |
| Determinism and idempotency | two runs identical; a finished run writes nothing |
| As-of audit (independent re-read) | clean |
| Retrieval-ordering audits in the loop | clean |

## B12. Gotchas and decisions to check before changing anything

1. **Entry week = week of `as_of`**, not of `local_date`; counters use `local_date`. Mixing them moves entries between weeks.
2. **A status is a pure function of the weekly labels**, so back-fill and week-by-week stepping must agree. Do not add state that depends on when the job ran.
3. **Do not tune the lifecycle numbers to get statuses** (spec §15). They are placeholders.
4. **Never read PI inclusively in the loop** (strict reader), or reruns diverge.
5. **Only `support` and `flags` are read from Evidence.** Adding another field would start copying statistics into PI (property 10).
6. **The situations line is diary-only by design** (amendment 44). A sentence that mixes a diary ref with anything else is skipped, not trimmed.
7. **`pck-v6` cannot tell a situation from a feeling or habit** in every case, and cannot detect broken grammar after the frame.
8. **The association is code text, always.** A model rewrite added nothing and once let "this week" into a stored note (amendment 43).
9. **A memory is never edited.** To change text, write a new version; P1 `--rebuild` keeps the `pi_text` overlay.
10. **`supported` is persistence, not confirmation**, and `same_day_only` memories must keep "same day".

## B13. Quick checks (read-only)

```bash
# status of every long-term memory, latest version
sqlite3 output/pi_loop_polish.db "select relationship_key, status, version from pi_long_memories m where version=(select max(version) from pi_long_memories where memory_id=m.memory_id)"

# text outcomes of the situations line
sqlite3 output/pi_loop_polish.db "select status, count(*) from pi_text group by status"

# weekly job records
sqlite3 output/pi_loop_polish.db "select week, written_at from pi_weekly_runs order by week"
```

```bash
uv run python -m v0_code.pi_engine.run --config config/pi_meera_iyer_v1.yaml                 # P1 replay -> output/pi.db, then the audit
uv run python -m v0_code.pi_engine.run_text --config config/pi_meera_iyer_v1.yaml --sample    # P2 sample (needs the API key)
uv run python -m v0_code.loop_engine.run --config config/loop_meera_iyer_v1.yaml              # L1 loop, code layer
```
