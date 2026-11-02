"""DL-002 correction rules and data-quality detectors. Each anomaly type is tested on its own."""

import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from app.catalog.rules import availability, effective_promotion, is_sellable, promo_price
from etl.models import Dataset


@dataclass(frozen=True)
class AnomalyType:
    entity: str
    description: str
    rule: str


# Report order. Rules reference DL-002 (corrections) or DL-001 (findings).
ANOMALY_TYPES: dict[str, AnomalyType] = {
    "order_total_mismatch": AnomalyType(
        "order",
        "Stored order total differs from the sum of its items (current prices × quantity).",
        "Keep the original total (amount paid); flag the order (DL-002).",
    ),
    "untrusted_description": AnomalyType(
        "product",
        "Description contradicts the product name or specs.",
        "Name and specs win; the description is never shown or indexed (DL-002).",
    ),
    "out_of_stock_active": AnomalyType(
        "product",
        "Active product with zero stock.",
        "Unavailable; suggest alternatives (DL-002).",
    ),
    "discontinued": AnomalyType(
        "product",
        "Discontinued product, whatever its stock.",
        "Not sellable (DL-002).",
    ),
    "coming_soon": AnomalyType(
        "product",
        "Product not launched yet.",
        "Sold on pre-sale without immediate delivery; shown as coming soon (DL-BE-006).",
    ),
    "not_on_sale_in_order": AnomalyType(
        "order",
        "Order contains a discontinued product; a product that is out of stock or coming soon "
        "(pre-sale, DL-BE-006) does not count.",
        "Kept as historical data; flagged on the order item.",
    ),
    "duplicate_promotions": AnomalyType(
        "product",
        "Product with more than one promotion row.",
        "Only active promotions apply; the largest discount wins (DL-002).",
    ),
    "active_promotions": AnomalyType(
        "product",
        "Products with an effective (active) promotion.",
        "Informational: these are the only discounts the agent may quote.",
    ),
    "no_promotion_validity_dates": AnomalyType(
        "promotion",
        "Promotions have no start or end date.",
        "`is_active` is the only source of truth; no date logic.",
    ),
    "shared_email": AnomalyType(
        "customer",
        "Several customers share one email address.",
        "Both kept and flagged; identity checks use order number + email or phone.",
    ),
    "missing_purchase_channel": AnomalyType(
        "order",
        "Orders do not record whether the purchase was online (§4.1 withdrawal right).",
        "The agent asks the customer for the channel before applying §4.1.",
    ),
    "nfc_normalized": AnomalyType(
        "any",
        "Text value changed by Unicode NFC normalization.",
        "Normalize every text to NFC. DL-001's 'Ponta Porã' finding was a CRLF artefact (DL-005).",
    ),
    "empty_category": AnomalyType(
        "category",
        "Category without products, although the manual says the store sells it.",
        "Informational; the agent says the category is not available.",
    ),
    "policy_conflict": AnomalyType(
        "policy",
        "The policy manual contradicts itself.",
        "Use the authoritative value per DL-002.",
    ),
}

UNTRUSTED_DESCRIPTION_IDS: dict[int, str] = {
    135: "describes a Fender Jazz Bass with an Alder body; name is Music Man, specs say Ash",
    136: "describes a Precision bass with a split-coil pickup; name is Ibanez",
    137: "describes a 5-string Ibanez; name is Yamaha, specs say 4 strings",
    138: "describes a StingRay model with features the specs do not list",
    139: "describes a Pearl Export with Poplar/mahogany shells; name is Yamaha, specs say Maple",
    140: "describes a Tama with Birch shells; name is Pearl, specs say Maple",
    141: "describes a Stage Custom kit with features the specs do not list",
    142: "describes a Roland workstation with 88 keys; name is Korg, specs say 61 keys",
    143: "describes a Nord Stage piano; specs say type Synthesizer",
    144: "describes a Yamaha arranger; name is Roland",
}

# Known contradictions in challenge/data/store_policies.pdf (DL-001), recorded statically.
POLICY_CONFLICTS: dict[str, str] = {
    "1.2-vs-7-whatsapp": "§1.2 lists WhatsApp (67) 3341-4444; §7 lists (67) 3321-4500. "
    "Use (67) 3341-4444 for calls and (67) 3321-4500 for WhatsApp (DL-FE-005).",
    "1.2-email-accent": "§1.2 lists contato@empóriodamusica.com.br; the cover lists "
    "contato@emporiodamusica.com.br. Use the address without the accent.",
    "3-vs-3.1-installments": "§3 table says up to 12x with a R$ 100,00 minimum installment; "
    "§3.1 sets up to 3x without a minimum installment (except below R$ 50,00), 4–6x with a "
    "R$ 80,00 minimum and 7–12x with R$ 100,00. The §3 R$ 100,00 minimum applies from 4x on; "
    "the rest of §3.1 stands (DL-FE-005).",
}


@dataclass(frozen=True)
class Anomaly:
    type: str
    record: str  # "order 3", "product 135", "1.2-vs-7-whatsapp", ...
    detail: str


@dataclass(frozen=True)
class Derived:
    """Rows ready to load, keyed by table name, each sorted by primary key."""

    tables: dict[str, list[dict]]
    anomalies: list[Anomaly]


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def _state(is_active: bool) -> str:
    return "active" if is_active else "inactive"


