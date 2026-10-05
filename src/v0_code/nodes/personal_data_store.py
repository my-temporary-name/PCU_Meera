"""Node 5: Personal Data Store — persists Threshold Evaluator + Linker output, verbatim."""

from pathlib import Path
from typing import Any

from loguru import logger

from v0_code.data.store import PersonalDataStore
from v0_code.graph.state import UMCState

GLUCOSE_BIOMARKER = "cgm_glucose_reading"  # the only biomarker the linker produces pairings for


async def personal_data_store_node(state: UMCState) -> dict[str, Any]:
    db_path = Path(state.output_dir) / "personal_data_store.db"

    reading_rows = [(r.event_id, r.timestamp, r.biomarker, r.value, r.status) for r in state.threshold_results]
    pairing_rows = [
        (p.glucose_event_id, p.glucose_timestamp, GLUCOSE_BIOMARKER, p.glucose_value, p.glucose_status, p.candidate_id, p.candidate_type, p.lag_minutes)
        for p in state.pairings
    ]

    with PersonalDataStore(db_path, reset=True) as store:
        store.insert_readings(reading_rows)
        store.insert_pairings(pairing_rows)

    logger.info(f"personal_data_store: {len(reading_rows)} readings, {len(pairing_rows)} pairings -> {db_path}")
    return {
        "store_output": str(db_path),
        "store_counts": {"readings": len(reading_rows), "pairings": len(pairing_rows)},
    }
