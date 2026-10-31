"""Deterministic catalog rules (DL-002). The ETL stores their results; agent tools reuse them."""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from app.chat.protocol import Availability

_CENT = Decimal("0.01")


class PromotionLike(Protocol):
    promotion_id: int
    discount_percent: int
    is_active: bool


def availability(status: str, stock_quantity: int) -> Availability:
    if status == "discontinued":
        return "discontinued"
    if status == "coming_soon":
        return "coming_soon"
    if stock_quantity == 0:
        return "out_of_stock"
    return "in_stock"


def is_sellable(status: str, stock_quantity: int) -> bool:
    return availability(status, stock_quantity) == "in_stock"


def effective_promotion[P: PromotionLike](promos: Iterable[P]) -> P | None:
    """Largest active discount wins; ties go to the lowest promotion_id."""
    active = [p for p in promos if p.is_active]
    if not active:
        return None
    return min(active, key=lambda p: (-p.discount_percent, p.promotion_id))


def promo_price(price_brl: Decimal, discount_percent: int) -> Decimal:
    discounted = price_brl * (100 - discount_percent) / 100
    return discounted.quantize(_CENT, rounding=ROUND_HALF_UP)
