"""State Engine pure rules (spec 6: R6 position, R7 run counting, R8 opening, R9/R10 closing). No store, no model."""

import pytest

from v0_code.state_engine.position import percentile_label, sd_position
from v0_code.state_engine.runs import Tracker

SD = (1.0, 2.0, 4.0)
PCT = (0.35, 0.15, 0.05)


# ---- R6 position -------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("value,label,z", [(100.0, "within", 0.0), (109.9, "within", 0.99), (110.0, "slightly above", 1.0), (119.9, "slightly above", 1.99), (120.0, "clearly above", 2.0),
                                           (139.9, "clearly above", 3.99), (140.0, "far above", 4.0), (90.0, "slightly below", -1.0), (60.0, "far below", -4.0), (80.0, "clearly below", -2.0)])
def test_sd_position_labels_by_absolute_z_with_direction(value, label, z):
    p = sd_position(value, 100.0, 10.0, SD)
    assert p["label"] == label and p["z"] == pytest.approx(z, abs=0.011)


def test_boundaries_belong_to_the_larger_label_and_within_has_no_direction():
    assert sd_position(110.0, 100.0, 10.0, SD)["level"] == "slightly"
    w = sd_position(105.0, 100.0, 10.0, SD)
    assert (w["level"], w["direction"], w["label"]) == ("within", None, "within")


def test_a_zero_spread_is_far_unless_the_value_equals_the_median():
    assert sd_position(5.0, 5.0, 0.0, SD)["label"] == "within"
    assert sd_position(6.0, 5.0, 0.0, SD)["label"] == "far above" and sd_position(4.0, 5.0, 0.0, SD)["label"] == "far below"


@pytest.mark.parametrize("share,label", [(0.50, "within"), (0.36, "within"), (0.35, "slightly"), (0.16, "slightly"), (0.15, "clearly"), (0.06, "clearly"), (0.05, "far"), (0.0, "far")])
def test_percentile_labels_use_the_share_of_earlier_days_at_least_as_bad(share, label):
    assert percentile_label(share, PCT) == label


# ---- R7 - R10 persistence ----------------------------------------------------------------------------------------------------------------------

def feed(t, seq, n_open=2, n_close=2):
    """seq: (level, direction) per new reading; returns the events per reading."""
    out = []
    for lvl, d in seq:
        out.append(t.new_reading(lvl, d, n_open, n_close))
    return out


def test_two_readings_at_clearly_in_the_same_direction_open_an_item_on_the_second():
    t = Tracker(open_rank=2, close_rank=1)
    ev = feed(t, [("clearly", "above"), ("clearly", "above")])
    assert [e["opened"] for e in ev] == [False, True] and t.run_count == 2 and t.open


def test_a_reading_within_slightly_resets_the_run_before_it_opens():
    t = Tracker(2, 1)
    ev = feed(t, [("clearly", "above"), ("slightly", "above"), ("clearly", "above")])
    assert [e["opened"] for e in ev] == [False, False, False] and t.run_count == 1 and not t.open


def test_a_reading_in_the_other_direction_starts_a_new_run_at_one():
    t = Tracker(2, 1)
    feed(t, [("clearly", "above"), ("clearly", "below")])
    assert (t.run_direction, t.run_count) == ("below", 1)
    assert feed(t, [("far", "below")])[0]["opened"]


def test_one_reading_is_enough_when_n_open_is_one_and_a_far_value_opens_at_once():
    t = Tracker(2, 1)
    assert t.new_reading("clearly", "below", 1, 1)["opened"]
    t2 = Tracker(2, 1)
    assert t2.new_reading("far", "above", 2, 2, severe=True)["opened"]                      # severe: no persistence needed


def test_an_open_item_closes_after_n_close_consecutive_readings_at_slightly_or_better():
    t = Tracker(2, 1)
    feed(t, [("clearly", "above"), ("clearly", "above")])
    ev = feed(t, [("slightly", "above"), ("within", None)])
    assert [e["closed"] for e in ev] == [False, True] and not t.open and t.run_count == 0


def test_a_worse_reading_resets_the_close_count():
    t = Tracker(2, 1)
    feed(t, [("clearly", "above"), ("clearly", "above"), ("slightly", "above")])
    assert t.close_count == 1
    feed(t, [("clearly", "above")])
    assert t.close_count == 0 and t.open
    ev = feed(t, [("within", None), ("within", None)])
    assert ev[-1]["closed"]


def test_a_reading_in_the_opposite_direction_counts_toward_closing_the_open_item():
    t = Tracker(2, 1)
    feed(t, [("clearly", "above"), ("clearly", "above")])
    ev = feed(t, [("clearly", "below"), ("clearly", "below")])                                # leaves the item's direction twice: it closes, and a new run builds
    assert ev[-1]["closed"] and t.run_direction == "below"


def test_after_closing_a_new_deviation_opens_a_new_item():
    t = Tracker(2, 1)
    feed(t, [("clearly", "above"), ("clearly", "above"), ("within", None), ("within", None)])
    ev = feed(t, [("clearly", "above"), ("clearly", "above")])
    assert ev[-1]["opened"] and t.open


def test_one_reading_closes_a_daily_item_when_n_close_is_one():
    t = Tracker(2, 1)
    assert t.new_reading("far", "below", 1, 1)["opened"]
    assert t.new_reading("slightly", "below", 1, 1)["closed"]


def test_going_stale_drops_the_run_and_closes_an_open_item():
    t = Tracker(2, 1)
    feed(t, [("clearly", "above")])
    assert t.go_stale() == {"closed": False} and t.run_count == 0
    feed(t, [("clearly", "above"), ("clearly", "above")])
    assert t.open and t.go_stale() == {"closed": True} and t.run_count == 0 and not t.open   # spec R3 / property 6: a stale value never keeps an item open
