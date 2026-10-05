"""The Evidence Engine on the first patient's real store (Stage 2a: the daily refresh). Skipped when the store or the configs are not present."""

import hashlib
from datetime import date
from pathlib import Path

import pytest

from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.loader import load_data
from v0_code.evidence_engine.refresh import DailyRefresh
from v0_code.evidence_engine.storage import EvidenceStore

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "config/evidence_meera_iyer_v1.yaml"
STORE = ROOT / "output/personal_data_store.db"
needs = pytest.mark.skipif(not (CFG.exists() and STORE.exists()), reason="needs the evidence config and the store")
DAY = date(2026, 9, 17)


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    cfg = EvidenceConfig.from_yaml(CFG, ROOT)
    lib, data, conn = load_data(cfg, ROOT)
    ref = DailyRefresh(data, lib, cfg, None)
    recs, summary = ref.compute(DAY)
    return {r["relationship_key"]: r for r in recs}, summary, (cfg, lib, data, conn, ref)


@needs
def test_the_real_library_and_rulebook_agree(real):
    cfg, lib, data, conn, ref = real[2]
    assert len(lib.pairs) == 69 and len(lib.runnable()) == 49


@needs
def test_sixty_three_relationships_with_meal_kinds_expanded(real):
    recs, summary, _ = real
    assert len(recs) == summary["n_relationships"] == 63                                  # 49 pairs, seven of them expanded over three meal kinds
    assert {k.rsplit(":", 1)[1] for k in recs if k.endswith(("breakfast", "lunch", "dinner"))} == {"breakfast", "lunch", "dinner"}


@needs
def test_the_two_relationships_that_cannot_be_ordered(real):
    recs = real[0]
    for k in ("strained_period@1d->post_meal_peak:breakfast", "strained_period@same_day->systolic_reading"):
        r = recs[k]
        assert r["support"] == "insufficient" and r["insufficient_reason"] == "no_ordered_exposure" and r["history"]["n_units"] == 0 and r["permutation"] is None
    assert sum(r["insufficient_reason"] == "no_ordered_exposure" for r in recs.values()) == 2


@needs
def test_the_dinner_relationships_of_the_worked_example(real):
    recs = real[0]
    s = recs["sleep_hours@prev_night->post_meal_peak:dinner"]
    assert s["form"] == "continuous" and s["effect_kind"] == "spearman_rho" and s["history"]["n_dropped_by_detrend"] == 10 and 330 <= s["history"]["n_units"] <= 340
    assert abs(s["effect"] - 0.12) < 0.03 and "same_day_unverified" not in s["flags"]
    m = recs["missed_dose@2d->post_meal_peak:dinner"]
    assert "same_day_unverified" in m["flags"] and abs(m["effect"] - 0.24) < 0.05 and 230 <= m["n_exposed"] <= 245 and 95 <= m["n_reference"] <= 100
    i = recs["symptom_entry@3d->post_meal_peak:dinner"]
    assert i["support"] == "not_supported" and i["effect"] < -0.4 and set(i["flags"]) >= {"contrary", "placebo_fired"}


@needs
def test_minimums_hold_on_the_real_record(real):
    recs = real[0]
    assert recs["alcohol_entry@1d->post_meal_peak:dinner"]["support"] == "insufficient" and "small_group" in recs["alcohol_entry@1d->post_meal_peak:dinner"]["flags"]
    assert all(r["support"] == "insufficient" for r in recs.values() if r["insufficient_reason"])
    assert all(r["permutation"] is None for r in recs.values() if r["support"] == "insufficient")


@needs
def test_the_real_store_is_untouched_and_the_other_databases_are_read_only(real, tmp_path):
    before = hashlib.md5(STORE.read_bytes()).hexdigest()
    cfg, lib, data, conn, ref = real[2]
    st = EvidenceStore(tmp_path / "e.db")
    DailyRefresh(data, lib, cfg, st).refresh(DAY)
    st.close()
    assert hashlib.md5(STORE.read_bytes()).hexdigest() == before


# ---- Stage 2b on the real packets -----------------------------------------------------------------------------------------------------------------------
PACKETS = ROOT / "output/rulebook_lookup.db"
HANDOFFS = ROOT / "output/state_engine.db"
needs_b = pytest.mark.skipif(not (CFG.exists() and STORE.exists() and PACKETS.exists() and HANDOFFS.exists()), reason="needs the packets and the hand-offs")


