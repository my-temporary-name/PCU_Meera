"""Findings Engine config (findings_engine_spec.md section 10): defaults live in the YAML, never in code. The patient's timezone and the diary severity keywords come from the
Baseline Engine config the file names; the version is the hash of the YAML text."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from v0_code.baseline_v2.config import Config as BaselineConfig


@dataclass(frozen=True)
class FindingsConfig:
    method_version: str
    patient_id: str
    timezone: str
    gap_hours: float
    max_span_hours: float
    diary: dict
    diary_severity_order: tuple
    state_memory: dict
    pi: dict
    seen_before_bands: dict
    part_of_day: dict
    text: dict
    text_sample: dict
    paths: dict
    version: str

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @classmethod
    def from_yaml(cls, path: str | Path, root: str | Path = ".") -> "FindingsConfig":
        text = Path(path).read_text()
        raw = yaml.safe_load(text)["findings"]
        root = Path(root)
        baseline = BaselineConfig.from_yaml(_abs(raw["baseline_config"], root))
        paths = {k: str(_abs(v, root)) for k, v in {"baseline_config": raw["baseline_config"], "evidence_library": raw["evidence_library"], "phrasebook": raw["phrasebook"], **raw["paths"]}.items()}
        return cls(method_version=raw["method_version"], patient_id=baseline.patient_id, timezone=baseline.timezone, gap_hours=float(raw["case"]["gap_hours"]),
                   max_span_hours=float(raw["case"]["max_span_hours"]), diary=dict(raw["diary"]), diary_severity_order=tuple(baseline.diary_severity_order),
                   state_memory=dict(raw["state_memory"]), pi=dict(raw.get("pi") or {}), seen_before_bands=dict(raw.get("seen_before_bands") or {}), part_of_day=dict(raw.get("part_of_day") or {}), text=dict(raw.get("text") or {}), text_sample=dict(raw.get("text_sample") or {}),
                   paths=paths, version=f"{baseline.patient_id}-findings-{hashlib.sha256(text.encode()).hexdigest()[:12]}")


def _abs(p: str, root: Path) -> Path:
    return Path(p) if Path(p).is_absolute() else root / p
