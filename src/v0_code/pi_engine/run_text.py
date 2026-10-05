"""Run PI's text layer (stage P2, prompt pp-v3) on a SAMPLE of long-term memory versions.

    uv run python -m v0_code.pi_engine.run_text --config config/pi_<patient>.yaml --sample [--seed 20260] [--no-network] [--refresh] [--drop-other-prompt-rows]

The association sentence of every note is the stored P1 code text and is never sent to the model. The model writes only the situations line, from the mid-term entries. Reads the
stored memory versions (never changes them); writes only `pi_text` and `pi_llm` of PI's database, a JSONL log, and the report. Versions of one memory that are consecutive in the sample are
run in order, so a later version sees the previous line and its entries (a chain)."""

import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from v0_code.evidence_engine.library import load_library
from v0_code.findings_engine import llm
from v0_code.findings_engine.factors import parse_key
from v0_code.intel_common.phrasebook import Phrasebook
from v0_code.pi_engine import text_layer, text_view
from v0_code.pi_engine.config import PiConfig
from v0_code.pi_engine.engine import PiReader
from v0_code.pi_engine.storage import PiStore
from v0_code.pi_engine.weeks import week_of

ROOT = Path(__file__).resolve().parents[3]
P1_TABLES = ("pi_mid_memories", "pi_mid_entries", "pi_entry_keys", "pi_long_memories", "pi_weekly_runs")


class NoNetwork:
    """A client that refuses to be called: proof that a run is served from the cache."""

    def __init__(self):
        self.chat = self
        self.completions = self

    def create(self, **kw):
        raise RuntimeError("no network call is allowed in this run")


def load_versions(store: PiStore, cfg: PiConfig, pi: PiReader | None = None) -> list[dict]:
    """Every stored long-term version with the facts the sample needs (and, when `pi` is given, how many entries cite it in its own week)."""
    out = []
    for rj in (r[0] for r in store.conn.execute("SELECT record_json FROM pi_long_memories ORDER BY relationship_key, version")):
        m = json.loads(rj)
        week = week_of(m["written_at"], cfg.tz).iso
        v = {**m, "week": week, "regenerated": text_view.regeneration_due(m["created_week"], week, cfg.regenerate_every_weeks), "backfilled": m["version"] == 1 and m["status"] == "supported"}
        if pi is not None:
            v["entries_this_week"] = sum(m["relationship_key"] in e["relationship_keys"] for e in pi.get_open_week(m["written_at"])["entries"])
        out.append(v)
    return out


def select_sample(vs: list[dict], plan: dict, seed: int) -> list[tuple[str, tuple]]:
    """(why, (memory_id, version)): a chain of consecutive versions of one memory first, then the required kinds, then seeded picks across the weeks up to `n_total`."""
    rng = random.Random(seed)
    chosen: dict = {}
    uid = lambda v: (v["memory_id"], v["version"])
    L = int(plan.get("chain_length", 3))
    mems: dict = {}
    for v in vs:
        mems.setdefault(v["memory_id"], []).append(v)
    windows = []
    for mid in sorted(mems):
        g = sorted(mems[mid], key=lambda v: v["version"])
        for i in range(len(g) - L + 1):
            w = g[i:i + L]
            if all(x["entries_this_week"] > 0 and x["status"] != "retracted" for x in w) and [x["version"] for x in w] == list(range(w[0]["version"], w[0]["version"] + L)):
                windows.append(w)
    if windows:
        for i, v in enumerate(rng.choice(windows), 1):
            chosen[uid(v)] = f"chain: {i} of {L}"

    def pick(why, pool):
        pool = [v for v in pool if uid(v) not in chosen]
        pool = sorted([v for v in pool if v["entries_this_week"] > 0] or pool, key=uid)
        if pool:
            chosen[uid(rng.choice(pool))] = why
    plain = lambda v: not v["backfilled"] and not v["regenerated"]
    pick("same-day only", [v for v in vs if v["same_day_only"] and v["status"] == "supported" and plain(v)])
    pick("candidate", [v for v in vs if v["status"] == "candidate" and not v["regenerated"]])
    pick("supported", [v for v in vs if v["status"] == "supported" and plain(v) and not v["same_day_only"] and "placebo_fired" not in v["flags_seen"]])
    pick("back-filled supported", [v for v in vs if v["backfilled"]])
    pick("weakened", [v for v in vs if v["status"] == "weakened" and v["relationship_key"] == plan.get("weakened_key")] or [v for v in vs if v["status"] == "weakened"])
    pick("regenerated", [v for v in vs if v["regenerated"] and v["status"] in ("supported", "candidate")])
    pick("placebo_fired", [v for v in vs if "placebo_fired" in v["flags_seen"] and v["status"] == "supported" and plain(v)])
    pick("retracted", [v for v in vs if v["status"] == "retracted"])
    rest = sorted((v for v in vs if uid(v) not in chosen and v["status"] != "retracted" and v["entries_this_week"] > 0), key=lambda v: (v["week"], uid(v)))
    weeks = sorted({v["week"] for v in rest})
    rng.shuffle(weeks)
    pool = {w: [v for v in rest if v["week"] == w] for w in weeks}
    for w in weeks:
        rng.shuffle(pool[w])
    while len(chosen) < int(plan["n_total"]) and any(pool.values()):
        for w in weeks:
            if pool[w] and len(chosen) < int(plan["n_total"]):
                chosen[uid(pool[w].pop())] = "seeded"
    return [(why, u) for u, why in chosen.items()]


