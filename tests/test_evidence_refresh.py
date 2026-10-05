"""Evidence Engine, Stage 2a: the history table (ordering, anchoring, availability, detrending) and the daily refresh, on a synthetic second patient with other stream
names, another time zone, other meal kinds and block names, its own rulebook and library (see tests/evidence_synth.py). Nothing here knows the first patient."""

import hashlib
import json
import math
import shutil
import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pytest

import evidence_synth as syn
from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.library import LibraryError
from v0_code.evidence_engine.loader import load_data
from v0_code.evidence_engine.refresh import DailyRefresh
from v0_code.evidence_engine.storage import EvidenceStore
from v0_code.evidence_engine.units import Unit, detrend

N_DAYS = 240
LAST = syn.START + timedelta(days=N_DAYS - 1)


@pytest.fixture(scope="module")
def patient(tmp_path_factory):
    d = tmp_path_factory.mktemp("synth")
    return d, syn.make_patient(d, n_days=N_DAYS)


def engine(cfg_path, store=None):
    cfg = EvidenceConfig.from_yaml(cfg_path, Path(cfg_path).parent)
    lib, data, conn = load_data(cfg, Path(cfg_path).parent)
    return cfg, lib, data, conn, DailyRefresh(data, lib, cfg, store)


@pytest.fixture(scope="module")
def last_day(patient):
    d, cfgp = patient
    cfg, lib, data, conn, ref = engine(cfgp)
    recs, summary = ref.compute(LAST)
    return {r["relationship_key"]: r for r in recs}, summary, (cfg, lib, data, conn, ref)


# ---- loading ---------------------------------------------------------------------------------------------------------------------------------------
def test_second_patient_loads_through_the_library_check(patient):
    engine(patient[1])


def test_library_check_runs_at_load_and_fails_loudly(patient, tmp_path):
    d, _ = patient
    shutil.copytree(d, tmp_path / "p")
    p = tmp_path / "p"
    text = (p / "candidates.csv").read_text().replace("r_meal,3,secondary", "r_meal,3,primary")
    (p / "candidates.csv").write_text(text)
    (p / "evidence.yaml").write_text((p / "evidence.yaml").read_text().replace(str(d), str(p)))
    with pytest.raises(LibraryError) as e:
        engine(p / "evidence.yaml")
    assert "weight_tier" in str(e.value)


# ---- the daily refresh on the synthetic patient ------------------------------------------------------------------------------------------------------
def test_planted_relationships_are_found_and_nulls_are_not(last_day):
    recs, summary, _ = last_day
    for key in ("pill_skip@2d->day_level", "stress_block@1d->meal_peak:supper", "unwell_note@same_day->night_len", "steps_before@60m->hour_level"):
        r = recs[key]
        assert r["support"] in ("supported", "suggestive") and r["effect"] > 0.3, (key, r["support"], r["effect"])
    assert recs["rest_hours@prev_night->meal_peak:supper"]["support"] != "supported"
    assert recs["unwell_note@prev_day->day_level"]["support"] != "supported"


def test_one_record_per_relationship_with_meal_kinds_expanded(last_day):
    recs, summary, (cfg, lib, data, conn, ref) = last_day
    assert summary["n_relationships"] == len(recs) == 5 * 2 + 3 + 2 + 1                          # five meal pairs x two kinds, three day pairs, two night pairs, one hour pair
    assert {r["outcome_scope"].get("meal_kind") for r in recs.values() if r["outcome_id"] == "meal_peak"} == {"brunch", "supper"}
    assert ref.relationships(syn.START)[0][1] is None or ref.scopes(lib.runnable()[0], syn.START) == []        # on day one no meal kind has any history


def test_a_unit_with_no_ordered_exposure_is_insufficient(last_day):
    r = last_day[0]["stress_block@1d->meal_peak:brunch"]                        # the brunch starts before the first block has ended
    assert r["support"] == "insufficient" and r["insufficient_reason"] == "no_ordered_exposure" and r["history"]["n_units"] == 0


