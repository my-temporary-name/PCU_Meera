# Intelligence Layer: how Evidence Engine, Findings Engine and PI work together

## 0. Status and how to use this document

**What exists today** (built, tested, not yet committed): the Plausibility Filter, Threshold Evaluator, Short-Range Linker and Personal Data Store; Baseline Engine v2 (`memory_v2`); State Engine (hand-offs); Rulebook Lookup (packets, with hourly steps now in the store).

**What this document covers:** how three new components fit together so that nothing is duplicated, nothing is missing and nothing is over-built: **Evidence Engine**, **Findings Engine** and **PI** (the Personalized Intelligence memory). It states our requirements, who owns what, what each one reads and writes, the timing, and a worked example.

**How it is being built:** one stage at a time. Each stage is built from its spec, run over the whole replay, and checked before the next one starts. The Evidence Engine is built and has been scored against the ground-truth manifest. The Findings Engine and PI specs are written together (`findings_engine_spec.md`, `pi_spec.md`), because they run as a loop, and are built in stages: Findings code layer, Findings text layer, PI code layer with the replay driver, PI text layer, then the full loop.

Everything marked *illustrative* below uses real numbers from Meera's data computed in my own prototype scripts. None of it is engine output.

---

## 1. The picture

```
State Engine: deviation item opens (2 readings in a row) --> hand-off
        |
Rulebook Lookup --> packet (what to check; rules only)
        |
EVIDENCE ENGINE --> evidence store   [all statistics, saved once, reused]
        |                    |
        v                    | (by evidence_id)
FINDINGS ENGINE  <-----------+
   reads: evidence + diary text + state memory (memory_v2) + PI memories
   writes: finding = structured part (code) + text part (LLM, no digits)
        |
        v
PI   mid-term memory (a week of findings)  --weekly LLM update-->  long-term memory (per relationship)
        |
        +--> read by Findings Engine next time (the loop)

NARRATIVE LAYER (later): reads evidence + findings + PI + state memory and writes the final answer
```

| Component | One-line job | Works with | LLM? |
|---|---|---|---|
| **Evidence Engine** | Does this factor show up in her own history? | Numbers | No |
| **Findings Engine** | What does the evidence mean for this event? Write it down. | Labels and text | Yes, wording only |
| **PI** | Remember what we have concluded about her, week by week | Findings and evidence references | Yes, weekly wording update only |

---

## 2. Our requirements

1. **Evidence Engine outputs numbers; Findings Engine outputs text.** PI builds memories from Findings output. The Narrative Layer uses Evidence and Findings (and PI and the state memory) to compose the final answer.
2. **Evidence is saved once and reused.** Relationship statistics are computed once a day and reused by every hand-off that day. They are kept as a history.
3. **Findings and PI are in a loop.** Everything Findings produces is saved into PI as mid-term and long-term memory. PI memories are an input to Findings the next time.
4. **Mid-term memory** is what Findings produced, accumulated for a week. **Long-term memory** is updated every week by an LLM that reads the mid-term memory.
5. **PI uses an LLM** for that weekly update. In V0, PI only creates and updates memories. It does **not** reorder or rewrite the rulebook.
6. **LLMs write text with no numbers.** Numbers live only in the evidence store.
7. **Real time.** When an item opens (two readings in a row for glucose and heart rate; one reading for daily measures), the chain runs at once: packet, evidence, finding. Nothing waits for the end of the day. Only PI's weekly update is slower.
8. **Names:** the baseline's memories are **state memory** (`memory_v2`: how her numbers behaved). PI's memories are **findings memory** (what we concluded about why). PI never restates facts the state memory already holds.
9. **The status of a relationship is decided by PI's code**, not by an LLM and not by one event.
10. **Association language only.** No causal claims anywhere.
11. **One component at a time,** each checked on the full replay before the next starts.
12. **Generic.** No patient-specific values in code.
13. **Keep it small.** Section 13 lists what V0 builds and what it skips.

---

## 3. Who owns what

| Task | Evidence | Findings | PI |
|---|---|---|---|
| Fetch her history and compute statistics | owns | | |
| Label each factor (`supported`, `suggestive`, `not_supported`, `insufficient`) by a fixed rule | owns | | |
| Overlap between factors, placebo controls | owns | | |
| Whether this event was exposed to a factor | owns | | |
| Read the diary text | | owns | |
| Group hand-offs into cases | | owns | |
| Combine factors into one explanation, write the wording | | owns | |
| Pass the evidence labels through unchanged | | owns | |
| Store findings as mid-term memory | | | owns |
| Decide each relationship's status (`candidate`, `supported`, `weakened`, `retracted`) | | | owns (code) |
| Update long-term wording each week | | | owns (LLM, checked by code) |
| Retrieve memories as of a time | | | owns |

