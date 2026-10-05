"""State Engine inputs and usuals: availability (spec 3.1) and the reading-level usual (spec 4.2b), without a store."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from v0_code.state_engine.config import StateConfig
from v0_code.state_engine.inputs import availability, end_of_day, parse_ts
from v0_code.state_engine.usual import ReadingUsual, bucket_of, percentile, summarize

TZ = ZoneInfo("Asia/Kolkata")
ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


def dt(s):
    return datetime.fromisoformat(s)


# ---- 3.1 availability ----------------------------------------------------------------------------------------------------------------------------

def test_a_timestamped_value_is_available_from_its_own_timestamp_in_the_patients_timezone():
    vt, av = availability("timestamp", "2026-09-17T07:00:00+05:30", TZ)
    assert vt == av == dt("2026-09-17T07:00:00+05:30")
    vt, av = availability("timestamp", "2026-09-17T01:30:00+00:00", TZ)                       # a UTC stamp is read as local time in the patient's zone
    assert av.isoformat() == "2026-09-17T07:00:00+05:30"


def test_a_date_only_record_follows_the_streams_rule():
    assert availability("21:00", "2026-09-17", TZ)[1].isoformat() == "2026-09-17T21:00:00+05:30"
    assert availability("end_of_day", "2026-09-17", TZ)[1].isoformat() == "2026-09-18T00:00:00+05:30"
    assert availability({"morning": "12:00", "evening": "21:00"}, "2026-09-17", TZ, "evening")[1].isoformat() == "2026-09-17T21:00:00+05:30"


def test_a_stream_that_says_timestamp_but_has_only_a_date_is_end_of_day():
    assert availability("timestamp", "2026-09-17", TZ)[1].isoformat() == "2026-09-18T00:00:00+05:30"


def test_a_timed_record_is_never_made_to_wait_for_a_clock_time_fallback():
    assert availability("21:00", "2026-09-17T09:00:00+05:30", TZ)[1].isoformat() == "2026-09-17T09:00:00+05:30"


def test_a_date_only_string_is_midnight_of_that_date_in_the_patients_zone_whatever_the_machine_zone():
    d, has_time = parse_ts("2026-09-17", TZ)
    assert not has_time and d.isoformat() == "2026-09-17T00:00:00+05:30"
    assert end_of_day(d).isoformat() == "2026-09-18T00:00:00+05:30"


# ---- 4.2b the reading-level usual -----------------------------------------------------------------------------------------------------------------

def test_buckets_are_the_nearest_multiple_with_halves_rounding_up():
    assert [bucket_of(m, 15) for m in (0, 7, 7.5, 62, 77, 82.4, 82.5, 120)] == [0, 0, 15, 60, 75, 75, 90, 120]


def test_percentiles_interpolate_between_ranks():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(vals, 50) == 3.0 and percentile(vals, 10) == pytest.approx(1.4) and percentile(vals, 90) == pytest.approx(4.6)
    s = summarize([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
    assert s["n"] == 8 and s["median"] == 4.5 and s["sd"] == 2.0                             # population SD, like the baseline's profile


def make(readings, meals=(), kinds=("dinner",)):
    """readings: (day_index, 'HH:MM', value) on a 15-minute grid in the patient's zone."""
    rows = []
    for d, hm, v in readings:
        h, m = map(int, hm.split(":"))
        t = datetime(2026, 1, 1, h, m, tzinfo=TZ) + timedelta(days=d)
        rows.append((d, h * 60 + m, v, t))
    rows.sort(key=lambda r: r[3])
    return ReadingUsual("g", rows, list(meals), kinds, 180, 15)


def test_the_clock_time_usual_uses_only_earlier_days_within_the_band_and_wraps_over_midnight():
    ru = make([(d, hm, 100.0 + d) for d in range(5) for hm in ("22:15", "22:30", "22:45", "23:00", "23:15", "23:30")])
    u = ru.clock_time(3, 22 * 60 + 45, 30)                                                   # days 0-2 only; 22:15..23:15 are within 30 minutes of 22:45
    assert u["n"] == 15 and u["median"] == 101.0 and u["context"] == {"time_of_day": "22:45", "band_minutes": 30}
    assert ru.clock_time(0, 22 * 60 + 45, 30) is None                                        # nothing before day 0
    wrap = make([(d, hm, 50.0) for d in range(3) for hm in ("23:45", "00:00", "00:15")])
    assert wrap.clock_time(2, 0, 30)["n"] == 6                                               # 23:45 is 15 minutes from 00:00 across midnight


