"""The text layer (findings_engine_spec.md 8): the numberless view, the seven checks, the model call with its retry and fallback, and the cache. A fake client stands in for the
model, so nothing here needs the network."""

import json
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from v0_code.evidence_engine.library import load_library
from v0_code.findings_engine import textcheck, textlayer
from v0_code.findings_engine.codeline import code_sentences
from v0_code.findings_engine.storage import FindingsStore
from v0_code.findings_engine.textcheck import check_text, parse
from v0_code.findings_engine.view import backing_entries, banned_words_in_view, build_view, merge_diary, view_hash, view_ids
from v0_code.intel_common.phrasebook import Phrasebook
from zoneinfo import ZoneInfo

import test_findings_factors as ff

ROOT = Path(__file__).resolve().parent.parent
PB = Phrasebook.load(ROOT / "config/findings_phrasebook_v0.yaml")
IST = ZoneInfo("Asia/Kolkata")
BANDS = {"night": [0, 5], "morning": [5, 12], "afternoon": [12, 18], "evening": [18, 24]}
TEXT_CFG = {"model": "m", "reasoning_effort": "low", "timeout_seconds": 90, "sdk_retries": 0, "retries": 1, "headline_max_words": 20, "sentences": {"min": 2, "max": 8}, "copy_words": 7, "cache": True}
LIB = load_library(ROOT / "config/evidence_library_v0.yaml")


def record_a():
    """Example A as a stored-version-like record (the structured layer from the factor tests plus the fields the view reads)."""
    c = ff.content(ff.example_a())
    return {"finding_id": "fnd_x_v2", "case_id": "x", "version": 2, "as_of": "2026-09-17T22:30:00+05:30", "local_date": "2026-09-17", **c}


HANDOFFS = [{"handoff_id": "a", "context": {"last_meal": {"label": "festive_dinner_2", "minutes_ago": 62}}}]
DIARY = [{"view_id": "d1", "category": "life_event", "timestamp": "2026-09-17T20:00:00+05:30", "description": "Quarter-close deadline day, delivered the numbers 3 times, largely deskbound",
          "severity_or_note": "moderate"},
         {"view_id": "d2", "category": "symptom", "timestamp": "2026-09-16T13:00:00+05:30", "description": "Noticed father unusually tired", "severity_or_note": "concerning, not her own symptom"}]
MEMORY = [{"view_id": "s1", "use": "yesterday_day", "gist_headline": "Missed multiple medicines during a stressful day.", "is_notable": 1}]


def view_a(rec=None, diary=None, pi=None):
    return build_view(rec or record_a(), HANDOFFS, DIARY if diary is None else diary, MEMORY, PB, IST, BANDS, pi)


# ---- the view -----------------------------------------------------------------------------------------------------------------------------------------
def test_the_view_has_the_new_keys_and_the_record_ids():
    v = view_a()
    assert list(v) == ["situation", "things", "sets", "history", "not_known_yet", "diary", "earlier_summaries", "earlier_conclusions"]
    assert v["situation"]["mode"] == "may_discuss_links" and v["situation"]["meal_context"] == "a festive dinner about an hour earlier" and "part_of_day" not in v["situation"]
    assert v["situation"]["measures"] == [{"id": "m1", "what": "heart rate was clearly above her usual", "part_of_day": "evening"},
                                          {"id": "m2", "what": "glucose was clearly above her usual", "part_of_day": "evening"}]
    f = {x["id"]: x for x in v["things"]}
    assert f["f1"]["wording"] == "event_unusual" and f["f1"]["position"].endswith("after dinners") and f["f3"]["set"] == "g1" and f["f4"]["wording"] == "present_only"
    assert f["f3"]["wording"] == "asserted" and f["f2"]["wording"] == "asserted_same_day"
    assert v["sets"] == [{"id": "g1", "reason": "present_together", "members": ["f2", "f3"]}]
    assert v["history"] == {"id": "h1", "note": "enough history"} and v["not_known_yet"] == {"id": "n1", "items": ["the day's step total"]} and v["earlier_conclusions"] == []
    assert [d["id"] for d in v["diary"]] == ["d1", "d2"] and v["diary"][0]["when"] == "that day" and v["diary"][1]["when"] == "the day before"
    assert v["diary"][1]["severity_or_note"] == "concerning, not her own symptom"
    assert v["earlier_summaries"] == [{"id": "s1", "window": "yesterday", "headline": "Missed multiple medicines during a stressful day."}]


def test_part_of_day_comes_from_each_measures_own_opened_at():
    rec = record_a()
    rec["measures"][0]["opened_at"] = "2026-09-17T09:05:00+05:30"
    ms = view_a(rec)["situation"]["measures"]
    assert [m["part_of_day"] for m in ms] == ["morning", "evening"]
    rec["measures"][1]["opened_at"] = "2026-09-17T02:30:00+05:30"
    assert [m["part_of_day"] for m in view_a(rec)["situation"]["measures"]] == ["morning", "night"]


def strip_ids(v):
    if isinstance(v, dict):
        return {k: strip_ids(x) for k, x in v.items() if k not in ("id", "members", "set", "about")}
    return [strip_ids(x) for x in v] if isinstance(v, list) else v


