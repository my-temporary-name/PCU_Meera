# Repo map: what is in each folder and file

A quick guide to the repository. Folder first, then the files that matter. Starred items (★) are the ones to open first.
Generated folders (`output/`, `backups/`, `__pycache__`) are listed at the end.

## Start here (repo root)

| File | What it is |
|---|---|
| ★ `README.md` | Tour of the repo, how to run it, how the model step works. |
| ★ `CLAUDE.md` | The most complete technical description of every component, decision and gotcha. Read it before changing code. |
| `pyproject.toml`, `uv.lock`, `.python-version` | Python 3.12 and dependencies (managed with `uv`). |
| `PRODUCT.md`, `DESIGN.md` | Product and design notes for the doctor's view (colours, tone, components). |
| `DOCTORS_VIEW_WALKTHROUGH.md` | Walkthrough of the doctor's view screens. |
| `mm.md` | Summary of the synthetic dataset (patient, period, what was injected). |
| `mm2.md` | Early note confirming the first-pass scope of the chain (historical). |
| `four_boxes_ripple_and_amoeba_split_demo.html`, `living_orbi.html` | Stand-alone design demos for the doctor's view. Not part of the pipeline. |

## `understand/`: reading material

- ★ `how_the_numbers_flow.md`: how a reading becomes a finding, with real counts at every step.
- `repo_map.md`: this file.

## `component_understanding/`: one file per component

Each file has a plain-words Part A (with examples) and a technical Part B.
`01` plausibility filter and threshold evaluator, `02` linker and data store, `03` baseline engine, `04` state engine, `05` rulebook lookup, `06` evidence engine, `07` findings engine, `08` PI (findings memory).

## `src/v0_code/`: the code

| Folder / file | What it does |
|---|---|
| ★ `graph/` | The LangGraph pipeline. `builder.py` wires `load_inputs → filter → threshold → linker → store → baseline`; `state.py` holds the shared state. |
| `nodes/` | Thin graph nodes (read state, call logic, write output). `baseline_engine.py` writes the v1 baseline; `memory_llm.py` / `memory_writer.py` are the v1 model flow. |
| ★ `logic/` | The decision logic, no LangGraph: `plausibility.py`, `threshold.py`, `linker.py`, plus v1 baseline helpers (`memory_records.py`, `registry.py`, `anchors.py`, `data_quality.py`). |
| `data/` | Loading and storage. `loaders.py` normalises every source file; `store.py` is the SQLite Personal Data Store; `context_ingest.py` and `ingest_config.py` write non-threshold streams. |
| ★ `baseline_v2/` | Baseline Engine v2: per day / week / month entries (`engine.py`, `windows.py`, `anchors.py`, `material.py`, `render.py`) and the model "gist" text (`gist*.py`, `stage_d.py`, `cleanup.py`). Output goes to `memory_v2`. |
| ★ `state_engine/` | Compares the latest reading with her usual; opens deviation items and hand-offs (`engine.py`, `position.py`, `runs.py`, `usual.py`). |
| `rulebook_lookup/` | Builds the ordered checklist of candidate factors for each hand-off (`lookup.py`, `rulebook.py`, `grammar.py`). |
| ★ `evidence_engine/` | Tests with statistics whether each factor shows up in her history (`stats.py`, `history.py`, `refresh.py`, `event_checks.py`). |
| ★ `findings_engine/` | Groups hand-offs into cases and writes the careful account (`loop.py` cases, `wording.py` classes, `view.py` + `textcheck.py` + `textlayer.py` model text). |
| `pi_engine/` | Findings memory: weekly labels, lifecycle of long-term memories, situations line (`labels.py`, `lifecycle.py`, `text_layer.py`). |
| `loop_engine/` | Runs Findings and PI together in time order (`driver.py`, `l2.py`, `pi_live.py`) and the audits. |
| `intel_common/` | Shared by Findings, PI and loop: the phrase book reader and time helpers. |
| `viz/` | `plots.py`: one PNG per biomarker. |
| `cli.py`, `run_memory_stage.py` | Entry points (`v0-code`, `v0-plot`, memory stage runner). |

