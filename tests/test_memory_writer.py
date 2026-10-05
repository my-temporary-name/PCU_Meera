"""The model's reduced job (headline, what stood out, notable reason) and the checks that guard it."""

import asyncio
import json

import pytest

from v0_code.nodes import memory_writer as mw
from v0_code.nodes.memory_writer import ModelEntry, assemble, check_notable, find_date, is_notable_by_code, validate_light

REC = {
    "window_id": "week_X", "tier": "week", "quiet": False, "reliable": True, "confidence": "high",
    "anchors_crossed": [], "anchors_questionable": [], "diary_events": [],
    "events_in_window": [{"date": "2026-01-22", "text": "Elder daughter's mid-term exam stress begins, mild household tension"}],
    "deltas": {"glucose_tir_pct": -3.45, "glucose_cv_pct": 0.14, "glucose_gmi_pct": 0.33},
    "stream_change_table": {"glucose": 14.33, "sleep": -1.82, "mood": -3.0, "steps": -802.76},
    "stream_direction_table": {"glucose": "up", "sleep": "down", "mood": "down", "steps": "flat"},
}
RENDERED = {"numbers": ["Glucose: average 146.37 mg/dL, time in range 95.21%."], "what_changed": ["Average glucose: up 14.33 mg/dL", "Sleep: down 1.82 hours",
            "Mood: 3 fewer strained periods of the day", "Steps: down 802.76 steps"]}
GOOD = ["Glucose ran higher than the week before, at about 146 mg/dL.", "Sleep fell by about 1.8 hours.", "Fewer strained periods of the day helped the mood picture."]


def entry(sentences=GOOD, headline="A harder week.", reason=None):
    return ModelEntry(headline=headline, what_stood_out=list(sentences), notable_reason=reason)


def fails(model, rec=REC):
    return validate_light(model, rec, RENDERED)


def kinds(f):
    return {x.split(":")[0].split(" ")[0] for x in f}


# ---- notability is code's ---------------------------------------------------------------------------------------------------------

def test_notability_is_forced_by_the_code_rule():
    assert not is_notable_by_code({"anchors_crossed": []})                                                      # empty -> false
    assert not is_notable_by_code({"anchors_crossed": ["a"], "anchors_questionable": ["a"]})                    # entirely questionable -> false
    assert is_notable_by_code({"anchors_crossed": ["a", "b"], "anchors_questionable": ["a"]})
    assert is_notable_by_code({"anchors_crossed": ["a"], "anchors_questionable": []})


def test_check_notable_guards_both_directions():
    assert check_notable({"is_notable": True, "notable_reason": "x"}, REC) == ["is_notable_must_be_false", "notable_reason_must_be_null_when_not_notable"]
    notable = {**REC, "anchors_crossed": ["sleep_hours_change"]}
    assert check_notable({"is_notable": True, "notable_reason": None}, notable) == ["notable_reason_missing_for_notable_window"]
    assert check_notable({"is_notable": True, "notable_reason": "Sleep fell."}, notable) == []


def test_a_notable_window_requires_a_notable_reason_from_the_model():
    notable = {**REC, "anchors_crossed": ["sleep_hours_change"]}
    assert any(f.startswith("notable_reason_missing") for f in validate_light(entry(), notable, RENDERED))
    assert not any(f.startswith("notable_reason_missing") for f in validate_light(entry(reason="Sleep fell a lot."), notable, RENDERED))


# ---- the six kept checks ------------------------------------------------------------------------------------------------------------

def test_a_clean_entry_passes():
    assert fails(entry()) == []


def test_numbers_must_be_grounded_rounding_is_fine():
    assert any(f.startswith("ungrounded_number") for f in fails(entry(["Glucose averaged 300 mg/dL.", *GOOD[1:]])))
    assert not any(f.startswith("ungrounded_number") for f in fails(entry(["Glucose averaged about 150 mg/dL.", *GOOD[1:]])))


def test_causal_language_is_rejected():
    assert any(f.startswith("forbidden_language") for f in fails(entry(["Glucose rose because sleep fell.", *GOOD[1:]])))


