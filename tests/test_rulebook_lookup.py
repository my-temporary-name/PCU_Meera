"""Rulebook Lookup (spec: task/rulebook_lookup_spec.md, Amendments on top). Tests use a synthetic second patient with its own measures, streams and medicines
(no name of the first patient anywhere), and then the real rulebook on the real hand-offs for the section 9.3 numbers."""

import copy
import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path

import pytest

from v0_code.rulebook_lookup.config import RulebookConfig
from v0_code.rulebook_lookup.grammar import GrammarError, parse_applies, parse_context_match, parse_requires
from v0_code.rulebook_lookup.lookup import build_packet
from v0_code.rulebook_lookup.rulebook import RulebookError, load_rulebook
from v0_code.rulebook_lookup.storage import PacketStore
from v0_code.rulebook_lookup.windows import resolve_lookback

ROOT = Path(__file__).resolve().parent.parent

RULE_COLS = ["rule_id", "measure", "direction", "context_match", "context_condition", "meera_handoffs_in_year", "status", "primary_count", "secondary_max",
             "tertiary_max", "max_total", "budget_reason", "basis", "review_status", "rulebook_version"]
CAND_COLS = ["rule_id", "rank", "weight_tier", "candidate", "requires_streams", "lookback_kind", "lookback_value", "applies_if_rule", "check_type",
             "data_status_meera_code", "data_kinds_text", "lookback_text", "applies_if_text", "check_text", "outcome_compared_text", "evidence_level", "sources",
             "meera_data_status_text", "note", "review_status"]


def rule(rule_id, measure, direction, ctx="", status="active", pri=1, sec=1, ter=0, total=None, version="t-1"):
    return {"rule_id": rule_id, "measure": measure, "direction": direction, "context_match": ctx, "context_condition": "", "meera_handoffs_in_year": "0",
            "status": status, "primary_count": str(pri), "secondary_max": str(sec), "tertiary_max": str(ter), "max_total": str(pri + sec + ter if total is None else total),
            "budget_reason": "", "basis": "", "review_status": "unreviewed", "rulebook_version": version}


def cand(rule_id, rank, tier, name, req, kind="same_calendar_day", value="", applies="", ev="A", src="S1", note="", check="group_comparison"):
    return {"rule_id": rule_id, "rank": str(rank), "weight_tier": tier, "candidate": name, "requires_streams": req, "lookback_kind": kind, "lookback_value": str(value),
            "applies_if_rule": applies, "check_type": check, "data_status_meera_code": "available", "data_kinds_text": "", "lookback_text": f"{kind} {value}".strip(),
            "applies_if_text": "", "check_text": f"check {name}", "outcome_compared_text": f"outcome {name}", "evidence_level": ev, "sources": src,
            "meera_data_status_text": "", "note": note, "review_status": "unreviewed"}


def good_rules():
    return [
        rule("sys_fed", "systolic", "above", "last_meal_minutes_ago<=90", pri=1, sec=1, ter=1),
        rule("sys_fasted", "systolic", "above", "last_meal_minutes_ago>90 or last_meal absent", pri=1, sec=1, ter=0),
        rule("lux_deferred", "lux", "above", "", status="deferred", pri=0, sec=2, ter=0),
        rule("pulse_open", "pulse", "below", "", pri=1, sec=0, ter=0),
    ]


def good_cands():
    return [
        cand("sys_fed", 1, "primary", "alpha", "pulse_log", "minutes_before_open", 120),
        cand("sys_fed", 2, "secondary", "beta", "diary_x[mood]", "days_ending_at_open", 2, applies="patient_flag:takes_ace", note="a note"),
        cand("sys_fed", 3, "secondary", "gamma", "ghost_stream", ev="B"),
        cand("sys_fed", 4, "secondary", "delta", "pulse_daily|pulse_log", "previous_evening", ev="B", src="S2;S1"),
        cand("sys_fed", 5, "tertiary", "epsilon", "pulse_log;ghost_stream", "at_open", applies="medication_class_present:ace_inhibitor|medication_class_present:zzz", ev="B"),
        cand("sys_fed", 6, "tertiary", "zeta", "pulse_log", "minutes_around_open", 30, ev="C", src=""),
        cand("sys_fasted", 1, "primary", "alpha", "pulse_log", "previous_night"),
        cand("sys_fasted", 2, "secondary", "dawn", "time_of_day", "same_calendar_day", applies="open_time_between:22:00-04:00"),
        cand("lux_deferred", 1, "secondary", "x1", "pulse_log", ev="D", src=""),
        cand("lux_deferred", 2, "secondary", "x2", "pulse_log", ev="D", src=""),
        cand("pulse_open", 1, "primary", "only", "pulse_log", "previous_calendar_day"),
    ]


