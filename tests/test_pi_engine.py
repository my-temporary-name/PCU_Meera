"""PI: record_finding, the mid-term memories, the weekly job, and the retrieval calls (pi_spec.md 4 to 9, as amended)."""

import json
import sqlite3
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from pi_helpers import LIB, MISSED, PB, SLEEP, START, STRESS, finding, make_cfg, make_evidence, weekly
from v0_code.pi_engine.engine import Pi, PiConflict, SealedWeekError
from v0_code.pi_engine.storage import PiStore
from v0_code.pi_engine.weeks import week_end_time, week_of_date

IST = ZoneInfo("Asia/Kolkata")
S, SUG, NS = "supported", "suggestive", "not_supported"


def mk(tmp_path, keys, **cfg_over):
    labels = make_evidence(tmp_path, keys)
    cfg = make_cfg(tmp_path, **cfg_over)
    return Pi(cfg, PiStore(cfg.paths["db_path"]), labels, LIB, PB), cfg


def wk(n):
    """Week n of the test span (0 = Mon 2 Mar)."""
    return week_of_date(date.fromordinal(START.toordinal() + 7 * n))


def run_week(pi, n):
    w = wk(n)
    return pi.weekly_job(w, week_end_time(w, IST))


def at(day_offset, hh=12, mm=0):
    d = date.fromordinal(START.toordinal() + day_offset)
    return f"{d.isoformat()}T{hh:02d}:{mm:02d}:00+05:30"


def rec(pi, case, version, day_offset, rels, hh=12, mm=0, local=None, **kw):
    local_date = local or date.fromordinal(START.toordinal() + day_offset).isoformat()
    return pi.record_finding(finding(case, version, at(day_offset, hh, mm), local_date, rels, **kw))


# ---- record_finding and the mid-term memory --------------------------------------------------------------------------------------------------------------------------
def test_an_entry_lands_in_the_week_of_its_as_of_not_of_its_local_date(tmp_path):
    pi, _ = mk(tmp_path, {})
    rec(pi, "case_a", 1, 6, [], hh=23, mm=30)                                                     # Sunday 23:30, week one
    rec(pi, "case_a", 2, 7, [], hh=0, mm=20, local="2026-03-08")                                  # Monday 00:20 on the clock, local date still Sunday
    one, two = pi.get_open_week(at(6, 23, 45)), pi.get_open_week(at(7, 1))
    assert one["week"]["iso"] == "2026-W10" and two["week"]["iso"] == "2026-W11"
    assert [(e["case_id"], e["entry_version"], e["local_date"]) for e in two["entries"]] == [("case_a", 2, "2026-03-08")]


def test_recording_the_same_finding_twice_writes_nothing_and_a_changed_one_is_a_conflict(tmp_path):
    pi, _ = mk(tmp_path, {})
    assert rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])]) == "written"
    before = pi.store.conn.execute("SELECT COUNT(*) FROM pi_mid_entries").fetchone()[0], pi.store.conn.execute("SELECT COUNT(*) FROM pi_mid_memories").fetchone()[0]
    assert rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])]) == "same"
    assert (pi.store.conn.execute("SELECT COUNT(*) FROM pi_mid_entries").fetchone()[0], pi.store.conn.execute("SELECT COUNT(*) FROM pi_mid_memories").fetchone()[0]) == before
    with pytest.raises(PiConflict):
        rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])], headline="Another headline.")


def test_new_versions_of_a_case_append_entry_versions_and_the_latest_wins(tmp_path):
    pi, _ = mk(tmp_path, {})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])], headline="first")
    rec(pi, "case_a", 2, 1, [(SLEEP, S, "exposed", []), (MISSED, S, "exposed", [])], hh=14, headline="second")
    wk1 = pi.get_open_week(at(1, 15))
    assert [(e["entry_version"], e["headline"]) for e in wk1["entries"]] == [(2, "second")]
    assert sorted(wk1["relationship_keys_touched"]) == sorted([SLEEP, MISSED]) and wk1["case_days"] == ["2026-03-03"]
    assert pi.get_open_week(at(1, 13))["entries"][0]["entry_version"] == 1                       # as-of: the second version was not there yet
    assert pi.store.conn.execute("SELECT COUNT(*) FROM pi_mid_entries").fetchone()[0] == 2        # both versions are kept


