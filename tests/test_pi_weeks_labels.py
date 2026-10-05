"""PI: calendar weeks (ISO names, patient timezone), the week label rule with partial weeks, and the reading of the Evidence store's daily labels."""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from v0_code.pi_engine.labels import EvidenceLabels, LabelCfg, WeekCounts, needed_days, week_label
from v0_code.pi_engine.weeks import Week, days_present, week_end_time, week_of, week_of_date, weeks_between

IST = ZoneInfo("Asia/Kolkata")
CFG = LabelCfg(days_needed=5, of=7, min_days=4, scale=True)


# ---- weeks ---------------------------------------------------------------------------------------------------------------------------------------------------
def test_a_week_is_monday_to_sunday_with_an_iso_name():
    w = week_of_date(date(2026, 9, 17))
    assert (w.iso, w.start, w.end) == ("2026-W38", date(2026, 9, 14), date(2026, 9, 20))
    assert week_of_date(date(2025, 11, 18)).iso == "2025-W47" and week_of_date(date(2025, 10, 1)).iso == "2025-W40"
    assert week_of_date(date(2025, 12, 29)).iso == "2026-W01"                                      # ISO year, not calendar year
    assert week_of_date(date(2026, 1, 4)).end == date(2026, 1, 4) and week_of_date(date(2026, 1, 5)).start == date(2026, 1, 5)


def test_an_entry_belongs_to_the_week_of_its_as_of_in_the_patients_timezone():
    assert week_of("2026-09-13T23:30:00+05:30", IST).iso == "2026-W37"                              # Sunday evening
    assert week_of("2026-09-14T00:10:00+05:30", IST).iso == "2026-W38"
    assert week_of("2026-09-13T20:00:00+00:00", IST).iso == "2026-W38"                              # 01:30 on Monday in the patient's zone
    assert week_of("2026-09-13T20:00:00+00:00", ZoneInfo("UTC")).iso == "2026-W37"


def test_the_weekly_job_time_is_the_end_of_sunday_in_the_patients_zone():
    t = week_end_time(week_of_date(date(2026, 9, 14)), IST)
    assert t.isoformat() == "2026-09-20T23:59:59+05:30"


def test_weeks_between_is_inclusive_and_ordered():
    ws = weeks_between(week_of_date(date(2025, 10, 1)), week_of_date(date(2025, 10, 22)))
    assert [w.iso for w in ws] == ["2025-W40", "2025-W41", "2025-W42", "2025-W43"]


def test_days_present_counts_only_days_inside_the_data_span():
    first, last = date(2025, 10, 1), date(2026, 9, 17)
    assert days_present(week_of_date(date(2025, 10, 1)), first, last) == 5                         # Wed to Sun
    assert days_present(week_of_date(date(2026, 9, 14)), first, last) == 4                         # Mon to Thu
    assert days_present(week_of_date(date(2026, 3, 2)), first, last) == 7


# ---- the week label ------------------------------------------------------------------------------------------------------------------------------------------
def counts(days, sup=0, sug=0, ns=0, ins=0, placebo=0, contrary=0):
    assert sup + sug + ns + ins == days
    return WeekCounts("w", days, sup, sug, ns, ins, placebo, contrary, days_with_record=days - ins)


@pytest.mark.parametrize("days,expected", [(7, 5), (6, 5), (5, 4), (4, 3)])
def test_the_threshold_scales_with_the_days_that_exist_rounded_up(days, expected):
    assert needed_days(days, 5, 7, CFG) == expected
    assert needed_days(7, 5, 7, LabelCfg(5, 7, 4, False)) == 5 and needed_days(4, 5, 7, LabelCfg(5, 7, 4, False)) == 5


@pytest.mark.parametrize("c,label", [
    (counts(7, sup=5, ns=2), "supported"), (counts(7, sup=4, ns=3), "not_supported"), (counts(7, sup=3, sug=2, ns=2), "suggestive"), (counts(7, sup=1, ins=6), "insufficient"),
    (counts(7, ins=5, ns=2), "insufficient"), (counts(7, sup=2, sug=2, ns=3), "not_supported"),
    (counts(5, sup=4, ns=1), "supported"), (counts(5, sup=3, ns=2), "not_supported"), (counts(5, sup=2, sug=2, ns=1), "suggestive"),
    (counts(4, sup=3, ns=1), "supported"), (counts(4, sup=2, ns=2), "not_supported"), (counts(4, ins=3, ns=1), "insufficient"),
    (counts(3, sup=3), "insufficient"), (counts(2, sup=2), "insufficient"), (counts(1, ns=1), "insufficient")])