def write_csv(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def write_rulebook(d, rules=None, cands=None, sources=("S1", "S2")):
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    write_csv(d / "rules.csv", RULE_COLS, rules if rules is not None else good_rules())
    write_csv(d / "candidates.csv", CAND_COLS, cands if cands is not None else good_cands())
    (d / "book.md").write_text("## Sources\n\n| ID | Source | Type |\n|---|---|---|\n" + "\n".join(f"| {s} | [x](http://x) | ref |" for s in sources) + "\n")
    return d


RAW_CFG = {
    "rulebook_dir": "unused", "rules_file": "rules.csv", "candidates_file": "candidates.csv", "sources_file": "book.md", "raised_bar_above": 2,
    "stream_map": {"pulse_log": "pulse_series", "pulse_daily": None, "diary_x": "diary_table", "time_of_day": "derived", "med_list": "derived:medication_classes"},
    "medication_classes": {"ramipril": ["ace_inhibitor"]},
    "patient_flags": {"has_thing": True},
    "derived_flags": {"takes_ace": "ace_inhibitor"},
}


def cfg_for(tz="UTC", raw=None, regex="^m\\d+_"):
    return RulebookConfig.from_dict(copy.deepcopy(raw or RAW_CFG), timezone=tz, medication_id_regex=regex)


def handoff(measure="systolic", direction="above", opened="2030-05-10T22:30:00+00:00", meal=60, value=151.0, status="high", **kw):
    h = {"handoff_id": f"handoff_{measure}_{opened[:16]}", "item_id": f"{measure}_{opened[:16]}", "written_at": opened, "measure": measure, "direction": direction,
         "size": "clearly", "trigger": "persistence", "value": value, "clinical_status": status, "usual_basis": "clock_time", "position_z": 2.1, "opened_at": opened,
         "context": {"last_meal": None if meal is None else {"label": "x", "time": opened, "minutes_ago": meal}, "medication": None, "sleep_last_night": None,
                     "other_open_items": [], "diary_today_count": 0}, "snapshot_as_of": opened}
    h.update(kw)
    return h


@pytest.fixture()
def book(tmp_path):
    return load_rulebook(write_rulebook(tmp_path / "rb"), cfg_for())


# ---------------------------------------------------------------- grammar -------------------------------------------------------------------------
@pytest.mark.parametrize("text,minutes,expected", [
    ("last_meal_minutes_ago<=180", 180, True), ("last_meal_minutes_ago<=180", 181, False), ("last_meal_minutes_ago<=180", None, False),
    ("last_meal_minutes_ago>180 or last_meal absent", 181, True), ("last_meal_minutes_ago>180 or last_meal absent", 180, False),
    ("last_meal_minutes_ago>180 or last_meal absent", None, True), ("", 5, True), ("", None, True),
    ("last_meal_minutes_ago>=10 and last_meal_minutes_ago<20", 10, True), ("last_meal_minutes_ago>=10 and last_meal_minutes_ago<20", 20, False),
    ("last_meal absent or last_meal_minutes_ago<5 and last_meal_minutes_ago>1", None, True), ("last_meal absent or last_meal_minutes_ago<5 and last_meal_minutes_ago>1", 7, False),
])
def test_context_match(text, minutes, expected):
    assert parse_context_match(text).matches(minutes) is expected


@pytest.mark.parametrize("bad", ["last_meal_minutes_ago<=", "meal_gap<5", "last_meal_minutes_ago ~ 4", "or", "last_meal_minutes_ago<=x"])
def test_context_match_unparseable(bad):
    with pytest.raises(GrammarError):
        parse_context_match(bad)


def test_requires_groups_alternatives_and_category():
    g = parse_requires("a;b[sym]|c;d")
    assert [[(t.name, t.category) for t in grp] for grp in g] == [[("a", None)], [("b", "sym"), ("c", None)], [("d", None)]]
    assert g[1][0].generic == "b[sym]"


@pytest.mark.parametrize("bad", ["", "a;;b", "a|", "a[b"])
def test_requires_unparseable(bad):
    with pytest.raises(GrammarError):
        parse_requires(bad)


def test_applies_terms_and_errors():
    t = parse_applies("patient_flag:x|medication_class_present:y;open_time_between:04:00-09:00")
    assert len(t) == 2 and [a.kind for a in t[0].atoms] == ["patient_flag", "medication_class_present"] and t[0].text == "patient_flag:x|medication_class_present:y"
    assert parse_applies("") == ()
    for bad in ["nonsense:x", "patient_flag:", "open_time_between:4-9", "open_time_between:25:00-26:00", "stream_present"]:
        with pytest.raises(GrammarError):
            parse_applies(bad)


@pytest.mark.parametrize("opened,expected", [
    ("2030-05-10T03:59:00+00:00", False), ("2030-05-10T04:00:00+00:00", True), ("2030-05-10T08:59:00+00:00", True), ("2030-05-10T09:00:00+00:00", False)])
def test_open_time_between_start_inclusive_end_exclusive(opened, expected):
    cfg = cfg_for()
    ok, _ = cfg.evaluate_applies(parse_applies("open_time_between:04:00-09:00"), opened)
    assert ok is expected


def test_open_time_between_crosses_midnight_and_uses_patient_zone():
    cfg = cfg_for()
    t = parse_applies("open_time_between:22:00-04:00")
    assert cfg.evaluate_applies(t, "2030-05-10T23:30:00+00:00")[0] and cfg.evaluate_applies(t, "2030-05-10T03:00:00+00:00")[0]
    assert not cfg.evaluate_applies(t, "2030-05-10T12:00:00+00:00")[0]
    kolkata = cfg_for(tz="Asia/Kolkata")                                   # 23:00 UTC is 04:30 local
    assert not kolkata.evaluate_applies(parse_applies("open_time_between:22:00-04:00"), "2030-05-10T23:00:00+00:00")[0]
    assert kolkata.evaluate_applies(parse_applies("open_time_between:04:00-09:00"), "2030-05-10T23:00:00+00:00")[0]


def test_flags_classes_streams_unknown_is_false_not_error():
    cfg = cfg_for()
    ev = lambda s: cfg.evaluate_applies(parse_applies(s), "2030-05-10T10:00:00+00:00")
    assert ev("patient_flag:has_thing")[0] and ev("patient_flag:takes_ace")[0]
    assert not ev("patient_flag:nope")[0] and ev("patient_flag:nope")[1] == "patient_flag:nope"
    assert ev("medication_class_present:ace_inhibitor")[0] and not ev("medication_class_present:statin")[0]
    assert ev("stream_present:pulse_log")[0] and not ev("stream_present:pulse_daily")[0] and not ev("stream_present:unmapped")[0]
    ok, detail = ev("patient_flag:nope|medication_class_present:statin")                 # an OR group fails as a whole, named as written
    assert not ok and detail == "patient_flag:nope|medication_class_present:statin"
    assert ev("patient_flag:has_thing;patient_flag:nope")[1] == "patient_flag:nope"       # AND: the failing term


def test_explicit_flag_wins_over_derived():
    raw = copy.deepcopy(RAW_CFG)
    raw["patient_flags"] = {"takes_ace": False}
    assert not cfg_for(raw=raw).flag("takes_ace")


def test_medicine_ids_are_normalised_by_the_baseline_pattern():
    raw = copy.deepcopy(RAW_CFG)
    raw["medication_classes"] = {"m002_ramipril": ["ace_inhibitor"], "other": []}
    cfg = cfg_for(raw=raw)
    assert cfg.medicines == ("ramipril", "other") and cfg.class_present("ace_inhibitor")
    assert cfg.classes_of("m009_ramipril") == ("ace_inhibitor",) and cfg.classes_of("ramipril") == ("ace_inhibitor",)


def test_medication_list_stream_needs_nonempty_classes():
    assert cfg_for().stream_available("med_list")
    raw = copy.deepcopy(RAW_CFG)
    raw["medication_classes"] = {}
    assert not cfg_for(raw=raw).stream_available("med_list")
    assert cfg_for().stream_available("time_of_day") and not cfg_for().stream_available("pulse_daily") and not cfg_for().stream_available("unknown")


# ---------------------------------------------------------------- windows (section 3) ------------------------------------------------------------
def win(kind, value, opened, tz="UTC"):
    return resolve_lookback(kind, value, opened, tz)


def test_windows_minutes_before_and_days_ending():
    o = "2030-05-10T22:30:00+00:00"
    assert win("minutes_before_open", 240, o) == {"start": "2030-05-10T18:30:00+00:00", "end": o, "includes_after_open": False}
    assert win("days_ending_at_open", 1, o)["start"] == "2030-05-10T00:00:00+00:00"
    assert win("days_ending_at_open", 2, o)["start"] == "2030-05-09T00:00:00+00:00"
    assert win("days_ending_at_open", 3, o)["start"] == "2030-05-08T00:00:00+00:00"
    assert win("same_calendar_day", None, o) == {"start": "2030-05-10T00:00:00+00:00", "end": o, "includes_after_open": False}
    assert win("previous_calendar_day", None, o) == {"start": "2030-05-09T00:00:00+00:00", "end": "2030-05-10T00:00:00+00:00", "includes_after_open": False}


def test_windows_use_the_patient_zone_not_utc():
    o = "2030-05-10T22:30:00+05:30"
    w = win("same_calendar_day", None, o, "Asia/Kolkata")
    assert w["start"] == "2030-05-10T00:00:00+05:30" and w["end"] == o
    w2 = win("same_calendar_day", None, "2030-05-10T20:00:00+00:00", "Asia/Kolkata")          # 01:30 local on the 11th
    assert w2["start"] == "2030-05-11T00:00:00+05:30"


def test_windows_fallback_to_the_offset_in_opened_at():
    w = resolve_lookback("same_calendar_day", None, "2030-05-10T22:30:00+05:30", None)
    assert w["start"] == "2030-05-10T00:00:00+05:30"


@pytest.mark.parametrize("opened,start,end", [
    ("2030-05-10T22:30:00+00:00", "2030-05-10T18:00:00+00:00", "2030-05-10T22:30:00+00:00"),        # after 18:00: the current evening, cut at opened_at
    ("2030-05-10T03:00:00+00:00", "2030-05-09T18:00:00+00:00", "2030-05-10T00:00:00+00:00"),        # before 18:00: yesterday's whole evening
    ("2030-05-10T18:00:00+00:00", "2030-05-09T18:00:00+00:00", "2030-05-10T00:00:00+00:00"),        # exactly 18:00: that window has not started before opened_at
    ("2030-05-10T18:01:00+00:00", "2030-05-10T18:00:00+00:00", "2030-05-10T18:01:00+00:00"),
    ("2030-05-10T07:00:00+00:00", "2030-05-09T18:00:00+00:00", "2030-05-10T00:00:00+00:00"),
])
def test_previous_evening(opened, start, end):
    assert win("previous_evening", None, opened) == {"start": start, "end": end, "includes_after_open": False}


def test_previous_night_at_open_and_around_open():
    o = "2030-05-10T22:30:00+00:00"
    assert win("previous_night", None, o) == {"record": "latest_sleep_record_at_or_before_open", "includes_after_open": False}
    assert win("at_open", None, o) == {"at": o, "includes_after_open": False}
    assert win("minutes_around_open", 60, o) == {"start": "2030-05-10T21:30:00+00:00", "end": "2030-05-10T23:30:00+00:00", "includes_after_open": True,
                                                  "earliest_evaluation_time": "2030-05-10T23:30:00+00:00"}


def test_no_window_ends_after_open_except_around_open():
    o = "2030-05-10T14:07:00+00:00"
    for kind, v in [("minutes_before_open", 90), ("days_ending_at_open", 4), ("same_calendar_day", None), ("previous_calendar_day", None), ("previous_evening", None)]:
        assert win(kind, v, o)["end"] <= o and win(kind, v, o)["includes_after_open"] is False


def test_unknown_lookback_kind_raises():
    with pytest.raises(GrammarError):
        win("sometime", None, "2030-05-10T14:07:00+00:00")


# ---------------------------------------------------------------- loading and validation (property 14) ----------------------------------------------
def test_synthetic_rulebook_loads(book):
    assert book.version == "t-1" and [r.rule_id for r in book.rules] == ["sys_fed", "sys_fasted", "lux_deferred", "pulse_open"]
    assert [c.candidate for c in book.candidates["sys_fed"]] == ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]


