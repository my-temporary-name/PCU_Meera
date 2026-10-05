"""Stage C: the gist (spec section 7). Tests for the gist view (no numbers), the four output checks, the prompts and the run logic.
Offline only: no test here calls a model."""

import json
import re

import pytest

from v0_code.baseline_v2.gist_check import (CHECKS, check_gist, check_structure, parse_batch, parse_json)
from v0_code.baseline_v2.gist_view import build_gist_view, diary_texts, freq_word


def T(measure, label, direction, size, count_like=False):
    return {"measure": measure, "label": label, "direction": direction, "size": size, "count_like": count_like, "delta": 1.0, "unit": "", "domain": measure}


TAGS = [T("cgm_glucose_reading", "glucose", "up", "moderate"), T("variability", "variability", "down", "small"), T("sleep_duration", "sleep", "down", "large"),
        T("resting_heart_rate", "resting heart rate", "up", "large"), T("continuous_heart_rate", "heart rate", "up", "small"), T("step_count", "steps", "flat", "none"),
        T("medication_adherence", "medication adherence", "down", "moderate"), T("mood_state", "strained periods of the day", "up", "moderate", True),
        T("hydration", "hydration", "not_enough_data", "none"), T("post_meal_peak", "post-meal glucose peak", "up", "small"), T("sedentary_time", "sedentary time", "up", "small")]


def fails(cfg, headline, sentences, diary=()):
    return check_gist(cfg, {"headline": headline, "sentences": sentences}, TAGS, list(diary))


def kinds(f):
    return sorted({x["check"] for x in f})


OK_S = ["Sleep fell markedly.", "Metformin was missed on a few days."]


# ---- frequency words -------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("k,n,unit,word", [(1, 1, "days", "on this day"), (1, 7, "days", "on one day"), (2, 7, "days", "on a few days"), (3, 7, "days", "on a few days"),
                                         (4, 7, "days", "on most days"), (7, 7, "days", "every day"), (1, 5, "readings", "on one reading"), (3, 5, "readings", "on most readings"),
                                         (5, 5, "readings", "every reading"), (2, 4, "days", "on a few days")])
def test_frequency_words(k, n, unit, word):
    assert freq_word(k, n, unit) == word


# ---- check 4: structure -----------------------------------------------------------------------------------------------------------------------

def test_structure_accepts_the_exact_shape_only():
    assert check_structure({"headline": "A short one.", "sentences": ["One.", "Two."]}) == []
    assert check_structure({"headline": "x " * 15, "sentences": ["One.", "Two."]}) == []
    for bad in ({"headline": "x " * 16, "sentences": ["One.", "Two."]}, {"headline": "H", "sentences": ["One."]}, {"headline": "H", "sentences": ["a", "b", "c", "d", "e"]},
                {"headline": "", "sentences": ["a", "b"]}, {"headline": "H", "sentences": "One. Two."}, {"headline": "H", "sentences": ["a", ""]},
                {"headline": "H", "sentences": ["a", "b"], "extra": 1}, {"headline": "H"}, ["H"], {"headline": 3, "sentences": ["a", "b"]}):
        assert check_structure(bad), bad


def test_parse_json_is_strict_about_extra_text():
    obj, f = parse_json('{"headline": "H", "sentences": ["a", "b"]}')
    assert obj and not f
    for raw in ("Here you go: {\"headline\": \"H\", \"sentences\": [\"a\", \"b\"]}", "not json", "", "```json\n{\"headline\": \"H\", \"sentences\": [\"a\", \"b\"]}\n```"):
        obj, f = parse_json(raw)
        assert obj is None and f[0]["check"] == "structure"


def test_parse_batch_matches_keys_and_a_missing_key_is_that_windows_failure():
    raw = json.dumps({"1": {"headline": "H", "sentences": ["a", "b"]}, "3": {"headline": "H", "sentences": ["a"]}})
    out = parse_batch(raw, ["1", "2", "3"])
    assert out["1"][1] == [] and out["2"][0] is None and out["2"][1][0]["check"] == "structure" and out["3"][1][0]["check"] == "structure"
    assert all(v[1][0]["check"] == "structure" for v in parse_batch("garbage", ["1", "2"]).values())