**Never-do list (this is what prevents overlap):**
- Evidence never reads PI, the diary text or state memory, and never writes words.
- Findings never computes statistics, never changes a label, never decides a status, and never restates what the state memory already says.
- PI never computes statistics, never changes wording except in the weekly update, and never reads the diary.
- Only Findings writes to PI. PI is the only place beliefs accumulate. Nothing else keeps its own copy.

---

## 4. What goes in and what comes out

### Evidence Engine

| | |
|---|---|
| **In** | The packet (which factors, how far back, how many). The hand-off. Her history from the store, as of the event. The State Engine's availability rules and the baseline's cleaning rule. |
| **Out** | **Relationship evidence** (daily, cached): statistics for each relationship. **Event evidence** (per hand-off): each factor's label, whether the event was exposed, any event-specific statistic, overlap, and what was not tested. Details: `evidence_engine_spec.md`. |

### Findings Engine

| | |
|---|---|
| **In** | The case's event evidence records. The diary entries and context around the case. The state memory for those dates. **PI memories** for the relationships touched (what we already believe about her). |
| **Out** | A **finding** with a structured part (set by code) and a text part (LLM, no digits). Its structured part is what PI stores. |

### PI

| | |
|---|---|
| **In** | Findings (structured and text). Evidence references, which PI's code resolves in the evidence store to decide statuses. |
| **Out** | Mid-term memories (a week of findings), long-term memories (one per relationship), and retrieval for Findings: "what do we already believe about this relationship, as of this time". |

---

## 5. The objects, and where they live

| Object | Made by | Stored in | Key | Read by |
|---|---|---|---|---|
| Hand-off | State Engine | `state_engine.db` | `handoff_id` | Rulebook, Evidence, Findings |
| Packet | Rulebook Lookup | `rulebook_lookup.db` | `packet_id` | Evidence |
| Relationship evidence | Evidence | `evidence_engine.db` | `rel`, key, date and method version joined by vertical bars | Evidence, Findings, PI (code), Narrative |
| Event evidence | Evidence | `evidence_engine.db` | `ev_<handoff_id>` | Findings, Narrative |
| Case | Findings | Findings' store | `case_<first hand-off time>` | Findings, PI |
| Finding (versioned) | Findings | Findings' store | `fnd_<case>_v<n>` | PI, Narrative |
| Mid-term memory | PI | PI's store | `pi_mid_<year>-W<week>` | Findings, Narrative |
| Long-term memory | PI | PI's store | `pi_long_<relationship_key>` | Findings, Narrative |
| State memory | Baseline Engine v2 | `memory_v2` | `window_id` | Findings, Narrative |

Each of the new components gets its own database file, as the State Engine and Rulebook Lookup did.

---

## 6. Timing: three clocks

| Clock | When | What runs |
|---|---|---|
| **Event** | Each time a hand-off is written (real time) | Packet, then event evidence, then the case is opened or extended, then Findings writes a **provisional** finding |
| **Daily** | Start of each local day | Evidence refreshes every relationship as of that day (from completed earlier days) |
| **Weekly** | End of each calendar week (Monday to Sunday by default) | PI assembles the mid-term memory, updates relationship statuses in code, and the LLM updates long-term wording for relationships touched that week |

**Replay driver.** Meera's data is historical, so a small deterministic driver steps through time in order: for each day, run the daily refresh; for each hand-off in time order, run packet, evidence and Findings; at each week end, run PI. Every read is as-of that moment. PI memories carry a `written_at` on the replay clock, and reads only see memories written before the event. Without this, a September memory could influence an October finding.

---

## 7. Cases

Hand-offs cluster. On Meera's year, the 287 hand-offs fall on only 93 days. The median is 2 a day, the maximum is 11, 79% sit on days with three or more, and on 40 of the 93 days two or more measures fire. If Findings and PI worked per hand-off, one bad day would produce about eleven near-duplicate findings and PI's counters would count one situation eleven times.

