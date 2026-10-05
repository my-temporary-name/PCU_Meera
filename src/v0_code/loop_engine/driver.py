"""The loop driver (stage L1, code layer only; pi_spec.md 11 and findings_engine_spec.md 5): Findings runs LIVE, in time order, with PI.

Findings' own event loop (hand-offs and completions by time) is the clock. `LoopHooks.before_event(t)` runs PI's weekly job for every week end that lies before the event, so the memories
written at a week end are visible to everything after it; `after_version` puts each version into PI's open week (`record_finding`) the moment it is written, so the next version can see
it. Findings reads PI only through `PiLive` (PI's retrieval calls, as-of, STRICT: a version sees only what was written strictly before its own time, so a write at the same instant never changes what it read and a rerun reads exactly what the first run read). At the end of the data the remaining weekly jobs run, the last one at the final day (23:59:59).

Writes only to the loop's own databases (Findings' tables in `findings_loop.db`, PI's in `pi_loop.db`). Idempotent and resumable: every step is a function of what is as-of, so a run over
existing databases writes nothing new and a run that stopped early (`max_events`) is continued by running again."""

from dataclasses import dataclass, field
from datetime import datetime

from v0_code.findings_engine.context import Context
from v0_code.findings_engine.loop import Settings, replay
from v0_code.findings_engine.run import prepare
from v0_code.findings_engine.storage import FindingsStore
from v0_code.loop_engine.config import LoopConfig
from v0_code.loop_engine.pi_live import PiLive
from v0_code.pi_engine.driver import schedule
from v0_code.pi_engine.engine import PiReader
from v0_code.pi_engine.run import build as build_pi


@dataclass
class LoopHooks:
    pi: object
    jobs: list
    next_job: int = 0
    versions_written: int = 0
    versions_same: int = 0
    weeks_run: int = 0
    weeks_new: int = 0

    def __post_init__(self):
        self.final_time = self.jobs[-1][1]

    def _run(self, i: int) -> None:
        week, t = self.jobs[i]
        self.weeks_new += self.pi.store.get_run(week.iso) is None
        self.pi.weekly_job(week, t)
        self.weeks_run += 1

    def before_event(self, t) -> None:
        while self.next_job < len(self.jobs) and self.jobs[self.next_job][1] < t:
            self._run(self.next_job)
            self.next_job += 1

    def after_version(self, version: dict) -> None:
        if datetime.fromisoformat(version["as_of"]) > self.final_time:
            raise ValueError(f"{version['finding_id']} is later than the end of the data")
        if self.pi.record_finding(version) == "written":
            self.versions_written += 1
        else:
            self.versions_same += 1

    def finish(self) -> None:
        while self.next_job < len(self.jobs):
            self._run(self.next_job)
            self.next_job += 1


@dataclass
class LoopResult:
    replay: object
    pi: object
    live: PiLive
    context_reads: list
    counts: dict = field(default_factory=dict)
    stopped: bool = False


def run_loop(cfg: LoopConfig, rebuild: bool = False, max_events: int | None = None) -> LoopResult:
    fcfg = cfg.findings
    lib, pb, data = prepare(fcfg)
    pi = build_pi(cfg.pi, rebuild=rebuild, db=cfg.pi_db)
    hooks = LoopHooks(pi, schedule(pi))
    live = PiLive(PiReader(cfg.pi, pi.store, strict=True), cfg.state_words, int(fcfg.pi.get("mid_term_recent_weeks", 2)), bool(fcfg.pi.get("include_open_week", True)))
    ctx = Context(fcfg)
    settings = Settings(fcfg.gap_hours, fcfg.max_span_hours, fcfg.tz)
    result = replay(data["handoffs"], data["packet_status"], data["evidence"], data["completions"], settings, lib, pb, pi=live, context=ctx, hooks=hooks, max_events=max_events)
    stopped = max_events is not None and max_events < len(data["handoffs"]) + len(data["completions"])
    if not stopped:
        hooks.finish()
        pi.store.clear_progress("stopped_after_events")
        pi.store.set_progress("done", "1")
    else:
        pi.store.set_progress("stopped_after_events", max_events)
    ctx.close()
    store = FindingsStore(cfg.findings_db, rebuild=rebuild)
    counts = store.write_replay(result, {"method_version": fcfg.method_version, "config_version": fcfg.version, "phrasebook_version": pb.raw.get("version", ""), "library_version": lib.version,
                                         "loop_config_version": cfg.version, "loop_stage": "L1"})
    store.close()
    counts.update({"weeks_run": hooks.weeks_run, "weeks_new": hooks.weeks_new, "entries_written": hooks.versions_written, "entries_same": hooks.versions_same})
    return LoopResult(result, pi, live, ctx.reads, counts, stopped)
