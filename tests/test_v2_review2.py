"""Stage B review, round 2 (general, config-driven rules; no anchor retuning, no input correction, nothing tailored to this patient's data):
 1. continuous streams get no clinical status            5. blood pressure uses its existing statuses in the status-deviation path
 2. adherence_pct_change fires only on a drop            6. labels ("Notable change" / "Large change"), lab-gap wording, whole-number units
 3. week_gist_weekday: none -> every non-early week queued   7. month entries list diary entries only at moderate severity or worse
 4. code lines use the two most important material items"""

import dataclasses
import re

import pytest

from v0_code.baseline_v2 import anchors as A
from v0_code.baseline_v2.config import Config
from v0_code.baseline_v2.engine import stream_day_status
from v0_code.baseline_v2.render import (EARLY_LINE, early_code_line, fallback_code_line, fmt_unit, material_lines, phrase, plural_categories, top_material_lines)
from v0_code.baseline_v2.windows import bp_status_items, diary_severity_rank, split_month_diary, weekday_name


# ---- 1. continuous streams: no clinical status ------------------------------------------------------------------------------------------------

def test_a_continuous_stream_gets_no_status_even_when_its_readings_carry_one(v2_cfg):
    hr, rhr, sleep = v2_cfg.stream("continuous_heart_rate"), v2_cfg.stream("resting_heart_rate"), v2_cfg.stream("sleep_duration")
    readings = [("t1", 55.0, "low"), ("t2", 56.0, "low"), ("t3", 70.0, "normal")]
    assert stream_day_status(hr, readings) is None                       # zero-step hours include sleep: no per-reading "at rest" status
    assert stream_day_status(rhr, [("t", 77.0, "normal")]) == "normal"   # the daily resting value keeps its status
    assert stream_day_status(sleep, [("t", 6.7, "borderline_low")]) == "borderline_low"


def test_it_is_the_streams_kind_in_config_that_decides_not_its_name(v2_cfg):
    daily = dataclasses.replace(v2_cfg.stream("continuous_heart_rate"), kind="daily")
    assert stream_day_status(daily, [("t", 55.0, "low")]) == "low"


def test_on_the_real_data_continuous_heart_rate_has_no_status_profile_or_deviation(v2_all):
    for tier in ("day", "week", "month"):
        for r in v2_all[tier].values():
            assert not any(i["kind"] == "status_worse_than_usual" and i["measure"] == "continuous_heart_rate" for i in r["material_changes"]), r["window_id"]
    for r in v2_all["day"].values():
        assert "continuous_heart_rate" not in r["facts"]["statuses"] and "cgm_glucose_reading" not in r["facts"]["statuses"]
        assert r["facts"]["profile_asof"]["continuous_heart_rate"]["usual_status"] is None
    assert any(r["facts"]["statuses"].get("resting_heart_rate") for r in v2_all["day"].values())        # the daily resting value still has one
    assert all(c["measure"] != "continuous_heart_rate" for m in v2_all["month"].values() for c in m["facts"]["chronic_findings"])
    assert any(t["measure"] == "continuous_heart_rate" and t["direction"] in ("up", "down") for r in v2_all["day"].values() for t in r["tags"])     # still feeds direction tags


# ---- 2. adherence_pct_change: drops only -------------------------------------------------------------------------------------------------------

QUIET = {"tir": 0.0, "cv": 0.0, "gmi": 0.0, "sleep": 0.0, "resting_hr": 0.0, "steps": 0.0, "adherence_pct": 0.0, "meds_changed": 0, "severe_curr": 0.0, "severe_prior": 0.0, "lab_gap": 0.0}


@pytest.mark.parametrize("tier", ["week", "month"])
def test_adherence_pct_change_fires_on_a_drop_only(v2_cfg, tier):
    th = 15 if tier == "week" else 10
    assert A.evaluate(v2_cfg, tier, {**QUIET, "adherence_pct": -(th + 0.01)}, 3) == ["adherence_pct_change"]
    assert A.evaluate(v2_cfg, tier, {**QUIET, "adherence_pct": th + 5.0}, 3) == []              # a recovery does not cross
    assert A.evaluate(v2_cfg, tier, {**QUIET, "adherence_pct": -float(th)}, 3) == []            # equal to the threshold is still not "more than"