# ---- check 2: causal language -----------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text", ["Sleep fell because of stress.", "It was caused by the week.", "Stress triggered it.", "Glucose rose, which led to worry.", "The week resulted in change.",
                                  "Sleep fell due to stress.", "That explains the rise.", "Rise is attributable to it.", "Glucose was driven by sleep.",
                                  "She was responsible.", "Thanks to the hospital stay, sleep fell.", "A cause of worry."])
def test_causal_language_is_rejected(v2_cfg, text):
    assert "causal" in kinds(fails(v2_cfg, "H", [text, "Sleep fell markedly."]))


def test_co_occurrence_wording_is_fine(v2_cfg):
    assert fails(v2_cfg, "A hard week.", ["Glucose rose clearly while sleep fell sharply.", "Sleep fell alongside a hospital stay."]) == []


# ---- check 3: digits, dates, months, quotes, copied diary text, internal words ----------------------------------------------------------------------

@pytest.mark.parametrize("text,why", [("Sleep fell on 3 days.", "digit"), ("Sleep fell in 2025.", "digit"), ("In November sleep fell.", "month"), ("Sleep fell in december.", "month"),
                                    ('She wrote "tired" often.', "quote"), ("She wrote “tired” often.", "quote"), ("The anchor moved.", "internal"), ("A tag was set.", "internal"),
                                    ("Each stream moved.", "internal"), ("The record shows it.", "internal"), ("The window was short.", "internal"), ("Notable change.", "internal"),
                                    ("The direction table says so.", "internal"), ("A flag was raised.", "internal"), ("A field changed.", "internal"), ("The tier is week.", "internal")])
def test_forbidden_content(v2_cfg, text, why):
    assert "forbidden_content" in kinds(fails(v2_cfg, "H", [text, "Sleep fell markedly."])), why


def test_may_and_march_are_months_only_when_capitalised_mid_sentence(v2_cfg):
    assert "forbidden_content" not in kinds(fails(v2_cfg, "H", ["May be the start of rest.", "She may rest."]))
    assert "forbidden_content" in kinds(fails(v2_cfg, "H", ["It began in May.", "Sleep fell markedly."]))


def test_five_words_copied_from_a_diary_entry_are_rejected_but_four_are_fine(v2_cfg):
    diary = ["Father hospitalized overnight - chest pain and weakness"]
    assert "forbidden_content" in kinds(fails(v2_cfg, "H", ["Her father hospitalized overnight with chest pain was in the news.", "Her father hospitalized overnight, chest pain and weakness followed."], diary))
    assert "forbidden_content" in kinds(fails(v2_cfg, "H", ["Overnight chest pain and weakness appeared.", "Sleep fell markedly."], diary))
    assert "forbidden_content" not in kinds(fails(v2_cfg, "H", ["Chest pain appeared, and weakness.", "Sleep fell markedly."], diary))


# ---- check 1: direction and size agree with the tags (clause-level binding, compound terms) ----------------------------------------------------------

def test_matching_direction_and_size_pass(v2_cfg):
    assert fails(v2_cfg, "H", ["Glucose rose clearly while sleep fell markedly and resting heart rate rose sharply.", "Medication adherence fell noticeably."]) == []


def test_wrong_direction_fails(v2_cfg):
    f = fails(v2_cfg, "H", ["Sleep rose sharply.", "Glucose fell clearly."])
    assert kinds(f) == ["direction_size"] and len(f) == 2


def test_wrong_size_word_fails_and_missing_size_word_is_fine(v2_cfg):
    assert kinds(fails(v2_cfg, "H", ["Sleep fell slightly.", "Glucose rose clearly."])) == ["direction_size"]          # sleep is large
    assert kinds(fails(v2_cfg, "H", ["Glucose rose sharply.", "Sleep fell markedly."])) == ["direction_size"]           # glucose is moderate
    assert fails(v2_cfg, "H", ["Sleep fell.", "Glucose rose."]) == []
    assert kinds(fails(v2_cfg, "H", ["Sleep fell much.", "Glucose rose a little."])) == ["direction_size"]                 # "much" suits sleep (large); "a little" does not suit glucose (moderate)


