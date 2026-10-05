"""Local time: the patient's timezone comes from the baseline config (`patient.timezone`), and part of day from config bands."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


def timezone_from_baseline(path: str | Path) -> str:
    return yaml.safe_load(Path(path).read_text())["patient"]["timezone"]


def to_local(ts: str | datetime, tz: ZoneInfo) -> datetime:
    return (datetime.fromisoformat(ts) if isinstance(ts, str) else ts).astimezone(tz)


def part_of_day(dt: datetime, bands: dict) -> str:
    """`bands`: name -> [from_hour, to_hour) in local hours (config)."""
    h = dt.hour
    for name, (a, b) in bands.items():
        if a <= h < b:
            return name
    raise ValueError(f"hour {h} is in no part-of-day band")
