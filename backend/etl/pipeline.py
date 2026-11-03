"""Builds everything the seed loads, in memory and without a database."""

from pathlib import Path

from etl.models import validate_dataset
from etl.rules import Derived, apply_rules
from etl.sources import read_sources

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "inputs" / "data"
REPORT_PATH = REPO_ROOT / "docs" / "data-quality-report.md"


def build_payload(data_dir: Path = DATA_DIR) -> Derived:
    return apply_rules(validate_dataset(read_sources(data_dir)))
