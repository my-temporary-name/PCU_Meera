# V0 output guide

The final outputs of V0 are `output/findings_loop_polish.db` (Findings, with the model texts) and `output/pi_loop_polish.db` (PI). Everything else is an input to them or an earlier stage. All databases are SQLite; open them read-only.

## Where everything is (`output/`)

| file | what it is |
|---|---|
| `personal_data_store.db` | the cleaned readings and context (`raw_events`, `context_events`), the threshold results and linker pairings, and the Baseline Engine's window records and gists (`memory_v2`, `memory_records`) |
| `state_engine.db` | the State Engine: `state_items` (565 deviations the engine opened), `state_handoffs` (287 alerts handed on), `state_log` (one snapshot per 15-minute tick) |
| `rulebook_lookup.db` | `rulebook_packets`: for each alert, the ordered list of candidate factors to test |
| `evidence_engine.db` | `event_evidence` (per alert: what was tested and the label of each factor), `event_completions` (late results), `relationship_evidence` (one record per relationship per day), `evidence_runs` |
| **`findings_loop_polish.db`** | **final Findings output** (below) |
| **`pi_loop_polish.db`** | **final PI output** (below) |
| `findings_engine.db`, `pi.db`, `findings_loop.db`, `pi_loop.db`, `findings_loop_full.db`, `pi_loop_full.db` | earlier stages (F1 / F2, P1, L1, L2); kept, not the final output |

## `findings_loop_polish.db`

- `cases`: one row per case (alerts close in time are one case): id, local date, opened and last alert time, closed time.
- `case_handoffs`: which alerts joined which case (`counted` = it produced a version); `unattached_handoffs`: alerts that opened no case.
- `findings`: one row per **version** of a case (a new version for each new alert or late result). `record_json` is the structured layer: measures, factors with their labels and wording classes, groups, `repeat` (PI status and seen-before band), `refs` (diary, state-memory and PI references). Versions are never changed.
- `finding_text`: the text of each version: `text_json` has `headline` and `sentences` (each with `text` and `refs`); `text_source` is `llm` or `code_line` (fallback); `from_prompt` is set when an answer written under an earlier prompt was kept; `prompt_version`, `checks_version`, `view_hash`.
- `finding_llm`: the model's raw answers, token usage and the failed checks of every attempt.
- `meta`: versions of the method, config and prompts; `l2_call_log` is the log of model calls by week.

## `pi_loop_polish.db`

- `pi_mid_entries`: each version as an entry in its calendar week (headline and sentences); `pi_mid_memories`: one row per week (`open`, then `sealed`); `pi_entry_keys`: which relationships each entry mentions.
- `pi_long_memories`: **long-term memories**, one row per relationship per version: `status` (candidate, supported, weakened, retracted), `weekly_labels`, `counters`, `text` (the association sentence), `status_history`. A new version is written only when something changes.
- `pi_text`: the situations line of each long-term version (`text_json.situations`, or null), `pi_llm`: its model answers and failed checks.
- `pi_weekly_runs`: one record per weekly job.

## SQL

Run from `output/` in the `sqlite3` shell, opening `findings_loop_polish.db` and attaching the others:

```sql
ATTACH DATABASE 'pi_loop_polish.db' AS pi;
ATTACH DATABASE 'evidence_engine.db' AS ev;
```

**(a) Every case with its latest text**

```sql
SELECT c.case_id, c.local_date, f.version,
       json_extract(t.text_json,'$.headline') AS headline,
       (SELECT group_concat(json_extract(s.value,'$.text'),' ') FROM json_each(t.text_json,'$.sentences') s) AS body
FROM cases c
JOIN findings f ON f.case_id = c.case_id AND f.version = (SELECT MAX(version) FROM findings WHERE case_id = c.case_id)
JOIN finding_text t ON t.finding_id = f.finding_id
ORDER BY c.opened_at;
```

**(b) PI's long-term notes with status and situations line** (latest version of each relationship)

```sql
SELECT m.relationship_key, m.version, m.status, m.written_at,
       json_extract(m.record_json,'$.text.sentences[0]') AS association,
       json_extract(x.text_json,'$.situations') AS situations
FROM pi.pi_long_memories m
LEFT JOIN pi.pi_text x ON x.memory_id = m.memory_id AND x.version = m.version
WHERE m.version = (SELECT MAX(version) FROM pi.pi_long_memories WHERE memory_id = m.memory_id)
ORDER BY m.relationship_key;
```

**(c) The evidence for one case** (here `case_2025-11-08T11:00:00+05:30`; each counted alert has one evidence record listing every factor tested, its label and flags)

```sql
SELECT h.handoff_id, e.evidence_id, e.event_time, e.record_json
FROM case_handoffs h
JOIN ev.event_evidence e ON e.handoff_id = h.handoff_id
WHERE h.case_id = 'case_2025-11-08T11:00:00+05:30' AND h.counted = 1;
```

The relationship-level evidence behind a factor is in `ev.relationship_evidence` (`relationship_key`, `as_of_date`, `record_json`); the keys come from `findings.record_json` (`factors[].relationship_key`).

## Notes

- A version's text is only a wording of its structured layer; the labels and classes in `findings.record_json` are what the code decided. Nine versions use the code line (`text_source = 'code_line'`).
- `scripts/v0_docs.py` regenerates `V0_year_in_numbers.md` and `V0_showcase.md` from these databases.
