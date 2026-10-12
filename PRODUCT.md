# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary (Doctor's view):** a doctor in a hospital or clinic, before and during a patient visit. The job is to recall what the patient has been through, what changed since the last visit, and what to look at today, in a minute or two. Confirmed in the init interview.
- **Other audiences of the dashboard:** the internal team (reviewing the pipeline and the Doctor's view) and doctors giving feedback on the NMG Lite clinical framework as applied to the synthetic patient. Confirmed.
- No external or patient-facing audience was named. The public GitHub Pages link exists but was not named as an intended audience.

## Product Purpose

A dashboard over one patient's Personal Clinical Unit (PCU) data, built on the UMC (Unified Medical Context) pipeline. It shows her year of readings (Oct 2025 to Sep 2026) and, for clinicians, applies the doctors' NMG Lite Version 1 framework (October 2026) to her record. The pipeline sections show how readings turn into alerts, cases, baselines and long-term notes; the Doctor's view ("Clinical" section) shows per-domain Green, Amber and Red clinical-attention signals, her own baseline and direction, the events around changes, and suggested review dates.

## Positioning

Not a diagnosis tool and not a risk score. The Doctor's view reads only the CSVs in `final/` and `doctors_requirement/doctors_pack/doctors_data/`, applies the document's rules deterministically, and states which rule produced each signal. It deliberately keeps domain signals separate and never combines them into one overall colour.

## Operating Context

- One synthetic patient, `meera_iyer_v1` (43-year-old woman, type 2 diabetes since Feb 2022, hypertension, subclinical hypothyroidism). All data is synthetic; much of the 2021 to 2025 clinic history is a labelled best guess built around a persona document.
- The Doctor's view is meant to be used by a doctor in their own clinic software. As-of date is 17 Sep 2026; the previous clinic visit was 17 Jun 2026.
- Source documents: `doctors_requirement/NMG Lite Version 1 - Clinical Submission - October 2026.md` (the clinical source of truth), `claude_app.md`, and the doctors' pack rules (38 band rules, A1 to X5, and 9 follow-up rows).
- Delivery: a local server (`dashboard_v2/serve.py`, port 8766) and a public static site on GitHub Pages (`my-temporary-name/PCU_Meera`); the pipeline source is in a private repo. A move to the GitHub org `Indian-AI-Research-Organisation` is planned, not done.

## Capabilities and Constraints

- The Doctor's view is a tab inside the dashboard (an iframe over `doctors/index.html`) and also runs standalone (port 8780).
- Domains: anthropometry, glycemia, blood pressure, lipids, kidney, liver, physical activity, lifestyle and modifiers. Each opens as a popup with the values on the left and the trend of the selected value on the right, plus Rules, Events and All values tabs.
- Blood pressure and liver have no band in the document; they show values and trend with a grey, "no priority defined" signal.
- Engines, config, specs and databases are finished and accepted. The standing rule is no more changes to them; work now is on the view.
- The Doctor's view reads no model and no pipeline database. No risk score (document section 8 is deliberately separate and not built).
- Open: the "since last visit" window follows the real record (13 weeks), not the 4 to 5 weeks assumed in conversation; "Concern today" is composed from the 17 Sep diary and the visit reason, not a recorded statement.

## Brand Commitments

- Name in the interface: "Doctor's view" (not "NMG Lite view").
- The user's standing preferences for this view: no truncated text, definitions stated once (legend or hover), pastel and flat styling matching the dashboard theme, click-to-open detail instead of long scrolling, plain one-line explanations, no redundancy, no "best guess" or "persona" labels, no top banner or sentence block.

## Evidence on Hand

- Real files: `final/*.csv` (the one-year synthetic dataset) and `doctors_requirement/doctors_pack/doctors_data/*.csv` (12 history files, 231 rows, every row tagged `synthetic_best_guess_v1` or `persona_document`).
- A supplied portrait of the patient, `doctors_requirement/nmg_view/img/meera.jpg` (provided by the user).
- Absent: real patients, real clinic notes, a doctor-reviewed treatment-goals record (the goals are marked "doctor to confirm"), and any doctor-written visit narrative. Do not fabricate these.

## Product Principles

1. The doctor's time comes first: the first screen answers who she is, what happened last time, what changed since and what she brings today.
2. Every signal is traceable to a rule ID, and rule text is one hover away.
3. Signals stay per domain; never collapse them into one colour, score or diagnosis.
4. Say what the data does not contain; never fill a gap with a plausible invention.
5. Detail is on demand (popups, tabs), not on a long scrolling page.

## Accessibility & Inclusion

No product-specific requirement was established. Existing practice: signal colours are always written out in words as well, and both a light and a dark theme are supported.