def test_a_direction_word_binds_to_the_nearest_preceding_measure_in_its_clause(v2_cfg):
    assert fails(v2_cfg, "H", ["Glucose rose clearly, while sleep fell markedly.", "Resting heart rate rose sharply and medication adherence fell noticeably."]) == []
    # a later measure takes over: "fell" belongs to sleep, so the claim about glucose is the "rose"
    assert kinds(fails(v2_cfg, "H", ["Glucose rose clearly while sleep rose markedly.", "Resting heart rate rose sharply."])) == ["direction_size"]


def test_glucose_and_sleep_fell_binds_fell_to_sleep_only(v2_cfg):
    # "Glucose and sleep fell": split at "and" -> clause 1 "Glucose" (no direction word, binds to nothing), clause 2 "sleep fell" (correct). Passes.
    assert fails(v2_cfg, "H", ["Glucose and sleep fell markedly.", "Resting heart rate rose sharply."]) == []


def test_a_direction_word_with_no_measure_in_its_clause_binds_to_nothing(v2_cfg):
    assert fails(v2_cfg, "H", ["Sleep fell markedly, while higher overall.", "Glucose rose clearly."]) == []
    assert fails(v2_cfg, "H", ["Slightly higher blood pressure was seen.", "Sleep fell markedly."]) == []        # forward modifier: nothing precedes it in its clause
    assert fails(v2_cfg, "H", ["More activity was seen.", "Sleep fell markedly."]) == []
    assert fails(v2_cfg, "H", ["More stress was noted.", "Sleep fell markedly."]) == []


def test_compound_terms_are_matched_longest_phrase_first(v2_cfg):
    # glucose is UP, glucose variability is DOWN: "glucose variability fell" is correct and must not be read as glucose falling
    assert fails(v2_cfg, "H", ["Glucose variability fell a little.", "Sleep fell markedly."]) == []
    assert kinds(fails(v2_cfg, "H", ["Glucose variability rose a little.", "Sleep fell markedly."])) == ["direction_size"]
    assert fails(v2_cfg, "H", ["Average glucose rose clearly.", "Estimated glucose rose clearly."]) == []
    assert kinds(fails(v2_cfg, "H", ["Average glucose fell clearly.", "Sleep fell markedly."])) == ["direction_size"]
    assert fails(v2_cfg, "H", ["The post-meal glucose peak rose a little.", "Sleep fell markedly."]) == []
    assert kinds(fails(v2_cfg, "H", ["The post-meal glucose peak fell a little.", "Sleep fell markedly."])) == ["direction_size"]
    assert fails(v2_cfg, "H", ["Resting heart rate rose sharply.", "Heart rate rose a little."]) == []
    assert kinds(fails(v2_cfg, "H", ["Resting heart rate fell sharply.", "Sleep fell markedly."])) == ["direction_size"]


def test_a_count_of_periods_uses_more_or_fewer(v2_cfg):
    assert fails(v2_cfg, "H", ["More strained periods of the day clearly appeared.", "Sleep fell markedly."]) == []        # forward modifier: binds to nothing
    assert fails(v2_cfg, "H", ["Strained periods of the day rose noticeably.", "Sleep fell markedly."]) == []
    assert kinds(fails(v2_cfg, "H", ["Strained periods of the day fell noticeably.", "Sleep fell markedly."])) == ["direction_size"]


def test_a_claim_about_a_flat_or_not_enough_data_measure_fails(v2_cfg):
    assert kinds(fails(v2_cfg, "H", ["Steps rose a little.", "Sleep fell markedly."])) == ["direction_size"]           # flat
    assert kinds(fails(v2_cfg, "H", ["Hydration fell clearly.", "Sleep fell markedly."])) == ["direction_size"]        # not enough data
    assert fails(v2_cfg, "H", ["Steps stayed steady.", "Sleep fell markedly."]) == []                                  # no direction word: not a claim


def test_a_measure_with_no_tag_is_not_checked(v2_cfg):
    assert fails(v2_cfg, "H", ["Blood pressure was above the reference range on a few readings.", "Sleep fell markedly."]) == []


def test_the_headline_is_checked_too(v2_cfg):
    assert kinds(fails(v2_cfg, "Sleep rose sharply.", OK_S)) == ["direction_size"]


def test_every_check_has_a_name():
    assert set(CHECKS) == {"direction_size", "causal", "forbidden_content", "structure"}


# ---- the gist view ----------------------------------------------------------------------------------------------------------------------------

