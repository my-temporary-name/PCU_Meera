"""Stage D prerequisites: the four wording/view tweaks and the full-run driver (stop rules, resume, checkpoint). Offline: a fake client only."""

import json
import re
import shutil
from types import SimpleNamespace

import pytest

from v0_code.baseline_v2.gist_check import check_gist
from v0_code.baseline_v2.gist_view import build_gist_view, usual_places, wording_tags
from test_v2_gist import T, _row, GLU_TAG, SLEEP_TAG, M_ANCHOR, M_DIARY_MILD, M_DIARY_SEV, M_MISSED, M_LARGE, M_STATUS


# ---- 1. top_items order -----------------------------------------------------------------------------------------------------------------------

def test_top_items_order_is_diary_then_missed_then_changes_then_status(v2_cfg):
    rhr = T("resting_heart_rate", "resting heart rate", "up", "large")
    row = _row(tags=[SLEEP_TAG, GLU_TAG, rhr], anchors_crossed=["sleep_hours_change", "glucose_GMI_change"],
               material_changes=[M_ANCHOR, {"kind": "anchor_crossed", "anchor": "glucose_GMI_change"}, M_MISSED, M_DIARY_SEV, M_STATUS, M_LARGE])
    items = build_gist_view(v2_cfg, row)["top_items"]
    assert [i.split(":")[0].split(" (")[0] for i in items] == ["diary entry", "missed medicines", "notable or large changes"]


def test_the_status_item_is_fourth_so_it_appears_only_when_a_kind_above_it_is_absent(v2_cfg):
    row = _row(tags=[SLEEP_TAG], material_changes=[M_MISSED, M_STATUS, M_LARGE])
    assert [i.split(":")[0] for i in build_gist_view(v2_cfg, row)["top_items"]] == ["missed medicines", "notable or large changes", "unusual statuses"]


def test_anchors_and_large_changes_are_one_item_ordered_by_size_large_first(v2_cfg):
    rhr = T("resting_heart_rate", "resting heart rate", "up", "large")
    glu = T("cgm_glucose_reading", "average glucose", "up", "moderate")
    row = _row(tags=[glu, SLEEP_TAG, rhr], anchors_crossed=["glucose_GMI_change", "sleep_hours_change"],
               material_changes=[{"kind": "anchor_crossed", "anchor": "glucose_GMI_change"}, {"kind": "anchor_crossed", "anchor": "sleep_hours_change"},
                                 {"kind": "large_change", "measure": "resting_heart_rate", "label": "resting heart rate", "direction": "up", "direction_word": "up", "size": "large"}])
    (item,) = build_gist_view(v2_cfg, row)["top_items"]
    assert item == "notable or large changes: sleep down (large); resting heart rate up (large); average glucose up (moderate)"


def test_a_change_with_no_tag_such_as_the_lab_difference_leads_the_changes_item(v2_cfg):
    row = _row(tags=[SLEEP_TAG], anchors_crossed=["lab_cgm_discordance", "sleep_hours_change"], material_changes=[{"kind": "anchor_crossed", "anchor": "sleep_hours_change"}, {"kind": "anchor_crossed", "anchor": "lab_cgm_discordance"}])
    (item,) = build_gist_view(v2_cfg, row)["top_items"]
    assert item.startswith("notable or large changes: HbA1c and the glucose-based estimate differ; sleep down (large)")


def test_on_the_golden_week_the_diary_leads_then_missed_doses_then_the_changes(v2_stored, v2_cfg):
    w = next(r for r in v2_stored[0]["week"] if r["window_id"] == "week_ENDING_2025-11-22")
    items = build_gist_view(v2_cfg, w)["top_items"]
    assert items[0].startswith("diary entry (severe") and items[1].startswith("missed medicines") and items[2].startswith("notable or large changes: sleep down (large)")


# ---- 2. "average glucose" -----------------------------------------------------------------------------------------------------------------

