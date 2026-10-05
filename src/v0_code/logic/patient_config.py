"""Per-patient configuration: the few places where "what counts" depends on the person, not the pipeline.

Keep this file small and declarative. Anything here may be overridden for another patient without touching logic.
"""

# Mood categories that count as strain. A day's mood value is the number of time blocks in one of these;
# calm and uplifted blocks do not count, so "3 fewer strained periods" is good news and never reads as mood "down".
STRAIN_CATEGORIES: tuple[str, ...] = ("mild_stress", "tired_low_energy", "anxious", "overwhelmed_high_distress")

# A stream's "usual" status (its most common day-level status) is only defined with this many days of data;
# before that, any non-normal status counts as a deviation.
MIN_USUAL_DAYS = 14