def mutate(rules=None, cands=None, sources=("S1", "S2")):
    return rules if rules is not None else good_rules(), cands if cands is not None else good_cands(), sources


def broken(tmp_path, fn):
    rules, cands = good_rules(), good_cands()
    r = fn(rules, cands)
    sources = ("S1", "S2")
    if isinstance(r, tuple):
        rules, cands = r[0], r[1]
        sources = r[2] if len(r) > 2 else sources
    d = write_rulebook(tmp_path / "bad", rules, cands, sources)
    with pytest.raises(RulebookError) as e:
        load_rulebook(d, cfg_for())
    return str(e.value)


def test_fail_ranks_not_contiguous(tmp_path):
    def f(rules, cands):
        cands[1]["rank"] = "9"
    assert "sys_fed" in broken(tmp_path, f) and "rank" in broken(tmp_path, f)


def test_fail_tier_order(tmp_path):
    def f(rules, cands):
        cands[0]["weight_tier"], cands[1]["weight_tier"] = "secondary", "primary"
    assert "tier" in broken(tmp_path, f)


def test_fail_secondary_not_ordered_by_evidence(tmp_path):
    def f(rules, cands):
        cands[1]["evidence_level"], cands[2]["evidence_level"] = "C", "A"
    msg = broken(tmp_path, f)
    assert "evidence" in msg and "secondary" in msg


