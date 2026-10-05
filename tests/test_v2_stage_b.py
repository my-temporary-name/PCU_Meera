"""Baseline Engine v2, Stage B: week and month tiers (code only). Same rules as Stage A: as-of dates, cleaned values, config-driven."""

import json
import shutil
import sqlite3
from collections import Counter
from datetime import date, timedelta

import pytest

from v0_code.baseline_v2.data import Reading, StoreView
from v0_code.baseline_v2.engine import build_windows
from v0_code.baseline_v2.trust import clean_series, glucose_metrics
from v0_code.baseline_v2.windows import best_and_worst, checkpoint_indices, chronic_findings, lab_link, weekday_name, worst_mood


# ---- pure helpers ---------------------------------------------------------------------------------------------------------------------

def test_checkpoints_are_every_n_days_plus_a_final_partial_one():
    assert checkpoint_indices(100, 30) == [29, 59, 89, 99] and checkpoint_indices(90, 30) == [29, 59, 89] and checkpoint_indices(10, 30) == [9]


def test_weekday_name_comes_from_the_calendar():
    assert weekday_name("2026-01-04") == "Sunday" and weekday_name("2026-01-05") == "Monday"


def _d(day, tir, mean):
    return {"date": day, "tir_pct": tir, "glucose_mean": mean}


def test_best_day_is_highest_tir_ties_by_lowest_mean_worst_is_lowest_tir_ties_by_highest_mean():
    days = [_d("d1", 100.0, 130.0), _d("d2", 100.0, 120.0), _d("d3", 100.0, 140.0), _d("d4", 90.0, 150.0), _d("d5", 90.0, 160.0)]
    best, worst, identical = best_and_worst(days)
    assert (best["date"], worst["date"], identical) == ("d2", "d5", False)


def test_when_every_day_is_identical_no_best_or_worst_day_is_named():
    assert best_and_worst([_d(f"d{i}", 100.0, 125.0) for i in range(7)]) == (None, None, True)


def test_worst_mood_ranks_by_the_configured_distress_order(v2_cfg):
    blocks = lambda *cats: {f"b{i}": {"category": c} for i, c in enumerate(cats)}
    assert worst_mood(blocks("positive_uplifted", "calm_stable", "mild_stress"), v2_cfg) == "mild_stress"
    assert worst_mood(blocks("positive_uplifted", "calm_stable"), v2_cfg) == "calm_stable"          # uplifted is never the worst while anything else was recorded
    assert worst_mood(blocks("positive_uplifted"), v2_cfg) == "positive_uplifted"
    assert worst_mood(blocks("calm_stable", "overwhelmed_high_distress", "anxious"), v2_cfg) == "overwhelmed_high_distress"
    assert worst_mood({}, v2_cfg) is None


def test_chronic_findings_need_enough_days_and_the_configured_share(v2_cfg):
    hist = {"steps": ["low"] * 18 + ["normal"] * 2, "sleep": ["normal"] * 10 + ["low"] * 10, "hydration": ["normal"] * 19 + ["low"], "short": ["low"] * 5}
    out = chronic_findings(hist, v2_cfg)
    assert [f["measure"] for f in out] == ["steps", "sleep"] and out[0]["share_pct"] == 90.0 and out[1]["share_pct"] == 50.0       # 50% is included; 5% is not; 5 days is too few


def _r(ts_day, hour, v):
    from datetime import datetime
    dt = datetime.fromisoformat(f"{ts_day}T{hour:02d}:00:00+00:00")
    return Reading(dt.isoformat(), dt, v)


def test_lab_link_gap_is_the_labs_hba1c_minus_the_gmi_of_the_prior_readings_only(v2_cfg):
    from datetime import datetime
    kept = [_r("2026-01-01", h, 120.0) for h in range(8)] + [_r("2026-01-02", 12, 300.0)]              # a later reading must not count
    lab = (datetime.fromisoformat("2026-01-02T08:00:00+00:00"), 7.0, "high")
    (l,) = lab_link([lab], kept, v2_cfg, as_of="2026-01-05")
    gmi = round(3.31 + 0.02392 * 120.0, 2)
    assert l["gmi_90d_prior"] == gmi and l["gap_hba1c_minus_gmi"] == round(7.0 - gmi, 2) and l["cgm_days"] == 1 and l["lab_date"] == "2026-01-02"
    assert lab_link([lab], kept, v2_cfg, as_of="2026-01-01") == []                                    # a lab after the checkpoint does not exist yet
    (none,) = lab_link([(datetime.fromisoformat("2025-06-01T08:00:00+00:00"), 7.0, "high")], kept, v2_cfg, as_of="2026-01-05")
    assert none["gmi_90d_prior"] is None and none["gap_hba1c_minus_gmi"] is None


