"""Stream registry: the one place that lists what exists, so the memory builder never branches
per-biomarker in code. Adding a stream means adding a row here.

`source` is where raw values come from:
- 'raw_events'      -> already filtered/evaluated by components 1-2
- 'context_events'  -> ingested verbatim by data/context_ingest.py (never Threshold-Evaluated)
- 'derived'         -> computed from the day record itself

Week aggregation / direction / cumulative tables are driven from these rows (logic/stream_tables.py):
- `path`    where the stream's daily value lives inside a day record
- `agg`     how a 7-day window aggregates it (mean | sum_mean | counts | list | adherence | mood | meals | crossings)
- `numeric` True -> the stream gets a direction (vs prior window) and a delta vs cumulative history
- `label`   plain-English name used in co-movement lists, so the LLM never has to echo a field name
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stream:
    name: str
    domain: str
    source: str
    kind: str  # continuous | daily | hourly | event | categorical
    day_agg: list[str] = field(default_factory=list)
    expected_per_day: int | None = None  # for completeness; None = not a regular-cadence stream
    label: str = ""
    path: tuple[str, ...] | None = None
    agg: str | None = None
    numeric: bool = False
    unit: str = ""  # plain unit for a numeric stream's value/change ("bpm", "hours", "mg/dL", ...)
    count_like: bool = False  # a count of periods: a change is worded "N fewer/more <unit>", never "rose/fell N"


REGISTRY: list[Stream] = [
    Stream("cgm_glucose_reading", "glucose", "raw_events", "continuous", ["mean", "min", "max", "time_of_day_profile"], 96,
           label="glucose", path=("glucose", "mean"), agg="glucose", numeric=True, unit="mg/dL"),
    Stream("sleep_duration", "sleep", "raw_events", "daily", ["value"], 1, label="sleep", path=("sleep", "duration_hours"), agg="mean", numeric=True, unit="hours"),
    Stream("sleep_quality", "sleep", "context_events", "daily", ["value"], 1, label="sleep quality", path=("sleep", "quality"), agg="counts"),
    Stream("step_count", "activity", "raw_events", "daily", ["value"], 1, label="steps", path=("activity", "total_steps"), agg="sum_mean", numeric=True, unit="steps"),
    Stream("steps_hourly_profile", "activity", "context_events", "hourly", ["sum", "peak_hour"], None),  # never ingested; completeness is judged on step_count
    Stream("sedentary_time", "lifestyle", "raw_events", "daily", ["value"], 1, label="sedentary time", path=("activity", "sedentary_minutes"), agg="mean", numeric=True, unit="minutes"),
    Stream("continuous_heart_rate", "heart_rate", "context_events", "continuous", ["mean", "min", "max", "resting_mean"], 96,
           label="heart rate", path=("heart_rate", "continuous_mean"), agg="mean", numeric=True, unit="bpm"),
    Stream("resting_period_heart_rate", "heart_rate", "derived", "daily", ["value"], None,
           label="resting heart rate", path=("heart_rate", "resting_period_mean"), agg="mean", numeric=True, unit="bpm"),
    Stream("resting_heart_rate", "heart_rate", "raw_events", "daily", ["value"], 1,
           label="daily resting heart rate", path=("heart_rate", "resting_heart_rate_daily"), agg="mean", numeric=True, unit="bpm"),
    Stream("blood_pressure_systolic", "blood_pressure", "raw_events", "event", ["list"], None, label="blood pressure", path=("blood_pressure",), agg="list"),
    Stream("blood_pressure_diastolic", "blood_pressure", "raw_events", "event", ["list"], None),
    Stream("medication_adherence", "adherence", "context_events", "event", ["per_medication_taken", "overall_pct"], None,
           label="medication adherence", agg="adherence", numeric=True, unit="percentage points"),
    Stream("mood_state", "mood", "context_events", "categorical", ["by_time_block"], 3, label="mood", agg="mood", numeric=True, unit="strained periods of the day", count_like=True),
    Stream("meal_events", "meals", "context_events", "event", ["list_with_food_description"], None, label="post-meal glucose peak", agg="meals", numeric=True, unit="mg/dL"),
    Stream("diary_context", "diary", "context_events", "event", ["list_with_category_and_severity_note"], None),
    Stream("hydration", "lifestyle", "raw_events", "daily", ["value"], 1, label="hydration", path=("lifestyle", "hydration_ml"), agg="mean", numeric=True, unit="mL"),
    Stream("screen_time", "lifestyle", "raw_events", "daily", ["value"], 1, label="screen time", path=("lifestyle", "screen_time_hours"), agg="mean", numeric=True, unit="hours"),
    Stream("location", "lifestyle", "context_events", "daily", ["value"], 1, label="location", path=("lifestyle", "location"), agg="counts"),
    Stream("bmi", "body", "raw_events", "daily", ["value"], None),
    Stream("waist_hip_ratio", "body", "raw_events", "daily", ["value"], None),
    Stream("other_threshold_crossings", "derived", "derived", "event", [], None, label="other measures out of range", path=("other_threshold_crossings",), agg="crossings"),
]

# Non-glucose biomarkers eligible for 'other_threshold_crossings' (raw_events only, since
# context_events rows never got a Threshold Evaluator status).
THRESHOLD_CROSSING_BIOMARKERS = {
    "resting_heart_rate", "blood_pressure_systolic", "blood_pressure_diastolic",
    "bmi", "waist_hip_ratio", "hydration", "screen_time", "sedentary_time", "step_count",
    "hba1c", "total_cholesterol", "ldl_c", "hdl_c", "triglycerides", "alt", "ast", "ggt",
    "creatinine", "egfr", "fasting_glucose", "sleep_duration",
}


def numeric_streams() -> list[Stream]:
    return [s for s in REGISTRY if s.numeric]


def by_domain(domain: str) -> list[Stream]:
    return [s for s in REGISTRY if s.domain == domain]


def get(name: str) -> Stream | None:
    return next((s for s in REGISTRY if s.name == name), None)