def test_fail_tertiary_not_ordered_by_evidence(tmp_path):
    def f(rules, cands):
        cands[4]["evidence_level"], cands[5]["evidence_level"] = "D", "A"
    assert "tertiary" in broken(tmp_path, f)


def test_fail_primary_count(tmp_path):
    def f(rules, cands):
        rules[0]["primary_count"] = "2"
    assert "primary_count" in broken(tmp_path, f)


def test_fail_unknown_source(tmp_path):
    def f(rules, cands):
        cands[0]["sources"] = "S1;S99"
    msg = broken(tmp_path, f)
    assert "S99" in msg and "source" in msg


def test_fail_grammar_terms(tmp_path):
    def f(rules, cands):
        cands[0]["applies_if_rule"] = "bogus:thing"
    assert "bogus" in broken(tmp_path, f)

    def g(rules, cands):
        cands[0]["requires_streams"] = "a;;b"
    assert "requires_streams" in broken(tmp_path, g)

    def h(rules, cands):
        rules[0]["context_match"] = "last_meal_minutes_ago<="
    assert "context_match" in broken(tmp_path, h)

    def k(rules, cands):
        cands[0]["lookback_kind"] = "whenever"
    assert "lookback_kind" in broken(tmp_path, k)

    def m(rules, cands):
        cands[0]["lookback_value"] = ""
    assert "lookback_value" in broken(tmp_path, m)


def test_fail_rule_without_candidates_unless_deferred(tmp_path):
    def f(rules, cands):
        return rules, [c for c in cands if c["rule_id"] != "pulse_open"]
    assert "pulse_open" in broken(tmp_path, f)
    rules, cands = good_rules(), [c for c in good_cands() if c["rule_id"] != "lux_deferred"]
    d = write_rulebook(tmp_path / "ok", rules, cands)
    load_rulebook(d, cfg_for())                                    # a deferred rule may have none


def test_fail_repeated_rule_id(tmp_path):
    def f(rules, cands):
        rules.append(dict(rules[3]))
    assert "repeated" in broken(tmp_path, f)


def test_fail_two_rules_can_match_the_same_handoff(tmp_path):
    def f(rules, cands):
        rules[1]["context_match"] = "last_meal_minutes_ago>=90 or last_meal absent"        # 90 matches both
    assert "same hand-off" in broken(tmp_path, f)

    def g(rules, cands):
        rules.append(rule("pulse_dup", "pulse", "below"))
        cands.append(cand("pulse_dup", 1, "primary", "a", "pulse_log"))
    assert "same hand-off" in broken(tmp_path, g)


def test_fail_rules_file_versions_disagree(tmp_path):
    def f(rules, cands):
        rules[2]["rulebook_version"] = "t-2"
    assert "rulebook_version" in broken(tmp_path, f)


def test_fail_max_total_below_primary_count(tmp_path):
    def f(rules, cands):
        rules[0]["max_total"] = "0"
    assert "max_total" in broken(tmp_path, f)


def test_fail_candidate_for_unknown_rule_and_bad_enums(tmp_path):
    def f(rules, cands):
        cands.append(cand("ghost_rule", 1, "primary", "a", "pulse_log"))
    assert "ghost_rule" in broken(tmp_path, f)

    def g(rules, cands):
        cands[0]["check_type"] = "vibes"
    assert "check_type" in broken(tmp_path, g)

    def h(rules, cands):
        rules[0]["status"] = "maybe"
    assert "status" in broken(tmp_path, h)


def test_all_errors_are_reported_together(tmp_path):
    def f(rules, cands):
        rules[0]["primary_count"] = "2"
        cands[0]["sources"] = "S77"
    msg = broken(tmp_path, f)
    assert "primary_count" in msg and "S77" in msg


# ---------------------------------------------------------------- one packet --------------------------------------------------------------------
def packet(book, h=None, cfg=None):
    return build_packet(h or handoff(), book, cfg or cfg_for())


def test_packet_post_meal_example(book):
    p = packet(book)
    assert p["packet_id"] == "packet_" + p["handoff_id"] and "status" not in p
    assert p["rulebook_version"] == "t-1" and p["rulebook_review_status"] == "unreviewed"
    assert p["matched_rule"] == {"rule_id": "sys_fed", "status": "active", "context_match": "last_meal_minutes_ago<=90",
                                 "budget": {"primary": "all", "primary_count": 1, "secondary_max": 1, "tertiary_max": 1, "max_total": 3}, "review_status": "unreviewed"}
    assert [c["candidate"] for c in p["selected"]] == ["alpha", "beta", "epsilon"]
    assert [c["rank"] for c in p["selected"]] == [1, 2, 5]
    assert p["skipped"] == [{"candidate": "gamma", "reason": "no_stream", "detail": "ghost_stream"}]
    assert p["not_selected"] == [{"candidate": "delta", "weight_tier": "secondary", "reason": "budget"}, {"candidate": "zeta", "weight_tier": "tertiary", "reason": "budget"}]
    assert p["counts"] == {"candidates_in_rule": 6, "selected": 3, "skipped": 1, "not_selected": 2}
    assert p["evidence_bar_hint"] == "raised"                               # 3 selected > raised_bar_above 2


