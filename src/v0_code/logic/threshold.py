"""Component 2 logic: deterministic threshold lookup and status assignment."""

from datetime import date

from v0_code.graph.state import Reading, ThresholdResult

# Data biomarker name -> threshold-table biomarker name (when they differ).
# cgm readings are judged against the fasting_glucose row (no cgm-specific row exists).
THRESHOLD_ALIASES = {"cgm_glucose_reading": "fasting_glucose", "continuous_heart_rate": "resting_heart_rate"}

# The only heart-rate reference is for *resting* HR, so these streams are judged only when at rest.
RESTING_ONLY = {"continuous_heart_rate"}


def age_on(dob: str, on: str) -> int:
    born, day = date.fromisoformat(dob), date.fromisoformat(on[:10])
    return day.year - born.year - ((day.month, day.day) < (born.month, born.day))


def _group_matches(group: str, age: int, sex: str) -> bool:
    if group in ("all_adult", f"adult_{sex}"):
        return True
    if group.startswith("adult_"):
        return False
    low, _, high = group.partition("-")
    return int(low) <= age <= (10**6 if high == "plus" else int(high))


def select_row(
    rows: list[dict[str, str]], biomarker: str, age: int, sex: str
) -> dict[str, str] | None:
    name = THRESHOLD_ALIASES.get(biomarker, biomarker)
    for row in rows:
        if row["biomarker"] in (name, f"{name}_{sex}") and _group_matches(
            row["age_group"], age, sex
        ):
            return row
    return None


def _num(row: dict[str, str], key: str) -> float | None:
    raw = row.get(key, "")
    return float(raw) if raw != "" else None


def assign_status(value: float, row: dict[str, str]) -> str:
    """Side-based tiering. Only statuses the row can support are emitted (no critical tiers exist)."""
    n_low, n_high = _num(row, "normal_low"), _num(row, "normal_high")
    b_low, b_high = _num(row, "borderline_low"), _num(row, "borderline_high")
    abn_high = _num(row, "abnormal_high")

    if (n_low is None or value >= n_low) and (n_high is None or value <= n_high):
        return "normal"

    if n_low is not None and value < n_low:
        has_band = b_low is not None and b_high is not None and b_high < n_low
        return "borderline_low" if has_band and value >= b_low else "low"

    has_band = b_low is not None and b_high is not None and n_high is not None and b_low >= n_high
    if abn_high is not None and value >= abn_high:
        return "high"
    return "borderline_high" if has_band else "high"


def skip_reason(reading: Reading, steps_by_hour: dict[str, float]) -> str | None:
    """Why a plausible reading has no applicable reference range, or None if it should be evaluated."""
    if reading.biomarker in RESTING_ONLY:
        steps = steps_by_hour.get(reading.timestamp[:13])
        if steps is None:
            return "no activity data to confirm resting state"
        if steps > 0:
            return "not at rest (steps > 0 in that hour)"
    return None


def evaluate_threshold(
    reading: Reading, rows: list[dict[str, str]], dob: str, sex: str
) -> ThresholdResult | None:
    row = select_row(rows, reading.biomarker, age_on(dob, reading.timestamp), sex)
    if row is None:
        return None
    return ThresholdResult(
        event_id=reading.event_id,
        biomarker=reading.biomarker,
        timestamp=reading.timestamp,
        value=reading.value,
        age_group_used=row["age_group"],
        status=assign_status(reading.value, row),
        confidence_source="",
    )
