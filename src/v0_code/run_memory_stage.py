"""Run the memory writer over the stored records, tier by tier, resumably. Not part of the graph.

    uv run python -m v0_code.run_memory_stage                # day (4 per call), then week (2), then month (1), same stop rules
    uv run python -m v0_code.run_memory_stage --tier day     # one tier

Reads the code-built records from output/personal_data_store.db (`uv run v0-code --rebuild` builds them). After EVERY batch it saves
memory_json, llm_status, llm_raw and is_notable for the batch's windows. Statuses:
  ok                  the model's headline / what-stood-out / notable reason passed the checks
  code_only_early     no flat band yet (first 14 days; first month checkpoint): NO model call — code-rendered entry, code headline, confidence low
  code_only_fallback  rejected after its one retry: code-rendered entry, code-made headline (top two material changes)
A window with one of these statuses is done and is skipped on resume; anything else (skipped, an old 'rejected') is run.

Stops launching new batches (in-flight ones finish and are saved) and does NOT continue to the next tier when
  - a tier's first-attempt failure rate (model-attempted windows only) is over 25%, judged once min(20, windows to run) have been attempted, or
  - any number the model wrote is grounded nowhere in the rendered text (an `ungrounded_number` failure, first attempt or final).
"""

import argparse
import asyncio
import json
import random
import sys
import time
from collections import Counter

from loguru import logger

from v0_code.data.store import PersonalDataStore
from v0_code.nodes import memory_writer as W
from v0_code.nodes.memory_llm import _llm

DB = "output/personal_data_store.db"
BATCH_SIZE = {"day": 4, "week": 2, "month": 1}
TIERS = ("day", "week", "month")
MAX_FIRST_ATTEMPT_FAILURE = 0.25
MIN_WINDOWS_FOR_RATE = 20
DONE = ("ok", W.STATUS_EARLY, W.STATUS_FALLBACK)


class CountingLLM:
    """Counts every model call (batch calls and retries alike)."""

    def __init__(self, llm):
        self.llm, self.calls = llm, 0

    async def ainvoke(self, messages):
        self.calls += 1
        return await self.llm.ainvoke(messages)


def failure_kind(f: str) -> str:
    return f.split(":")[0].split(" ")[0]


def _raw_blob(r: dict) -> str:
    return json.dumps({"raw": r["raw"], "failures": r["failures"], "first_attempt_ok": r["first_attempt_ok"],
                       "first_attempt_failures": r["first_attempt_failures"]})


def _persist(store: PersonalDataStore, r: dict) -> None:
    store.update_memory_llm_result(r["window_id"], json.dumps(r["memory"]), r["memory"]["is_notable"], r["llm_status"], _raw_blob(r))


def load_pending(store: PersonalDataStore, tier: str) -> list[dict]:
    rows = store.conn.execute("SELECT window_id, tier, record_json, llm_status FROM memory_records WHERE tier = ? ORDER BY start_date", (tier,)).fetchall()
    return [{"window_id": r["window_id"], "tier": r["tier"], "record": json.loads(r["record_json"]), "prior_record": None}
            for r in rows if r["llm_status"] not in DONE]


async def run_stage(tier: str, batch_size: int, db_path: str = DB, concurrency: int = 6, llm=None) -> dict:
    t0 = time.time()
    store = PersonalDataStore(db_path)
    total = store.conn.execute("SELECT COUNT(*) FROM memory_records WHERE tier = ?", (tier,)).fetchone()[0]
    pending = load_pending(store, tier)
    early = [w for w in pending if W.is_early(w["record"])]
    model_ws = [w for w in pending if not W.is_early(w["record"])]
    logger.info(f"stage {tier}: {total} windows | {total - len(pending)} already done | {len(early)} early (no model call) | {len(model_ws)} to run, {batch_size} per call")
    for w in early:  # no model call, saved immediately
        _persist(store, W._result(w, W.STATUS_EARLY, None, None, [], None))
    state = {"tier": tier, "total": total, "early_saved": len(early), "to_run": len(model_ws), "attempted": 0, "first_failed": 0, "ungrounded": [],
             "headline_direction_failures": 0, "stopped": None, "batches_done": 0, "calls": 0, "seconds": 0.0}
    if not model_ws:
        state["seconds"] = time.time() - t0
        return state
    llm = CountingLLM(llm or _llm())
    gate, call_sem, stop = asyncio.Semaphore(concurrency), asyncio.Semaphore(concurrency), asyncio.Event()
    min_n = min(MIN_WINDOWS_FOR_RATE, len(model_ws))

    async def one(batch: list[dict]) -> None:
        async with gate:
            if stop.is_set():
                return
            results = await W.process_batch(llm, tier, batch, call_sem)
            for r in results:  # persist after EVERY batch: a stop or a crash never loses finished windows
                _persist(store, r)
                if r["first_attempt_ok"] is None:
                    continue
                state["attempted"] += 1
                state["first_failed"] += 0 if r["first_attempt_ok"] else 1
                fails = (r["failures"] or []) + (r["first_attempt_failures"] or [])
                state["headline_direction_failures"] += sum(1 for f in fails if f.startswith("wrong_direction") and f.endswith("[headline]"))
                for f in fails:
                    if f.startswith("ungrounded_number"):
                        state["ungrounded"].append((r["window_id"], f[:200]))
            state["batches_done"] += 1
            rate = state["first_failed"] / max(state["attempted"], 1)
            logger.info(f"stage {tier}: batch {state['batches_done']} saved | attempted {state['attempted']} | first-attempt failures {state['first_failed']} ({100*rate:.0f}%)")
            if state["ungrounded"] and not state["stopped"]:
                state["stopped"] = f"a number is grounded nowhere ({len(state['ungrounded'])} so far, first: {state['ungrounded'][0]})"
                stop.set()
            elif state["attempted"] >= min_n and rate > MAX_FIRST_ATTEMPT_FAILURE and not state["stopped"]:
                state["stopped"] = f"{tier}: first-attempt failure rate {100*rate:.0f}% is over {int(100*MAX_FIRST_ATTEMPT_FAILURE)}% after {state['attempted']} windows"
                stop.set()

    await asyncio.gather(*(one(model_ws[i : i + batch_size]) for i in range(0, len(model_ws), batch_size)))
    state["calls"], state["seconds"] = llm.calls, time.time() - t0
    state["remaining"] = store.conn.execute("SELECT COUNT(*) FROM memory_records WHERE tier = ? AND llm_status NOT IN (?, ?, ?)", (tier, *DONE)).fetchone()[0]
    return state