def test_on_the_real_data_only_drops_cross_and_recoveries_still_show_in_what_changed(v2_all):
    recoveries = 0
    for tier in ("week", "month"):
        for r in v2_all[tier].values():
            if "adherence_pct_change" in r["anchors_crossed"]:
                assert r["deltas_clean"]["adherence_pct"] < 0, r["window_id"]
            d = r["deltas_clean"]["adherence_pct"]
            if d is not None and d > 15:
                recoveries += 1
                assert "adherence_pct_change" not in r["anchors_crossed"]
                assert re.search(r"Medication adherence: up [\d.]+ percentage points", r["deviation_text"]), r["window_id"]
    assert recoveries > 0


# ---- 3. week_gist_weekday: none ----------------------------------------------------------------------------------------------------------------

def test_the_weekday_setting_none_means_no_weekday_rule(v2_cfg):
    assert v2_cfg.week_gist_weekday is None
    with_day = dataclasses.replace(v2_cfg, gist={**v2_cfg.gist, "week_gist_weekday": "Sunday"})
    assert with_day.week_gist_weekday == "Sunday"
    assert dataclasses.replace(v2_cfg, gist={"week_gist_weekday": "None"}).week_gist_weekday is None


def test_with_no_weekday_every_non_early_non_quiet_week_is_queued_for_a_gist(v2_all):
    queued = skipped = 0
    for w in v2_all["week"].values():
        assert w["gist_status"] != "code_line_week_skipped"
        if w["gist_status"] is None:
            queued += 1
            assert not w["quiet"]
        else:
            assert w["gist_status"] in ("code_line_early", "code_line_quiet")
    assert queued == sum(1 for w in v2_all["week"].values() if w["gist_status"] is None) > 300


# ---- 4. code lines: the two most important material items ---------------------------------------------------------------------------------------

def _row(items, cfg):
    return {"material_changes": items, "tags": [], "deltas_clean": {"sleep": -2.0, "tir": 0.0, "cv": 0.0, "gmi": 0.0, "resting_hr": 0.0, "steps": 0.0, "adherence_pct": 0.0, "meds_changed": 2, "severe_curr": 0.0, "severe_prior": 0.0, "lab_gap": 0.0}}


def _diary(severity, text="x"):
    return {"kind": "diary_event", "date": "2026-01-05", "category": "life_event", "text": text, "severity_note": severity}


MISSED = {"kind": "missed_dose", "medicine": "med_1_metformin", "days": 1}
LARGE = {"kind": "large_change", "measure": "hydration", "label": "hydration", "direction": "down", "direction_word": "down", "size": "large"}
STATUS = {"kind": "status_worse_than_usual", "measure": "sleep_duration", "status": "low", "usual": "normal"}
ANCHOR = {"kind": "anchor_crossed", "anchor": "sleep_hours_change"}


def test_priority_is_anchors_then_diary_by_severity_then_missed_doses_then_large_changes_then_statuses(v2_cfg):
    items = [STATUS, LARGE, MISSED, _diary("mild", "mild one"), _diary("severe, crisis", "severe one"), _diary("moderate", "moderate one"), ANCHOR]
    lines = top_material_lines(v2_cfg, _row(items, v2_cfg), n=7)
    assert len(lines) == 7
    assert lines[0].startswith("Notable change") and "severe one" in lines[1] and "moderate one" in lines[2] and "mild one" in lines[3]
    assert lines[4].startswith("Missed dose") and lines[5].startswith("Large change") and "worse than its usual" in lines[6]


