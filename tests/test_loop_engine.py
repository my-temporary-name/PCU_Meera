"""Stage L1, the loop (code layer only): Findings reads PI as-of through PI's retrieval API. Unit tests of the PI adapter (`PiLive`), the earlier-conclusion items, the independent as-of
audit and the property that a PI status never changes a wording class. The real-data regression checks are in test_loop_real.py."""

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from pi_helpers import LIB, MISSED, PB, SLEEP, STRESS, finding
from test_pi_engine import NS, S, SUG, at, mk, rec, run_week
from v0_code.findings_engine.factors import NullPi, build_content
from v0_code.loop_engine import audit as laudit
from v0_code.loop_engine.pi_live import PiLive, earlier_conclusions
from v0_code.pi_engine.engine import PiReader

ROOT = Path(__file__).resolve().parent.parent
IST = ZoneInfo("Asia/Kolkata")
WORDS = {"candidate": "early", "supported": "repeated", "weakened": "fading"}


def dt(day_offset, hh=12, mm=0):
    return datetime.fromisoformat(at(day_offset, hh, mm))


def fac(key, wording="asserted", n=1, label="supported", kind="relationship"):
    return {"factor_id": f"f{n}", "kind": kind, "relationship_key": key, "label": label, "wording_class": wording}


def live(pi, strict=False, **kw):
    reader = PiReader(pi.cfg, pi.store, strict=True) if strict else pi
    return PiLive(reader, kw.get("words", WORDS), kw.get("recent", 2), kw.get("open_week", True))


def promoted(tmp_path, keys=(SLEEP,), pattern=(S, S, S)):
    """A PI with entries in week one citing each key (case_a) and the weekly job of week one run: the memories exist from Sunday 23:59:59 of week one."""
    pi, _ = mk(tmp_path, {k: __import__("pi_helpers").weekly(list(pattern)) for k in keys})
    rec(pi, "case_a", 1, 1, [(k, S, "exposed", []) for k in keys])
    run_week(pi, 0)
    return pi


# ---- reading PI as-of --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_status_and_seen_before_are_read_as_of_the_versions_time(tmp_path):
    pi = promoted(tmp_path)
    p = live(pi)
    p.at(dt(3))                                                                           # inside week one: no weekly job has run yet, so no long-term memory exists
    assert p.status(SLEEP) is None and p.seen_before(SLEEP) == "this_week" and p.seen_before(SLEEP, exclude_case="case_a") == "none"
    p.at(dt(8))                                                                           # week two: the memory written at the end of week one is visible
    assert p.status(SLEEP) is not None and p.seen_before(SLEEP) == "this_week"
    assert p.status("never@1d->x") is None and p.seen_before("never@1d->x") == "none"


def test_a_memory_written_later_is_never_seen(tmp_path):
    pi = promoted(tmp_path)
    p = live(pi)
    p.at(dt(6, 23, 59))                                                                   # one minute before the job time of week one (23:59:59)
    assert p.status(SLEEP) is None
    p.at(datetime.fromisoformat("2026-03-08T23:59:59+05:30"))                              # exactly the job time: written at or before as_of
    assert p.status(SLEEP) is not None


def test_a_strict_reader_sees_only_what_was_written_strictly_before_the_versions_time(tmp_path):
    """The loop's reads are strict, so a version never sees a write made at its own instant: a rerun over a database that already holds that write reads exactly what the first run read."""
    pi = promoted(tmp_path)
    job_time = datetime.fromisoformat("2026-03-08T23:59:59+05:30")
    strict, loose = live(pi, strict=True), live(pi)
    for p_ in (strict, loose):
        p_.at(job_time)
    assert strict.status(SLEEP) is None and loose.status(SLEEP) is not None
    strict.at(datetime.fromisoformat("2026-03-09T00:00:00+05:30"))
    assert strict.status(SLEEP) is not None
    entry_time = datetime.fromisoformat(at(1))                                              # case_a's entry was written at exactly this moment
    strict.at(entry_time)
    loose.at(entry_time)
    assert strict.seen_before(SLEEP) == "none" and loose.seen_before(SLEEP) == "this_week"
    assert strict.memory_refs([fac(SLEEP)], "c") == [] and [r["status"] for r in loose.memory_refs([fac(SLEEP)], "c")] == ["open"]


