"""Product tools (US1, US4). Prices and stock come from stored, rule-derived columns."""

import re
import uuid
from decimal import Decimal
from typing import Annotated

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from app.chat import protocol as p
from app.retrieval import ProductFilters
from app.retrieval import search_products as _search_products
from app.retrieval import similar_to_product as _similar_to_product
from app.tools.context import ToolContext, ToolError
from app.tools.registry import tool

MAX_CARDS = 6


class ProductView(BaseModel):
    product_id: int
    name: str
    category_id: int
    category: str
    price_brl: Decimal
    promo_price_brl: Decimal | None
    discount_percent: int | None
    availability: p.Availability
    is_sellable: bool
    stock_quantity: int
    specs: dict[str, str]
    description: str | None


class ProductsResult(BaseModel):
    count: int
    products: list[ProductView]


class Candidate(BaseModel):
    product_id: int
    name: str


class ProductLookup(BaseModel):
    product: ProductView | None = None
    candidates: list[Candidate] = []
    requested_quantity: int | None = None
    enough_stock: bool | None = None


def _lookup(view: ProductView, quantity: int | None) -> ProductLookup:
    if quantity is None:
        return ProductLookup(product=view)
    return ProductLookup(
        product=view,
        requested_quantity=quantity,
        enough_stock=view.is_sellable and view.stock_quantity >= quantity,
    )


_SELECT = """
    SELECT p.product_id, p.name, c.name AS category, p.category_id, p.price_brl,
           p.promo_price_brl, p.effective_discount_percent, p.availability, p.is_sellable,
           p.stock_quantity,
           p.specs, p.description, p.description_trusted
    FROM products p JOIN categories c USING (category_id)
"""


def _view(row: dict) -> ProductView:
    discounted = row["effective_discount_percent"] > 0
    return ProductView(
        product_id=row["product_id"],
        name=row["name"],
        category_id=row["category_id"],
        category=row["category"],
        price_brl=row["price_brl"],
        promo_price_brl=row["promo_price_brl"] if discounted else None,
        discount_percent=row["effective_discount_percent"] if discounted else None,
        availability=row["availability"],
        is_sellable=row["is_sellable"],
        stock_quantity=row["stock_quantity"],
        specs=row["specs"],
        # Untrusted descriptions contradict the name/specs (DL-001): never shown.
        description=row["description"] if row["description_trusted"] else None,
    )


async def views_by_ids(conn: psycopg.AsyncConnection, ids: list[int]) -> list[ProductView]:
    if not ids:
        return []
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(f"{_SELECT} WHERE p.product_id = ANY(%s)", (ids,))
        rows = {r["product_id"]: r for r in await cur.fetchall()}
    return [_view(rows[i]) for i in ids if i in rows]


def product_cards(ctx: ToolContext, views: list[ProductView]) -> None:
    """Emits one data-products part (at most 6 cards), mapped per the #4 contract."""
    if not views:
        return
    cards = [
        p.ProductCard(
            id=v.product_id,
            name=v.name,
            category_id=v.category_id,
            price_brl=float(v.price_brl),
            promo_price_brl=float(v.promo_price_brl) if v.promo_price_brl is not None else None,
            discount_percent=v.discount_percent,
            availability=v.availability,
        )
        for v in views[:MAX_CARDS]
    ]
    event = p.DataProducts(
        id=f"products-{uuid.uuid4().hex[:8]}", data=p.ProductsData(products=cards)
    )
    ctx.emit(event.model_dump(mode="json", by_alias=True))


@tool
async def search_products(
    ctx: ToolContext,
    query: str,
    category_id: int | None = None,
    max_price_brl: Decimal | None = None,
    only_sellable: bool = True,
    limit: Annotated[int, Field(ge=1, le=10)] = 5,
) -> ProductsResult:
    """Search the catalog by text. The budget is compared with the current (promo) price."""
    filters = ProductFilters(
        category_id=category_id, only_sellable=only_sellable, max_price=max_price_brl
    )
    async with ctx.pool.connection() as conn:
        result = await _search_products(conn, ctx.embedder, query, filters=filters, limit=limit)
        views = await views_by_ids(conn, [h.product_id for h in result.hits])
    product_cards(ctx, views)
    return ProductsResult(count=len(views), products=views)


_TOKEN = re.compile(r"\w+")


@tool
async def get_product(
    ctx: ToolContext,
    product_id: int | None = None,
    name: str | None = None,
    quantity: Annotated[int, Field(ge=1)] | None = None,
) -> ProductLookup:
    """Get one product by id or name, with its stock quantity. Pass `quantity` when the customer
    asks for several units: `enough_stock` says whether that many can be sold right now. An
    ambiguous name returns candidates instead."""
    if product_id is None and not (name or "").strip():
        raise ToolError("invalid_input", "give product_id or name")
    async with ctx.pool.connection() as conn:
        if product_id is not None:
            views = await views_by_ids(conn, [product_id])
            if not views:
                raise ToolError("not_found")
            product_cards(ctx, views)
            return _lookup(views[0], quantity)
        result = await _search_products(conn, ctx.embedder, name or "", limit=5)
        views = await views_by_ids(conn, [h.product_id for h in result.hits])
    wanted = {t.casefold() for t in _TOKEN.findall(name or "")}
    matching = [v for v in views if wanted <= {t.casefold() for t in _TOKEN.findall(v.name)}]
    if len(matching) == 1:
        product_cards(ctx, matching)
        return _lookup(matching[0], quantity)
    if not views:
        raise ToolError("not_found")
    pool = matching or views
    return ProductLookup(candidates=[Candidate(product_id=v.product_id, name=v.name) for v in pool])


@tool
async def find_similar_products(
    ctx: ToolContext,
    product_id: int | None = None,
    description: str | None = None,
    max_price_brl: Decimal | None = None,
    limit: Annotated[int, Field(ge=1, le=5)] = 3,
) -> ProductsResult:
    """Find sellable alternatives to a product (same category) or to a text description."""
    if product_id is None and not (description or "").strip():
        raise ToolError("invalid_input", "give product_id or description")
    async with ctx.pool.connection() as conn:
        if product_id is not None:
            base = await views_by_ids(conn, [product_id])
            if not base:
                raise ToolError("not_found")
            cur = await conn.execute(
                "SELECT category_id FROM products WHERE product_id = %s", (product_id,)
            )
            (category_id,) = await cur.fetchone()
            filters = ProductFilters(
                category_id=category_id, only_sellable=True, max_price=max_price_brl
            )
            result = await _similar_to_product(conn, product_id, filters=filters, limit=limit)
        else:
            filters = ProductFilters(only_sellable=True, max_price=max_price_brl)
            result = await _search_products(
                conn, ctx.embedder, description or "", filters=filters, limit=limit
            )
        views = await views_by_ids(conn, [h.product_id for h in result.hits])
    product_cards(ctx, views)
    return ProductsResult(count=len(views), products=views)


@tool
async def get_active_promotions(ctx: ToolContext, category_id: int | None = None) -> ProductsResult:
    """List products with an active promotion, with original price, promo price and percent."""
    async with ctx.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT product_id FROM products WHERE effective_discount_percent > 0 "
                "AND (%s::int IS NULL OR category_id = %s) ORDER BY product_id",
                (category_id, category_id),
            )
            ids = [r[0] for r in await cur.fetchall()]
        views = await views_by_ids(conn, ids)
    product_cards(ctx, views)
    return ProductsResult(count=len(views), products=views)