def _walk(x, path=()):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _walk(v, path + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _walk(v, path + (i,))
    else:
        yield path, x


@pytest.fixture()
def stored(v2_stored):
    return v2_stored[0]


def test_the_view_has_no_digits_or_dates_outside_diary_text_in_every_queued_window(stored):
    from v0_code.baseline_v2.config import Config
    cfg = Config.from_yaml("config/patient_meera_iyer_v1.yaml")
    n = 0
    for tier, rows in stored.items():
        for r in rows:
            if r["gist"]["status"] is not None:
                continue
            n += 1
            view = build_gist_view(cfg, r)
            for path, leaf in _walk(view):
                if isinstance(leaf, str) and path[:1] == ("diary",) and path[-1] in ("text", "severity"):
                    continue
                if isinstance(leaf, str) and path[:1] == ("top_items",) and leaf.startswith("diary entry"):          # diary text passes through as written
                    continue
                assert not re.search(r"\d", re.sub(r"HbA1c", "", str(leaf))), (r["window_id"], path, leaf)          # HbA1c is the one allowed digit token
    assert n > 500


def test_the_view_names_every_missed_medicine_every_diary_entry_and_never_a_steady_measure(stored, v2_cfg):
    for r in stored["week"][:60] + stored["day"][20:120]:
        if r["gist"]["status"] is not None:
            continue
        view = build_gist_view(v2_cfg, r)
        meds = {v2_cfg.medicine_name(i["medicine"]) for i in r["material_changes"] if i["kind"] == "missed_dose"}
        assert meds == {m["medicine"] for m in view.get("missed_medicines", [])}, r["window_id"]
        assert len(view.get("diary", [])) == sum(1 for i in r["material_changes"] if i["kind"] == "diary_event"), r["window_id"]
        shown = {m["measure"] for m in view.get("measures", [])}
        moved = {v2_cfg.measure_name(t["measure"]) for t in r["tags"] if t["direction"] in ("up", "down")}
        assert shown == moved, r["window_id"]
        assert set(diary_texts(r)) == {i["text"] for i in r["material_changes"] if i["kind"] == "diary_event"}


def test_the_view_has_a_places_entry_only_for_somewhere_other_than_her_usual_places(stored, v2_cfg):
    w = next(r for r in stored["week"] if r["window_id"] == "week_ENDING_2025-11-22")
    view = build_gist_view(v2_cfg, w, usual_places={"home", "home_wfh"})
    assert {"place": "hospital", "how_often": "on most days"} in view["places"] and not any(p["place"] in ("home", "home wfh") for p in view["places"])


def test_the_month_view_has_long_standing_patterns_a_lab_difference_and_counts_only_as_words(stored, v2_cfg):
    m = next(r for r in stored["month"] if r["window_id"] == "month_ENDING_2025-12-29")
    view = build_gist_view(v2_cfg, m)
    assert any(p["measure"] == "steps" for p in view["long_standing_patterns"])
    assert "differ" in view["lab_vs_glucose_estimate"]
    assert re.fullmatch(r"[a-z :,]+", view["other_diary_entries"]), view["other_diary_entries"]


def test_the_view_says_when_the_window_is_not_reliable_and_notes_removed_readings(stored, v2_cfg):
    early = next(r for r in stored["week"] if not r["reliable"])
    assert build_gist_view(v2_cfg, early)["reliable"] == "no"
    removed = next(r for r in stored["day"] if r["window_id"] == "day_2026-04-23")
    assert "one questionable glucose reading was removed" in build_gist_view(v2_cfg, removed)["data_notes"]


# ================================================================================================================================================
# Stage C review: plural/possessive matching, no ambiguous aliases, the lab line, headline finishing, dedupe, top_items, warning mode
# ================================================================================================================================================

from v0_code.baseline_v2.gist_check import finalize_headline, normalize_text


def test_text_is_normalised_to_singular_stems_without_possessives_or_hyphens():
    assert normalize_text("Post-meal glucose peaks rose") == "post meal glucose peak rose"
    assert normalize_text("Glucose's variability fell") == "glucose variability fell"
    assert normalize_text("Strained periods; stress; less; this; was") == "strained period; stress; less; this; was"
    assert normalize_text("The lab's long-term blood sugar tests") == "the lab long term blood sugar test"      # (normalisation is generic; the lab line itself now says HbA1c)


def test_plural_and_possessive_forms_match_the_longer_measure(v2_cfg):
    # post-meal glucose peak is up/small, glucose is up/moderate
    assert fails(v2_cfg, "H", ["Post-meal glucose peaks rose a little.", "Sleep fell markedly."]) == []
    f = fails(v2_cfg, "H", ["Post-meal glucose peaks rose sharply.", "Sleep fell markedly."])
    assert kinds(f) == ["direction_size"] and "post meal glucose peak" in f[0]["detail"]
    assert fails(v2_cfg, "H", ["Post-meal glucose peaks were slightly higher.", "Sleep fell markedly."]) == []
    assert fails(v2_cfg, "H", ["The post meal glucose peak rose a little.", "Sleep fell markedly."]) == []            # no hyphen
    # glucose is up, glucose variability is down: the possessive must not turn this into a claim about glucose
    assert fails(v2_cfg, "H", ["Glucose's variability fell a little.", "Sleep fell markedly."]) == []
    assert kinds(fails(v2_cfg, "H", ["Strained periods of the day rose noticeably.", "Resting heart rates fell sharply."])) == ["direction_size"]


def test_ambiguous_aliases_are_gone(v2_cfg):
    terms = v2_cfg.measure_terms()
    for t in ("blood sugar", "activity", "physical activity", "stress"):
        assert t not in terms
    assert terms["glucose variability"] == "variability" and terms["post-meal glucose peak"] == "post_meal_peak"


def test_the_lab_line_is_its_own_unchecked_measure(v2_cfg):
    # glucose is up/moderate here and the glucose-based estimate sits after "higher"; neither is a claim about a tag
    lab_down = [T("cgm_glucose_reading", "glucose", "down", "small")]
    for sentence in ("HbA1c is higher than the glucose-based estimate.", "The hba1c was higher than the glucose based estimate.",
                     "The glucose-based estimate is lower than HbA1c."):
        assert check_gist(v2_cfg, {"headline": "H", "sentences": [sentence, "Glucose fell a little."]}, lab_down, []) == [], sentence
    # but a real claim about glucose in the same text is still checked
    assert kinds(check_gist(v2_cfg, {"headline": "H", "sentences": ["Glucose rose a little.", "HbA1c is higher than the glucose-based estimate."]}, lab_down, [])) == ["direction_size"]


def test_headlines_are_finished_by_code():
    assert finalize_headline("a holiday visit with friends") == "A holiday visit with friends."
    assert finalize_headline("  Already done.  ") == "Already done."
    assert finalize_headline("A question?") == "A question?"
    assert finalize_headline("no stop!") == "No stop!"


def test_sentence_level_direction_failures_can_be_warnings_but_the_headline_stays_strict(v2_cfg):
    warns: list = []
    sentences_bad = {"headline": "Sleep fell markedly.", "sentences": ["Sleep rose sharply.", "Glucose rose clearly."]}
    assert check_gist(v2_cfg, sentences_bad, TAGS, [], sentence_mode="warn", warnings=warns) == [] and len(warns) == 1 and warns[0]["check"] == "direction_size"
    headline_bad = {"headline": "Sleep rose sharply.", "sentences": ["Sleep fell markedly.", "Glucose rose clearly."]}
    warns = []
    assert kinds(check_gist(v2_cfg, headline_bad, TAGS, [], sentence_mode="warn", warnings=warns)) == ["direction_size"] and warns == []
    assert kinds(check_gist(v2_cfg, sentences_bad, TAGS, [])) == ["direction_size"]                                  # strict is the default
    # the other checks are never softened
    assert "causal" in kinds(check_gist(v2_cfg, {"headline": "H", "sentences": ["Sleep fell because of stress.", "Glucose rose clearly."]}, TAGS, [], sentence_mode="warn", warnings=[]))


# ---- view: top_items and the month dedupe -------------------------------------------------------------------------------------------------------

def _row(tier="week", **kw):
    base = {"window_id": "w", "tier": tier, "reliable": True, "tags": [], "co_movement": {"glucose_direction": "flat", "same_direction": [], "opposite_direction": []}, "material_changes": [], "deltas_clean": {},
            "anchors_crossed": [], "anchors_questionable": [], "facts": {"n_days": 7, "aggregates": {"location_days": {}}, "lifestyle": {}, "chronic_findings": [], "deltas": {"clean": {}}}}
    base.update(kw)
    return base


SLEEP_TAG = T("sleep_duration", "sleep", "down", "large")
GLU_TAG = T("cgm_glucose_reading", "glucose", "up", "moderate")
M_ANCHOR = {"kind": "anchor_crossed", "anchor": "sleep_hours_change"}
M_DIARY_MILD = {"kind": "diary_event", "date": "2026-01-01", "category": "life_event", "text": "Small errand", "severity_note": "mild"}
M_DIARY_SEV = {"kind": "diary_event", "date": "2026-01-02", "category": "life_event", "text": "Father hospitalized overnight", "severity_note": "severe, family crisis"}
M_MISSED = {"kind": "missed_dose", "medicine": "med_1_metformin", "days": 2, "of": 7}
M_LARGE = {"kind": "large_change", "measure": "resting_heart_rate", "label": "resting heart rate", "direction": "up", "direction_word": "up", "size": "large"}
M_STATUS = {"kind": "status_worse_than_usual", "measure": "sleep_duration", "status": "low", "usual": "normal", "days": 3, "of": 7}


def test_top_items_come_first_and_are_at_most_three(v2_cfg):
    row = _row(tags=[SLEEP_TAG, GLU_TAG], anchors_crossed=["sleep_hours_change"], material_changes=[M_ANCHOR, M_MISSED, M_DIARY_MILD, M_DIARY_SEV, M_STATUS, M_LARGE])
    view = build_gist_view(v2_cfg, row)
    assert list(view)[0] == "top_items" and len(view["top_items"]) == 3
    d, m, c = view["top_items"]
    assert d.startswith("diary entry (severe, family crisis)") and "Father hospitalized overnight" in d           # the most severe entry stands for the diary theme; the mild one does not
    assert m.startswith("missed medicines") and "metformin on a few days" in m
    assert c.startswith("notable or large changes: sleep down (large)")


def test_top_items_skip_what_is_absent_and_a_mild_diary_entry_is_not_a_theme(v2_cfg):
    row = _row(tags=[SLEEP_TAG], material_changes=[M_DIARY_MILD, M_STATUS, M_LARGE])
    items = build_gist_view(v2_cfg, row)["top_items"]
    assert [i.split(":")[0] for i in items] == ["notable or large changes", "unusual statuses"]
    assert "top_items" not in build_gist_view(v2_cfg, _row(material_changes=[{"kind": "data_gap", "hours": 2.2}]))


def test_top_items_have_no_digits_outside_diary_text(stored, v2_cfg):
    n = 0
    for tier, rows in stored.items():
        for r in rows:
            if r["gist"]["status"] is not None:
                continue
            view = build_gist_view(v2_cfg, r)
            assert len(view.get("top_items", [])) <= 3
            for item in view.get("top_items", []):
                if not item.startswith("diary entry"):
                    assert not re.search(r"\d", item.replace("HbA1c", "")), (r["window_id"], item)
            n += 1
    assert n > 500


def test_a_month_drops_the_unusual_status_a_long_standing_pattern_already_covers(stored, v2_cfg):
    m = next(r for r in stored["month"] if r["window_id"] == "month_ENDING_2025-12-29")
    raw_unusual = {v2_cfg.measure_name(i["measure"]) for i in m["material_changes"] if i["kind"] == "status_worse_than_usual"}
    view = build_gist_view(v2_cfg, m)
    long_standing = {p["measure"] for p in view["long_standing_patterns"]}
    assert raw_unusual & long_standing                                                                     # the case exists in the real data (sleep)
    assert not ({u["measure"] for u in view.get("unusual_statuses", [])} & long_standing)
    w = next(r for r in stored["week"] if r["window_id"] == "week_ENDING_2025-11-22")                      # weeks are unchanged
    assert {u["measure"] for u in build_gist_view(v2_cfg, w)["unusual_statuses"]} == {v2_cfg.measure_name(i["measure"]) for i in w["material_changes"] if i["kind"] == "status_worse_than_usual"}


def test_the_lab_line_uses_the_configured_name(stored, v2_cfg):
    m = next(r for r in stored["month"] if r["window_id"] == "month_ENDING_2025-12-29")
    assert build_gist_view(v2_cfg, m)["lab_vs_glucose_estimate"] == "HbA1c is higher than the glucose-based estimate (they differ)"