def test_packet_candidate_object_keys_and_provenance(book):
    p = packet(book)
    beta = p["selected"][1]
    assert set(beta) == {"rank", "weight_tier", "candidate", "check_type", "check_text", "outcome_compared_text", "streams", "lookback", "resolved_window",
                         "evidence_level", "sources", "data_status_code", "review_status", "note"}
    assert beta["note"] == "a note" and p["selected"][0]["note"] is None
    assert beta["streams"] == [{"generic": "diary_x[mood]", "patient_stream": "diary_table", "category": "mood", "available": True, "used": True}]
    assert beta["lookback"] == {"kind": "days_ending_at_open", "value": 2, "text": "days_ending_at_open 2"}
    assert beta["resolved_window"]["start"] == "2030-05-09T00:00:00+00:00" and beta["sources"] == ["S1"] and beta["review_status"] == "unreviewed"
    assert beta["data_status_code"] == "available" and beta["weight_tier"] == "secondary"
    assert p["selected"][0]["lookback"]["value"] == 120


def test_streams_for_a_partly_available_token_list(book):
    eps = packet(book)["selected"][2]
    assert eps["streams"] == [{"generic": "pulse_log", "patient_stream": "pulse_series", "category": None, "available": True, "used": True},
                              {"generic": "ghost_stream", "patient_stream": None, "category": None, "available": False, "used": False}]


def test_fallback_alternatives_have_used_and_fallback_for(tmp_path):
    cands = good_cands()
    cands[3]["requires_streams"] = "pulse_daily|pulse_log|diary_x"
    cands[3]["weight_tier"], cands[3]["rank"] = "secondary", "4"
    rules = good_rules()
    rules[0]["secondary_max"], rules[0]["max_total"] = "2", "4"
    # secondary order beta, gamma(skipped), delta -> both beta and delta are selected now
    b = load_rulebook(write_rulebook(tmp_path / "fb", rules, cands), cfg_for())
    delta = next(c for c in packet(b)["selected"] if c["candidate"] == "delta")
    assert delta["streams"] == [
        {"generic": "pulse_daily", "patient_stream": None, "category": None, "available": False, "used": False},
        {"generic": "pulse_log", "patient_stream": "pulse_series", "category": None, "available": True, "used": True, "fallback_for": "pulse_daily"},
        {"generic": "diary_x", "patient_stream": "diary_table", "category": None, "available": True, "used": False, "fallback_for": "pulse_daily"}]


def test_no_available_alternative_means_no_used(tmp_path):
    cands = good_cands()
    cands[2]["requires_streams"] = "ghost_stream|ghost_two"
    b = load_rulebook(write_rulebook(tmp_path / "x", None, cands), cfg_for())
    p = packet(b)
    assert p["skipped"][0]["detail"] == "ghost_stream; ghost_two"


def test_unavailable_primary_is_skipped_and_uses_no_budget(tmp_path):
    cands = good_cands()
    cands[0]["requires_streams"] = "ghost_stream"                    # the primary has no stream
    b = load_rulebook(write_rulebook(tmp_path / "x", None, cands), cfg_for())
    p = packet(b)
    assert [c["candidate"] for c in p["selected"]] == ["beta", "epsilon"]
    assert {s["candidate"] for s in p["skipped"]} == {"alpha", "gamma"}


def test_skipped_candidates_do_not_use_budget(tmp_path):
    cands = good_cands()
    cands[1]["applies_if_rule"] = "patient_flag:nope"                # beta no longer applies: the one secondary slot goes to delta
    b = load_rulebook(write_rulebook(tmp_path / "x", None, cands), cfg_for())
    p = packet(b)
    assert [c["candidate"] for c in p["selected"]] == ["alpha", "delta", "epsilon"]
    assert {"candidate": "beta", "reason": "applies_if_not_met", "detail": "patient_flag:nope"} in p["skipped"]


def test_two_primaries_cannot_fit_in_max_total(tmp_path):
    rules = good_rules()
    rules[0].update(primary_count="2", secondary_max="0", tertiary_max="0", max_total="1")           # max_total below the primaries: invalid
    cands = good_cands()
    cands[1] = cand("sys_fed", 2, "primary", "beta", "pulse_log")
    d = write_rulebook(tmp_path / "x", rules, cands)
    with pytest.raises(RulebookError):
        load_rulebook(d, cfg_for())


def test_max_total_stops_secondary_and_tertiary_but_never_a_primary(tmp_path):
    rules = good_rules()
    rules[0].update(secondary_max="1", tertiary_max="1", max_total="1")                              # primary 1 + caps 1 + 1, total 1
    b = load_rulebook(write_rulebook(tmp_path / "x", rules, good_cands()), cfg_for())
    p = packet(b)
    assert [c["candidate"] for c in p["selected"]] == ["alpha"]
    assert all(n["reason"] == "budget" for n in p["not_selected"]) and p["counts"]["not_selected"] == 4 and p["counts"]["skipped"] == 1


def test_completeness_every_candidate_exactly_once(book):
    for h in [handoff(meal=60), handoff(meal=500), handoff(meal=None), handoff(measure="pulse", direction="below"), handoff(measure="lux")]:
        p = packet(book, h)
        if p.get("status") == "unmatched":
            continue
        names = [c["candidate"] for c in p["selected"]] + [c["candidate"] for c in p["skipped"]] + [c["candidate"] for c in p["not_selected"]]
        rule_cands = [c.candidate for c in book.candidates[p["matched_rule"]["rule_id"]]]
        assert sorted(names) == sorted(rule_cands) and p["counts"]["candidates_in_rule"] == len(rule_cands)
        assert p["counts"]["selected"] + p["counts"]["skipped"] + p["counts"]["not_selected"] == len(rule_cands)
        ranks = [c["rank"] for c in p["selected"]]
        assert ranks == sorted(ranks)


