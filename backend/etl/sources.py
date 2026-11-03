"""Reads the read-only source CSVs into NFC strings, recording what NFC changed."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from app.text import nfc

CSV_FILES = ("categories", "products", "promotions", "customers", "orders", "order_items")


@dataclass(frozen=True)
class SourceRow:
    file: str
    line: int
    values: dict[str, str]


@dataclass
class SourceData:
    tables: dict[str, list[SourceRow]]
    # "customers.csv:18 city" for every cell whose NFC form differs from the raw text.
    nfc_changes: list[str] = field(default_factory=list)


def read_csv(path: Path, nfc_changes: list[str]) -> list[SourceRow]:
    rows = []
    # newline="" lets the csv module handle CRLF, so no value keeps a trailing "\r";
    # utf-8-sig drops a byte-order mark if an editor ever adds one.
    with path.open(encoding="utf-8-sig", newline="") as f:
        for line, raw in enumerate(csv.DictReader(f), start=2):
            values = {}
            for key, value in raw.items():
                normalized = nfc(value)
                if normalized != value:
                    nfc_changes.append(f"{path.name}:{line} {key}")
                values[key] = normalized
            rows.append(SourceRow(file=path.name, line=line, values=values))
    return rows


def read_sources(data_dir: Path) -> SourceData:
    changes: list[str] = []
    tables = {name: read_csv(data_dir / f"{name}.csv", changes) for name in CSV_FILES}
    return SourceData(tables=tables, nfc_changes=changes)
