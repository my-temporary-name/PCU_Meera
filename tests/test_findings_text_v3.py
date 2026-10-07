"""Text layer, closing round (prompt p-v3, checks ck-v5): clinical terms only if the view has them, an exposure is never the object of a claim, no repeated phrase in a sentence,
and the new internal words."""

import json
import re

import pytest

import test_findings_factors as ff
from test_findings_text import BANDS, DIARY, HANDOFFS, IST, MEMORY, PB, TEXT_CFG, good, names, record_a, run_checks, view_a
from v0_code.findings_engine import textcheck, textclean, textlayer
from v0_code.findings_engine.textcheck import check_text
from v0_code.findings_engine.view import banned_words_in_view, build_view, view_ids


# ---- versions and the prompt -----------------------------------------------------------------------------------------------------------------------------------
def test_versions_vocabulary_and_the_first_line_of_the_prompt():
    assert textlayer.PROMPT_VERSION == "p-v5" and textcheck.CHECKS_VERSION == "ck-v7"           # (the L2 versions; see test_findings_text_v4)
    assert textlayer.COMPATIBLE_PROMPTS == {"p-v5": ("p-v4", "p-v3", "p-v2", "p-v1")}
    p = textlayer.SYSTEM_PROMPT
    assert p.startswith("You write a short plain-language account of one situation in a person's health record.\n") and "diabetes" not in p.lower()
    assert "things that were present" in p and "sets of things" in p and "often_together" in p
    for w in ("entangled", "bundle", "pair", "points"):
        assert w in PB.raw["internal_words"]
        body, listing = p.split("Do not use the words:")
        assert w in listing.split("\n")[0] and not re.search(rf"\b{w}\w*", body.lower()), w


def test_the_view_uses_no_internal_word_in_a_key_or_a_value():
    banned = {w.lower() for w in PB.raw["internal_words"]}
    ov = [{"a": "sleep_hours@prev_night", "b": "missed_dose@2d", "a_view": "x", "b_view": "y", "share_given_a": 0.9, "share_overall": 0.3, "ratio": 3.0, "flag": True}]
    c = ff.content([ff.item("h1", "2026-09-17T10:00:00+05:30", [ff.F(2, "sleep", "sleep_hours@prev_night->hr_day_mean", "supported", [], "exposed", tail=1.0),
                                                              ff.F(3, "missed", "missed_dose@2d->hr_day_mean", "supported", ["same_day_unverified"], "exposed")], overlap=ov, measure="heart_rate")])
    rec = {"finding_id": "x", "as_of": "2026-09-17T10:00:00+05:30", "local_date": "2026-09-17", **c}
    v = build_view(rec, [], [], [], PB, IST, BANDS)
    assert v["sets"] == [{"id": "g1", "reason": "often_together", "members": ["f1", "f2"]}] and banned_words_in_view(v, banned) == []
    assert banned_words_in_view(view_a(), banned) == [] and view_a()["sets"][0]["reason"] == "present_together"


@pytest.mark.parametrize("word,text", [("entangled", "These are entangled."), ("bundle", "The bundle was present."), ("bundles", "Two bundles."), ("pair", "A pair of items."), ("pairs", "Some pairs."),
                                      ("points", "The points were present.")])
def test_the_new_internal_words_fail_check_5(word, text):
    g = good()
    g["sentences"][0]["text"] = text
    assert 5 in names(run_checks(g)), word


# ---- check 11: clinical terms ------------------------------------------------------------------------------------------------------------------------------------
def test_the_clinical_term_list_is_phrase_book_config():
    terms = PB.raw["clinical_terms"]
    assert {"insulin", "hypoglycemia", "hypoglycaemia", "hyperglycemia", "hyperglycaemia", "infection", "diagnosis", "diagnosed"} <= set(terms)