def test_the_top_two_skip_nothing_that_outranks_them(v2_cfg):
    assert len(top_material_lines(v2_cfg, _row([STATUS, MISSED, LARGE], v2_cfg), n=2)) == 2
    two = top_material_lines(v2_cfg, _row([STATUS, LARGE, MISSED], v2_cfg), n=2)
    assert two[0].startswith("Missed dose") and two[1].startswith("Large change")
    assert top_material_lines(v2_cfg, _row([], v2_cfg), n=2) == []


def test_the_fallback_line_is_the_top_two_or_a_nothing_deviated_line(v2_cfg):
    line = fallback_code_line(v2_cfg, _row([STATUS, MISSED, ANCHOR], v2_cfg))             # the top_items priority: missed doses, then anchors/large changes (statuses would be third)
    assert line.startswith("Missed dose") and "Notable change" in line and "worse than its usual" not in line
    assert fallback_code_line(v2_cfg, _row([], v2_cfg)) == "Nothing deviated from her usual."


def test_the_early_line_still_says_there_is_not_enough_history_and_then_gives_the_top_two(v2_cfg):
    assert early_code_line(v2_cfg, _row([], v2_cfg)) == EARLY_LINE == "Not enough history yet to compare."
    line = early_code_line(v2_cfg, _row([STATUS, MISSED], v2_cfg))
    assert line.startswith(EARLY_LINE + " Missed dose") and "worse than its usual" in line


def test_on_the_real_data_early_windows_carry_their_top_two_items(v2_all):
    days = [v2_all["day"][w] for w in sorted(v2_all["day"])]
    early = [d for d in days if d["gist_status"] == "code_line_early"]
    with_material = [d for d in early if d["material_changes"]]
    assert len(early) == 14 and with_material
    for d in with_material:
        assert d["gist_headline"].startswith("Not enough history yet to compare. ") and len(d["gist_headline"]) > len(EARLY_LINE) + 5


# ---- 5. blood pressure in the status-deviation path --------------------------------------------------------------------------------------------

def _bp(s, d):
    return {"systolic_status": s, "diastolic_status": d}


def test_a_blood_pressure_reading_is_judged_by_the_worse_of_its_two_numbers(v2_cfg):
    earlier = [_bp("normal", "normal")] * 20
    window = [_bp("normal", "high"), _bp("high", "normal"), _bp("normal", "normal"), _bp("borderline_high", "normal"), _bp("normal", "normal")]
    (item,) = bp_status_items(v2_cfg, window, earlier, min_rank=2)
    assert (item["kind"], item["measure"], item["status"], item["usual"], item["days"], item["of"], item["unit"]) == ("status_worse_than_usual", "blood_pressure", "high", "normal", 2, 5, "readings")


def test_min_material_status_applies_to_blood_pressure(v2_cfg):
    earlier = [_bp("normal", "normal")] * 20
    window = [_bp("borderline_high", "normal")] * 3 + [_bp("normal", "normal")] * 2
    assert bp_status_items(v2_cfg, window, earlier, min_rank=2) == []
    (item,) = bp_status_items(v2_cfg, window, earlier, min_rank=1)
    assert item["status"] == "borderline_high" and item["days"] == 3 and item["of"] == 5


def test_blood_pressure_that_is_usually_abnormal_is_not_a_deviation_and_too_little_history_gives_none(v2_cfg):
    assert bp_status_items(v2_cfg, [_bp("high", "high")] * 3, [_bp("high", "normal")] * 20, min_rank=2) == []
    assert bp_status_items(v2_cfg, [_bp("high", "high")] * 3, [_bp("normal", "normal")] * 5, min_rank=2) == []       # fewer earlier readings than min_days_for_compare: no usual yet
    assert bp_status_items(v2_cfg, [], [_bp("normal", "normal")] * 20, min_rank=2) == []


def test_the_blood_pressure_line_reads_as_the_example(v2_cfg):
    row = _row([{"kind": "status_worse_than_usual", "measure": "blood_pressure", "status": "high", "usual": "normal", "days": 3, "of": 5, "unit": "readings"}], v2_cfg)
    assert material_lines(v2_cfg, row) == ["Blood pressure above the reference range on 3 of 5 readings, worse than its usual (within the reference range)."]


