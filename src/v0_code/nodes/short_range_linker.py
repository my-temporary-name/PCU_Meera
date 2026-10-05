"""Node 4: Short-Range Event Linker — glucose high/low readings only."""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from v0_code.data.writers import write_csv
from v0_code.graph.state import UMCState
from v0_code.logic.linker import find_pairings

PAIRING_COLUMNS = [
    "glucose_event_id",
    "glucose_timestamp",
    "glucose_value",
    "glucose_status",
    "candidate_type",
    "candidate_id",
    "candidate_timestamp",
    "lag_minutes",
    "candidate_summary",
]
QUALIFYING_STATUSES = {"high", "low"}


async def short_range_linker_node(state: UMCState) -> dict[str, Any]:
    glucose_events = [
        r for r in state.threshold_results if r.biomarker == "cgm_glucose_reading" and r.status in QUALIFYING_STATUSES
    ]

    hr_readings = sorted(
        ((r.timestamp, r.value) for r in state.passed_readings if r.biomarker == "continuous_heart_rate")
    )
    hr_times = [int(datetime.fromisoformat(ts).timestamp()) for ts, _ in hr_readings]
    hr_values = [v for _, v in hr_readings]

    pairings = []
    for reading in glucose_events:
        pairings.extend(
            find_pairings(
                reading,
                state.meals,
                state.adherence_by_date,
                state.steps_by_hour,
                hr_times,
                hr_values,
                state.sleep_by_date,
                state.context_events_by_date,
                state.diary_by_date,
                state.mood_by_date_block,
            )
        )

    output = write_csv(Path(state.output_dir) / "short_range_pairings.csv", PAIRING_COLUMNS, pairings)
    counts = dict(Counter(p.candidate_type for p in pairings))
    # event_id repeats across months (see CLAUDE.md) — dedupe by (event_id, timestamp), not event_id alone.
    with_pairings = len({(p.glucose_event_id, p.glucose_timestamp) for p in pairings})
    logger.info(f"short_range_linker: {len(glucose_events)} qualifying readings, {len(pairings)} pairings, {counts}")
    return {
        "pairings": pairings,
        "linker_output": output,
        "linker_counts": counts,
        "qualifying_glucose_events": len(glucose_events),
        "glucose_events_with_pairings": with_pairings,
    }