def banned_set():
    return {w.lower() for w in PB.raw['internal_words']}


def test_no_key_or_value_of_the_view_contains_a_banned_word():
    pres = dict(check="presence_check", support="not_applicable", state=None, es={"present": True})
    kinds = [ff.F(3, "sleep", ff.SLEEP, "not_supported", ["contrary"], "exposed"), ff.F(4, "stress", ff.STRESS, "insufficient", [], "exposed", reason="history"), ff.F(8, "thyroid_status", **pres)]
    for rec in (record_a(), {"finding_id": "x", "as_of": "2026-09-17T10:00:00+05:30", "local_date": "2026-09-17", **ff.content([ff.item("h1", "2026-09-17T10:00:00+05:30", kinds)])}):
        for hist in ("enough", "enough_for_some", "not_enough_history_yet"):
            rec["history_note"] = hist
            pi = [{"id": "p1", "about": ["f2"], "state": "early", "text": "An early observation.", "seen_before": "this_week"}]
            assert banned_words_in_view(view_a(rec, pi=pi), banned_set()) == []


def test_the_prompt_uses_no_banned_word_outside_its_list_and_the_list_has_exposure():
    body, listing = textlayer.SYSTEM_PROMPT.split("Do not use the words:")
    listing = listing.split("\n")[0]
    assert "exposure, exposures" in listing and all(w in listing for w in PB.raw["internal_words"])
    low = body.lower() + "\n".join(textlayer.SYSTEM_PROMPT.split("Do not use the words:")[1].split("\n")[1:]).lower()
    for w in PB.raw["internal_words"]:
        assert not re.search(rf"\b{re.escape(w)}\b", low), w


def test_not_mentioned_not_known_yet_and_static_facts_are_not_listed():
    rec = record_a()
    names_ = {f["name"] for f in view_a(rec)["things"]}
    assert not any("day's step total" in n or "alcohol" in n or "symptom" in n for n in names_)
    pres = dict(check="presence_check", support="not_applicable", state=None, es={"present": True})
    c = ff.content([ff.item("h1", "2026-09-17T10:00:00+05:30", [ff.F(8, "thyroid_status", **pres), ff.F(2, "sleep", ff.SLEEP, "supported", [], "exposed", tail=1.0)])])
    rec = {"finding_id": "x", "as_of": "2026-09-17T10:00:00+05:30", "local_date": "2026-09-17", **c}
    v = build_view(rec, [], [], [], PB, IST, BANDS)
    assert [f["name"] for f in v["things"]] == ["short sleep the night before"] and "thyroid" not in json.dumps(v)
    assert any(f["candidate"] == "thyroid_status" and f["wording_class"] == "exposure_only" for f in rec["factors"])        # still in the structured layer


def test_the_view_hash_is_stable_and_changes_with_the_view():
    assert view_hash(view_a()) == view_hash(view_a())
    v = view_a()
    v["situation"]["mode"] = "describe_only"
    assert view_hash(v) != view_hash(view_a())


def test_a_contrary_point_carries_its_statement_and_a_present_only_one_no_outcome():
    c = ff.content([ff.item("h1", "2026-09-17T10:00:00+05:30", [ff.F(3, "sleep", ff.SLEEP, "not_supported", ["contrary"], "exposed"), ff.F(4, "stress", ff.STRESS, "not_supported", [], "exposed")])])
    v = build_view({"finding_id": "x", "as_of": "2026-09-17T10:00:00+05:30", "local_date": "2026-09-17", **c}, [], [], [], PB, IST, BANDS)
    by = {f["wording"]: f for f in v["things"]}
    assert by["contrary_note"]["statement"] == "her glucose peaks after dinner have tended to be lower" and "outcome" not in by["present_only"]
    assert v["situation"]["mode"] == "describe_only"


def test_the_prompt_is_the_specs_verbatim_and_carries_the_new_rules():
    spec = (ROOT / "task/findings_engine_spec.md").read_text()
    block = spec.split("**System prompt**")[1].split("```")[1].strip()
    assert textlayer.SYSTEM_PROMPT == block
    retry = spec.split("**Retry addendum (appended once):**")[1].split("```")[1].strip()
    assert textlayer.RETRY_ADDENDUM == retry
    p = textlayer.SYSTEM_PROMPT
    assert "A set id counts as citing all the things in that set" in p and "two to eight short sentences" in p
    assert "concerns someone else" in p and "an earlier summary says" in p and "only in the same sentence as the thing it is about" in p


# ---- the diary entries behind a point ----------------------------------------------------------------------------------------------------------------------
ENTRIES = [
    {"context_id": "c1", "timestamp": "2025-11-14T10:00:00+05:30", "category": "symptom", "description": "Headache", "severity_or_note": "mild"},
    {"context_id": "c2", "timestamp": "2025-11-16T13:00:00+05:30", "category": "symptom", "description": "Noticed father unusually tired and low-appetite at family lunch", "severity_or_note": "concerning, not her own symptom"},
    {"context_id": "c3", "timestamp": "2025-11-17T09:00:00+05:30", "category": "life_event", "description": "Family gathering", "severity_or_note": ""},
    {"context_id": "c4", "timestamp": "2025-11-18T06:00:00+05:30", "category": "symptom", "description": "Slept badly", "severity_or_note": "mild"},
    {"context_id": "c5", "timestamp": "2025-11-18T20:00:00+05:30", "category": "symptom", "description": "after the event", "severity_or_note": ""},
]
for _e in ENTRIES:
    _e["at"] = datetime.fromisoformat(_e["timestamp"])
