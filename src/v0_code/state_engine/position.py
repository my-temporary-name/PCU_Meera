"""Position (spec R6): where a value sits against the patient's own usual, in units of her own spread. These labels are NOT the Baseline
Engine's size labels (which use the flat band, 0.5 x SD), so the same word does not mean the same distance."""

import math

from v0_code.state_engine.config import LABELS

Z_CAP = 99.0       # a value off a zero spread is "infinitely" far; stored as this cap


def sd_position(value: float, median: float, sd: float | None, thresholds: tuple[float, float, float]) -> dict:
    """z = (value - median) / sd. |z| < t1 within, < t2 slightly, < t3 clearly, otherwise far; direction above/below (none when within)."""
    if sd is None or sd <= 0:
        z = 0.0 if value == median else math.copysign(Z_CAP, value - median)
    else:
        z = (value - median) / sd
    a = abs(z)
    level = LABELS[0] if a < thresholds[0] else LABELS[1] if a < thresholds[1] else LABELS[2] if a < thresholds[2] else LABELS[3]
    direction = None if level == "within" else ("above" if z > 0 else "below")
    return {"z": z, "level": level, "direction": direction, "label": level if direction is None else f"{level} {direction}"}


def percentile_label(share: float, thresholds: tuple[float, float, float]) -> str:
    """Share of earlier days at least as bad: at most t3 far, at most t2 clearly, at most t1 slightly, otherwise within."""
    t1, t2, t3 = thresholds
    return "far" if share <= t3 else "clearly" if share <= t2 else "slightly" if share <= t1 else "within"
