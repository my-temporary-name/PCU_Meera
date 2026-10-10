"""Checks for the NMG Lite view: spec section 7 expected results, derived values, and independence from the pipeline."""
import json, re, subprocess, sys, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))


def _build():
    subprocess.run([sys.executable, str(HERE / "build_nmg.py")], check=True, capture_output=True)
    return json.loads((HERE / "data" / "nmg.json").read_text())


def _rules():
    out = subprocess.run(["node", str(HERE / "tests" / "run_rules.mjs")], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


DATA = _build()
RULES = _rules()

SIGNALS = {"anthropometry": "red", "glycemia": "red", "bp": "none", "lipids": "red", "kidney": "green",
           "liver": "none", "activity": "amber", "lifestyle": "amber"}

TABLE = {  # key: (latest, baseline, change, since-dx value, since-dx delta)
    "hba1c": (7.4, 7.2, 0.2, 8.0, -0.6), "fpg": (138, 134, 4, 162, -24), "ldl": (126, 125, 1, 140, -14),
    "hdl": (45, 46, -1, 44, 1), "tg": (180, 175.5, 4.5, 190, -10), "egfr": (93.7, 93.7, 0, 96.7, -3.0),
    "alt": (43, 44, -1, 38, 5), "uacr": (18, 13, 5, 18, 0), "tsh": (3.0, 3.1, -0.1, 4.2, -1.2),
    "weight": (72.1, 71.8, 0.3, 69.5, 2.6), "waist": (91.5, 90.5, 1.0, 86.0, 5.5),
}


def test_section7_signals():
    got = {d["id"]: d["signal"] for d in RULES["domains"]}
    assert got == SIGNALS


def test_glycemic_state_and_first_followup():
    assert RULES["state"].startswith("S4")
    f5 = [f for f in RULES["followup"] if f["rule"] == "F5"][0]
    assert f5["next"] == "2026-12-17"


def test_baseline_direction_since_diagnosis():
    for k, (latest, base, chg, sd, sdd) in TABLE.items():
        v = DATA["vars"][k]
        assert abs(v["latest"]["v"] - latest) < 1e-6, k
        assert abs(v["baseline"]["v"] - base) < 1e-6, k
        assert v["direction"]["dir"] == "steady", k
        assert abs(v["direction"]["change"] - chg) < 1e-6, k
        assert abs(v["since_dx"]["v"] - sd) < 1e-6 and abs(v["since_dx"]["delta"] - sdd) < 1e-6, k


def test_glucose_input_unchanged():
    assert DATA["meta"]["glucose_md5"].startswith("508468f1")


def test_no_pipeline_dependency():
    src = (HERE / "build_nmg.py").read_text()
    assert not re.search(r"^\s*(import|from)\s+(v0_code|sqlite3)", src, re.M)
    assert ".db" not in src
    for p in (HERE / "js").glob("*.js"):
        t = p.read_text()
        assert "dashboard_v2" not in t and "output/" not in t, p.name
