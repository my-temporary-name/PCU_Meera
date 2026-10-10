# Doctor's view: check report (as of 2026-09-17)

Everything for the view lives in `doctors_requirement/nmg_view/`. It reads only `final/*.csv` and `doctors_requirement/doctors_pack/doctors_data/*.csv`
(no model, no pipeline database, no engine import). The existing dashboards are untouched. Run it: `python3 doctors_requirement/nmg_view/serve.py` (port 8780).
Tests: `uv run python -m pytest -q doctors_requirement/nmg_view/tests` (5 pass).

## Matches
- Spec section 7: all eight domain signals (Red / Red / none / Red / Green / none / Amber / Amber), glycemic state S4, first follow-up F5 by 2026-12-17.
- Spec section 7 baseline table: all 11 series (latest, 24-month baseline, direction, change, since-diagnosis value and delta) reproduce exactly.
- Glucose input md5 `508468f1`; 5 readings above 600 and the 65.0 clip are handled as the Baseline rule says.

## Differences from `doctors_derived_values.md`
1. **Window lengths.** The pack's "90 days" and "14 days" CGM windows are 91 and 15 calendar days. I use true windows (90 and 14): 8,586 readings / mean 120.05 and 1,326 / 134.27.
2. **Post-meal "last 30 days"** medians use 31 days in the pack. Mine (true 30 days): 137.4 / 136.8 / 135.7 against the pack's 136.1 / 136.7 / 135.4.
3. **Resting heart rate range** (pack: 64 to 102) vs mine, which takes the last reading per day (max 98). Not reconciled against the raw stream.
4. **HbA1c vs GMI gap on 6 March:** 0.55 (mine) vs 0.56 (pack), a window-definition effect (lab day excluded, 90 days before).
5. **90th percentile** uses linear interpolation (as the pack does).
6. **eGFR inconsistency** is noted by the pack itself; the view shows the data value 93.7.

## Where the spec gives no band or an undefined term (defaults used)
- Blood pressure (N1) and liver (N2): no colour; values, trend, goal shown.
- Undefined clauses are not scored and carry a note: M3 (multiple major modifiers), P3 (persistently / high / deterioration), L3 follow-ups, K2.
- UACR missing means no Green. Several signals in one domain: the worst one wins (A4).
- Goals (HbA1c < 7.0, BP < 130/80, LDL < 70) are best guesses and badged so.
- IPAQ: every entry low (258 MET-min a week on 2026-09-17).
- Persona-sourced and best-guess values carry a badge and a hollow marker on charts; the fixed sentence is shown at the top; no overall colour, risk score, diagnosis or advice.

It is also a tab in dashboard_v2 ("Doctor's view", shown in a frame; dashboard_v2's server maps `/doctors/` to this folder). Not published, committed or pushed.