def test_every_read_is_logged_with_what_it_returned(tmp_path):
    pi = promoted(tmp_path)
    p = live(pi)
    p.at(dt(8))
    p.status(SLEEP)
    p.seen_before(SLEEP, exclude_case="case_a")
    assert [r["call"] for r in p.reads] == ["get_long_term", "get_seen_before"] and all(r["as_of"] == dt(8).isoformat() for r in p.reads)
    assert p.reads[0]["written_at"] <= dt(8).isoformat() and p.reads[0]["key"] == SLEEP


# ---- refs.pi_memories ---------------------------------------------------------------------------------------------------------------------------------------------------------
def test_memory_refs_list_the_long_term_memories_of_usable_relationships_the_open_week_and_the_sealed_weeks(tmp_path):
    pi = promoted(tmp_path, keys=(SLEEP, MISSED))
    rec(pi, "case_b", 1, 8, [(SLEEP, S, "exposed", [])])                                   # an entry in week two
    p = live(pi)
    p.at(dt(9))
    refs = p.memory_refs([fac(SLEEP, "asserted", 1), fac(MISSED, "exposure_only", 2), fac(STRESS, "asserted", 3, label="not_supported")], "case_x")
    long = [r for r in refs if r["tier"] == "long_term"]
    assert [r["relationship_key"] for r in long] == [SLEEP, MISSED] and [r.get("view_id") for r in long] == ["p1", "p2"]            # not_supported is not a usable factor
    assert all(r["written_at"] <= dt(9).isoformat() and r["version"] == 1 for r in long)
    mid = [r for r in refs if r["tier"] == "mid_term"]
    assert mid[0] == {"tier": "mid_term", "memory_id": "pi_mid_2026-W11", "status": "open", "finding_ids": ["fnd_case_b_v1"]}
    assert [m["memory_id"] for m in mid[1:]] == ["pi_mid_2026-W10"] and mid[1]["status"] == "sealed" and mid[1]["sealed_at"] <= dt(9).isoformat()


def test_only_relationships_the_view_shows_get_a_view_id_and_a_retracted_one_gets_none(tmp_path):
    pi = promoted(tmp_path, keys=(SLEEP, MISSED))
    p = live(pi)
    p.at(dt(9))
    refs = p.memory_refs([fac(SLEEP, "not_mentioned", 1), fac(MISSED, "hedged", 2)], "case_x")
    assert {r["relationship_key"]: r.get("view_id") for r in refs if r["tier"] == "long_term"} == {SLEEP: None, MISSED: "p1"}
    retracted = {**pi.get_long_term(MISSED, dt(9)), "status": "retracted", "version": 2, "written_at": dt(7).isoformat()}
    pi.store.put_long(retracted)
    refs = live(pi)
    refs.at(dt(9))
    out = refs.memory_refs([fac(MISSED, "asserted", 1)], "case_x")
    assert [(r["status"], r.get("view_id")) for r in out if r["tier"] == "long_term"] == [("retracted", None)]


def test_no_open_week_entry_means_no_open_week_ref(tmp_path):
    pi = promoted(tmp_path)
    p = live(pi, open_week=True)
    p.at(dt(9))                                                                           # week two has no entry yet
    assert [r["status"] for r in p.memory_refs([fac(SLEEP)], "c") if r["tier"] == "mid_term"] == ["sealed"]
    off = live(pi, open_week=False)
    off.at(dt(9))
    assert [r["status"] for r in off.memory_refs([fac(SLEEP)], "c") if r["tier"] == "mid_term"] == ["sealed"]


# ---- the view's earlier conclusions -------------------------------------------------------------------------------------------------------------------------------------------
def record_for(pi, factors, repeat, refs):
    return {"factors": factors, "repeat": repeat, "refs": {"pi_memories": refs}}


