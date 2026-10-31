import re

import pytest

from etl.pipeline import REPORT_PATH, build_payload
from etl.report import DL001_TRACEABILITY, render
from etl.rules import ANOMALY_TYPES


@pytest.fixture(scope="module")
def report() -> str:
    return render(build_payload())


def test_summary_counts_match_the_catalogue(report):
    counts = dict(re.findall(r"^\| (\w+) \| \w+ \| (\d+) \|", report, re.MULTILINE))

    assert counts == {
        "order_total_mismatch": "2",
        "untrusted_description": "10",
        "out_of_stock_active": "1",
        "discontinued": "2",
        "coming_soon": "1",
        "non_sellable_in_order": "2",
        "duplicate_promotions": "3",
        "active_promotions": "4",
        "no_promotion_validity_dates": "25",
        "shared_email": "2",
        "missing_purchase_channel": "20",
        "nfc_normalized": "0",
        "empty_category": "3",
        "policy_conflict": "3",
    }


def test_every_dl001_finding_is_traced(report):
    for finding, handled in DL001_TRACEABILITY:
        assert f"| {finding} | {handled} |" in report


def test_details_start_with_the_type_description(report):
    for name, kind in ANOMALY_TYPES.items():
        if f"### {name}" in report:
            assert f"### {name}\n\n{kind.description}\n" in report


def test_customer_contacts_are_masked(report):
    payload = build_payload()
    for customer in payload.tables["customers"]:
        assert customer["email"] not in report
        assert customer["phone"] not in report


def test_render_is_deterministic(report):
    assert render(build_payload()) == report


def test_committed_report_matches_a_fresh_render(report):
    assert REPORT_PATH.read_text(encoding="utf-8") == report, (
        "docs/data-quality-report.md is stale: run `uv run python -m etl` and commit it"
    )