SYMPTOM = "symptom_entry@3d->post_meal_peak:lunch"


def symptom_record(state="exposed", extra=()):
    f = ff.F(6, "illness_symptoms", SYMPTOM, "insufficient", [], state, reason="history", date="2025-11-18")
    c = ff.content([ff.item("h1", "2025-11-18T15:15:00+05:30", [f, *extra], date="2025-11-18")])
    return {"finding_id": "x", "as_of": "2025-11-18T15:15:00+05:30", "local_date": "2025-11-18", **c}


def test_the_entries_behind_an_exposed_diary_point_are_found_by_the_librarys_category_and_window():
    rec = symptom_record()
    got = backing_entries(rec, LIB, ENTRIES, "diary_context", IST, 3)
    assert [(e["context_id"], e["backs"]) for e in got] == [("c4", ["f1"]), ("c2", ["f1"])]                  # c1 is before the window, c3 is another category, c5 is after as_of
    assert backing_entries(symptom_record("not_exposed"), LIB, ENTRIES, "diary_context", IST, 3) == []
    assert backing_entries(rec, LIB, ENTRIES, "another_source", IST, 3) == []
    many = ENTRIES + [{**ENTRIES[1], "context_id": f"x{i}", "timestamp": f"2025-11-17T0{i}:00:00+05:30", "at": datetime.fromisoformat(f"2025-11-17T0{i}:00:00+05:30")} for i in range(1, 4)]
    assert len(backing_entries(rec, LIB, many, "diary_context", IST, 3)) == 3                                  # at most three per point


def test_backing_entries_are_listed_first_keep_their_note_and_do_not_use_the_windows_places():
    rec = symptom_record()
    window = [{"view_id": "d1", "category": "life_event", "timestamp": "2025-11-18T07:00:00+05:30", "description": "Father hospitalized overnight", "severity_or_note": "severe, family crisis",
               "context_id": "c9"},
              {"view_id": "d2", "category": "symptom", "timestamp": "2025-11-18T06:00:00+05:30", "description": "Slept badly", "severity_or_note": "mild", "context_id": "c4"}]
    merged = merge_diary(window, backing_entries(rec, LIB, ENTRIES, "diary_context", IST, 3))
    assert [(e["view_id"], e.get("backs")) for e in merged] == [("d2", ["f1"]), ("d3", ["f1"]), ("d1", None)]      # a window entry that backs a point is promoted and keeps its id; new ones get the next ids
    v = view_a(rec, diary=merged)
    first = v["diary"][0]
    assert first["backs"] == ["f1"] and v["diary"][1]["severity_or_note"] == "concerning, not her own symptom" and v["diary"][1]["when"] == "in the days before" and "backs" not in v["diary"][2]


# ---- the checks ---------------------------------------------------------------------------------------------------------------------------------------
def good():
    return {"headline": "Glucose and heart rate were clearly above her usual in the evening.",
            "sentences": [{"text": "The rise after this dinner was among the very highest she has had within the hour or so after dinners.", "refs": ["f1"]},
                          {"text": "Missed doses on the same day or the day before and short sleep the night before have tended to move together with higher glucose peaks after dinner, and both were present, "
                                   "the missed doses on the same day.", "refs": ["g1", "f2", "f3"]},
                          {"text": "It is not known yet how active she was that day.", "refs": ["n1"]}]}


def run_checks(obj, view=None, rec=None):
    view = view or view_a()
    return check_text(obj, view, rec or record_a(), PB, TEXT_CFG, view_ids(view))


def names(fs):
    return sorted({f["check"] for f in fs})


def test_a_good_answer_passes_every_check():
    assert run_checks(good()) == []


def test_check_1_structure():
    g = good()
    assert parse("not json")[1][0]["check"] == 1 and parse("[1]")[1][0]["check"] == 1
    long = {**g, "headline": "word " * 21}
    assert 1 in names(run_checks(long))
    assert 1 in names(run_checks({**g, "sentences": g["sentences"][:1]})) and 1 in names(run_checks({**g, "sentences": g["sentences"] * 3}))      # 9 sentences
    assert 1 not in names(run_checks({**g, "sentences": g["sentences"] * 2}))                                                                      # six are allowed
    eight = g["sentences"] * 2 + g["sentences"][:2]
    assert len(eight) == 8 and 1 not in names(run_checks({**g, "sentences": eight})) and 1 in names(run_checks({**g, "sentences": eight + g["sentences"][:1]}))     # eight are allowed, nine are not
    assert 1 in names(run_checks({**g, "sentences": [{"text": "x y", "refs": []}, g["sentences"][0]]}))


def test_check_2_refs_exist():
    g = good()
    g["sentences"][0]["refs"] = ["f99"]
    assert names(run_checks(g)) == [2]