# ---- week tier ------------------------------------------------------------------------------------------------------------------------

def _days(v2_all):
    return [v2_all["day"][w] for w in sorted(v2_all["day"])]


def test_one_week_per_day_from_the_seventh_each_spanning_seven_days(v2_all):
    weeks = [v2_all["week"][w] for w in sorted(v2_all["week"])]
    days = _days(v2_all)
    assert len(weeks) == 346 and weeks[0]["end_date"] == days[6]["end_date"] and weeks[-1]["end_date"] == days[-1]["end_date"]
    for w in weeks:
        e = date.fromisoformat(w["end_date"])
        assert w["window_id"] == f"week_ENDING_{w['end_date']}" and w["start_date"] == (e - timedelta(days=6)).isoformat() and w["tier"] == "week"


def test_the_first_14_weeks_have_no_flat_band_or_previous_window_and_get_the_early_code_line(v2_all):
    weeks = [v2_all["week"][w] for w in sorted(v2_all["week"])]
    for w in weeks[:14]:
        assert w["gist_status"] == "code_line_early" and w["gist_headline"].startswith("Not enough history yet to compare.") and all(t["direction"] == "not_enough_data" for t in w["tags"])
    assert weeks[14]["gist_status"] != "code_line_early" and any(t["direction"] != "not_enough_data" for t in weeks[14]["tags"])


def test_week_gist_weekday_rule_when_configured_early_quiet_sunday_or_anchor_else_a_code_line_from_the_top_two_changes(v2_weeks_with_weekday_rule):
    from v0_code.baseline_v2.render import fallback_code_line
    v2_cfg, weeks = v2_weeks_with_weekday_rule
    seen = Counter()
    for w in weeks.values():
        sunday = weekday_name(w["end_date"]) == v2_cfg.week_gist_weekday
        if w["gist_status"] == "code_line_early":
            continue
        if w["quiet"]:
            assert w["gist_status"] == "code_line_quiet"
        elif sunday or w["anchors_crossed"]:
            assert w["gist_status"] is None                            # the LLM gist, later
        else:
            assert w["gist_status"] == "code_line_week_skipped"
            assert w["gist_headline"] == fallback_code_line(v2_cfg, w)
        seen[w["gist_status"]] += 1
    assert seen[None] > 0 and seen["code_line_week_skipped"] > 0


def test_every_missed_dose_in_the_week_is_counted_and_rendered(v2_all, v2_cfg):
    days = _days(v2_all)
    by_date = {d["end_date"]: d for d in days}
    n = 0
    for w in v2_all["week"].values():
        span = [by_date[(date.fromisoformat(w["end_date"]) - timedelta(days=k)).isoformat()] for k in range(6, -1, -1)]
        expect = Counter(m for d in span for m, s in d["facts"]["adherence"]["per_medication"].items() if s != "taken")
        got = {i["medicine"]: i for i in w["material_changes"] if i["kind"] == "missed_dose"}
        assert {m: c for m, c in expect.items()} == {m: i["days"] for m, i in got.items()}, w["window_id"]
        for m, c in expect.items():
            n += 1
            assert got[m]["of"] == 7 and f"Missed dose: {v2_cfg.medicine_name(m)}, {c} of 7 days." in w["deviation_text"], (w["window_id"], m)
    assert n > 500


def test_every_diary_event_in_the_week_appears_verbatim_and_dated(v2_all):
    by_date = {d["end_date"]: d for d in _days(v2_all)}
    n = 0
    for w in v2_all["week"].values():
        for k in range(7):
            ds = (date.fromisoformat(w["end_date"]) - timedelta(days=k)).isoformat()
            for e in by_date[ds]["facts"]["diary_events"]:
                n += 1
                assert e["text"] in w["deviation_text"] and f"Diary, {ds}" in w["deviation_text"], (w["window_id"], e["text"])
    assert n > 700                                      # every event appears in up to 7 rolling windows