def test_flags_follow_the_ordering_and_the_groups(last_day):
    recs = last_day[0]
    assert "same_day_unverified" in recs["pill_skip@2d->day_level"]["flags"] and "same_day_unverified" in recs["stress_block@1d->day_level"]["flags"]
    assert "same_day_unverified" in recs["pill_skip@2d->meal_peak:supper"]["flags"]
    assert "same_day_unverified" not in recs["unwell_note@same_day->night_len"]["flags"] and "same_day_unverified" not in recs["stress_block@1d->meal_peak:supper"]["flags"]
    for r in recs.values():
        assert ("small_group" in r["flags"]) == (r["insufficient_reason"] == "small_group")


def test_insufficient_never_carries_a_p_value_or_a_positive_label(last_day):
    for r in last_day[0].values():
        if r["support"] == "insufficient":
            assert r["permutation"] is None and r["adjustment"] is None and r["effect"] is None


def test_adjusted_p_is_never_below_the_unadjusted_and_the_family_is_the_tested_set(last_day):
    recs, summary, _ = last_day
    tested = [r for r in recs.values() if r["permutation"]]
    assert summary["family_size"] == summary["n_tested"] == summary["placebo_tested"] == len(tested)
    assert all(r["adjustment"]["family_size"] == len(tested) and r["adjustment"]["p_adjusted"] >= r["permutation"]["p"] - 1e-6 for r in tested)
    assert summary["placebo_fired"] == sum(r["placebo"]["fired"] for r in tested)
    assert all(("placebo_fired" in r["flags"]) == r["placebo"]["fired"] for r in tested)
    assert all(not (r["placebo"]["fired"] and r["support"] == "supported") for r in tested)
    assert sum(summary["counts"].values()) == summary["n_relationships"]


def test_orientation_is_applied_consistently(last_day):
    recs = last_day[0]
    assert recs["unwell_note@same_day->night_len"]["orientation"] == {"outcome_worse_is": "lower", "exposure_risk_side": "exposed"}
    assert recs["unwell_note@same_day->night_len"]["effect"] > 0                       # an unwell day before shortens sleep: lower outcome is worse, exposure raises risk
    assert recs["unwell_note@same_day->night_len"]["raw_difference"] < 0               # the raw difference is in the outcome's own unit, so negative hours


def test_history_never_contains_the_outcome_date(last_day):
    for r in last_day[0].values():
        if r["history"] and r["history"]["last_day"]:
            assert r["history"]["last_day"] < LAST.isoformat()


# ---- the ordering, anchoring and availability rules, one by one ------------------------------------------------------------------------------------------
def units(ref, outcome, scope=None):
    return ref.units(outcome)[scope]


def test_block_counts_for_a_meal_unit_only_once_it_has_ended(patient, last_day):
    cfg, lib, data, conn, ref = last_day[2]
    expo, outcome = lib.exposures["stress_block"], lib.outcomes["meal_peak"]
    for u in units(ref, "meal_peak", "supper")[10:40]:
        v, why = ref.ev.value(expo, "1d", outcome, u, False)
        blocks = {r.block: r.category == "stressed" for r in data.by_date("mood")[u.date]}
        assert v == float(any(blocks.values())) and why is None                       # both blocks (11:00 and 17:00) ended before a supper at 18:45 or later
    for u in units(ref, "meal_peak", "brunch")[10:20]:
        assert ref.ev.value(expo, "1d", outcome, u, False) == (None, "unordered")      # nothing has ended before a brunch at about 10:00


def test_day_level_unit_counts_every_exposure_in_the_window_as_date_resolution(last_day):
    cfg, lib, data, conn, ref = last_day[2]
    expo, outcome = lib.exposures["stress_block"], lib.outcomes["day_level"]
    for u in units(ref, "day_level")[20:40]:
        v, why = ref.ev.value(expo, "1d", outcome, u, False)
        assert v == float(any(r.category == "stressed" for r in data.by_date("mood")[u.date]))             # the same date's blocks count, flagged by the library
    note = lib.exposures["unwell_note"]
    for u in units(ref, "day_level")[20:60]:
        v, _ = ref.ev.value(note, "prev_day", outcome, u, False)
        prev = u.date - timedelta(days=1)
        assert v == float(any(r.category == "unwell" for r in data.by_date("diary").get(prev, [])))


