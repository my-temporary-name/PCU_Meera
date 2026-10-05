"""Baseline cleanup round: tentative wording, fallback code lines, three checker fixes, the affected-window selection and the read-only audit.
Offline only."""

import json
import shutil

import pytest

from v0_code.baseline_v2.gist_check import check_gist, normalize_text
from v0_code.baseline_v2.render import fallback_code_line
from v0_code.baseline_v2.storage import MemoryV2Store
from test_v2_gist import T, _row, GLU_TAG, SLEEP_TAG, M_ANCHOR, M_DIARY_MILD, M_DIARY_SEV, M_MISSED, M_LARGE, M_STATUS

TAGS = [T("cgm_glucose_reading", "average glucose", "up", "moderate"), T("sleep_duration", "sleep", "flat", "none"), T("post_meal_peak", "post-meal glucose peak", "up", "small"),
        T("resting_heart_rate", "resting heart rate", "up", "large")]


def kinds(f):
    return sorted({x["check"] for x in f})


def chk(cfg, headline, sentences, reliable=True, tags=TAGS):
    return check_gist(cfg, {"headline": headline, "sentences": sentences}, tags, [], reliable=reliable)


# ---- 1. tentative wording ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("word", ["tentative", "tentatively", "uncertain", "Tentative", "UNCERTAIN"])
def test_tentative_wording_is_rejected_for_a_reliable_window(v2_cfg, word):
    f = chk(v2_cfg, "H", [f"Comparisons are {word} this time.", "Nothing else."])
    assert kinds(f) == ["forbidden_content"] and word.lower() in f[0]["detail"].lower()


def test_tentative_wording_is_allowed_only_when_the_view_says_not_reliable(v2_cfg):
    s = ["Comparisons are tentative.", "Nothing else."]
    assert chk(v2_cfg, "H", s, reliable=False) == []
    assert kinds(chk(v2_cfg, "H", s, reliable=True)) == ["forbidden_content"]
    assert kinds(chk(v2_cfg, "H", s)) == ["forbidden_content"]                                       # reliable is the default


# ---- 2. fallback code lines -------------------------------------------------------------------------------------------------------------------

M_MISSED_ALL = [{"kind": "missed_dose", "medicine": m, "days": 4, "of": 30} for m in ("med_1_metformin", "med_2_amlodipine", "med_3_levothyroxine")]
M_SUMMARY = {"kind": "diary_summary", "count": 10, "by_category": {"life_event": 8, "habit": 1, "social_interaction": 1}}


def test_a_fallback_line_never_begins_with_the_other_diary_entries_count(v2_cfg):
    row = _row("month", tags=[SLEEP_TAG], material_changes=[M_SUMMARY, *M_MISSED_ALL, M_STATUS])
    line = fallback_code_line(v2_cfg, row)
    assert not line.startswith("10 other") and "other diary entries" not in line
    assert line.startswith("Missed dose: metformin") and line.index("metformin") < line.index("amlodipine") < line.index("levothyroxine")


def test_a_fallback_line_names_every_missed_medicine_and_the_next_item(v2_cfg):
    row = _row("month", tags=[SLEEP_TAG], material_changes=[M_SUMMARY, *M_MISSED_ALL, M_STATUS])
    line = fallback_code_line(v2_cfg, row)
    for med in ("metformin", "amlodipine", "levothyroxine"):
        assert med in line
    assert "Sleep below the reference range" in line                                                  # the second item: statuses (no changes were present)


def test_fallback_priority_is_the_same_as_top_items(v2_cfg):
    rhr = T("resting_heart_rate", "resting heart rate", "up", "large")
    glu = T("cgm_glucose_reading", "average glucose", "up", "moderate")
    big = _row(tags=[SLEEP_TAG, glu, rhr], anchors_crossed=["glucose_GMI_change", "sleep_hours_change"],
               material_changes=[{"kind": "anchor_crossed", "anchor": "glucose_GMI_change"}, M_ANCHOR, M_MISSED, M_DIARY_MILD, M_DIARY_SEV, M_STATUS, M_LARGE])
    big["deltas_clean"] = {"gmi": 0.3, "sleep": -2.0}
    line = fallback_code_line(v2_cfg, big)
    assert line.startswith("Diary, 2026-01-02") and "Father hospitalized overnight" in line and "Small errand" not in line         # the severe entry is the theme, the mild one is not
    assert line.index("Missed dose") > line.index("Diary") and "Notable change" not in line                                         # only two items: diary theme, missed doses
    no_diary = _row(tags=[SLEEP_TAG, glu, rhr], anchors_crossed=["glucose_GMI_change", "sleep_hours_change"],
                    material_changes=[{"kind": "anchor_crossed", "anchor": "glucose_GMI_change"}, M_ANCHOR, M_LARGE, M_STATUS])
    no_diary["deltas_clean"] = {"gmi": 0.3, "sleep": -2.0}
    line = fallback_code_line(v2_cfg, no_diary)
    assert line.startswith("Notable change: sleep") and line.index("sleep") < line.index("resting heart rate") < line.index("GMI")           # large first, then the moderate one
    assert "worse than its usual" in line                                                                                           # the second item: statuses


