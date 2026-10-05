"""PI is generic: no stream, measure, medicine or patient name in the engine, and a second synthetic patient (another timezone, library, phrases and keys) runs on config alone."""

import json
from pathlib import Path

from pi_synth import KEY_A, KEY_B, make_pi_patient
from v0_code.pi_engine import run as pirun
from v0_code.pi_engine.config import PiConfig
from v0_code.pi_engine.storage import PiStore

ROOT = Path(__file__).resolve().parent.parent


def test_the_engine_names_no_stream_measure_medicine_or_patient():
    banned = ["glucose", "heart_rate", "sleep_duration", "metformin", "amlodipine", "levothyroxine", "meal_events", "diary_context", "step_count", "hydration", "screen_time", "blood_pressure",
              "mood_state", "medication_adherence", "thyroid", "meera", "iyer", "cgm", "dinner", "lunch", "breakfast", "missed_dose", "sleep_hours", "post_meal"]
    for f in (ROOT / "src/v0_code/pi_engine").glob("*.py"):
        text = f.read_text().lower()
        for w in banned:
            assert w not in text, f"{w} appears in {f.name}"


def test_a_second_patient_runs_on_config_alone(tmp_path, capsys):
    cfgp = make_pi_patient(tmp_path / "p2")
    assert pirun.main(["--config", str(cfgp), "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "as-of audit: clean" in out and "mode code_only" in out
    cfg = PiConfig.from_yaml(cfgp, tmp_path)
    assert cfg.timezone == "Asia/Tokyo"
    s = PiStore(cfg.paths["db_path"], readonly=True)
    runs = s.runs()
    assert [r["week"] for r in runs][0] == "2026-W19" and runs[-1]["written_at"].endswith("+09:00") and runs[-1]["written_at"] == "2026-06-18T23:59:59+09:00"
    rows = {json.loads(r[0])["relationship_key"]: json.loads(r[0]) for r in s.conn.execute("SELECT record_json FROM pi_long_memories ORDER BY version")}
    assert set(rows) == {KEY_A, KEY_B}
    a = rows[KEY_A]
    assert a["same_day_only"] is True and "skipped pills" in a["text"]["sentences"][0].lower() and "bigger sugar swings after supper" in a["text"]["sentences"][0] and a["text"]["source"] == "code_text"
    assert "glucose" not in json.dumps(rows).lower() and "dinner" not in json.dumps(rows).lower()


def test_a_second_run_of_the_second_patient_writes_nothing(tmp_path):
    cfgp = make_pi_patient(tmp_path / "p3")
    pirun.main(["--config", str(cfgp), "--root", str(tmp_path), "--no-audit"])
    cfg = PiConfig.from_yaml(cfgp, tmp_path)
    before = json.dumps(PiStore(cfg.paths["db_path"], readonly=True).dump(), sort_keys=True)
    pirun.main(["--config", str(cfgp), "--root", str(tmp_path), "--no-audit"])
    assert json.dumps(PiStore(cfg.paths["db_path"], readonly=True).dump(), sort_keys=True) == before
