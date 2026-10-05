"""PI's situations-line views over every stored long-term version of the real run (skipped when output/pi.db is absent)."""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "output/pi.db"
pytestmark = pytest.mark.skipif(not DB.exists(), reason="needs the real PI run")


@pytest.fixture(scope="module")
def built():
    from v0_code.evidence_engine.library import load_library
    from v0_code.findings_engine.factors import parse_key
    from v0_code.intel_common.phrasebook import Phrasebook
    from v0_code.pi_engine import run_text, text_view
    from v0_code.pi_engine.config import PiConfig
    from v0_code.pi_engine.engine import PiReader
    from v0_code.pi_engine.storage import PiStore
    cfg = PiConfig.from_yaml(ROOT / "config/pi_meera_iyer_v1.yaml", ROOT)
    lib, pb = load_library(cfg.paths["evidence_library"]), Phrasebook.load(cfg.paths["phrasebook"])
    store = PiStore(DB, readonly=True)
    pi = PiReader(cfg, store)
    vs = run_text.load_versions(store, cfg, pi)
    kinds = {parse_key(v["relationship_key"])[3] for v in vs} - {None}
    src = text_view.FindingsSentences(cfg.paths["findings_db"])
    views = {(m["memory_id"], m["version"]): text_view.build_view(pi, m, None, m["regenerated"], pb, lib, kinds, src, cfg.text.get("diary_ref_prefix", "d")) for m in vs if m["status"] != "retracted"}
    return pb, vs, views, src


def test_every_view_has_only_diary_only_sentences_no_digit_and_at_most_six(built):
    pb, vs, views, src = built
    assert len(views) == len(vs) - 1
    diary = {}
    for (mid, ver), (v, ids) in views.items():
        if v is None:
            assert ids == []
            continue
        assert list(v) == ["link", "previous_situations", "sentences"] and 1 <= len(v["sentences"]) <= 6 and len(set(v["sentences"])) == len(v["sentences"]) and 1 <= len(ids) <= 6, (mid, ver)
        assert not re.search(r"\d", json.dumps(v, ensure_ascii=False)), (mid, ver)
        for fid in ids:
            marked = dict(src(fid))
            for t in v["sentences"]:
                if t in marked:
                    assert marked[t] and all(re.fullmatch(r"d\d+", r) for r in marked[t]), (fid, t, marked[t])
                    diary[t] = marked[t]
    assert diary                                                                                         # the real run has diary-only sentences


def test_a_version_with_no_entry_this_week_has_no_view(built):
    pb, vs, views, src = built
    for m in vs:
        if m["status"] != "retracted" and m["entries_this_week"] == 0:
            assert views[(m["memory_id"], m["version"])][0] is None


def test_the_view_has_no_state_and_no_association(built):
    pb, vs, views, src = built
    for (mid, ver), (v, _) in views.items():
        if v is not None:
            text = json.dumps({k: x for k, x in v.items() if k != "sentences"}, ensure_ascii=False)
            assert "early observation" not in text and "repeatedly" not in text and "state" not in v