def test_on_the_real_data_blood_pressure_deviations_appear_in_weeks_and_months_only_at_abnormal(v2_all):
    n = 0
    for tier in ("week", "month"):
        for r in v2_all[tier].values():
            for i in r["material_changes"]:
                if i.get("measure") == "blood_pressure":
                    n += 1
                    assert i["kind"] == "status_worse_than_usual" and i["status"] in ("low", "high") and 0 < i["days"] <= i["of"] and i["unit"] == "readings"
                    assert re.search(r"Blood pressure (above|below) the reference range on \d+ of \d+ readings", r["deviation_text"])
    assert n > 0
    assert not any(i.get("measure") == "blood_pressure" for r in v2_all["day"].values() for i in r["material_changes"])         # weeks and months only


# ---- 6. labels and rounding ---------------------------------------------------------------------------------------------------------------------

def test_an_anchor_crossing_is_a_notable_change_and_large_change_is_reserved_for_a_large_tag(v2_all):
    for tier in ("day", "week", "month"):
        for r in v2_all[tier].values():
            lines = r["deviation_text"].split("NUMBERS:")[0].splitlines()
            n_anchor = sum(1 for i in r["material_changes"] if i["kind"] == "anchor_crossed" and i["anchor"] != "lab_cgm_discordance")
            n_large = sum(1 for i in r["material_changes"] if i["kind"] == "large_change")
            assert sum(l.strip().startswith("- Notable change") for l in lines) == n_anchor, r["window_id"]
            assert sum(l.strip().startswith("- Large change") for l in lines) == n_large, r["window_id"]
            assert not any(l.strip().startswith("- Large move") for l in lines)
    assert any("Large change in" in r["deviation_text"] for r in v2_all["day"].values())


def test_the_lab_gap_is_a_difference_not_a_change(v2_all):
    m = v2_all["month"]["month_ENDING_2025-12-29"]
    assert "Lab HbA1c and the glucose-based estimate differ by 1.12 points." in m["deviation_text"]
    assert not any("lab" in l.lower() and l.strip().startswith("- Notable change") for l in m["deviation_text"].splitlines())
    assert "lab HbA1c and the glucose-based estimate differ by 1.12 points" in m["notable_reason"]


def test_steps_ml_and_minutes_are_whole_numbers_in_every_rendered_text(v2_all):
    bad = [re.compile(p) for p in (r"\d+\.\d+ (steps|mL|minutes)\b", r"steps (average )?\d+\.\d+", r"average \d+\.\d+ per day", r"hydration \d+\.\d+", r"sedentary time \d+\.\d+",
                                   r"Sedentary: average \d+\.\d+", r"steps \d+\.\d+", r"sedentary[^\n]*\d+\.\d+ minutes")]
    for tier in v2_all.values():
        for r in tier.values():
            for rx in bad:
                assert not rx.search(r["deviation_text"]), (r["window_id"], rx.pattern, rx.search(r["deviation_text"]).group(0))


def test_whole_number_units_come_from_config_and_other_units_keep_their_decimals(v2_cfg):
    assert fmt_unit(1473.57, "steps", v2_cfg) == "1474" and fmt_unit(1839.4, "mL", v2_cfg) == "1839" and fmt_unit(619.5, "minutes", v2_cfg) == "620"
    assert fmt_unit(6.9, "hours", v2_cfg) == "6.9" and fmt_unit(0.33, "points", v2_cfg) == "0.33"
    assert phrase(-1751.0, "steps", cfg=v2_cfg) == "down 1751 steps" and phrase(49.71, "minutes", cfg=v2_cfg) == "up 50 minutes" and phrase(-0.5, "hours", cfg=v2_cfg) == "down 0.5 hours"


# ---- 7. month entries: diary entries at moderate severity or worse ------------------------------------------------------------------------------------