def test_a_meal_unit_ignores_diary_entries_after_its_start(last_day):
    cfg, lib, data, conn, ref = last_day[2]
    expo, outcome = lib.exposures["unwell_note"], lib.outcomes["meal_peak"]
    checked = 0
    for u in units(ref, "meal_peak", "brunch"):
        notes = [r for r in data.by_date("diary").get(u.date, []) if r.category == "unwell"]
        if notes and all(n.ts > u.start for n in notes) and not [r for d in (1, 2) for r in data.by_date("diary").get(u.date - timedelta(days=d), []) if r.category == "unwell"]:
            assert ref.ev.value(expo, "3d", outcome, u, False) == (0.0, None)         # an entry later the same day does not count for an earlier meal
            checked += 1
    assert checked > 0


def test_sleep_exposure_for_a_meal_is_the_latest_record_at_or_before_its_start(last_day):
    cfg, lib, data, conn, ref = last_day[2]
    expo, outcome = lib.exposures["rest_hours"], lib.outcomes["meal_peak"]
    for u in units(ref, "meal_peak", "supper")[:30]:
        v, _ = ref.ev.value(expo, "prev_night", outcome, u, False)
        assert v == data.by_date("sleep")[u.date][0].value                             # the 06:30 record of the same date: it ended before the meal


def test_the_hourly_exposure_is_the_row_stamped_one_hour_earlier(last_day):
    cfg, lib, data, conn, ref = last_day[2]
    expo, outcome = lib.exposures["steps_before"], lib.outcomes["hour_level"]
    by_ts = {r.ts: r.value for r in data.records("steps_hourly")}
    for u in units(ref, "hour_level")[500:520]:
        v, _ = ref.ev.value(expo, "60m", outcome, u, False)
        assert v == by_ts[u.start - timedelta(hours=1)]


def test_the_hourly_row_of_the_unit_s_own_hour_never_counts(last_day):
    cfg, lib, data, conn, ref = last_day[2]
    expo, outcome = lib.exposures["steps_before"], lib.outcomes["hour_level"]
    by_ts = {r.ts: r.value for r in data.records("steps_hourly")}
    u = next(x for x in units(ref, "hour_level") if x.hour == 12 and by_ts[x.start] != by_ts[x.start - timedelta(hours=1)])
    assert ref.ev.value(expo, "60m", outcome, u, False)[0] == by_ts[u.start - timedelta(hours=1)] != by_ts[u.start]


def test_the_shifted_window_counts_back_from_the_day_before(last_day):
    cfg, lib, data, conn, ref = last_day[2]
    expo, outcome = lib.exposures["unwell_note"], lib.outcomes["night_len"]
    for u in units(ref, "night_len")[20:80]:
        v, _ = ref.ev.value(expo, "same_day", outcome, u, False)
        assert v == float(any(r.category == "unwell" for r in data.by_date("diary").get(u.date - timedelta(days=1), [])))
    pill = lib.exposures["pill_skip"]
    for u in units(ref, "night_len")[20:40]:
        v, _ = ref.ev.value(pill, "1d", outcome, u, False)
        assert v == float(data.by_date("adherence")[u.date - timedelta(days=1)][0].text == "skipped")


def test_late_exposure_binarizes_at_the_as_of_quantile(last_day):
    cfg, lib, data, conn, ref = last_day[2]
    pair = next(p for p in lib.runnable() if p["exposure"] == "late_start")
    ser = ref.series(pair, "supper")
    h = ser.at(LAST, data.tz)
    assert h.threshold is not None and set(np.unique(h.x)) <= {0.0, 1.0}
    raw = ser.x_raw[:ser.n_complete_before(LAST, data.tz)]
    assert abs((raw >= h.threshold).mean() - 0.25) < 0.15