def test_wrong_direction_is_rejected_and_right_direction_passes():
    assert any(f.startswith("wrong_direction") for f in fails(entry(["Sleep rose by about 1.8 hours.", *GOOD[1:]])))
    assert not any(f.startswith("wrong_direction") for f in fails(entry()))
    # mood: "fewer strained periods" agrees with a negative change; "more" contradicts it
    assert any(f.startswith("wrong_direction") for f in fails(entry([GOOD[0], GOOD[1], "She had more strained periods of the day."])))


def test_a_direction_word_about_a_flat_measure_is_rejected():
    # the tag says steps are flat, so "went up" is a wrong claim (this is exactly the week-ending-2025-12-09 failure mode)
    assert any(f.startswith("wrong_direction") for f in fails(entry([GOOD[0], GOOD[1], "Steps went up a little."])))


@pytest.mark.parametrize("text", ["On 2025-12-09 glucose rose.", "Glucose rose on Dec 9.", "Glucose rose on 12-24.", "Glucose rose on the 9th.", "It happened 9 December."])
def test_the_model_may_not_write_dates(text):
    assert find_date(text)
    assert any(f.startswith("date_written_by_model") for f in fails(entry([text, *GOOD[1:]])))


def test_ordinary_numbers_and_ranges_are_not_dates():
    for t in ("Sleep averaged 6.9 hours.", "Time in range was 95.21%.", "Glucose ranged 110 to 180.", "Steps were 1,800."):
        assert find_date(t) is None, t


def test_the_model_may_not_quote_or_copy_diary_text():
    assert any(f.startswith("quote_marks") for f in fails(entry([GOOD[0], 'She noted "exam stress".', GOOD[2]])))
    copied = "Her elder daughter's mid-term exam stress begins at home."
    assert any(f.startswith("diary_text_copied") for f in fails(entry([GOOD[0], GOOD[1], copied])))
    assert not any(f.startswith(("diary_text_copied", "quote_marks")) for f in fails(entry([GOOD[0], GOOD[1], "Family stress around a child's exams added strain."])))


def test_sentence_count_is_enforced_with_a_lower_floor_for_quiet_windows():
    assert any(f.startswith("what_stood_out_count") for f in fails(entry(GOOD[:2])))
    assert any(f.startswith("what_stood_out_count") for f in fails(entry(GOOD + GOOD)))
    assert not any(f.startswith("what_stood_out_count") for f in validate_light(entry(GOOD[:1]), {**REC, "quiet": True}, RENDERED))


# ---- setting words are a prompt rule only ---------------------------------------------------------------------------------------------

def test_setting_words_are_a_prompt_rule_not_a_validator():
    assert "supervised" in mw.SYSTEM_PROMPT and "unless the text says so" in mw.SYSTEM_PROMPT
    assert not any("supervis" in f for f in fails(entry(["Two supervised blood-pressure readings were high.", *GOOD[1:]])))  # accepted rare miss


# ---- the old validators sit behind a flag, default off -----------------------------------------------------------------------------------

def test_strict_validators_are_off_by_default_and_catch_voice_when_on(monkeypatch, pipeline_records):
    assert mw.STRICT_VALIDATORS is False
    rec = pipeline_records["week_ENDING_2026-01-23"]
    raw = {"headline": "A steady week.", "what_stood_out": ["Glucose stayed in range.", "Steps stayed low.", "The record shows steady glucose elsewhere."], "notable_reason": None}
    assert mw.validate_window(raw, rec, None, rec["window_id"])[0] is not None          # off: passes the six checks
    monkeypatch.setattr(mw, "STRICT_VALIDATORS", True)
    model, f = mw.validate_window(raw, rec, None, rec["window_id"])
    assert model is None and any(x.startswith("system_voice") for x in f)                # on: the legacy voice check fires


# ---- the flow, with a stub model ------------------------------------------------------------------------------------------------------------

class StubLLM:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    async def ainvoke(self, messages):
        self.calls += 1
        r = self.replies.pop(0)
        return type("R", (), {"content": json.dumps(r(messages) if callable(r) else r)})()


def _window(pipeline_records, wid):
    return {"window_id": wid, "tier": pipeline_records[wid]["tier"], "record": pipeline_records[wid], "prior_record": None}


GOOD_REPLY = {"headline": "A steady day.", "what_stood_out": ["Glucose stayed in range all day.", "A dose was missed.", "Activity was low."], "notable_reason": None}