@pytest.mark.parametrize("text", ["It happened at 5 in the evening.", "This was the first time.", "It rose in March.", "She felt it once.", "It happened at four p.m."])
def test_check_3_digits_dates_times_and_counting_words(text):
    g = good()
    g["sentences"][0]["text"] = text
    assert 3 in names(run_checks(g))


@pytest.mark.parametrize("text", ["Short sleep caused the rise.", "A late meal triggered it.", "This led to a rise.", "It is due to stress.", "It happened because of stress.", "Sleep explains it.",
                                  "Stress affected her.", "Activity had an impact.", "It was influenced by sleep.", "Doses contributed.", "As a result she rose.", "Thanks to the walk."])
def test_check_4_causal_wording(text):
    g = good()
    g["sentences"][0]["text"] = text
    assert 4 in names(run_checks(g))


def test_check_5_copied_diary_text_and_internal_words():
    g = good()
    g["sentences"][0]["text"] = "The diary says quarter-close deadline day, delivered the numbers."
    g["sentences"][0]["refs"] = ["d1"]
    assert 5 in names(run_checks(g))
    ok = good()
    ok["sentences"][0]["text"] = "The diary describes a busy deadline day at work."
    ok["sentences"][0]["refs"] = ["d1"]
    assert run_checks(ok) == []
    for w in ("evidence", "factor", "case", "class", "group", "memory", "exposure", "exposures"):
        bad = good()
        bad["sentences"][0]["text"] = f"There is a {w} here."
        assert 5 in names(run_checks(bad)), w


def test_check_6_claim_level_matches_the_refs():
    g = good()
    # exposure_only factor with a claim phrase
    g["sentences"][0] = {"text": "A stressed period has tended to move together with higher peaks.", "refs": ["f4"]}
    assert 6 in names(run_checks(g))
    # a hedged phrase on an asserted factor is allowed; a claim phrase with no factor is not
    h = good()
    h["sentences"][0] = {"text": "Short sleep may be linked to higher glucose peaks after dinner.", "refs": ["f3"]}
    assert run_checks(h) == []
    n = good()
    n["sentences"][0] = {"text": "Something has tended to move together with higher peaks.", "refs": ["m1"]}
    assert 6 in names(run_checks(n))
    # a same-day class needs "same day"
    s = good()
    s["sentences"][1] = {"text": "Missed doses have tended to move together with higher glucose peaks after dinner.", "refs": ["f2"]}
    assert 6 in names(run_checks(s))
    # a cited group id counts as citing all its members: the claim level is judged on the members
    m = good()
    m["sentences"][1] = {"text": "Missed doses on the same day have tended to move together with higher peaks, and short sleep too.", "refs": ["g1"]}
    assert run_checks(m) == []
    m["sentences"][1] = {"text": "Missed doses on the same day may be linked to higher peaks.", "refs": ["g1"]}
    assert run_checks(m) == []
    m["sentences"][1] = {"text": "Missed doses have tended to move together with higher peaks.", "refs": ["g1"]}                  # a same-day member needs "same day"
    assert 6 in names(run_checks(m))
    m["sentences"][1] = {"text": "A stressed period has tended to move together with higher peaks.", "refs": ["g1", "f4"]}      # a group plus an other-class point
    assert 6 in names(run_checks(m))
    # an event factor in a claim sentence is another class
    e = good()
    e["sentences"][1]["refs"] = ["g1", "f2", "f3", "f1"]
    assert 6 in names(run_checks(e))


def test_check_7_no_longer_fails_a_text_it_is_completed_by_code():
    g = good()
    g["sentences"][2] = {"text": "She was also clearly above her usual.", "refs": ["m1"]}
    assert run_checks(g) == []                                                                    # a missing statement is not a failure any more
    assert textcheck.missing_required(g, view_a(), record_a()) == ["n1"]
    rec = record_a()
    rec["history_note"] = "not_enough_history_yet"
    view = view_a(rec)
    assert textcheck.missing_required(good(), view, rec) == ["h1"]
    ok = good()
    ok["sentences"][2]["refs"] = ["n1", "h1"]
    ok["sentences"].append({"text": "There is not enough history yet to say what usually goes with this.", "refs": ["h1"]})
    assert textcheck.missing_required(ok, view, rec) == []


# ---- the call, the retry, the fallback and the cache ----------------------------------------------------------------------------------------------------
class FakeClient:
    def __init__(self, answers):
        self.answers, self.calls, self.prompts = list(answers), 0, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.calls += 1
        self.prompts.append(kw["messages"])
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50, completion_tokens_details=SimpleNamespace(reasoning_tokens=20))
        return SimpleNamespace(usage=usage, choices=[SimpleNamespace(message=SimpleNamespace(content=a if isinstance(a, str) else json.dumps(a)))])


def gen(client, store=None, refresh=False):
    rec = record_a()
    return textlayer.generate(view_a(rec), rec, code_sentences(rec, PB), client, TEXT_CFG, PB, store, refresh)


def test_first_attempt_pass_uses_the_model_text():
    c = FakeClient([good()])
    r = gen(c)
    assert (r.text_source, r.status, c.calls) == ("llm", "ok", 1) and r.text["source"] == "llm" and r.text["sentences"][0]["refs"] == ["f1"] and r.usage[0]["input_tokens"] == 100
    assert c.prompts[0][0]["role"] == "system" and c.prompts[0][0]["content"] == textlayer.SYSTEM_PROMPT and c.prompts[0][1]["content"].startswith("VIEW:\n")


