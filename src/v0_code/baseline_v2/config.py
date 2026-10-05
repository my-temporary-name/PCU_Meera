"""Baseline Engine v2 config: everything patient-specific, loaded from YAML and versioned.

Rule 6 of task/baselineV2.md: nothing patient-specific in code (timezone, pronoun, medications, thresholds, anchors, strain
categories, step floors, device ranges). The engine reads this object and nothing else about the patient.
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


@dataclass(frozen=True)
class StreamCfg:
    name: str
    domain: str
    kind: str                       # continuous | daily | hourly | event | categorical | derived
    label: str = ""
    unit: str = ""
    agg: str = "value"
    source: str = "raw"             # raw (raw_events) | context_num (context_events.value_num) | context (context_events rows)
    expected_per_day: int | None = None
    count_like: bool = False        # a count of periods: a change reads "N fewer/more <unit>", never "went up/down"

    @property
    def display(self) -> str:
        return self.label or self.name.replace("_", " ")


@dataclass(frozen=True)
class StatusStreamCfg:
    name: str
    label: str
    components: tuple[str, ...]
    facts_key: str


@dataclass(frozen=True)
class AnchorCfg:
    name: str
    thresholds: dict[str, float | str | bool]    # tier -> threshold; "min(2, n_meds)" kept as a string, resolved per window


@dataclass(frozen=True)
class Config:
    patient_id: str
    timezone: str
    pronoun: str
    strain_mood_categories: tuple[str, ...]
    medication_id_regex: str
    mood_distress_order: tuple[str, ...]
    min_days_for_compare: int
    reliable_completeness_pct: float
    device_range: tuple[float, float]
    max_step_change_per_15min: float
    glucose_expected_per_day: int
    gap_hours_flag: float
    lab_biomarker: str
    week_days: int
    month_every_days: int
    min_days_in_window: int
    chronic_min_share_pct: float
    streams: tuple[StreamCfg, ...]
    sd_multiplier: float
    min_material_status: str
    small_below: float
    moderate_below: float
    anchors: dict[str, AnchorCfg]
    status_streams: tuple[StatusStreamCfg, ...] = ()
    diary_severity_order: tuple[str, ...] = ("severe", "moderate", "mild")
    month_min_severity: str = "moderate"
    month_max_listed: int = 8
    whole_number_units: tuple[str, ...] = ("steps", "mL", "minutes")
    gist: dict = field(default_factory=dict)
    version: str = ""

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def stream(self, name: str) -> StreamCfg | None:
        return next((s for s in self.streams if s.name == name), None)

    def distress_rank(self, category: str | None) -> int:
        """Higher = more distressed. A category in the configured order ranks by position; an unknown category ranks below all of them."""
        order = self.mood_distress_order
        return order.index(category) if category in order else -1

    def medicine_name(self, med_id: str) -> str:
        """Plain medicine name from a stored id, using the patient's id convention from config."""
        name = re.sub(self.medication_id_regex, "", med_id) if self.medication_id_regex else med_id
        return name.replace("_", " ")

    @property
    def week_gist_weekday(self) -> str | None:
        """The weekday whose weeks always get a gist, or None (config 'none') for no weekday rule: every non-early, non-quiet week is queued."""
        v = self.gist.get("week_gist_weekday")
        return None if v is None or str(v).strip().lower() in ("", "none", "null") else str(v)

    def measure_name(self, stream: str) -> str:
        """How the gist view (and the output check) names a measure: config `gist.measure_names`, else the stream's label."""
        sc = self.stream(stream)
        ss = next((s for s in self.status_streams if s.name == stream), None)
        return self.gist.get("measure_names", {}).get(stream) or (sc.display if sc else ss.label if ss else stream.replace("_", " "))

    def measure_terms(self) -> dict[str, str]:
        """Every phrase that names a measure -> its stream (lower case): its gist name, its label, its configured aliases. Status streams
        (blood pressure) are included so a mention of them binds to a measure that has no direction tag."""
        terms: dict[str, str] = {}
        for sc in self.streams:
            for t in [self.measure_name(sc.name), sc.display, *self.gist.get("measure_aliases", {}).get(sc.name, [])]:
                terms.setdefault(t.lower(), sc.name)
        for ss in self.status_streams:
            terms.setdefault(ss.label.lower(), ss.name)
        for key, phrase in self.gist.get("unchecked_measures", {}).items():
            terms.setdefault(re.sub(r"^the\s+", "", phrase.lower()), key)
        return terms

    def unchecked_name(self, key: str) -> str:
        """The phrase for a named thing the check recognises but never compares with a tag (e.g. the month lab line's "the lab's long-term blood sugar test")."""
        return self.gist["unchecked_measures"][key]

    @property
    def usual_place_count(self) -> int:
        return int(self.gist.get("usual_place_count", 2))

    @property
    def anchor_size_floor(self) -> str:
        return self.gist.get("anchor_size_floor", "moderate")

    @property
    def possessive(self) -> str:
        return {"she": "her", "he": "his"}.get(self.pronoun, "their")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        text = Path(path).read_text()
        raw = yaml.safe_load(text)
        p, h, g = raw["patient"], raw["history"], raw["glucose"]
        streams = tuple(StreamCfg(**{k: v for k, v in row.items()}) for row in raw["streams"])
        anchors = {}
        for name, spec in raw.get("anchors", {}).items():
            anchors[name] = AnchorCfg(name, {"any": spec} if isinstance(spec, bool) else dict(spec))
        return cls(
            patient_id=p["id"], timezone=p["timezone"], pronoun=p["pronoun"], strain_mood_categories=tuple(p.get("strain_mood_categories", [])), medication_id_regex=p.get("medication_id_regex", ""), mood_distress_order=_distress_order(p),
            min_days_for_compare=int(h["min_days_for_compare"]), reliable_completeness_pct=float(h["reliable_completeness_pct"]),
            device_range=(float(g["device_range"][0]), float(g["device_range"][1])), max_step_change_per_15min=float(g["max_step_change_per_15min"]),
            glucose_expected_per_day=int(g.get("expected_per_day", 96)), gap_hours_flag=float(g.get("gap_hours_flag", 1.0)), lab_biomarker=g.get("lab_biomarker", "hba1c"),
            week_days=int(raw.get("windows", {}).get("week_days", 7)), month_every_days=int(raw.get("windows", {}).get("month_every_days", 30)),
            min_days_in_window=int(raw.get("windows", {}).get("min_days_in_window", 4)), chronic_min_share_pct=float(raw.get("chronic", {}).get("min_share_pct", 50)),
            streams=streams, sd_multiplier=float(raw["flat_band"]["sd_multiplier"]), min_material_status=_material_status(raw.get("min_material_status", "abnormal")),
            small_below=float(raw["size_labels"]["small_below"]), moderate_below=float(raw["size_labels"]["moderate_below"]),
            anchors=anchors, gist=raw.get("gist", {}),
            status_streams=tuple(StatusStreamCfg(s["name"], s.get("label", s["name"]), tuple(s["components"]), s.get("facts_key", s["name"])) for s in raw.get("status_streams", [])),
            diary_severity_order=tuple(raw.get("diary", {}).get("severity_order", ["severe", "moderate", "mild"])), month_min_severity=raw.get("diary", {}).get("month_min_severity", "moderate"),
            month_max_listed=int(raw.get("diary", {}).get("month_max_listed", 8)), whole_number_units=tuple(raw.get("rendering", {}).get("whole_number_units", ["steps", "mL", "minutes"])),
            version=f"{p['id']}-{hashlib.sha256(text.encode()).hexdigest()[:12]}",
        )


