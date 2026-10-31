"""Search documents for products (US4). Untrusted descriptions are left out (DL-002)."""

from etl.rules import UNTRUSTED_DESCRIPTION_IDS


def build_product_doc(product: dict, category_name: str) -> str:
    specs = "; ".join(f"{k}: {v}" for k, v in sorted(product["specs"].items()))
    parts = [product["name"], category_name, specs]
    if product["product_id"] not in UNTRUSTED_DESCRIPTION_IDS:
        parts.append(product["description"])
    return "\n".join(p for p in parts if p)