def test_a_failed_check_is_retried_once_with_the_failures_appended_then_passes():
    bad = good()
    bad["sentences"][0]["text"] = "Sleep caused it."
    c = FakeClient([bad, good()])
    r = gen(c)
    assert (r.status, c.calls, [len(x) for x in r.checks]) == ("ok", 2, [1, 0]) and r.checks[0][0]["check"] == 4
    assert "Your previous answer failed these checks" in c.prompts[1][1]["content"] and "causal" in c.prompts[1][1]["content"] and c.prompts[1][1]["content"].startswith(c.prompts[0][1]["content"])


def test_two_failures_store_the_code_line():
    bad = good()
    bad["sentences"][0]["text"] = "Sleep caused it."
    c = FakeClient([bad, bad])
    r = gen(c)
    rec = record_a()
    assert (r.status, r.text_source, c.calls) == ("code_line_fallback", "code_line", 2) and r.text["source"] == "code_line"
    assert r.text["headline"] == code_sentences(rec, PB)[0] and [s["text"] for s in r.text["sentences"]] == code_sentences(rec, PB)[1:]


def test_a_call_error_and_bad_json_count_as_failed_attempts():
    c = FakeClient([TimeoutError("took too long"), "not json"])
    r = gen(c)
    assert r.status == "code_line_fallback" and r.checks[0][0]["name"] == "call_error" and r.checks[1][0]["check"] == 1 and r.llm_raw[0].startswith("ERROR")
    c = FakeClient([TimeoutError("slow"), good()])
    assert gen(c).status == "ok"


