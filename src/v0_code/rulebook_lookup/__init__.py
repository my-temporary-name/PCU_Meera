"""Rulebook Lookup (spec: task/rulebook_lookup_spec.md, Amendments on top): one packet of candidate factors to test per State Engine hand-off.
Deterministic, stateless, read-only toward every other database, no LLM, no network. Nothing patient-specific lives here: streams, medicines, flags and the
time zone are in the `rulebook:` config block, the checklist is data (the rulebook CSVs)."""
