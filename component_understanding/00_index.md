# Component guides: index

One guide per component. Each has **Part A** (plain words, with real examples from the patient, readable without opening code) and **Part B** (technical detail: modules, inputs, storage, results, gotchas, quick checks).

For the folder-by-folder map of the whole repo see `understand/repo_map.md`. For the numbers flowing through every step see `understand/how_the_numbers_flow.md`.

## The chain, in one line each

| # | Guide | In one line | Main numbers on this patient |
|---|---|---|---|
| 1 | [Plausibility filter and threshold evaluator](01_plausibility_filter_and_threshold_evaluator.md) | Rejects impossible readings, then gives every other reading a status against a reference range. | 77,797 readings in, 5 rejected, 44,469 given a status |
| 2 | [Short-range linker and personal data store](02_short_range_linker_and_personal_data_store.md) | Pairs high or low glucose with what happened nearby; stores everything in SQLite. | 138,118 pairings, 182,587 stored rows |
| 3 | [Baseline engine](03_baseline_engine.md) | Builds day, week and month windows, her usual, and a short model-worded gist. | 710 windows, 590 gists |
| 4 | [State engine](04_state_engine.md) | Every 15 minutes compares her latest reading with her usual and raises alerts. | 33,792 ticks, 565 items, 287 hand-offs |
| 5 | [Rulebook lookup](05_rulebook_lookup.md) | Turns each alert into a checklist of factors worth testing. | 10 rules, 287 packets |
| 6 | [Evidence engine](06_evidence_engine.md) | Tests each factor on her own history and labels it (supported, suggestive, not supported, insufficient). | 63 relationships x 352 days = 22,148 records |
| 7 | [Findings engine](07_findings_engine.md) | Groups alerts into cases and writes a careful, checked text for each version. | 116 cases, 284 versions |
| 8 | [PI (findings memory)](08_pi_findings_memory.md) | Keeps weekly notes and one long-term note per link, with a status decided by counting weeks. | 51 weeks, 29 long-term memories |

## Reading order

1. Read Part A of guides 1 to 8 in order for the full story.
2. Read Part B of the component you are about to change.
3. Then read the matching section of `CLAUDE.md` (decisions to check before changing anything) and the spec in `task/`.

## Three rules that hold across all components

- **Code decides every fact.** A model only words what the code decided, and only in three places: the Baseline gist (3), the Findings text (7) and the PI situations line (8).
- **Nothing looks ahead.** Every read is "as of" the moment of the thing being decided.
- **Records are append-only** in Findings and PI; a new version is added, never an edit.

## Known open points

- File 03 has no "known limits / parked items" section yet (the cleanup audit lists them in `output/baseline_v2_cleanup_audit.md`).
- Guide 7 notes that two sources disagree on the polish run's first-attempt failures (29 in `docs/loop_polish_report.md`, 43 in `understand/how_the_numbers_flow.md` section 7). The report's figure is used.