- A **case** opens at the first hand-off and stays open while later hand-offs arrive within a gap of `case_gap_hours` (default 6; on the first patient's 287 hand-offs this gives 116 cases from the 279 counted hand-offs (the 8 deferred ones never open a case), at most three starting a day, the longest spanning 28 hours). A case is not one local day, because a day is only known at midnight.
- When a hand-off joins an open case, Findings writes a new **version** of the finding. Versions are kept. The latest version is what PI reads at week end.
- PI counts **case-days**: distinct local dates on which a relationship was tested in a case, and those on which the factor was exposed. It never counts hand-offs.
- Evidence stays per hand-off, because the relationship evidence is cached daily anyway.

---

## 8. Labels, statuses and wording

**Evidence labels** describe one moment: `supported`, `suggestive`, `not_supported`, `insufficient` (and `not_applicable` for presence checks).

**PI statuses** describe what we believe about a relationship over time: `candidate`, `supported`, `weakened`, `retracted`.

PI's code decides statuses weekly from the evidence history, with these defaults (placeholders, in config):
- A relationship's **week label** comes from its seven daily labels: `supported` if at least five days were `supported`; `suggestive` if at least five days were supported or suggestive; `insufficient` if at least five days were insufficient; otherwise `not_supported`.
- `candidate` to `supported`: the week label is `supported` two weeks in a row.
- `supported` to `weakened`: the week label is `not_supported` two weeks in a row.
- `weakened` to `supported`: `supported` again two weeks in a row.
- `weakened` to `retracted`: `not_supported` for six further weeks, or the flag `contrary` for four weeks in a row.
- `insufficient` and `suggestive` weeks neither promote nor demote.

Wording the LLMs must use, by label or status:

| Label or status | Allowed wording |
|---|---|
| `supported` | "tends to", "has been linked to" |
| `suggestive` | "may be linked to" |
| `not_supported` | not asserted; at most "no clear link in her history" |
| `insufficient` | "not enough history yet" |
| flag `contrary` | "was lower on those days" (association only) |
| flag `same_day_unverified` | "occurred on the same day"; never "before" |
| `not_yet_available` | "not known yet" |
| PI status `candidate` | "early observation" |
| PI status `weakened` | "no longer clearly seen" |

---

## 9. The two LLM steps

### Findings Engine

- **Provisional output at event time.** It uses only what is available when the item opens, and says what is not known yet.
- **The LLM sees no numbers.** It sees labels, exposure states, position words ("very low end of her sleep"), the diary entries, the state memory headlines and the PI memory text and status. Code attaches the numbers later (the Narrative Layer fills them in from the evidence store).
- **Output has two layers.** The structured part is set by code: factors, labels, relationship keys, evidence IDs, diary references. The text part is written by the LLM: a headline and a few short sentences.
- **Checks on the text (small):** no digits, no dates, no copied diary phrases of five or more words, no causal wording, wording matches the label table in section 8, and every sentence names the relationship or diary entry it relies on. A failure keeps a code-written line instead.

### PI weekly update

- **Mid-term memory (code):** at week end, assemble the latest version of each finding of the week, with its case IDs and relationship keys. No LLM.
- **Statuses (code):** update as in section 8, reading the relationship evidence history by ID.
- **Long-term update (LLM):** for each relationship touched that week, the LLM sees the previous long-term text, the week's finding texts for that relationship and the new status, and writes updated wording. It sees no digits.
- **Checks:** no digits; wording matches the status; each sentence ties to a relationship key; old text versions are kept; and every few weeks the text is regenerated from the structured data to stop drift. A failure keeps the previous text.
- **Only relationships touched that week** are rewritten. The others keep their wording.

---

## 10. The eight fixes and where each one lives

| # | Fix | Where it lives |
|---|---|---|
| 1 | Cases, not hand-offs, are the unit | Findings opens and extends cases (section 7). PI counts case-days. |
| 2 | Honest statistics: detrending, circular-shift permutation, correction across the family, minimum group sizes, placebos, continuous exposures where available | Evidence Engine spec, section 7 |
| 3 | One availability rule | Evidence uses the State Engine's `available_at`; `not_yet_available` is its own state |
| 4 | A driver that steps through time | Replay driver (section 6); every read is as-of |
| 5 | Status is driven by the relationship's evidence history, not by single events | PI's code (section 8) |
| 6 | Guardrails on PI's LLM | Section 9 |
| 7 | A ground-truth manifest and a scoring step | A separate task after Evidence Engine runs; the manifest is not written yet |
| 8 | Exposure and outcome definitions live in a static config derived from the tables in the Evidence spec (sections 6 and Appendix A), checked against the rulebook at load. Nothing generates them at run time. | Evidence Engine spec |

---

## 11. Worked example (illustrative)

**22:30, Sept 17.** The glucose item opens (185.0, clinical status high). The packet selects seven factors.

**Evidence record (numbers stay in the evidence store):** meal `supported` (the first-hour peak is at the 99th percentile of her earlier dinners); missed dose in the last 2 days and previous night's sleep `supported` (in an illustration that corrects for five tests only; with the real family they would likely be `suggestive`); mood and steps `not_supported`; alcohol `insufficient`. The event was exposed to the meal, the missed doses, the short sleep and the evening mood. Steps are `not_yet_available`.

**Case.** Opens at 22:30. Findings writes version 1 (provisional).

```json
{
  "finding_id": "fnd_case_2026-09-17T22:30_v1",
  "case_id": "case_2026-09-17T22:30",
  "version": 1,
  "provisional": true,
  "handoff_ids": [
    "handoff_glucose_2026-09-17T22:30"
  ],
  "evidence_ids": [
    "ev_handoff_glucose_2026-09-17T22:30"
  ],
  "structured": {
    "factors": [
      {
        "candidate": "meal_composition",
        "relationship_key": null,
        "label": "supported",
        "event_exposure": "exposed"
      },
      {
        "candidate": "medication_adherence",
        "relationship_key": "missed_dose@2d->post_meal_peak:dinner",
        "label": "supported",
        "flags": [
          "same_day_unverified"
        ],
        "event_exposure": "exposed"
      },
      {
        "candidate": "sleep",
        "relationship_key": "sleep_hours@prev_night->post_meal_peak:dinner",
        "label": "supported",
        "flags": [],
        "event_exposure": "exposed"
      },
      {
        "candidate": "activity",
        "relationship_key": "steps_total@1d->post_meal_peak:dinner",
        "label": "not_supported",
        "flags": [
          "same_day_unverified"
        ],
        "event_exposure": "not_yet_available"
      }
    ],
    "diary_refs": [
      "ctx:2026-09-17#1",
      "ctx:2026-09-17#2"
    ],
    "state_memory_dates": [
      "2026-09-16"
    ],
    "pi_memories_read": []
  },
  "text": {
    "headline": "Glucose rose well above her usual after a festive dinner, on a day with missed doses and a very short night.",
    "sentences": [
      "The rise in the first hour after this dinner was among the highest she has had after dinners.",
      "Missed doses and short sleep have each been linked to higher dinner peaks in her history, and both were present today.",
      "The diary describes a deadline day with minimal proper meals."
    ]
  }
}
```

**22:45 to 23:15.** If another hand-off joined (for example heart rate), Findings would write version 2 of the same case.

**End of the week (Sunday 23:59).** PI assembles the mid-term memory and creates a long-term memory for each relationship touched. The status starts as `candidate` because a relationship needs two supported weeks in a row.

```json
{
  "memory_id": "pi_mid_2026-W38",
  "tier": "mid_term",
  "week": {
    "start": "2026-09-14",
    "end": "2026-09-20"
  },
  "written_at": "2026-09-20T23:59:00+05:30 (replay clock)",
  "case_ids": [
    "case_2026-09-17T22:30"
  ],
  "relationship_keys": [
    "missed_dose@2d->post_meal_peak:dinner",
    "sleep_hours@prev_night->post_meal_peak:dinner"
  ],
  "findings": [
    {
      "finding_id": "fnd_case_2026-09-17T22:30_v1",
      "headline": "Glucose rose well above her usual after a festive dinner, on a day with missed doses and a very short night.",
      "sentences": [
        "The rise in the first hour after this dinner was among the highest she has had after dinners.",
        "Missed doses and short sleep have each been linked to higher dinner peaks in her history, and both were present today.",
        "The diary describes a deadline day with minimal proper meals."
      ]
    }
  ]
}
```

```json
{
  "memory_id": "pi_long_missed_dose@2d->post_meal_peak:dinner",
  "tier": "long_term",
  "relationship_key": "missed_dose@2d->post_meal_peak:dinner",
  "status": "candidate",
  "status_since": "2026-09-20",
  "weekly_labels": [
    {
      "week": "2026-W38",
      "label": "supported"
    }
  ],
  "flags": [
    "same_day_unverified"
  ],
  "counters": {
    "case_days": 1,
    "exposed_case_days": 1,
    "first_seen": "2026-09-17",
    "last_seen": "2026-09-17"
  },
  "evidence_refs": [
    "rel|missed_dose@2d->post_meal_peak:dinner|2026-09-17|ev-v0"
  ],
  "text": "Missed doses in recent days have been linked to higher dinner peaks in her history. This is an early observation.",
  "text_version": 1,
  "written_at": "2026-09-20T23:59:00+05:30 (replay clock)"
}
```

**Next time.** On a later evening with a similar glucose rise, Findings reads these memories. It can say this is not the first time in recent weeks, and it keeps the wording at "early observation" until PI's status changes. Evidence is computed fresh from her history; PI's beliefs never feed back into the statistics.

---

## 12. V0 scope

**Build**
- Evidence Engine: relationship and event evidence, daily cache, labels, placebo and overlap checks.
- Findings Engine: cases, versioned findings, the structured and text layers.
- PI: weekly mid-term bundle, status lifecycle in code, weekly LLM long-term update, retrieval as-of.
- A replay driver.

**Skip**
- Pattern Discovery and any new factors beyond the rulebook.
- The GI Aggregator (needs many patients).
- Embedding-based similarity search.
- A Knowledge Graph interface.
- PI reordering or rewriting the rulebook.
- The Narrative Layer (a later component; it will use the references defined here).
- Hourly steps as a State Engine measure.

---

## 13. What to expect

- **Many relationships will be `insufficient` or `suggestive`.** After detrending, effects on Meera's data are small, and a daily family of about 50 tests needs strong evidence. In Oct to Dec almost nothing is testable. Alcohol, weather and travel entries (6, 4 and 2 days in her year) can never be learned. This is a result of the data, not a defect. Do not tune thresholds to produce findings.
- **Slow trends fake part of every link.** Detrending halved the apparent effects on the examples I tried.
- **V0 can only confirm or weaken the rulebook's relationships.** A cause that appears only in the diary (such as a family member's hospitalization) can be mentioned as context by Findings but cannot become a finding, because there is no evidence for it.
- **The data was built to contain these relationships.** The engine will find what the generator put in, so a good-looking result on Meera is not proof that it learns a real person. The ground-truth scoring step and the placebo controls exist to keep us honest.
- **Date-only records cannot be ordered within a day.** Relationships that depend on them carry `same_day_unverified`.
- **Everything built so far is uncommitted.**