def test_the_week_label_rule(c, label):
    assert week_label(c, CFG) == label


def test_a_week_with_fewer_than_four_days_is_never_decisive():
    assert week_label(counts(3, sup=3), CFG) == "insufficient" and week_label(counts(3, ns=3), CFG) == "insufficient"


# ---- the Evidence store's daily labels -------------------------------------------------------------------------------------------------------------------------
@pytest.fixture()
def evidence(tmp_path):
    p = tmp_path / "ev.db"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE relationship_evidence (id INTEGER PRIMARY KEY AUTOINCREMENT, evidence_id TEXT, relationship_key TEXT, as_of_date TEXT, method_version TEXT, config_version TEXT, inputs_hash TEXT, status TEXT, record_json TEXT)")
    import json
    rows = []
    d0 = date(2026, 3, 2)
    for i in range(14):
        d = date.fromordinal(d0.toordinal() + i)
        for key, sup, flags in (("a@1d->x", "supported" if i != 3 else "suggestive", ["same_day_unverified"] + (["placebo_fired"] if i in (1, 2) else [])), ("b@1d->x", "not_supported", ["contrary"] if i < 5 else [])):
            rows.append((f"rel|{key}|{d.isoformat()}|ev-v0", key, d.isoformat(), "ev-v0", "c", f"h{i}", "current", json.dumps({"support": sup, "flags": flags, "as_of_date": d.isoformat()})))
    c.executemany("INSERT INTO relationship_evidence (evidence_id, relationship_key, as_of_date, method_version, config_version, inputs_hash, status, record_json) VALUES (?,?,?,?,?,?,?,?)", rows)
    c.execute("INSERT INTO relationship_evidence (evidence_id, relationship_key, as_of_date, method_version, config_version, inputs_hash, status, record_json) VALUES ('rel|a@1d->x|2026-03-02|ev-v0','a@1d->x','2026-03-02','ev-v0','c','old','superseded','{\"support\":\"insufficient\",\"flags\":[]}')")
    c.commit()
    c.close()
    return EvidenceLabels(p)


def test_the_span_and_first_day_come_from_the_evidence_records(evidence):
    assert evidence.span() == (date(2026, 3, 2), date(2026, 3, 15)) and evidence.first_day("a@1d->x") == date(2026, 3, 2) and evidence.first_day("nope") is None


def test_week_counts_read_the_current_records_by_date_and_count_missing_days_as_insufficient(evidence):
    span = evidence.span()
    c = evidence.week_counts("a@1d->x", week_of_date(date(2026, 3, 2)), span)
    assert (c.days_in_week, c.supported, c.suggestive, c.not_supported, c.insufficient, c.placebo_days, c.contrary_days, c.days_with_record) == (7, 6, 1, 0, 0, 2, 0, 7)
    b = evidence.week_counts("b@1d->x", week_of_date(date(2026, 3, 2)), span)
    assert (b.not_supported, b.contrary_days) == (7, 5)
    partial = evidence.week_counts("a@1d->x", week_of_date(date(2026, 3, 16)), (date(2026, 3, 2), date(2026, 3, 17)))          # two days that exist but have no record
    assert partial.days_in_week == 2 and partial.insufficient == 2 and partial.days_with_record == 0


def test_the_evidence_ref_of_a_week_is_the_last_day_with_a_record(evidence):
    w = week_of_date(date(2026, 3, 9))
    assert evidence.last_record_id("a@1d->x", w, w.end) == "rel|a@1d->x|2026-03-15|ev-v0"
    assert evidence.last_record_id("a@1d->x", w, date(2026, 3, 12)) == "rel|a@1d->x|2026-03-12|ev-v0"       # never a day after the cut-off
    assert evidence.last_record_id("a@1d->x", week_of_date(date(2026, 4, 6)), date(2026, 4, 12)) is None


def test_reads_are_cut_at_a_date_so_a_later_label_never_leaks_in(evidence):
    span = (date(2026, 3, 2), date(2026, 3, 8))
    c = evidence.week_counts("a@1d->x", week_of_date(date(2026, 3, 2)), span, until=date(2026, 3, 4))
    assert c.days_in_week == 3 and c.supported + c.suggestive + c.not_supported + c.insufficient == 3 and c.supported == 3 and c.suggestive == 0