def test_earlier_conclusions_carry_the_state_word_the_association_text_and_the_seen_before_band(tmp_path):
    pi = promoted(tmp_path, keys=(SLEEP, MISSED))
    p = live(pi)
    p.at(dt(9))
    factors = [fac(SLEEP, "asserted", 1), fac(SLEEP, "hedged", 2), fac(MISSED, "exposure_only", 3)]
    refs = p.memory_refs(factors, "case_x")
    r = record_for(pi, factors, [{"relationship_key": SLEEP, "pi_status": "supported", "seen_before": "recent_weeks"}, {"relationship_key": MISSED, "pi_status": "supported", "seen_before": "this_week"}], refs)
    items = earlier_conclusions(r, pi, WORDS)
    assert [i["id"] for i in items] == ["p1", "p2"] and items[0]["about"] == ["f1", "f2"] and items[1]["about"] == ["f3"]
    m = pi.get_long_term(SLEEP, dt(9))
    assert items[0]["state"] == WORDS[m["status"]] and items[0]["text"] == " ".join(m["text"]["sentences"]) and items[0]["seen_before"] == "recent_weeks" and items[1]["seen_before"] == "this_week"
    assert "situations" not in items[0]                                                      # L1: the situations line is null, so the key is left out
    assert not any(ch.isdigit() for i in items for ch in i["text"])


def test_a_weakened_memory_is_fading_and_a_retracted_one_has_no_item(tmp_path):
    pi = promoted(tmp_path, keys=(SLEEP, MISSED))
    base = pi.get_long_term(SLEEP, dt(9))
    pi.store.put_long({**base, "status": "weakened", "version": 2, "written_at": dt(7).isoformat()})
    pi.store.put_long({**pi.get_long_term(MISSED, dt(9)), "status": "retracted", "version": 2, "written_at": dt(7).isoformat()})
    p = live(pi)
    p.at(dt(9))
    factors = [fac(SLEEP, "asserted", 1), fac(MISSED, "asserted", 2)]
    refs = p.memory_refs(factors, "case_x")
    items = earlier_conclusions(record_for(pi, factors, [{"relationship_key": SLEEP, "pi_status": "weakened", "seen_before": "none"}], refs), pi, WORDS)
    assert [(i["about"], i["state"]) for i in items] == [(["f1"], "fading")]


def test_the_items_come_from_the_versions_the_record_names_not_from_whatever_is_latest(tmp_path):
    pi = promoted(tmp_path)
    p = live(pi)
    p.at(dt(9))
    factors = [fac(SLEEP)]
    refs = p.memory_refs(factors, "c")
    first = earlier_conclusions(record_for(pi, factors, [{"relationship_key": SLEEP, "pi_status": "x", "seen_before": "none"}], refs), pi, WORDS)
    pi.store.put_long({**pi.get_long_term(SLEEP, dt(9)), "status": "weakened", "version": 2, "written_at": dt(13).isoformat()})          # a later version
    again = earlier_conclusions(record_for(pi, factors, [{"relationship_key": SLEEP, "pi_status": "x", "seen_before": "none"}], refs), pi, WORDS)
    assert again == first


# ---- a PI status never changes what Findings says --------------------------------------------------------------------------------------------------------------------------
class StubPi:
    def __init__(self, status, band):
        self._s, self._b = status, band

    def status(self, key):
        return self._s

    def seen_before(self, key, exclude_case=None):
        return self._b


def items_for_property():
    from test_findings_factors import example_a
    return example_a()


@pytest.mark.parametrize("status", [None, "candidate", "supported", "weakened", "retracted"])
@pytest.mark.parametrize("band", ["none", "this_week", "recent_weeks", "earlier"])
def test_property_a_pi_status_and_seen_before_never_change_a_wording_class_a_mode_or_a_group(status, band):
    base = build_content(items_for_property(), {}, LIB, PB, NullPi(), case_id="c")
    got = build_content(items_for_property(), {}, LIB, PB, StubPi(status, band), case_id="c")
    strip = lambda c: {k: v for k, v in c.items() if k != "repeat"}
    assert strip(got) == strip(base)
    assert [f["wording_class"] for f in got["factors"]] == [f["wording_class"] for f in base["factors"]] and got["mode"] == base["mode"] and got["groups"] == base["groups"]
    assert all(r["pi_status"] == status and r["seen_before"] == band for r in got["repeat"]) and all(r["pi_status"] is None and r["seen_before"] == "none" for r in base["repeat"])


