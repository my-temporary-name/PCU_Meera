"""Config for ingest-only streams (config/ingest_streams.yaml): readings already parsed from the data dir, written verbatim to context_events, used only by the
engines named in `used_by`. Nothing here knows a stream or file name."""

from dataclasses import dataclass
from pathlib import Path

import yaml

from v0_code.logic.registry import REGISTRY

STORE_TABLES = ("raw_events", "numeric_summary", "context_events", "memory_records", "memory_v2")
DEFAULT_PATH = Path(__file__).resolve().parents[3] / "config" / "ingest_streams.yaml"


class IngestConfigError(ValueError):
    pass


@dataclass(frozen=True)
class IngestStream:
    name: str
    kind: str
    biomarker: str                 # the parsed readings (Reading.biomarker) this stream is made of
    used_by: tuple[str, ...]


def load_ingest_streams(path: str | Path = DEFAULT_PATH) -> tuple[IngestStream, ...]:
    raw = (yaml.safe_load(Path(path).read_text()) or {}).get("ingest_streams") or {}
    owned = {s.name for s in REGISTRY}
    out, errors = [], []
    for name, row in raw.items():
        row = row or {}
        if name in owned:
            errors.append(f"{name}: already a stream in the Baseline registry; an ingest-only stream must not be")
        if name in STORE_TABLES:
            errors.append(f"{name}: is the name of a store table")
        if not row.get("kind"):
            errors.append(f"{name}: kind is required")
        biomarker = (row.get("source") or {}).get("biomarker")
        if not biomarker:
            errors.append(f"{name}: source.biomarker is required")
        used_by = tuple(row.get("used_by") or ())
        if not used_by:
            errors.append(f"{name}: used_by is required and must name at least one engine (an ingest-only stream is read only by the engines it names)")
        out.append(IngestStream(name, row.get("kind", ""), biomarker or "", used_by))
    if errors:
        raise IngestConfigError("Cannot load the ingest streams:\n - " + "\n - ".join(errors))
    return tuple(out)