def test_glucose_is_called_average_glucose_in_the_view_the_tags_and_the_checker(v2_cfg, v2_stored):
    assert v2_cfg.measure_name("cgm_glucose_reading") == "average glucose" and v2_cfg.stream("cgm_glucose_reading").display == "average glucose"
    w = next(r for r in v2_stored[0]["week"] if r["window_id"] == "week_ENDING_2025-11-22")
    assert next(t for t in w["tags"] if t["measure"] == "cgm_glucose_reading")["label"] == "average glucose"
    view = build_gist_view(v2_cfg, w)
    names = [m["measure"] for m in view["measures"]] + view["moved_the_same_way_as_glucose"] + view["moved_the_opposite_way_to_glucose"]
    assert "average glucose" in names and "glucose" not in names
    tags = [T("cgm_glucose_reading", "average glucose", "up", "moderate")]
    for s in ("Average glucose rose clearly.", "Glucose rose clearly.", "Estimated glucose rose clearly."):
        assert check_gist(v2_cfg, {"headline": "H", "sentences": [s, "Nothing else."]}, tags, []) == [], s
    assert check_gist(v2_cfg, {"headline": "H", "sentences": ["Average glucose fell clearly.", "Nothing else."]}, tags, [])


# ---- 3. size floor for an anchor-crossed measure ------------------------------------------------------------------------------------------------

def test_a_measure_that_crossed_an_anchor_is_worded_at_least_moderate_but_the_stored_tag_is_unchanged(v2_cfg):
    steps = T("step_count", "steps", "up", "small")
    row = _row(tags=[steps, GLU_TAG], anchors_crossed=["steps_abs_change"], material_changes=[{"kind": "anchor_crossed", "anchor": "steps_abs_change"}])
    view = build_gist_view(v2_cfg, row)
    assert {"measure": "steps", "direction": "up", "size": "moderate"} in view["measures"] and "steps up (moderate)" in view["top_items"][0]
    assert row["tags"][0]["size"] == "small"                                                        # stored tag untouched
    assert [t["size"] for t in wording_tags(row)] == ["moderate", "moderate"]
    big = T("sleep_duration", "sleep", "down", "large")
    assert wording_tags(_row(tags=[big], anchors_crossed=["sleep_hours_change"]))[0]["size"] == "large"                # never lowered
    assert wording_tags(_row(tags=[steps], anchors_crossed=[]))[0]["size"] == "small"                                  # no anchor, no floor


def test_the_checker_asks_for_clearly_for_a_floored_measure(v2_cfg):
    steps = T("step_count", "steps", "up", "small")
    row = _row(tags=[steps], anchors_crossed=["steps_abs_change"])
    ok = {"headline": "H", "sentences": ["Steps rose clearly.", "Nothing else."]}
    low = {"headline": "H", "sentences": ["Steps rose slightly.", "Nothing else."]}
    assert check_gist(v2_cfg, ok, wording_tags(row), []) == []
    assert [f["check"] for f in check_gist(v2_cfg, low, wording_tags(row), [])] == ["direction_size"]
    assert check_gist(v2_cfg, low, row["tags"], []) == []                                          # without the floor "slightly" was right


# ---- 4. hygiene -------------------------------------------------------------------------------------------------------------------------------

def test_reliability_is_mentioned_only_when_the_window_is_not_reliable(v2_cfg):
    assert "reliable" not in build_gist_view(v2_cfg, _row(material_changes=[M_MISSED]))
    assert build_gist_view(v2_cfg, _row(reliable=False, material_changes=[M_MISSED]))["reliable"] == "no"


