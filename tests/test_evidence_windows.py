"""Evidence windows (spec 3.1 rules 5 to 8): anchored to the outcome date or the unit start, never to the hand-off."""

from datetime import date, datetime, timedelta, timezone

import pytest

from v0_code.evidence_engine.windows import window_for

TZ = timezone(timedelta(hours=5, minutes=30))
EVENING = ("18:00", "24:00")


def dt(d, h=0, m=0):
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)


D = date(2026, 9, 17)


def w(tag, unit, start, shift=0, shifted=False, excludes=False):
    return window_for(tag, unit, start, D, shift, shifted, excludes, EVENING)


def test_day_windows_for_a_meal_unit_stop_at_the_unit_start():
    x = w("1d", "meal", dt(D, 21, 28))
    assert x.dates == (D,) and x.lo == dt(D) and x.hi == dt(D, 21, 28) and x.includes_unit_date
    x = w("3d", "meal", dt(D, 21, 28))
    assert x.dates == (D - timedelta(days=2), D - timedelta(days=1), D) and x.lo == dt(D - timedelta(days=2))
    assert w("same_day", "meal", dt(D, 21, 28)).dates == (D,)
    assert w("2d", "reading", dt(D, 8, 0)).dates == (D - timedelta(days=1), D)


def test_day_windows_for_a_day_unit_cover_whole_dates():
    x = w("2d", "day", dt(D))
    assert x.dates == (D - timedelta(days=1), D) and x.includes_unit_date and x.hi == dt(D + timedelta(days=1))


def test_shift_counts_back_from_the_day_before_only_for_shifted_tags():
    y = D - timedelta(days=1)
    assert w("same_day", "day", dt(D), shift=-1, shifted=True).dates == (y,)
    assert not w("same_day", "day", dt(D), shift=-1, shifted=True).includes_unit_date
    assert w("2d", "day", dt(D), shift=-1, shifted=True).dates == (y - timedelta(days=1), y)
    assert w("prev_day", "day", dt(D), shift=-1, shifted=False).dates == (y,)            # not shifted: the day before the outcome date


def test_prev_day_and_at_open_and_excludes():
    x = w("prev_day", "day", dt(D))
    assert x.dates == (D - timedelta(days=1),) and not x.includes_unit_date and x.hi == dt(D)
    assert w("at_open", "reading", dt(D, 8, 0)).dates == (D,)
    e = w("7d", "day", dt(D), excludes=True)
    assert e.dates == tuple(D - timedelta(days=i) for i in range(7, 0, -1)) and not e.includes_unit_date


def test_minute_windows_end_at_the_unit_start():
    x = w("720m", "day", dt(D))
    assert x.lo == dt(D) - timedelta(hours=12) and x.hi == dt(D) and x.dates == () and not x.includes_unit_date
    x = w("60m", "hour", dt(D, 15, 0))
    assert x.lo == dt(D, 14, 0) and x.hi == dt(D, 15, 0)


def test_prev_evening_is_the_evening_before_the_anchor_date():
    x = w("prev_evening", "day", dt(D))
    assert x.lo == dt(D - timedelta(days=1), 18, 0) and x.hi == dt(D) and x.dates == (D - timedelta(days=1),)


def test_prev_night_is_a_record_rule():
    assert w("prev_night", "meal", dt(D, 21, 28)).kind == "prev_night"


def test_unknown_tag_raises():
    with pytest.raises(ValueError):
        w("sometimes", "day", dt(D))