def test_a_fallback_with_nothing_to_say_is_the_nothing_deviated_line(v2_cfg):
    assert fallback_code_line(v2_cfg, _row(material_changes=[])) == "Nothing deviated from her usual."


# ---- 3. checker fixes -------------------------------------------------------------------------------------------------------------------------

def test_non_breaking_and_similar_hyphens_read_as_hyphens():
    expect = "post meal glucose peak rose"
    for dash in ("-", "‐", "‑", "‒", "﹣", "－"):
        assert normalize_text(f"Post{dash}meal glucose peaks rose") == expect, repr(dash)
    assert normalize_text("co­operate") == "cooperate"                                          # a soft hyphen is nothing at all


def test_a_non_breaking_hyphen_no_longer_turns_the_peak_into_glucose(v2_cfg):
    tags = [T("cgm_glucose_reading", "average glucose", "up", "small"), T("post_meal_peak", "post-meal glucose peak", "up", "moderate")]
    assert chk(v2_cfg, "H", ["The post‑meal glucose peak rose noticeably.", "Nothing else."], tags=tags) == []
    assert kinds(chk(v2_cfg, "H", ["The post‑meal glucose peak rose sharply.", "Nothing else."], tags=tags)) == ["direction_size"]


@pytest.mark.parametrize("text", ["It resulted in worry.", "That results in worry.", "As a result she slept badly.", "Stress affected the week.", "It impacted sleep.", "It influenced the week.",
                                  "Walks contributed to it."])
def test_the_causal_list_has_the_new_phrases(v2_cfg, text):
    assert "causal" in kinds(chk(v2_cfg, "H", [text, "Nothing else."]))


@pytest.mark.parametrize("text", ["Follow-up results were reassuring.", "She read the results.", "The outcome was good.", "A resulting calm.", "She was affectionate."])
def test_result_alone_is_not_causal_any_more(v2_cfg, text):
    assert "causal" not in kinds(chk(v2_cfg, "H", [text, "Nothing else."]))


@pytest.mark.parametrize("text", ["Sleep fell below the reference range on a day.", "Sleep rose above the reference range on a day.", "Sleep was above the reference range on a day.",
                                  "Sleep was slightly below the reference range on most days.", "Sleep that fell below the reference range on one day."])
def test_reference_range_phrases_are_statuses_not_trends(v2_cfg, text):
    assert chk(v2_cfg, "H", [text, "Nothing else."]) == []                                           # sleep's tag is flat; a trend claim would fail


def test_real_trend_claims_are_still_checked(v2_cfg):
    assert kinds(chk(v2_cfg, "H", ["Sleep fell sharply.", "Nothing else."])) == ["direction_size"]
    assert kinds(chk(v2_cfg, "H", ["Sleep fell and sleep was below the reference range.", "Nothing else."])) == ["direction_size"]


# ---- 4. selecting and resetting the windows to redo -----------------------------------------------------------------------------------------------

from v0_code.baseline_v2 import cleanup as C


def _stored(wid, tier, headline, sentences, status="gist_ok", reliable=True, **kw):
    r = _row(tier, reliable=reliable, **{"tags": TAGS, **kw})
    r["window_id"] = wid
    r["gist"] = {"headline": headline, "sentences": sentences, "status": status}
    return r


def test_affected_windows_are_found_offline_with_their_reasons(v2_cfg):
    rows = {"day": [
        _stored("day_a", "day", "Fine.", ["Calm day.", "Nothing else."]),
        _stored("day_b", "day", "Fine.", ["Comparisons are tentative.", "Nothing else."]),
        _stored("day_c", "day", "Fine.", ["Sleep affected the day.", "Nothing else."]),
        _stored("day_d", "day", "Slightly higher glucose today.", ["Calm day.", "Nothing else."]),
        _stored("day_e", "day", "Missed doses.", [], status="code_line_fallback"),
        _stored("day_f", "day", "Fine.", ["Comparisons are tentative.", "Nothing else."], reliable=False),
        _stored("day_g", "day", "Average glucose rose.", ["Calm day.", "Nothing else."]),
        _stored("day_h", "day", "Quiet.", [], status="code_line_quiet")], "week": [], "month": []}
    out = C.affected_windows(v2_cfg, rows)
    assert set(out) == {"day_b", "day_c", "day_d", "day_e"}
    assert out["day_b"] == ["forbidden_content"] and out["day_c"] == ["causal"] and out["day_d"] == ["bare glucose in the headline"] and out["day_e"] == ["fallback"]


