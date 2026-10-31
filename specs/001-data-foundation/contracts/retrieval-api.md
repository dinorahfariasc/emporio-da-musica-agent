# Contract: Embeddings and Retrieval (Python, in-process) · PR B

Consumed by the agent tools in #6. Signatures are binding; internals are not.

## `app/db.py`

```python
def get_pool(settings: Settings) -> AsyncConnectionPool
    # Module-level, created once per process, opened lazily.
    # min_size=0, max_size=4, kwargs={"prepare_threshold": None}, over DATABASE_URL (pooled).
```

## `app/embeddings`

```python
EMBEDDING_DIM: Final = 1024
InputType = Literal["document", "query"]

class EmbeddingsUnavailable(Exception): ...

class Embedder(Protocol):
    provider: str          # "voyage" | "fake"
    model: str             # "voyage-4" | "fake-ngram-v1"
    async def embed(self, texts: Sequence[str], input_type: InputType) -> list[list[float]]: ...
        # len(result) == len(texts); each vector has EMBEDDING_DIM floats, L2-normalized.
        # Raises EmbeddingsUnavailable on provider failure (after the profile's retries).

def get_embedder(settings: Settings, *, purpose: Literal["seed", "query"]) -> Embedder
    # purpose selects the retry/timeout profile (research R2).

async def embed_cached(conn, embedder: Embedder, texts: Sequence[str], input_type: InputType) -> list[list[float]]
    # Read/write-through over embedding_cache. Key: sha256(nfc(text)) for documents,
    # sha256(normalize_for_cache(text)) for queries (research R10).
```

## `app/text.py` (PR A)

```python
def nfc(text: str) -> str                    # NFC + strips zero-width chars (U+200B..U+200D, U+FEFF)
def normalize_for_cache(text: str) -> str    # nfc, casefold, collapse whitespace, strip
```

## `app/retrieval`

```python
class PolicyHit(BaseModel):
    section: str               # "4.1"
    title: str
    parent_section: str | None # "4"
    parent_title: str | None   # "Política de Trocas e Devoluções"
    breadcrumb: str            # "§4 Política de Trocas e Devoluções > 4.1 Direito de Arrependimento (Compras Online)"
    body: str
    score: float               # RRF score
    fts_rank: int | None       # 1-based rank in the full-text list, None if absent
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
    max_price: Decimal | None = None       # compared with products.promo_price_brl
    exclude_ids: frozenset[int] = frozenset()

class SearchResult(BaseModel, Generic[T]):  # T = PolicyHit | ProductHit
    hits: list[T]
    mode: Literal["hybrid", "fulltext", "vector"]
    degraded_reason: str | None   # "embeddings_unavailable" | "index_provider_mismatch"

async def search_policies(conn, embedder: Embedder, query: str, *, limit: int = 5) -> SearchResult[PolicyHit]
async def search_products(conn, embedder: Embedder, query: str, *, filters: ProductFilters = ProductFilters(), limit: int = 10) -> SearchResult[ProductHit]
async def similar_to_product(conn, product_id: int, *, filters: ProductFilters = ProductFilters(), limit: int = 5) -> SearchResult[ProductHit]
    # Uses the stored embedding of product_id; never calls a provider; always excludes product_id;
    # mode="vector". Unknown product_id → empty hits.
```

**Guarantees**
- `query` is NFC-normalized; an empty or stopword-only query returns no full-text hits.
- Full-text matches **any** query lexeme (research R4).
- Never raises because the provider failed: degrades to `mode="fulltext"` and logs one warning.
- `index_metadata` is read at most once per 5 minutes per process.
- Only parameterized SQL (constitution I). Hits carry IDs, category and availability; prices and
  stock are read by the tools from `products` (deterministic).

## `app/catalog/rules.py` (PR A)

```python
Availability = Literal["available", "out_of_stock", "discontinued", "coming_soon"]

def availability(status: str, stock_quantity: int) -> Availability
def is_sellable(status: str, stock_quantity: int) -> bool
def effective_promotion(promos: Iterable[PromotionLike]) -> PromotionLike | None   # active only, max %, tie → lowest id
def promo_price(price_brl: Decimal, discount_percent: int) -> Decimal             # ROUND_HALF_UP, 2 places
```
