"""State Engine: compares the latest reading of each measure with the patient's baseline and shows where the person stands right now
(spec: task/state_engine.md). Deterministic, read-only toward the Personal Data Store and the Baseline Engine, no LLM."""