def test_an_entry_holds_the_usable_relationships_and_no_event_level_or_unusable_factor(tmp_path):
    pi, _ = mk(tmp_path, {})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", ["same_day_unverified"]), (MISSED, "suggestive", "not_exposed", [])])
    e = pi.get_case_entry("case_a", at(2))
    assert e["relationship_keys"] == [SLEEP, MISSED] and e["relationships"][0] == {"relationship_key": SLEEP, "exposed": True, "label": "supported", "flags": ["same_day_unverified"]}
    assert e["relationships"][1]["exposed"] is False and e["mode"] == "relationship" and e["sentences"] == ["One sentence."]
    assert "not_usable@1d->x" not in json.dumps(e)


def test_a_sealed_week_never_changes(tmp_path):
    pi, _ = mk(tmp_path, {})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    run_week(pi, 0)
    with pytest.raises(SealedWeekError):
        rec(pi, "case_b", 1, 3, [(SLEEP, S, "exposed", [])])
    sealed = pi.get_sealed_weeks(1, at(8))[0]
    assert sealed["status"] == "sealed" and sealed["sealed_at"] == "2026-03-08T23:59:59+05:30" and [e["case_id"] for e in sealed["entries"]] == ["case_a"]
    assert pi.get_open_week(at(3))["status"] == "open"                                           # as of day three the week was still open
    assert pi.get_open_week("2026-03-08T23:59:59+05:30")["status"] == "sealed"


# ---- the weekly job ----------------------------------------------------------------------------------------------------------------------------------------------------
def long(pi, key, as_of="2030-01-01T00:00:00+05:30"):
    return pi.get_long_term(key, as_of)


def test_a_relationship_that_was_supported_for_weeks_is_created_as_supported_with_back_filled_labels(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 8)})
    for n in (0, 1):
        run_week(pi, n)                                                                           # nothing used yet: no memory
    assert long(pi, SLEEP) is None
    rec(pi, "case_a", 1, 17, [(SLEEP, S, "exposed", [])])                                          # week three (Wed 18 Mar)
    r = run_week(pi, 2)
    m = long(pi, SLEEP)
    assert r["memories_created"] == [SLEEP] and m["version"] == 1 and m["status"] == "supported" and m["status_since"] == "2026-03-15"
    assert [(x["week"], x["label"], x["days_supported"], x["days_in_week"]) for x in m["weekly_labels"]] == [("2026-W10", S, 7, 7), ("2026-W11", S, 7, 7), ("2026-W12", S, 7, 7)]
    assert m["status_history"] == [{"week": "2026-W11", "from": "candidate", "to": "supported"}] and m["story_coupling"] == "unknown" and m["tier"] == "long_term"
    assert m["evidence_refs"] == [f"rel|{SLEEP}|2026-03-08|ev-v0", f"rel|{SLEEP}|2026-03-15|ev-v0", f"rel|{SLEEP}|2026-03-22|ev-v0"]
    assert m["text"] == {"sentences": ["Short sleep the night before has repeatedly moved together with higher glucose peaks after dinner in her history."], "source": "code_text"} and m["text_version"] == 1
    assert m["finding_ids"] == ["fnd_case_a_v1"] and m["same_day_only"] is False and m["written_at"] == "2026-03-22T23:59:59+05:30"


def test_evidence_refs_cover_decisive_weeks_only(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S, SUG, NS, "insufficient", S])})
    rec(pi, "case_a", 1, 29, [(SLEEP, S, "exposed", [])])
    for n in range(0, 5):
        run_week(pi, n)
    m = long(pi, SLEEP)
    assert [x["label"] for x in m["weekly_labels"]] == [S, SUG, NS, "insufficient", S]
    assert m["evidence_refs"] == [f"rel|{SLEEP}|2026-03-08|ev-v0", f"rel|{SLEEP}|2026-03-22|ev-v0", f"rel|{SLEEP}|2026-04-05|ev-v0"]