def test_a_meal_with_no_kind_has_no_units(patient, tmp_path):
    d, _ = patient
    def extra(readings, ctx):
        ctx.append(("food_log", f"{syn.START.isoformat()}T15:00:00+09:00", syn.START.isoformat(), "x", None, "tea_time", "{}"))
    cfgp = syn.make_patient(tmp_path / "k", n_days=40, extra=extra)
    cfg, lib, data, conn, ref = engine(cfgp)
    assert set(ref.units("meal_peak")) == {"brunch", "supper"}
    assert sum(len(v) for v in ref.units("meal_peak").values()) == 80


def test_a_late_meal_enters_the_history_one_day_late(tmp_path):
    day = syn.START + timedelta(days=100)
    def extra(readings, ctx):
        ctx[:] = [c for c in ctx if not (c[0] == "food_log" and c[2] == day.isoformat() and "supper" in c[5])]
        ctx.append(("food_log", f"{day.isoformat()}T22:15:00+09:00", day.isoformat(), "x", None, "supper_late", "{}"))
    cfgp = syn.make_patient(tmp_path / "late", n_days=150, extra=extra)
    cfg, lib, data, conn, ref = engine(cfgp)
    pair = next(p for p in lib.runnable() if p["exposure"] == "pill_skip" and p["outcome"] == "meal_peak")
    ser = ref.series(pair, "supper")
    i = next(i for i, u in enumerate(ser.units) if u.date == day)
    assert ser.units[i].end == datetime.combine(day + timedelta(days=1), time(0, 45), tzinfo=data.tz)
    assert ser.n_complete_before(day, data.tz) == i and ser.n_complete_before(day + timedelta(days=1), data.tz) == i                 # not yet complete at the start of day + 1
    assert ser.n_complete_before(day + timedelta(days=2), data.tz) == i + 2                                                           # in at day + 2, with the next day's meal


def test_the_outcome_baseline_uses_only_earlier_values():
    t0 = datetime(2026, 1, 1, tzinfo=syn.TZ)
    def mk(vals):
        us = [Unit(t0 + timedelta(days=i), t0 + timedelta(days=i + 1), (t0 + timedelta(days=i)).date(), v) for i, v in enumerate(vals)]
        detrend(us, "day", 30, 10)
        return us
    vals = [float(10 + (i % 7)) for i in range(60)]
    a = mk(vals)
    b = mk(vals[:40] + [999.0] * 20)                                              # later values change
    assert all(math.isnan(u.resid) for u in a[:10]) and not math.isnan(a[10].resid)
    assert [u.resid for u in a[:40]] == [u.resid for u in b[:40]]                  # nothing before the change moves
    assert a[10].resid == pytest.approx(vals[10] - np.median(vals[:10]))
    w = mk(vals)                                                                  # a 30-day window: the baseline of day 50 ignores days before day 20
    assert w[50].resid == pytest.approx(vals[50] - np.median(vals[20:50]))


def test_hour_units_are_detrended_against_the_same_clock_hour():
    t0 = datetime(2026, 1, 1, tzinfo=syn.TZ)
    us = [Unit(t0 + timedelta(days=d, hours=h), t0 + timedelta(days=d, hours=h + 1), (t0 + timedelta(days=d)).date(), float(100 * h + d % 3), None, h) for d in range(20) for h in (3, 15)]
    detrend(us, "hour", 30, 10)
    assert all(abs(u.resid) <= 2 for u in us[20:])                                 # a fixed daily cycle is removed completely


# ---- storage, idempotency, determinism, as-of, read-only ---------------------------------------------------------------------------------------------
def test_refresh_is_deterministic_and_idempotent(patient, tmp_path):
    d, cfgp = patient
    day = syn.START + timedelta(days=150)
    rows = []
    for n in (1, 2):
        st = EvidenceStore(tmp_path / f"e{n}.db")
        cfg, lib, data, conn, ref = engine(cfgp, st)
        s1 = ref.refresh(day)
        before = st.conn.execute("SELECT COUNT(*) FROM relationship_evidence").fetchone()[0]
        s2 = ref.refresh(day)                                                     # the same date again: nothing is written twice
        assert set(s2["writes"]) == {"reused"} and st.conn.execute("SELECT COUNT(*) FROM relationship_evidence").fetchone()[0] == before
        rows.append([tuple(r) for r in st.conn.execute("SELECT * FROM relationship_evidence ORDER BY evidence_id")] + [tuple(r) for r in st.conn.execute("SELECT * FROM evidence_runs")])
        st.close()
    assert rows[0] == rows[1] and len(rows[0]) > 10


