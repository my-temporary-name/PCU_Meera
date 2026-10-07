# UMC upstream pipeline (patient `meera_iyer_v1`)

A deterministic pipeline that turns one synthetic patient's year of readings (Oct 2025 to Sep 2026) into short, checked context, through eight components:
Plausibility filter and Threshold evaluator, Short-range linker and Personal Data Store, Baseline Engine, State Engine, Rulebook Lookup, Evidence Engine, Findings Engine, PI.
Code decides every fact; a model only words what the code decided, and every sentence is checked.

- **How the numbers flow, component by component:** `understand/how_the_numbers_flow.md`
- **Specs:** `task/` and the Amendments inside each spec; **engine notes and reports:** `docs/`; **project guide:** `CLAUDE.md`
- **Dashboard (the visual layer):** `dashboard_v2/` (static site, no build step). It is published from a separate public repo.

## Run it

```bash
uv sync                                   # Python 3.12
uv run python -m pytest -q tests          # tests
uv run v0-code                            # first graph: filter, evaluator, linker, store, baseline -> output/
```

The later engines each have their own command (State, Rulebook, Evidence, Findings, PI, loop); the exact commands and options are in `CLAUDE.md`.
The databases in `output/` are not in git (they are large and reproducible): run the pipeline to recreate them.

## The model step

The Baseline gist, the Findings text and the PI situations line call a model through OpenRouter (`openai/gpt-5-mini`). Put your own key in a local `.env` (never commit it):

```
OPENROUTER_API_KEY=...
```

Every other step is plain Python and needs no key.

## Rebuild the dashboard data

```bash
uv run python dashboard_v2/build_data.py
uv run python dashboard_v2/build_pipeline.py     # needs output/*.db from the pipeline
uv run python dashboard_v2/serve.py              # http://127.0.0.1:8766
```
