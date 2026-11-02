"""Payment options from policy §3 / §3.1 (research R8). Pure, Decimal, ROUND_HALF_UP.

The manual gives R$ 80,00 (§3.1) and R$ 100,00 (§3 table) as the 4x–6x minimum; the store page
and the agent use R$ 100,00 (DL-FE-005)."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel

CENT = Decimal("0.01")
PIX_DISCOUNT = Decimal("0.05")
MIN_SPLIT = Decimal("50")  # below this, no installments
UP_TO_3X_FREE = 3
TIER_4_6_MIN = Decimal("100")
TIER_7_12_MIN = Decimal("100")
COMBINED_MIN = Decimal("2000")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


class PixOption(BaseModel):
    applies: bool
    amount_brl: Decimal
    reason: Literal["promo_active"] | None = None


class Installment(BaseModel):
    times: int
    installment_brl: Decimal
    total_brl: Decimal


class PaymentOptions(BaseModel):
    amount_brl: Decimal
    pix: PixOption
    installments: list[Installment]
    combined_payment_allowed: bool


def _max_installments(amount: Decimal) -> int:
    if amount < MIN_SPLIT:
        return 1
    count = UP_TO_3X_FREE
    for times in range(4, 13):
        minimum = TIER_4_6_MIN if times <= 6 else TIER_7_12_MIN
        if amount / times < minimum:
            break
        count = times
    return count


def payment_options(price_brl: Decimal, promo_price_brl: Decimal | None = None) -> PaymentOptions:
    promo_active = promo_price_brl is not None and promo_price_brl < price_brl
    amount = _money(promo_price_brl if promo_active else price_brl)  # type: ignore[arg-type]
    if promo_active:
        # §6.2: the PIX discount does not apply on top of a promotional price.
        pix = PixOption(applies=False, amount_brl=amount, reason="promo_active")
    else:
        pix = PixOption(applies=True, amount_brl=_money(amount * (1 - PIX_DISCOUNT)))
    installments = [
        Installment(times=n, installment_brl=_money(amount / n), total_brl=amount)
        for n in range(1, _max_installments(amount) + 1)
    ]
    return PaymentOptions(
        amount_brl=amount,
        pix=pix,
        installments=installments,
        combined_payment_allowed=amount > COMBINED_MIN,
    )