def test_usual_places_are_her_two_most_frequent_before_the_window(v2_cfg):
    hist = [("2026-01-01", "home_wfh"), ("2026-01-02", "home_wfh"), ("2026-01-03", "office"), ("2026-01-04", "office"), ("2026-01-05", "home"), ("2026-01-06", "hospital"), ("2026-01-09", "hospital"), ("2026-01-10", "hospital")]
    assert usual_places(v2_cfg, hist, "2026-01-07") == {"home_wfh", "office"}                       # only days strictly before 2026-01-07
    assert usual_places(v2_cfg, hist, "2026-01-11") == {"hospital", "home_wfh"}                     # hospital 3, then home_wfh and office tie on 2: the name breaks the tie
    assert usual_places(v2_cfg, hist, "2026-01-01") == set()                                         # no history: nothing is "usual" yet


def test_a_place_is_listed_only_when_it_is_not_usual(v2_stored, v2_cfg):
    w = next(r for r in v2_stored[0]["week"] if r["window_id"] == "week_ENDING_2025-11-22")
    both = build_gist_view(v2_cfg, w, usual_places=set())["places"]
    only = build_gist_view(v2_cfg, w, usual_places={"office"})["places"]
    assert {"place": "office", "how_often": "on one day"} in both and not any(p["place"] == "office" for p in only) and any(p["place"] == "hospital" for p in only)
    assert "places" not in build_gist_view(v2_cfg, w, usual_places={"office", "hospital", "home"})


def test_hba1c_passes_the_digit_check_but_other_digits_do_not(v2_cfg):
    tags = [T("sleep_duration", "sleep", "down", "large")]
    ok = {"headline": "HbA1c is higher than the glucose-based estimate.", "sentences": ["Sleep fell markedly.", "The hba1c differs."]}
    assert check_gist(v2_cfg, ok, tags, []) == []
    assert [f["check"] for f in check_gist(v2_cfg, {"headline": "H", "sentences": ["HbA1c was seen on 3 days.", "Sleep fell markedly."]}, tags, [])] == ["forbidden_content"]


def test_the_month_lab_line_says_hba1c(v2_stored, v2_cfg):
    m = next(r for r in v2_stored[0]["month"] if r["window_id"] == "month_ENDING_2025-12-29")
    view = build_gist_view(v2_cfg, m)
    assert view["lab_vs_glucose_estimate"] == "HbA1c is higher than the glucose-based estimate (they differ)"
    assert any(i.startswith("notable or large changes: HbA1c and the glucose-based estimate differ") for i in view["top_items"])


# ---- Stage D driver -------------------------------------------------------------------------------------------------------------------------------

from v0_code.baseline_v2 import stage_d as D
from v0_code.baseline_v2.storage import MemoryV2Store

NEUTRAL = json.dumps({"headline": "Nothing stood out much this time", "sentences": ["She felt fine.", "Nothing else to add."]})
ONE_ITEM = json.dumps({"headline": "Nothing stood out", "sentences": ["She felt fine. Nothing else to add."]})
BAD_DIR = json.dumps({"headline": "Nothing stood out", "sentences": ["Hydration fell a little while hydration rose a lot.", "Nothing else to add."]})


class Auto:
    """A client whose answer comes from fn(messages, call_number)."""
    def __init__(self, fn):
        self.fn, self.n = fn, 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.n += 1
        r = self.fn(kw["messages"], self.n)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=r))],
                               usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, completion_tokens_details=SimpleNamespace(reasoning_tokens=20)))


def _fresh(v2_stored, tmp_path, tiers=("day", "week", "month")):
    db = tmp_path / "d.db"
    shutil.copy(v2_stored[1], db)
    store = MemoryV2Store(db)
    rows = {t: [store.get_memory(t, r["end_date"], full=True) for r in v2_stored[0][t]] for t in tiers}
    return store, rows


def small(cfg, day=40, week=6, month=2):
    """Cut the work down for a test: the first n pending windows per tier."""
    return {"day": day, "week": week, "month": month}


