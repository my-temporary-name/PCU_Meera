# 7. Findings Engine

You can read Part A without opening any code. It explains what the Findings Engine does, how it decides what may be said, and how the text gets written, using real cases from this patient. Part B is the technical detail for engineers.

Numbers come from the final database `output/findings_loop_polish.db` (read directly), `task/findings_engine_spec.md` (with its Amendments, which win over the body), `docs/loop_polish_report.md` and `understand/how_the_numbers_flow.md` §7, unless said otherwise.

---

# Part A. The idea in plain words

## A1. Where it sits, and what problem it solves

So far the chain has produced:

| Component | What it gave us |
|---|---|
| State Engine | an **alert**: "her glucose is clearly above her usual at 22:30" |
| Rulebook Lookup | a **checklist** of factors worth checking |
| Evidence Engine | for each factor, a **label and flags** from her own history (supported, suggestive, not supported, insufficient; placebo fired; same-day; and so on), plus whether the factor was present at that moment |

That is a lot of numbers and codes. Nobody can read it. The Findings Engine turns it into **one short, careful, plain-language account** of what happened and what was present alongside it. For example:

> *Glucose was clearly above her usual in the evening after dinner. Missed doses on the same day or the day before were present, and this has come up before. Short sleep the night before was present and low for her. The day's step total is not known yet.*

The key word is **careful**. The engine never says "this caused that". The strongest thing it is ever allowed to say is that two things "have tended to move together" in her history. Everything it may say is decided by **code**, from the evidence labels. A language model is used only at the very end, to put the allowed content into smooth sentences, and its output is checked.

> **One line:** it groups alerts into cases, decides by code which factors may be mentioned and how strongly, and only then has a model word it.

## A2. The analogy: a medical scribe with a rulebook

Imagine a scribe writing case notes for a doctor. The scribe has been given a **fact sheet** (the evidence) and a strict **style guide**:

- "Say a factor was *present* only if the sheet says it was."
- "Say two things *tend to move together* only if the sheet says that link is supported."
- "If the sheet says the test was unreliable, say the factor was present and say nothing about a link."
- "If something isn't known yet, say 'not known yet'. Never guess."
- "No numbers. No causes. No advice."

The scribe may be fluent, but the style guide decides what goes in. In this system the **style guide is code** (the wording classes), the **scribe is a language model**, and a **proofreader (code again) rejects anything that breaks the guide**. If the scribe fails twice, the proofreader writes the note from a template.

## A3. Three words: alert, case, version

| Word | Meaning | Example |
|---|---|---|
| **Alert** | one fact: a measure stayed off her usual (a State Engine hand-off). Once written, it is fixed | glucose above her usual at 22:30 |
| **Case** | a group of alerts that belong to one situation: an alert joins the open case if it arrives within **6 hours** of the case's last alert, up to **36 hours** in all | heart rate at 21:45 and glucose at 22:30 on 17 Sep 2026 form one case |
| **Version** | the written account of a whole case **at one moment**. Each new alert makes a new version that includes everything known so far. Earlier versions are never changed | version 1 knows only the heart-rate alert; version 2 knows both |

An alert is the *cause* of a version, and a version is the cumulative picture after that alert, but they are not the same thing. On this patient: **287 alerts → 116 cases → 284 versions**. The gap is explained in A9.

## A4. A real example, step by step: the glucose alert of 9 Sep 2026, 22:30

This case has one alert, so it has one version, `fnd_case_2026-09-09T22:30:00+05:30_v1`.

**Step 1. Collect.** The engine gathers the Evidence Engine's record for the alert, what the diary and the Baseline summaries say about the day, and PI's earlier conclusions (all strictly as of 22:30).

**Step 2. List the factors and decide how each may be worded.** The Evidence record had 7 factors. For each, code assigns exactly one *wording class* (the limit on what may be said):

| Factor | Evidence label and flags | Present at the alert? | Wording class | What the text may say |
|---|---|---|---|---|
| meal composition | not supported | exposed | *not mentioned* | nothing (a meal response at the 77th percentile is not unusual enough) |
| medication adherence | **suggestive**, `placebo_fired`, `same_day_unverified` | exposed (a missed dose) | ***present only*** | that it was present, **no link** (the placebo test fired, so the "suggestive" is not trusted) |
| sleep | not supported, `placebo_fired` | exposed (about the 13th percentile of her sleep, so "low for her") | ***present only*** (+ "low for her") | that it was present, no link |
| stress / mood | not supported | not exposed | *not mentioned* | nothing |
| activity | not supported | **not yet available** | *not known yet* | "not known yet" |
| illness symptoms | not supported, `contrary` | not exposed | *not mentioned* | nothing |
| alcohol | insufficient, `small_group` | not exposed | *not mentioned* | nothing |