def test_flow_ok_on_first_attempt(pipeline_records):
    w = _window(pipeline_records, "day_2025-12-26")
    (res,) = asyncio.run(mw.process_batch(StubLLM([{w["window_id"]: GOOD_REPLY}]), "day", [w], asyncio.Semaphore(1)))
    assert res["llm_status"] == "ok" and res["first_attempt_ok"] and res["memory"]["headline"] == "A steady day."
    assert res["memory"]["rendered"]["material_changes"]            # code-rendered facts are always present


def test_flow_retries_once_then_ok(pipeline_records):
    w = _window(pipeline_records, "day_2025-12-26")
    bad = {**GOOD_REPLY, "what_stood_out": ["Glucose rose because of dinner.", "A dose was missed.", "Activity was low."]}
    llm = StubLLM([{w["window_id"]: bad}, {w["window_id"]: GOOD_REPLY}])
    (res,) = asyncio.run(mw.process_batch(llm, "day", [w], asyncio.Semaphore(1)))
    assert res["llm_status"] == "ok" and not res["first_attempt_ok"] and llm.calls == 2
    assert any(f.startswith("forbidden_language") for f in res["first_attempt_failures"])


def test_flow_falls_back_to_a_code_made_entry_after_two_failures(pipeline_records):
    w = _window(pipeline_records, "day_2025-12-26")
    bad = {**GOOD_REPLY, "headline": "Glucose rose because of dinner."}
    bad2 = {**GOOD_REPLY, "what_stood_out": ["Glucose rose on 2025-12-26.", "A dose was missed.", "Activity was low."]}
    (res,) = asyncio.run(mw.process_batch(StubLLM([{w["window_id"]: bad}, {w["window_id"]: bad2}]), "day", [w], asyncio.Semaphore(1)))
    m = res["memory"]
    assert res["llm_status"] == "code_only_fallback" and not res["first_attempt_ok"]
    assert m["headline"] and m["rendered"]["material_changes"] and m["is_notable"] is False       # never an empty memory
    top_two = [x.rstrip(".") for x in m["rendered"]["material_changes"][:2]]
    assert m["headline"] == "; ".join(top_two) + "."                                              # the top two material changes, from the code section
    assert m["what_stood_out"] == []


def test_fallback_when_the_retry_call_itself_fails_is_still_a_full_entry(pipeline_records):
    w = _window(pipeline_records, "day_2025-12-26")

    class Boom(StubLLM):
        async def ainvoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return type("R", (), {"content": json.dumps({w["window_id"]: {**GOOD_REPLY, "headline": "Because of dinner."}})})()
            raise RuntimeError("network down")
    (res,) = asyncio.run(mw.process_batch(Boom([]), "day", [w], asyncio.Semaphore(1)))
    assert res["llm_status"] == "code_only_fallback" and res["memory"]["headline"]


def test_a_quiet_window_falls_back_to_a_nothing_deviated_headline(pipeline_records):
    quiet = next(r for r in pipeline_records.values() if r["tier"] == "day" and r["quiet"] and not mw.is_early(r))
    m = mw.assemble_code_only(quiet, mw.STATUS_FALLBACK)
    assert m["headline"] == "Nothing deviated from her usual." and m["rendered"]["numbers"]


def test_a_notable_code_only_entry_carries_a_code_made_notable_reason(pipeline_records):
    rec = pipeline_records["week_ENDING_2025-11-22"]
    m = mw.assemble_code_only(rec, mw.STATUS_FALLBACK)
    assert m["is_notable"] and m["notable_reason"] and "sleep down" in m["notable_reason"] and check_notable(m, rec) == []


def test_assemble_forces_notable_reason_null_when_not_notable(pipeline_records):
    rec = pipeline_records["week_ENDING_2025-12-09"]
    a = assemble(rec, entry(reason="Something dramatic happened."))
    assert a["is_notable"] is False and a["notable_reason"] is None and check_notable(a, rec) == []


# ---- direction tags (fix 1) ----------------------------------------------------------------------------------------------------------