def test_rule_chosen_by_context(book):
    assert packet(book, handoff(meal=90))["matched_rule"]["rule_id"] == "sys_fed"
    assert packet(book, handoff(meal=91))["matched_rule"]["rule_id"] == "sys_fasted"
    assert packet(book, handoff(meal=None))["matched_rule"]["rule_id"] == "sys_fasted"
    h = handoff(meal=None)
    del h["context"]["last_meal"]                                                    # a missing key is also "absent"
    assert packet(book, h)["matched_rule"]["rule_id"] == "sys_fasted"
    assert packet(book, handoff(meal=91))["handoff_summary"]["last_meal_minutes_ago"] == 91
    assert packet(book, handoff(meal=None))["handoff_summary"]["last_meal_minutes_ago"] is None


def test_unmatched_packet(book):
    p = packet(book, handoff(measure="unknown_thing"))
    assert p["status"] == "unmatched" and p["matched_rule"] is None and p["selected"] == [] and p["skipped"] == [] and p["not_selected"] == []
    assert p["counts"] == {"candidates_in_rule": 0, "selected": 0, "skipped": 0, "not_selected": 0} and p["evidence_bar_hint"] == "standard"
    assert packet(book, handoff(direction="below"))["status"] == "unmatched"          # same measure, other direction


def test_deferred_packet_lists_every_candidate_as_rule_deferred(book):
    p = packet(book, handoff(measure="lux"))
    assert p["status"] == "deferred" and p["matched_rule"]["rule_id"] == "lux_deferred" and p["matched_rule"]["status"] == "deferred"
    assert p["selected"] == [] and p["skipped"] == []
    assert p["not_selected"] == [{"candidate": "x1", "weight_tier": "secondary", "reason": "rule_deferred"}, {"candidate": "x2", "weight_tier": "secondary", "reason": "rule_deferred"}]
    assert p["counts"] == {"candidates_in_rule": 2, "selected": 0, "skipped": 0, "not_selected": 2} and p["evidence_bar_hint"] == "standard"


def test_ambiguous_packet_takes_first_rule_in_file_order(tmp_path):
    rules = good_rules()
    rules[1]["context_match"] = ""                                                    # overlaps with sys_fed
    b = load_rulebook(write_rulebook(tmp_path / "x", rules, good_cands()), cfg_for(), validate=False)
    p = packet(b, handoff(meal=10))
    assert p["status"] == "ambiguous" and p["matched_rule"]["rule_id"] == "sys_fed" and p["selected"]


def test_around_open_candidate_carries_after_open_flag(tmp_path):
    rules = good_rules()
    rules[0].update(secondary_max="2", tertiary_max="2", max_total="5")
    b = load_rulebook(write_rulebook(tmp_path / "x", rules, good_cands()), cfg_for())
    zeta = next(c for c in packet(b)["selected"] if c["candidate"] == "zeta")
    assert zeta["resolved_window"]["includes_after_open"] is True and zeta["resolved_window"]["earliest_evaluation_time"] == "2030-05-10T23:00:00+00:00"
    assert zeta["resolved_window"]["start"] == "2030-05-10T22:00:00+00:00" and zeta["resolved_window"]["end"] == "2030-05-10T23:00:00+00:00"
    for c in packet(b)["selected"]:
        if c["candidate"] != "zeta":
            assert c["resolved_window"]["includes_after_open"] is False


def test_no_look_ahead_in_any_window_but_around_open(tmp_path):
    rules = good_rules()
    rules[0].update(secondary_max="3", tertiary_max="2", max_total="6")
    b = load_rulebook(write_rulebook(tmp_path / "x", rules, good_cands()), cfg_for())
    for opened in ["2030-05-10T22:30:00+00:00", "2030-05-10T03:00:00+00:00", "2030-05-10T18:00:00+00:00"]:
        for c in packet(b, handoff(opened=opened))["selected"]:
            w = c["resolved_window"]
            if "end" in w and c["candidate"] != "zeta":
                assert w["end"] <= opened


def test_handoff_summary_is_copied_exactly(book):
    obj = {"taken": 1, "expected": 3, "missed": ["a", "b"]}
    h = handoff(value=obj, status=None, position_z=None, usual_basis="profile")
    s = packet(book, h)["handoff_summary"]
    assert s == {"measure": "systolic", "direction": "above", "size": "clearly", "trigger": "persistence", "position_z": None, "usual_basis": "profile", "value": obj,
                 "clinical_status": None, "opened_at": h["opened_at"], "last_meal_minutes_ago": 60}
    assert s["value"] is not obj and s["value"] == obj


def test_hint_standard_when_not_above_the_limit(book):
    cfg = cfg_for()
    p = build_packet(handoff(measure="pulse", direction="below"), book, cfg)
    assert p["evidence_bar_hint"] == "standard" and [c["candidate"] for c in p["selected"]] == ["only"]


def test_conditional_time_applicability(book):
    night = packet(book, handoff(meal=500, opened="2030-05-10T23:00:00+00:00"))
    day = packet(book, handoff(meal=500, opened="2030-05-10T12:00:00+00:00"))
    assert "dawn" in [c["candidate"] for c in night["selected"]]
    assert {"candidate": "dawn", "reason": "applies_if_not_met", "detail": "open_time_between:22:00-04:00"} in day["skipped"]


def test_previous_night_window_is_a_record(book):
    a = packet(book, handoff(meal=500))["selected"][0]
    assert a["resolved_window"] == {"record": "latest_sleep_record_at_or_before_open", "includes_after_open": False}


def test_weights_are_never_numbers_and_packet_has_no_data(book):
    for h in [handoff(), handoff(meal=500), handoff(measure="lux")]:
        p = packet(book, h)
        s = json.dumps(p)
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if re.search(r"weight|confidence|score|probab|prior", k):
                        assert not isinstance(v, (int, float)), f"{k} is a number"
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(p)
        for c in p["selected"]:
            assert c["weight_tier"] in ("primary", "secondary", "tertiary") and isinstance(c["evidence_level"], str)
        assert set(p["handoff_summary"]) == {"measure", "direction", "size", "trigger", "position_z", "usual_basis", "value", "clinical_status", "opened_at", "last_meal_minutes_ago"}
        assert "context" not in p and "diary_today_count" not in s


