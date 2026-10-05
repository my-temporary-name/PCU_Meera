"""The patient evidence config (spec section 10) plus what is read, never written, from the State Engine and Baseline configs (spec 4.4). Statistical thresholds
are placeholders from the spec and live here, never in code."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

from v0_code.state_engine.config import StateConfig


@dataclass(frozen=True)
class EvidenceConfig:
    method_version: str
    min_history_units: int                 # at least this many usable units ...
    min_history_days: int                  # ... AND at least this many distinct outcome dates (both must be met, spec 7.2)
    detrend_window_days: int
    detrend_min_prior: int
    min_exposed: int
    min_reference: int
    n_perm: int
    min_shift_fraction: float
    q: float
    labels: dict
    placebo_shift_fraction: float
    overlap: dict
    event_exposure: dict
    percentile_check: dict
    shape_check: dict
    pattern_repeat: dict
    sets: dict                             # named lists of values the library refers to as config.<set>.<name> (every top-level block of lists of strings)
    presence_flags: dict
    presence_flag_sources: dict
    picks: dict                            # `<name>_pick` keys: which value of a day with two records to use (first | last)
    stream_map: dict                       # generic token -> store name (str) or {table, name}; null = no stream
    paths: dict                            # library, state_config, rulebook_dir, candidates_file, rulebook_config, store_db, packets_db, handoffs_db, db_path
    state: StateConfig
    config_version: str = ""

    @property
    def tz(self):
        return self.state.tz

    @property
    def baseline(self):
        return self.state.baseline

    @classmethod
    def from_dict(cls, raw: dict, state: StateConfig, text: str = "") -> "EvidenceConfig":
        h, perm, mult = raw["history"], raw["permutation"], raw["multiplicity"]
        det = h["detrend"]
        return cls(
            method_version=raw["method_version"], min_history_units=int(h["min_history_units"]), min_history_days=int(h["min_history_days"]), detrend_window_days=int(det["window_days"]),
            detrend_min_prior=int(det["min_prior_values"]), min_exposed=int(raw["min_exposed"]), min_reference=int(raw["min_reference"]), n_perm=int(perm["n"]),
            min_shift_fraction=float(perm["min_shift_fraction"]), q=float(mult["q"]), labels=dict(raw["labels"]), placebo_shift_fraction=float(raw["placebo"]["shift_fraction"]),
            overlap=dict(raw["overlap"]), event_exposure=dict(raw["event_exposure"]), percentile_check=dict(raw["percentile_check"]), shape_check=dict(raw["shape_check"]),
            pattern_repeat=dict(raw["pattern_repeat"]), sets={k: v for k, v in raw.items() if isinstance(v, dict) and v and all(isinstance(x, list) and all(isinstance(i, str) for i in x) for x in v.values())}, presence_flags=dict(raw.get("presence_flags") or {}),
            presence_flag_sources=dict(raw.get("presence_flag_sources") or {}), picks={k: v for k, v in raw.items() if k.endswith("_pick")},
            stream_map=dict(raw["stream_map"]), paths=dict(raw.get("paths") or {}), state=state, config_version=hashlib.sha256(text.encode()).hexdigest()[:12])

    @classmethod
    def from_yaml(cls, path: str | Path, root: str | Path | None = None) -> "EvidenceConfig":
        text = Path(path).read_text()
        raw = yaml.safe_load(text)["evidence"]
        root = Path(root) if root else Path.cwd()
        state_path = Path(raw["paths"]["state_config"])
        state = StateConfig.from_yaml(state_path if state_path.is_absolute() else root / state_path, root=root)
        lib_path = Path(raw["paths"]["library"])
        lib_text = (lib_path if lib_path.is_absolute() else root / lib_path).read_text()
        cfg = cls.from_dict(raw, state, text + lib_text)
        return cfg
