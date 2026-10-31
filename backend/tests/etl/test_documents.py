import pytest

from etl.documents import build_product_doc
from etl.pipeline import build_payload

UNTRUSTED = {135: "Fender Jazz Bass", 142: "88 teclas"}


@pytest.fixture(scope="module")
def products():
    return {p["product_id"]: p for p in build_payload().tables["products"]}


def test_untrusted_descriptions_are_left_out(products):
    for pid, token in UNTRUSTED.items():
        assert token not in build_product_doc(products[pid], "Categoria")
    for pid in range(135, 145):
        doc = build_product_doc(products[pid], "Categoria")
        assert products[pid]["description"] not in doc


def test_trusted_products_include_description_and_sorted_specs(products):
    doc = build_product_doc(products[81], "Violões")
    assert products[81]["description"] in doc
    assert "back_sides: Meranti; color: Natural; electronics: no" in doc


def test_every_product_gets_a_doc(products):
    assert len(products) == 65
    assert all(build_product_doc(p, "c") for p in products.values())
