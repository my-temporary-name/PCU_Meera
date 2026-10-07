# Dashboard v2: Clinical Timeline + Pipeline

A copy of `dashboard/` (which is untouched) extended with a pipeline mode. Opens on the patient timeline; the Pipeline section follows every alert from the reading to the context written about it.

```bash
uv run python dashboard_v2/build_data.py     # reads final/, output/*.db (read-only) -> dashboard_v2/data/ (about 6.6 MB, 116 case files loaded on demand)
uv run python dashboard_v2/serve.py          # http://127.0.0.1:8766  (--rebuild to regenerate data, --no-open to skip the browser)
```

| Section | Views |
|---|---|
| Patient timeline | Full year, Months, Weeks, Labs & body (from `final/` and the threshold results; alerts and cases are drawn on the glucose charts) |
| Pipeline | Overview (the 8 components), one page per component (`#/stage/<id>`: in, out, counts, real examples), Cases & alerts (`#/cases`, `#/cases/alerts`), **Case trace** (`#/case/<id>[/<version>]`), PI notes (`#/pi`, `#/pi/<key>`), Baseline windows, Quality |
| Reference | Data sources and glossary |

Case trace: the context chart (glucose, heart rate, steps, alerts as numbered pins), then six steps: alert, rulebook packet, evidence per factor, structured layer, text, and what the text drew on. Hover a reference chip (m1, f2, d1, p1...) in a sentence to highlight the item it cites.

Nothing from `output_for_doctor/` is used (no episodes, no old events or baselines). Data build: `build_data.py` (timeline data) and `build_pipeline.py` (pipeline data); data test: `tests/test_dashboard_v2_data.py`.