def run_sample(pi, vs: list[dict], sample, tcfg, pb, lib, kinds, client, rows: dict, refresh: bool, regen_every: int, refs=None) -> tuple[list[dict], dict]:
    index = {(v["memory_id"], v["version"]): v for v in vs}
    overlay = {u: r for lst in rows.values() for u, r in lst if r.get("prompt_version") == text_layer.PROMPT_VERSION}
    groups: dict = {}
    for why, uid in sample:
        groups.setdefault(uid[0], []).append((why, uid))
    for g in groups.values():
        g.sort(key=lambda x: x[1][1])
    results: dict = {}
    units: dict = {}
    for r in range(max(len(g) for g in groups.values())):
        batch = []
        for mid in sorted(groups):
            if r >= len(groups[mid]):
                continue
            why, uid = groups[mid][r]
            m = index[uid]
            prev = results.get((mid, m["version"] - 1)) or (overlay.get((mid, m["version"] - 1)) and text_layer.TextResult(overlay[(mid, m["version"] - 1)]["text"], "ok", [], [], []))
            previous = {"line": prev.text["situations"], "entry_ids": prev.text["entry_ids"]} if prev is not None and prev.text.get("situations") else None
            retracted = m["status"] == "retracted"
            view, ids = (None, []) if retracted else text_view.build_view(pi, m, previous, m["regenerated"], pb, lib, kinds, refs, tcfg.get("diary_ref_prefix", "d"))
            batch.append({"uid": uid, "why": why, "view": view, "ids": ids, "assoc": m["text"], "previous": previous, "retracted": retracted, "week": m["week"], "relationship_key": m["relationship_key"],
                          "status": m["status"]})
        def one(u):
            return u["uid"], text_layer.generate(u["view"], u["ids"], u["assoc"], u["previous"], u["retracted"], client, tcfg, pb, lib, kinds, rows, u["uid"], refresh)
        with ThreadPoolExecutor(max_workers=int(tcfg.get("concurrency", 1))) as ex:
            results.update(dict(ex.map(one, batch)))
        for u in batch:
            units[u["uid"]] = u
    return [units[uid] for _, uid in sample], results


def unique_path(base: Path, stem: str, ext: str) -> Path:
    n = 1
    while (base / f"{stem}_{n}{ext}").exists():
        n += 1
    return base / f"{stem}_{n}{ext}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--sample", action="store_true", required=True)
    ap.add_argument("--seed", type=int, default=20260)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--drop-other-prompt-rows", action="store_true", help="explicit clean-up: delete stored texts made under another prompt version")
    ap.add_argument("--db")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = PiConfig.from_yaml(Path(a.config) if Path(a.config).is_absolute() else root / a.config, root)
    lib, pb = load_library(cfg.paths["evidence_library"]), Phrasebook.load(cfg.paths["phrasebook"])
    pb.check(lib)
    store = PiStore(a.db or cfg.paths["db_path"])
    if a.drop_other_prompt_rows:
        print("deleted", store.drop_text_rows(text_layer.PROMPT_VERSION), "stored texts made under another prompt version")
    pi = PiReader(cfg, store)
    vs = load_versions(store, cfg, pi)
    kinds = {parse_key(v["relationship_key"])[3] for v in vs} - {None}
    snap = lambda: json.dumps({t: [list(r) for r in store.conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2")] for t in P1_TABLES}, sort_keys=True)
    before = snap()
    sample = select_sample(vs, cfg.text_sample, a.seed)
    client = NoNetwork() if a.no_network else llm.make_client(cfg.text)
    rows = store.text_rows()
    t0 = time.monotonic()
    refs = text_view.FindingsSentences(cfg.paths["findings_db"])
    units, results = run_sample(pi, vs, sample, cfg.text, pb, lib, kinds, client, rows, a.refresh, cfg.regenerate_every_weeks, refs)
    refs.close()
    wall = round(time.monotonic() - t0, 1)
    for u in units:                                                                  # saved from the main thread, in a fixed order
        r = results[u["uid"]]
        if not r.from_cache and u["view"] is not None:
            store.put_text(u["uid"][0], u["uid"][1], text_layer.cache_key(u["view"], cfg.text), text_layer.view_hash(u["view"]), r.as_dict())
        elif not r.from_cache:
            store.put_text(u["uid"][0], u["uid"][1], r.status, "none", r.as_dict())
    identical = snap() == before
    log = unique_path(root / "output", f"pi_text_sample_seed{a.seed}", ".jsonl")
    with open(log, "w") as f:
        for u in units:
            r = results[u["uid"]]
            f.write(json.dumps({**{k: u[k] for k in ("uid", "why", "view", "ids", "assoc", "previous", "week", "relationship_key", "status")}, "result": r.as_dict(), "from_cache": r.from_cache}, ensure_ascii=False) + "\n")
    calls = sum(len(r.llm_raw) for r in results.values() if not r.from_cache)
    st = {}
    for r in results.values():
        st[r.status] = st.get(r.status, 0) + 1
    print(f"{len(units)} versions; model calls {calls}; from cache {sum(r.from_cache for r in results.values())}; statuses {st}; wall {wall}s; structured layer unchanged: {identical}; log {log.name}")
    store.close()
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