**Step 3. Decide the mode.** The finding is in **descriptive** mode, not "relationship" mode, because no factor was both *usable for a link* (supported or suggestive, with no placebo problem) and *present*. A descriptive finding says what happened and what was present, and makes no link claim.

**Step 4. Add the extras.**
- **History note:** enough history ("enough"). Nothing needs to be said about it.
- **Not known yet:** "the day's step total" (it only arrives at the end of the day).
- **Seen before (from PI):** PI already holds a long-term note on "missed dose in the last 2 days → dinner glucose peak", status *supported* since 28 Jun 2026. So this finding may say "this has come up before". **A PI status never changes the wording class.** The missed dose stays "present only". PI only allows the extra phrase.

**Step 5. Write the code line.** Code always builds a plain template line from the structure first, so every finding has a text even if no model is available:

> *Glucose was clearly above her usual. Present: missed doses on the same day or the day before, short sleep the night before (low for her). Not known yet: the day's step total.*

**Step 6. The model words it.** The model receives a **numberless view** (no digits, no dates, only what may be mentioned, each with its wording class). It writes a headline and a few sentences, each citing the view items it relies on. For this alert it wrote:

> **Glucose was clearly above her usual in the evening after dinner.**
> 1. Glucose was clearly above her usual in the evening. *(cites the measure)*
> 2. Missed doses on the same day or the day before were present, and this has come up before. *(cites the missed-dose item and PI's earlier conclusion)*
> 3. Short sleep the night before was present and low for her. *(cites the sleep item)*
> 4. The day's step total is not known yet. *(cites the "not known yet" item)*

**Step 7. Check.** Code checks the text against the rules (A6). It passed, so it was stored as the version's text (`source = llm`, `status = ok`).

Notice what the text did **not** say: no link between sleep or the missed dose and the glucose rise (the evidence did not allow it), no number, no cause.

## A5. The wording ladder: how strong may a sentence be?

The wording class is the heart of the engine. In plain words:

| Evidence says | The text may say |
|---|---|
| supported, nothing unusual | "has tended to move together with" the outcome |
| supported, same-day only | the same, **and** it must say "on the same day" (we can't prove which came first) |
| suggestive | "may be linked to" |
| supported or suggestive but the placebo fired | only "was present" (no link) |
| not supported, but the opposite direction was seen | "on days with X, the outcome has tended to be lower" |
| insufficient: too little history | "was present", with "there is not enough history yet" said once |
| event unusually large (percentile ≥ 90) | how unusual this event was, in words ("among the very highest she has had") |
| sensor-artifact check supported | "may be a sensor artifact" |
| exposure not yet available | "not known yet" |
| factor not present / no data | **nothing** |

A sentence is never allowed to be stronger than the **weakest** class it cites. Evidence labels and flags are never altered. The weight tiers (primary, secondary, tertiary) and PI statuses never change a class either.

## A6. How the text is checked

The model's answer must pass fixed checks (the version is `ck-v7`). In plain words:

- **Structure.** A headline of at most 20 words and 2 to 8 sentences, each citing at least one item of the view.
- **No digits, dates, times, month names or counting words** ("one", "twice").
- **No causal words** ("because", "caused", "triggered", "led to", "due to", "affected", "influenced", "contributed", "as a result"...).
- **No copied diary text** (no run of 7 words) and **no internal words** (evidence, label, relationship, factor, supported, case, engine, memory, group, class, exposure, entangled, bundle, pair...).
- **Claim strength matches the class.** "Has tended to move together with" only for the right classes. A same-day point must say "same day" (or "that day" / "on the day").
- **History and not-known-yet sentences**, only when the view says so (completed by code if missing).
- **"This has come up before" / "an early observation"** only in a sentence that also cites the earlier conclusion and the thing it is about.
- **Things in a set are described together;** an often-together set must say they often occur together and that their separate roles cannot be told apart.
- **No clinical terms** (insulin, infection, hypoglycemia...) unless the view itself uses them.
- **A claim must be followed by its outcome** ("may be linked to higher glucose peaks after dinner"), never by another thing or "each other".
- **No repeated phrase** in one sentence.

**Retry and fallback.** If a check fails, the model gets **one retry** with the failures appended. If it fails again, the **code line** is stored as the text (`status = code_line_fallback`). On this patient **9 of 284 versions (3.2%)** ended on the code line.

**Caching.** The model's answer is stored against a hash of the view, the model, the prompt and the checks version. Re-running the same view makes **no new model call**, so a replay is repeatable.

## A7. Descriptive mode and relationship mode

| Mode | When | What the text does |
|---|---|---|
| **descriptive** | no factor is both usable for a link and present | says what was off, what was present (with position words like "low for her"), what is not known yet, and, if relevant, that there isn't enough history to say what usually goes with it |
| **relationship** | at least one factor is supported or suggestive (no placebo trouble), present, and carries a claim class | the above, plus sentences like "X has tended to move together with Y in her history" or "may be linked to" |

On this patient: **165 versions descriptive, 119 relationship**. All 27 cases before **10 December 2025** are descriptive, because the Evidence Engine tests no relationship before then. The first relationship version is **15 Dec 2025**.

Even in descriptive mode, a *very unusual event* (for example a meal response at the 99th percentile) is still stated ("among the very highest she has had after dinners"), because that is a fact about the event, not a link.

## A8. Groups: factors that must be described together

If two factors that both show a link nearly always occur together (the Evidence Engine's `entangled` flag), the text must not present them as two independent explanations. Two kinds of group:

- **Often-together set (entangled):** the text says the items often occur together and their separate roles cannot be told apart.
- **Present-together set (co-exposed):** other usable, present factors are described as a pair ("were both present").

**Real example, the evening of 17 Sep 2026.** The heart-rate alert (21:45) and the glucose alert (22:30) form one case. Version 2's text:

> **Evening heart rate and glucose were clearly above her usual after a festive dinner.**
> - Heart rate was clearly above her usual in the evening.
> - Glucose was clearly above her usual in the evening.
> - A stressed or low-mood period on the same day and short sleep the night before **often occur together and their separate roles cannot be told apart**; both have tended to move together with higher heart rate over the day. *(cites the often-together set and two earlier conclusions)*
> - Missed doses on the same day or the day before and short sleep the night before **may be linked to** higher glucose peaks after dinner. *(a present-together set; mixed strengths use "may be linked to")*
> - The size of this meal's rise was among the very highest she has had within the hour or so after dinners.
> - More activity in the hour before was present and was high for her.
> - A stressed or low-mood period on the same day was present.
> - The day's step total is not known yet.

This is relationship mode (several factors are supported and present), and every claim sentence uses only the wording its class allows. Note that version 1 of this same case (the heart-rate alert alone) did not pass its checks twice and was stored as the code line, which is a real example of the fallback.

## A9. Why 287 alerts became 284 versions

| | Number |
|---|---|
| Alerts from the State Engine | 287 |
| less 8 deferred screen-time alerts (4 are recorded inside a case that already existed, 4 sit outside any case) | − 8 |
| **Counted alerts, each making one version** | **279** |
| plus **5 completions** (a second event for five of the same alerts) | + 5 |
| **Versions** | **284** |
| **Cases** | **116** |

- **Deferred alerts** (the screen-time rule, no clinical evidence base) are recorded but never open a case, never make a version and never move the 6-hour clock.
- **A completion** is not a new alert. Five glucose-below alerts need a sensor-artifact check that uses the reading *after* the alert. At the moment the alert opens, the evidence says "not yet available". About an hour later the check is completed, and that is recorded as one more version of the same case.
- So "287 − 284 = 3 missing" is the wrong reading. The real picture is 287 − 8 + 5.

Alerts per case: 58 cases have 1 alert, 21 have 2, 13 have 3, 11 have 4, and a few have up to 11.

## A10. "This has come up before" (the link to PI)

PI is the long-term memory. When a relationship in this case already has a long-term note, the Findings Engine can read it (strictly as of the version's moment) and tell the text layer how recently it was last seen: this week, in recent weeks, earlier, or never. That is the only thing PI changes. It allows the phrase "this has come up before" or "an early observation", and only in a sentence that also cites the thing it is about. **PI never upgrades a wording class.** The 9 Sep example above shows it: PI knew the missed-dose link was "supported", but today's placebo flag kept the wording at "present only".

## A11. What it deliberately does NOT do

- It computes **no statistics** and shows **no numbers**. All numbers stay in the Evidence store.
- It never changes an Evidence label or flag, and never decides what to believe over time (that is PI).
- It makes **no causal claim**, gives **no advice, diagnosis or prediction**.
- It does not read raw readings or the rulebook files.
- It does not search for new factors. A cause that appears only in the diary can be mentioned as context, but it cannot become a relationship.
- The model never decides *what* may be said, only *how* to phrase what code allowed.

## A12. Honest caveats

- **A "supported" label means "moved together in her history", not mechanism.** The wording is deliberately weak.
- **More than half of supported links are same-day**, so the text says "on the same day" and never "before".
- **Whose symptom?** The diary category doesn't say whose symptom it is. The evidence counts a symptom note about her *father* as an illness exposure. The text layer must read the diary note (it carries "concerning, not her own symptom") to avoid describing her as ill. A structured "subject" field upstream is the proper fix and is parked.
- **A 6-hour gap splits a long crisis into several cases.** Case counts are placeholders: at a 3-hour gap there would be 176 cases, at 12 hours 85.
- **Text can vary between model versions.** The cache makes a replay repeatable, but not identical across model versions.
- **Known text limits:** 13 versions repeat the headline as a sentence or write a sentence twice (reported in `docs/loop_polish_report.md`).
- **The first patient's data is synthetic,** and part of the relationships was built in, so "supported" is not proof the system learned her.

## A13. Where its output goes

Every version goes to **PI** (matched by `finding_id`): first with the code line, then with the final model text swapped in at the week barrier. PI reads the findings by week to build weekly labels and long-term notes. Later versions read PI's notes back as of their time (the loop).

---

# Part B. Technical detail

## B1. Position in the system

```
State Engine hand-offs ─┐
Rulebook packets ───────┤                    ┌─► output/findings_loop_polish.db   (the final output)
Evidence records ───────┼─► FINDINGS ENGINE ─┤      cases · case_handoffs · unattached_handoffs
Diary, memory_v2, PI ───┘   (code layer F1   │      findings · finding_text · finding_llm · meta
(all read-only, as-of)      + text layer F2) └─► PI record_finding(...)  (a no-op when PI is absent)
```

Two layers, built and tested separately:

| Layer | What it does | LLM | Stage |
|---|---|---|---|
| **Code layer** | cases, factor table, mode, wording classes, groups, repeat information, history note, the code line, hand-over to PI | **No** | F1 |
| **Text layer** | headline and sentences from the numberless view, checks, one retry, fallback to the code line | Yes (`openai/gpt-5-mini`, reasoning low, 90 s timeout, SDK retries 0, concurrency 6) | F2 |

With the text layer off, every finding carries the code line (`text.source = code_line`). The text layer must never change the structured layer (the `findings` rows are never touched; the model's result lives in `finding_text` and `finding_llm`).

Method `fe-v0`, phrase book `pb-v0`, library `lib-v0`, final prompt **`p-v5`**, final checks **`ck-v7`**. The engine names no stream, measure, medicine or patient (a test enforces it); a second synthetic patient (`tests/findings_synth.py`) runs on config alone.

```bash
uv run python -m v0_code.findings_engine.run --config config/findings_meera_iyer_v1.yaml --stage F1      # code layer: replay -> output/findings_engine.db
uv run python -m v0_code.findings_engine.run --config ... --stage F1 --rebuild                           # drop the Findings tables first (the text cache survives)
uv run python -m v0_code.findings_engine.run --config ... --gaps 3 6 12                                  # case counts at other gaps, nothing written
uv run python -m v0_code.findings_engine.run_text --sample [--seed N] | --all [--no-network] [--refresh] # text layer
uv run python -m v0_code.loop_engine.run --config config/loop_meera_iyer_v1.yaml                         # the loop with PI, code layer only
uv run python -m v0_code.loop_engine.run_l2 --config config/loop_meera_iyer_v1.yaml                      # the loop with the models (about 14 to 19 min, needs the API key)
```

## B2. Modules (`src/v0_code/findings_engine/` and `intel_common/`)

| Module | Role |
|---|---|
| `config.py`, `inputs.py` | config; read-only inputs from the four upstream databases |
| `loop.py` | the minimal ordered event loop and the case rules; pure (no database, no clock) |
| `factors.py` | the factor table, wording classes, mode, groups, repeat, history note |
| `wording.py` | `classify_relationship` / `classify_event` (the precedence rules) |
| `codeline.py` | the code-written line (Appendix C templates) |
| `context.py` | selects diary entries and state-memory windows (references only) |
| `view.py` | the numberless view for the model; merges identical things |
| `textlayer.py`, `llm.py`, `textclean.py`, `textcheck.py` | prompt, call, cleanup and the checks |
| `storage.py` | own SQLite file; versions are append-only |
| `audit.py`, `report_text.py`, `run.py`, `run_text.py` | as-of audit, reports, CLIs |
| `intel_common/phrasebook.py`, `timeutil.py` | the shared phrase book and time helpers (also used by PI) |

Config: `config/findings_meera_iyer_v1.yaml`, plus the shared, patient-independent `config/findings_phrasebook_v0.yaml`, checked at load against the Evidence library: every exposure, outcome, window tag and event candidate must have a phrase, every wording class a template, and no phrase may contain a digit, an internal word or a counting word.

## B3. Inputs (all read-only, all as-of the version)

| Input | From | Used for |
|---|---|---|
| Hand-offs | State Engine | `handoff_id`, measure, direction, size, `opened_at`, last-meal context |
| Packets | Rulebook Lookup | `matched_rule`, `selected[]`, `status` (only `ok` packets are counted) |
| Event evidence and completions | Evidence Engine | factors (candidate, `support`, `flags`, `event_exposure`, `event_specific`), `overlap`, `not_tested`, `counts` |
| Relationship evidence | Evidence Engine | by id, for the key and phrase only. **No statistic is read into the view** |
| Evidence library | `config/evidence_library_v0.yaml` | exposure risk side, outcome direction, pair ordering (for position words and same-day) |
| Diary | store (`context_events`, stream `diary_context`) | category, time, text and the entry's note (`meta.note`); from the start of the previous local day up to `as_of`; at most 6; moderate or worse first, then most recent |
| State memory | `memory_v2` | `day_<yesterday>`, `week_ENDING_<yesterday>`, the latest month ending before the local date; windows with status `code_line_early` skipped. Only **yesterday's day window, and only if notable,** reaches the model's view |
| PI | PI retrieval, **strictly before** the version's time | long-term memory of each usable relationship, the open week, the last 2 sealed weeks |

Not read: raw readings, statistics, the rulebook CSVs, PI's internal tables.

## B4. Cases and versions (`loop.py`)

- **Order of events:** counted hand-offs by `opened_at` then `handoff_id`; completions by `evaluated_from.end`; at equal times, hand-offs come before completions.
- **Counted** = the packet status is `ok`. A `deferred` or `unmatched` hand-off is recorded in `case_handoffs` with `counted = 0` if a case is open and can take it, otherwise in `unattached_handoffs`. It **never opens a case and never moves the gap clock**.
- **Joining:** a counted hand-off joins the open case if `time − case.last ≤ gap_hours (6)` and `time − case.first ≤ max_span_hours (36)`. Otherwise the old case closes and a new one opens.
- **Ids:** `case_<opened_at of the first hand-off>`; `finding_id = fnd_<case_id>_v<n>`; the case's `local_date` is the local date of its first hand-off (a case can run past midnight).
- **Versions:** one per counted hand-off and one per completion. Versions are append-only; writing a different record under an existing id raises `ImmutableVersionError`.
- **Closing** is a row in `cases` (`closed_at` = last counted hand-off + gap) and **writes no version**. Stored versions keep `provisional: true, closed: false`; a reader asks `cases` whether a version is the last one.
- **No wall-clock time is stored anywhere**, so a re-run produces identical records.

## B5. The code layer (`factors.py`, `wording.py`)

**Factor table.** Factors of all the case's hand-offs are merged: relationship factors by `relationship_key`, presence checks by candidate, other event checks one per hand-off, keyless factors (reasons like `no_definition`) by candidate and reason. Label and flags come from the evidence record with the latest outcome date (flags are the union within it). Exposure state merges as `exposed` > `not_yet_available` > `not_exposed` > `no_data`. Ids `f1, f2...` in rank order of the first hand-off; measures `m1, m2...`. Rank and weight tier are copied through and affect nothing.

**Wording class** (precedence applied in this order):
1. exposure `not_yet_available` → `not_known_yet`
2. exposure not `exposed` → `not_mentioned`
3. relationship: `supported` / `suggestive` with `placebo_fired` → `exposure_only`; `supported` → `asserted` (or `asserted_same_day` with `same_day_unverified`); `suggestive` → `hedged` (or `hedged_same_day`); `not_supported` with `contrary` and no placebo → `contrary_note`, else `exposure_only`; `insufficient` with reason `history` or `small_group` → `exposure_only_history`, any other reason → `not_mentioned`
4. event level: percentile `supported` → `event_unusual`; shape `supported` → `artifact_note`; shape `not_yet_available` → `not_known_yet`; presence → `exposure_only` only if present; pattern `supported` → `exposure_only`; everything else → `not_mentioned`

That is **11 classes**: asserted, asserted_same_day, hedged, hedged_same_day, exposure_only, exposure_only_history, contrary_note, not_mentioned, not_known_yet, event_unusual, artifact_note.

**Mode.** `relationship` only if an exposed relationship factor carries a claim class (`asserted`, `asserted_same_day`, `hedged`, `hedged_same_day`); otherwise `descriptive`. Event statements (`event_unusual`, `artifact_note`, `contrary_note`) are added in either mode.

**Groups.** *Entangled*: connected components of the `entangled` overlap flags (union over the case's hand-offs; `a` and `b` matched to factors by the part of the key before `->`, within the same hand-off's record). Only claim-class relationship factors can be members. *Co-exposed*: the remaining claim-class, exposed factors form one group if there are at least two. Ids: entangled groups first (by first member), then the co-exposed group.

**Position words.** For every exposed factor with a tail percentile, the percentile maps to words using the exposure's risk side **from the Evidence library**: low side 0–5 "among the very lowest she has had", 5–25 "low for her"; high side 95–100 "among the very highest she has had", 75–95 "high for her". Lower edge inclusive, upper exclusive, last band closed at 100. Binarized exposures get none. The event percentile uses the high side plus the phrase book's suffix ("within the hour or so after dinners").

**Repeat information.** For each usable relationship factor: PI's long-term status (`pi_status`, or null) and `seen_before` = `none` / `this_week` (within 7 days) / `recent_weeks` (within 28 days) / `earlier`, from the latest `local_date` among the relationship's entries in all mid-term memories (open week included, written at or before `as_of`) and its long-term `last_seen`, **excluding the current case**. A PI status never changes a class, mode or group (property test).

**History note.** Over the case's keyed relationship factors: none `insufficient(history)` → `enough`; more than half → `not_enough_history_yet`; otherwise `enough_for_some`. **Not-known-yet:** the plain-words list of exposures whose state is `not_yet_available`.

**Code line.** One template per mode (relationship, descriptive, event-level only), built with the same phrases. Presence-check facts that are static (for example "her thyroid medicine") stay in the structured layer but are left out of the code line and the view. Co-exposed sentence: "<A> and <B> were both present."

## B6. The text layer

**The view** (numberless, built by `view.py`): `situation` (mode as `may_discuss_links` or `describe_only`, measures with a clause and strength per direction, part of day from each measure's own `opened_at`, meal context in words), `things` (every factor except `not_mentioned`, `not_known_yet` and static presence checks: id, name, outcome phrase, wording, position words, set id; things with identical content are **merged** into one carrying all member ids), `sets`, `not_known_yet` (`n1`), `history` (`h1`), `diary` (id, category, when, part of day, text, note; entries that back an exposed point come first with `backs`), `earlier_summaries` (yesterday's window only, only if notable, and none in a version with an artifact point) and `earlier_conclusions` (`p<k>`: about, state word, text, seen-before band). No key or value may contain an internal word (a test scans every view, also the 284 real ones), and the stored record keeps its own internal names.

**Output:** `{"headline": "...", "sentences": [{"text": "...", "refs": ["f1", "g1", "d1", ...]}]}`. Headline at most 20 words, 2 to 8 sentences, each citing at least one view id. A set id counts as citing all its members.

**Prompt** `p-v5` is Appendix B of the spec (19 rules). Highlights: wording per class (rule 3), no causal verbs (4), things in a set are described together (5), history said once (6), diary paraphrased and "whose symptom" respected (7), earlier conclusions only beside the thing they are about (8), no advice (9), no view ids in text (11), exact phrases (12), mixed strengths use "may be linked to" (14), no clinical terms the view lacks (15), claim followed by its outcome (17), cite a merged thing by its `id` (19).

**Checks** (`textcheck.py`, `ck-v7`, "do not add other checks"):

| # | Check |
|---|---|
| 1 | structure (valid JSON, headline ≤ 20 words, 2–8 sentences, each with a ref) |
| 2 | every ref exists in the view |
| 3 | no digits, dates, clock words, month names, counting words, view ids in text |
| 4 | no causal wording (stems: caus*, trigger*, led to, due to, because, explains, driven by, responsible, affect*, impact*, influenc*, contribut*, as a result, thanks to ...) |
| 5 | no copied diary text (run of 7 words), no internal words, no underscore token |
| 6 | claim level matches the cited classes; same-day classes say "same day" / "same-day" / "that day" / "on the day"; "moved together" forms count as the same claim |
| 7 | history and not-known-yet sentences (**completed by code**, not a failure) |
| 8 | recurrence wording only with an earlier conclusion; an earlier summary never beside a claim or an artifact |
| 9 | an often-together set is described as such |
| 10 | at most one sentence cites an earlier summary |
| 11 | clinical terms only if the view has them |
| 12 | the object of a claim is an outcome, never another thing or "each other" |
| 13 | no view phrase twice in a sentence (position phrases exempt) |
| 14 | a claim phrase is followed by an outcome phrase |
| 15 | a sentence citing an earlier conclusion also cites the thing it is about |
| 16 | no `h1` sentence when the history note is "enough" |

**Cleanup before checks:** capitalise headline and sentences, finish a sentence with a full stop (headline untouched), lower-case after "says", strip quotes around the view's own phrases. `text.raw` and `text.cleaned` are kept.

**Retry, fallback, cache.** One retry with the failed checks appended, then the code line (`status = code_line_fallback`). A failed call (timeout or API error) counts as a failed attempt. The cache key is the hash of the view plus the model, effort, retries, length limits, copy window, prompts and `CHECKS_VERSION`, so a changed prompt is never served a stale answer. A saved text is **re-judged from the model's raw answer** under the current checks and kept for a view whose hash is unchanged if it still passes; otherwise the model is asked again. A new fallback never replaces an accepted older answer. A full run goes in waves of 12, saves after each wave, resumes from the store, and stops after 40 new versions if more than 45% fail their first attempt or more than 10% of calls end in a call error.

## B7. The loop with PI and the models (stages L1 and L2)

- The Findings event loop is the clock. In the loop, each version is put into PI's open week at once with its **code line**; at each **week barrier** (when an event passes a week end, and at the end) the week's texts are written (concurrency 6), PI's entries get the final text (`replace_entry_text`, open weeks only, only the text changes), PI's weekly job runs, and the situation lines of the memory versions it wrote are generated.
- **Strict PI reads:** only what was written strictly before the version's time (an inclusive read made a rerun read something the first run did not). Every read is logged.
- **Regression guarantees (tested):** every version equals the code-only (F1) version except `repeat` and `refs.pi_memories`; PI's tables are byte-identical to a code-only replay; as-of audits and the call-ordering audit are clean; a zero-call rerun is identical.
- The mid-term headlines are **not** shown to the Findings model (they would carry other cases' claim wording into this case, make a week's versions depend on each other, and change every view hash). A "same measure within seven days" item is the parked way to give that context.
- Polish round (`p-v5` / `ck-v7`, amendment AA): same-day wording accepts "that day" / "on the day"; identical things are merged in the view; check 15 and check 16 added; saved texts are re-judged and kept where they still pass.

## B8. Storage (`output/findings_loop_polish.db`)

| Table | Key | Holds |
|---|---|---|
| `cases` | `case_id` | `local_date`, `opened_at`, `last_handoff_at`, `closed_at`, `status`, `n_counted`, `n_recorded`, `n_versions` |
| `case_handoffs` | `(case_id, handoff_id)` | `joined_at`, `counted`, `packet_status` |
| `unattached_handoffs` | `handoff_id` | hand-offs outside any case |
| `findings` | `finding_id` | the structured record (`record_json`), `case_id`, `version`, `as_of`, `mode`, `provisional`, `closed`, `text_source`, `status`. **Append-only** |
| `finding_text` | `finding_id` | the text layer's result: `text_json`, `text_source`, `status`, `cache_key`, `view_hash`, prompt, checks and settings versions, `from_prompt` |
| `finding_llm` | `finding_id` | `view_hash`, `llm_raw`, `usage_json`, `checks_json` (one list entry per attempt) |
| `meta` | `key` | versions (`prompt_version p-v5`, `checks_version ck-v7`, `phrasebook_version`, `library_version`, ...) and the call log |

**The finding record holds no statistics.** Evidence is referenced by id. Keys: `finding_id`, `case_id`, `version`, `provisional`, `closed`, `as_of`, `local_date`, `handoff_ids`, `evidence_ids`, `completion_ids`, `mode`, `measures` (`measure_id`, `measure`, `direction`, `strength`, `opened_at`), `factors` (`factor_id`, `candidate`, `kind`, `relationship_key`, `label`, `flags`, `exposure`, `position`, `wording_class`, `group`, `handoff_ids`, `insufficient_reason`), `groups`, `history_note`, `not_known_yet`, `repeat`, `refs` (`diary`, `state_memory`, `pi_memories`), `text`, `checks`, `status`.

## B9. Results on this patient

| | Number |
|---|---|
| Alerts in / counted / completions | 287 / 279 / 5 |
| **Cases / versions** | **116 / 284** |
| Versions descriptive / relationship | 165 / 119 (by each case's last version: 67 / 49) |
| First relationship version | 15 Dec 2025 (all 27 cases before 10 Dec are descriptive) |
| Factor entries across the 284 versions | 3,126 |
| Texts: model-written and checked (`source = llm`, `ok`) | 275 |
| Texts: **code-line fallbacks** | **9 (3.2%)**; acceptance was at most 11 (4%) |
| History note: enough / not enough yet | 204 / 80 (all 80 before December) |
| Co-exposed groups marked | 44 |
| Measures per version | 180 one, 77 two, 16 three, 11 four |

Wording classes across the 3,126 factor entries: not mentioned 1,605; not known yet 560; present with little history 403; present, no link 320; stated as a pattern 105; same-day pattern 76; unusual event 42; may be linked 8; possible artifact 3; contrary note 2; may be linked, same day 2.

Last polish run (`docs/loop_polish_report.md`): the model wrote 151 texts, **29 of which failed their first attempt** (repeated phrase 12, claim level 8, copied diary 5, causal 3, structure 3, counting 2); 131 texts were kept as they were; PI situations lines: 97 regenerated, 30 reused, 47 with no call. Known text limit: 13 versions repeat the headline as a sentence (10) or write a sentence twice (3). The older summary in `understand/how_the_numbers_flow.md` §7 lists 43 first-attempt failures for the same run; I did not reconcile the two figures.

## B10. Gotchas and decisions to check before changing anything

1. **Never change evidence labels or flags**, and never let a PI status, weight tier or rank change a wording class, mode or group (property tests).
2. **The code line is the safety net.** A version is never left without a text. If the model fails twice, the code line is stored.
3. **Versions are append-only.** Do not "fix" a stored version. A `--rebuild` of the code layer drops the Findings tables but keeps the text cache.
4. **Deferred and unmatched hand-offs** never open a case, never make a version and never move the gap clock. They are still recorded.
5. **Case gap and span (6 h, 36 h) are placeholders.** Re-run with `--gaps` to see how counts change (176 / 116 / 85 at 3 / 6 / 12 h).
6. **Same-day classes need "same day" wording**, because the evidence cannot show which came first. Check 6 enforces it.
7. **No statistic and no digit in any text or view** (property). Diary text may contain digits, but the model must not repeat them.
8. **Whose symptom** is a known upstream limit. The diary note must be read; a structured `subject` field is parked.
9. **Context reads are strictly as-of.** Diary up to `as_of`, state memory windows that ended before the local date, PI strictly before the version. Run `audit.py` after any change.
10. **Prompt and checks are versioned.** A text produced under an older prompt is kept only if it still passes the current checks and the view is unchanged.
11. **The model's answer costs money.** The loop with the models used about 480,000 tokens in and 485,000 out in the stored call log. Always use the cache and `--no-network` for dry runs.
12. **Tests:** `tests/test_findings_cases.py`, `test_findings_factors.py`, `test_findings_store.py`, `test_findings_wording.py`, `test_findings_text*.py` (v1 to v5), `test_phrasebook.py`, `test_loop_engine.py`, `test_loop_l2.py`, `test_loop_real.py`.

## B11. Quick checks (read-only)

```bash
sqlite3 -readonly output/findings_loop_polish.db \
  "select mode, count(*) from findings group by 1;"                                  # descriptive 165 / relationship 119

sqlite3 -readonly output/findings_loop_polish.db \
  "select text_source, status, count(*) from finding_text group by 1,2;"             # llm ok 275 / code_line fallback 9

sqlite3 -readonly output/findings_loop_polish.db \
  "select case_id, n_counted, n_versions from cases order by n_versions desc limit 5;"

sqlite3 -readonly output/findings_loop_polish.db \
  "select text_json from finding_text where finding_id='fnd_case_2026-09-09T22:30:00+05:30_v1';"
```

Dashboard pages: `#/stage/findings`, `#/cases`, `#/case/<id>`. Reports: `docs/findings_f1_report.md`, `docs/findings_f2_full_report*.md`, `docs/loop_l1_report.md`, `docs/loop_l2_report.md`, `docs/loop_polish_report.md`.
