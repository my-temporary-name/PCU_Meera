"""Load the engine: the library, its check against the rulebook (property 16), and the read-only store."""

import sqlite3
from pathlib import Path

from v0_code.evidence_engine.config import EvidenceConfig
from v0_code.evidence_engine.data import EvidenceData
from v0_code.evidence_engine.library import Library, load_library


def resolve(root: Path, p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else root / q


def load_library_checked(cfg: EvidenceConfig, root: Path) -> Library:
    from v0_code.rulebook_lookup.config import RulebookConfig
    lib = load_library(resolve(root, cfg.paths["library"]))
    presence = None
    if cfg.paths.get("rulebook_config") and cfg.presence_flags:
        presence = (cfg.presence_flags, cfg.presence_flag_sources, RulebookConfig.from_yaml(resolve(root, cfg.paths["rulebook_config"]), root))
    lib.check(resolve(root, cfg.paths["rulebook_dir"]), cfg.paths["candidates_file"], presence)
    return lib


def open_store(cfg: EvidenceConfig, root: Path) -> sqlite3.Connection:
    p = resolve(root, cfg.paths["store_db"])
    return sqlite3.connect(f"file:{p}?mode=ro", uri=True)


def load_data(cfg: EvidenceConfig, root: Path) -> tuple[Library, EvidenceData, sqlite3.Connection]:
    lib = load_library_checked(cfg, root)
    conn = open_store(cfg, root)
    return lib, EvidenceData(conn, cfg, lib), conn
