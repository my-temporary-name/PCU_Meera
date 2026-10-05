"""Evidence Engine, Stage 2b: event evidence for one packet (spec 8 E1 to E6, 7.3, 7.4, 9.2, 9.3), on the synthetic second patient (tests/evidence_synth.py)."""

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
from v0_code.evidence_engine.events import EventEngine
from v0_code.evidence_engine.loader import load_data
from v0_code.evidence_engine.refresh import DailyRefresh
from v0_code.evidence_engine.storage import EvidenceStore

N_DAYS = 240
D = syn.START + timedelta(days=200)
SHORT_SLEEP_DAY = syn.START + timedelta(days=210)


def short_sleep(readings, ctx):
    for i, r in enumerate(readings):
        if r[2] == "sleep_h" and r[1].startswith(SHORT_SLEEP_DAY.isoformat()):
            readings[i] = (r[0], r[1], r[2], 2.0, r[4])


@pytest.fixture(scope="module")
def patient(tmp_path_factory):
    d = tmp_path_factory.mktemp("synth_events")
    return d, syn.make_patient(d, n_days=N_DAYS, extra=short_sleep)


def build(cfgp, tmp, name="e.db"):
    cfg = EvidenceConfig.from_yaml(cfgp, Path(cfgp).parent)
    lib, data, conn = load_data(cfg, Path(cfgp).parent)
    st = EvidenceStore(tmp / name)
    ref = DailyRefresh(data, lib, cfg, st)
    return EventEngine(data, lib, cfg, st, ref), lib, data, cfg, st, ref


@pytest.fixture(scope="module")
def eng(patient, tmp_path_factory):
    return build(patient[1], tmp_path_factory.mktemp("evstore"))


def sel(lib, rule, ranks):
    out = []
    for r in ranks:
        p = lib.pair(rule, r)
        out.append({"rank": r, "weight_tier": p["tier"], "candidate": p["candidate"], "check_type": p["check_type"], "lookback": {"kind": "x", "value": None}})
    return out


def packet(lib, rule, ranks, hid, skipped=(), not_selected=(), status=None):
    p = {"packet_id": f"packet_{hid}", "handoff_id": hid, "matched_rule": {"rule_id": rule, "status": "active"}, "selected": sel(lib, rule, ranks), "skipped": list(skipped), "not_selected": list(not_selected)}
    if status:
        p["status"] = status
    return p