---

## 14. Build order and gates

| Step | Build | Gate (what must be true before the next step) |
|---|---|---|
| 1 | **Evidence Engine** | Done. Runs deterministically and read-only; scored against the manifest (formulas found with the right sign, placebo rate 8.6%). Labels mean "moved together in her history". |
| F1 | **Findings code layer** (`findings_engine_spec.md`, sections 5 to 7) | Over the full replay: the expected number of cases and versions, no duplicates, every factor traces to an evidence id, wording classes follow the table, no numbers in any text |
| F2 | **Findings text layer** (section 8) | Checks pass; the code line is used when they fail; the text never changes the structured layer. PI is empty at this stage. |
| P1 | **PI code layer and the replay driver** (`pi_spec.md`, sections 6, 7, 9, 11) | Statuses move only on persistence; as-of reads never see the future; weeks seal and never change |
| P2 | **PI text layer** (section 8) | Text stays tied to its relationship and status; no digits; a failed check keeps the previous text |
| L | **The loop** | One end-to-end run over the year. Hand-read several weeks, including the hospitalization week (descriptive mode), the week of 17 September, and a week with no findings. Check that nothing PI says changes an evidence label. |

Between steps: no design changes mid-step; bugs are fixed with a test that failed first; everything else goes on a parked list.

---

## 15. Open decisions (defaults, all in config)

| Decision | Default |
|---|---|
| Case gap | 6 hours (116 cases on the first patient; compare 3 hours: 176, 12 hours: 85) |
| Week boundary | Calendar weeks, Monday to Sunday, update at Sunday 23:59 local |
| Status promotion | Two consecutive supported weeks; demotion after two consecutive not-supported weeks |
| PI regeneration from structured data | Every four weeks |
| LLM and settings | Same provider pattern as the baseline gist: low reasoning effort, 90-second timeout, retry once, then a code-written line |
| Evidence thresholds | Placeholders in `evidence_engine_spec.md` section 10 |