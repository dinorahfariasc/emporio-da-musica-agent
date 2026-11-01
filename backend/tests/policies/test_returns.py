from datetime import date, timedelta

import pytest

from app.policies.returns import ReturnOrder, eligibility

DELIVERY = date(2026, 3, 1)
BOUGHT = date(2026, 2, 10)


def _order(**kw) -> ReturnOrder:
    base = {"status": "delivered", "order_date": BOUGHT, "estimated_delivery": DELIVERY}
    return ReturnOrder(**{**base, **kw})


@pytest.mark.parametrize(("days", "eligible"), [(0, True), (7, True), (8, False)])
def test_regret_window_is_seven_days_from_delivery(days, eligible):
    result = eligibility(_order(), "regret", True, DELIVERY + timedelta(days=days))
    assert result.eligible is eligible
    assert result.rule == "4.1"
    assert result.deadline == DELIVERY + timedelta(days=7)
    assert result.reason_code == ("within_window" if eligible else "window_expired")


def test_regret_asks_the_channel_first():
    result = eligibility(_order(), "regret", None, DELIVERY)
    assert (result.eligible, result.reason_code) == (False, "ask_channel")


def test_regret_does_not_apply_to_store_purchases():
    result = eligibility(_order(), "regret", False, DELIVERY)
    assert (result.eligible, result.reason_code) == (False, "store_purchase")


@pytest.mark.parametrize(("days", "eligible"), [(7, True), (8, False)])
def test_preference_window(days, eligible):
    result = eligibility(_order(), "preference", None, DELIVERY + timedelta(days=days))
    assert result.eligible is eligible and result.rule == "4.3"
    if eligible:
        assert "availability" in result.reason_code


@pytest.mark.parametrize(
    ("days_after_purchase", "eligible", "rule", "code"),
    [
        (30, True, "4.2", "within_window"),
        (31, False, "8.1", "legal_warranty"),
    ],
)
def test_defect_window_counts_from_the_purchase(days_after_purchase, eligible, rule, code):
    today = BOUGHT + timedelta(days=days_after_purchase)
    result = eligibility(_order(), "defect", None, today)
    assert (result.eligible, result.rule, result.reason_code) == (eligible, rule, code)


@pytest.mark.parametrize(("days", "code"), [(90, "legal_warranty"), (91, "manufacturer_warranty")])
def test_legal_warranty_counts_90_days_from_delivery(days, code):
    result = eligibility(_order(), "defect", None, DELIVERY + timedelta(days=days))
    assert result.eligible is False and result.reason_code == code


def test_wind_instrument_mouthpiece_is_never_eligible():
    order = _order(item_names=("Boquilha Yamaha 4C",))
    for reason in ("regret", "defect", "preference"):
        result = eligibility(order, reason, True, DELIVERY)
        assert (result.eligible, result.rule, result.reason_code) == (
            False,
            "4.4",
            "non_eligible_item",
        )


@pytest.mark.parametrize("status", ["pending", "confirmed"])
def test_an_order_not_delivered_yet_is_not_eligible(status):
    order = _order(status=status, estimated_delivery=None)
    assert eligibility(order, "regret", True, DELIVERY).reason_code == "not_delivered_yet"


def test_a_shipped_order_before_its_estimated_delivery_is_not_eligible():
    order = _order(status="shipped")
    result = eligibility(order, "regret", True, DELIVERY - timedelta(days=1))
    assert result.reason_code == "not_delivered_yet"


def test_cancelled_order_has_nothing_to_return():
    assert eligibility(_order(status="cancelled"), "regret", True, DELIVERY).reason_code == (
        "order_cancelled"
    )


def test_dataset_orders_are_outside_every_window_today():
    """US6-5: the oldest-to-newest dataset orders against the real date (2026-11-01)."""
    today = date(2026, 11, 1)
    order = _order(order_date=date(2026, 2, 3), estimated_delivery=date(2026, 2, 17))
    assert eligibility(order, "regret", True, today).reason_code == "window_expired"
    assert eligibility(order, "defect", None, today).reason_code == "manufacturer_warranty"
