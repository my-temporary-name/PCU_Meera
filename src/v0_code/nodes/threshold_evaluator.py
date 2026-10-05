"""Node 3: Threshold Evaluator."""

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from loguru import logger

from v0_code.data.writers import write_csv
from v0_code.graph.state import Reading, UMCState
from v0_code.logic.threshold import evaluate_threshold, skip_reason

THRESHOLD_COLUMNS = [
    "event_id",
    "biomarker",
    "timestamp",
    "value",
    "age_group_used",
    "status",
    "confidence_source",
]


def _daily_step_counts(readings: list[Reading]) -> list[Reading]:
    """step_count thresholds are per day; sum plausible hourly steps into daily totals."""
    totals: dict[str, float] = defaultdict(float)
    for r in readings:
        if r.biomarker == "steps_hourly":
            totals[r.timestamp[:10]] += r.value
    return [
        Reading(
            event_id=f"step_count_{day}",
            biomarker="step_count",
            timestamp=day,
            value=total,
            source_file="steps_hourly_yearly.csv",
        )
        for day, total in sorted(totals.items())
    ]


async def threshold_evaluator_node(state: UMCState) -> dict[str, Any]:
    dob, sex = state.patient_dob, state.patient_sex
    candidates = [r for r in state.passed_readings if r.biomarker != "steps_hourly"]
    candidates += _daily_step_counts(state.passed_readings)

    results, missing, not_applicable = [], Counter(), Counter()
    for reading in candidates:
        why = skip_reason(reading, state.steps_by_hour)
        if why:
            not_applicable[f"{reading.biomarker}: {why}"] += 1
            continue
        res = evaluate_threshold(reading, state.threshold_rows, dob, sex)
        if res is None:
            missing[reading.biomarker] += 1
        else:
            results.append(res)

    output = write_csv(
        Path(state.output_dir) / "threshold_evaluation_results.csv", THRESHOLD_COLUMNS, results
    )
    status_counts = dict(Counter(r.status for r in results))
    logger.info(f"threshold_evaluator: {status_counts}; no threshold row: {dict(missing)}; not applicable: {dict(not_applicable)}")
    return {
        "threshold_results": results,
        "threshold_output": output,
        "status_counts": status_counts,
        "no_threshold_row": dict(missing),
        "not_applicable": dict(not_applicable),
    }
