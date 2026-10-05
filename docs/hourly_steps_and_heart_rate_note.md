# Note: hourly steps and continuous heart rate were generated together

For this patient (`meera_iyer_v1`, a synthetic record) the hourly steps (`final/steps_hourly_yearly.csv`, now the ingest-only context stream `step_count_hourly`) and the 15-minute continuous heart rate (`final/continuous_heart_rate_yearly.csv`) were produced together by the data generator. Any relationship between activity in the preceding hour and heart rate on this patient is therefore **built in by construction**, not an observation about a real person.

What this means for Rulebook Lookup and the Evidence Engine that will use its packets:

- The `heart_rate_above` / `activity` candidate (hourly steps, 60 minutes before opening) can be expected to come out "supported" on this patient almost by design. A strong result there is not evidence that the method finds real causes; it is a check that the plumbing works.
- The same caution applies to any other check that pairs the two streams (for example the Threshold Evaluator already treats heart rate as "resting" only in hours with zero steps, which relies on the same coupling).
- Treat this patient's activity-to-heart-rate result as a positive control, never as a finding to report to a clinician or to carry into a rulebook weight.
