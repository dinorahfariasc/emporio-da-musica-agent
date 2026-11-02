from decimal import Decimal as D

import pytest

from app.policies.payments import payment_options


def _times(amount: str) -> list[int]:
    return [i.times for i in payment_options(D(amount)).installments]


def test_pix_is_five_percent_off_list_price():
    options = payment_options(D("2199.00"))
    assert options.pix.applies
    assert options.pix.amount_brl == D("2089.05")


def test_pix_rounds_half_up():
    assert payment_options(D("10.10")).pix.amount_brl == D("9.60")  # 9.595


def test_active_promotion_blocks_pix_and_uses_promo_price():
    options = payment_options(D("549.00"), D("439.20"))
    assert not options.pix.applies
    assert options.pix.reason == "promo_active"
    assert options.pix.amount_brl == D("439.20")
    assert options.amount_brl == D("439.20")


@pytest.mark.parametrize(
    ("amount", "max_times"),
    [
        ("49.99", 1),
        ("50", 3),
        ("240", 3),
        ("320", 3),  # 4x would be R$ 80,00: below the R$ 100,00 minimum (DL-FE-005)
        ("399.99", 3),
        ("400", 4),
        ("600", 6),
        ("700", 7),
        ("1200", 12),
    ],
)
def test_installment_boundaries(amount, max_times):
    assert _times(amount) == list(range(1, max_times + 1))


def test_installment_values_round_half_up():
    options = payment_options(D("100.00"))
    assert [i.installment_brl for i in options.installments] == [
        D("100.00"),
        D("50.00"),
        D("33.33"),
    ]


@pytest.mark.parametrize(("amount", "allowed"), [("2000.00", False), ("2000.01", True)])
def test_combined_payment_needs_more_than_two_thousand(amount, allowed):
    assert payment_options(D(amount)).combined_payment_allowed is allowed