def test_a_same_day_only_relationship_says_same_day_and_a_candidate_stays_candidate(tmp_path):
    pi, _ = mk(tmp_path, {"sleep_hours@prev_night->hr_day_mean": weekly([S, NS, S]), STRESS: weekly([SUG])})
    rec(pi, "case_a", 1, 1, [("sleep_hours@prev_night->hr_day_mean", S, "exposed", ["same_day_unverified"]), (STRESS, "suggestive", "not_exposed", [])])
    run_week(pi, 0)
    a, b = long(pi, "sleep_hours@prev_night->hr_day_mean"), long(pi, STRESS)
    assert a["same_day_only"] is True and a["status"] == "candidate" and a["flags_seen"] == ["same_day_unverified"]
    assert a["text"]["sentences"][0].endswith("in her history, on the same day. This is an early observation.")
    assert b["status"] == "candidate" and b["evidence_refs"] == [] and [x["label"] for x in b["weekly_labels"]] == [SUG] and b["counters"]["exposed_case_days"] == 0


def test_counters_count_dates_once_however_many_cases_and_versions(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 8)})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    rec(pi, "case_a", 2, 1, [(SLEEP, S, "exposed", [])], hh=15)
    rec(pi, "case_b", 1, 1, [(SLEEP, S, "not_exposed", [])], hh=20)
    rec(pi, "case_c", 1, 3, [(SLEEP, S, "not_exposed", [])])
    run_week(pi, 0)
    c = long(pi, SLEEP)["counters"]
    assert c == {"case_days": 2, "exposed_case_days": 1, "first_seen": "2026-03-03", "last_seen": "2026-03-05", "weeks_seen": 1}


def test_a_case_across_midnight_on_sunday_keeps_its_date_and_is_counted_by_the_job_that_sees_the_entry(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 8)})
    rec(pi, "case_x", 1, 6, [(SLEEP, S, "not_exposed", [])], hh=23, mm=0)
    run_week(pi, 0)
    assert long(pi, SLEEP)["counters"] == {"case_days": 1, "exposed_case_days": 0, "first_seen": "2026-03-08", "last_seen": "2026-03-08", "weeks_seen": 1}
    rec(pi, "case_x", 2, 7, [(SLEEP, S, "exposed", [])], hh=0, mm=30, local="2026-03-08")
    run_week(pi, 1)
    m = long(pi, SLEEP)
    assert m["counters"] == {"case_days": 1, "exposed_case_days": 1, "first_seen": "2026-03-08", "last_seen": "2026-03-08", "weeks_seen": 2} and m["version"] == 2


def test_a_week_whose_only_effect_is_one_more_label_writes_no_new_version(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S, SUG, SUG, SUG])})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    run_week(pi, 0)
    r = run_week(pi, 1)
    assert long(pi, SLEEP)["version"] == 1 and r["memories_created"] == [] and r["statuses_changed"] == [] and r["counts"]["memories_written"] == 0
    assert long(pi, SLEEP)["weekly_labels"][-1]["week"] == "2026-W10"                            # the stored version stops at its own week


def test_a_status_change_writes_a_new_version_and_is_reported_in_the_run_record(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S, S, NS, NS, NS])})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    rs = [run_week(pi, n) for n in range(0, 4)]
    assert [r["statuses_changed"] for r in rs] == [[], [{"relationship_key": SLEEP, "from": "candidate", "to": "supported"}], [], [{"relationship_key": SLEEP, "from": "supported", "to": "weakened"}]]
    m = long(pi, SLEEP)
    assert m["version"] == 3 and m["status"] == "weakened" and m["status_since"] == "2026-03-29" and m["text"]["sentences"][0].endswith("are no longer clearly seen together in her history.")
    assert m["text_version"] == 3 and [h["to"] for h in m["status_history"]] == ["supported", "weakened"]