## `config/`: all patient-specific settings

One YAML per engine, so no patient, stream or medicine name is hard-coded in the engines.

- ★ `patient_meera_iyer_v1.yaml`: Baseline v2 (timezone, streams, anchors, gist settings). Other engines read from it.
- `state_*`, `rulebook_*`, `evidence_*`, `findings_*`, `pi_*`, `loop_*`: the settings for each engine.
- ★ `evidence_library_v0.yaml`: the 69 factor/outcome pairs the Evidence Engine can test.
- ★ `findings_phrasebook_v0.yaml`: the only words Findings and PI may use for each measure, exposure and wording class.
- `ingest_streams.yaml`: streams copied into the store for downstream use only.

## `task/`: the specifications

- ★ `intelligence_layer_overview.md`: the big picture of the layers after the store.
- `components.md`, `inputs.md`: spec for the filter and threshold evaluator, and the list of files evaluated.
- `baseline.md`, `baselineV2.md`: Baseline Engine specs (v1, v2).
- `state_engine.md`, `rulebook_lookup_spec.md`, `evidence_engine_spec.md`, `findings_engine_spec.md`, `pi_spec.md`: one spec each; the amendments at the top override the body.
- `evidence_engine/`: the rulebook data (`rulebook_v0.md`, `_rules.csv`, `_candidates.csv`).
- `ground_truth_manifest.md`: what was injected into the synthetic data.

## `tests/`

About 58 files, roughly one per engine and stage. `*_synth.py` / `pi_helpers.py` build synthetic patients so engines are tested on config alone. `*_real.py` tests check the real outputs. Run: `uv run python -m pytest -q tests`.

## `docs/`: reports and notes

- ★ `V0_output_guide.md`: how to read the outputs.
- `V0_showcase.md`, `V0_year_in_numbers.md`: summaries with counts.
- Stage reports, one per step: `evidence_engine_*`, `findings_f1/f2_*`, `pi_p1/p2_*`, `loop_l1/l2/polish_report.md`, `state_engine_*`, `rulebook_lookup_step1_report.md`.
- `baseline_engine_v2_brief.md`, `dashboard_v2_plan.md`, `doctors_data_check.md`, `hourly_steps_and_heart_rate_note.md`: design notes.

## `final/` and `ranges/`: the data

- ★ `final/`: the year of synthetic data for the patient (glucose, heart rate, steps, sleep, meals, adherence, labs, diary, context events). Note: `event_id` is not unique in these files.
- `final/Meera_Diary_Yearly_Oct2025_Sep2026.md` and `Generation_Logs_...md`: the persona diary and how the data was made.
- ★ `ranges/`: `plausibility_bounds.csv` (hard device limits) and `threshold_ranges_full.csv` (clinical ranges).

## Front ends

- `dashboard_v2/`: the current dashboard (`build_data.py` builds JSON, `serve.py` serves it; own `README.md`).
- `dashboard/`: the first dashboard, kept for reference.
- `doctors_requirement/`: the doctor's view (`nmg_view/`) and the clinical submission document, with the doctors' pack.
- `output_for_doctor/`: monthly event and episode JSON and `weekly_baseline_v2.json`, read by the dashboards. `UMC_Output_Files_Reference_Guide.md` explains them.

## `scripts/`

- `v0_docs.py`: generates the V0 documentation tables.

## Generated, not hand-written

- `output/`: everything the pipeline writes. Databases: `personal_data_store.db`, `state_engine.db`, `rulebook_lookup.db`, `evidence_engine.db`, `findings_engine.db`, `pi.db`, and the loop copies (`findings_loop_polish.db` and `pi_loop_polish.db` are the final ones). Also CSV results, stage reports and the model's raw answers (`*.jsonl`).
- `backups/`: dated copies of the databases (October 2026).
- `__pycache__/`: Python cache.