@pytest.mark.parametrize("term", ["insulin", "hypoglycemia", "hypoglycaemia", "hyperglycemia", "hyperglycaemia", "infection", "diagnosis", "diagnosed"])
def test_check_11_a_clinical_term_must_be_in_the_view(term):
    g = good()
    g["sentences"][0]["text"] = f"There was some {term} noted."
    fs = run_checks(g)
    assert 11 in names(fs) and any(term in f["detail"] for f in fs if f["check"] == 11)
    h = good()
    h["headline"] = f"{term.capitalize()} was noted."
    assert 11 in names(run_checks(h))


def test_check_11_passes_when_the_view_has_the_term_and_ignores_other_words():
    diary = [{**DIARY[0], "description": "Took the usual insulin before dinner"}]
    view = view_a(diary=diary)
    g = good()
    g["sentences"][0] = {"text": "The diary mentions insulin before dinner.", "refs": ["d1"]}
    assert check_text(g, view, record_a(), PB, TEXT_CFG, view_ids(view)) == []
    ok = good()
    ok["sentences"][0]["text"] = "Her glucose was clearly above her usual."
    assert 11 not in names(run_checks(ok))
    g2 = good()
    g2["sentences"][0]["text"] = "The infections were not mentioned."                          # a plural of a listed term counts
    assert 11 in names(run_checks(g2))


# ---- check 12: an exposure is never the object of a claim -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "Missed doses on the same day or the day before has tended to move together with short sleep the night before.",
    "Short sleep the night before may be linked to missed doses on the same day or the day before.",
    "Short sleep has tended to move together with short sleep the night.",                         # a shortened exposure phrase (its first words) is still an exposure
    "Short sleep the night before has tended to move together with 'missed doses on the same day or the day before'."])
def test_check_12_the_object_of_a_claim_is_an_outcome_not_another_thing(text):
    g = good()
    g["sentences"][1] = {"text": text, "refs": ["g1", "f2", "f3"]}
    assert 12 in names(run_checks(g)), text
    h = good()
    h["headline"] = "Short sleep may be linked to missed doses on the same day or the day before."
    assert 12 in names(run_checks(h))


def test_check_12_lets_outcomes_and_unrelated_wording_through():
    g = good()
    g["sentences"][1] = {"text": "Missed doses on the same day and short sleep the night before have tended to move together with higher glucose peaks after dinner, and both were present.", "refs": ["g1"]}
    assert run_checks(g) == []
    g["sentences"][1] = {"text": "Short sleep the night before may be linked to a higher resting heart rate, and missed doses on the same day were present too.", "refs": ["f3", "f2"]}
    assert 12 not in names(run_checks(g))


# ---- check 13: no phrase twice in a sentence -----------------------------------------------------------------------------------------------------------------------
def test_check_13_a_view_phrase_may_not_appear_twice_in_one_sentence():
    g = good()
    g["sentences"][1] = {"text": "Short sleep the night before, missed doses on the same day or the day before and short sleep the night before were present.", "refs": ["g1"]}
    fs = run_checks(g)
    assert 13 in names(fs) and any("short sleep the night before" in f["detail"] for f in fs if f["check"] == 13)
    ok = good()
    ok["sentences"][1] = {"text": "Short sleep the night before was present. Missed doses on the same day or the day before were present too.", "refs": ["f2", "f3"]}
    assert 13 not in names(run_checks(ok))
    two = good()
    two["sentences"][0] = {"text": "The size of this meal's rise was among the very highest she has had, and the size of this meal's rise was unusual.", "refs": ["f1"]}
    assert 13 in names(run_checks(two))
    head = good()
    head["headline"] = "Short sleep the night before and short sleep the night before."
    assert 13 in names(run_checks(head))


def test_check_13_counts_a_phrase_inside_a_longer_phrase_once():
    view = view_a()
    view["things"].append({"id": "f9", "wording": "present_only", "name": "short sleep"})        # a shorter phrase that sits inside a longer one
    g = good()
    g["sentences"][1] = {"text": "Short sleep the night before was present.", "refs": ["f3"]}
    assert 13 not in names(check_text(g, view, record_a(), PB, TEXT_CFG, view_ids(view)))


