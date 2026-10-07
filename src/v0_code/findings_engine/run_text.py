"""Run the text layer (stage F2) on a sample of case versions.

    uv run python -m v0_code.findings_engine.run_text --config config/findings_<patient>.yaml --sample [--seed 20260] | --all   # about 30 versions -> finding_text / finding_llm + a report
    uv run python -m v0_code.findings_engine.run_text --config ... --sample --no-network                                    # the same sample with a client that refuses to be called (cache check)
    uv run python -m v0_code.findings_engine.run_text --config ... --sample --refresh                                       # recompute instead of reusing the cache

Reads the stored versions (never changes them); writes only `finding_text` and `finding_llm` of the Findings database, a JSONL log with the view and the raw answers of every
version (a new file per run), and the sample report."""

import argparse
import json
import random
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from v0_code.findings_engine import run as frun
from v0_code.findings_engine import textlayer
from v0_code.findings_engine.codeline import code_sentences
from v0_code.findings_engine.config import FindingsConfig
from v0_code.findings_engine.context import Context
from v0_code.findings_engine.storage import FindingsStore
from v0_code.findings_engine.view import backing_entries, banned_words_in_view, build_view, merge_diary, view_hash

ROOT = Path(__file__).resolve().parents[3]


class NoNetwork:
    """A client that refuses to be called: proof that a run is served from the cache."""
    calls = 0

    def __init__(self):
        self.chat = self
        self.completions = self

    def create(self, **kw):
        NoNetwork.calls += 1
        raise RuntimeError("no network call is allowed in this run")


def select_sample(versions: list[dict], seed: int, plan: dict) -> list[tuple[str, str]]:
    """(finding_id, why) in a fixed order. `plan` (config `text_sample`) names the fixed picks; the early and the seeded ones come from the last version of the other cases with a
    seeded random generator."""
    NAMED_CASES, MONTHLY, RARE, ARTIFACT = plan["named_cases"], plan["monthly"], plan["rare"], plan["artifact"]
    EARLY_END, N_EARLY, N_SEEDED = plan["early_before"], int(plan["n_early"]), int(plan["n_seeded"])
    by_id = {v["finding_id"]: v for v in versions}
    chosen: dict[str, str] = {}

    def add(fid: str, why: str) -> None:
        if fid in by_id and fid not in chosen:
            chosen[fid] = why

    for v in versions:
        if v["case_id"] in NAMED_CASES:
            add(v["finding_id"], "named case")
    for fid in MONTHLY:
        add(fid, "monthly case")
    for fid in RARE:
        add(fid, "rare class")
    add(ARTIFACT, "artifact case")
    last: dict = {}
    for v in versions:
        last[v["case_id"]] = v
    taken_cases = {by_id[f]["case_id"] for f in chosen}
    rng = random.Random(seed)
    early = [v for v in last.values() if v["local_date"] < EARLY_END and v["case_id"] not in taken_cases and v["mode"] == "descriptive" and len(v["handoff_ids"]) >= 1]
    for v in rng.sample(sorted(early, key=lambda v: v["case_id"]), N_EARLY):
        add(v["finding_id"], "early descriptive case")
    taken_cases = {by_id[f]["case_id"] for f in chosen}
    rest = sorted((v for v in last.values() if v["case_id"] not in taken_cases and v["local_date"] >= EARLY_END), key=lambda v: v["case_id"])
    months = sorted({v["local_date"][:7] for v in rest})
    rng.shuffle(months)
    pool = {m: [v for v in rest if v["local_date"][:7] == m] for m in months}
    for m in pool:
        rng.shuffle(pool[m])
    picked = 0
    while picked < N_SEEDED and any(pool.values()):
        for m in months:
            if pool[m] and picked < N_SEEDED:
                add(pool[m].pop()["finding_id"], "seeded pick")
                picked += 1
    return list(chosen.items())


def better_of(old, new):
    """Keep an accepted answer over a fallback: a new result replaces the old one only if it is accepted, or if the old one was not."""
    return new if new.status == "ok" or old.status != "ok" else old


def select_rerun(rechecked: dict, extra=(), only=None) -> list[str]:
    """The versions that go back to the model: those that still end in a fallback after the re-check, plus the named extras (ids that exist); `only` limits the list to those ids."""
    ids = {fid for fid, r in rechecked.items() if r.status != "ok"} | {e for e in extra if e in rechecked}
    return sorted(ids & set(only) if only is not None else ids)


