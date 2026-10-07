"""Findings text layer, the polish round: prompt p-v5 and checks ck-v7. (1) a same-day point needs one of four same-day markers; (2) things with the same name, wording and position are merged in the
view and refs resolve to every member; (3) a sentence that cites an earlier conclusion must cite what it is about (check 15); (4) cleanup finishes a sentence with a full stop, and a sentence
may not cite the history note when there is enough history (check 16). The structured layer is never touched."""

import copy
import json

import pytest

from test_findings_text import PB, TEXT_CFG, good, names, record_a, run_checks, view_a
from v0_code.findings_engine import textcheck, textclean, textlayer
from v0_code.findings_engine.textcheck import check_text
from v0_code.findings_engine.view import merge_things, thing_index, view_ids


def test_versions_and_compatible_prompts():
    assert textlayer.PROMPT_VERSION == "p-v5" and textcheck.CHECKS_VERSION == "ck-v7"
    assert textlayer.COMPATIBLE_PROMPTS == {"p-v5": ("p-v4", "p-v3", "p-v2", "p-v1")}


# ---- 1. the same-day marker ----------------------------------------------------------------------------------------------------------------------------------------
def same_day_view():
    v = view_a()
    v["things"][2]["wording"] = "asserted_same_day"            # short sleep the night before: its own phrase has no same-day marker
    return v


def say(text, refs, view=None):
    g = good()
    g["sentences"][1] = {"text": text, "refs": refs}
    v = view or same_day_view()
    return check_text(g, v, record_a(), PB, TEXT_CFG, view_ids(v))


@pytest.mark.parametrize("marker", ["same day", "same-day", "that day", "on the day", "Same Day"])
def test_check_6_a_same_day_point_needs_one_of_four_markers(marker):
    assert 6 not in names(say(f"Short sleep the night before has tended to move together with higher glucose peaks after dinner, {marker}.", ["f3"]))


def test_check_6_a_same_day_point_without_a_marker_fails_and_the_message_lists_the_markers():
    fs = say("Short sleep the night before has tended to move together with higher glucose peaks after dinner.", ["f3"])
    assert 6 in names(fs) and any("same day" in f["detail"] and "that day" in f["detail"] and "on the day" in f["detail"] for f in fs if f["check"] == 6)


def test_check_6_a_marker_is_not_needed_for_a_point_that_is_not_a_same_day_one():
    v = view_a()
    assert 6 not in names(say("Short sleep the night before has tended to move together with higher glucose peaks after dinner.", ["f3"], v))


def test_the_prompt_states_the_four_same_day_markers():
    p = textlayer.SYSTEM_PROMPT
    assert 'the sentence must contain "same day", "same-day", "that day" or "on the day"' in p


# ---- 2. identical things are merged in the view -------------------------------------------------------------------------------------------------------------------
THINGS = [{"id": "f1", "wording": "present_only", "name": "short sleep the night before", "position": "among the very lowest she has had"},
          {"id": "f2", "wording": "present_only", "name": "low fluid intake the day before"},
          {"id": "f3", "wording": "present_only", "name": "short sleep the night before", "position": "among the very lowest she has had"},
          {"id": "f4", "wording": "present_only", "name": "short sleep the night before"},                      # no position: a different thing
          {"id": "f5", "wording": "present_only", "name": "short sleep the night before", "position": "among the very lowest she has had"},
          {"id": "f6", "wording": "asserted", "name": "short sleep the night before", "outcome": "higher glucose", "position": "among the very lowest she has had"}]


def test_things_with_identical_content_merge_into_the_first_one_carrying_every_id():
    things, primary = merge_things(copy.deepcopy(THINGS))
    assert [t["id"] for t in things] == ["f1", "f2", "f4", "f6"]
    assert things[0]["ids"] == ["f1", "f3", "f5"] and "ids" not in things[1] and "ids" not in things[2]
    assert primary == {"f1": "f1", "f3": "f1", "f5": "f1", "f2": "f2", "f4": "f4", "f6": "f6"}
    assert list(things[0])[:2] == ["id", "ids"]


def test_merging_changes_nothing_when_there_is_nothing_to_merge():
    one = copy.deepcopy(THINGS[:2])
    assert merge_things(copy.deepcopy(one)) == (one, {"f1": "f1", "f2": "f2"})


def test_every_member_id_is_a_valid_ref_and_resolves_to_its_thing():
    v = view_a()
    v["things"] = merge_things(copy.deepcopy(THINGS))[0]
    v["sets"], v["diary"] = [], []
    ids = view_ids(v)
    assert {"f1", "f3", "f5", "f2", "f4", "f6"} <= ids
    idx = thing_index(v)
    assert idx["f5"] is idx["f1"] and idx["f2"]["name"] == "low fluid intake the day before"


def test_a_ref_to_a_merged_member_passes_check_2_and_is_judged_as_the_thing():
    v = view_a()
    v["things"] = merge_things(copy.deepcopy(THINGS))[0]
    v["sets"] = []
    g = good()
    g["sentences"] = [{"text": "Short sleep the night before was present.", "refs": ["f5"]}, {"text": "Short sleep the night before may be linked to higher glucose.", "refs": ["f3"]}]
    fs = check_text(g, v, record_a(), PB, TEXT_CFG, view_ids(v))
    assert 2 not in names(fs) and 6 in names(fs)                  # f3 stands for the present-only thing: "may be linked to" is stronger than its wording