def test_deterministic(book):
    h = handoff()
    assert json.dumps(packet(book, h)) == json.dumps(packet(book, copy.deepcopy(h)))


def test_does_not_modify_the_handoff(book):
    h = handoff()
    before = copy.deepcopy(h)
    packet(book, h)
    assert h == before


# ---------------------------------------------------------------- the packet log ------------------------------------------------------------------
def test_store_replaces_by_packet_id_and_has_no_timestamp(book, tmp_path):
    db = tmp_path / "log.db"
    s = PacketStore(db)
    p = packet(book)
    s.write(p)
    s.write(p)
    assert len(s.packets()) == 1
    cols = [r[1] for r in s.conn.execute("PRAGMA table_info(rulebook_packets)")]
    assert cols == ["packet_id", "handoff_id", "rule_id", "status", "rulebook_version", "n_selected", "n_skipped", "n_not_selected", "packet_json"]
    row = s.conn.execute("SELECT * FROM rulebook_packets").fetchone()
    assert row["rule_id"] == "sys_fed" and row["status"] == "ok" and row["n_selected"] == 3 and row["n_skipped"] == 1 and row["n_not_selected"] == 2
    assert json.loads(row["packet_json"]) == p
    changed = copy.deepcopy(p)
    changed["rulebook_version"] = "t-2"
    s.write(changed)                                                           # same packet id, new content: replaced, not duplicated
    assert len(s.packets()) == 1 and s.packets()[0]["rulebook_version"] == "t-2"
    s.close()


def test_store_status_and_null_rule_for_unmatched(book, tmp_path):
    s = PacketStore(tmp_path / "log.db")
    s.write(packet(book, handoff(measure="unknown_thing")))
    s.write(packet(book, handoff(measure="lux")))
    rows = {r["status"]: r["rule_id"] for r in s.conn.execute("SELECT status, rule_id FROM rulebook_packets")}
    assert rows == {"unmatched": None, "deferred": "lux_deferred"}


def test_store_is_never_wiped_by_default_only_by_rebuild(book, tmp_path):
    db = tmp_path / "log.db"
    s = PacketStore(db)
    s.write(packet(book))
    s.close()
    s2 = PacketStore(db)                                                       # a plain open keeps the rows
    assert len(s2.packets()) == 1
    s2.close()
    s3 = PacketStore(db, rebuild=True)
    assert s3.packets() == []
    s3.close()


def test_rerun_gives_identical_rows(book, tmp_path):
    hs = [handoff(), handoff(meal=500), handoff(measure="lux"), handoff(opened="2030-05-11T01:00:00+00:00")]
    dumps = []
    for i in range(2):
        s = PacketStore(tmp_path / f"l{i}.db", rebuild=True)
        for h in hs:
            s.write(packet(book, h))
        dumps.append(list(s.conn.execute("SELECT * FROM rulebook_packets ORDER BY packet_id")))
        s.close()
    assert [tuple(r) for r in dumps[0]] == [tuple(r) for r in dumps[1]]


# ---------------------------------------------------------------- generic (property 15) ----------------------------------------------------------
def test_no_patient_names_in_the_engine_code():
    banned = ["glucose", "heart_rate", "sleep_duration", "metformin", "amlodipine", "levothyroxine", "meal_events", "diary_context", "step_count", "hydration",
              "screen_time", "blood_pressure", "mood_state", "medication_adherence", "thyroid", "meera", "cgm", "location"]
    for f in (ROOT / "src/v0_code/rulebook_lookup").glob("*.py"):
        text = f.read_text().lower().replace("data_status_meera_code", "")          # a column name of the rulebook file format, not a patient reference
        for w in banned:
            assert w not in text, f"{w} appears in {f.name}"


def test_second_patient_runs_on_config_alone(tmp_path):
    cfg = cfg_for(tz="America/New_York")
    b = load_rulebook(write_rulebook(tmp_path / "x"), cfg)
    p = build_packet(handoff(opened="2030-05-10T03:30:00+00:00", meal=500), b, cfg)             # 23:30 the evening before, New York
    assert p["matched_rule"]["rule_id"] == "sys_fasted"
    dawn = next((c for c in p["selected"] if c["candidate"] == "dawn"), None)
    assert dawn is not None and dawn["resolved_window"]["start"] == "2030-05-09T00:00:00-04:00"


# ---------------------------------------------------------------- the real rulebook on the real hand-offs -------------------------------------------
REAL_CFG = ROOT / "config/rulebook_meera_iyer_v1.yaml"
STATE_DB = ROOT / "output/state_engine.db"
real = pytest.mark.skipif(not (REAL_CFG.exists() and STATE_DB.exists()), reason="needs config/rulebook_meera_iyer_v1.yaml and output/state_engine.db")


@pytest.fixture(scope="module")
def real_run():
    from v0_code.state_engine.storage import StateStore
    cfg = RulebookConfig.from_yaml(REAL_CFG, ROOT)
    book = load_rulebook(cfg.rulebook_path(ROOT), cfg)
    hs = StateStore(STATE_DB, readonly=True)
    handoffs = hs.handoffs()
    hs.close()
    return cfg, book, handoffs, [build_packet(h, book, cfg) for h in handoffs]


@real
def test_real_rulebook_loads_and_counts(real_run):
    cfg, book, handoffs, packets = real_run
    assert len(book.rules) == 10 and sum(len(v) for v in book.candidates.values()) == 69 and book.version == "v0-draft-1"
    assert len(packets) == len(handoffs) == 287 and len({p["packet_id"] for p in packets}) == 287
    assert not [p for p in packets if p.get("status") == "unmatched" or p.get("status") == "ambiguous"]


