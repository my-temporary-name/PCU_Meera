# Dashboard v2: plan and to-do (working document; check items off as they are done)

## 0. What we are building (my understanding, agreed before any code)

- A **new folder `dashboard_v2/`**, a copy of `dashboard/`. **`dashboard/` stays exactly as it is** (the GitHub Pages workflow `.github/workflows` deploys it; I do not touch it, the workflow, or its `data/`).
- v2 **opens on the patient timeline** exactly as v1 does (Full year, Months, Weeks, Episodes, Glucose events, Baselines, Labs & body, Data sources). **Nothing from v1 is removed.**
- v2 adds a **pipeline mode** (a second section in the sidebar): for each component, its **input and its output**, and the **correlation between them**, so any final sentence can be traced back to the readings that caused it.
- Same theme (colours, fonts, ECharts, vanilla ES modules, hash router, no build step). Read-only: it shows data, it adds no analysis.
- Data source: the final outputs `output/findings_loop_polish.db` and `output/pi_loop_polish.db` plus the upstream databases (read-only). New JSON goes to `dashboard_v2/data/`; v1's JSON stays as it is.

## 1. The chain to show (and the keys that link it)

| # | Component | Input | Output | Key to the next |
|---|---|---|---|---|
| 1 | Plausibility filter + Threshold evaluator | raw readings | accepted readings with status | `event_id` + timestamp |
| 2 | Short-range linker + Personal Data Store | threshold results | pairings, `raw_events`, `context_events` | glucose `(event_id, timestamp)` |
| 3 | Baseline Engine v2 | store | day / week / month windows, gists (`memory_v2`) | `window_id` |
| 4 | State Engine | store + baseline | items and **alerts** (`state_handoffs`) | `handoff_id` |
| 5 | Rulebook Lookup | alert | packet: ordered candidate factors | `handoff_id` / `packet_id` |
| 6 | Evidence Engine | packet + history | per-alert evidence (`event_evidence`), daily relationship evidence | `evidence_id` = `ev_<handoff_id>`, `relationship_key` |
| 7 | Findings Engine | alerts + evidence + context | cases, versions (structured layer), text | `case_id`, `finding_id`, refs |
| 8 | PI | versions | weekly memories, long-term notes, situations lines | `memory_id`, `relationship_key`, `finding_id` |

Trace chain for one case: alert (on the glucose chart) -> packet -> evidence per factor -> structured layer -> text with refs -> PI notes drawn on (`refs.pi_memories`) -> the long-term memory's history.

## 2. New views (pipeline mode)

1. **Pipeline overview**: the 8 components as a flow, in/out counts per stage, versions of method / prompt / checks.
2. **Component page** (one template, 8 instances): what goes in, what comes out, config, counts, a few real rows, link to the next stage.
3. **Case trace** (the main new view): pick a case (list by month), see the chain above step by step, each step linking to the next and to the matching v1 view (event / episode / week).
4. **Cases list**: all 116 cases with headline, versions, mode, source (model / kept / fallback).
5. **PI view**: weekly memories, relationship status over time, long-term notes with situations lines and their version history.
6. **Quality view**: fallbacks and reasons, check failures, reuse, model calls and tokens, the known limit (repeated headline/sentence).

## 3. Constraints so we do not drift

- v1 untouched (`git status` must show no change under `dashboard/`).
- Static, no server code beyond the existing `serve.py` copy; ECharts vendored; no new dependencies.
- Size: no raw model answers, no raw 282k-row tables. Per-case JSON loaded on demand; index files small. Target `dashboard_v2/data` well under 15 MB.
- Every number shown is read from a database by `build_data.py`; no copied numbers.
- Plain wording on the component pages: the text is a wording of the structured layer (the labels and classes are what the code decided).
- No changes to engines, configs, specs or databases. Report and export only.

## 4. To-do