def test_the_driver_runs_day_then_week_then_month_and_saves_every_window(v2_cfg, v2_stored, tmp_path):
    store, rows = _fresh(v2_stored, tmp_path)
    for t, n in (("day", 12), ("week", 5), ("month", 2)):
        for r in [x for x in rows[t] if x["gist"]["status"] is None][n:]:
            store.save_gist(r["window_id"], "Parked.", [], "code_line_quiet")                      # leave only the first n pending
    rows = {t: [store.get_memory(t, r["end_date"], full=True) for r in v2_stored[0][t]] for t in rows}
    order = []
    cli = Auto(lambda msgs, n: (order.append(re.search(r"TIER: (\w+)", msgs[1]["content"]).group(1)), NEUTRAL)[1])
    summary = D.run_stage_d(v2_cfg, store, rows, cli, batch_size={"day": 1, "week": 1, "month": 1}, min_sample=5, log=lambda e: None, say=lambda s: None)
    assert order == ["day"] * 12 + ["week"] * 5 + ["month"] * 2 and summary["stopped"] is None
    assert store.conn.execute("SELECT COUNT(*) FROM memory_v2 WHERE gist_status='gist_ok'").fetchone()[0] == 19


def test_a_second_run_does_nothing_and_an_interrupted_run_resumes(v2_cfg, v2_stored, tmp_path):
    store, rows = _fresh(v2_stored, tmp_path, tiers=("day",))
    for r in [x for x in rows["day"] if x["gist"]["status"] is None][6:]:
        store.save_gist(r["window_id"], "Parked.", [], "code_line_quiet")
    rows = {"day": [store.get_memory("day", r["end_date"], full=True) for r in v2_stored[0]["day"]], "week": [], "month": []}
    cli = Auto(lambda m, n: NEUTRAL)
    D.run_stage_d(v2_cfg, store, rows, cli, batch_size={"day": 1, "week": 1, "month": 1}, min_sample=5, log=lambda e: None, say=lambda s: None, stop_after_windows=3)
    assert cli.n == 3
    rows = {"day": [store.get_memory("day", r["end_date"], full=True) for r in v2_stored[0]["day"]], "week": [], "month": []}
    D.run_stage_d(v2_cfg, store, rows, cli, batch_size={"day": 1, "week": 1, "month": 1}, min_sample=5, log=lambda e: None, say=lambda s: None)
    assert cli.n == 6                                                                                  # only the three left were sent
    rows = {"day": [store.get_memory("day", r["end_date"], full=True) for r in v2_stored[0]["day"]], "week": [], "month": []}
    D.run_stage_d(v2_cfg, store, rows, cli, batch_size={"day": 1, "week": 1, "month": 1}, min_sample=5, log=lambda e: None, say=lambda s: None)
    assert cli.n == 6                                                                                  # idempotent: nothing pending, nothing sent


def test_first_attempt_failure_above_25_percent_in_a_tier_stops_the_run(v2_cfg, v2_stored, tmp_path):
    store, rows = _fresh(v2_stored, tmp_path, tiers=("day",))
    rows["week"], rows["month"] = [], []
    # every first attempt is a structure failure; the retry is fine, so there are no fallbacks, only first-attempt failures
    cli = Auto(lambda msgs, n: ONE_ITEM if len(msgs) == 2 else NEUTRAL)
    s = D.run_stage_d(v2_cfg, store, rows, cli, batch_size={"day": 1, "week": 1, "month": 1}, min_sample=10, wave={"day": 5, "week": 5, "month": 5}, log=lambda e: None, say=lambda s: None)
    assert s["stopped"] and "first-attempt failure" in s["stopped"] and "day" in s["stopped"]
    assert s["tiers"]["day"]["attempted"] == 10                                                          # stopped at the first wave boundary at or after the minimum sample