# ---- the independent as-of audit ----------------------------------------------------------------------------------------------------------------------------------------
def stored(pi, tmp_path, versions):
    """The audit reads PI's database and the stored Findings records only."""
    from v0_code.findings_engine.storage import FindingsStore
    f = FindingsStore(tmp_path / "loop_f.db")
    for v in versions:
        f.put_finding(v)
    f.close()
    return tmp_path / "loop_f.db"


def version_record(case, ver, as_of, local, repeat, refs):
    base = finding(case, ver, as_of, local, [])
    return {**base, "provisional": True, "closed": False, "status": "ok", "repeat": repeat, "refs": {"diary": [], "state_memory": [], "pi_memories": refs}, "text": {**base["text"], "source": "code_line"}}


def test_the_audit_passes_a_correct_record_and_names_each_kind_of_violation(tmp_path):
    pi = promoted(tmp_path)
    rec(pi, "case_b", 1, 8, [(SLEEP, S, "exposed", [])])                                   # an entry in week two, so there is an open week to read
    p = live(pi)
    p.at(dt(9))
    refs = p.memory_refs([fac(SLEEP)], "case_x")
    m = pi.get_long_term(SLEEP, dt(9))
    good = version_record("case_x", 1, dt(9).isoformat(), "2026-03-11", [{"relationship_key": SLEEP, "pi_status": m["status"], "seen_before": "this_week"}], refs)
    cfg = pi.cfg
    pi.store.conn.commit()
    path = stored(pi, tmp_path, [good])
    bad, n = laudit.audit_pi_reads(path, pi.store.path, cfg.tz, cfg.seen_before_bands, 2, strict=False)
    assert bad == [] and n["long_term"] == 1 and n["open_week"] >= 1 and n["sealed"] == 1 and n["repeat"] == 1
    wrong_status = {**good, "finding_id": "fnd_case_y_v1", "case_id": "case_y", "repeat": [{"relationship_key": SLEEP, "pi_status": "retracted", "seen_before": "this_week"}]}
    wrong_band = {**good, "finding_id": "fnd_case_z_v1", "case_id": "case_z", "repeat": [{"relationship_key": SLEEP, "pi_status": m["status"], "seen_before": "earlier"}]}
    early = {**good, "finding_id": "fnd_case_e_v1", "case_id": "case_e", "as_of": dt(3).isoformat()}                      # claims a memory that was written after its as_of
    future_entry = {**good, "finding_id": "fnd_case_f_v1", "case_id": "case_f", "as_of": dt(9).isoformat(), "refs": {**good["refs"], "pi_memories": refs + [{"tier": "mid_term", "memory_id": "pi_mid_2026-W11", "status": "open", "finding_ids": ["fnd_case_a_v1"]}]}}
    path = stored(pi, tmp_path, [wrong_status, wrong_band, early, future_entry])
    bad, _ = laudit.audit_pi_reads(path, pi.store.path, cfg.tz, cfg.seen_before_bands, 2, strict=False)
    text = "\n".join(bad)
    assert "fnd_case_y_v1" in text and "pi_status" in text
    assert "fnd_case_z_v1" in text and "seen_before" in text
    assert "fnd_case_e_v1" in text and "written after as_of" in text
    assert "fnd_case_f_v1" in text and "open week" in text


def test_the_loop_engine_names_no_stream_measure_medicine_or_patient():
    banned = ["glucose", "heart_rate", "sleep_duration", "metformin", "amlodipine", "levothyroxine", "meal_events", "diary_context", "step_count", "hydration", "screen_time", "blood_pressure",
              "mood_state", "medication_adherence", "thyroid", "meera", "iyer", "cgm", "dinner", "lunch", "breakfast", "missed_dose", "sleep_hours", "post_meal"]
    for f in (ROOT / "src/v0_code/loop_engine").glob("*.py"):
        text = f.read_text().lower()
        for w in banned:
            assert w not in text, f"{w} appears in {f.name}"