def test_build_view_maps_sets_backs_and_p_items_to_the_merged_thing():
    from v0_code.findings_engine.view import build_view
    rec = record_a()
    base = view_a()
    for f in rec["factors"]:
        pass
    # a record with a second present-only factor that has the same name as f4
    dup = copy.deepcopy([f for f in rec["factors"] if f["factor_id"] == "f4"][0])
    dup["factor_id"] = "f8"
    dup["relationship_key"] = "strained_period@same_day->hr_day_mean" if False else dup["relationship_key"]
    rec2 = {**rec, "factors": rec["factors"] + [dup]}
    from test_findings_text import BANDS, DIARY, HANDOFFS, IST, MEMORY
    v = build_view(rec2, HANDOFFS, DIARY, MEMORY, PB, IST, BANDS, [{"id": "p1", "about": ["f4", "f8"], "state": "early", "text": "x", "seen_before": "none"}])
    four = next(t for t in v["things"] if t["id"] == "f4")
    assert four["ids"] == ["f4", "f8"] and [t["id"] for t in v["things"] if t["id"] in ("f4", "f8")] == ["f4"]
    assert v["earlier_conclusions"][0]["about"] == ["f4"]
    assert [t["id"] for t in base["things"]] == ["f1", "f2", "f3", "f4"]                      # a view without duplicates is unchanged
    assert rec2["factors"][-1]["factor_id"] == "f8" and len(rec2["factors"]) == len(rec["factors"]) + 1          # the record is not touched


def test_the_prompt_says_how_to_cite_a_merged_thing():
    assert 'A thing that lists several "ids" stands for all of them: cite its "id".' in textlayer.SYSTEM_PROMPT


# ---- 3. check 15: an earlier conclusion is cited together with what it is about -------------------------------------------------------------------------------------
P_ITEM = [{"id": "p1", "about": ["f2"], "state": "early", "text": "An early observation of missed doses and higher dinner peaks.", "seen_before": "this_week"}]


def with_p(sentences):
    g = good()
    g["sentences"] = sentences
    v = view_a(pi=copy.deepcopy(P_ITEM))
    return check_text(g, v, record_a(), PB, TEXT_CFG, view_ids(v))


def test_check_15_a_sentence_that_cites_an_earlier_conclusion_must_cite_what_it_is_about():
    ok = with_p([{"text": "Missed doses on the same day or the day before have tended to move together with higher glucose peaks after dinner, same day, and this has come up before.", "refs": ["f2", "p1"]},
                 {"text": "Her glucose was clearly above her usual.", "refs": ["m1"]}])
    assert 15 not in names(ok)
    alone = with_p([{"text": "This has come up before.", "refs": ["p1"]}, {"text": "Her glucose was clearly above her usual.", "refs": ["m1"]}])
    assert 15 in names(alone) and any("stand alone" in f["detail"] or "about" in f["detail"] for f in alone if f["check"] == 15)
    other = with_p([{"text": "Short sleep the night before was present and this has come up before.", "refs": ["f3", "p1"]}, {"text": "Her glucose was clearly above her usual.", "refs": ["m1"]}])
    assert 15 in names(other)


def test_check_15_a_cited_set_counts_as_citing_its_members_and_a_merged_member_as_its_thing():
    v = view_a(pi=[{"id": "p1", "about": ["f2", "f3"], "state": "repeated", "text": "x", "seen_before": "none"}])
    g = good()
    g["sentences"] = [{"text": "Missed doses and short sleep have tended to move together with higher glucose peaks after dinner, same day, and this has come up before.", "refs": ["g1", "p1"]},
                      {"text": "Her glucose was clearly above her usual.", "refs": ["m1"]}]
    assert 15 not in names(check_text(g, v, record_a(), PB, TEXT_CFG, view_ids(v)))


def test_the_prompt_ties_an_earlier_conclusion_to_its_thing():
    p = textlayer.SYSTEM_PROMPT
    assert "only in the same sentence as the thing it is about" in p and "must also cite the thing(s) that item is about" in p and "never stands alone in a sentence" in p


# ---- 4. cleanup punctuation and check 16 ------------------------------------------------------------------------------------------------------------------------------
def test_cleanup_finishes_every_sentence_that_lacks_a_final_mark_and_leaves_the_headline():
    obj = {"headline": "A headline without a mark", "sentences": [{"text": "No mark here", "refs": ["m1"]}, {"text": "Already done.", "refs": ["m1"]}, {"text": "A question?", "refs": ["m1"]},
                                                                   {"text": "Shouted!", "refs": ["m1"]}, {"text": "  trailing space ", "refs": ["m1"]}]}
    out, changes = textclean.clean(obj, view_a())
    assert [s["text"] for s in out["sentences"]] == ["No mark here.", "Already done.", "A question?", "Shouted!", "Trailing space."] and out["headline"] == "A headline without a mark"
    assert "punctuation_added" in changes and obj["sentences"][0]["text"] == "No mark here"                       # the raw is not changed


def test_cleanup_changes_nothing_when_every_sentence_is_finished():
    obj = {"headline": "H.", "sentences": [{"text": "One.", "refs": ["m1"]}]}
    assert textclean.clean(obj, view_a()) == (obj, [])


def test_check_16_a_sentence_may_not_cite_the_history_note_when_there_is_enough_history():
    g = good()
    g["sentences"][2] = {"text": "There is enough history here.", "refs": ["h1"]}
    assert 16 in names(run_checks(g))
    rec = record_a()
    rec["history_note"] = "not_enough_history_yet"
    assert 16 not in names(run_checks(g, view_a(rec), rec))
    rec["history_note"] = "enough_for_some"
    assert 16 not in names(run_checks(g, view_a(rec), rec))


def test_the_prompt_says_nothing_about_history_when_there_is_enough():
    assert 'If the history note says there is enough history, say nothing about history and do not cite "h1".' in textlayer.SYSTEM_PROMPT