@pytest.fixture(scope="module")
def stage_b(tmp_path_factory):
    from v0_code.evidence_engine.run import main
    db = tmp_path_factory.mktemp("stageb") / "e.db"
    assert main(["--config", str(CFG), "--stage", "B", "--db", str(db)]) == 0
    st = EvidenceStore(db, readonly=True)
    from v0_code.rulebook_lookup.storage import PacketStore
    p = PacketStore(PACKETS, readonly=True)
    out = st.events(), {x["handoff_id"]: x for x in p.packets()}, st
    return out


@needs_b
def test_every_packet_has_one_record_and_every_candidate_appears_exactly_once(stage_b):
    events, packets, st = stage_b
    assert len(events) == len(packets) == 287 and len({e["evidence_id"] for e in events}) == 287
    for e in events:
        p = packets[e["handoff_id"]]
        names = [f["candidate"] for f in e["factors"]] + [n["candidate"] for n in e["not_tested"]]
        assert sorted(names) == sorted(x["candidate"] for k in ("selected", "skipped", "not_selected") for x in p[k]) and len(set(names)) == len(names)
        assert e["counts"]["factors"] == len(e["factors"]) and e["counts"]["not_tested"] == len(e["not_tested"])


@needs_b
def test_deferred_packets_have_no_factors(stage_b):
    events, packets, st = stage_b
    d = [e for e in events if packets[e["handoff_id"]].get("status") == "deferred"]
    assert len(d) == 8 and all(e["factors"] == [] and [n["reason"] for n in e["not_tested"]] == ["rule_deferred"] * 2 for e in d)


@needs_b
def test_the_five_low_glucose_events_have_completions_and_the_records_are_unchanged(stage_b):
    events, packets, st = stage_b
    comps = st.completions()
    low = [e for e in events if e["rule_id"] == "glucose_below"]
    assert len(low) == 5 and sorted(c["evidence_id"] for c in comps) == sorted(e["evidence_id"] for e in low) and all(c["candidate"] == "sensor_artifact" for c in comps)
    for e in low:
        f = next(f for f in e["factors"] if f["candidate"] == "sensor_artifact")
        assert f["support"] == "not_yet_available" and f["event_specific"]["earliest_evaluation_time"]


@needs_b
def test_an_end_of_day_outcome_has_the_day_before_as_its_outcome_date(stage_b):
    events, packets, st = stage_b
    h = [e for e in events if e["rule_id"] == "hydration_below"]
    assert h and all(e["as_of_date"] < e["event_time"][:10] for e in h)
    assert all(e["as_of_date"] == e["event_time"][:10] for e in events if e["rule_id"] not in ("hydration_below",))


@needs_b
def test_the_worked_example_event(stage_b):
    events, packets, st = stage_b
    e = next(e for e in events if e["handoff_id"] == "handoff_glucose_2026-09-17T22:30")
    assert [(f["rank"], f["candidate"], f["support"]) for f in e["factors"]] == [
        (1, "meal_composition", "supported"), (2, "medication_adherence", "supported"), (3, "sleep", "supported"), (4, "stress_mood", "not_supported"),
        (5, "activity", "not_supported"), (6, "illness_symptoms", "not_supported"), (10, "alcohol", "insufficient")]
    ex = {f["candidate"]: f["event_exposure"]["state"] for f in e["factors"]}
    assert ex == {"meal_composition": "exposed", "medication_adherence": "exposed", "sleep": "exposed", "stress_mood": "exposed", "activity": "not_yet_available",
                  "illness_symptoms": "not_exposed", "alcohol": "not_exposed"}
    m = e["factors"][0]["event_specific"]
    assert (m["elapsed_minutes"], m["bucket_minutes"], m["bucket_size"], m["observed"], m["percentile"]) == (62, 60, 15, 185.0, 99) and abs(m["history_median"] - 150.1) < 0.1
    assert e["factors"][2]["event_exposure"]["tail_percentile"] == 0.6 and e["factors"][4]["event_exposure"]["available_at"] == "end_of_day"
    assert [n["reason"] for n in e["not_tested"]] == ["not_selected_budget", "skipped_by_packet", "skipped_by_packet"] and e["counts"]["supported"] == 3
    assert set(e["factors"][5]["flags"]) == {"contrary", "placebo_fired"}