def test_the_weeks_glucose_metrics_are_computed_on_the_cleaned_readings_pooled_over_the_week(v2_all, v2_cfg, pipeline_run):
    _, db = pipeline_run
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    kept, removed = clean_series(StoreView(ro, v2_cfg).glucose_series, v2_cfg)
    ro.close()
    by_day = {}
    for r in kept:
        by_day.setdefault(r.dt.date().isoformat(), []).append(r.value)
    for w in v2_all["week"].values():
        e = date.fromisoformat(w["end_date"])
        vals = [v for k in range(6, -1, -1) for v in by_day.get((e - timedelta(days=k)).isoformat(), [])]
        m = glucose_metrics(vals, 96 * 7)
        g = w["facts"]["glucose"]
        assert (g["mean"], g["tir_pct"], g["cv_pct"], g["tar_severe_pct"], g["n_readings"]) == (m["mean"], m["tir_pct"], m["cv_pct"], m["tar_severe_pct"], m["n_readings"]), w["window_id"]
        assert g["max_value"] <= v2_cfg.device_range[1]


def test_the_day_by_day_list_has_seven_dated_entries_with_flags(v2_all, v2_cfg):
    by_date = {d["end_date"]: d for d in _days(v2_all)}
    for w in v2_all["week"].values():
        traj = w["facts"]["daily_trajectory"]
        assert [t["date"] for t in traj] == [(date.fromisoformat(w["end_date"]) - timedelta(days=k)).isoformat() for k in range(6, -1, -1)]
        for t in traj:
            d = by_date[t["date"]]
            assert t["missed_medicines"] == sorted(m for m, s in d["facts"]["adherence"]["per_medication"].items() if s != "taken")
            assert t["diary_event_count"] == len(d["facts"]["diary_events"]) and t["sleep_hours"] == d["facts"]["sleep"]["duration_hours"]
            assert t["date"] in w["deviation_text"]
    assert "DAY BY DAY" in next(iter(v2_all["week"].values()))["deviation_text"]


def test_best_and_worst_day_follow_the_tie_break_and_differ_unless_all_days_tie(v2_all):
    for w in v2_all["week"].values():
        traj, f = w["facts"]["daily_trajectory"], w["facts"]
        tirs = [(t["tir_pct"], t["glucose_mean"]) for t in traj]
        if len(set(tirs)) == 1:
            assert f["best_day"] is None and f["worst_day"] is None and f["best_and_worst_note"]
            continue
        top = max(t["tir_pct"] for t in traj)
        best = min((t for t in traj if t["tir_pct"] == top), key=lambda t: (t["glucose_mean"], t["date"]))
        low = min(t["tir_pct"] for t in traj)
        worst = min((t for t in traj if t["tir_pct"] == low), key=lambda t: (-t["glucose_mean"], t["date"]))
        assert f["best_day"]["date"] == best["date"] and f["worst_day"]["date"] == worst["date"] and best["date"] != worst["date"], w["window_id"]


def test_each_days_worst_mood_is_the_most_distressed_category_that_day(v2_all, v2_cfg):
    by_date = {d["end_date"]: d for d in _days(v2_all)}
    for w in list(v2_all["week"].values())[::10]:
        for t in w["facts"]["daily_trajectory"]:
            cats = [b["category"] for b in by_date[t["date"]]["facts"]["mood"]["blocks"].values()]
            if cats:
                assert v2_cfg.distress_rank(t["worst_mood"]) == max(v2_cfg.distress_rank(c) for c in cats)
                if len(set(cats)) > 1:
                    assert t["worst_mood"] != "positive_uplifted"


def test_week_is_notable_exactly_when_an_anchor_crossed(v2_all):
    for w in v2_all["week"].values():
        assert w["is_notable"] == bool(w["anchors_crossed"]) and (w["notable_reason"] is None) == (not w["anchors_crossed"])


def test_quiet_week_means_an_empty_material_list(v2_all):
    for w in v2_all["week"].values():
        assert w["quiet"] == (not w["material_changes"])


def test_golden_hospitalization_week_shows_sleep_down_adherence_down_resting_hr_up_glucose_up(v2_all):
    w = v2_all["week"]["week_ENDING_2025-11-22"]
    tags = {t["measure"]: t for t in w["tags"]}
    assert tags["sleep_duration"]["direction"] == "down" and tags["medication_adherence"]["direction"] == "down"
    assert tags["resting_heart_rate"]["direction"] == "up" and tags["cgm_glucose_reading"]["direction"] == "up"
    assert w["is_notable"] and w["anchors_crossed"]
    for text in ("Father hospitalized overnight - chest pain and weakness", "Hospital day 2, coordinating care and family logistics"):
        assert f'"{text}"' in w["deviation_text"]
    assert "Diary, 2025-11-18" in w["deviation_text"] and any(i["kind"] == "missed_dose" for i in w["material_changes"])


