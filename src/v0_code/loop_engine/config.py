"""Loop config (stage L1): which Findings and PI configs it combines, where it writes (its own two databases), and the state words of the earlier conclusions. Nothing is tuned here: the
seen_before bands must be the same in both configs, and the PI reads follow the Findings config (`findings.pi`)."""

import hashlib
from dataclasses import dataclass
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
                   version=f"{f.patient_id}-loop-{hashlib.sha256(text.encode()).hexdigest()[:12]}")
