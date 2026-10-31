from datetime import date

import pytest

from etl.models import ValidationFailed, validate_dataset
from etl.pipeline import DATA_DIR
from etl.sources import SourceRow, read_sources


@pytest.fixture
def source():
    return read_sources(DATA_DIR)


def _replace(source, table: str, index: int, **changes: str):
    row = source.tables[table][index]
    source.tables[table][index] = SourceRow(row.file, row.line, {**row.values, **changes})


def _errors(source) -> str:
    with pytest.raises(ValidationFailed) as exc:
        validate_dataset(source)
    return str(exc.value)


def test_real_dataset_is_valid(source):
    ds = validate_dataset(source)

    assert len(ds.products) == 65 and len(ds.order_items) == 22


def test_empty_optional_order_fields_become_null(source):
    orders = {o.order_id: o for o in validate_dataset(source).orders}

    assert orders[1].tracking_code == "BRAB1234567BR"
    assert orders[1].estimated_delivery == date(2025, 10, 25)
    assert orders[9].tracking_code is None
    assert orders[9].estimated_delivery is None
    assert orders[9].notes is None


def test_empty_required_field_is_an_error(source):
    _replace(source, "products", 0, price_brl="")

    assert "products.csv:2 price_brl" in _errors(source)


@pytest.mark.parametrize(
    ("category_index", "specs"),
    [
        (0, '{"top": "Spruce"}'),  # missing keys
        (
            0,
            '{"top": "a", "back_sides": "a", "neck": "a", "strings": "nylon", "scale": "650mm", '
            '"electronics": "no", "color": "Natural", "frets": "19"}',
        ),  # extra key
    ],
)
def test_specs_must_match_the_category_schema(source, category_index, specs):
    _replace(source, "products", category_index, specs=specs)

    assert "products.csv:2 specs" in _errors(source)


def test_unknown_status_and_payment_method_are_rejected(source):
    _replace(source, "products", 0, status="archived")
    _replace(source, "orders", 0, payment_method="cash")

    errors = _errors(source)
    assert "products.csv:2 status" in errors
    assert "orders.csv:2 payment_method" in errors


def test_order_item_with_unknown_product_is_rejected(source):
    _replace(source, "order_items", 0, product_id="999")

    assert "order_items.csv:2 product_id: unknown product_id 999" in _errors(source)
