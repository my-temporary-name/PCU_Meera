"""Lookback resolution (spec 3, Amendments 7 and 10): a lookback kind becomes absolute times for one hand-off. No clock of its own: everything is relative to
`opened_at`, in the patient's time zone (the offset in `opened_at` only when no zone is configured). Rulebook Lookup never checks whether data exists in a window."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from v0_code.rulebook_lookup.grammar import GrammarError, LOOKBACK_KINDS

EVENING_START_HOUR = 18          # the evening window is 18:00 to 24:00 (spec 3)
RECORD_PREVIOUS_NIGHT = "latest_sleep_record_at_or_before_open"


def local_time(opened_at: str, tz_name: str | None) -> datetime:
    dt = datetime.fromisoformat(opened_at)
    if dt.tzinfo is None:
        raise GrammarError(f"opened_at has no UTC offset: {opened_at!r}")
    return dt.astimezone(ZoneInfo(tz_name)) if tz_name else dt


def _midnight(d: date, tz) -> datetime:
    return datetime.combine(d, time(0, 0), tzinfo=tz)


def _shift_minutes(dt: datetime, minutes: int) -> datetime:
    """Absolute (elapsed-time) arithmetic, then back to the local zone."""
    return (dt.astimezone(timezone.utc) + timedelta(minutes=minutes)).astimezone(dt.tzinfo)


def resolve_lookback(kind: str, value: int | None, opened_at: str, tz_name: str | None) -> dict:
    if kind not in LOOKBACK_KINDS:
        raise GrammarError(f"unknown lookback_kind {kind!r}")
    o = local_time(opened_at, tz_name)
    tz, d = o.tzinfo, o.date()
    if kind == "minutes_before_open":
        return _win(_shift_minutes(o, -value), o)
    if kind == "days_ending_at_open":
        return _win(_midnight(d - timedelta(days=value - 1), tz), o)
    if kind == "same_calendar_day":
        return _win(_midnight(d, tz), o)
    if kind == "previous_calendar_day":
        return _win(_midnight(d - timedelta(days=1), tz), _midnight(d, tz))
    if kind == "previous_night":
        return {"record": RECORD_PREVIOUS_NIGHT, "includes_after_open": False}
    if kind == "previous_evening":
        today = datetime.combine(d, time(EVENING_START_HOUR, 0), tzinfo=tz)
        if today < o:                                               # that evening started before opened_at: it is the one to look at (cut at opened_at)
            return _win(today, min(_midnight(d + timedelta(days=1), tz), o))
        yesterday = datetime.combine(d - timedelta(days=1), time(EVENING_START_HOUR, 0), tzinfo=tz)
        return _win(yesterday, _midnight(d, tz))
    if kind == "at_open":
        return {"at": o.isoformat(), "includes_after_open": False}
    end = _shift_minutes(o, value)                                    # minutes_around_open
    return {"start": _shift_minutes(o, -value).isoformat(), "end": end.isoformat(), "includes_after_open": True, "earliest_evaluation_time": end.isoformat()}


def _win(start: datetime, end: datetime) -> dict:
    return {"start": start.isoformat(), "end": end.isoformat(), "includes_after_open": False}