def test_the_weekly_job_is_idempotent_and_records_a_run(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 8)})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    a = run_week(pi, 0)
    n = pi.store.conn.execute("SELECT (SELECT COUNT(*) FROM pi_long_memories), (SELECT COUNT(*) FROM pi_weekly_runs), (SELECT COUNT(*) FROM pi_mid_memories)").fetchone()
    b = run_week(pi, 0)
    assert a == b and pi.store.conn.execute("SELECT (SELECT COUNT(*) FROM pi_long_memories), (SELECT COUNT(*) FROM pi_weekly_runs), (SELECT COUNT(*) FROM pi_mid_memories)").fetchone() == n
    assert a["week"] == "2026-W10" and a["written_at"] == "2026-03-08T23:59:59+05:30" and a["usage_json"] == {} and a["texts_kept"] == 0 and a["texts_updated"] == 1
    assert a["counts"]["entries"] == 1 and a["counts"]["case_days"] == 1 and a["mid_memory"] == "pi_mid_2026-W10"


def test_an_empty_week_is_still_sealed(tmp_path):
    pi, _ = mk(tmp_path, {})
    run_week(pi, 3)
    s = pi.get_sealed_weeks(1, at(40))[0]
    assert s["week"]["iso"] == "2026-W13" and s["entries"] == [] and s["case_days"] == []


def test_the_final_partial_week_counts_only_the_days_that_exist(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 9)})
    rec(pi, "case_a", 1, 8 * 7 + 1, [(SLEEP, S, "exposed", [])])
    for n in range(0, 8):
        run_week(pi, n)
    w = wk(8)                                                                                      # Mon 27 Apr to Sun 3 May; the data end on Wed 29 Apr
    r = pi.weekly_job(w, datetime(2026, 4, 29, 23, 59, 59, tzinfo=IST))
    m = long(pi, SLEEP)
    last = m["weekly_labels"][-1]
    assert (last["week"], last["days_in_week"], last["label"]) == ("2026-W18", 3, "insufficient") and m["written_at"] == "2026-04-29T23:59:59+05:30"
    assert r["written_at"] == "2026-04-29T23:59:59+05:30" and pi.get_sealed_weeks(1, "2026-04-29T23:59:59+05:30")[0]["sealed_at"] == "2026-04-29T23:59:59+05:30"


def test_event_level_and_unusable_factors_make_no_memory_and_an_untested_key_makes_an_empty_one(tmp_path):
    pi, _ = mk(tmp_path, {})
    rec(pi, "case_a", 1, 1, [("steps_total@1d->day_min_glucose", S, "exposed", [])])
    run_week(pi, 0)
    assert [m["relationship_key"] for m in pi.list_long_term(None, "2030-01-01T00:00:00+05:30")] == ["steps_total@1d->day_min_glucose"]
    m = long(pi, "steps_total@1d->day_min_glucose")
    assert m["weekly_labels"] == [] and m["status"] == "candidate" and m["evidence_refs"] == []


def test_regeneration_falls_due_every_four_weeks_from_the_creation_week(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S, SUG, SUG, SUG, SUG, SUG, SUG, SUG])})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    due = [run_week(pi, n)["counts"]["regeneration_due"] for n in range(0, 6)]
    assert due == [[], [], [], [], [SLEEP], []]
    assert long(pi, SLEEP)["text_version"] == 1                                                    # the code text did not change, so nothing was rewritten