@real
def test_real_selected_counts_match_section_9_3(real_run):
    _, _, _, packets = real_run
    per_rule = {}
    for p in packets:
        per_rule.setdefault(p["matched_rule"]["rule_id"], []).append(p)
    expected = {"heart_rate_above": (124, 8), "glucose_above_no_recent_meal": (59, 5), "glucose_above_post_meal": (40, 7), "medication_adherence_below": (24, 6),
                "resting_heart_rate_above": (12, 6), "sleep_below": (10, 6), "screen_time_above": (8, 0), "glucose_below": (5, 5), "blood_pressure_above": (3, 7),
                "hydration_below": (2, 5)}
    for rid, (n, sel) in expected.items():
        assert len(per_rule[rid]) == n, rid
        assert {p["counts"]["selected"] for p in per_rule[rid]} == {sel}, rid


@real
def test_real_skips_and_cuts_match_section_9_3(real_run):
    _, _, _, packets = real_run
    def count(rid, key, name, reason=None):
        return sum(1 for p in packets if p["matched_rule"]["rule_id"] == rid and any(x["candidate"] == name and (reason is None or x["reason"] == reason) for x in p[key]))
    assert count("glucose_above_post_meal", "skipped", "cycle_phase") == 40 and count("glucose_above_no_recent_meal", "skipped", "cycle_phase") == 59
    assert count("glucose_above_post_meal", "skipped", "other_medications") == 40 and count("blood_pressure_above", "skipped", "other_medications") == 3
    assert count("heart_rate_above", "skipped", "caffeine_stimulants", "no_stream") == 124 and count("glucose_below", "skipped", "hypoglycemic_agent", "applies_if_not_met") == 5
    assert count("glucose_above_no_recent_meal", "skipped", "dawn_effect") == 43 and count("glucose_above_no_recent_meal", "not_selected", "dawn_effect") == 16
    assert count("glucose_above_post_meal", "not_selected", "meal_timing") == 40 and count("glucose_above_no_recent_meal", "not_selected", "prior_evening_meal") == 59
    assert count("resting_heart_rate_above", "not_selected", "unusual_activity_prior_day") == 12 and count("sleep_below", "not_selected", "illness_symptoms") == 10
    never = set()
    sel = {}
    for p in packets:
        for c in p["selected"]:
            sel.setdefault(p["matched_rule"]["rule_id"], set()).add(c["candidate"])
    book_rows = list(csv.DictReader(open(ROOT / "task/evidence_engine/rulebook_v0_candidates.csv")))
    never = [(r["rule_id"], r["candidate"]) for r in book_rows if r["candidate"] not in sel.get(r["rule_id"], set())]
    assert len(never) == 14


@real
def test_real_deferred_packets(real_run):
    _, _, _, packets = real_run
    d = [p for p in packets if p.get("status") == "deferred"]
    assert len(d) == 8 and all(p["selected"] == [] and p["skipped"] == [] and len(p["not_selected"]) == 2 and p["counts"]["candidates_in_rule"] == 2 for p in d)


@real
def test_real_example_17_sept(real_run):
    _, _, _, packets = real_run
    p = next(p for p in packets if p["handoff_id"] == "handoff_glucose_2026-09-17T22:30")
    assert p["matched_rule"]["rule_id"] == "glucose_above_post_meal" and p["evidence_bar_hint"] == "raised"
    assert p["counts"] == {"candidates_in_rule": 10, "selected": 7, "skipped": 2, "not_selected": 1}
    assert [c["rank"] for c in p["selected"]] == [1, 2, 3, 4, 5, 6, 10]
    assert [s["candidate"] for s in p["skipped"]] == ["other_medications", "cycle_phase"] and p["not_selected"] == [{"candidate": "meal_timing", "weight_tier": "secondary", "reason": "budget"}]
    first = p["selected"][0]
    assert first["resolved_window"] == {"start": "2026-09-17T18:30:00+05:30", "end": "2026-09-17T22:30:00+05:30", "includes_after_open": False}
    assert [s["patient_stream"] for s in first["streams"]] == ["meal_events", "meal_events"]
    assert p["selected"][1]["resolved_window"]["start"] == "2026-09-16T00:00:00+05:30" and p["selected"][5]["resolved_window"]["start"] == "2026-09-15T00:00:00+05:30"
    assert p["selected"][2]["resolved_window"]["record"] == "latest_sleep_record_at_or_before_open"
    assert p["selected"][6]["candidate"] == "alcohol" and p["selected"][6]["sources"] == []


@real
def test_real_heart_rate_activity_resolves_to_hourly_steps(real_run):
    _, _, _, packets = real_run
    for p in (p for p in packets if p["matched_rule"]["rule_id"] == "heart_rate_above"):
        act = p["selected"][0]
        assert act["candidate"] == "activity" and act["streams"] == [
            {"generic": "step_count_hourly", "patient_stream": "step_count_hourly", "category": None, "available": True, "used": True},
            {"generic": "step_count", "patient_stream": "step_count", "category": None, "available": True, "used": False, "fallback_for": "step_count_hourly"}]


@real
def test_real_low_glucose_packets_carry_around_open(real_run):
    _, _, handoffs, packets = real_run
    lows = [p for p in packets if p["matched_rule"]["rule_id"] == "glucose_below"]
    assert len(lows) == 5
    for p in lows:
        w = p["selected"][0]["resolved_window"]
        assert p["selected"][0]["candidate"] == "sensor_artifact" and w["includes_after_open"] is True and w["earliest_evaluation_time"] > p["handoff_summary"]["opened_at"]


@real
def test_real_run_leaves_the_other_databases_untouched(tmp_path):
    import subprocess, sys
    files = [ROOT / "output/personal_data_store.db", STATE_DB]
    before = [hashlib.md5(f.read_bytes()).hexdigest() for f in files]
    out = tmp_path / "log.db"
    r = subprocess.run([sys.executable, "-m", "v0_code.rulebook_lookup.run", "--config", str(REAL_CFG), "--db", str(out), "--no-report"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert [hashlib.md5(f.read_bytes()).hexdigest() for f in files] == before
    s = PacketStore(out, readonly=True)
    assert len(s.packets()) == 287
    s.close()