def test_severity_is_ranked_by_the_configured_keywords(v2_cfg):
    assert diary_severity_rank(v2_cfg, "severe, family crisis") < diary_severity_rank(v2_cfg, "moderate, improving") < diary_severity_rank(v2_cfg, "mild") < diary_severity_rank(v2_cfg, "positive")
    assert diary_severity_rank(v2_cfg, None) == diary_severity_rank(v2_cfg, "concerning, not her own symptom")           # no configured keyword: unranked


def test_the_month_lists_only_moderate_or_worse_up_to_the_cap_and_counts_the_rest(v2_cfg):
    ev = [{"date": f"2026-01-{i:02d}", "category": "life_event", "text": f"e{i}", "severity_note": "severe"} for i in range(1, 11)]
    ev += [{"date": "2026-01-20", "category": "symptom", "text": "mild one", "severity_note": "mild"}] * 4 + [{"date": "2026-01-21", "category": "life_event", "text": "pos", "severity_note": "positive"}] * 2
    listed, summary = split_month_diary(v2_cfg, ev)
    assert len(listed) == 8 and all(diary_severity_rank(v2_cfg, e["severity_note"]) <= diary_severity_rank(v2_cfg, "moderate") for e in listed)
    assert summary["count"] == 8 and summary["by_category"] == {"life_event": 4, "symptom": 4}                           # 2 severe over the cap + 4 mild + 2 positive
    assert plural_categories({"life_event": 6, "symptom": 4}) == "6 life events, 4 symptoms" and plural_categories({"symptom": 1}) == "1 symptom"


def test_a_month_with_no_overflow_has_no_summary_item(v2_cfg):
    ev = [{"date": "2026-01-02", "category": "life_event", "text": "a", "severity_note": "moderate"}]
    assert split_month_diary(v2_cfg, ev) == (ev, None)
    assert split_month_diary(v2_cfg, []) == ([], None)


def test_on_the_real_data_the_month_tier_follows_the_diary_rule_and_week_tier_is_unchanged(v2_all, v2_cfg):
    days = [v2_all["day"][w] for w in sorted(v2_all["day"])]
    for m in v2_all["month"].values():
        start = m["facts"]["last_n_start"]
        in_window = [e for d in days if start <= d["end_date"] <= m["end_date"] for e in d["facts"]["diary_events"]]
        listed = [i for i in m["material_changes"] if i["kind"] == "diary_event"]
        summary = [i for i in m["material_changes"] if i["kind"] == "diary_summary"]
        assert len(listed) <= 8 and all(diary_severity_rank(v2_cfg, i["severity_note"]) <= diary_severity_rank(v2_cfg, "moderate") for i in listed), m["window_id"]
        assert len(listed) + (summary[0]["count"] if summary else 0) == len(in_window), m["window_id"]
        if summary:
            assert re.search(rf"{summary[0]['count']} other diary entr(y|ies): ", m["deviation_text"])
    assert any(i["kind"] == "diary_summary" for m in v2_all["month"].values() for i in m["material_changes"])
    for w in v2_all["week"].values():                                    # weeks keep every event
        assert not any(i["kind"] == "diary_summary" for i in w["material_changes"])


def test_the_ignored_anchor_caveat_uses_the_same_word_as_the_anchor_line(v2_all):
    m = v2_all["month"]["month_ENDING_2025-12-29"]
    assert "A notable change (severe range appeared or cleared) was ignored" in m["deviation_text"]
    assert not any("A large change (" in r["deviation_text"] for tier in v2_all.values() for r in tier.values())


def test_joined_code_lines_are_separate_sentences(v2_cfg):
    items = [_diary("severe", "Father hospitalized"), MISSED]
    line = early_code_line(v2_cfg, _row(items, v2_cfg))
    assert '"Father hospitalized" (severe). Missed dose' in line
    assert fallback_code_line(v2_cfg, _row(items, v2_cfg)).count(". ") == 1
