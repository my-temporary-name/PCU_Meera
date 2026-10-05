"""Exposure windows (spec 3.1 rules 5 to 8). Every window is anchored to the outcome date (day outcomes) or the unit start (meal, hour and reading outcomes),
never to the hand-off's `opened_at`. The packet's `resolved_window` is not used."""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class Window:
    kind: str                    # dates | minutes | prev_night
    dates: tuple                 # local dates the window covers (date-resolution values count when their date is in here)
    lo: datetime | None          # timestamped values count when lo <= value time <= hi (hi is the unit start for meal, hour and reading units)
    hi: datetime | None
    includes_unit_date: bool     # the window includes the outcome unit's own date
    bounded: bool = False        # lo..hi is a time-of-day bound (minute and evening windows), not just the whole dates


def _mid(d: date, tz) -> datetime:
    return datetime.combine(d, time(0, 0), tzinfo=tz)


def _hhmm(s: str, d: date, tz) -> datetime:
    h, m = (int(x) for x in s.split(":"))
    return _mid(d, tz) + timedelta(hours=h, minutes=m)


def window_for(tag: str, unit: str, start: datetime, unit_date: date, shift_days: int, shifted: bool, excludes: bool, evening: tuple[str, str]) -> Window:
    """`shifted`: the tag is one of the library's shifted tags AND the outcome has a non-zero exposure shift (windows are counted back from the day before).
    `excludes`: the window stops the day before the outcome day (a 7-day window ending yesterday)."""
    tz = start.tzinfo
    anchor = unit_date + timedelta(days=shift_days) if shifted and shift_days else unit_date
    day_unit = unit == "day"

    def end_of(last: date) -> datetime:
        nxt = _mid(last + timedelta(days=1), tz)
        return nxt if day_unit else min(start, nxt)

    m = re.fullmatch(r"(\d+)d", tag)
    if m or tag == "same_day":
        n = int(m.group(1)) if m else 1
        if excludes:
            dates = tuple(anchor - timedelta(days=i) for i in range(n, 0, -1))
            return Window("dates", dates, _mid(dates[0], tz), _mid(anchor, tz), False)
        dates = tuple(anchor - timedelta(days=i) for i in range(n - 1, -1, -1))
        return Window("dates", dates, _mid(dates[0], tz), end_of(dates[-1]), unit_date in dates)
    if tag == "prev_day":
        d = anchor - timedelta(days=1)
        return Window("dates", (d,), _mid(d, tz), _mid(anchor, tz), False)
    if tag == "at_open":
        return Window("dates", (unit_date,), _mid(unit_date, tz), end_of(unit_date), True)
    if tag == "prev_evening":
        d = anchor - timedelta(days=1)
        lo = _hhmm(evening[0], d, tz)
        hi = _hhmm(evening[1], d, tz)
        return Window("dates", (d,), lo, min(hi, start) if not day_unit else hi, False, True)
    m = re.fullmatch(r"(?:pm)?(\d+)m", tag)
    if m:
        return Window("minutes", (), start - timedelta(minutes=int(m.group(1))), start, False, True)
    if tag == "prev_night":
        return Window("prev_night", (), None, start, False)
    raise ValueError(f"unknown lookback tag {tag!r}")