# ---- which versions go back to the model ---------------------------------------------------------------------------------------------------------------------------
def test_the_clinical_terms_scan_helper_finds_terms_not_in_the_view():
    from v0_code.findings_engine import report_text
    row = {"finding_id": "x", "result": {"text_source": "llm", "text": {"headline": "Insulin dosing was noted.", "sentences": [{"text": "Fine.", "refs": ["m1"]}]}}, "view": view_a()}
    assert [h[1] for h in report_text.clinical_term_hits([row], PB)] == ["insulin"]
    row["view"] = view_a(diary=[{**DIARY[0], "description": "insulin before dinner"}])
    assert report_text.clinical_term_hits([row], PB) == []


@pytest.mark.parametrize("text", ["Short sleep the night before and missed doses on the same day may be linked to each other.",
                                  "Short sleep the night before has tended to move together with one another.",
                                  "Short sleep the night before and missed doses on the same day have tended to move together with each other, same day."])
def test_check_12_a_claim_whose_object_is_each_other_is_a_link_between_exposures(text):
    g = good()
    g["sentences"][1] = {"text": text, "refs": ["g1"]}
    assert 12 in names(run_checks(g)), text


def test_the_checks_version_changed_with_check_12():
    assert textcheck.CHECKS_VERSION.startswith("ck-v")


# ---- F2 final touches: check 14, underscore tokens, position phrases in check 13 ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "Short sleep the night before has tended to move together with, same day, and their separate roles cannot be told apart.",
    "Short sleep the night before has tended to move together with same day higher glucose peaks after dinner.",
    "Short sleep the night before may be linked to, and missed doses were present.",
    "Short sleep the night before has tended to move together with and missed doses.",
    "Short sleep the night before may be linked to."])
def test_check_14_a_claim_phrase_must_be_followed_by_an_outcome(text):
    g = good()
    g["sentences"][1] = {"text": text, "refs": ["g1", "f2", "f3"]}
    fs = run_checks(g)
    assert 14 in names(fs) and any("outcome" in f["detail"] for f in fs if f["check"] == 14), text


def test_check_14_lets_a_claim_with_an_outcome_through():
    g = good()
    g["sentences"][1] = {"text": "Short sleep the night before and missed doses on the same day have tended to move together with higher glucose peaks after dinner, same day.", "refs": ["g1"]}
    assert 14 not in names(run_checks(g))
    g["headline"] = "Short sleep may be linked to, and nothing else."
    assert 14 in names(run_checks(g))


@pytest.mark.parametrize("text", ["These present_together items were present.", "The wording was present_only here.", "A thing_called_this appeared."])
def test_a_token_with_an_underscore_is_a_check_failure(text):
    g = good()
    g["sentences"][0]["text"] = text
    fs = run_checks(g)
    assert any("underscore" in f["detail"] for f in fs), text


def test_position_phrases_are_exempt_from_check_13():
    view = view_a()
    view["things"] += [{"id": "f8", "wording": "present_only", "name": "low fluid intake the day before", "position": "among the very lowest she has had"},
                       {"id": "f9", "wording": "present_only", "name": "low activity the day before", "position": "among the very lowest she has had"}]
    view["things"][2]["position"] = "among the very lowest she has had"
    g = good()
    g["sentences"][1] = {"text": "Low fluid intake the day before, among the very lowest she has had, and low activity the day before, among the very lowest she has had, were present.", "refs": ["f8", "f9"]}
    assert 13 not in names(check_text(g, view, record_a(), PB, TEXT_CFG, view_ids(view)))
    g["sentences"][1] = {"text": "Low fluid intake the day before and low fluid intake the day before were present.", "refs": ["f8"]}
    assert 13 in names(check_text(g, view, record_a(), PB, TEXT_CFG, view_ids(view)))                  # other phrases still count


def test_the_checks_and_prompt_versions_are_the_l2_ones():
    assert textcheck.CHECKS_VERSION == "ck-v7" and textlayer.PROMPT_VERSION == "p-v5"