def test_a_second_run_makes_no_model_call_and_refresh_recomputes(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    c = FakeClient([good()])
    rec, view = record_a(), view_a()
    first = textlayer.generate(view, rec, code_sentences(rec, PB), c, TEXT_CFG, PB, s)
    s.put_text("fnd_x_v2", textlayer.cache_key(view, TEXT_CFG), view_hash(view), first.as_dict())
    c2 = FakeClient([])
    again = textlayer.generate(view, rec, code_sentences(rec, PB), c2, TEXT_CFG, PB, s)
    assert c2.calls == 0 and again.from_cache and again.text == first.text and again.usage == first.usage
    c3 = FakeClient([good()])
    textlayer.generate(view, rec, code_sentences(rec, PB), c3, TEXT_CFG, PB, s, refresh=True)
    assert c3.calls == 1
    other = {**TEXT_CFG, "model": "another"}
    c4 = FakeClient([good()])
    textlayer.generate(view, rec, code_sentences(rec, PB), c4, other, PB, s)
    assert c4.calls == 1                                                                          # a different model is a different cache key


def test_the_text_layer_never_changes_a_stored_version(tmp_path):
    s = FindingsStore(tmp_path / "f.db")
    version = {"finding_id": "fnd_x_v2", "case_id": "x", "version": 2, "as_of": "t", "mode": "relationship", "provisional": True, "closed": False, "text": {"source": "code_line"}, "status": "ok"}
    s.put_finding(version)
    before = s.conn.execute("SELECT record_json FROM findings").fetchall()
    s.put_text("fnd_x_v2", "k", "h", {"text": {"headline": "x"}, "text_source": "llm", "status": "ok", "llm_raw": [], "usage": [], "checks": []})
    assert s.conn.execute("SELECT record_json FROM findings").fetchall() == before and s.texts()["fnd_x_v2"]["text_source"] == "llm"
    s.close()
    FindingsStore(tmp_path / "f.db", rebuild=True)
    assert FindingsStore(tmp_path / "f.db", readonly=True).texts() != {}                       # a code-layer rebuild keeps the text layer's cache


# ---- check 8: recurrence wording and earlier summaries ----------------------------------------------------------------------------------------------------------
PI_ITEM = [{"id": "p1", "about": ["f2"], "state": "early", "text": "An early observation of missed doses and higher dinner peaks.", "seen_before": "this_week"}]


def test_check_8_recurrence_wording_needs_an_earlier_conclusion_item():
    g = good()
    g["sentences"][0] = {"text": "This has come up before.", "refs": ["f1"]}
    assert 8 in names(run_checks(g))
    g["sentences"][0] = {"text": "This was an early observation.", "refs": ["s1"]}
    assert 8 in names(run_checks(g))
    pv = view_a(pi=PI_ITEM)
    g["sentences"][0] = {"text": "This has come up before, that day.", "refs": ["f2", "p1"]}
    assert run_checks(g, pv) == []
    g["sentences"][0] = {"text": "It is an early observation, and it came up before, that day.", "refs": ["f2", "p1"]}
    assert run_checks(g, pv) == []
    g["sentences"][0] = {"text": "This came up before, that day.", "refs": ["f2"]}
    assert 8 in names(run_checks(g, pv))                                                          # the item exists in the view but the sentence does not cite it


def test_check_8_an_earlier_summary_is_not_combined_with_a_point_claim_or_an_artifact():
    g = good()
    g["sentences"][0] = {"text": "An earlier summary says she missed doses.", "refs": ["s1"]}
    assert run_checks(g) == []
    g["sentences"][0] = {"text": "An earlier summary says she missed doses, and short sleep has tended to move together with higher peaks.", "refs": ["s1", "f3"]}
    assert 8 in names(run_checks(g))                                                              # a claim-class point with an earlier summary
    g["sentences"][0] = {"text": "An earlier summary says she missed doses; short sleep has tended to move together with peaks.", "refs": ["s1"]}
    assert 8 in names(run_checks(g)) or 6 in names(run_checks(g))                                 # the claim phrase with no point cited is already check 6
    g["sentences"][0] = {"text": "An earlier summary says she missed doses, and she was also present at the meal.", "refs": ["s1", "f4"]}
    assert run_checks(g) == []                                                                    # a present-only point may sit beside an earlier summary
    art = ff.content([ff.item("h1", "2026-09-17T10:00:00+05:30", [{**ff.F(1, "sensor_artifact", check="shape_check", support="supported", state=None, es={})}])])
    rec = {"finding_id": "x", "as_of": "2026-09-17T10:00:00+05:30", "local_date": "2026-09-17", **art}
    view = build_view(rec, [], [], MEMORY, PB, IST, BANDS)
    view["earlier_summaries"] = [{"id": "s1", "window": "yesterday", "headline": "Missed medicines."}]          # the view builder would leave it out; the rule still holds if it were there
    ans = {"headline": "Glucose was clearly above her usual.", "sentences": [{"text": "This may be a sensor artifact.", "refs": ["f1"]},
                                                                           {"text": "An earlier summary says she missed medicines, and this may be a sensor artifact.", "refs": ["s1", "f1"]}]}
    assert 8 in names(check_text(ans, view, rec, PB, TEXT_CFG, view_ids(view)))


# ---- earlier summaries in the view -------------------------------------------------------------------------------------------------------------------------
def memory3(notable=1):
    return [{"view_id": "s1", "use": "yesterday_day", "gist_headline": "Missed multiple medicines.", "is_notable": notable},
            {"view_id": "s2", "use": "last_week", "gist_headline": "A busy week.", "is_notable": 1},
            {"view_id": "s3", "use": "latest_month", "gist_headline": "A steady month.", "is_notable": 1}]


def test_only_a_notable_yesterday_summary_reaches_the_view():
    rec = record_a()
    v = build_view(rec, HANDOFFS, DIARY, memory3(1), PB, IST, BANDS)
    assert [s["id"] for s in v["earlier_summaries"]] == ["s1"] and v["earlier_summaries"][0]["window"] == "yesterday"
    assert build_view(rec, HANDOFFS, DIARY, memory3(0), PB, IST, BANDS)["earlier_summaries"] == []                 # not notable: left out
    assert build_view(rec, HANDOFFS, DIARY, memory3(None), PB, IST, BANDS)["earlier_summaries"] == []
    only_week = [m for m in memory3(1) if m["use"] != "yesterday_day"]
    assert build_view(rec, HANDOFFS, DIARY, only_week, PB, IST, BANDS)["earlier_summaries"] == []                  # week and month are never in the view
    wide = build_view(rec, HANDOFFS, DIARY, memory3(1), PB, IST, BANDS, summaries={"use": ["yesterday_day", "last_week"], "notable_only": False})
    assert [s["id"] for s in wide["earlier_summaries"]] == ["s1", "s2"]                                           # the rule is config, not code


def test_a_version_with_an_artifact_point_has_no_earlier_summary():
    art = ff.content([ff.item("h1", "2026-09-17T10:00:00+05:30", [ff.F(1, "sensor_artifact", check="shape_check", support="supported", state=None, es={})])])
    rec = {"finding_id": "x", "as_of": "2026-09-17T10:00:00+05:30", "local_date": "2026-09-17", **art}
    assert [p["wording"] for p in build_view(rec, [], [], memory3(1), PB, IST, BANDS)["things"]] == ["artifact_note"]
    assert build_view(rec, [], [], memory3(1), PB, IST, BANDS)["earlier_summaries"] == []


def test_check_10_at_most_one_sentence_cites_an_earlier_summary():
    g = good()
    g["sentences"][0] = {"text": "An earlier summary says she missed doses.", "refs": ["s1"]}
    assert run_checks(g) == []
    g["sentences"][1] = {"text": "An earlier summary says she was busy.", "refs": ["s1"]}
    assert 10 in names(run_checks(g))


# ---- check 9: an entangled bundle is described as entangled -----------------------------------------------------------------------------------------------
def entangled_record():
    ov = [{"a": "sleep_hours@prev_night", "b": "missed_dose@2d", "a_view": "x", "b_view": "y", "share_given_a": 0.9, "share_overall": 0.3, "ratio": 3.0, "flag": True}]
    c = ff.content([ff.item("h1", "2026-09-17T10:00:00+05:30", [ff.F(2, "sleep", "sleep_hours@prev_night->hr_day_mean", "supported", [], "exposed", tail=1.0),
                                                              ff.F(3, "missed", "missed_dose@2d->hr_day_mean", "supported", ["same_day_unverified"], "exposed")], overlap=ov, measure="heart_rate")])
    return {"finding_id": "x", "as_of": "2026-09-17T10:00:00+05:30", "local_date": "2026-09-17", **c}


def entangled_answer(sentence):
    return {"headline": "Heart rate was clearly above her usual.", "sentences": [{"text": "Her heart rate was clearly above her usual.", "refs": ["m1"]}, {"text": sentence, "refs": ["g1"]},
                                                                              {"text": "There is nothing else to add.", "refs": ["h1"]}]}


def test_check_9_a_sentence_citing_an_entangled_bundle_says_so():
    rec = entangled_record()
    view = build_view(rec, [], [], [], PB, IST, BANDS)
    assert view["sets"][0]["reason"] == "often_together"
    claim = "Short sleep the night before and missed doses on the same day have tended to move together with higher heart rate"
    run = lambda s: check_text(entangled_answer(s), view, {**rec, "history_note": "enough_for_some"}, PB, TEXT_CFG, view_ids(view))
    assert names(run(claim + ".")) == [9]
    assert names(run(claim + ", and they often occur together.")) == [9]
    assert names(run(claim + "; their separate roles cannot be told apart.")) == [9]
    assert run(claim + "; they often occur together and their separate roles cannot be told apart.") == []
    assert run(claim + "; they often occur together, so their separate roles cannot be told apart.") == []
    other = good()                                                                                # a co-exposed bundle needs no such wording
    assert run_checks(other) == []


# ---- view ids never appear in the text --------------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["The g1 members were present.", "Point f3 was present.", "See m1 for details.", "The d1 entry says so.", "As s1 says.", "p2 applies.", "Per h1 there is no history.", "Listed in n1."])
def test_a_view_id_in_the_text_is_a_check_failure(text):
    g = good()
    g["sentences"][0]["text"] = text
    fs = run_checks(g)
    assert 3 in names(fs) and any("view id" in f["detail"] for f in fs)
    h = good()
    h["headline"] = text
    assert any("view id" in f["detail"] for f in run_checks(h))


# ---- the prompt's added rules ------------------------------------------------------------------------------------------------------------------------------
def test_the_prompt_has_the_new_rules():
    p = textlayer.SYSTEM_PROMPT
    assert "Never write view ids" in p and "f1, g1, m1, d1, s1, p1, h1, n1" in p and "only in refs" in p
    assert "Use each thing's phrase exactly as given, including its window phrase" in p and "do not shorten or merge phrases" in p
    assert 'Do not use "drink", "drank" or "drinking" for fluid intake' in p


# ---- the cache key --------------------------------------------------------------------------------------------------------------------------------------------
def test_the_cache_key_covers_the_view_prompts_model_settings_and_checks_version(monkeypatch):
    v = view_a()
    base = textlayer.cache_key(v, TEXT_CFG)
    assert textlayer.cache_key(view_a(), TEXT_CFG) == base
    v2 = view_a()
    v2["situation"]["mode"] = "describe_only"
    assert textlayer.cache_key(v2, TEXT_CFG) != base
    for k, val in (("model", "other"), ("reasoning_effort", "high"), ("retries", 2), ("headline_max_words", 15), ("sentences", {"min": 2, "max": 4}), ("copy_words", 6)):
        assert textlayer.cache_key(v, {**TEXT_CFG, k: val}) != base, k
    assert textlayer.cache_key(v, {**TEXT_CFG, "timeout_seconds": 5, "concurrency": 1}) == base                  # settings that do not change an answer do not change the key
    for name in ("SYSTEM_PROMPT", "USER_TEMPLATE", "RETRY_ADDENDUM"):
        monkeypatch.setattr(textlayer, name, getattr(textlayer, name) + " x")
        assert textlayer.cache_key(v, TEXT_CFG) != base, name
        monkeypatch.undo()
    monkeypatch.setattr(textcheck, "CHECKS_VERSION", "another")
    assert textlayer.cache_key(v, TEXT_CFG) != base


# ---- the full run: waves, resumability and the stop rules ----------------------------------------------------------------------------------------------------
def fake_result(first_fail=False, call_error=False, fallback=False):
    checks = [[{"check": 0, "name": "call_error", "detail": "x"}] if call_error else ([{"check": 6, "name": "claim_level", "detail": "x"}] if first_fail else [])]
    if fallback or (first_fail and fallback is None):
        checks.append([{"check": 6, "name": "claim_level", "detail": "x"}])
    if first_fail and not fallback:
        checks.append([])
    return textlayer.TextResult({"headline": "h", "sentences": [], "source": "llm"}, "code_line" if fallback else "llm", "code_line_fallback" if fallback else "ok", ["raw"] * len(checks),
                                [{"wall_seconds": 1}] * len(checks), checks)


def waves_env(tmp_path, n, plan, monkeypatch):
    from v0_code.findings_engine import run_text
    store = FindingsStore(tmp_path / "w.db")
    records = [{"finding_id": f"v{i:03d}"} for i in range(n)]
    views = {r["finding_id"]: {"situation": {"mode": "m"}, "i": i} for i, r in enumerate(records)}
    calls = []

    def fake_generate(view, record, sentences, client, tcfg, pb, store_, refresh):
        calls.append(record["finding_id"])
        return plan(view["i"])
    monkeypatch.setattr(textlayer, "generate", fake_generate)
    monkeypatch.setattr(textlayer, "cached", lambda view, tcfg, st, fid=None: None if st is None or st.get_cached(textlayer.cache_key(view, tcfg), fid) is None else textlayer.TextResult(
        {"headline": "h", "sentences": [], "source": "llm"}, "llm", "ok", [], [], [], from_cache=True))
    monkeypatch.setattr(run_text, "code_sentences", lambda r, pb: ["x"])
    return run_text, store, records, views, calls


STOP = {"after": 40, "max_first_failure": 0.45, "max_call_errors": 0.10}


def test_the_full_run_stops_when_too_many_first_attempts_fail(tmp_path, monkeypatch):
    run_text, store, records, views, calls = waves_env(tmp_path, 100, lambda i: fake_result(first_fail=i % 2 == 0), monkeypatch)
    # half of the versions fail their first attempt: over 45 percent at the check after 40
    res, reason = run_text.run_waves({**TEXT_CFG, "concurrency": 2}, None, store, records, views, None, wave=10, stop=STOP)
    assert reason and "first attempt" in reason and 40 <= len(res) < 100 and len(calls) == len(res)
    assert len(store.texts()) == len(res)                                                         # every finished version was saved before the stop


def test_the_full_run_stops_on_api_errors_and_otherwise_finishes_and_is_resumable(tmp_path, monkeypatch):
    run_text, store, records, views, calls = waves_env(tmp_path, 60, lambda i: fake_result(call_error=i % 5 == 0), monkeypatch)
    res, reason = run_text.run_waves({**TEXT_CFG, "concurrency": 2}, None, store, records, views, None, wave=10, stop=STOP)
    assert reason and "error" in reason
    store2 = FindingsStore(tmp_path / "ok.db")
    run_text2, _, records2, views2, calls2 = waves_env(tmp_path, 60, lambda i: fake_result(first_fail=i % 10 == 0), monkeypatch)
    res, reason = run_text2.run_waves({**TEXT_CFG, "concurrency": 2}, None, store2, records2, views2, None, wave=10, stop=STOP)
    assert reason is None and len(res) == 60 and len(calls2) == 60
    again, reason = run_text2.run_waves({**TEXT_CFG, "concurrency": 2}, None, store2, records2, views2, None, wave=10, stop=STOP)
    assert reason is None and len(again) == 60 and len(calls2) == 60                               # the second run served everything from the store: no new call


def test_a_cached_result_is_each_versions_own_when_two_versions_share_a_key(tmp_path):
    """Two versions with the same view get the same cache key; each is generated, and a replay must give each one its own stored text."""
    s = FindingsStore(tmp_path / "f.db")
    for fid, head in (("fnd_a_v1", "first text"), ("fnd_b_v1", "second text")):
        s.put_text(fid, "same-key", "h", {"text": {"headline": head, "sentences": [], "source": "llm"}, "text_source": "llm", "status": "ok", "llm_raw": ["r"], "usage": [{}], "checks": [[]]})
    assert s.get_cached("same-key", "fnd_b_v1")["text"]["headline"] == "second text"
    assert s.get_cached("same-key", "fnd_a_v1")["text"]["headline"] == "first text"
    assert s.get_cached("same-key", "fnd_c_v1")["text"]["headline"] == "first text"            # a version with no row of its own gets a stored result for the view
    assert s.get_cached("another-key", "fnd_a_v1") is None
    v, rec = view_a(), record_a()
    key = textlayer.cache_key(v, TEXT_CFG)
    s.put_text("fnd_x_v2", key, view_hash(v), {"text": {"headline": "mine", "sentences": [], "source": "llm"}, "text_source": "llm", "status": "ok", "llm_raw": [], "usage": [], "checks": []})
    s.put_text("fnd_a_v1", key, view_hash(v), {"text": {"headline": "other", "sentences": [], "source": "llm"}, "text_source": "llm", "status": "ok", "llm_raw": [], "usage": [], "checks": []})
    assert textlayer.cached(v, TEXT_CFG, s, "fnd_x_v2").text["headline"] == "mine"


def test_a_version_served_from_a_twins_cache_entry_gets_its_own_stored_row(tmp_path, monkeypatch):
    run_text, store, records, views, calls = waves_env(tmp_path, 3, lambda i: fake_result(), monkeypatch)
    views["v002"] = views["v000"]                                                                  # v002 has the same view (and so the same key) as v000
    run_text.run_waves({**TEXT_CFG, "concurrency": 1}, None, store, records[:1], views, None, wave=10)
    monkeypatch.setattr(textlayer, "cached", lambda view, tcfg, st, fid=None: textlayer.TextResult({"headline": "h", "sentences": [], "source": "llm"}, "llm", "ok", [], [], [], from_cache=True)
                        if st.get_cached(textlayer.cache_key(view, tcfg), fid) else None)
    res, reason = run_text.run_waves({**TEXT_CFG, "concurrency": 1}, None, store, [records[2]], views, None, wave=10)
    assert reason is None and "v002" in store.texts() and len(calls) == 1
