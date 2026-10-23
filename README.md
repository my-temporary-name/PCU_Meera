# UMC upstream pipeline (patient `meera_iyer_v1`)

A deterministic pipeline that turns one **synthetic** patient's year of readings (1 Oct 2025 to 17 Sep 2026) into short, checked pieces of context, through eight components:

| # | Component | What it does | Code |
|---|---|---|---|
| 1 | Plausibility filter and Threshold evaluator | rejects impossible readings, gives every other reading a status against a reference range | `src/v0_code/logic/`, `nodes/` |
| 2 | Short-range linker and Personal Data Store | pairs high or low glucose with what happened nearby; stores everything | `src/v0_code/logic/linker.py`, `data/` |
| 3 | Baseline Engine | builds day, week and month windows, her usual, and a short gist | `src/v0_code/baseline_v2/` |
| 4 | State Engine | compares the newest reading with her usual every 15 minutes and raises alerts | `src/v0_code/state_engine/` |
| 5 | Rulebook Lookup | turns each alert into a checklist of factors worth testing | `src/v0_code/rulebook_lookup/` |
| 6 | Evidence Engine | tests each factor on her own history and labels it | `src/v0_code/evidence_engine/` |
| 7 | Findings Engine | groups alerts into cases and writes a checked text for each version | `src/v0_code/findings_engine/` |
| 8 | PI | keeps weekly and long-term notes of what keeps coming up | `src/v0_code/pi_engine/` |

The code decides every fact. A model only words what the code decided, and every sentence is checked.
The only model calls are the Baseline gist, the Findings text and the PI situations line.

## What is in each folder

### `understand/`: start here
- `how_the_numbers_flow.md`: one section per component, with the real numbers coming in and going out and why they differ (for example 77,797 readings checked, 44,469 given a status, 287 alerts, 116 cases, 29 long-term notes). Read this first to follow the whole chain.

- `repo_map.md`: what is in each folder and which files to open first.

### `component_understanding/`: one guide per component
Start at `00_index.md`. Each of the eight guides has a plain-words Part A (with real examples) and a technical Part B.

### `src/v0_code/`: the code
One sub-folder per engine, each with its own config, storage and run command:
- `baseline_v2/`, `state_engine/`, `rulebook_lookup/`, `evidence_engine/`, `findings_engine/`, `pi_engine/`: components 3 to 8.
- `loop_engine/`: runs Findings and PI together in time order, so Findings can read PI's earlier notes (the one loop in the pipeline).
- `logic/`, `nodes/`, `graph/`, `data/`: components 1 and 2 and the first graph (LangGraph) that runs them: load, filter, evaluate, link, store, baseline. `data/loaders.py` turns every source file into readings.
- `intel_common/`: small helpers shared by the engines (the phrase book, time handling).
- `viz/`: the older per-measure plots.

### `config/`: all patient-specific settings
One YAML file per engine (`state_meera_iyer_v1.yaml`, `rulebook_meera_iyer_v1.yaml`, `evidence_meera_iyer_v1.yaml`, `findings_meera_iyer_v1.yaml`, `pi_meera_iyer_v1.yaml`, `loop_meera_iyer_v1.yaml`, `patient_meera_iyer_v1.yaml` for the Baseline), plus the fixed libraries: `evidence_library_v0.yaml` (the 69 candidate relationships), `findings_phrasebook_v0.yaml` (the words the text may use) and `ingest_streams.yaml`. No stream, measure or patient name is hard-coded in the engines; it all lives here.

### `task/`: the specifications
The spec of each engine (`state_engine.md`, `rulebook_lookup_spec.md`, `evidence_engine_spec.md`, `findings_engine_spec.md`, `pi_spec.md`, `baselineV2.md`) with the amendments added after review, the first-component spec (`components.md`, `inputs.md`), and `task/evidence_engine/` with the rulebook itself (10 rules, 69 candidates, their sources).

### `tests/`
About 58 test files, including a second synthetic patient (`*_synth.py`) that runs each engine on configuration alone, as a check that nothing patient-specific is hard-coded. Run with `uv run python -m pytest -q tests`.

### `docs/`: reports and notes
The result report of each stage (Evidence 2a and 2b, Findings F1 and F2, PI P1 and P2, the loop L1, L2 and polish rounds), the State Engine notes and counts, and three overview documents: `V0_output_guide.md` (what every output file holds), `V0_year_in_numbers.md` and `V0_showcase.md` (real examples). `dashboard_v2_plan.md` is the dashboard's plan.

### `final/` and `ranges/`: the data
- `final/`: the patient's year as CSV files (glucose every 15 minutes, heart rate, hourly steps, sleep, meals, medicines, mood, diary, labs and so on) plus the generation notes and the diary. The data is synthetic.
- `ranges/`: the reference ranges (`threshold_ranges_full.csv`) and the plausibility bounds (`plausibility_bounds.csv`) used by component 1.

### `dashboard_v2/`: the dashboard (source)
A static, read-only site with no build step: `index.html`, `css/`, `js/` (a hash router and one view per page), the vendored charts, and `data/` (JSON the pages read). `build_data.py` and `build_pipeline.py` regenerate that JSON from the pipeline's databases; `serve.py` runs it locally. The published copy lives in a separate public repository.

### `dashboard/`: the first dashboard (kept for reference)
The earlier clinical-timeline dashboard. It is no longer published.

### Root files
`CLAUDE.md` (the project guide: commands, decisions worth knowing and how each engine behaves), `pyproject.toml` and `uv.lock` (Python 3.12 dependencies), `scripts/v0_docs.py` (a read-only export that writes `docs/V0_year_in_numbers.md` and `docs/V0_showcase.md` from the databases), `mm.md` (the synthetic dataset's summary document) and `mm2.md` (an earlier working note on scope, kept as history).

### Not in git
`output/` (the databases and CSV results, about 380 MB), `backups/` and `output_for_doctor/`. They are large or reproducible: run the pipeline to recreate them.

## Run it

```bash
uv sync                                   # Python 3.12
uv run python -m pytest -q tests          # tests
uv run v0-code                            # components 1 to 3: filter, evaluator, linker, store, baseline -> output/
```

The later engines each have their own command (State, Rulebook, Evidence, Findings, PI, loop); the exact commands and options are in `CLAUDE.md`. Run them in order, because each reads the database the one before it wrote.

## The model step

The Baseline gist, the Findings text and the PI situations line call a model through OpenRouter (`openai/gpt-5-mini`). Put your own key in a local `.env` (never commit it):

```
OPENROUTER_API_KEY=...
```

Every other step is plain Python and needs no key.

## Rebuild the dashboard data

```bash
uv run python dashboard_v2/build_data.py
uv run python dashboard_v2/build_pipeline.py     # needs the databases in output/
uv run python dashboard_v2/serve.py              # http://127.0.0.1:8766
```
