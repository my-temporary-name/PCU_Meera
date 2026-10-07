"""Loop config (stage L1): which Findings and PI configs it combines, where it writes (its own two databases), and the state words of the earlier conclusions. Nothing is tuned here: the
seen_before bands must be the same in both configs, and the PI reads follow the Findings config (`findings.pi`)."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from v0_code.findings_engine.config import FindingsConfig
from v0_code.pi_engine.config import PiConfig


class LoopConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LoopConfig:
    findings: FindingsConfig
    pi: PiConfig
    findings_db: str
    pi_db: str
    state_words: dict
    version: str
    l2: dict = field(default_factory=dict)                  # stage L2: its own databases, the F2 database to reuse answers from, concurrency and the stop rules

    @classmethod
    def from_yaml(cls, path: str | Path, root: str | Path = ".") -> "LoopConfig":
        text = Path(path).read_text()
        raw = yaml.safe_load(text)["loop"]
        root = Path(root)
        ab = lambda p: Path(p) if Path(p).is_absolute() else root / p
        f, p = FindingsConfig.from_yaml(ab(raw["findings_config"]), root), PiConfig.from_yaml(ab(raw["pi_config"]), root)
        if f.seen_before_bands != p.seen_before_bands:
            raise LoopConfigError(f"the seen_before bands differ: Findings {f.seen_before_bands}, PI {p.seen_before_bands}")
        if f.timezone != p.timezone:
            raise LoopConfigError(f"the time zones differ: Findings {f.timezone}, PI {p.timezone}")
        paths = {k: str(ab(v)) for k, v in raw["paths"].items()}
        if paths["findings_db"] == f.paths["db_path"] or paths["pi_db"] == p.paths["db_path"]:
            raise LoopConfigError("the loop must write to its own databases, not to the Findings or PI outputs")
        return cls(findings=f, pi=p, findings_db=paths["findings_db"], pi_db=paths["pi_db"], state_words=dict(raw["pi_state_words"]),
                   version=f"{f.patient_id}-loop-{hashlib.sha256(text.encode()).hexdigest()[:12]}", l2=_l2(raw.get("l2"), ab, f, p, paths))


def _l2(raw: dict | None, ab, f: FindingsConfig, p: PiConfig, l1_paths: dict) -> dict:
    if not raw:
        return {}
    out = {"findings_db": str(ab(raw["paths"]["findings_db"])), "pi_db": str(ab(raw["paths"]["pi_db"])), "f2_db": str(ab(raw["f2_db"])) if raw.get("f2_db") else None,
           "concurrency": int(raw.get("concurrency", 6)), "stop": dict(raw["stop"]), "read_list": dict(raw.get("read_list") or {}),
           "previous": {k: str(ab(v)) for k, v in raw["previous"].items()} if raw.get("previous") else None}
    protected = {l1_paths["findings_db"], l1_paths["pi_db"], f.paths["db_path"], p.paths["db_path"], *(out["previous"] or {}).values()}
    if out["findings_db"] in protected or out["pi_db"] in protected:
        raise LoopConfigError("L2 must write to its own databases, not to an earlier output")
    return out
