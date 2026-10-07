"""Stage L2: the loop LIVE with the models (findings_engine_spec.md amendment Z, pi_spec.md amendments 44 to 47).

Findings' event loop is the clock, as in L1 (strict PI reads; the structured layer of every version is exactly L1's). What is new is the text, written week by week:

- `after_version`: each version is put into PI's open week at once with its CODE LINE text, so the structured reads of the later versions (`seen_before`, the open-week references) are the
  same as in L1. The version is kept for the week's barrier.
- the BARRIER, run when an event lies past a week end (and at the end of the data): (1) the Findings texts of the week's versions are written, concurrency `l2.concurrency`; their views
  hold the earlier conclusions as of the version's time (strict reads, so they depend only on PI as of the last weekly jobs: the versions of a week are independent); an answer from the
  F2 database is kept for a view that did not change if it passes the current checks; (2) each entry's text is replaced by the final text (nothing else of the entry changes); (3) PI's
  weekly job runs; (4) the situations lines of the memory versions the job wrote are generated (diary-only sentences of the week's entries), concurrency the same.
- Stop rules: after the first `stop.after_calls` model calls, if more than `max_first_failure` of the versions failed their first attempt or more than `max_call_errors` of the calls ended
  in an API error or timeout, the run stops (`StopLoop`) with everything saved; running again continues.

Writes only the L2 databases. Idempotent and resumable: texts are cached by view, finished weeks are skipped, entries already recorded are not recorded again."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime

from v0_code.findings_engine import llm, textlayer
from v0_code.findings_engine.context import Context
from v0_code.findings_engine.factors import parse_key
from v0_code.findings_engine.loop import Settings, replay
from v0_code.findings_engine.run import prepare
from v0_code.findings_engine.run_text import view_builder
from v0_code.findings_engine.storage import FindingsStore
from v0_code.findings_engine.view import view_hash, view_ids
from v0_code.loop_engine.config import LoopConfig
from v0_code.loop_engine.pi_live import PiLive, earlier_conclusions
from v0_code.pi_engine import text_layer as pi_text_layer
from v0_code.pi_engine import text_view
from v0_code.pi_engine.driver import schedule
from v0_code.pi_engine.engine import PiReader
from v0_code.pi_engine.run import build as build_pi
from v0_code.pi_engine.storage import PiStore


class StopLoop(RuntimeError):
    pass


@dataclass
class Counters:
    calls: int = 0
    versions: int = 0
    first_fail: int = 0
    call_errors: int = 0
    checked: bool = False


@dataclass
class L2Result:
    replay: object
    pi: object
    live: PiLive
    log: dict
    counters: Counters
    findings_db: str = ""
    pi_db: str = ""
    notes: dict = field(default_factory=dict)


def _sentences(text: dict) -> list[str]:
    return [s["text"] if isinstance(s, dict) else s for s in text["sentences"]]


class L2Hooks:
    def __init__(self, cfg: LoopConfig, pi, live, jobs, build, ctx, lib, pb, kinds, fstore, client, seeds, f2, pi_seeds, prev=None):
        self.cfg, self.pi, self.live, self.jobs, self.build, self.lib, self.pb, self.kinds = cfg, pi, live, jobs, build, lib, pb, kinds
        self.fstore, self.client, self.seeds, self.f2, self.pi_seeds, self.prev = fstore, client, seeds, f2, pi_seeds, prev
        self.fcfg, self.tcfg, self.ptcfg = cfg.findings, cfg.findings.text, cfg.pi.text
        self.reader = live.reader
        self.next_job, self.buffer, self.counters = 0, [], Counters()
        self.stop = cfg.l2["stop"]
        self.workers = int(cfg.l2["concurrency"])
        self.refs_src = text_view.FindingsSentences(fstore.path)
        self.prefix = cfg.pi.text.get("diary_ref_prefix", "d")
        self.final_time = jobs[-1][1]
        self.entries_written = self.entries_same = 0
        self.weeks_run = self.weeks_skipped = 0
        self.log = {"barriers": [], "calls": []}
        self.t0 = time.monotonic()
        self.all_versions: list[dict] = []

    # ---- the clock --------------------------------------------------------------------------------------------------------------------------------------
    def before_event(self, t) -> None:
        while self.next_job < len(self.jobs) and self.jobs[self.next_job][1] < t:
            self.barrier(self.next_job)
            self.next_job += 1

    def after_version(self, v: dict) -> None:
        if datetime.fromisoformat(v["as_of"]) > self.final_time:
            raise ValueError(f"{v['finding_id']} is later than the end of the data")
        self.all_versions.append(v)
        if self.pi.store.entry_by_finding(v["finding_id"]) is None:               # recorded with the code line; the final text goes in at the barrier
            self.pi.record_finding(v)
            self.entries_written += 1
        else:
            self.entries_same += 1
        self.buffer.append(v)

    def finish(self) -> None:
        while self.next_job < len(self.jobs):
            self.barrier(self.next_job)
            self.next_job += 1

    # ---- one barrier ------------------------------------------------------------------------------------------------------------------------------------
    def barrier(self, i: int) -> None:
        week, job_time = self.jobs[i]
        versions, self.buffer = self.buffer, []
        if self.pi.store.get_run(week.iso) is not None:                            # finished in an earlier run: its texts, entries and lines are stored
            self.weeks_skipped += 1
            return
        b = {"barrier": i, "week": week.iso, "job_time": job_time.isoformat(), "versions": [v["finding_id"] for v in versions], "texts_start": self._now()}
        results = self.texts(i, versions)
        b["texts_end"] = self._now()
        for v in versions:
            t = results[v["finding_id"]].text
            self.pi.replace_entry_text(v["finding_id"], t["headline"], _sentences(t))
        b["job_at"] = self._now()
        self.pi.weekly_job(week, job_time)
        self.weeks_run += 1
        b["lines_start"] = self._now()
        b["lines"] = self.lines(i, week, job_time)
        b["lines_end"] = self._now()
        self.log["barriers"].append(b)

    def _now(self) -> float:
        return round(time.monotonic() - self.t0, 3)

    # ---- the Findings texts of the week ---------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _call_error(checks: list) -> bool:
        return any(att and att[0]["check"] == 0 for att in checks)

    def _acceptable(self, hit: dict) -> bool:
        """A stored result is used as it is if it is a text, or a genuine fallback (the checks failed twice): a rerun then makes no call. A fallback that came from an API error or timeout is not."""
        return hit["status"] == "ok" or not self._call_error(hit["checks"])

    def _own_recheck(self, store, view: dict, v: dict, code: list[str]):
        """The version's OWN accepted answer in another database (the F2 text), judged again under the current checks and the current view; kept if it passes. Another version's answer for an
        identical view (a twin) is not used here."""
        for row in store.find_texts(view_hash(view), textlayer.settings_key(self.tcfg), [textlayer.PROMPT_VERSION, *textlayer.COMPATIBLE_PROMPTS.get(textlayer.PROMPT_VERSION, ())], v["finding_id"]):
            if row["finding_id"] != v["finding_id"]:
                continue
            r = textlayer.reevaluate(row, view, v, code, self.pb, self.tcfg, view_ids(view))
            if r.status == "ok":
                return r
        return None

    def _recheck(self, row: dict, view: dict, v: dict, code: list[str]):
        """A stored result judged again under the current checks and cleanup, from the answer the model gave (a text) or from its saved answers in order (a fallback). Returns a TextResult
        that passes, or None."""
        if row["text_source"] == "llm" and (row["text"] or {}).get("raw"):
            text, _ = textlayer.evaluate(json.dumps(row["text"]["raw"]), view, v, self.pb, self.tcfg, view_ids(view))
            if text is None:
                return None
            prompt = row.get("prompt_version") or textlayer.PROMPT_VERSION
            return textlayer.TextResult(text, "llm", "ok", row["llm_raw"], row["usage"], row["checks"], from_cache=True, prompt_version=prompt,
                                        from_prompt=row.get("from_prompt") or (prompt if prompt != textlayer.PROMPT_VERSION else None), settings_key=textlayer.settings_key(self.tcfg))
        if row["text_source"] != "llm":
            r = textlayer.reevaluate(row, view, v, code, self.pb, self.tcfg, view_ids(view))
            return r if r.status == "ok" else None
        return None

    def decide(self, view: dict, v: dict, code: list[str], unchanged: bool):
        """(a stored answer or None, why). In this order: (1) this version's own row in this run's database (a resume); (2) the previous run's row for this version, if its view hash equals the
        current one and its saved answer still passes the current checks (`kept`, or `kept_recleaned` when the cleanup changes its text), or a fallback whose saved answers now pass; (3) its own row
        in a seed database, then an identical-view answer (a twin) of this run or a seed. Otherwise the model, with the reason: no previous row, the view changed (merged things, or the earlier
        conclusions), the old text now fails, or the old fallback still fails. Without a previous run the F2 database is used as before (the version's own text for a view that did not change)."""
        fid, key = v["finding_id"], textlayer.cache_key(view, self.tcfg)
        hit = self.fstore.get_cached(key, fid)
        if hit is not None and hit["finding_id"] == fid and self._acceptable(hit):
            return textlayer._from_row(hit, self.tcfg), "resume"
        why = "no_previous"
        if self.prev is not None:
            row = self.prev.own_row(fid)
            if row is not None:
                if row["view_hash"] == view_hash(view):
                    r = self._recheck(row, view, v, code)
                    if r is not None:
                        same = [s["text"] if isinstance(s, dict) else s for s in r.text["sentences"]] == [s["text"] if isinstance(s, dict) else s for s in row["text"]["sentences"]] and r.text["headline"] == row["text"]["headline"]
                        return r, "kept" if same else "kept_recleaned"
                    why = "fallback_before" if row["text_source"] != "llm" else "fails_now"
                else:
                    why = "view_changed:" + ("merged_things" if any("ids" in t for t in view["things"]) else "earlier_conclusions")
        elif self.f2 is not None and unchanged:
            r = self._own_recheck(self.f2, view, v, code)
            if r is not None:
                return r, "f2"
        for store in self.seeds:
            hit = store.get_cached(key, fid)
            if hit is not None and hit["finding_id"] == fid and self._acceptable(hit):
                return textlayer._from_row(hit, self.tcfg), "seed"
        for store in [self.fstore] + self.seeds:
            hit = store.get_cached(key, fid)
            if hit is not None and self._acceptable(hit):
                return textlayer._from_row(hit, self.tcfg), "twin"
        return None, why

    def texts(self, i: int, versions: list[dict]) -> dict:
        results, todo = {}, []
        for v in versions:
            items = earlier_conclusions(v, self.reader, self.cfg.state_words, self.pi.store.situations_line)
            view = self.build(v, items)
            code = [v["text"]["headline"]] + [s["text"] for s in v["text"]["sentences"]]
            hit, why = self.decide(view, v, code, unchanged=not items)
            if hit is not None:
                results[v["finding_id"]] = hit
                self.fstore.put_text(v["finding_id"], textlayer.cache_key(view, self.tcfg), view_hash(view), hit.as_dict())
                self.log["calls"].append({"barrier": i, "phase": "findings_text", "id": v["finding_id"], "as_of": v["as_of"], "attempts": 0, "from_cache": True, "from_prompt": hit.from_prompt,
                                          "p_items": len(items), "status": hit.status, "cause": why})
            else:
                todo.append((v, view, code, len(items), why))

        def one(task):
            v, view, code, _, _why = task
            return textlayer.generate(view, v, code, self.client, self.tcfg, self.pb, None, False, True)

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            done = list(ex.map(one, todo))
        for (v, view, code, n_items, why), r in zip(todo, done):                     # saved from the main thread, in time order
            self.fstore.put_text(v["finding_id"], textlayer.cache_key(view, self.tcfg), view_hash(view), r.as_dict())
            results[v["finding_id"]] = r
            self._count(r.checks)
            self.log["calls"].append({"barrier": i, "phase": "findings_text", "id": v["finding_id"], "as_of": v["as_of"], "attempts": len(r.checks), "from_cache": False, "p_items": n_items,
                                      "status": r.status, "first_attempt_failed": bool(r.checks and r.checks[0]), "cause": why})
        self.check_stop()
        return results

    # ---- the PI situations lines of the weekly job ------------------------------------------------------------------------------------------------------
    def lines(self, i: int, week, job_time) -> list[dict]:
        written = self.pi.store.long_written_at(job_time.isoformat())
        rows = {}
        for src in [self.pi.store] + self.pi_seeds:
            for k, lst in src.text_rows().items():
                rows.setdefault(k, []).extend((u, r) for u, r in lst if not self._call_error(r.get("checks") or []))          # a line lost to an API error is tried again
        tasks, out = [], []
        for m in written:
            retracted = m["status"] == "retracted"
            prev_text = self.pi.store.text_of(m["memory_id"], m["version"] - 1) if m["version"] > 1 else None
            previous = {"line": prev_text["situations"], "entry_ids": prev_text["entry_ids"]} if prev_text and prev_text.get("situations") else None
            regenerated = text_view.regeneration_due(m["created_week"], week.iso, self.cfg.pi.regenerate_every_weeks)
            view, ids = (None, []) if retracted else text_view.build_view(self.pi, m, previous, regenerated, self.pb, self.lib, self.kinds, self.refs_src, self.prefix)
            tasks.append((m, view, ids, previous, retracted))

        def one(task):
            m, view, ids, previous, retracted = task
            return pi_text_layer.generate(view, ids, m["text"], previous, retracted, self.client, self.ptcfg, self.pb, self.lib, self.kinds, rows, (m["memory_id"], m["version"]), False, True)

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            done = list(ex.map(one, tasks))
        for (m, view, ids, previous, retracted), r in zip(tasks, done):
            if view is not None:
                self.pi.store.put_text(m["memory_id"], m["version"], pi_text_layer.cache_key(view, self.ptcfg), pi_text_layer.view_hash(view), r.as_dict())
            else:
                self.pi.store.put_text(m["memory_id"], m["version"], r.status, "none", r.as_dict())
            called = bool(r.llm_raw) and not r.from_cache
            if called:
                self._count(r.checks)
            rec = {"barrier": i, "phase": "pi_line", "id": f"{m['memory_id']}#{m['version']}", "as_of": job_time.isoformat(), "attempts": len(r.llm_raw) if called else 0, "from_cache": r.from_cache,
                   "status": r.status, "entry_ids": ids, "first_attempt_failed": bool(called and r.checks and r.checks[0])}
            self.log["calls"].append(rec)
            out.append(rec)
        self.check_stop()
        return out

    # ---- stop rules -------------------------------------------------------------------------------------------------------------------------------------
    def _count(self, checks: list) -> None:
        c = self.counters
        c.versions += 1
        c.calls += len(checks)
        c.first_fail += bool(checks and checks[0])
        c.call_errors += sum(1 for att in checks if att and att[0]["check"] == 0)

    def check_stop(self) -> None:
        c = self.counters
        if c.checked or c.calls < int(self.stop["after_calls"]):
            return
        c.checked = True
        if c.first_fail / c.versions > float(self.stop["max_first_failure"]):
            raise StopLoop(f"stopped after {c.calls} model calls: {c.first_fail} of {c.versions} versions ({100 * c.first_fail / c.versions:.0f}%) failed their first attempt (limit {100 * float(self.stop['max_first_failure']):.0f}%)")
        if c.call_errors / c.calls > float(self.stop["max_call_errors"]):
            raise StopLoop(f"stopped after {c.calls} model calls: {c.call_errors} calls ({100 * c.call_errors / c.calls:.0f}%) ended in an API error or timeout (limit {100 * float(self.stop['max_call_errors']):.0f}%)")


def run_l2(cfg: LoopConfig, client, rebuild: bool = False, findings_db: str | None = None, pi_db: str | None = None, seeds: tuple = (), pi_seeds: tuple = (), use_f2: bool = True) -> L2Result:
    fcfg = cfg.findings
    lib, pb, data = prepare(fcfg)
    fdb, pdb = findings_db or cfg.l2["findings_db"], pi_db or cfg.l2["pi_db"]
    pi = build_pi(cfg.pi, rebuild=rebuild, db=pdb)
    reader = PiReader(cfg.pi, pi.store, strict=True)
    live = PiLive(reader, cfg.state_words, int(fcfg.pi.get("mid_term_recent_weeks", 2)), bool(fcfg.pi.get("include_open_week", True)))
    ctx = Context(fcfg)
    build, _ = view_builder(fcfg, pb, data, lib, ctx)
    fstore = FindingsStore(fdb, rebuild=rebuild)
    previous = cfg.l2.get("previous") if use_f2 else None
    prev = FindingsStore(previous["findings_db"], readonly=True) if previous else None
    f2 = FindingsStore(cfg.l2["f2_db"], readonly=True) if use_f2 and cfg.l2.get("f2_db") and not previous else None
    seed_stores = [FindingsStore(p, readonly=True) for p in seeds]
    pi_seed_stores = [PiStore(p, readonly=True) for p in pi_seeds] + ([PiStore(previous["pi_db"], readonly=True)] if previous else [])
    kinds = {parse_key(r[0])[3] for r in pi.labels.conn.execute("SELECT DISTINCT relationship_key FROM relationship_evidence WHERE status = 'current'")} - {None}
    hooks = L2Hooks(cfg, pi, live, schedule(pi), build, ctx, lib, pb, kinds, fstore, client, seed_stores, f2, pi_seed_stores, prev)
    settings = Settings(fcfg.gap_hours, fcfg.max_span_hours, fcfg.tz)
    stopped = None
    result = None
    try:
        result = replay(data["handoffs"], data["packet_status"], data["evidence"], data["completions"], settings, lib, pb, pi=live, context=ctx, hooks=hooks)
        hooks.finish()
        pi.store.clear_progress("stopped")
        pi.store.set_progress("done", "1")
    except StopLoop as e:
        stopped = str(e)
        pi.store.set_progress("stopped", stopped)
    meta = {"method_version": fcfg.method_version, "config_version": fcfg.version, "phrasebook_version": pb.raw.get("version", ""), "library_version": lib.version, "loop_config_version": cfg.version,
            "loop_stage": "L2", "prompt_version": textlayer.PROMPT_VERSION, "checks_version": textlayer.textcheck.CHECKS_VERSION}
    if result is not None:
        fstore.write_replay(result, meta)
    else:
        for v in hooks.all_versions:                                                    # a stop: the versions made so far (the rest is made again when the run continues)
            fstore.put_finding(v)
    if hooks.log["barriers"]:                                                           # the log of this run is added to the earlier runs' (a run that finds every week done adds nothing)
        old = fstore.conn.execute("SELECT value FROM meta WHERE key = 'l2_call_log'").fetchone()
        merged = json.loads(old[0]) if old else {"runs": 0, "barriers": [], "calls": []}
        merged["runs"] += 1
        merged["barriers"] += [{**b, "run": merged["runs"]} for b in hooks.log["barriers"]]
        merged["calls"] += [{**c, "run": merged["runs"]} for c in hooks.log["calls"]]
        fstore.conn.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", ("l2_call_log", json.dumps(merged, ensure_ascii=False)))
        fstore.conn.commit()
    ctx.close()
    hooks.refs_src.close()
    for s in seed_stores + ([f2] if f2 else []) + ([prev] if prev else []):
        s.close()
    for s in pi_seed_stores:
        s.close()
    fstore.close()
    res = L2Result(result, pi, live, hooks.log, hooks.counters, fdb, pdb, {"stopped": stopped, "weeks_run": hooks.weeks_run, "weeks_skipped": hooks.weeks_skipped, "entries_written": hooks.entries_written,
                                                                           "entries_same": hooks.entries_same})
    if stopped:
        raise StopLoop(stopped)
    return res
