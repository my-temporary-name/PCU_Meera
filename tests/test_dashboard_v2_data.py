"""Dashboard v2 data (Phase 1): the pipeline JSON is consistent with the databases and its ids resolve. Skipped when the data has not been built (uv run python dashboard_v2/build_data.py)."""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "dashboard_v2/data"
pytestmark = pytest.mark.skipif(not (D / "pipeline.json").exists(), reason="dashboard_v2 data not built")


def load(n):
    return json.loads((D / n).read_text())


def test_alerts_cases_and_case_files_line_up():
    alerts, cases = load("alerts.json"), load("cases.json")
    assert len(alerts) == 287 and len(cases) == 116
    ids = {c["id"] for c in cases}
    assert all((D / "case" / f"{i}.json").exists() for i in ids) and len(list((D / "case").glob("*.json"))) == 116
    assert {a["case"] for a in alerts if a["case"]} <= ids and sum(1 for a in alerts if a["counted"]) == sum(c["alerts"] for c in cases)


def test_every_case_file_carries_the_whole_chain():
    total = 0
    for c in load("cases.json"):
        d = json.loads((D / "case" / f"{c['id']}.json").read_text())
        assert d["alerts"] and d["versions"] and len(d["versions"]) == c["versions"]
        for a in d["alerts"]:
            if a["counted"]:
                assert d["packets"][a["id"]]["status"] == "ok" and d["evidence"][a["id"]]["factors"]
        for v in d["versions"]:
            total += 1
            t = v["text"]
            assert t["headline"] and t["sentences"] and t["source"] in ("llm", "code_line")
            assert all(isinstance(s["refs"], list) for s in t["sentences"])
            for n in v["pi_notes"]:
                assert n["association"] and n["view_id"].startswith("p")
            assert [x["id"] for x in v["measures"]] and v["factors"]
    assert total == 284


def test_pi_pipeline_and_quality_numbers():
    pi, q, p = load("pi.json"), load("quality.json"), load("pipeline.json")
    assert len(pi["weeks"]) == 51 and len(pi["memories"]) == 29 and sum(len(m["versions"]) for m in pi["memories"]) == 174
    assert sum(q["text_sources"].values()) == 284 and q["text_sources"]["fallback"] == len(q["fallbacks"])
    assert [s["n"] for s in p["stages"]] == list(range(1, 9)) and all(s["in"] and s["out"] and s["counts"] for s in p["stages"])


def test_nothing_from_the_old_output_is_in_v2_and_v1_is_untouched():
    assert not (D / "events.json").exists() and not (D / "episodes.json").exists() and not (D / "baseline.json").exists()
    src = (ROOT / "dashboard_v2/build_data.py").read_text() + (ROOT / "dashboard_v2/build_pipeline.py").read_text()
    assert '/ "output_for_doctor"' not in src and "_events_final" not in src and "_episodes_final" not in src and "weekly_baseline" not in src            # no path to the old output
    changed = subprocess.run(["git", "status", "--porcelain", "dashboard"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    assert changed == ""