def test_fallbacks_above_10_percent_switch_the_sentence_check_to_warn_and_the_run_continues(v2_cfg, v2_stored, tmp_path):
    store, rows = _fresh(v2_stored, tmp_path, tiers=("day",))
    rows["week"], rows["month"] = [], []
    pend = [x for x in rows["day"] if x["gist"]["status"] is None]
    for r in pend[30:]:
        store.save_gist(r["window_id"], "Parked.", [], "code_line_quiet")
    rows["day"] = [store.get_memory("day", r["end_date"], full=True) for r in v2_stored[0]["day"]]
    cli = Auto(lambda msgs, n: BAD_DIR)                                                                  # fails the strict direction check, twice per window
    events = []
    s = D.run_stage_d(v2_cfg, store, rows, cli, batch_size={"day": 1, "week": 1, "month": 1}, min_sample=10, wave={"day": 5, "week": 5, "month": 5},
                      stop_first_attempt_rate=1.01, log=lambda e: None, say=events.append)
    assert s["mode_switched_at"] is not None and s["tiers"]["day"]["attempted"] == 30
    assert s["tiers"]["day"]["fallbacks"] == 10 and s["tiers"]["day"]["warnings"] >= 20                 # 10 windows fell back in strict mode, then the rest were accepted with warnings
    assert any("warn" in e.lower() and "switch" in e.lower() for e in events)
    assert s["stopped"] is None


def test_an_accepted_entry_with_a_digit_or_date_stops_the_run():
    assert D.audit_entry({"headline": "Fine.", "sentences": ["One.", "Two."]}) == []
    assert D.audit_entry({"headline": "Fine.", "sentences": ["Seen on 3 days.", "Two."]})
    assert D.audit_entry({"headline": "Seen in November.", "sentences": ["One.", "Two."]})
    assert D.audit_entry({"headline": "HbA1c is higher.", "sentences": ["One.", "Two."]}) == []


def test_a_checkpoint_of_five_entries_is_printed_once_after_the_first_forty_day_windows(v2_cfg, v2_stored, tmp_path):
    store, rows = _fresh(v2_stored, tmp_path, tiers=("day",))
    rows["week"], rows["month"] = [], []
    for r in [x for x in rows["day"] if x["gist"]["status"] is None][60:]:
        store.save_gist(r["window_id"], "Parked.", [], "code_line_quiet")
    rows["day"] = [store.get_memory("day", r["end_date"], full=True) for r in v2_stored[0]["day"]]
    out = []
    D.run_stage_d(v2_cfg, store, rows, Auto(lambda m, n: NEUTRAL), batch_size={"day": 1, "week": 1, "month": 1}, min_sample=10, wave={"day": 20, "week": 12, "month": 6},
                  log=lambda e: None, say=out.append, checkpoint_after=40)
    cps = [o for o in out if "CHECKPOINT" in o]
    assert len(cps) == 1 and cps[0].count("headline:") == 5


def test_reset_gists_returns_only_model_written_gists_to_pending(v2_stored, tmp_path):
    store, rows = _fresh(v2_stored, tmp_path, tiers=("day",))
    pend = [x for x in rows["day"] if x["gist"]["status"] is None][:3]
    for r, st in zip(pend, ("gist_ok", "gist_retry_ok", "code_line_fallback")):
        store.save_gist(r["window_id"], "H.", ["a", "b"], st, "[]", [])
    quiet = next(x for x in rows["day"] if x["gist"]["status"] == "code_line_quiet")
    assert store.reset_gists() == 3
    assert all(store.get_memory("day", r["end_date"])["gist"]["status"] is None for r in pend)
    assert store.get_memory("day", quiet["end_date"])["gist"]["status"] == "code_line_quiet"            # code lines untouched


def test_the_report_reads_only_the_call_logs_not_the_run_summary_file(tmp_path):
    (tmp_path / "gist_stage_d_100.jsonl").write_text(json.dumps({"window_id": "day_x", "attempt": 1}) + "\n")
    (tmp_path / "gist_stage_d_runs.jsonl").write_text(json.dumps({"stamp": 1, "seconds": 2}) + "\n")
    assert D._read_logs(str(tmp_path)) == [{"window_id": "day_x", "attempt": 1}]