def view_builder(cfg, pb, data, lib, ctx=None):
    """A function record -> the Findings view (as-of context, backing diary entries, optional earlier conclusions), and the Context it reads (the caller closes it)."""
    hmap = {h["handoff_id"]: h for h in data["handoffs"]}
    ctx = ctx or Context(cfg)

    def build(r: dict, pi_items: list[dict] | None = None) -> dict:
        as_of = datetime.fromisoformat(r["as_of"])
        diary, memory = ctx.diary(as_of, r["local_date"]), ctx.state_memory(as_of, r["local_date"])
        assert [(x["view_id"], x["context_id"]) for x in diary] == [(x["view_id"], x["context_id"]) for x in r["refs"]["diary"]], r["finding_id"]
        assert [(x["view_id"], x["window_id"]) for x in memory] == [(x["view_id"], x["window_id"]) for x in r["refs"]["state_memory"]], r["finding_id"]
        backing = backing_entries(r, lib, ctx.all_diary, cfg.diary["library_source"], cfg.tz, int(cfg.diary["backing_per_point"]))
        merged = merge_diary(diary, backing)
        assert all(e["at"] <= as_of for e in merged), r["finding_id"]                      # nothing after as_of, backing entries included
        view = build_view(r, [hmap[h] for h in r["handoff_ids"]], merged, memory, pb, cfg.tz, cfg.part_of_day, pi_items, cfg.state_memory.get("view"))
        bad = banned_words_in_view(view, set(pb.raw["internal_words"]))
        assert not bad, (r["finding_id"], bad)                                              # no key or value of a view is a banned word
        return view
    return build, ctx


def build_views(cfg, pb, data, versions: list[dict], lib, pi_items=None) -> dict:
    """`pi_items`: None (PI absent, as in F2) or a function record -> the view's `earlier_conclusions` items (stages L1 and L2)."""
    build, ctx = view_builder(cfg, pb, data, lib)
    out = {r["finding_id"]: build(r, pi_items(r) if pi_items else None) for r in versions}
    ctx.close()
    return out


def run_waves(tcfg: dict, pb, store, records: list[dict], views: dict, client, refresh: bool = False, wave: int = 12, stop: dict | None = None, keep: dict | None = None, allow_model: bool = True) -> tuple[dict, str | None]:
    """Run the text layer over `records` in waves. Cached versions are served first and cost nothing; the others are generated `wave` at a time (concurrency from config),
    and each finished wave is saved before the next starts, so a stopped or interrupted run resumes from the store. `stop` ({after, max_first_failure, max_call_errors}):
    once `after` new versions are done, one check of the first-attempt failure rate and the share of calls that ended in a call error; over a limit, the run stops and
    says why. Returns ({finding_id: TextResult}, stop reason or None)."""
    results: dict = {}
    if not refresh:
        for r in records:                                                          # lookups in this thread: a connection belongs to one thread
            fid = r["finding_id"]
            hit = textlayer.cached(views[fid], tcfg, store, fid)
            if hit is None:
                hit = textlayer.lookup(views[fid], r, code_sentences(r, pb), tcfg, pb, store)
                if hit is not None and not hit.needs_model:                         # an earlier compatible answer that passes: stored under the current key from now on
                    store.put_text(fid, textlayer.cache_key(views[fid], tcfg), view_hash(views[fid]), hit.as_dict())
            if hit is not None and (not hit.needs_model or not allow_model):
                results[fid] = hit
                if not hit.needs_model and fid not in store.texts_ids():           # served from a twin's entry: give this version its own row
                    store.put_text(fid, textlayer.cache_key(views[fid], tcfg), view_hash(views[fid]), hit.as_dict())
    todo = [r for r in records if r["finding_id"] not in results]
    if not allow_model:                                                            # a re-check: nothing is generated; versions with no usable stored answer stay as fallbacks
        for r in todo:
            results[r["finding_id"]] = textlayer.TextResult(textlayer.code_line_text(code_sentences(r, pb)), "code_line", "code_line_fallback", [], [], [], from_cache=True, needs_model=True)
        return results, None
    new = first_fail = calls = call_errors = 0
    checked = False

    def one(r):
        return r["finding_id"], textlayer.generate(views[r["finding_id"]], r, code_sentences(r, pb), client, tcfg, pb, None, True)

    for k in range(0, len(todo), wave):
        batch = todo[k:k + wave]
        with ThreadPoolExecutor(max_workers=int(tcfg["concurrency"])) as ex:
            done = dict(ex.map(one, batch))
        for r in batch:                                                            # saved from the main thread, in a fixed order
            res = done[r["finding_id"]]
            if keep and r["finding_id"] in keep:
                res = better_of(keep[r["finding_id"]], res)                          # a new fallback never replaces an accepted older answer
            store.put_text(r["finding_id"], textlayer.cache_key(views[r["finding_id"]], tcfg), view_hash(views[r["finding_id"]]), res.as_dict())
            results[r["finding_id"]] = res
            new += 1
            first_fail += bool(res.checks[0])
            calls += len(res.checks)
            call_errors += sum(1 for att in res.checks if att and att[0]["check"] == 0)
        if stop and not checked and new >= int(stop["after"]):
            checked = True
            if first_fail / new > float(stop["max_first_failure"]):
                return results, f"stopped after {new} new versions: {first_fail} ({100 * first_fail / new:.0f}%) failed their first attempt (limit {100 * float(stop['max_first_failure']):.0f}%)"
            if call_errors / calls > float(stop["max_call_errors"]):
                return results, f"stopped after {new} new versions: {call_errors} of {calls} calls ({100 * call_errors / calls:.0f}%) ended in a call error (limit {100 * float(stop['max_call_errors']):.0f}%)"
    return results, None


