"""PI config (pi_spec.md section 10): defaults live in the YAML, never in code. The patient's timezone comes from the Baseline Engine config the file names."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from v0_code.baseline_v2.config import Config as BaselineConfig
from v0_code.pi_engine.labels import LabelCfg
from v0_code.pi_engine.lifecycle import LifecycleCfg


@dataclass(frozen=True)
class PiConfig:
    method_version: str
    patient_id: str
    timezone: str
    label: LabelCfg
    lifecycle: LifecycleCfg
    seen_before_bands: dict
    regenerate_every_weeks: int
    text: dict
    replay: dict
    paths: dict
    version: str
    text_sample: dict = field(default_factory=dict)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @classmethod
    def from_yaml(cls, path: str | Path, root: str | Path = ".") -> "PiConfig":
        text = Path(path).read_text()
        raw = yaml.safe_load(text)["pi"]
        root = Path(root)
        ab = lambda p: str(Path(p) if Path(p).is_absolute() else root / p)
        baseline = BaselineConfig.from_yaml(ab(raw["baseline_config"]))
        wl, pw, lc, rc = raw["week_label"], raw["week"]["partial_week"], raw["lifecycle"], raw["lifecycle"]["retract_on_contrary"]
        label = LabelCfg(days_needed=int(wl["days_needed"]), of=int(wl["of"]), min_days=int(pw["min_days"]), scale=bool(pw["scale_threshold"]))
        life = LifecycleCfg(promote_after=int(lc["promote_after_weeks"]), weaken_after=int(lc["weaken_after_weeks"]), retract_after=int(lc["retract_after_weeks"]), contrary_days=int(rc["days_per_week"]),
                            contrary_of=int(wl["of"]), contrary_weeks=int(rc["weeks"]), repromote_after=int(lc["repromote_after_weeks"]), placebo_max_share=float(lc["placebo_fired_max_share"]),
                            min_days=int(pw["min_days"]), scale=bool(pw["scale_threshold"]))
        paths = {k: ab(v) for k, v in {"baseline_config": raw["baseline_config"], "evidence_library": raw["evidence_library"], "phrasebook": raw["phrasebook"], **raw["paths"]}.items()}
        return cls(method_version=raw["method_version"], patient_id=baseline.patient_id, timezone=baseline.timezone, label=label, lifecycle=life, seen_before_bands=dict(raw["seen_before_bands"]),
                   regenerate_every_weeks=int(raw["text"]["regenerate_every_weeks"]), text=dict(raw["text"]), replay=dict(raw.get("replay") or {"mode": "full"}), paths=paths,
                   version=f"{baseline.patient_id}-pi-{hashlib.sha256(text.encode()).hexdigest()[:12]}", text_sample=dict(raw.get("text_sample") or {}))
