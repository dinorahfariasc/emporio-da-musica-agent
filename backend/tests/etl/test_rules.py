from collections import defaultdict
from decimal import Decimal

import pytest

from etl.pipeline import build_payload


@pytest.fixture(scope="module")
def payload():
    return build_payload()


@pytest.fixture(scope="module")
def anomalies(payload):
    by_type = defaultdict(dict)
    for a in payload.anomalies:
        by_type[a.type][a.record] = a.detail
    return by_type


def _rows(payload, table, key):
    return {row[key]: row for row in payload.tables[table]}


def test_order_total_mismatch_keeps_original_total(payload, anomalies):
    orders = _rows(payload, "orders", "order_id")

    assert set(anomalies["order_total_mismatch"]) == {"order 3", "order 20"}
    assert orders[3]["total_brl"] == Decimal("3450")
    assert orders[3]["items_total_brl"] == Decimal("3498")
    assert orders[20]["total_brl"] == Decimal("1400")
    assert orders[20]["items_total_brl"] == Decimal("1488")
    assert orders[3]["total_mismatch"] and orders[20]["total_mismatch"]
    assert not orders[1]["total_mismatch"]


def test_descriptions_135_to_144_are_untrusted(payload, anomalies):
    trusted = {
        pid: p["description_trusted"] for pid, p in _rows(payload, "products", "product_id").items()
    }

    assert {pid for pid, ok in trusted.items() if not ok} == set(range(135, 145))
    assert len(anomalies["untrusted_description"]) == 10


def test_availability_of_the_flagged_products(payload, anomalies):
    products = _rows(payload, "products", "product_id")

    assert products[96]["availability"] == "out_of_stock"
    assert products[113]["availability"] == "discontinued"
    assert products[136]["availability"] == "discontinued"
    assert products[130]["availability"] == "coming_soon"
    assert not any(products[i]["is_sellable"] for i in (96, 113, 130, 136))
    assert set(anomalies["discontinued"]) == {"product 113", "product 136"}
    assert set(anomalies["out_of_stock_active"]) == {"product 96"}
    assert set(anomalies["coming_soon"]) == {"product 130"}


def test_only_four_real_promotions_are_effective(payload, anomalies):
    effective = {
        pid: p["effective_discount_percent"]
        for pid, p in _rows(payload, "products", "product_id").items()
        if p["effective_promotion_id"]
    }

    assert effective == {90: 18, 94: 8, 121: 20, 127: 10}
    assert _rows(payload, "products", "product_id")[90]["promo_price_brl"] == Decimal("1967.18")
    assert set(anomalies["duplicate_promotions"]) == {"product 93", "product 96", "product 99"}


def test_coming_soon_product_in_orders_is_flagged(payload, anomalies):
    flagged = {
        (i["order_id"], i["product_id"])
        for i in payload.tables["order_items"]
        if i["product_not_on_sale"]
    }

    assert flagged == {(3, 130), (14, 130)}
    assert set(anomalies["not_on_sale_in_order"]) == {"order 3", "order 14"}


def test_shared_email_is_flagged_and_masked(payload, anomalies):
    customers = _rows(payload, "customers", "customer_id")

    assert {i for i, c in customers.items() if c["email_shared"]} == {11, 43}
    assert (
        anomalies["shared_email"]["customer 11"] == "email b***@jmail.com shared with customer 43"
    )


def test_informational_anomalies(anomalies):
    assert set(anomalies["empty_category"]) == {"category 6", "category 7", "category 8"}
    assert len(anomalies["missing_purchase_channel"]) == 20
    assert len(anomalies["no_promotion_validity_dates"]) == 25
    assert len(anomalies["policy_conflict"]) == 3
    assert anomalies["nfc_normalized"] == {}