def unique_path(base: Path, stem: str, ext: str) -> Path:
    n = 1
    while (base / f"{stem}_{n}{ext}").exists():
        n += 1
    return base / f"{stem}_{n}{ext}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--root", default=str(ROOT))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sample", action="store_true", help="the sample of about 30 versions")
    mode.add_argument("--all", action="store_true", help="every stored version, in waves, resumable, with the stop rules of config text.stop")
    mode.add_argument("--recheck", action="store_true", help="NO model calls: judge every saved answer again under the current checks (answers from a compatible earlier prompt are accepted if they pass)")
    mode.add_argument("--rerun", action="store_true", help="re-check, then ask the model (current prompt) only for the versions that still end in a fallback and those whose first attempt failed check 6")
    ap.add_argument("--seed", type=int, default=20260)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--no-network", action="store_true")
    ap.add_argument("--db")
    ap.add_argument("--only", action="append", default=None, help="with --rerun: send back only these finding ids (repeatable)")
    ap.add_argument("--also", action="append", default=[], help="with --rerun: a finding id to send back to the model as well (repeatable)")
    a = ap.parse_args(argv)
    root = Path(a.root)
    cfg = FindingsConfig.from_yaml(Path(a.config) if Path(a.config).is_absolute() else root / a.config, root)
    lib, pb, data = frun.prepare(cfg)
    db = a.db or cfg.paths["db_path"]
    store = FindingsStore(db)
    versions = store.findings()
    before = {r[0]: r[1] for r in store.conn.execute("SELECT finding_id, record_json FROM findings")}
    store.adopt_legacy(textlayer.settings_key(cfg.text), "p-v1", "ck-v3")                      # rows written before prompt versions were recorded were made under p-v1 / ck-v3
    sample = select_sample(versions, a.seed, cfg.text_sample) if a.sample else [(v["finding_id"], "full run") for v in versions]
    by_id = {v["finding_id"]: v for v in versions}
    records = [by_id[f] for f, _ in sample]
    views = build_views(cfg, pb, data, records, lib)
    client = NoNetwork() if a.no_network else textlayer.llm.make_client(cfg.text)
    NoNetwork.calls = 0
    import time
    t0 = time.monotonic()
    wave = int(cfg.text.get("wave", 12))
    if a.recheck or a.rerun:
        was = {fid: t["status"] for fid, t in store.texts().items()}
        results, reason = run_waves(cfg.text, pb, store, records, views, client, False, wave=wave, allow_model=False)
        after_recheck = sum(r.status != "ok" for r in results.values())
        print(f"re-check (no model calls): fallbacks before {sum(v != 'ok' for v in was.values())}, after {after_recheck}; accepted under the current checks from an earlier prompt: "
              f"{sum(1 for r in results.values() if r.from_prompt)}; stored versions needing the model: {sum(r.needs_model for r in results.values())}")
        if a.rerun:
            ids = select_rerun(results, a.also, a.only)
            subset = [r for r in records if r["finding_id"] in set(ids)]
            print(f"going back to the model for {len(subset)} versions: {sum(results[i].status != 'ok' for i in ids)} still fallbacks, {sum(results[i].status == 'ok' for i in ids)} named extras")
            fresh, reason = run_waves(cfg.text, pb, store, subset, views, client, True, wave=wave, keep={i: results[i] for i in ids})
            results.update(fresh)
    else:
        results, reason = run_waves(cfg.text, pb, store, records, views, client, a.refresh, wave=wave, stop=cfg.text.get("stop") if a.all else None)
    wall = round(time.monotonic() - t0, 1)
    after = {r[0]: r[1] for r in store.conn.execute("SELECT finding_id, record_json FROM findings")}
    identical = before == after
    log = unique_path(root / "output", f"findings_text_sample_seed{a.seed}" if a.sample else "findings_text_recheck" if a.recheck else "findings_text_rerun" if a.rerun else "findings_text_full", ".jsonl")
    with open(log, "w") as f:
        for fid, why in sample:
            if fid not in results:
                continue
            r = results[fid]
            f.write(json.dumps({"finding_id": fid, "why": why, "view_hash": view_hash(views[fid]), "view": views[fid], "result": r.as_dict(), "from_cache": r.from_cache}, ensure_ascii=False) + "\n")
    calls = sum(len(r.llm_raw) for r in results.values() if not r.from_cache)
    print(f"{len(results)} of {len(sample)} versions; model calls {calls}; from cache {sum(r.from_cache for r in results.values())}; fallbacks {sum(r.status != 'ok' for r in results.values())}; "
          f"wall {wall}s; stored versions unchanged: {identical}; log {log.name}")
    if reason:
        print("STOPPED:", reason)
    store.close()
    return 0 if identical and not reason else 1


if __name__ == "__main__":
    sys.exit(main())