async def run_all(tiers=TIERS, db_path: str = DB, batch_sizes=BATCH_SIZE, llm=None) -> list[dict]:
    """Tier after tier; the first tier that stops ends the run (later tiers do not start)."""
    out = []
    for tier in tiers:
        st = await run_stage(tier, batch_sizes[tier], db_path, llm=llm)
        out.append(st)
        if st["stopped"]:
            break
    return out


def summarize(tier: str, db_path: str = DB) -> dict:
    """Counts, failure rates and reasons, from what is stored (so it covers every resumed run)."""
    store = PersonalDataStore(db_path)
    total = store.conn.execute("SELECT COUNT(*) FROM memory_records WHERE tier = ?", (tier,)).fetchone()[0]
    rows = store.conn.execute("SELECT window_id, llm_status, llm_raw, record_json FROM memory_records WHERE tier = ?", (tier,)).fetchall()
    status = Counter(r["llm_status"] for r in rows)
    attempted = first_fail = headline_dir = 0
    first_kinds, final_kinds = Counter(), Counter()
    quiet = 0
    for r in rows:
        quiet += bool(json.loads(r["record_json"]).get("quiet"))
        if not r["llm_raw"]:
            continue
        blob = json.loads(r["llm_raw"])
        if blob["first_attempt_ok"] is None:
            continue
        attempted += 1
        if not blob["first_attempt_ok"]:
            first_fail += 1
            first_kinds.update({failure_kind(f) for f in blob["first_attempt_failures"] or []})
        if r["llm_status"] != "ok":
            final_kinds.update({failure_kind(f) for f in blob["failures"] or []})
        headline_dir += sum(1 for f in (blob["failures"] or []) + (blob["first_attempt_failures"] or []) if f.startswith("wrong_direction") and f.endswith("[headline]"))
    fallback = status.get(W.STATUS_FALLBACK, 0)
    return {"tier": tier, "windows": total, "status": dict(status), "model_attempted": attempted,
            "first_attempt_failures": first_fail, "first_attempt_failure_rate": round(first_fail / attempted, 3) if attempted else None,
            "final_failures_to_fallback": fallback, "final_failure_rate": round(fallback / attempted, 3) if attempted else None,
            "first_attempt_failure_kinds": dict(first_kinds.most_common()), "final_failure_kinds": dict(final_kinds.most_common()),
            "headline_direction_failures": headline_dir, "quiet": quiet, "quiet_fraction": round(quiet / total, 3) if total else None}


def random_entries(tier: str, n: int = 5, db_path: str = DB, seed: int = 5) -> list[dict]:
    store = PersonalDataStore(db_path)
    ids = [r["window_id"] for r in store.conn.execute("SELECT window_id FROM memory_records WHERE tier = ? AND llm_status = 'ok' ORDER BY start_date", (tier,))]
    pick = sorted(random.Random(seed).sample(ids, min(n, len(ids))))
    return [json.loads(store.conn.execute("SELECT memory_json FROM memory_records WHERE window_id = ?", (w,)).fetchone()[0]) for w in pick]


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the memory writer over the stored records, resumably")
    ap.add_argument("--tier", default="all", choices=["all", *TIERS])
    ap.add_argument("--batch-size", type=int, default=None, help="override for a single --tier")
    ap.add_argument("--db", default=DB)
    args = ap.parse_args()
    t0 = time.time()
    tiers = TIERS if args.tier == "all" else (args.tier,)
    sizes = {**BATCH_SIZE, **({args.tier: args.batch_size} if args.batch_size and args.tier != "all" else {})}
    states = asyncio.run(run_all(tiers, args.db, sizes))
    for st in states:
        print(json.dumps({k: v for k, v in st.items() if k != "ungrounded"}))
        if st.get("ungrounded"):
            print("ungrounded numbers:", json.dumps(st["ungrounded"][:5]))
    for t in tiers:
        print(json.dumps(summarize(t, args.db)))
    print(f"total model calls: {sum(s['calls'] for s in states)} | total seconds: {time.time() - t0:.0f}")
    stopped = next((s["stopped"] for s in states if s["stopped"]), None)
    if stopped:
        print("STOPPED:", stopped)
        sys.exit(2)


if __name__ == "__main__":
    main()
