"""Component 1 logic: deterministic plausibility check with templated reasons."""

from v0_code.graph.state import FilterResult, Reading

ACTIVE_CONTEXT_BIOMARKERS = {
    "fasting_glucose",
    "cgm_glucose_reading",
    "blood_pressure_systolic",
    "blood_pressure_diastolic",
}
RESTING_CONTEXT_BIOMARKERS = {"resting_heart_rate", "continuous_heart_rate"}
# No dedicated bounds row exists for the 15-minute stream; physiological limits are the same.
BOUNDS_ALIASES = {"continuous_heart_rate": "resting_heart_rate"}
BP_BIOMARKERS = {"blood_pressure_systolic", "blood_pressure_diastolic"}
AT_HOME = {"home", "home_wfh"}
CLINICAL_LOCATIONS = {"hospital", "clinic"}


def _fmt(x: float) -> str:
    return f"{x:g}"


def _context_check(
    reading: Reading,
    steps_by_hour: dict[str, float],
    location_by_date: dict[str, str],
) -> tuple[str, str]:
    """Return (label, templated context detail) for readings that need a context check."""
    steps = steps_by_hour.get(reading.timestamp[:13])
    location = location_by_date.get(reading.timestamp[:10])
    detail = f"steps={'n/a' if steps is None else _fmt(steps)} same hour, location={location or 'n/a'}"

    if steps is None and location is None:
        return "FLAGGED_ERROR", "context check: no context data at timestamp"

    if reading.biomarker in RESTING_CONTEXT_BIOMARKERS:
        if steps is not None and steps == 0:
            return "CONFIRMED_ERROR", f"context check: {detail}, person resting"
        return "FLAGGED_ERROR", f"context check: {detail}, resting not confirmed"

    if reading.biomarker in BP_BIOMARKERS and location in CLINICAL_LOCATIONS:
        return "FLAGGED_ERROR", f"context check: {detail}, clinical setting"

    active = (steps or 0) > 0 or (location is not None and location not in AT_HOME)
    if active:
        return "CONFIRMED_ERROR", f"context check: {detail}, person active"
    return "FLAGGED_ERROR", f"context check: {detail}, activity not confirmed"


def check_plausibility(
    reading: Reading,
    bounds: dict[str, dict[str, str]],
    steps_by_hour: dict[str, float],
    location_by_date: dict[str, str],
) -> FilterResult:
    def result(label: str, reason: str) -> FilterResult:
        return FilterResult(
            event_id=reading.event_id,
            biomarker=reading.biomarker,
            timestamp=reading.timestamp,
            raw_value=reading.value,
            filter_result=label,
            reason=reason,
        )

    row = bounds.get(BOUNDS_ALIASES.get(reading.biomarker, reading.biomarker))
    if row is None:
        return result("FLAGGED_ERROR", "no plausibility_bounds row for biomarker")

    floor, ceiling = float(row["plausible_floor"]), float(row["plausible_ceiling"])
    if floor <= reading.value <= ceiling:
        return result("PASS", f"within [{_fmt(floor)}, {_fmt(ceiling)}]")

    if reading.value < floor:
        breach = f"below plausible_floor ({_fmt(floor)})"
    else:
        breach = f"exceeds plausible_ceiling ({_fmt(ceiling)})"

    if (
        reading.biomarker in ACTIVE_CONTEXT_BIOMARKERS
        or reading.biomarker in RESTING_CONTEXT_BIOMARKERS
    ):
        label, detail = _context_check(reading, steps_by_hour, location_by_date)
        return result(label, f"{breach}; {detail}")

    return result("CONFIRMED_ERROR", f"{breach}; context check: none required")