def test_no_table_holds_a_wall_clock_timestamp(tmp_path):
    st = EvidenceStore(tmp_path / "e.db")
    for t in ("relationship_evidence", "event_evidence", "event_completions", "evidence_runs"):
        cols = [r[1] for r in st.conn.execute(f"PRAGMA table_info({t})")]
        assert not [c for c in cols if "created" in c or "updated" in c or c.endswith("_at") and c not in ("evaluated_from",)], (t, cols)
    st.close()


def test_the_record_follows_the_example_shape_and_ids(last_day):
    r = last_day[0]["rest_hours@prev_night->meal_peak:supper"]
    assert r["evidence_id"] == f"rel|rest_hours@prev_night->meal_peak:supper|{LAST.isoformat()}|ev-v0" and r["as_of_date"] == LAST.isoformat()
    assert set(r) >= {"evidence_id", "relationship_key", "exposure_id", "outcome_id", "outcome_scope", "unit", "form", "check_type", "as_of_date", "history", "orientation", "detrend",
                      "n_exposed", "n_reference", "effect_kind", "effect", "raw_difference", "permutation", "adjustment", "support", "flags", "placebo", "method_version",
                      "config_version", "inputs_hash", "status"}
    assert r["outcome_scope"] == {"meal_kind": "supper"} and r["permutation"]["n"] == 2000 and set(r["permutation"]) == {"method", "n", "p", "p_contrary"}
    assert 1 / 2001 <= r["permutation"]["p"] <= 1 and r["status"] == "current" and r["effect_kind"] == "spearman_rho" and r["n_reference"] is None


def test_a_changed_input_supersedes_the_old_record_and_nothing_else_moves(patient, tmp_path):
    d, cfgp = patient
    day = syn.START + timedelta(days=150)
    st = EvidenceStore(tmp_path / "e.db")
    engine(cfgp, st)[4].refresh(day)
    old = {r["relationship_key"]: r for r in st.relationships_on(day.isoformat())}
    # change one sleep reading well before the date: only relationships built on sleep can change
    p2 = tmp_path / "p2"
    shutil.copytree(d, p2)
    (p2 / "evidence.yaml").write_text((p2 / "evidence.yaml").read_text().replace(str(d), str(p2)))
    c = sqlite3.connect(p2 / "store.db")
    c.execute("UPDATE raw_events SET value = value + 3 WHERE biomarker = 'sleep_h' AND timestamp LIKE ?", (f"{(syn.START + timedelta(days=60)).isoformat()}%",))
    c.commit()
    c.close()
    out = engine(p2 / "evidence.yaml", st)[4].refresh(day)
    assert out["writes"].get("superseded", 0) >= 1 and out["writes"].get("reused", 0) >= 1
    new = {r["relationship_key"]: r for r in st.relationships_on(day.isoformat())}
    changed = {k for k in new if new[k]["inputs_hash"] != old[k]["inputs_hash"]}
    assert changed and all("rest_hours" in k or "night_len" in k for k in changed)
    assert st.conn.execute("SELECT COUNT(*) FROM relationship_evidence WHERE status = 'superseded'").fetchone()[0] == len(changed)
    st.close()


def truncated_patient(d, tmp, cut: date):
    p = tmp / f"cut_{cut.isoformat()}"
    shutil.copytree(d, p)
    (p / "evidence.yaml").write_text((p / "evidence.yaml").read_text().replace(str(d), str(p)))
    c = sqlite3.connect(p / "store.db")
    c.execute("DELETE FROM raw_events WHERE substr(timestamp, 1, 10) >= ?", (cut.isoformat(),))
    c.execute("DELETE FROM context_events WHERE date >= ?", (cut.isoformat(),))
    c.commit()
    c.close()
    return p / "evidence.yaml"