def test_the_call_estimate_follows_the_batch_sizes_and_the_observed_retry_rates(v2_cfg):
    est = C.estimate_calls(v2_cfg, {"day": 9, "week": 5, "month": 2})
    assert est["first_attempt_calls"] == {"day": 3, "week": 3, "month": 2} and est["total_first"] == 8
    assert est["retries_expected"] >= 1 and est["total_expected"] == est["total_first"] + est["retries_expected"]


def test_reset_can_target_named_windows_only(v2_cfg, v2_stored, tmp_path):
    db = tmp_path / "c.db"
    shutil.copy(v2_stored[1], db)
    store = MemoryV2Store(db)
    pend = [r for r in v2_stored[0]["day"] if r["gist"]["status"] is None][:3]
    for r in pend:
        store.save_gist(r["window_id"], "H.", ["a", "b"], "gist_ok", "[]", [])
    assert store.reset_gists([pend[0]["window_id"], pend[1]["window_id"]]) == 2
    assert [store.get_memory("day", r["end_date"])["gist"]["status"] for r in pend] == [None, None, "gist_ok"]


# ---- 5. the read-only audit -----------------------------------------------------------------------------------------------------------------------

def _mat(*items):
    return list(items)


def test_audit_a_lists_missed_medicines_the_gist_does_not_name(v2_cfg):
    r1 = _stored("w1", "week", "Missed doses.", ["She missed metformin and amlodipine.", "Nothing else."], material_changes=[*M_MISSED_ALL])
    r2 = _stored("w2", "week", "Missed metformin, amlodipine and levothyroxine.", ["Nothing else.", "Calm."], material_changes=[*M_MISSED_ALL])
    miss = C.audit_missed_medicines(v2_cfg, {"week": [r1, r2]})
    assert miss == [{"window_id": "w1", "missing": ["levothyroxine"]}]


def test_audit_b_lists_windows_whose_serious_diary_theme_is_not_mentioned(v2_cfg):
    sev = {"kind": "diary_event", "date": "2026-01-02", "category": "life_event", "text": "Father hospitalized overnight - chest pain", "severity_note": "severe, family crisis"}
    mild = {"kind": "diary_event", "date": "2026-01-03", "category": "life_event", "text": "Bought groceries downtown", "severity_note": "mild"}
    ok = _stored("w1", "week", "A hospital stay for her father.", ["Sleep fell.", "Nothing else."], material_changes=[sev, mild])
    bad = _stored("w2", "week", "A calm week.", ["Sleep fell.", "Nothing else."], material_changes=[sev])
    mild_only = _stored("w3", "week", "A calm week.", ["Nothing else.", "Calm."], material_changes=[mild])
    miss = C.audit_diary_theme(v2_cfg, {"week": [ok, bad, mild_only]})
    assert [m["window_id"] for m in miss] == ["w2"] and "Father hospitalized" in miss[0]["entries"][0]


def test_audit_c_counts_the_watched_words(v2_cfg):
    rows = {"day": [_stored("d1", "day", "Tentative start.", ["Affected by it.", "Calm."]), _stored("d2", "day", "Fine.", ["Calm.", "Contributed a bit."]), _stored("d3", "day", "Fine.", ["Calm.", "Calm."])], "week": [], "month": []}
    out = C.audit_words(rows)
    assert out["counts"] == {"tentative": 1, "affected": 1, "impacted": 0, "influenced": 0, "contributed": 1} and out["windows"] == ["d1", "d2"]


def test_audit_facts_finds_a_wrong_medicine_a_wrong_date_and_a_wrong_forward_direction(v2_cfg):
    base = dict(tags=TAGS, material_changes=[{"kind": "missed_dose", "medicine": "med_1_metformin", "days": 1}])
    wrong_med = _stored("w1", "day", "Missed amlodipine.", ["Nothing else.", "Calm."], **base)
    wrong_date = _stored("w2", "day", "Missed metformin on Tuesday.", ["Nothing else.", "Calm."], **base)
    wrong_dir = _stored("w3", "day", "Missed metformin.", ["She had lower average glucose.", "Calm."], **base)           # glucose is UP: a forward modifier the checker cannot see
    right_dir = _stored("w4", "day", "Missed metformin.", ["She had higher average glucose.", "Calm."], **base)
    decoy = _stored("w0", "week", "Missed metformin, amlodipine and levothyroxine.", ["Calm.", "Nothing else."], material_changes=[*M_MISSED_ALL])          # makes the three names known
    out = C.audit_wrong_facts(v2_cfg, {"day": [wrong_med, wrong_date, wrong_dir, right_dir], "week": [decoy], "month": []})
    assert {(o["window_id"], o["kind"]) for o in out} == {("w1", "wrong medicine"), ("w2", "wrong date"), ("w3", "wrong direction")}