def test_tags_are_one_line_per_measure_with_direction_and_amount(pipeline_records):
    from v0_code.logic.render import direction_tags
    tags = {t.term: t.text for t in direction_tags(pipeline_records["week_ENDING_2025-11-22"])}
    assert tags["sedentary time"] == "sedentary time: up 49.71 minutes"
    assert tags["average glucose"] == "average glucose: up 14.33 mg/dL"
    assert tags["mood"] == "mood: 1.57 more strained periods of the day"
    flat = {t.term: t.text for t in direction_tags(pipeline_records["week_ENDING_2025-12-09"])}
    assert flat["average glucose"] == "average glucose: flat" and flat["post-meal glucose peak"] == "post-meal glucose peak: flat"


def test_golden_failure_week_2025_12_09_headline_said_higher_but_code_says_flat(pipeline_records):
    from v0_code.logic.render import direction_tags
    from v0_code.nodes.memory_writer import direction_failures
    tags = direction_tags(pipeline_records["week_ENDING_2025-12-09"])
    bad = "Glucose was mostly in range but average and meal peaks were higher, alongside a noticeable drop in medication adherence."
    assert any("post-meal glucose peak went up" in f and "flat" in f for f in direction_failures(bad, tags))
    assert direction_failures("Glucose held steady and medication adherence fell sharply.", tags) == []


def test_golden_failure_week_2025_11_22_sedentary_time_moved_the_same_way_as_glucose_not_opposite(pipeline_records):
    from v0_code.logic.render import direction_tags
    from v0_code.nodes.memory_writer import direction_failures
    tags = direction_tags(pipeline_records["week_ENDING_2025-11-22"])
    bad = "Sleep fell by 1.82 hours and sedentary time increased, moving the opposite way to glucose."
    f = direction_failures(bad, tags)
    assert any("sedentary time moved the opposite way to average glucose" in x for x in f)
    assert not any("sleep moved" in x for x in f)   # sleep really did move the opposite way to glucose
    assert direction_failures("Sedentary time rose, moving the same way as glucose, while sleep fell, the opposite way to glucose.", tags) == []


def test_direction_claims_are_checked_per_clause_and_decimals_do_not_split_sentences(pipeline_records):
    from v0_code.logic.render import direction_tags
    from v0_code.nodes.memory_writer import direction_failures
    tags = direction_tags(pipeline_records["day_2025-12-26"])
    ok = "Average glucose was 121.25 mg/dL with 100% time in range and dropped 5.99 mg/dL versus the previous day; variability fell 7.45 percentage points."
    assert direction_failures(ok, tags) == []


def test_a_negated_relation_is_not_a_claim(pipeline_records):
    from v0_code.logic.render import direction_tags
    from v0_code.nodes.memory_writer import direction_failures
    tags = direction_tags(pipeline_records["week_ENDING_2025-12-09"])
    assert direction_failures("Post-meal peaks averaged 170 mg/dL and no other measure moved together with glucose.", tags) == []


def test_headline_and_notable_reason_are_checked_too():
    notable = {**REC, "anchors_crossed": ["sleep_hours_change"]}
    assert any(f.startswith("wrong_direction") for f in validate_light(entry(headline="Sleep rose a lot.", reason="Sleep fell."), notable, RENDERED))
    assert any(f.startswith("wrong_direction") for f in validate_light(entry(reason="Sleep rose sharply."), notable, RENDERED))


def test_early_in_the_record_a_measure_with_a_change_but_no_flat_band_still_gets_a_directional_tag():
    from v0_code.logic.render import direction_tags
    rec = {"tier": "day", "deltas": {"sleep_hours": 2.9}, "stream_direction_table": {"glucose": "flat", "sleep": "insufficient_data"},
           "stream_change_table": {"glucose": 0.5, "sleep": None}}
    tag = {t.term: t for t in direction_tags(rec)}["sleep"]
    assert tag.direction == "up" and "2.9 hours" in tag.text and "no flat band yet" in tag.text   # consistent with the anchor line


# ---- prompt-only lines (fix 3) ---------------------------------------------------------------------------------------------------------------

def test_the_prompt_asks_for_the_diary_theme_in_the_headline_without_dates_or_quotes():
    assert "moderate or worse severity" in mw.SYSTEM_PROMPT and "names their theme in plain words" in mw.SYSTEM_PROMPT
    assert "without dates or quotes" in mw.SYSTEM_PROMPT


