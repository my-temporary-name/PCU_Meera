"""Node 1: load reference tables, patient facts, context and normalized readings."""

from pathlib import Path
from typing import Any

from loguru import logger

from v0_code.data import loaders
from v0_code.graph.state import UMCState


async def load_inputs_node(state: UMCState) -> dict[str, Any]:
    data_dir, ranges_dir = Path(state.data_dir), Path(state.ranges_dir)
    dob, sex = loaders.load_patient_facts(data_dir)
    steps, location = loaders.load_context(data_dir)
    readings = loaders.load_readings(data_dir)
    logger.info(f"load_inputs: {len(readings)} readings loaded")
    return {
        "plausibility_bounds": loaders.load_plausibility_bounds(ranges_dir),
        "threshold_rows": loaders.load_threshold_rows(ranges_dir),
        "patient_dob": dob,
        "patient_sex": sex,
        "steps_by_hour": steps,
        "location_by_date": location,
        "readings": readings,
        "meals": loaders.load_meals(data_dir),
        "adherence_by_date": loaders.load_adherence_by_date(data_dir),
        "context_events_by_date": loaders.load_context_events_by_date(data_dir),
        "sleep_by_date": loaders.load_sleep_by_date(data_dir),
        "mood_by_date_block": loaders.load_mood_by_date_block(data_dir),
        "diary_by_date": loaders.load_diary_by_date(data_dir),
    }
