"""Calendar weeks (pi_spec.md 4): Monday to Sunday in the patient's timezone, named by ISO week."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Week:
    iso: str            # 2026-W38
    start: date         # Monday
    end: date           # Sunday


def week_of_date(d: date) -> Week:
    year, number, _ = d.isocalendar()
    monday = d - timedelta(days=d.weekday())
    return Week(f"{year}-W{number:02d}", monday, monday + timedelta(days=6))


def week_of(ts: str | datetime, tz: ZoneInfo) -> Week:
    """The week that contains a moment, read in the patient's timezone (an entry belongs to the week of its as_of, not of its local date)."""
    dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
    return week_of_date(dt.astimezone(tz).date())


def week_end_time(week: Week, tz: ZoneInfo) -> datetime:
    """When the weekly job runs: Sunday 23:59:59 in the patient's zone."""
    return datetime.combine(week.end, time(23, 59, 59), tzinfo=tz)


def weeks_between(first: Week, last: Week) -> list[Week]:
    out, w = [], first
    while w.start <= last.start:
        out.append(w)
        w = week_of_date(w.start + timedelta(days=7))
    return out


def days_present(week: Week, first_day: date, last_day: date) -> int:
    """How many days of the week lie inside the data span."""
    lo, hi = max(week.start, first_day), min(week.end, last_day)
    return max(0, (hi - lo).days + 1)
