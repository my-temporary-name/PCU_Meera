"""Stage A review, round 1 (four general rules, each driven by config or structure, none tailored to this patient's data):
 1. adherence_meds_changed fires only on worsening (taken -> missed); recoveries still show in "what changed".
 2. min_material_status (default: abnormal): borderline statuses are shown in the numbers but are not material.
 3. No "large move" item for a measure already represented by another material item.
 4. Count-like streams (mood) are always worded "strained periods of the day: more / fewer", never "mood up / down"."""

import dataclasses
import re
import sqlite3

import pytest

from v0_code.baseline_v2 import anchors as A
from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.data import StoreView
from v0_code.baseline_v2.engine import build_days, meds_worsened
from v0_code.baseline_v2.material import build_material
from v0_code.baseline_v2.tags import make_tag


# ---- 1. worsening only ---------------------------------------------------------------------------------------------------------------

def test_only_taken_to_missed_counts_as_a_medicine_getting_worse():
    assert meds_worsened({"a": "taken", "b": "taken"}, {"a": "missed", "b": "taken"}) == 1
    assert meds_worsened({"a": "missed", "b": "missed"}, {"a": "taken", "b": "taken"}) == 0          # two recoveries: not a worsening
    assert meds_worsened({"a": "taken", "b": "missed"}, {"a": "missed", "b": "taken"}) == 1          # one each way: one worsening
    assert meds_worsened({"a": "missed"}, {"a": "missed"}) == 0
    assert meds_worsened({"a": "taken"}, {"a": "taken", "new": "missed"}) == 0                         # a medicine with no previous day cannot have worsened
    assert meds_worsened(None, {"a": "missed"}) is None


def test_two_recoveries_do_not_cross_the_anchor_but_two_new_misses_do(v2_cfg):
    base = {"tir": 0.0, "cv": 0.0, "gmi": 0.0, "sleep": 0.0, "resting_hr": 0.0, "steps": 0.0, "adherence_pct": 0.0, "severe_curr": 0.0, "severe_prior": 0.0}
    prev, rec, new_miss = {"a": "missed", "b": "missed", "c": "taken"}, {"a": "taken", "b": "taken", "c": "taken"}, {"a": "taken", "b": "taken", "c": "missed"}
    assert A.evaluate(v2_cfg, "day", {**base, "meds_changed": meds_worsened(prev, rec)}, 3) == []
    two = meds_worsened({"a": "taken", "b": "taken", "c": "taken"}, {"a": "missed", "b": "missed", "c": "taken"})
    assert A.evaluate(v2_cfg, "day", {**base, "meds_changed": two}, 3) == ["adherence_meds_changed"]


def test_on_the_real_data_the_anchor_fires_only_when_enough_medicines_got_worse(v2_rows, v2_cfg):
    days = sorted(v2_rows)
    recoveries_only = 0
    for prev_id, wid in zip(days, days[1:]):
        p, c = v2_rows[prev_id]["facts"]["adherence"]["per_medication"], v2_rows[wid]["facts"]["adherence"]["per_medication"]
        worse = meds_worsened(p, c)
        need = min(2, v2_rows[wid]["facts"]["n_medications"])
        assert ("adherence_meds_changed" in v2_rows[wid]["anchors_crossed"]) == (worse is not None and worse >= need > 0), wid
        recovered = sum(1 for m, s in c.items() if p.get(m) == "missed" and s == "taken")
        if recovered >= 2 and (worse or 0) < need:
            recoveries_only += 1
            assert "adherence_meds_changed" not in v2_rows[wid]["anchors_crossed"]
    assert recoveries_only > 0                       # the data does contain days of pure recovery: the check was not vacuous


def test_a_recovery_still_appears_in_what_changed(v2_rows):
    r = v2_rows["day_2026-01-27"]                    # two medicines went from missed to taken
    assert "adherence_meds_changed" not in r["anchors_crossed"]
    assert re.search(r"Medication adherence: up [\d.]+ percentage points", r["deviation_text"].split("WHAT CHANGED")[1])


def test_the_anchor_text_says_which_way(v2_cfg):
    from v0_code.baseline_v2.render import anchor_phrase
    assert anchor_phrase(v2_cfg, "adherence_meds_changed", {"meds_changed": 2}, []) == "2 medicines went from taken to missed"


