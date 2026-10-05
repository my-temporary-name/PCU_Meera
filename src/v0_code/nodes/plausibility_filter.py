"""Node 2: Signal Plausibility Filter."""

from collections import Counter
from pathlib import Path
from typing import Any

from loguru import logger

from v0_code.data.writers import write_csv
from v0_code.graph.state import UMCState
from v0_code.logic.plausibility import check_plausibility

FILTER_COLUMNS = ["event_id", "biomarker", "timestamp", "raw_value", "filter_result", "reason"]


async def plausibility_filter_node(state: UMCState) -> dict[str, Any]:
    results = [
        check_plausibility(r, state.plausibility_bounds, state.steps_by_hour, state.location_by_date)
        for r in state.readings
    ]
    passed = [r for r, res in zip(state.readings, results) if res.filter_result == "PASS"]
    counts = dict(Counter(res.filter_result for res in results))
    output = write_csv(
        Path(state.output_dir) / "plausibility_filter_results.csv", FILTER_COLUMNS, results
    )
    logger.info(f"plausibility_filter: {counts}")
    return {
        "filter_results": results,
        "passed_readings": passed,
        "filter_output": output,
        "filter_counts": counts,
    }


def route_after_filter(state: UMCState) -> str:
    return "threshold_evaluator" if state.passed_readings else "__end__"
