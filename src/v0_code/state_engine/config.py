"""State Engine config (spec 4.3): defaults from the spec live in the YAML, never in code. The version is the hash of the YAML text."""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from v0_code.baseline_v2.config import Config as BaselineConfig

LABELS = ("within", "slightly", "clearly", "far")          # position labels, from nearest to usual to furthest
LABEL_RANK = {l: i for i, l in enumerate(LABELS)}


@dataclass(frozen=True)
class StreamCfg:
    name: str                           # stream / biomarker name in the baseline registry
    key: str                            # name in the snapshot
    kind: str                           # continuous | daily | periodic | count | label | lab
    source: dict
    available_at: object                # "timestamp" | "end_of_day" | "HH:MM" | {block: "HH:MM"}
    freshness_minutes: int | None = None
    freshness_end_of_day: bool = False
    usual_basis: str | None = None      # glucose | clock_time | profile | history_percentile
    position_method: str | None = None  # sd | percentile | none (None = the default method)
    n_open: int | None = None
    n_close: int | None = None
    unit: str | None = None
    status_from: dict | None = None
    cleaning: str | None = None
    clock_band_minutes: int | None = None
    role: str | None = None             # sleep: the measure shown as `sleep_last_night` in a hand-off
    cadence_minutes: int | None = None  # how often a value is expected (daily = 1440, cadence_days x 1440)
    adverse_directions: tuple[str, ...] = ()   # the directions that are bad for her; an item in any other direction is favourable

    @property
    def tracks_overdue(self) -> bool:
        """Daily, periodic, count and lab measures arrive on a cadence and become OVERDUE; continuous measures go STALE; labels are informational."""
        return self.kind in ("daily", "periodic", "count", "lab")


@dataclass(frozen=True)
class StateConfig:
    patient_id: str
    timezone: str
    tick_minutes: int
    min_history_days: int
    min_samples_usual: int
    overdue_grace: float
    last_meal_window_minutes: int
    method_default: str
    thresholds_sd: tuple[float, float, float]
    thresholds_percentile: tuple[float, float, float]
    open_label: str
    close_label: str
    n_open: int
    n_close: int
    severe_position: str
    severe_statuses: tuple[str, ...]
    glucose_usual_basis: str
    meal_window_minutes: int
    meal_bucket_minutes: int
    clock_band_minutes: int
    meal_kinds: tuple[str, ...]
    streams: tuple[StreamCfg, ...]
    context_streams: dict
    baseline: BaselineConfig
    db_path: str
    version: str = ""

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def stream(self, name: str) -> StreamCfg | None:
        return next((s for s in self.streams if s.name == name), None)

    def stream_by_key(self, key: str) -> StreamCfg | None:
        return next((s for s in self.streams if s.key == key), None)

    def method(self, s: StreamCfg) -> str:
        return s.position_method or self.method_default

    def opens_after(self, s: StreamCfg) -> int:
        return s.n_open if s.n_open is not None else self.n_open

    def closes_after(self, s: StreamCfg) -> int:
        return s.n_close if s.n_close is not None else self.n_close

    def unit(self, s: StreamCfg) -> str:
        if s.unit:
            return s.unit
        b = self.baseline.stream(s.name)
        return b.unit if b else ""

    @classmethod
    def from_yaml(cls, path: str | Path, root: str | Path | None = None) -> "StateConfig":
        text = Path(path).read_text()
        raw = yaml.safe_load(text)["state"]
        base_path = Path(raw["baseline_config"])
        if not base_path.is_absolute() and root is not None:
            base_path = Path(root) / base_path
        baseline = BaselineConfig.from_yaml(base_path)
        pos, per, sev, glu = raw["position"], raw["persistence"], raw["severe"], raw["glucose"]
        streams = []
        for name, s in raw["streams"].items():
            fresh = s.get("freshness")
            if fresh not in (None, "end_of_day"):
                raise ValueError(f"stream {name}: freshness must be end_of_day or use freshness_minutes")
            cad = s.get("cadence_minutes") or (int(s["cadence_days"]) * 1440 if s.get("cadence_days") else (1440 if s.get("cadence") == "daily" else None))
            if s["kind"] in ("daily", "periodic", "count", "lab") and not cad:
                raise ValueError(f"stream {name}: a {s['kind']} measure needs a cadence (cadence: daily, cadence_days or cadence_minutes) to know when it is overdue")
            adverse = tuple(s.get("adverse_directions") or ())
            if s.get("position_method") != "none":
                if not adverse or any(d not in ("above", "below") for d in adverse):
                    raise ValueError(f"stream {name}: adverse_directions must list above and/or below (the directions that are bad for her); got {s.get('adverse_directions')!r}")
            streams.append(StreamCfg(
                name=name, key=s.get("key", name), kind=s["kind"], source=s["source"], available_at=s["available_at"],
                freshness_minutes=s.get("freshness_minutes"), freshness_end_of_day=fresh == "end_of_day", usual_basis=s.get("usual_basis"),
                position_method=s.get("position_method"), n_open=s.get("n_open"), n_close=s.get("n_close"), unit=s.get("unit"),
                status_from=s.get("status_from"), cleaning=s.get("cleaning"), clock_band_minutes=s.get("clock_band_minutes"), role=s.get("role"), cadence_minutes=cad, adverse_directions=adverse))
        if glu["usual_basis"] not in ("meal_relative_with_clock_fallback", "clock_time"):
            raise ValueError(f"glucose.usual_basis must be meal_relative_with_clock_fallback or clock_time, got {glu['usual_basis']!r}")
        for lab in (per["open_label"], per["close_label"], sev["position"]):
            if lab not in LABEL_RANK:
                raise ValueError(f"unknown position label {lab!r}; labels are {LABELS}")
        return cls(
            patient_id=baseline.patient_id, timezone=baseline.timezone, tick_minutes=int(raw["tick_minutes"]), min_history_days=int(raw["min_history_days"]),
            min_samples_usual=int(raw["min_samples_usual"]), overdue_grace=float(raw["overdue_grace"]), last_meal_window_minutes=int(raw.get("last_meal_window_minutes", 1440)), method_default=pos["method_default"],
            thresholds_sd=tuple(float(x) for x in pos["thresholds_sd"]), thresholds_percentile=tuple(float(x) for x in pos["thresholds_percentile"]),
            open_label=per["open_label"], close_label=per["close_label"], n_open=int(per["n_open"]), n_close=int(per["n_close"]),
            severe_position=sev["position"], severe_statuses=tuple(sev.get("statuses", ())), glucose_usual_basis=glu["usual_basis"],
            meal_window_minutes=int(glu["meal_window_minutes"]), meal_bucket_minutes=int(glu["meal_bucket_minutes"]), clock_band_minutes=int(glu["clock_band_minutes"]),
            meal_kinds=tuple(glu["meal_kinds"]), streams=tuple(streams), context_streams=raw.get("context_streams", {}), baseline=baseline, db_path=raw.get("db_path", "output/state_engine.db"),
            version=f"{baseline.patient_id}-state-{hashlib.sha256(text.encode()).hexdigest()[:12]}")


def parse_hhmm(s: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
    if not m:
        raise ValueError(f"not a clock time: {s!r}")
    return int(m.group(1)), int(m.group(2))