def test_no_look_ahead_a_store_cut_at_the_as_of_date_gives_identical_records(patient, tmp_path):
    d, cfgp = patient
    day = syn.START + timedelta(days=170)
    full = {r["relationship_key"]: r for r in engine(cfgp)[4].compute(day)[0]}
    cut = {r["relationship_key"]: r for r in engine(truncated_patient(d, tmp_path, day))[4].compute(day)[0]}
    assert full.keys() == cut.keys()
    for k in full:
        a, b = full[k], cut[k]
        a.pop("config_version"), b.pop("config_version")
        assert a == b, k


def test_the_stores_are_opened_read_only(patient, tmp_path):
    d, cfgp = patient
    f = d / "store.db"
    before = hashlib.md5(f.read_bytes()).hexdigest()
    st = EvidenceStore(tmp_path / "e.db")
    engine(cfgp, st)[4].refresh(syn.START + timedelta(days=100))
    st.close()
    assert hashlib.md5(f.read_bytes()).hexdigest() == before
    cfg, lib, data, conn, ref = engine(cfgp)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM context_events")


def test_a_missing_stream_gives_insufficient_no_stream(patient, tmp_path):
    d, _ = patient
    p = tmp_path / "ns"
    shutil.copytree(d, p)
    (p / "evidence.yaml").write_text((p / "evidence.yaml").read_text().replace(str(d), str(p)).replace("adherence: {table: context, name: pills}", "adherence: null"))
    recs = {r["relationship_key"]: r for r in engine(p / "evidence.yaml")[4].compute(LAST)[0]}
    for k in ("pill_skip@2d->day_level", "pill_skip@1d->night_len", "pill_skip@2d->meal_peak:supper"):
        assert recs[k]["support"] == "insufficient" and recs[k]["insufficient_reason"] == "no_stream" and recs[k]["history"] is None
    assert recs["unwell_note@prev_day->day_level"]["support"] != "no_stream"


def test_the_first_weeks_are_insufficient(patient):
    cfg, lib, data, conn, ref = engine(patient[1])
    recs, summary = ref.compute(syn.START + timedelta(days=20))
    assert all(r["support"] == "insufficient" for r in recs) and summary["n_tested"] == 0                      # the hourly relationship has the units but not 60 distinct days


def test_the_engine_code_names_no_stream_measure_medicine_or_patient():
    banned = ["glucose", "heart", "resting", "sleep", "steps", "systolic", "hydration", "screen", "metformin", "amlodipine", "levothyroxine", "thyroid", "meera", "cgm", "diary", "mood",
              "alcohol", "symptom", "missed", "dinner", "breakfast", "lunch", "medication", "blood_pressure", "location"]
    root = Path(__file__).resolve().parent.parent / "src/v0_code/evidence_engine"
    for f in root.glob("*.py"):
        text = f.read_text().lower()
        for w in banned:
            assert w not in text, f"{w!r} appears in {f.name}"


def test_an_hourly_relationship_is_not_tested_before_sixty_distinct_days(patient):
    cfg, lib, data, conn, ref = engine(patient[1])
    first_tested = None
    for k in range(20, 100, 3):
        D = syn.START + timedelta(days=k)
        rec = next(r for r in ref.compute(D)[0] if r["relationship_key"] == "steps_before@60m->hour_level")
        h = rec["history"]
        if rec["support"] == "insufficient":
            if h and h["n_units"] >= cfg.min_history_units and rec["insufficient_reason"] == "history":
                assert h["n_dates"] < cfg.min_history_days                                                     # plenty of units, too few distinct dates
        else:
            first_tested = first_tested or k
            assert h["n_units"] >= cfg.min_history_units and h["n_dates"] >= cfg.min_history_days
    assert first_tested is not None and first_tested >= 60                                                   # 60 distinct usable dates take at least 60 days (plus the detrend baseline)


def test_the_minimum_needs_both_units_and_dates(patient):
    cfg, lib, data, conn, ref = engine(patient[1])
    rec = next(r for r in ref.compute(syn.START + timedelta(days=30))[0] if r["relationship_key"] == "steps_before@60m->hour_level")
    assert rec["history"]["n_units"] > 60 and rec["history"]["n_dates"] < 60 and rec["support"] == "insufficient" and rec["insufficient_reason"] == "history"