def test_the_meal_relative_usual_matches_the_same_minutes_after_a_meal_of_the_same_kind():
    meals, rd = [], []
    for d in range(4):
        mt = datetime(2026, 1, 1, 20, 10, tzinfo=TZ) + timedelta(days=d)                  # dinner at 20:10 every day
        meals.append((mt, "dinner"))
        meals.append((mt - timedelta(hours=12), "breakfast"))
        for k in range(0, 8):
            rd.append((d, (mt + timedelta(minutes=5 + 15 * k)).strftime("%H:%M"), 100.0 + 10 * k + d))
    ru = make([(d, hm, v) for d, hm, v in rd], meals=meals)
    u = ru.meal_relative(3, "dinner", 65.0)                                                  # 65 min -> the 60-minute bucket: readings 20:15 + 15 k at k = 4 -> 21:15 = 65 min after
    assert u["n"] == 3 and u["context"] == {"meal_kind": "dinner", "minutes_since_meal": 60}
    assert u["median"] == 140.0 + 1.0                                                        # days 0..2: 140, 141, 142
    assert ru.meal_relative(0, "dinner", 65.0) is None and ru.meal_relative(3, "lunch", 65.0) is None


def test_the_meal_kind_is_a_label_text_match_in_the_configured_order():
    ru = make([(0, "12:00", 1.0)], kinds=("breakfast", "lunch", "dinner"))
    assert [ru.kind_of(x) for x in ("festive_dinner", "light_breakfast", "snack_lunch", "late_night_function_meal")] == ["dinner", "breakfast", "lunch", None]


# ---- config ---------------------------------------------------------------------------------------------------------------------------------

def test_the_defaults_come_from_the_yaml_and_the_config_version_is_the_hash_of_the_text():
    c = StateConfig.from_yaml(ROOT / "config" / "state_meera_iyer_v1.yaml", root=ROOT)
    assert (c.tick_minutes, c.min_history_days, c.min_samples_usual, c.thresholds_sd, c.thresholds_percentile) == (15, 14, 30, (1.0, 2.0, 4.0), (0.35, 0.15, 0.05))
    assert (c.open_label, c.close_label, c.n_open, c.n_close, c.severe_position) == ("clearly", "slightly", 2, 2, "far")
    assert c.timezone == "Asia/Kolkata" and c.version.startswith("meera_iyer_v1-state-") and c.baseline.version.startswith("meera_iyer_v1-")
    assert [s.key for s in c.streams][:2] == ["glucose", "heart_rate"] and c.stream("sleep_duration").role == "sleep"


def test_an_unknown_position_label_or_glucose_basis_is_refused(tmp_path):
    base = (ROOT / "config" / "state_meera_iyer_v1.yaml").read_text().replace("baseline_config: config/patient_meera_iyer_v1.yaml", f"baseline_config: {ROOT / 'config/patient_meera_iyer_v1.yaml'}")
    (tmp_path / "bad1.yaml").write_text(base.replace("open_label: clearly", "open_label: gigantic"))
    (tmp_path / "bad2.yaml").write_text(base.replace("usual_basis: meal_relative_with_clock_fallback", "usual_basis: vibes"))
    for f in ("bad1.yaml", "bad2.yaml"):
        with pytest.raises(ValueError):
            StateConfig.from_yaml(tmp_path / f)


# ---- adverse directions (config) ------------------------------------------------------------------------------------------------------------------

def test_every_measure_that_can_open_an_item_names_its_adverse_directions():
    c = StateConfig.from_yaml(ROOT / "config" / "state_meera_iyer_v1.yaml", root=ROOT)
    want = {"cgm_glucose_reading": ("above",), "continuous_heart_rate": ("above",), "resting_heart_rate": ("above",), "blood_pressure": ("above",), "sleep_duration": ("below",),
            "step_count": ("below",), "medication_adherence": ("below",), "hydration": ("below",), "screen_time": ("above",), "sedentary_time": ("above",)}
    assert {s.name: s.adverse_directions for s in c.streams if s.adverse_directions} == want
    assert c.stream("mood_state").adverse_directions == () and c.stream("hba1c").adverse_directions == ()          # position_method none: no direction to judge


@pytest.mark.parametrize("replacement", ["n_open: 2, n_close: 2}", "adverse_directions: [], n_open: 2, n_close: 2}", "adverse_directions: [sideways], n_open: 2, n_close: 2}"], ids=["missing", "empty", "unknown"])
def test_a_stream_without_valid_adverse_directions_is_refused(tmp_path, replacement):
    text = (ROOT / "config" / "state_meera_iyer_v1.yaml").read_text().replace("baseline_config: config/patient_meera_iyer_v1.yaml", f"baseline_config: {ROOT / 'config/patient_meera_iyer_v1.yaml'}")
    bad = text.replace("adverse_directions: [above], n_open: 2, n_close: 2, cleaning: baseline_glucose}", replacement[:-1] + ", cleaning: baseline_glucose}", 1)
    assert bad != text
    (tmp_path / "bad.yaml").write_text(bad)
    with pytest.raises(ValueError, match="adverse_directions"):
        StateConfig.from_yaml(tmp_path / "bad.yaml")
