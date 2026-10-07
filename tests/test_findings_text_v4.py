"""Findings text layer, stage L2: prompt p-v4 and checks ck-v6 (the loop's accepted changes): no time words offered, the history note wins over the per-thing history sentence, the
checks that exist are stated in the prompt, earlier conclusions never supply claim wording, and "moved together" counts as a claim in checks 6, 12 and 14."""

import re

import pytest

from test_findings_text import PB, good, names, run_checks
from v0_code.findings_engine import textcheck, textlayer


def test_versions_and_compatible_prompts():
    assert textlayer.PROMPT_VERSION.startswith("p-v") and textcheck.CHECKS_VERSION.startswith("ck-v")
    assert "p-v4" in textlayer.COMPATIBLE_PROMPTS["p-v5"]


def test_rule_1_no_longer_offers_recently_or_earlier_and_the_retry_says_wording():
    p = textlayer.SYSTEM_PROMPT
    rule1 = next(l for l in p.split("\n") if l.startswith("1. Write no digits"))
    assert 'Use "that day".' in rule1 and "recently" not in rule1 and "earlier" not in rule1
    assert "than the wording allows" in textlayer.RETRY_ADDENDUM and "class" not in textlayer.RETRY_ADDENDUM


def test_the_history_note_is_stated_once_and_wins_over_the_per_thing_sentence():
    p = textlayer.SYSTEM_PROMPT
    assert "Say nothing about history in these sentences" in p and "add that there is not enough history yet" not in p
    assert 'say so once, in one sentence that cites "h1" and claims no link; that one sentence covers every present_only_history thing' in p


def test_earlier_conclusions_never_supply_claim_wording():
    p = textlayer.SYSTEM_PROMPT
    assert "never supply claim wording" in p and "has repeatedly moved together with" in p and "only the thing's own wording" in p


@pytest.mark.parametrize("needle", ["Use no clinical term", "Do not write the same phrase of a thing twice in one sentence", "must be followed by the outcome given for that thing", "Write no word with an underscore"])
def test_the_checks_that_exist_are_stated_in_the_prompt(needle):
    assert needle in textlayer.SYSTEM_PROMPT


def test_the_prompt_has_no_internal_word_outside_its_list_and_no_diabetes():
    body, listing = textlayer.SYSTEM_PROMPT.split("Do not use the words:")
    low = body.lower() + "\n".join(listing.split("\n")[1:]).lower()
    for w in PB.raw["internal_words"]:
        assert w in listing.split("\n")[0] and not re.search(rf"\b{re.escape(w)}\b", low), w
    assert "diabetes" not in textlayer.SYSTEM_PROMPT.lower()


# ---- ck-v6: "moved together" is a claim ----------------------------------------------------------------------------------------------------------------------------
def with_sentence(text, refs):
    g = good()
    g["sentences"][1] = {"text": text, "refs": refs}
    return g


@pytest.mark.parametrize("claim", ["has repeatedly moved together with", "has moved together with", "have repeatedly moved together with", "moved together with"])
def test_check_6_a_moved_together_claim_needs_an_asserted_thing(claim):
    on_present_only = with_sentence(f"A stressed or low-mood period on the same day {claim} higher glucose peaks after dinner.", ["f4"])
    assert 6 in names(run_checks(on_present_only)), claim
    on_nothing = with_sentence(f"Short sleep the night before {claim} higher glucose peaks after dinner.", ["n1"])
    assert 6 in names(run_checks(on_nothing)), claim
    on_asserted = with_sentence(f"Short sleep the night before {claim} higher glucose peaks after dinner.", ["f3"])
    assert 6 not in names(run_checks(on_asserted)), claim


def test_check_6_a_moved_together_claim_is_judged_like_tended_to_move_together_for_a_hedged_thing():
    from test_findings_text import view_a
    view = view_a()
    view["things"][2]["wording"] = "hedged"
    g = with_sentence("Short sleep the night before has repeatedly moved together with higher glucose peaks after dinner.", ["f3"])
    assert 6 in names(textcheck.check_text(g, view, __import__("test_findings_text").record_a(), PB, __import__("test_findings_text").TEXT_CFG, __import__("v0_code.findings_engine.view", fromlist=["view_ids"]).view_ids(view)))


@pytest.mark.parametrize("text", ["Short sleep the night before has repeatedly moved together with missed doses on the same day or the day before.",
                                  "Short sleep the night before has moved together with each other.",
                                  "Missed doses on the same day or the day before have moved together with short sleep the night before."])
def test_check_12_the_object_of_a_moved_together_claim_must_be_an_outcome(text):
    assert 12 in names(run_checks(with_sentence(text, ["g1", "f2", "f3"]))), text


@pytest.mark.parametrize("text", ["Short sleep the night before has repeatedly moved together with, same day, and nothing else.", "Short sleep the night before has moved together with and missed doses.",
                                  "Short sleep the night before has repeatedly moved together."])
def test_check_14_a_moved_together_claim_must_be_followed_by_an_outcome(text):
    assert 14 in names(run_checks(with_sentence(text, ["f3"]))), text


def test_the_old_claim_wording_is_judged_as_before():
    g = with_sentence("Short sleep the night before has tended to move together with higher glucose peaks after dinner.", ["f3"])
    assert names(run_checks(g)) == []