def handoff(hid, opened, meal=None):
    return {"handoff_id": hid, "measure": "m", "direction": "above", "opened_at": opened.isoformat(),
            "context": {"last_meal": None if meal is None else {"label": meal[0], "time": meal[1].isoformat(), "minutes_ago": int((opened - meal[1]).total_seconds() // 60)}}}


def at(d, h, m=0):
    return datetime.combine(d, time(h, m), tzinfo=syn.TZ)


def supper(data, d):
    return next(r for r in data.records("meals") if r.date == d and r.category.startswith("supper"))


def factor(rec, cand):
    return next(f for f in rec["factors"] if f["candidate"] == cand)


# ---- the normal record ----------------------------------------------------------------------------------------------------------------------------------
def test_record_shape_ids_completeness_and_counts(eng):
    e, lib, data, cfg, st, ref = eng
    m = supper(data, D)
    T = m.ts + timedelta(minutes=62)
    hid = "h_normal"
    pk = packet(lib, "r_meal", [1, 2, 3, 4, 5, 6, 7], hid, skipped=[{"candidate": "x1", "reason": "applies_if_not_met", "detail": "d"}],
                not_selected=[{"candidate": "x2", "weight_tier": "tertiary", "reason": "budget"}])
    rec = e.record(pk, handoff(hid, T, ("supper_x", m.ts)))
    assert rec["evidence_id"] == f"ev_{hid}" and rec["packet_id"] == f"packet_{hid}" and rec["rule_id"] == "r_meal" and rec["event_time"] == T.isoformat()
    assert rec["as_of_date"] == D.isoformat() and rec["method_version"] == "ev-v0" and rec["config_version"]
    assert [f["rank"] for f in rec["factors"]] == [1, 2, 3, 4, 5, 6, 7]
    for f in rec["factors"]:
        assert set(f) >= {"rank", "weight_tier", "candidate", "check_type", "relationship_evidence_id", "support", "flags", "event_exposure", "event_specific"}
    names = [f["candidate"] for f in rec["factors"]] + [n["candidate"] for n in rec["not_tested"]]
    assert sorted(names) == sorted([x["candidate"] for x in pk["selected"]] + ["x1", "x2"])                  # every candidate exactly once
    assert rec["not_tested"] == [{"candidate": "x2", "reason": "not_selected_budget"},
                                 {"candidate": "x1", "reason": "skipped_by_packet", "packet_reason": "applies_if_not_met", "packet_detail": "d"}]            # unknown candidates keep packet order
    c = rec["counts"]
    assert c["factors"] == 7 and c["not_tested"] == 2 and sum(c[k] for k in ("supported", "suggestive", "not_supported", "insufficient", "not_applicable", "not_yet_available")) == 7
    skip = factor(rec, "skip")
    assert skip["relationship_evidence_id"] == f"rel|pill_skip@2d->meal_peak:supper|{D.isoformat()}|ev-v0"
    stored = st.get_relationship(skip["relationship_evidence_id"])
    assert skip["support"] == stored["support"] and skip["flags"] == stored["flags"]
    assert "effect" not in json.dumps(rec["factors"]) and "permutation" not in json.dumps(rec["factors"])                 # statistics live only in the relationship record


def test_a_no_definition_factor_is_insufficient(eng):
    e, lib, data, cfg, st, ref = eng
    m = supper(data, D)
    rec = e.record(packet(lib, "r_meal", [6], "h_nodef"), handoff("h_nodef", m.ts + timedelta(minutes=30), ("supper_x", m.ts)))
    f = rec["factors"][0]
    assert f["support"] == "insufficient" and f["reason"] == "no_definition" and f["relationship_evidence_id"] is None


def test_the_relationship_evidence_is_made_lazily_for_the_outcome_date(patient, tmp_path):
    e, lib, data, cfg, st, ref = build(patient[1], tmp_path)
    day = syn.START + timedelta(days=150)
    m = supper(data, day)
    assert not st.has_date(day.isoformat(), "ev-v0")
    e.record(packet(lib, "r_meal", [2], "h_lazy"), handoff("h_lazy", m.ts + timedelta(minutes=30), ("supper_x", m.ts)))
    assert st.has_date(day.isoformat(), "ev-v0") and len(st.relationships_on(day.isoformat())) > 0


# ---- E1: deferred and unmatched packets --------------------------------------------------------------------------------------------------------------------
def test_a_deferred_packet_has_no_factors_and_every_candidate_not_tested(eng):
    e, lib, data, cfg, st, ref = eng
    pk = {"packet_id": "packet_h_def", "handoff_id": "h_def", "status": "deferred", "matched_rule": {"rule_id": "r_def", "status": "deferred"}, "selected": [], "skipped": [],
          "not_selected": [{"candidate": "a", "weight_tier": "secondary", "reason": "rule_deferred"}, {"candidate": "b", "weight_tier": "secondary", "reason": "rule_deferred"}]}
    rec = e.record(pk, handoff("h_def", at(D, 10)))
    assert rec["factors"] == [] and rec["rule_id"] == "r_def" and rec["as_of_date"] == D.isoformat()
    assert rec["not_tested"] == [{"candidate": "a", "reason": "rule_deferred"}, {"candidate": "b", "reason": "rule_deferred"}]
    assert rec["counts"]["factors"] == 0 and rec["counts"]["not_tested"] == 2


def test_an_unmatched_packet_has_no_rule(eng):
    e, lib, data, cfg, st, ref = eng
    pk = {"packet_id": "packet_h_un", "handoff_id": "h_un", "status": "unmatched", "matched_rule": None, "selected": [], "skipped": [], "not_selected": []}
    rec = e.record(pk, handoff("h_un", at(D, 10)))
    assert rec["rule_id"] is None and rec["factors"] == [] and rec["not_tested"] == [] and rec["overlap"] == []


# ---- event exposure (7.4) ------------------------------------------------------------------------------------------------------------------------------
def state_of(e, lib, rule, rank, T, meal=None):
    hid = f"h_{rule}_{rank}_{T.isoformat()}"
    return factor(e.record(packet(lib, rule, [rank], hid), handoff(hid, T, meal)), lib.pair(rule, rank)["candidate"])["event_exposure"]


def test_a_date_only_record_that_is_not_yet_available_is_not_yet_available_never_not_exposed(eng):
    e, lib, data, cfg, st, ref = eng
    day = next(d for d in (D + timedelta(days=k) for k in range(40)) if data.by_date("adherence")[d][0].text == "taken" and data.by_date("adherence")[d - timedelta(days=1)][0].text == "taken")
    early, late = state_of(e, lib, "r_day", 1, at(day, 18)), state_of(e, lib, "r_day", 1, at(day, 22))
    assert early["state"] == "not_yet_available" and early["available_at"] == "21:00"                      # today's record arrives at 21:00, yesterday's taken
    assert late["state"] == "not_exposed"
    skipped_yesterday = next(d for d in (D + timedelta(days=k) for k in range(40)) if data.by_date("adherence")[d - timedelta(days=1)][0].text == "skipped")
    assert state_of(e, lib, "r_day", 1, at(skipped_yesterday, 18))["state"] == "exposed"                   # exposed if any available record shows it


def test_a_mood_block_counts_only_once_it_has_ended(eng):
    e, lib, data, cfg, st, ref = eng
    for d in (D + timedelta(days=k) for k in range(30)):
        blocks = {r.block: r.category == "stressed" for r in data.by_date("mood")[d]}
        noon = state_of(e, lib, "r_day", 2, at(d, 12))
        if blocks["am"]:
            assert noon["state"] == "exposed"
        else:
            assert noon["state"] == "not_yet_available"                                                    # the afternoon block has not ended
        evening = state_of(e, lib, "r_day", 2, at(d, 18))
        assert evening["state"] == ("exposed" if any(blocks.values()) else "not_exposed")


def test_a_continuous_exposure_reports_its_tail(eng):
    e, lib, data, cfg, st, ref = eng
    m = supper(data, SHORT_SLEEP_DAY)
    s = state_of(e, lib, "r_meal", 2, m.ts + timedelta(minutes=62), ("supper_x", m.ts))
    assert s["state"] == "exposed" and s["tail_percentile"] < 5
    m2 = supper(data, D)
    s2 = state_of(e, lib, "r_meal", 2, m2.ts + timedelta(minutes=62), ("supper_x", m2.ts))
    assert s2["state"] in ("exposed", "not_exposed") and 0 <= s2["tail_percentile"] <= 100
    assert (s2["state"] == "exposed") == (s2["tail_percentile"] <= 25)                                         # low sleep is the risky side


def test_a_binarized_exposure_compares_with_the_as_of_threshold(eng):
    e, lib, data, cfg, st, ref = eng
    pair = lib.pair("r_meal", 5)
    ser = ref.series(pair, "supper")
    for d in (D + timedelta(days=k) for k in range(8)):
        m = supper(data, d)
        h = ser.at(d, data.tz)
        s = state_of(e, lib, "r_meal", 5, m.ts + timedelta(minutes=62), ("supper_x", m.ts))
        assert s["state"] == ("exposed" if m.ts.hour * 60 + m.ts.minute >= h.threshold else "not_exposed")


def test_the_hourly_exposure_is_the_previous_hours_row(eng):
    e, lib, data, cfg, st, ref = eng
    rows = {r.ts: r.value for r in data.records("steps_hourly")}
    T = at(D, 14, 30)
    s = state_of(e, lib, "r_hour", 1, T)
    pct = 100 * np.mean(np.array([r for r in ref.series(lib.pair("r_hour", 1), None).x_raw[:ref.series(lib.pair("r_hour", 1), None).n_complete_before(D, data.tz)] if not np.isnan(r)]) <= rows[at(D, 13)])
    assert s["state"] in ("exposed", "not_exposed") and s["tail_percentile"] == pytest.approx(pct, abs=0.6)


def test_a_meal_with_no_kind_makes_every_relationship_factor_insufficient(eng):
    e, lib, data, cfg, st, ref = eng
    T = at(D, 15, 30)
    rec = e.record(packet(lib, "r_meal", [1, 2, 3, 4, 7], "h_nokind"), handoff("h_nokind", T, ("tea_time", at(D, 15))))
    for f in rec["factors"]:
        if f["check_type"] == "group_comparison":
            assert f["support"] == "insufficient" and f["reason"] == "no_meal_kind" and f["relationship_evidence_id"] is None
    assert factor(rec, "peak_check")["event_specific"]["history_n"] > 300                                      # the percentile still runs against all meals


# ---- event-level checks (7.3) -----------------------------------------------------------------------------------------------------------------------------
def test_the_percentile_check_compares_like_for_like(eng):
    e, lib, data, cfg, st, ref = eng
    m = supper(data, D)
    T = m.ts + timedelta(minutes=62)
    f = factor(e.record(packet(lib, "r_meal", [7], "h_pct"), handoff("h_pct", T, ("supper_x", m.ts))), "peak_check")
    es = f["event_specific"]
    series = data.readings("glucose")
    obs = max(v for t, v in series if m.ts <= t <= T)
    hist = []
    for r in data.records("meals"):
        if r.ts < m.ts and r.category.startswith("supper"):
            vals = [v for t, v in series if r.ts <= t <= r.ts + timedelta(minutes=60)]
            hist.append(max(vals))
    assert es["elapsed_minutes"] == 62 and es["bucket_minutes"] == 60 and es["bucket_size"] == 15 and es["observed"] == obs and es["history_n"] == len(hist)
    assert es["history_median"] == pytest.approx(float(np.median(hist)), abs=0.06) and es["history_p90"] == pytest.approx(float(np.percentile(hist, 90)), abs=0.06)
    assert es["percentile"] == round(100 * float(np.mean(np.array(hist) <= obs)))
    assert f["support"] == ("supported" if es["percentile"] >= 90 else "not_supported") and f["relationship_evidence_id"] is None
    assert f["event_exposure"]["state"] == ("exposed" if es["percentile"] >= 75 else "not_exposed")


def test_too_little_history_is_insufficient(eng):
    e, lib, data, cfg, st, ref = eng
    d = syn.START + timedelta(days=12)
    m = supper(data, d)
    f = factor(e.record(packet(lib, "r_meal", [7], "h_few"), handoff("h_few", m.ts + timedelta(minutes=62), ("supper_x", m.ts))), "peak_check")
    assert f["support"] == "insufficient" and f["event_specific"]["history_n"] == 12


def test_hours_since_the_last_meal_is_compared_at_the_same_clock_hour(eng):
    e, lib, data, cfg, st, ref = eng
    m = supper(data, D)
    T = m.ts + timedelta(minutes=95)
    f = factor(e.record(packet(lib, "r_meal", [8], "h_gap"), handoff("h_gap", T, ("supper_x", m.ts))), "gap_check")
    es = f["event_specific"]
    assert es["observed"] == pytest.approx(95 / 60, abs=0.01) and es["history_n"] >= 30 and 0 <= es["percentile"] <= 100
    bucket = datetime.combine(D, time(0), tzinfo=syn.TZ) + timedelta(minutes=15 * round(((T.hour * 60 + T.minute) / 15)))
    vals = []
    for k in range(1, 400):
        d = D - timedelta(days=k)
        t = datetime.combine(d, time(bucket.hour, bucket.minute), tzinfo=syn.TZ)
        prev = [r.ts for r in data.records("meals") if r.ts <= t]
        if prev:
            vals.append((t - max(prev)).total_seconds() / 3600)
    assert es["history_n"] == len(vals) and es["percentile"] == round(100 * float(np.mean(np.array(vals) <= es["observed"] + 1e-9)))


def test_the_pattern_checks_are_descriptive(eng):
    e, lib, data, cfg, st, ref = eng
    rec = e.record(packet(lib, "r_day", [4, 5], "h_pat"), handoff("h_pat", at(D, 12)))
    rise, rates = rec["factors"]
    assert rise["support"] in ("supported", "not_supported") and rise["event_specific"]["n_days"] >= 14 and 0 <= rise["event_specific"]["share"] <= 1
    assert rates["support"] == "not_applicable" and set(rates["event_specific"]["rates"]) == {"pill_a"}
    allr = data.by_date("adherence")
    miss = sum(1 for d, rs in allr.items() if d < D and rs[0].text == "skipped")
    tot = sum(1 for d in allr if d < D)
    assert rates["event_specific"]["rates"]["pill_a"] == {"n_match": miss, "total": tot, "rate": round(miss / tot, 4)}
    assert rise["event_exposure"] is None and rates["event_exposure"] is None


def test_a_presence_check_is_a_fact_from_config(eng):
    e, lib, data, cfg, st, ref = eng
    f = factor(e.record(packet(lib, "r_hour", [2], "h_pres"), handoff("h_pres", at(D, 12))), "anything")
    assert f["support"] == "not_applicable" and f["event_specific"] == {"present": True} and f["event_exposure"] is None and f["relationship_evidence_id"] is None


# ---- the shape check and its completion --------------------------------------------------------------------------------------------------------------------
LOW_DAY = syn.START + timedelta(days=120)


def lows(single):
    def extra(readings, ctx):
        short_sleep(readings, ctx)
        for i, r in enumerate(readings):
            if r[2] == "gl_cgm" and r[1].startswith(LOW_DAY.isoformat()) and r[1][11:16] in (("03:00",) if single else ("03:00", "03:15", "03:30")):
                readings[i] = (r[0], r[1], r[2], 55.0, r[4])
    return extra


@pytest.fixture(scope="module")
def shape_engines(tmp_path_factory):
    out = {}
    for single in (True, False):
        d = tmp_path_factory.mktemp(f"shape_{single}")
        cfgp = syn.make_patient(d, n_days=N_DAYS, extra=lows(single))
        out[single] = build(cfgp, d)
    return out


def test_the_shape_check_is_written_not_yet_available_and_completed_later(shape_engines):
    e, lib, data, cfg, st, ref = shape_engines[True]
    T = at(LOW_DAY, 3, 0)
    pk, ho = packet(lib, "r_hour", [3], "h_shape"), handoff("h_shape", T)
    rec, how = e.process(pk, ho)
    f = rec["factors"][0]
    assert f["support"] == "not_yet_available" and f["event_specific"]["earliest_evaluation_time"] == (T + timedelta(minutes=60)).isoformat() and f["event_exposure"] is None
    before = st.conn.execute("SELECT record_json FROM event_evidence WHERE evidence_id = 'ev_h_shape'").fetchone()[0]
    assert e.complete("ev_h_shape", data_until=T + timedelta(minutes=30)) == []                               # the readings after the event do not exist yet
    done = e.complete("ev_h_shape")
    assert len(done) == 1 and done[0]["support"] == "supported" and done[0]["candidate"] == "artifact"
    res = json.loads(st.conn.execute("SELECT result_json FROM event_completions WHERE evidence_id = 'ev_h_shape'").fetchone()[0])
    assert res["isolated"] is True and res["rebound"] is True and res["steep_drop"] is True and res["overnight"] is True and res["target_removed_by_cleaning"] is False
    assert st.conn.execute("SELECT record_json FROM event_evidence WHERE evidence_id = 'ev_h_shape'").fetchone()[0] == before            # the event record never changes
    assert e.complete("ev_h_shape") == [] and st.conn.execute("SELECT COUNT(*) FROM event_completions").fetchone()[0] == 1               # idempotent


def test_a_sustained_low_is_not_an_isolated_reading(shape_engines):
    e, lib, data, cfg, st, ref = shape_engines[False]
    T = at(LOW_DAY, 3, 15)
    e.process(packet(lib, "r_hour", [3], "h_run"), handoff("h_run", T))
    (c,) = e.complete("ev_h_run")
    assert c["support"] == "not_supported"
    assert json.loads(st.conn.execute("SELECT result_json FROM event_completions WHERE evidence_id = 'ev_h_run'").fetchone()[0])["isolated"] is False


# ---- overlap ----------------------------------------------------------------------------------------------------------------------------------------------
def test_overlap_is_one_entry_per_unordered_pair_of_supported_or_suggestive_factors(eng):
    e, lib, data, cfg, st, ref = eng
    m = supper(data, D)
    rec = e.record(packet(lib, "r_meal", [1, 2, 3, 4, 5], "h_ov"), handoff("h_ov", m.ts + timedelta(minutes=62), ("supper_x", m.ts)))
    strong = [f for f in rec["factors"] if f["support"] in ("supported", "suggestive") and f["check_type"] == "group_comparison"]
    assert len(rec["overlap"]) == len(strong) * (len(strong) - 1) // 2
    for o in rec["overlap"]:
        assert set(o) >= {"a", "b", "a_view", "share_given_a", "share_overall", "ratio", "flag"} and 0 <= o["share_given_a"] <= 1 and 0 <= o["share_overall"] <= 1
        assert o["flag"] == (o["share_given_a"] >= 0.25 and o["ratio"] is not None and o["ratio"] >= 2.0)
        assert o["a"].count("@") == 1 and "->" not in o["a"]


# ---- idempotency, immutability, read-only -------------------------------------------------------------------------------------------------------------------
def test_writing_the_same_packet_again_gives_the_same_record_and_no_duplicate(patient, tmp_path):
    e, lib, data, cfg, st, ref = build(patient[1], tmp_path)
    m = supper(data, D)
    pk, ho = packet(lib, "r_meal", [1, 2, 3, 7], "h_idem"), handoff("h_idem", m.ts + timedelta(minutes=62), ("supper_x", m.ts))
    r1, how1 = e.process(pk, ho)
    r2, how2 = e.process(pk, ho)
    assert r1 == r2 and how1 == "written" and how2 == "same" and st.conn.execute("SELECT COUNT(*) FROM event_evidence").fetchone()[0] == 1


def test_an_event_record_is_never_changed_after_it_is_written(patient, tmp_path):
    e, lib, data, cfg, st, ref = build(patient[1], tmp_path)
    m = supper(data, D)
    ho = handoff("h_imm", m.ts + timedelta(minutes=62), ("supper_x", m.ts))
    e.process(packet(lib, "r_meal", [2], "h_imm"), ho)
    stored = st.conn.execute("SELECT record_json FROM event_evidence").fetchone()[0]
    rec, how = e.process(packet(lib, "r_meal", [2, 3], "h_imm"), ho)                                             # a different record for the same id: the first one stays
    assert how == "differs" and st.conn.execute("SELECT record_json FROM event_evidence").fetchone()[0] == stored


def test_events_are_deterministic_across_runs(patient, tmp_path):
    outs = []
    for n in (1, 2):
        e, lib, data, cfg, st, ref = build(patient[1], tmp_path, f"d{n}.db")
        m = supper(data, D)
        e.process(packet(lib, "r_meal", [1, 2, 3, 4, 5, 7, 8], "h_det"), handoff("h_det", m.ts + timedelta(minutes=62), ("supper_x", m.ts)))
        outs.append([tuple(r) for r in st.conn.execute("SELECT * FROM event_evidence")] + [tuple(r) for r in st.conn.execute("SELECT * FROM relationship_evidence ORDER BY id")])
    assert outs[0] == outs[1]


def test_the_store_is_untouched(patient, tmp_path):
    f = patient[0] / "store.db"
    before = hashlib.md5(f.read_bytes()).hexdigest()
    e, lib, data, cfg, st, ref = build(patient[1], tmp_path)
    m = supper(data, D)
    e.process(packet(lib, "r_meal", [1, 2, 3], "h_ro"), handoff("h_ro", m.ts + timedelta(minutes=62), ("supper_x", m.ts)))
    assert hashlib.md5(f.read_bytes()).hexdigest() == before