MATERIAL_STATUS_RANK = {"abnormal": 2, "borderline": 1}      # abnormal = low/high only; borderline = borderline_* and low/high


def _material_status(value: str) -> str:
    if value not in MATERIAL_STATUS_RANK:
        raise ValueError(f"min_material_status must be one of {sorted(MATERIAL_STATUS_RANK)}, got {value!r}")
    return value


def _distress_order(p: dict) -> tuple[str, ...]:
    """Mood categories from least to most distressed. If the config gives no order: every non-strain category first (in listed order is
    unknown, so alphabetical), then the strain categories in their configured order."""
    if p.get("mood_distress_order"):
        return tuple(p["mood_distress_order"])
    return tuple(p.get("strain_mood_categories", []))


_MIN_RE = re.compile(r"^min\(\s*(\d+(?:\.\d+)?)\s*,\s*n_meds\s*\)$")


def resolve_threshold(value: float | str | bool, n_meds: int) -> float:
    """A numeric threshold, or the string 'min(<number>, n_meds)' resolved for this window (so a 1-medicine patient still works)."""
    if isinstance(value, str):
        m = _MIN_RE.match(value.strip())
        if not m:
            raise ValueError(f"unsupported threshold expression: {value!r}")
        return min(float(m.group(1)), float(n_meds)) if n_meds else float(m.group(1))
    return float(value)