# ---- 2. min_material_status -----------------------------------------------------------------------------------------------------------

def _mat(**over):
    kw = dict(anchors_crossed=[], per_medication={"m": "taken"}, diary_events=[], statuses={}, usual={}, tags=[], gap_hours=None, low_completeness=[], removed=[], date="2026-01-05")
    kw.update(over)
    return build_material(**kw)


def test_the_default_is_abnormal_and_the_value_is_validated(v2_cfg, tmp_path):
    assert v2_cfg.min_material_status == "abnormal"
    text = open("config/patient_meera_iyer_v1.yaml").read().replace("min_material_status: abnormal", "min_material_status: severe")
    (tmp_path / "bad.yaml").write_text(text)
    with pytest.raises(ValueError):
        Config.from_yaml(tmp_path / "bad.yaml")
    no_key = "\n".join(l for l in open("config/patient_meera_iyer_v1.yaml").read().splitlines() if not l.startswith("min_material_status"))
    (tmp_path / "nokey.yaml").write_text(no_key)
    assert Config.from_yaml(tmp_path / "nokey.yaml").min_material_status == "abnormal"          # absent = the default


def test_borderline_is_not_material_at_abnormal_and_is_at_borderline():
    s = dict(statuses={"sleep": "borderline_low"}, usual={"sleep": "normal"})
    assert _mat(**s) == [] and _mat(**s, min_status_rank=2) == []
    assert _mat(**s, min_status_rank=1)[0]["kind"] == "status_worse_than_usual"
    ab = dict(statuses={"sleep": "low"}, usual={"sleep": "normal"})
    assert _mat(**ab)[0]["kind"] == "status_worse_than_usual" and _mat(**ab, min_status_rank=1)[0]["kind"] == "status_worse_than_usual"


def test_borderline_statuses_are_shown_in_the_numbers_but_not_under_things_that_deviated(v2_rows):
    t = v2_rows["day_2025-12-26"]["deviation_text"]            # hydration and screen time are borderline that day
    deviated = t.split("NUMBERS")[0]
    assert "Hydration" not in deviated and "Screen time" not in deviated
    numbers = t.split("NUMBERS")[1].split("WHAT CHANGED")[0]
    assert "hydration 1839 mL (slightly below the reference range)" in numbers and "screen time 6.9 hours (slightly above the reference range)" in numbers


def test_under_the_default_no_borderline_status_is_ever_material(v2_rows):
    for r in v2_rows.values():
        for i in r["material_changes"]:
            if i["kind"] == "status_worse_than_usual":
                assert i["status"] in ("low", "high"), (r["window_id"], i)


def test_borderline_setting_restores_the_old_behaviour_and_has_fewer_quiet_days(v2_rows, v2_cfg, pipeline_run):
    _, db = pipeline_run
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    loose = build_days(dataclasses.replace(v2_cfg, min_material_status="borderline"), StoreView(ro, v2_cfg))
    ro.close()
    assert any(i["kind"] == "status_worse_than_usual" and i["status"].startswith("borderline") for r in loose for i in r["material_changes"])
    assert sum(r["quiet"] for r in loose) <= sum(r["quiet"] for r in v2_rows.values())
    assert [r["anchors_crossed"] for r in loose] == [v2_rows[r["window_id"]]["anchors_crossed"] for r in loose]      # anchors do not depend on this setting


# ---- 3. no duplicate "large move" ------------------------------------------------------------------------------------------------------

def _tag(measure, domain, size="large", direction="up"):
    return {"measure": measure, "label": measure, "domain": domain, "direction": direction, "size": size, "direction_word": direction}


def test_a_missed_dose_already_represents_the_adherence_measure():
    items = _mat(per_medication={"m": "missed"}, tags=[_tag("medication_adherence", "adherence", direction="down"), _tag("hydration", "lifestyle")])
    assert [i["measure"] for i in items if i["kind"] == "large_change"] == ["hydration"]


