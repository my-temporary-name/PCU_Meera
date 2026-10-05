"""Shared state and record models for the UMC signal-validation graph."""

from typing import Literal

from pydantic import BaseModel, Field

FilterLabel = Literal["PASS", "FLAGGED_ERROR", "CONFIRMED_ERROR"]


class Reading(BaseModel):
    event_id: str
    biomarker: str
    timestamp: str
    value: float
    source_file: str


class FilterResult(BaseModel):
    event_id: str
    biomarker: str
    timestamp: str
    raw_value: float
    filter_result: FilterLabel
    reason: str


class ThresholdResult(BaseModel):
    event_id: str
    biomarker: str
    timestamp: str
    value: float
    age_group_used: str
    status: str
    confidence_source: str = ""


class Pairing(BaseModel):
    glucose_event_id: str
    glucose_timestamp: str
    glucose_value: float
    glucose_status: str
    candidate_type: str
    candidate_id: str
    candidate_timestamp: str | None = None
    lag_minutes: float | None = None
    candidate_summary: str


class GlucoseWindow(BaseModel):
    window_type: Literal["day", "week"]
    window_start: str
    window_end: str
    n_readings: int
    completeness_pct: float
    reliable: bool
    mean: float
    gmi_pct: float
    tir_pct: float
    tar_pct: float
    tar_severe_pct: float
    tbr_pct: float
    tbr_severe_pct: float
    cv_pct: float
    delta_mean: float | None = None
    delta_tir_pct: float | None = None
    delta_cv_pct: float | None = None
    delta_gmi_pct: float | None = None
    is_notable: bool | None = None
    interpretive_note: str | None = None


class UMCState(BaseModel):
    # Run config
    data_dir: str
    ranges_dir: str
    output_dir: str

    # load_inputs artifacts
    plausibility_bounds: dict[str, dict[str, str]] = Field(default_factory=dict)
    threshold_rows: list[dict[str, str]] = Field(default_factory=list)
    patient_dob: str | None = None
    patient_sex: str | None = None
    steps_by_hour: dict[str, float] = Field(default_factory=dict)
    location_by_date: dict[str, str] = Field(default_factory=dict)
    readings: list[Reading] = Field(default_factory=list)

    # plausibility_filter artifacts
    filter_results: list[FilterResult] = Field(default_factory=list)
    passed_readings: list[Reading] = Field(default_factory=list)
    filter_output: str | None = None
    filter_counts: dict[str, int] = Field(default_factory=dict)

    # threshold_evaluator artifacts
    threshold_results: list[ThresholdResult] = Field(default_factory=list)
    threshold_output: str | None = None
    status_counts: dict[str, int] = Field(default_factory=dict)
    no_threshold_row: dict[str, int] = Field(default_factory=dict)
    not_applicable: dict[str, int] = Field(default_factory=dict)

    # short_range_linker context data (raw, not folded into Reading)
    meals: list[dict] = Field(default_factory=list)
    adherence_by_date: dict[str, list[dict]] = Field(default_factory=dict)
    context_events_by_date: dict[str, list[dict]] = Field(default_factory=dict)
    sleep_by_date: dict[str, dict] = Field(default_factory=dict)
    mood_by_date_block: dict[str, dict] = Field(default_factory=dict)
    diary_by_date: dict[str, dict] = Field(default_factory=dict)

    # short_range_linker artifacts
    pairings: list[Pairing] = Field(default_factory=list)
    linker_output: str | None = None
    linker_counts: dict[str, int] = Field(default_factory=dict)
    qualifying_glucose_events: int = 0
    glucose_events_with_pairings: int = 0

    # personal_data_store artifacts
    store_output: str | None = None
    store_counts: dict[str, int] = Field(default_factory=dict)

    # baseline_engine artifacts (glucose only, this pass)
    glucose_windows: list[GlucoseWindow] = Field(default_factory=list)
    baseline_llm_failures: list[dict] = Field(default_factory=list)
    baseline_counts: dict[str, int] = Field(default_factory=dict)
    memory_counts: dict[str, int] = Field(default_factory=dict)
    anchor_report: dict[str, dict] = Field(default_factory=dict)  # per tier: fire counts/rates + dead anchors
    glucose_caption_llm: bool = False  # run config: legacy per-window glucose caption (off by default)
