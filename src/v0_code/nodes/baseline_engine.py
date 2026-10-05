"""Node 6: Baseline Engine (glucose slice) — window metrics in code, judgment via LLM.

Reads glucose readings back from the Personal Data Store (not from source files), computes
every metric deterministically, then asks an LLM to judge notability and write one short
note per window from those already-computed numbers only. The LLM never calculates anything
and never sees a raw reading; a failed LLM call never blocks storing the numeric metrics.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from loguru import logger

from v0_code.data.context_ingest import build_context_rows
from v0_code.data.ingest_config import load_ingest_streams
from v0_code.data.store import PersonalDataStore
from v0_code.graph.state import GlucoseWindow, UMCState
from v0_code.logic.baseline_glucose import compute_glucose_windows
from v0_code.logic.anchors import anchor_fire_report
from v0_code.logic.memory_records import build_all_records

load_dotenv()

BATCH_SIZE = 15
MAX_CONCURRENT_BATCH_CALLS = 8
MODEL = "openai/gpt-5-nano"
GLUCOSE_BIOMARKER = "cgm_glucose_reading"

PROMPT = """You are reviewing continuous glucose monitoring (CGM) summary statistics for a \
single patient. Every number below was already computed by deterministic code — you do not \
calculate anything. Your only job, per window, is to judge whether the shift from the prior \
window to the current one is a clinically meaningful change worth flagging, not routine \
day-to-day noise, and if so, write one short sentence saying what changed, using only the \
numbers given.

Reference anchors for "notable" (weigh them together, none is a rigid rule on its own):
- Time in Range (tir_pct) moved by more than 10 percentage points
- Variability (cv_pct) moved by more than 8 percentage points
- GMI (gmi_pct) moved by more than 0.3 percentage points
- A severe range (tar_severe_pct or tbr_severe_pct) appeared where it was near zero, or \
disappeared after being present

Rules:
- Never invent a cause, a recommendation, or any fact not present in the numbers given.
- interpretive_note: at most ~25 words, factual, states the numbers that changed and the \
direction. Set it to null whenever is_notable is false.
- Refer to metrics by their natural clinical name, never their field name — "GMI" not \
"gmi_pct", "Time in Range" or "TIR" not "tir_pct", "variability" or "%CV" not "cv_pct".
- Return strict JSON only, one key per window number below, no extra keys, no prose outside \
the JSON: {{"1": {{"is_notable": bool, "interpretive_note": string or null}}, "2": {{...}}}}

