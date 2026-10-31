from decimal import Decimal
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

from app.chat.protocol import Availability

T = TypeVar("T")


class PolicyHit(BaseModel):
    section: str
    title: str
    parent_section: str | None
    parent_title: str | None
    breadcrumb: str
    body: str
    score: float
    fts_rank: int | None
    vector_rank: int | None


class ProductHit(BaseModel):
    product_id: int
    name: str
    category_id: int
    availability: Availability
    score: float
    fts_rank: int | None
    vector_rank: int | None


class ProductFilters(BaseModel):
    category_id: int | None = None
    only_sellable: bool = False
    max_price: Decimal | None = None
    exclude_ids: frozenset[int] = frozenset()


class SearchResult(BaseModel, Generic[T]):  # noqa: UP046 - pydantic generics
    hits: list[T]
    mode: Literal["hybrid", "fulltext", "vector"]
    degraded_reason: str | None = None


from app.retrieval.hybrid import (  # noqa: E402
    search_policies,
    search_products,
    similar_to_product,
)

__all__ = [
    "PolicyHit",
    "ProductFilters",
    "ProductHit",
    "SearchResult",
    "search_policies",
    "search_products",
    "similar_to_product",
]
