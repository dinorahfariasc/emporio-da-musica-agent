from decimal import Decimal
from pathlib import Path

import pytest

from app.catalog.rules import (
    availability,
    display_description,
    effective_promotion,
    is_sellable,
    promo_price,
    ready_to_ship,
)
from etl.models import PromotionRow
from etl.sources import read_csv

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.parametrize(
    ("status", "stock", "expected"),
    [
        ("discontinued", 13, "discontinued"),  # 136
        ("discontinued", 0, "discontinued"),  # 113
        ("coming_soon", 2, "coming_soon"),  # 130
        ("active", 0, "out_of_stock"),  # 96
        ("active", 5, "in_stock"),
    ],
)
def test_availability(status, stock, expected):
    assert availability(status, stock) == expected


@pytest.mark.parametrize(
    ("status", "stock", "sellable", "ready"),
    [
        ("active", 5, True, True),
        ("active", 0, False, False),
        ("coming_soon", 2, True, False),  # pre-sale: sold now, delivered when it arrives
        ("discontinued", 13, False, False),
    ],
)
def test_coming_soon_is_sellable_without_immediate_delivery(status, stock, sellable, ready):
    assert is_sellable(status, stock) is sellable
    assert ready_to_ship(status, stock) is ready


def _fixture_promotions() -> list[PromotionRow]:
    rows = read_csv(FIXTURES / "promotions_multi_active.csv", [])
    return [PromotionRow.model_validate(r.values) for r in rows]


def test_largest_active_discount_wins():
    promos = [p for p in _fixture_promotions() if p.product_id == 90]

    assert effective_promotion(promos).promotion_id == 2  # 25% beats 10%; 40% is inactive


def test_tie_goes_to_lowest_promotion_id():
    promos = [p for p in _fixture_promotions() if p.product_id == 94]

    assert effective_promotion(promos).promotion_id == 4


def test_no_active_promotion_means_none():
    promos = [p for p in _fixture_promotions() if not p.is_active]

    assert effective_promotion(promos) is None


def test_promo_price_rounds_half_up():
    assert promo_price(Decimal("599.90"), 18) == Decimal("491.92")
    assert promo_price(Decimal("2399.00"), 18) == Decimal("1967.18")
    assert promo_price(Decimal("599.90"), 0) == Decimal("599.90")


def test_untrusted_description_is_never_displayed():
    assert display_description({"description": "ok", "description_trusted": True}) == "ok"
    assert display_description({"description": "Fender", "description_trusted": False}) is None