def test_golden_599_week_is_not_notable_and_lists_the_removed_reading(v2_all):
    w = v2_all["week"]["week_ENDING_2025-12-09"]
    assert not w["is_notable"] and w["anchors_crossed"] == [] and "severe_range_appeared_or_cleared" in w["anchors_questionable"]
    assert any(i["kind"] == "questionable_reading_removed" and i["value"] == 599.0 for i in w["material_changes"]) and "Reading removed: 599" in w["deviation_text"]
    assert w["facts"]["glucose"]["max_value"] < 400
    for k in range(7):                                   # every week that contains the 599 day: the reading never makes it notable
        wk = v2_all["week"][f"week_ENDING_{(date(2025, 12, 9) + timedelta(days=k)).isoformat()}"]
        assert "severe_range_appeared_or_cleared" not in wk["anchors_crossed"] and any(i["kind"] == "questionable_reading_removed" for i in wk["material_changes"])


# ---- month tier -----------------------------------------------------------------------------------------------------------------------

def test_month_checkpoints_every_30_days_plus_the_final_partial_one(v2_all):
    months = [v2_all["month"][m] for m in sorted(v2_all["month"])]
    days = sorted(v2_all["day"])
    assert len(months) == 12 and months[0]["end_date"] == days[29].replace("day_", "") and months[-1]["end_date"] == days[-1].replace("day_", "")
    assert [m["facts"]["partial"] for m in months] == [False] * 11 + [True] and months[0]["gist_status"] == "code_line_early" and months[1]["gist_status"] != "code_line_early"


def test_cumulative_and_last_30_day_metrics_are_computed_on_cleaned_readings(v2_all, v2_cfg, pipeline_run):
    _, db = pipeline_run
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    kept, _ = clean_series(StoreView(ro, v2_cfg).glucose_series, v2_cfg)
    ro.close()
    dates = sorted(v2_all["day"])
    for m in v2_all["month"].values():
        end = m["end_date"]
        upto = [r.value for r in kept if r.dt.date().isoformat() <= end]
        c = glucose_metrics(upto, 96 * (dates.index(f"day_{end}") + 1))
        assert (m["facts"]["cumulative"]["mean"], m["facts"]["cumulative"]["tir_pct"], m["facts"]["cumulative"]["cv_pct"]) == (c["mean"], c["tir_pct"], c["cv_pct"]), end
        start30 = (date.fromisoformat(end) - timedelta(days=29)).isoformat()
        l30 = glucose_metrics([r.value for r in kept if start30 <= r.dt.date().isoformat() <= end], 96 * 30)
        assert m["facts"]["last_30_days"]["mean"] == l30["mean"] and m["facts"]["last_30_days"]["tir_pct"] == l30["tir_pct"], end


def test_lab_link_lists_only_labs_up_to_the_checkpoint_with_a_signed_gap_and_the_anchor_follows(v2_all, v2_cfg):
    for m in v2_all["month"].values():
        links = m["facts"]["lab_link"]
        assert all(l["lab_date"] <= m["end_date"] for l in links)
        for l in links:
            if l["gmi_90d_prior"] is not None:
                assert l["gap_hba1c_minus_gmi"] == round(l["hba1c_pct"] - l["gmi_90d_prior"], 2)
        recent = [l["gap_hba1c_minus_gmi"] for l in links if l["gap_hba1c_minus_gmi"] is not None and l["lab_date"] > (date.fromisoformat(m["end_date"]) - timedelta(days=30)).isoformat()]
        fires = bool(recent) and max(abs(g) for g in recent) >= 0.5
        assert ("lab_cgm_discordance" in m["anchors_crossed"]) == fires, m["window_id"]
    assert any("lab_cgm_discordance" in m["anchors_crossed"] for m in v2_all["month"].values())


