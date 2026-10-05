"""Findings Engine (spec: task/findings_engine_spec.md with its Amendments). Stage F1: the code layer. Turns the evidence for a deviation into cases, versioned findings, a
factor table with wording classes, groups and a code-written line. No model, no statistics, no numbers in any text. Reads the evidence, hand-offs, packets, diary and state
memory (all as-of) and writes only its own database. Nothing patient-specific lives in the code: phrases, fields, tables and the time zone are config."""
