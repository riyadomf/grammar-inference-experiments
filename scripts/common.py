"""Repository paths and recorded-result readers."""

import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def open_text(path):
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    if path.exists():
        return path.open(encoding="utf-8")
    return gzip.open(str(path) + ".gz", "rt", encoding="utf-8")


def rows(path):
    with open_text(path) as stream:
        return [json.loads(line) for line in stream]


def run_name(value):
    if not value or value in {".", ".."} or Path(value).name != value:
        raise ValueError("Run name must be one directory component")
    return value