def test_chronic_findings_are_as_of_the_checkpoint_and_at_least_the_configured_share(v2_all, v2_cfg):
    day_rows = [v2_all["day"][w] for w in sorted(v2_all["day"])]
    for m in v2_all["month"].values():
        hist = {}
        for d in day_rows:
            if d["end_date"] <= m["end_date"]:
                for s, st in d["facts"]["statuses"].items():
                    if st:
                        hist.setdefault(s, []).append(st)
        assert m["facts"]["chronic_findings"] == chronic_findings(hist, v2_cfg), m["window_id"]
        assert all(f["share_pct"] >= v2_cfg.chronic_min_share_pct for f in m["facts"]["chronic_findings"])
    last = v2_all["month"][sorted(v2_all["month"])[-1]]["facts"]["chronic_findings"]
    assert "step_count" in {f["measure"] for f in last}                      # found without being told: her steps are non-normal almost every day


def test_month_notable_follows_anchors_and_the_month_has_a_monthly_trajectory(v2_all):
    for m in v2_all["month"].values():
        assert m["is_notable"] == bool(m["anchors_crossed"])
        months = [x["month"] for x in m["facts"]["monthly_trajectory"]]
        assert months == sorted(months) and months[-1] == m["end_date"][:7] and m["facts"]["monthly_trajectory"][-1]["partial"] is True
        assert "MONTH BY MONTH" in m["deviation_text"] and "CHRONIC FINDINGS" in m["deviation_text"]


# ---- as-of and cleaning, for all tiers -------------------------------------------------------------------------------------------------------

def test_no_week_or_month_depends_on_data_after_its_end_date(v2_all, v2_cfg, pipeline_run, tmp_path):
    _, db = pipeline_run
    cutoff = "2026-04-30"
    copy = tmp_path / "trunc.db"
    shutil.copy(db, copy)
    c = sqlite3.connect(copy)
    c.execute("DELETE FROM raw_events WHERE substr(timestamp, 1, 10) > ?", (cutoff,))
    c.execute("DELETE FROM context_events WHERE date > ?", (cutoff,))
    c.commit()
    c.close()
    ro = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    short = build_windows(v2_cfg, StoreView(ro, v2_cfg))
    ro.close()
    n = 0
    for tier in ("week", "month"):
        for r in short[tier]:
            if r["window_id"] in v2_all[tier]:
                n += 1
                assert json.dumps(r, sort_keys=True, default=str) == json.dumps(v2_all[tier][r["window_id"]], sort_keys=True, default=str), r["window_id"]
    assert n > 100


def test_a_removed_reading_moves_nothing_in_the_week_or_month_tiers_either(v2_all, v2_cfg, pipeline_run, tmp_path):
    _, db = pipeline_run
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    _, removed = clean_series(StoreView(ro, v2_cfg).glucose_series, v2_cfg)
    ro.close()
    copy = tmp_path / "without_removed.db"
    shutil.copy(db, copy)
    c = sqlite3.connect(copy)
    for rm in removed:
        c.execute("DELETE FROM raw_events WHERE biomarker = 'cgm_glucose_reading' AND timestamp = ? AND value = ?", (rm.ts, rm.value))
    c.commit()
    c.close()
    ro = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    rebuilt = build_windows(v2_cfg, StoreView(ro, v2_cfg))
    ro.close()
    for tier in ("week", "month"):
        for b in rebuilt[tier]:
            r = v2_all[tier][b["window_id"]]
            for key in ("tags", "co_movement", "anchors_crossed", "is_notable", "notable_reason", "reliable", "confidence"):
                assert r[key] == b[key], (b["window_id"], key)
            assert r["facts"]["glucose" if tier == "week" else "cumulative"] == b["facts"]["glucose" if tier == "week" else "cumulative"]


# ---- the fixture patient: config only ------------------------------------------------------------------------------------------------------------

def test_the_fixture_patient_runs_the_week_and_month_tiers_with_config_alone(v2_fixture_all):
    cfg, all_ = v2_fixture_all
    assert len(all_["day"]) == 40 and len(all_["week"]) == 34 and sorted(all_["month"]) == ["month_ENDING_2026-01-30", "month_ENDING_2026-02-09"]
    w = all_["week"]["week_ENDING_2026-02-01"]
    assert {t["measure"] for t in w["tags"]} == {"cgm_glucose_reading", "time_in_range", "variability", "sleep_duration", "step_count", "medication_adherence"}
    assert any(i["kind"] == "missed_dose" and i["medicine"] == "rx_02_statin" and i["days"] == 1 and i["of"] == 7 for i in w["material_changes"])
    assert "Missed dose: statin, 1 of 7 days." in w["deviation_text"]
    assert all_["month"]["month_ENDING_2026-01-30"]["facts"]["lab_link"] == []                      # no lab biomarker in this patient's store