def test_a_crossed_anchor_already_represents_its_measure():
    items = _mat(anchors_crossed=["sleep_hours_change"], tags=[_tag("sleep_duration", "sleep"), _tag("step_count", "activity")])
    assert [i["measure"] for i in items if i["kind"] == "large_change"] == ["step_count"]
    items = _mat(anchors_crossed=["adherence_meds_changed"], tags=[_tag("medication_adherence", "adherence")])
    assert not [i for i in items if i["kind"] == "large_change"]


def test_a_status_item_already_represents_its_measure():
    items = _mat(statuses={"hydration": "low"}, usual={"hydration": "normal"}, tags=[_tag("hydration", "lifestyle")])
    assert [i["kind"] for i in items] == ["status_worse_than_usual"]


def test_a_measure_with_no_other_item_still_gets_its_large_move():
    assert [i["measure"] for i in _mat(tags=[_tag("hydration", "lifestyle")]) if i["kind"] == "large_change"] == ["hydration"]


def test_on_the_real_data_no_large_move_duplicates_another_item(v2_rows):
    for r in v2_rows.values():
        items = r["material_changes"]
        represented = {i["measure"] for i in items if i["kind"] == "status_worse_than_usual"}
        represented |= {A.ANCHOR_STREAM[i["anchor"]] for i in items if i["kind"] == "anchor_crossed" and i["anchor"] in A.ANCHOR_STREAM}
        if any(i["kind"] == "anchor_crossed" and i["anchor"] == "adherence_meds_changed" for i in items) or any(i["kind"] == "missed_dose" for i in items):
            represented.add("medication_adherence")
        for i in items:
            if i["kind"] == "large_change":
                assert i["measure"] not in represented, (r["window_id"], i)


# ---- 4. strained periods, never "mood up / down" ---------------------------------------------------------------------------------------

def test_count_like_tags_carry_more_or_fewer_words_and_others_up_or_down(v2_cfg):
    mood, sleep = v2_cfg.stream("mood_state"), v2_cfg.stream("sleep_duration")
    assert mood.label == "strained periods of the day" and mood.count_like
    up = make_tag(mood, 3.0, 1.0, {"flat_band": 0.5}, v2_cfg)
    down = make_tag(mood, 0.0, 2.0, {"flat_band": 0.5}, v2_cfg)
    assert (up["direction"], up["direction_word"]) == ("up", "more") and (down["direction"], down["direction_word"]) == ("down", "fewer")
    assert make_tag(sleep, 8.0, 7.0, {"flat_band": 0.2}, v2_cfg)["direction_word"] == "up"


def test_the_word_mood_is_never_a_direction_anywhere_in_the_text(v2_rows):
    pat = re.compile(r"\bmood\b[^\n]*?\b(up|down|more|fewer|rose|fell)\b", re.I)
    n = 0
    for r in v2_rows.values():
        for line in r["deviation_text"].splitlines():
            assert not pat.search(line), (r["window_id"], line)
            n += "strained period" in line
    assert n > 100                                    # the strained-period wording does appear


def test_strained_periods_wording_in_tags_comovement_deviations_and_text(v2_rows):
    seen = {"tag": 0, "co": 0, "large": 0, "changed": 0}
    for r in v2_rows.values():
        for t in r["tags"]:
            if t["measure"] == "mood_state":
                seen["tag"] += 1
                assert t["label"] == "strained periods of the day" and t["direction_word"] in ("more", "fewer", "flat", "not_enough_data")
        for e in r["co_movement"]["same_direction"] + r["co_movement"]["opposite_direction"]:
            if e["domain"] == "mood":
                seen["co"] += 1
                assert e["measure"] == "strained periods of the day" and e["direction_word"] in ("more", "fewer")
        for i in r["material_changes"]:
            if i["kind"] == "large_change" and i["measure"] == "mood_state":
                seen["large"] += 1
                assert i["label"] == "strained periods of the day" and i["direction_word"] in ("more", "fewer")
                assert f"Large change in strained periods of the day: {i['direction_word']}." in r["deviation_text"]
        for line in r["deviation_text"].split("WHAT CHANGED")[-1].split("MOVED TOGETHER")[0].splitlines():
            if line.strip().startswith("- Strained periods of the day"):
                seen["changed"] += 1
                assert re.search(r"Strained periods of the day: \d+ (more|fewer)", line) or "no change" in line, line
    assert all(v > 0 for v in seen.values()), seen
