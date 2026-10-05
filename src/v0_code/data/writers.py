"""CSV output helpers."""

import csv
from pathlib import Path
from typing import Any


def write_csv(path: Path, columns: list[str], records: list[Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec.model_dump(include=set(columns)))
    return str(path)
