"""Verbatim ingest of streams that never pass through Threshold Evaluator, into context_events.

No computation here — it reshapes data already parsed into UMCState by load_inputs_node
(itself parsed from final/ once per run) into (stream, timestamp, date, value_text, value_num,
category, meta_json) rows. This keeps CSV parsing in one place (data/loaders.py) while still
giving the memory builder a durable, queryable table instead of only transient in-memory state.
"""

import json

from v0_code.data.ingest_config import IngestStream
from v0_code.graph.state import UMCState

Row = tuple[str, str | None, str, str | None, float | None, str | None, str | None]


def build_context_rows(state: UMCState, ingest_streams: tuple[IngestStream, ...] | list[IngestStream] = ()) -> list[Row]:
    rows: list[Row] = []

    for m in state.meals:
        rows.append(("meal_events", m["timestamp"], m["timestamp"][:10], m["food"], None, m["label"], json.dumps({"meal_id": m["id"]})))

    for date, entries in state.adherence_by_date.items():
        for a in entries:
            rows.append(("medication_adherence", None, date, "taken" if a["taken"] else "missed", float(a["taken"]), a["medication"], json.dumps({"adherence_id": a["id"]})))

    for date, entries in state.context_events_by_date.items():
        for c in entries:
            rows.append(("diary_context", c["timestamp"], date, c["description"], None, c["category"], json.dumps({"id": c["id"], "note": c["note"]})))

    for date, sleep in state.sleep_by_date.items():
        rows.append(("sleep_quality", sleep["timestamp"], date, sleep["quality"], sleep["hours"], None, json.dumps({"id": sleep["id"]})))

    for key, mood in state.mood_by_date_block.items():
        date, block = key.split("|", 1)
        rows.append(("mood_state", None, date, mood["label"], None, mood["category"], json.dumps({"time_block": block, "id": mood["id"]})))

    for date, location in state.location_by_date.items():
        rows.append(("location", None, date, location, None, None, None))

    # Full continuous_heart_rate stream (plausibility-passed only), including active-period
    # readings that never reached raw_events because Threshold Evaluator never scores them.
    for r in state.passed_readings:
        if r.biomarker == "continuous_heart_rate":
            rows.append(("continuous_heart_rate", r.timestamp, r.timestamp[:10], None, r.value, None, None))

    # Ingest-only streams (config/ingest_streams.yaml): appended after everything above, so no existing row or id moves.
    for s in ingest_streams:
        for r in state.passed_readings:
            if r.biomarker == s.biomarker:
                rows.append((s.name, r.timestamp, r.timestamp[:10], None, r.value, None, None))

    return rows