def _record_sort_key(anomaly: Anomaly) -> tuple:
    return (
        list(ANOMALY_TYPES).index(anomaly.type),
        [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", anomaly.record)],
    )


def apply_rules(ds: Dataset) -> Derived:
    anomalies: list[Anomaly] = []
    add = anomalies.append

    promos_by_product = defaultdict(list)
    for promo in ds.promotions:
        promos_by_product[promo.product_id].append(promo)

    products = []
    offered: dict[int, bool] = {}  # active or pre-sale; a stock-out does not count
    prices: dict[int, Decimal] = {}
    for p in sorted(ds.products, key=lambda p: p.product_id):
        effective = effective_promotion(promos_by_product[p.product_id])
        discount = effective.discount_percent if effective else 0
        avail = availability(p.status, p.stock_quantity)
        offered[p.product_id] = p.status in ("active", "coming_soon")
        prices[p.product_id] = p.price_brl
        products.append(
            {
                "product_id": p.product_id,
                "category_id": p.category_id,
                "name": p.name,
                "price_brl": p.price_brl,
                "stock_quantity": p.stock_quantity,
                "status": p.status,
                "specs": p.specs,
                "description": p.description,
                "description_trusted": p.product_id not in UNTRUSTED_DESCRIPTION_IDS,
                "availability": avail,
                "is_sellable": is_sellable(p.status, p.stock_quantity),
                "effective_promotion_id": effective.promotion_id if effective else None,
                "effective_discount_percent": discount,
                "promo_price_brl": promo_price(p.price_brl, discount),
                "created_at": p.created_at,
            }
        )
        if p.product_id in UNTRUSTED_DESCRIPTION_IDS:
            add(
                Anomaly(
                    "untrusted_description",
                    f"product {p.product_id}",
                    UNTRUSTED_DESCRIPTION_IDS[p.product_id],
                )
            )
        if avail == "out_of_stock":
            add(Anomaly("out_of_stock_active", f"product {p.product_id}", "active, stock 0"))
        elif avail == "discontinued":
            add(Anomaly("discontinued", f"product {p.product_id}", f"stock {p.stock_quantity}"))
        elif avail == "coming_soon":
            add(Anomaly("coming_soon", f"product {p.product_id}", f"stock {p.stock_quantity}"))
        promos = promos_by_product[p.product_id]
        if len(promos) > 1:
            listed = ", ".join(
                f"{x.promotion_id} ({x.discount_percent}%, {_state(x.is_active)})"
                for x in sorted(promos, key=lambda x: x.promotion_id)
            )
            add(Anomaly("duplicate_promotions", f"product {p.product_id}", f"promotions {listed}"))
        if effective:
            add(
                Anomaly(
                    "active_promotions",
                    f"product {p.product_id}",
                    f"promotion {effective.promotion_id}: {discount}% ({effective.description})",
                )
            )

    promotions = [
        promo.model_dump() for promo in sorted(ds.promotions, key=lambda x: x.promotion_id)
    ]
    for promo in promotions:
        add(
            Anomaly(
                "no_promotion_validity_dates",
                f"promotion {promo['promotion_id']}",
                f"is_active={int(promo['is_active'])}",
            )
        )

    emails = defaultdict(list)
    for c in ds.customers:
        emails[c.email].append(c.customer_id)
    customers = []
    for c in sorted(ds.customers, key=lambda c: c.customer_id):
        shared_with = [i for i in emails[c.email] if i != c.customer_id]
        customers.append(
            {
                **c.model_dump(),
                "phone_digits": re.sub(r"\D", "", c.phone),
                "email_shared": bool(shared_with),
            }
        )
        if shared_with:
            others = ", ".join(f"customer {i}" for i in sorted(shared_with))
            add(
                Anomaly(
                    "shared_email",
                    f"customer {c.customer_id}",
                    f"email {mask_email(c.email)} shared with {others}",
                )
            )

    items_by_order = defaultdict(list)
    for item in ds.order_items:
        items_by_order[item.order_id].append(item)
    orders = []
    for o in sorted(ds.orders, key=lambda o: o.order_id):
        items_total = sum(
            (prices[i.product_id] * i.quantity for i in items_by_order[o.order_id]), Decimal(0)
        )
        mismatch = items_total != o.total_brl
        orders.append(
            {**o.model_dump(), "items_total_brl": items_total, "total_mismatch": mismatch}
        )
        if mismatch:
            add(
                Anomaly(
                    "order_total_mismatch",
                    f"order {o.order_id}",
                    f"stored {o.total_brl:.2f}, items sum {items_total:.2f} "
                    f"(diff {o.total_brl - items_total:.2f})",
                )
            )
        blocked = sorted(
            i.product_id for i in items_by_order[o.order_id] if not offered[i.product_id]
        )
        if blocked:
            listed = ", ".join(f"product {i}" for i in blocked)
            add(Anomaly("not_on_sale_in_order", f"order {o.order_id}", f"contains {listed}"))
        add(Anomaly("missing_purchase_channel", f"order {o.order_id}", "channel not recorded"))

    order_items = [
        {**i.model_dump(), "product_not_on_sale": not offered[i.product_id]}
        for i in sorted(ds.order_items, key=lambda i: (i.order_id, i.product_id))
    ]

    used_categories = {p.category_id for p in ds.products}
    for c in ds.categories:
        if c.category_id not in used_categories:
            add(Anomaly("empty_category", f"category {c.category_id}", c.name))

    for record in ds.nfc_changes:
        add(Anomaly("nfc_normalized", record, "normalized to NFC"))
    for slug, detail in POLICY_CONFLICTS.items():
        add(Anomaly("policy_conflict", slug, detail))

    tables = {
        "categories": [c.model_dump() for c in sorted(ds.categories, key=lambda c: c.category_id)],
        "products": products,
        "promotions": promotions,
        "customers": customers,
        "orders": orders,
        "order_items": order_items,
    }
    return Derived(tables=tables, anomalies=sorted(anomalies, key=_record_sort_key))
