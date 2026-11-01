"""Return and exchange eligibility (policy §4 and §8.1), decided without the model (FR-019).

Reference dates follow the spec: delivery = `estimated_delivery` (the dataset has no delivery
confirmation), purchase = `order_date`. Windows are counted in calendar days, inclusive.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

Reason = Literal["regret", "defect", "preference"]
Rule = Literal["4.1", "4.2", "4.3", "4.4", "8.1"]

WITHDRAWAL_DAYS = 7  # §4.1 (online purchases), §4.3 (preference)
DEFECT_DAYS = 30  # §4.2, from the purchase
LEGAL_WARRANTY_DAYS = 90  # §8.1, from receipt
# §4.4: "boquilhas de instrumentos de sopro". Custom setups and "venda final" items are not
# marked in the dataset, so they cannot be detected here.
NON_ELIGIBLE_ITEM_WORDS = ("boquilha",)
_NOT_DELIVERED = ("pending", "confirmed")


@dataclass(frozen=True)
class ReturnOrder:
    status: str
    order_date: date
    estimated_delivery: date | None
    item_names: tuple[str, ...] = ()


class Eligibility(BaseModel):
    eligible: bool
    rule: Rule | None
    window_days: int | None
    deadline: date | None
    reason_code: str
    next_step: str


def _decision(
    eligible: bool,
    reason_code: str,
    next_step: str,
    rule: Rule | None = None,
    window_days: int | None = None,
    deadline: date | None = None,
) -> Eligibility:
    return Eligibility(
        eligible=eligible,
        rule=rule,
        window_days=window_days,
        deadline=deadline,
        reason_code=reason_code,
        next_step=next_step,
    )


def eligibility(
    order: ReturnOrder, reason: Reason, bought_online: bool | None, today: date
) -> Eligibility:
    if order.status == "cancelled":
        return _decision(False, "order_cancelled", "O pedido foi cancelado; não há o que devolver.")
    if any(w in n.casefold() for n in order.item_names for w in NON_ELIGIBLE_ITEM_WORDS):
        return _decision(
            False,
            "non_eligible_item",
            "Boquilhas de instrumentos de sopro não podem ser trocadas nem devolvidas por "
            "questões de higiene (§4.4).",
            rule="4.4",
        )
    delivery = order.estimated_delivery
    if order.status in _NOT_DELIVERED or delivery is None or delivery > today:
        return _decision(
            False,
            "not_delivered_yet",
            "O pedido ainda não foi entregue; os prazos contam a partir do recebimento.",
        )

    if reason == "regret":
        if bought_online is None:
            return _decision(
                False,
                "ask_channel",
                "Pergunte se a compra foi feita online: o direito de arrependimento (§4.1) só "
                "vale para compras online.",
                rule="4.1",
            )
        if not bought_online:
            return _decision(
                False,
                "store_purchase",
                "O direito de arrependimento vale só para compras online (§4.1). Ofereça troca "
                "por preferência (§4.3) ou por defeito (§4.2), se couber.",
                rule="4.1",
            )
        deadline = delivery + timedelta(days=WITHDRAWAL_DAYS)
        if today <= deadline:
            return _decision(
                True,
                "within_window",
                "Devolução em até 7 dias corridos do recebimento, sem justificativa; produto "
                "na embalagem original, sem uso. Reembolso em até 10 dias úteis.",
                "4.1",
                WITHDRAWAL_DAYS,
                deadline,
            )
        return _decision(
            False,
            "window_expired",
            "O prazo de 7 dias do arrependimento terminou. Se houver defeito, a troca (§4.2) "
            "e a garantia legal (§8.1) podem valer.",
            "4.1",
            WITHDRAWAL_DAYS,
            deadline,
        )

    if reason == "preference":
        deadline = delivery + timedelta(days=WITHDRAWAL_DAYS)
        if today <= deadline:
            return _decision(
                True,
                "within_window_subject_to_availability",
                "Troca por preferência em até 7 dias, sujeita à disponibilidade do produto "
                "desejado; diferenças de valor são cobradas ou reembolsadas.",
                "4.3",
                WITHDRAWAL_DAYS,
                deadline,
            )
        return _decision(
            False,
            "window_expired",
            "O prazo de 7 dias para troca por preferência terminou.",
            "4.3",
            WITHDRAWAL_DAYS,
            deadline,
        )

    # defect
    defect_deadline = order.order_date + timedelta(days=DEFECT_DAYS)
    if today <= defect_deadline:
        return _decision(
            True,
            "within_window",
            "Troca por defeito de fabricação em até 30 dias corridos da compra.",
            "4.2",
            DEFECT_DAYS,
            defect_deadline,
        )
    legal_deadline = delivery + timedelta(days=LEGAL_WARRANTY_DAYS)
    if today <= legal_deadline:
        return _decision(
            False,
            "legal_warranty",
            "Passaram os 30 dias da troca (§4.2), mas vale a garantia legal de 90 dias do "
            "recebimento (§8.1): o cliente aciona o fabricante e a loja pode intermediar.",
            "8.1",
            LEGAL_WARRANTY_DAYS,
            legal_deadline,
        )
    return _decision(
        False,
        "manufacturer_warranty",
        "A garantia legal terminou. O cliente aciona a garantia do fabricante, e a loja pode "
        "intermediar o processo mediante solicitação (§4.2).",
        "4.2",
        None,
        None,
    )
