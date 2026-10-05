from v0_code.logic import stream_tables as st


def test_direction_uses_half_sd_band_and_flags_insufficient_history():
    history = [100.0 + (i % 2) * 10 for i in range(20)]  # SD 5 -> band 2.5
    assert st.direction(110.0, 100.0, history, "x") == "up"
    assert st.direction(101.0, 100.0, history, "x") == "flat"
    assert st.direction(90.0, 100.0, history, "x") == "down"
    assert st.direction(110.0, 100.0, history[:5], "x") == "insufficient_data"  # too little history -> never a guess
    assert st.direction(None, 100.0, history, "x") == "insufficient_data"


def test_cumulative_delta_excludes_window_and_is_null_when_unreliable():
    assert st.cumulative_delta(10.0, [4.0, 6.0], reliable=True) == 5.0
    assert st.cumulative_delta(10.0, [4.0, 6.0], reliable=False) is None
    assert st.cumulative_delta(10.0, [], reliable=True) is None


def test_week_value_needs_enough_days():
    assert st.window_mean([1.0, 2.0, 3.0, None, None, None, None]) is None  # 3 of 7 days
    assert st.window_mean([1.0, 2.0, 3.0, 4.0, None, None, None]) == 2.5


def test_candidates_split_same_opposite_flat_unavailable():
    c = st.candidates_from_directions({"glucose": "up", "sleep": "up", "steps": "down", "mood": "flat", "x": "insufficient_data"})
    assert c["same_direction"] == ["sleep"] and c["opposite_direction"] == ["steps"] and c["flat"] == ["mood"] and c["unavailable"] == ["x"]
    assert st.candidates_from_directions({"glucose": "flat", "sleep": "up"})["moved_while_glucose_flat"] == ["sleep"]


def test_confidence_rule():
    assert st.confidence(True, 100.0) == "high" and st.confidence(True, 90.0) == "high"
    assert st.confidence(True, 89.9) == "moderate" and st.confidence(True, 70.0) == "moderate"
    assert st.confidence(True, 69.9) == "low" and st.confidence(False, 100.0) == "low"


def test_adherence_aggregate_counts_taken_over_expected():
    day = {"adherence": {"per_medication": {"metformin": "taken", "amlodipine": "missed"}}}
    out = st.agg_adherence([("d1", day), ("d2", day)], None, {})
    assert out["per_medication"]["metformin"] == {"taken": 2, "expected": 2} and out["overall_pct"] == 50.0


def test_mood_aggregate_counts_categories_per_time_block():
    days = [("d1", {"mood": {"morning": {"category": "calm_stable"}, "evening": {"category": "anxious"}}}),
            ("d2", {"mood": {"morning": {"category": "calm_stable"}}})]
    out = st.agg_mood(days, None, {})
    assert out["morning"]["counts"] == {"calm_stable": 2} and out["evening"]["counts"] == {"anxious": 1}
