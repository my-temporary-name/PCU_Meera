"""Short-Range Event Linker: deterministic temporal-proximity pairings for glucose events only.

For each cgm_glucose_reading tagged high/low, checks whether each candidate type happened
within its own window. No causal claim, no scoring — only what happened nearby, in time.

Per-candidate-type matching policy (see CLAUDE.md for the rationale):
- meal, activity, context_event: emit one pairing per matching item found in the window
  (there can be several distinct, independent occurrences).
- medication: one pairing per medication logged that calendar date (time not considered,
  per spec — adherence has no timestamp).
- heart_rate: one pairing summarizing all plausible readings within +/-120 min (continuous
  15-min stream; emitting every sample would just be redundant oversampling).
- sleep, mood, diary: at most one pairing (one sleep row per night, one mood row per
  time-block, one diary entry per day).
"""

import bisect
from datetime import datetime, timedelta, timezone

from v0_code.graph.state import Pairing, ThresholdResult

IST = timezone(timedelta(hours=5, minutes=30))

MEAL_WINDOW_MIN = 150
MEDICATION_WINDOW_MIN = 240  # not applied: adherence has no timestamp, per spec
ACTIVITY_WINDOW_MIN = 90
HEART_RATE_WINDOW_MIN = 120


def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _lag(glucose_dt: datetime, candidate_ts: str | None) -> float | None:
    if candidate_ts is None:
        return None
    return round((glucose_dt - _dt(candidate_ts)).total_seconds() / 60, 1)


def _mood_block(hour: int) -> str:
    """Matches the diary's own 3-block scheme (morning 5-12, afternoon/evening 12-20, night 20-5)."""
    if 5 <= hour <= 11:
        return "morning"
    if 12 <= hour <= 19:
        return "afternoon"
    return "evening"


def find_pairings(
    reading: ThresholdResult,
    meals: list[dict],
    adherence_by_date: dict[str, list[dict]],
    steps_by_hour: dict[str, float],
    hr_times: list[int],
    hr_values: list[float],
    sleep_by_date: dict[str, dict],
    context_events_by_date: dict[str, list[dict]],
    diary_by_date: dict[str, dict],
    mood_by_date_block: dict[str, dict],
) -> list[Pairing]:
    t = _dt(reading.timestamp)
    date = reading.timestamp[:10]
    out: list[Pairing] = []

    def add(candidate_type: str, candidate_id: str, candidate_ts: str | None, summary: str) -> None:
        out.append(
            Pairing(
                glucose_event_id=reading.event_id,
                glucose_timestamp=reading.timestamp,
                glucose_value=reading.value,
                glucose_status=reading.status,
                candidate_type=candidate_type,
                candidate_id=candidate_id,
                candidate_timestamp=candidate_ts,
                lag_minutes=_lag(t, candidate_ts),
                candidate_summary=summary,
            )
        )

    # Meal: 0-150 min before.
    window_start = t - timedelta(minutes=MEAL_WINDOW_MIN)
    for m in meals:
        mt = _dt(m["timestamp"])
        if window_start <= mt <= t:
            add("meal", m["id"], m["timestamp"], f"{m['label']}: {m['food']}".strip(": "))

    # Medication/adherence: same day, no time filter (adherence rows carry no timestamp).
    for a in adherence_by_date.get(date, []):
        add("medication", a["id"], None, f"{a['medication']} {'taken' if a['taken'] else 'missed'}")

    # Steps/activity: hourly buckets starting within 0-90 min before, with steps > 0.
    window_start = t - timedelta(minutes=ACTIVITY_WINDOW_MIN)
    hour = t.replace(minute=0, second=0, microsecond=0)
    for k in range(2):  # 90 min can only reach back into the current and previous hour bucket
        bucket_start = hour - timedelta(hours=k)
        if bucket_start < window_start or bucket_start > t:
            continue
        key = bucket_start.isoformat()[:13]
        steps = steps_by_hour.get(key)
        if steps:
            add("activity", key, bucket_start.isoformat(), f"{steps:g} steps that hour")

    # Continuous heart rate: one summary pairing over +/-120 min (readings every 15 min).
    lo, hi = t - timedelta(minutes=HEART_RATE_WINDOW_MIN), t + timedelta(minutes=HEART_RATE_WINDOW_MIN)
    i = bisect.bisect_left(hr_times, int(lo.timestamp()))
    j = bisect.bisect_right(hr_times, int(hi.timestamp()))
    if j > i:
        window_vals = hr_values[i:j]
        nearest_idx = min(range(i, j), key=lambda x: abs(hr_times[x] - int(t.timestamp())))
        nearest_ts = datetime.fromtimestamp(hr_times[nearest_idx], tz=IST).isoformat()
        add(
            "heart_rate",
            f"hr_window_{reading.event_id}",
            nearest_ts,
            f"avg {sum(window_vals) / len(window_vals):.1f} bpm ({min(window_vals):g}-{max(window_vals):g}, n={len(window_vals)})",
        )

    # Sleep: previous night, same calendar date (the source already aligns the night to the wake date).
    sleep = sleep_by_date.get(date)
    if sleep:
        add("sleep", sleep["id"], sleep["timestamp"], f"{sleep['hours']:g}h ({sleep['quality']})")

    # Context event / diary: same calendar date.
    for c in context_events_by_date.get(date, []):
        summary = c["description"] + (f" — {c['note']}" if c["note"] else "")
        add("context_event", c["id"], c["timestamp"], f"{c['category']}: {summary}")
    diary = diary_by_date.get(date)
    if diary and (diary["title"] or diary["lines"]):
        add("diary", f"diary_{date}", None, diary["title"] or diary["lines"][0])

    # Mood: same time-block as the glucose reading's hour.
    mood = mood_by_date_block.get(f"{date}|{_mood_block(t.hour)}")
    if mood:
        add("mood", mood["id"], None, f"{mood['label']} ({mood['category']})")

    return out
