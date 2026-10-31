"""Typed rows for the challenge CSVs, plus dataset-wide checks (FR-002, FR-003)."""

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)

from etl.sources import SourceData, SourceRow


class ValidationFailed(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def _empty_to_none(value: Any) -> Any:
    return None if value == "" else value


def _parse_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


Text = Annotated[str, StringConstraints(min_length=1)]
Optional = BeforeValidator(_empty_to_none)
Id = Annotated[int, Field(gt=0)]
Money = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CategoryRow(_Row):
    category_id: Id
    name: Text
    description: Text


class ProductRow(_Row):
    product_id: Id
    price_brl: Money
    name: Text
    category_id: Id
    description: Text
    stock_quantity: Annotated[int, Field(ge=0)]
    status: Literal["active", "discontinued", "coming_soon"]
    specs: Annotated[dict[str, str], BeforeValidator(_parse_json)]
    created_at: date


class PromotionRow(_Row):
    promotion_id: Id
    product_id: Id
    discount_percent: Annotated[int, Field(ge=1, le=100)]
    description: Text
    is_active: bool


class CustomerRow(_Row):
    customer_id: Id
    name: Text
    phone: Annotated[str, StringConstraints(pattern=r"^\(\d{2}\) \d{4,5}-\d{4}$")]
    email: Annotated[
        str,
        StringConstraints(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
        AfterValidator(str.lower),
    ]
    city: Text


class OrderRow(_Row):
    order_id: Id
    customer_id: Id
    order_date: date
    status: Literal["pending", "confirmed", "shipped", "delivered", "cancelled"]
    total_brl: Money
    payment_method: Literal["pix", "boleto", "debit", "credit_3x", "credit_6x", "credit_12x"]
    tracking_code: Annotated[Text | None, Optional]
    estimated_delivery: Annotated[date | None, Optional]
    notes: Annotated[Text | None, Optional]


class OrderItemRow(_Row):
    order_id: Id
    quantity: Annotated[int, Field(gt=0)]
    product_id: Id


ROW_MODELS: dict[str, type[_Row]] = {
    "categories": CategoryRow,
    "products": ProductRow,
    "promotions": PromotionRow,
    "customers": CustomerRow,
    "orders": OrderRow,
    "order_items": OrderItemRow,
}

# Spec keys per category (data-model.md). Categories 6–8 have no products and no schema yet.
SPECS_KEYS: dict[int, frozenset[str]] = {
    1: frozenset({"body", "neck", "strings", "color"}),
    2: frozenset({"body", "neck", "strings", "color"}),
    3: frozenset({"shells", "pieces", "hardware", "color"}),
    4: frozenset({"keys", "type", "polyphony", "color"}),
    5: frozenset({"top", "back_sides", "neck", "strings", "scale", "electronics", "color"}),
    9: frozenset({"top", "back_sides", "neck", "strings", "scale", "electronics", "color"}),
}


@dataclass(frozen=True)
class Dataset:
    categories: list[CategoryRow]
    products: list[ProductRow]
    promotions: list[PromotionRow]
    customers: list[CustomerRow]
    orders: list[OrderRow]
    order_items: list[OrderItemRow]
    nfc_changes: list[str]


def _where(row: SourceRow, field: str) -> str:
    return f"{row.file}:{row.line} {field}"


def _parse_table(name: str, rows: list[SourceRow], errors: list[str]) -> list[Any]:
    model = ROW_MODELS[name]
    parsed = []
    for row in rows:
        try:
            parsed.append(model.model_validate(row.values))
        except ValidationError as exc:
            for err in exc.errors():
                field = ".".join(str(part) for part in err["loc"]) or "<row>"
                errors.append(f"{_where(row, field)}: {err['msg']}")
    return parsed


def _check_unique(name: str, rows: list[SourceRow], key: tuple[str, ...], errors: list[str]):
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        value = tuple(row.values.get(k, "") for k in key)
        if value in seen:
            errors.append(f"{_where(row, ','.join(key))}: duplicate key {value}")
        seen.add(value)


def validate_dataset(source: SourceData) -> Dataset:
    errors: list[str] = []
    parsed = {name: _parse_table(name, rows, errors) for name, rows in source.tables.items()}

    for name, key in [
        ("categories", ("category_id",)),
        ("products", ("product_id",)),
        ("promotions", ("promotion_id",)),
        ("customers", ("customer_id",)),
        ("orders", ("order_id",)),
        ("order_items", ("order_id", "product_id")),
    ]:
        _check_unique(name, source.tables[name], key, errors)

    if not errors:
        _check_references(source, parsed, errors)
    if errors:
        raise ValidationFailed(errors)
    return Dataset(**parsed, nfc_changes=source.nfc_changes)


def _check_references(source: SourceData, parsed: dict[str, list[Any]], errors: list[str]):
    category_ids = {c.category_id for c in parsed["categories"]}
    product_ids = {p.product_id for p in parsed["products"]}
    customer_ids = {c.customer_id for c in parsed["customers"]}
    order_ids = {o.order_id for o in parsed["orders"]}

    def check(table: str, field: str, valid: set[int]):
        for row, item in zip(source.tables[table], parsed[table], strict=True):
            if getattr(item, field) not in valid:
                errors.append(f"{_where(row, field)}: unknown {field} {getattr(item, field)}")

    check("products", "category_id", category_ids)
    check("promotions", "product_id", product_ids)
    check("orders", "customer_id", customer_ids)
    check("order_items", "order_id", order_ids)
    check("order_items", "product_id", product_ids)

    for row, product in zip(source.tables["products"], parsed["products"], strict=True):
        expected = SPECS_KEYS.get(product.category_id)
        if expected is None:
            errors.append(
                f"{_where(row, 'specs')}: no specs schema for category {product.category_id}"
            )
        elif set(product.specs) != expected:
            missing = sorted(expected - set(product.specs))
            extra = sorted(set(product.specs) - expected)
            errors.append(f"{_where(row, 'specs')}: missing {missing}, unexpected {extra}")
