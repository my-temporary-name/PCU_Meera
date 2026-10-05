"""PI: the code text (pi_spec.md 8.5 and amendment 39) and the phrase-book load check for statuses (property 17)."""

import re
from pathlib import Path

import pytest

from v0_code.evidence_engine.library import load_library
from v0_code.intel_common.phrasebook import Phrasebook, PhrasebookError
from v0_code.pi_engine.codetext import code_text, same_day_only

ROOT = Path(__file__).resolve().parent.parent
LIB = load_library(ROOT / "config/evidence_library_v0.yaml")
PB = Phrasebook.load(ROOT / "config/findings_phrasebook_v0.yaml")
SLEEP = "sleep_hours@prev_night->post_meal_peak:dinner"
MISSED = "missed_dose@2d->post_meal_peak:dinner"
SLEEP_DAY = "sleep_hours@prev_night->hr_day_mean"


def text(key, status, same=None):
    return code_text(key, status, same_day_only(LIB, key) if same is None else same, PB)


def test_same_day_only_comes_from_the_librarys_ordering():
    assert same_day_only(LIB, MISSED) is True and same_day_only(LIB, SLEEP) is False and same_day_only(LIB, SLEEP_DAY) is True


def test_a_supported_text_says_repeatedly_and_the_candidate_says_early_observation():
    assert text(SLEEP, "supported") == {"sentences": ["Short sleep the night before has repeatedly moved together with higher glucose peaks after dinner in her history."], "source": "code_text"}
    assert text(SLEEP, "candidate")["sentences"] == ["Short sleep the night before may be linked to higher glucose peaks after dinner in her history. This is an early observation."]


def test_agreement_follows_the_phrase_books_number():
    assert text(MISSED, "supported")["sentences"][0].startswith("Missed doses on the same day or the day before have repeatedly moved together with")


def test_same_day_only_memories_say_same_day_and_never_repeat_it():
    assert text(MISSED, "supported")["sentences"][0].count("same day") == 1                          # the exposure phrase already says it
    assert text(SLEEP_DAY, "supported")["sentences"][0].endswith("in her history, on the same day.")
    assert "same day" in text(SLEEP, "supported", same=True)["sentences"][0] and "same day" not in text(SLEEP, "supported", same=False)["sentences"][0]


def test_weakened_and_retracted_texts():
    assert text(SLEEP, "weakened")["sentences"] == ["Short sleep the night before and higher glucose peaks after dinner are no longer clearly seen together in her history."]
    assert text(SLEEP, "retracted")["sentences"] == ["This link, once suspected, is no longer supported by her history."]
    assert "same day" in text(SLEEP_DAY, "weakened")["sentences"][0]


@pytest.mark.parametrize("status", ["candidate", "supported", "weakened", "retracted"])
def test_no_text_has_a_digit_or_a_causal_word(status):
    for key in (SLEEP, MISSED, SLEEP_DAY):
        t = " ".join(text(key, status)["sentences"])
        assert not re.search(r"\d", t) and not re.search(r"caus|trigger|led to|because|explain|affect|impact|influenc|contribut", t.lower())


def test_the_phrase_book_needs_a_text_rule_for_every_status():
    raw = {**PB.raw, "pi_text": {k: v for k, v in PB.raw["pi_text"].items() if k != "weakened"}}
    with pytest.raises(PhrasebookError) as e:
        Phrasebook(raw).check(LIB)
    assert "weakened" in str(e.value)
    assert set(PB.raw["pi_text"]) == {"candidate", "supported", "weakened", "retracted"}


def test_every_runnable_relationship_of_the_library_has_a_code_text_for_every_status():
    for p in LIB.runnable():
        key = p["key"].replace("{meal_kind}", "dinner")
        for status in ("candidate", "supported", "weakened", "retracted"):
            assert text(key, status)["sentences"]