**Phase 0: setup**
- [x] Copy `dashboard/` to `dashboard_v2/`; plan written
- [x] v2 title/brand changed ("Clinical Timeline + Pipeline"), `serve.py` default port 8766; old-output data files (events, episodes, baseline) removed from v2

**Phase 1: data build** (`dashboard_v2/build_data.py`, extends v1's builder)
- [x] Timeline data kept from final/ and output/ (pipeline input and threshold results); nothing from output_for_doctor/
- [x] `pipeline.json`: stage counts, versions, in/out descriptions
- [x] `alerts.json`: 287 alerts with measure, direction, size, time, case id, packet id
- [x] `cases.json`: 116 cases index (headline, versions, mode, source, month, relationships cited)
- [x] `case/<case_id>.json` on demand: alert(s), packet candidates, evidence per factor (label, flags, exposure), structured factors, texts of every version with refs, PI notes drawn on
- [x] `pi.json`: weekly memories, long-term notes + status history + situations lines
- [x] `quality.json`: text sources, fallbacks with reasons, checks, calls/tokens
- [x] Size check and a data test (ids resolve: every alert has a case or is listed unattached)

**Phase 2: front end**
- [x] Router + sidebar: "Patient timeline" section (v1 views unchanged) and "Pipeline" section (new)
- [x] Pipeline overview, component page template
- [x] Case trace (with links into v1 event / week / episode views and onto the glucose chart)
- [x] Cases list, PI view, Quality view
- [x] Cross-links: alerts and cases on the year, month and week views open the case trace (v1 event/episode views no longer exist in v2)

**Phase 3: verification**
- [x] Every timeline view loads in v2 (headless-browser screenshots, no console errors) and shows the same data (spot check all 10)
- [x] Case trace for: hospitalization week (17-20 Nov 2025), 17 Sep 2026 evening, sensor-artifact case 8 Nov 2025
- [ ] Dark and light theme, narrow width, no console errors
- [x] `git status`: nothing under `dashboard/` changed; no database file added
- [x] Short README in `dashboard_v2/` (how to build, run, what each view shows)

**Not now** (parked unless asked): publishing v2 to GitHub Pages, editing the workflow, a narrative layer, any new analysis.


## Decisions since the plan (user, after the first draft)

- v1's Events, Episodes and Baselines views came from `output_for_doctor/` (old synthetic output). v2 does **not** use it. Events become **alerts and cases** from our pipeline; there are **no Episodes**; Baselines come from the Baseline Engine's `memory_v2` (`baselines.json`).
- Phase 1 status: data built (5.5 MB, 116 case files); `tests/test_dashboard_v2_data.py` passes. v1 views that still read the removed files (events, episodes, baselines, parts of overview/month/event) are rewritten in Phase 2.

## Phase 2 status

Built: pipeline overview, 8 component pages, cases and alerts, case trace with linked highlights, PI view (heatmap and per-relationship), baseline windows, quality view, timeline views re-wired to alerts and cases. Checked with headless Chrome screenshots (no console errors). Open: dark-theme and narrow-width polish, publishing (not requested).


## Baseline page (redesigned, `#/baselines[/week|month/<end date>/<measure>]`)

The page now starts from the baseline itself: what a baseline is (usual, usual range, window, learning period), a scrubbable week/month control, a scorecard of 13 measures (value, her usual, her usual range, position bar, change vs the previous window, usual status against clinical limits), what the engine wrote for the selected window, one chart per measure over the year (value, her usual as of each day, usual range, notable windows, learning period, optional clinical reference lines; click a point to select), a table of how her usual shifted checkpoint by checkpoint, lab HbA1c next to the glucose-based estimate, and below them the earlier list of written summaries. Data: `baselines.json` (values, previous values, usual, tags, glucose detail per window) and `baseline_meta.json` (names, units, wrong-way direction from the State Engine config, clinical normal band, labs), both from `build_pipeline.py`. No engine, config or database change.
