"""Evidence Engine (spec: task/evidence_engine_spec.md, revision 2). Tests, with statistics on one person's own history, whether each factor in a rulebook
packet shows up in her data. Numbers and labels only: no wording, no LLM, no network. Reads the store, the State Engine, Baseline and Rulebook Lookup outputs
and configs; writes only its own database. Nothing patient-specific lives in the code: the library (config/evidence_library_v0.yaml) and the patient evidence
config define every stream, outcome, exposure and threshold."""