# ---- retrieval ---------------------------------------------------------------------------------------------------------------------------------------------------------
def test_long_term_reads_are_as_of(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 8), MISSED: weekly([S] * 8)})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    rec(pi, "case_b", 1, 9, [(MISSED, S, "exposed", [])])
    run_week(pi, 0)
    run_week(pi, 1)
    assert pi.get_long_term(SLEEP, "2026-03-08T23:59:58+05:30") is None and pi.get_long_term(SLEEP, "2026-03-08T23:59:59+05:30")["version"] == 1
    assert pi.get_long_term(MISSED, "2026-03-08T23:59:59+05:30") is None and pi.get_long_term(MISSED, "2026-03-15T23:59:59+05:30")["written_at"] == "2026-03-15T23:59:59+05:30"
    many = pi.get_long_term_many([SLEEP, MISSED, "nothing@1d->x"], "2026-03-15T23:59:59+05:30")
    assert set(many) == {SLEEP, MISSED} and many[SLEEP]["version"] == 2                           # created a week earlier, promoted at the end of the second week
    assert sorted(m["relationship_key"] for m in pi.list_long_term("supported", "2026-03-15T23:59:59+05:30")) == sorted([MISSED, SLEEP])
    assert pi.list_long_term("weakened", "2026-03-15T23:59:59+05:30") == []
    assert [m["relationship_key"] for m in pi.list_long_term(None, "2026-03-08T23:59:59+05:30")] == [SLEEP]


def test_sealed_weeks_and_case_entries_are_as_of(tmp_path):
    pi, _ = mk(tmp_path, {})
    rec(pi, "case_a", 1, 1, [])
    rec(pi, "case_b", 1, 9, [])
    for n in (0, 1):
        run_week(pi, n)
    assert [w["week"]["iso"] for w in pi.get_sealed_weeks(5, "2026-03-15T23:59:59+05:30")] == ["2026-W11", "2026-W10"]
    assert [w["week"]["iso"] for w in pi.get_sealed_weeks(1, "2026-03-15T23:59:59+05:30")] == ["2026-W11"]
    assert [w["week"]["iso"] for w in pi.get_sealed_weeks(5, "2026-03-10T00:00:00+05:30")] == ["2026-W10"]
    assert pi.get_case_entry("case_b", at(9, 11)) is None and pi.get_case_entry("case_b", at(9, 13))["case_id"] == "case_b" and pi.get_case_entry("nobody", at(30)) is None


def test_seen_before_bands_include_the_open_week_and_exclude_the_current_case(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 8)})
    asof = lambda off: at(off, 20)
    assert pi.get_seen_before(SLEEP, asof(3)) == "none"
    rec(pi, "case_a", 1, 3, [(SLEEP, S, "exposed", [])])                                             # 5 Mar, the open week
    assert pi.get_seen_before(SLEEP, asof(4)) == "this_week" and pi.get_seen_before(SLEEP, asof(3), exclude_case="case_a") == "none"
    assert pi.get_seen_before(SLEEP, at(3, 11)) == "none"                                            # written at noon: not yet there at 11:00
    run_week(pi, 0)
    assert pi.get_seen_before(SLEEP, asof(10)) == "this_week"                                        # 5 Mar seen from 12 Mar: seven days
    assert pi.get_seen_before(SLEEP, asof(11)) == "recent_weeks"
    assert pi.get_seen_before(SLEEP, asof(30)) == "recent_weeks"                                     # 27 days
    assert pi.get_seen_before(SLEEP, asof(33)) == "earlier"
    assert pi.get_seen_before(SLEEP, asof(10), exclude_case="case_a") == "none"                      # the long-term date was made by that case alone
    rec(pi, "case_b", 1, 10, [(SLEEP, S, "not_exposed", [])])
    assert pi.get_seen_before(SLEEP, asof(10), exclude_case="case_a") == "this_week"
    assert pi.get_seen_before("other@1d->x", asof(10)) == "none"


def test_no_read_returns_anything_written_after_its_as_of(tmp_path):
    pi, _ = mk(tmp_path, {SLEEP: weekly([S] * 8)})
    rec(pi, "case_a", 1, 1, [(SLEEP, S, "exposed", [])])
    run_week(pi, 0)
    early = "2026-03-01T00:00:00+05:30"
    assert pi.get_long_term(SLEEP, early) is None and pi.get_open_week(early)["entries"] == [] and pi.get_sealed_weeks(5, early) == [] and pi.get_case_entry("case_a", early) is None
    assert pi.list_long_term(None, early) == [] and pi.get_seen_before(SLEEP, early) == "none"