def test_the_prompt_ties_direction_words_to_the_tags():
    assert "DIRECTION TAGS" in mw.SYSTEM_PROMPT and "ONE measure" in mw.SYSTEM_PROMPT


# ---- bug fix: a direction word with no measure of its own in its clause attaches to nothing -------------------------------------------------

def _tags(**kw):
    from v0_code.logic.render import Tag
    return [Tag(t.replace("_", " "), d, f"{t}: {d}") for t, d in kw.items()]


def test_higher_blood_pressure_is_not_a_claim_about_sleep():
    from v0_code.nodes.memory_writer import direction_failures
    tags = _tags(sleep="flat")
    assert direction_failures("Short sleep and modest activity during a family puja, with slightly higher blood pressure", tags) == []


def test_more_activity_is_not_a_claim_about_glucose():
    from v0_code.nodes.memory_writer import direction_failures
    tags = _tags(average_glucose="down")
    assert direction_failures("Lower average glucose with full time-in-range and more activity.", tags) == []
    assert direction_failures("Excellent in-range glucose with lower average, more activity and one missed dose.", tags) == []


def test_more_stress_is_not_a_claim_about_sleep():
    from v0_code.nodes.memory_writer import direction_failures
    tags = _tags(sleep="down", average_glucose="down")
    assert direction_failures("Short, poor-sleep day with lower glucose and more stress", tags) == []


def test_a_direction_word_in_a_clause_that_names_a_measure_is_still_checked():
    from v0_code.nodes.memory_writer import direction_failures
    tags = _tags(sleep="down")
    assert direction_failures("Sleep rose a lot, with slightly higher blood pressure", tags)            # sleep rose: wrong
    assert direction_failures("Sleep fell a lot, with slightly higher blood pressure", tags) == []      # sleep fell: right; BP ignored


# ---- early windows: no model call, code-written headline, confidence low -----------------------------------------------------------------------

def test_exactly_the_first_14_days_are_early(pipeline_records):
    days = sorted((r for r in pipeline_records.values() if r["tier"] == "day"), key=lambda r: r["date"])
    early = [r["date"] for r in days if mw.is_early(r)]
    assert early == [r["date"] for r in days[:14]]


def test_early_weeks_and_the_first_month_checkpoint_are_early_too(pipeline_records):
    weeks = sorted((r for r in pipeline_records.values() if r["tier"] == "week"), key=lambda r: r["end_date"])
    assert mw.is_early(weeks[0]) and not mw.is_early(weeks[-1])
    months = sorted((r for r in pipeline_records.values() if r["tier"] == "month"), key=lambda r: r["end_date"])
    assert mw.is_early(months[0]) and not mw.is_early(months[1])


def test_an_early_window_makes_no_model_call_and_is_code_only_with_low_confidence(pipeline_records):
    wid = "day_2025-10-03"
    w = _window(pipeline_records, wid)
    llm = StubLLM([])
    (res,) = asyncio.run(mw.process_batch(llm, "day", [w], asyncio.Semaphore(1)))
    m = res["memory"]
    assert llm.calls == 0 and res["llm_status"] == "code_only_early" and res["first_attempt_ok"] is None
    assert "Not enough history" in m["headline"] and m["confidence"] == "low" and m["rendered"]["material_changes"] is not None


def test_early_windows_are_skipped_inside_a_mixed_batch(pipeline_records):
    early, late = _window(pipeline_records, "day_2025-10-03"), _window(pipeline_records, "day_2025-12-26")
    llm = StubLLM([{late["window_id"]: GOOD_REPLY}])
    res = asyncio.run(mw.process_batch(llm, "day", [early, late], asyncio.Semaphore(1)))
    assert [r["llm_status"] for r in res] == ["code_only_early", "ok"] and llm.calls == 1


def test_no_stored_memory_is_ever_empty_whatever_the_status(pipeline_records):
    for wid in ("day_2025-10-03", "day_2025-12-26", "week_ENDING_2025-11-22", "month_ENDING_2026-02-27"):
        for status in (mw.STATUS_EARLY, mw.STATUS_FALLBACK):
            m = mw.assemble_code_only(pipeline_records[wid], status)
            assert m["headline"] and m["rendered"]["numbers"] and m["rendered"]["material_changes"] is not None