Windows:
{batch_json}
"""


def _window_payload(w: GlucoseWindow) -> dict[str, Any]:
    return {
        "window_type": w.window_type,
        "window_start": w.window_start,
        "window_end": w.window_end,
        "current": {
            "mean": w.mean,
            "gmi_pct": w.gmi_pct,
            "tir_pct": w.tir_pct,
            "tar_pct": w.tar_pct,
            "tar_severe_pct": w.tar_severe_pct,
            "tbr_pct": w.tbr_pct,
            "tbr_severe_pct": w.tbr_severe_pct,
            "cv_pct": w.cv_pct,
        },
        "deltas_vs_prior_window": {
            "delta_mean": w.delta_mean,
            "delta_tir_pct": w.delta_tir_pct,
            "delta_cv_pct": w.delta_cv_pct,
            "delta_gmi_pct": w.delta_gmi_pct,
        },
    }


def _parse(raw_text: str) -> dict[str, dict]:
    raw = json.loads(raw_text)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a JSON object, got {type(raw).__name__}")
    return raw


async def _call(llm, payload: dict[str, dict]) -> dict[str, dict]:
    batch_json = json.dumps(payload, ensure_ascii=False)
    response = await llm.ainvoke(PROMPT.format(batch_json=batch_json))
    content = getattr(response, "content", response)
    return _parse(content if isinstance(content, str) else str(content))


async def _judge_batch(
    llm, windows: list[GlucoseWindow], semaphore: asyncio.Semaphore, failures: list[dict]
) -> None:
    keyed = {str(i): w for i, w in enumerate(windows, start=1)}
    payload = {k: _window_payload(w) for k, w in keyed.items()}

    async with semaphore:
        try:
            results = await _call(llm, payload)
        except Exception as exc:
            logger.warning(f"Baseline Engine batch failed ({len(windows)} windows), retrying individually: {exc}")
            results = {}

        missing = [k for k in keyed if k not in results]
        for k in missing:
            try:
                single = await _call(llm, {k: payload[k]})
                results[k] = single.get(k, {})
            except Exception as exc:
                logger.error(f"Baseline Engine individual retry failed for window {keyed[k].window_start}: {exc}")
                failures.append({"window_start": keyed[k].window_start, "window_type": keyed[k].window_type, "error": str(exc)})

    for k, w in keyed.items():
        r = results.get(k)
        if isinstance(r, dict) and "is_notable" in r:
            w.is_notable = bool(r["is_notable"])
            w.interpretive_note = r.get("interpretive_note")


async def judge_windows(windows: list[GlucoseWindow]) -> list[dict]:
    """Mutates windows in place (is_notable/interpretive_note); returns a list of failures.

    Never raises: any LLM-side problem (missing key, network, bad model name, ...) degrades
    to 'no judgment for these windows' — the numeric metrics are computed and returned to the
    caller either way, so a broken LLM step can never lose the deterministic data."""
    judgeable = [w for w in windows if w.delta_mean is not None]  # nothing to compare -> no LLM call
    if not judgeable:
        return []

    try:
        llm = ChatOpenAI(
            model=MODEL,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    except Exception as exc:
        logger.error(f"Baseline Engine: could not start the LLM client, skipping judgment for all windows: {exc}")
        return [{"window_start": w.window_start, "window_type": w.window_type, "error": str(exc)} for w in judgeable]

    batches = [judgeable[i : i + BATCH_SIZE] for i in range(0, len(judgeable), BATCH_SIZE)]
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCH_CALLS)
    failures: list[dict] = []
    await asyncio.gather(*(_judge_batch(llm, b, semaphore, failures) for b in batches))
    return failures


async def baseline_engine_node(state: UMCState) -> dict[str, Any]:
    db_path = Path(state.output_dir) / "personal_data_store.db"
    with PersonalDataStore(db_path) as store:
        rows = store.get_events(GLUCOSE_BIOMARKER, "2000-01-01", "2100-01-01")
        readings = [(r["timestamp"], r["value"]) for r in rows]

    windows = compute_glucose_windows(readings)
    failures: list[dict] = []
    if state.glucose_caption_llm:  # legacy per-window caption: off by default (--glucose-caption)
        try:
            failures = await judge_windows(windows)
        except Exception as exc:
            logger.error(f"Baseline Engine: LLM judgment step failed unexpectedly, storing metrics without it: {exc}")
            failures = [{"window_start": "ALL", "window_type": "ALL", "error": str(exc)}]
    else:
        logger.info("baseline_engine: legacy glucose caption LLM skipped (default); numeric_summary metrics still written")

    rows_to_insert = [
        (
            GLUCOSE_BIOMARKER, w.window_type, w.window_start, w.window_end, w.n_readings,
            w.completeness_pct, int(w.reliable), w.mean, w.gmi_pct, w.tir_pct, w.tar_pct,
            w.tar_severe_pct, w.tbr_pct, w.tbr_severe_pct, w.cv_pct, w.delta_mean,
            w.delta_tir_pct, w.delta_cv_pct, w.delta_gmi_pct,
            None if w.is_notable is None else int(w.is_notable), w.interpretive_note,
        )
        for w in windows
    ]
    with PersonalDataStore(db_path) as store:
        store.insert_numeric_summaries(rows_to_insert)

    counts = {
        "day_windows": sum(1 for w in windows if w.window_type == "day"),
        "week_windows": sum(1 for w in windows if w.window_type == "week"),
        "notable": sum(1 for w in windows if w.is_notable),
        "llm_failures": len(failures),
    }
    logger.info(f"baseline_engine: {counts}")

    # --- cross-domain memory records (task/baseline.md rebuild) --- numeric only, no LLM yet.
    with PersonalDataStore(db_path) as store:
        store.conn.execute("DELETE FROM context_events")
        store.conn.execute("DELETE FROM memory_records")
        store.conn.commit()
        store.insert_context_events(build_context_rows(state, load_ingest_streams()))

    with PersonalDataStore(db_path) as store:
        built = build_all_records(store, state.steps_by_hour)
        for date, rec in built["day"].items():
            store.insert_memory_record(f"day_{date}", "day", date, date, rec["reliable"], json.dumps(rec["record"]), rec["prior_window_id"], json.dumps(rec["flags"]))
        for end_date, rec in built["week"].items():
            store.insert_memory_record(f"week_ENDING_{end_date}", "week", rec["start_date"], rec["end_date"], rec["reliable"], json.dumps(rec["record"]), rec["prior_window_id"], json.dumps(rec["flags"]))
        for rec in built["month"]:
            store.insert_memory_record(rec["record"]["window_id"], "month", rec["start_date"], rec["end_date"], rec["reliable"], json.dumps(rec["record"]), rec["prior_window_id"], json.dumps(rec["flags"]))

    memory_counts = {
        "day_records": len(built["day"]), "week_records": len(built["week"]), "month_records": len(built["month"]),
        "day_reliable": sum(1 for r in built["day"].values() if r["reliable"]),
        "week_reliable": sum(1 for r in built["week"].values() if r["reliable"]),
        "month_reliable": sum(1 for r in built["month"] if r["reliable"]),
        "day_anchors_crossed": sum(1 for r in built["day"].values() if r["anchors_crossed"]),
        "week_anchors_crossed": sum(1 for r in built["week"].values() if r["anchors_crossed"]),
        "month_anchors_crossed": sum(1 for r in built["month"] if r["anchors_crossed"]),
    }
    logger.info(f"memory_records (numeric only, LLM step not yet run): {memory_counts}")
    anchor_report = anchor_fire_report({
        "day": [r["anchors_crossed"] for r in built["day"].values()],
        "week": [r["anchors_crossed"] for r in built["week"].values()],
        "month": [r["anchors_crossed"] for r in built["month"]],
    })

    return {"glucose_windows": windows, "baseline_llm_failures": failures, "baseline_counts": counts, "memory_counts": memory_counts, "anchor_report": anchor_report}
