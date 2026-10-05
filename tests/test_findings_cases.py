"""Cases, versions and the minimal ordered event loop (findings_engine_spec.md 5 as amended): pure replay over hand-offs, packet statuses, evidence records and completions."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from v0_code.evidence_engine.library import load_library
from v0_code.findings_engine.loop import Settings, replay
from v0_code.intel_common.phrasebook import Phrasebook

ROOT = Path(__file__).resolve().parent.parent
LIB = load_library(ROOT / "config/evidence_library_v0.yaml")
PB = Phrasebook.load(ROOT / "config/findings_phrasebook_v0.yaml")
IST = ZoneInfo("Asia/Kolkata")
T0 = datetime(2026, 3, 10, 8, 0, tzinfo=IST)
SET = Settings(gap_hours=6, max_span_hours=36, tz=IST)


def ho(n, minutes, measure="glucose", status="ok"):
    t = (T0 + timedelta(minutes=minutes)).isoformat()
    hid = f"h{n}"
    return {"handoff_id": hid, "measure": measure, "direction": "above", "size": "clearly", "opened_at": t}, status


def ev(hid, opened_at, factors=()):
    return {"evidence_id": f"ev_{hid}", "handoff_id": hid, "rule_id": "r", "event_time": opened_at, "as_of_date": opened_at[:10], "factors": list(factors), "overlap": [], "not_tested": [], "counts": {}}


def run(spec, completions=(), settings=SET, factors=None, **kw):
    handoffs, status, evidence = [], {}, {}
    for h, s in spec:
        handoffs.append(h)
        status[h["handoff_id"]] = s
        if s == "ok":
            evidence[h["handoff_id"]] = ev(h["handoff_id"], h["opened_at"], (factors or {}).get(h["handoff_id"], ()))
    return replay(handoffs, status, evidence, list(completions), settings, LIB, PB, **kw)


def cases(r):
    return [(c["case_id"], c["n_counted"]) for c in r.cases]


def test_a_handoff_exactly_the_gap_after_the_last_joins_and_one_minute_more_opens_a_new_case():
    r = run([ho(1, 0), ho(2, 360), ho(3, 360 + 361)])
    assert cases(r) == [(f"case_{(T0).isoformat()}", 2), (f"case_{(T0 + timedelta(minutes=721)).isoformat()}", 1)]


def test_the_gap_is_measured_from_the_last_handoff_not_the_first():
    r = run([ho(i, i * 300) for i in range(6)])                       # every 5 hours: one chain of 25 hours
    assert len(r.cases) == 1 and r.cases[0]["n_counted"] == 6


def test_a_case_cannot_exceed_the_max_span():
    r = run([ho(i, i * 300) for i in range(10)])                      # 5-hourly for 45 hours: the 8th would reach 35 h, the 9th 40 h
    assert [c["n_counted"] for c in r.cases] == [8, 2] and r.cases[1]["opened_at"] == (T0 + timedelta(minutes=8 * 300)).isoformat()


def test_case_id_and_local_date_follow_the_first_handoff_in_the_patients_timezone():
    late = datetime(2026, 3, 10, 18, 30, tzinfo=ZoneInfo("UTC"))                  # 00:00 on the 11th in the patient's zone
    h = {"handoff_id": "h1", "measure": "glucose", "direction": "above", "size": "clearly", "opened_at": late.isoformat()}
    r = replay([h], {"h1": "ok"}, {"h1": ev("h1", late.isoformat())}, [], SET, LIB, PB)
    assert r.cases[0]["case_id"] == f"case_{late.isoformat()}" and r.cases[0]["local_date"] == "2026-03-11"


def test_a_case_that_runs_past_midnight_keeps_its_first_local_date():
    r = run([ho(1, 14 * 60), ho(2, 14 * 60 + 300)])                    # 22:00 and 03:00 next day
    assert r.cases[0]["local_date"] == "2026-03-10" and len(r.cases) == 1


def test_deferred_and_unmatched_are_recorded_but_never_open_a_case_or_extend_the_clock():
    r = run([ho(1, 0), ho(2, 300, status="deferred"), ho(3, 660)])    # the deferred one at 5 h does not push the gap clock: 11 h after the counted one
    assert cases(r) == [(f"case_{T0.isoformat()}", 1), (f"case_{(T0 + timedelta(minutes=660)).isoformat()}", 1)]
    joined = [(x["handoff_id"], x["counted"], x["case_id"]) for x in r.case_handoffs]
    assert ("h2", False, f"case_{T0.isoformat()}") in joined and len(r.versions) == 2
    alone = run([ho(1, 0, status="unmatched")])
    assert alone.cases == [] and [u["handoff_id"] for u in alone.unattached] == ["h1"] and alone.versions == []


def test_a_deferred_handoff_after_the_gap_is_unattached_not_joined():
    r = run([ho(1, 0), ho(2, 400, status="deferred")])
    assert [u["handoff_id"] for u in r.unattached] == ["h2"] and [x["handoff_id"] for x in r.case_handoffs if not x["counted"]] == []


def test_versions_one_per_counted_handoff_numbered_with_growing_handoff_lists_and_as_of_equal_event_time():
    r = run([ho(1, 0), ho(2, 90), ho(3, 120, status="deferred"), ho(4, 200)])
    v = r.versions
    assert [(x["finding_id"], x["version"], x["as_of"], x["handoff_ids"]) for x in v] == [
        (f"fnd_case_{T0.isoformat()}_v1", 1, T0.isoformat(), ["h1"]),
        (f"fnd_case_{T0.isoformat()}_v2", 2, (T0 + timedelta(minutes=90)).isoformat(), ["h1", "h2"]),
        (f"fnd_case_{T0.isoformat()}_v3", 3, (T0 + timedelta(minutes=200)).isoformat(), ["h1", "h2", "h4"])]
    assert all(x["provisional"] is True and x["closed"] is False and x["status"] == "ok" and x["text"]["source"] == "code_line" for x in v)
    assert v[2]["evidence_ids"] == ["ev_h1", "ev_h2", "ev_h4"] and v[0]["local_date"] == "2026-03-10"


def test_closed_at_is_the_last_counted_handoff_plus_the_gap_and_no_closing_version_is_written():
    r = run([ho(1, 0), ho(2, 90), ho(3, 1000)])
    first = r.cases[0]
    assert first["last_handoff_at"] == (T0 + timedelta(minutes=90)).isoformat() and first["closed_at"] == (T0 + timedelta(minutes=90 + 360)).isoformat() and first["status"] == "closed"
    assert len(r.versions) == 3 and r.cases[1]["status"] == "closed"                 # the last case closes at the end of the data
    assert r.cases[1]["closed_at"] == (T0 + timedelta(minutes=1000 + 360)).isoformat()


SHAPE = {"rank": 1, "weight_tier": "primary", "candidate": "sensor_artifact", "check_type": "shape_check", "relationship_evidence_id": None, "support": "not_yet_available", "flags": [],
         "event_exposure": None, "event_specific": {"earliest_evaluation_time": "x"}}


def done(hid, minutes, support="supported"):
    return {"evidence_id": f"ev_h{hid}", "candidate": "sensor_artifact", "support": support, "evaluated_from": {"start": "", "end": (T0 + timedelta(minutes=minutes)).isoformat()}}


def test_a_completion_writes_a_version_at_its_time_without_extending_the_gap_clock():
    r = run([ho(1, 0), ho(2, 400)], completions=[done(1, 120)], factors={"h1": [SHAPE]})
    assert cases(r)[0][1] == 1 and len(r.cases) == 2                      # the completion at 2 h does not keep the case open to 6 h after it
    v = r.versions
    assert [(x["version"], x["as_of"], x["completion_ids"]) for x in v[:2]] == [(1, T0.isoformat(), []), (2, (T0 + timedelta(minutes=120)).isoformat(), ["ev_h1#sensor_artifact"])]
    assert v[1]["factors"][0]["wording_class"] == "artifact_note" and v[0]["factors"][0]["wording_class"] == "not_known_yet" and v[0]["not_known_yet"] == ["the readings that follow"]


def test_at_equal_times_handoffs_come_before_completions_and_ties_break_by_id():
    r = run([ho(1, 0), ho(2, 120)], completions=[done(1, 120)], factors={"h1": [SHAPE]})
    assert [x["handoff_ids"] for x in r.versions] == [["h1"], ["h1", "h2"], ["h1", "h2"]] and r.versions[2]["completion_ids"] == ["ev_h1#sensor_artifact"]
    assert r.versions[1]["completion_ids"] == []


def test_input_order_does_not_matter_and_the_replay_is_deterministic():
    spec = [ho(1, 0), ho(2, 90), ho(3, 120, status="deferred"), ho(4, 700), ho(5, 710)]
    a = run(spec)
    b = run(list(reversed(spec)))
    assert json.dumps([a.cases, a.case_handoffs, a.unattached, a.versions], sort_keys=True) == json.dumps([b.cases, b.case_handoffs, b.unattached, b.versions], sort_keys=True)
    assert json.dumps(a.versions, sort_keys=True) == json.dumps(run(spec).versions, sort_keys=True)


def test_handoffs_in_one_case_with_the_same_time_order_by_id():
    r = run([ho(2, 0), ho(1, 0)])
    assert r.versions[0]["handoff_ids"] == ["h1"] and r.versions[1]["handoff_ids"] == ["h1", "h2"]


def test_no_record_carries_a_wall_clock_field():
    r = run([ho(1, 0), ho(2, 90)])
    text = json.dumps(r.versions)
    assert "written_at" not in text and "created" not in text and "updated" not in text


def test_a_changed_gap_changes_only_the_case_boundaries():
    spec = [ho(i, i * 240) for i in range(5)]
    assert len(run(spec, settings=Settings(3, 36, IST)).cases) == 5 and len(run(spec, settings=Settings(6, 36, IST)).cases) == 1


# ---- the loop's hooks and the PI binding (stage L1) ----------------------------------------------------------------------------------------------------------------------------
class Hooks:
    def __init__(self):
        self.log = []

    def before_event(self, t):
        self.log.append(("event", t.isoformat()))

    def after_version(self, v):
        self.log.append(("version", v["finding_id"]))


def test_hooks_run_before_every_event_and_after_every_version_and_change_nothing():
    spec = [ho(1, 0), ho(2, 30, status="deferred"), ho(3, 60)]
    h = Hooks()
    r, base = run(spec, hooks=h), run(spec)
    assert r.versions == base.versions and r.cases == base.cases and r.unattached == base.unattached
    assert [k for k, _ in h.log] == ["event", "version", "event", "event", "version"]
    assert h.log[0][1] == T0.isoformat() and h.log[1][1] == f"fnd_case_{T0.isoformat()}_v1"


def test_stopping_after_n_events_keeps_the_first_versions_unchanged_and_leaves_the_open_case_open():
    spec = [ho(1, 0), ho(2, 30), ho(3, 60), ho(4, 900)]
    full, part = run(spec), run(spec, max_events=2)
    assert part.versions == full.versions[:2] and len(part.cases) == 1 and part.cases[0]["status"] == "open" and part.cases[0]["closed_at"] is None
    assert run(spec, max_events=0).versions == [] and run(spec, max_events=99).versions == full.versions


class BoundPi:
    """The PI interface Findings uses: `at` is told the version's time first, then status / seen_before / memory_refs are asked."""

    def __init__(self):
        self.now, self.calls = None, []

    def at(self, as_of):
        self.now = as_of.isoformat()

    def status(self, key):
        self.calls.append(("status", key, self.now))
        return "candidate"

    def seen_before(self, key, exclude_case=None):
        self.calls.append(("seen", key, exclude_case, self.now))
        return "this_week"

    def memory_refs(self, factors, case_id):
        self.calls.append(("refs", case_id, self.now))
        return [{"view_id": "p1", "memory_id": "m", "version": 1}]


def test_a_pi_that_is_bound_to_the_versions_time_fills_repeat_and_the_pi_memory_refs_and_never_changes_the_structured_layer():
    key = "missed_dose@2d->post_meal_peak:dinner"
    fac = {"factor_id": "x", "relationship_evidence_id": f"rel|{key}|2026-03-10|ev-v0", "candidate": "c", "support": "supported", "flags": [], "event_specific": False, "exposure": "exposed"}
    spec = [ho(1, 0)]
    base = run(spec, factors={"h1": [fac]}).versions[0]
    pi = BoundPi()
    v = run(spec, factors={"h1": [fac]}, pi=pi).versions[0]
    assert v["refs"]["pi_memories"] == [{"view_id": "p1", "memory_id": "m", "version": 1}] and base["refs"]["pi_memories"] == []
    assert pi.calls and all(c[-1] == v["as_of"] for c in pi.calls)
    strip = lambda r: {k: x for k, x in r.items() if k not in ("repeat", "refs")}
    assert strip(v) == strip(base) and {k: x for k, x in v["refs"].items() if k != "pi_memories"} == {k: x for k, x in base["refs"].items() if k != "pi_memories"}