def test_the_strict_audit_rejects_a_read_of_something_written_at_the_versions_own_moment(tmp_path):
    pi = promoted(tmp_path)
    p = live(pi)
    entry_time = dt(1)                                                                      # case_a's own entry was written at exactly this moment
    p.at(entry_time)
    refs = p.memory_refs([fac(SLEEP)], "case_x")                                           # a non-strict read lists it
    v = version_record("case_x", 1, entry_time.isoformat(), "2026-03-03", [], refs)
    path = stored(pi, tmp_path, [v])
    assert laudit.audit_pi_reads(path, pi.store.path, pi.cfg.tz, pi.cfg.seen_before_bands, 2, strict=False)[0] == []
    bad, _ = laudit.audit_pi_reads(path, pi.store.path, pi.cfg.tz, pi.cfg.seen_before_bands, 2, strict=True)
    assert any("open week" in b for b in bad)


# ---- L2: the entry text is final only at the week's barrier; the situations line comes from the overlay ------------------------------------------------------------------------
def test_an_open_weeks_entry_text_can_be_replaced_until_the_week_is_sealed_and_only_the_text_changes(tmp_path):
    from v0_code.pi_engine.engine import SealedWeekError
    pi, _ = mk(tmp_path, {SLEEP: __import__("pi_helpers").weekly([S, S, S])})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])], headline="Provisional headline.", sentences=("Provisional sentence.",))
    before = pi.store.entry_by_finding("fnd_case_a_v1")
    pi.replace_entry_text("fnd_case_a_v1", "Final headline.", ["One final sentence.", "Another."])
    after = pi.store.entry_by_finding("fnd_case_a_v1")
    assert after["headline"] == "Final headline." and after["sentences"] == ["One final sentence.", "Another."]
    assert {k: v for k, v in after.items() if k not in ("headline", "sentences")} == {k: v for k, v in before.items() if k not in ("headline", "sentences")}
    assert pi.get_open_week(dt(2))["entries"][0]["headline"] == "Final headline."
    pi.replace_entry_text("fnd_case_a_v1", "Final headline.", ["One final sentence.", "Another."])                    # the same text again is fine
    run_week(pi, 0)
    with pytest.raises(SealedWeekError):
        pi.replace_entry_text("fnd_case_a_v1", "Too late.", ["x"])
    with pytest.raises(KeyError):
        pi.replace_entry_text("no_such_entry", "x", ["y"])


def test_the_situations_line_of_a_memory_version_is_read_from_the_text_overlay(tmp_path):
    pi = promoted(tmp_path)
    m = pi.get_long_term(SLEEP, dt(9))
    assert pi.store.situations_line(m["memory_id"], m["version"]) is None
    pi.store.put_text(m["memory_id"], m["version"], "k", "h", {"text": {"sentences": m["text"]["sentences"], "source": "code_text", "situations": "In the cases noted, the situations included a festival.", "entry_ids": []},
                                                              "text_source": "code_text", "status": "ok", "llm_raw": [], "usage": [], "checks": [], "prompt_version": "pp-v4", "checks_version": "pck-v6"})
    assert pi.store.situations_line(m["memory_id"], m["version"]) == "In the cases noted, the situations included a festival."


def test_an_earlier_conclusion_carries_the_situations_line_when_there_is_one(tmp_path):
    pi = promoted(tmp_path)
    p = live(pi)
    p.at(dt(9))
    factors = [fac(SLEEP)]
    refs = p.memory_refs(factors, "c")
    r = record_for(pi, factors, [{"relationship_key": SLEEP, "pi_status": "supported", "seen_before": "none"}], refs)
    line = "In the cases noted, the situations included a festival and a work trip."
    assert "situations" not in earlier_conclusions(r, pi, WORDS)[0]
    got = earlier_conclusions(r, pi, WORDS, situations=lambda mid, ver: line)[0]["situations"]
    assert got == "a festival and a work trip"                                               # the frame is left out: its word "cases" is an internal word no view may carry
    assert "situations" not in earlier_conclusions(r, pi, WORDS, situations=lambda mid, ver: None)[0]
