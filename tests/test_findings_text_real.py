"""The text layer's views over every stored version of the real run (skipped when output/findings_engine.db is absent)."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "output/findings_engine.db"
pytestmark = pytest.mark.skipif(not DB.exists() or not (ROOT / "output/personal_data_store.db").exists(), reason="needs the real pipeline outputs")


@pytest.fixture(scope="module")
def views():
    from v0_code.findings_engine import run as frun
    from v0_code.findings_engine.config import FindingsConfig
    from v0_code.findings_engine.run_text import build_views
    from v0_code.findings_engine.storage import FindingsStore
    cfg = FindingsConfig.from_yaml(ROOT / "config/findings_meera_iyer_v1.yaml", ROOT)
    lib, pb, data = frun.prepare(cfg)
    recs = FindingsStore(DB, readonly=True).findings()
    return pb, recs, build_views(cfg, pb, data, recs, lib)


def test_no_view_has_a_banned_word_in_a_key_or_a_value(views):
    from v0_code.findings_engine.view import banned_words_in_view
    pb, recs, vs = views
    assert len(vs) == 284
    for fid, v in vs.items():
        assert banned_words_in_view(v, set(pb.raw["internal_words"])) == [], fid


def test_no_digit_outside_ids_and_the_text_passed_on_as_written(views):
    pb, recs, vs = views

    def strip(v):
        if isinstance(v, dict):
            return {k: strip(x) for k, x in v.items() if k not in ("id", "ids", "members", "set", "about", "backs", "text", "severity_or_note", "headline")}
        return [strip(x) for x in v] if isinstance(v, list) else v
    import json
    for fid, v in vs.items():
        assert not re.search(r"\d", json.dumps(strip(v))), fid


def test_every_part_of_day_word_is_one_of_the_configured_bands_and_backing_entries_come_first(views):
    pb, recs, vs = views
    for v in vs.values():
        assert all(m["part_of_day"] in ("night", "morning", "afternoon", "evening") for m in v["situation"]["measures"])
        flags = [bool(d.get("backs")) for d in v["diary"]]
        assert flags == sorted(flags, reverse=True)                                                 # entries that back a point are first
        assert all(len(set(d["backs"])) <= 5 for d in v["diary"] if d.get("backs"))


def test_the_16_november_entry_backs_the_symptom_points_of_the_18_november_case(views):
    pb, recs, vs = views
    for fid in ("fnd_case_2025-11-18T08:17:00+05:30_v2", "fnd_case_2025-11-18T08:17:00+05:30_v3"):
        entries = [d for d in vs[fid]["diary"] if d.get("backs")]
        father = [d for d in entries if "father unusually tired" in d["text"].lower()]
        assert father and "not her own" in father[0]["severity_or_note"].lower() and father[0]["when"] == "in the days before", fid
