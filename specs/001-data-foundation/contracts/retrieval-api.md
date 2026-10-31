# Contract: Embeddings and Retrieval (Python, in-process)

Consumed by the agent tools in epic 002. Signatures are binding; internals are not.

## `app/embeddings`

```python
EMBEDDING_DIM: Final = 1024
InputType = Literal["document", "query"]

class EmbeddingsUnavailable(Exception): ...

class Embedder(Protocol):
    provider: str          # "voyage" | "fake"
    model: str             # "voyage-4" | "fake-ngram-v1"
    async def embed(self, texts: Sequence[str], input_type: InputType) -> list[list[float]]: ...
        # len(result) == len(texts); each vector has EMBEDDING_DIM floats and is L2-normalized.
        # Raises EmbeddingsUnavailable on provider failure (after the configured retries).

def get_embedder(settings: Settings, *, purpose: Literal["seed", "query"]) -> Embedder
    # purpose selects the retry/timeout profile (research R2).

async def embed_cached(conn, embedder: Embedder, texts: Sequence[str], input_type: InputType) -> list[list[float]]
    # Read-through/write-through over embedding_cache, keyed by normalize_for_cache(text).
```

## `app/text.py`

```python
def nfc(text: str) -> str                    # NFC + strips zero-width chars (U+200B..U+200D, U+FEFF)
def normalize_for_cache(text: str) -> str    # nfc, casefold, collapse whitespace, strip
```

## `app/retrieval`

```python
class PolicyHit(BaseModel):
    section: str          # "4.1"
    title: str
    parent_section: str | None
    body: str
    score: float          # RRF score
    fts_rank: int | None  # 1-based rank in the full-text list, None if absent
    vector_rank: int | None

class ProductHit(BaseModel):
    product_id: int
    name: str
    score: float
    fts_rank: int | None
    vector_rank: int | None

class SearchResult(BaseModel, Generic[T]):   # T bound to PolicyHit | ProductHit
    hits: list[T]
    mode: Literal["hybrid", "fulltext"]   # "fulltext" when degraded
    degraded_reason: str | None           # "embeddings_unavailable" | "index_provider_mismatch"

async def search_policies(conn, embedder: Embedder, query: str, *, limit: int = 5) -> SearchResult[PolicyHit]
async def search_products(conn, embedder: Embedder, query: str, *, limit: int = 10) -> SearchResult[ProductHit]
```

**Guarantees**
- `query` is NFC-normalized before use; an empty or whitespace-only query returns no hits.
- Never raises because the embeddings provider failed: it degrades to `mode="fulltext"` and
  logs one warning (FR-018).
- Uses only parameterized SQL (constitution I).
- `search_products` returns product IDs and names only. Price, stock and availability are read
  by the tools from `products` (deterministic), never from search text.

## `app/catalog/rules.py`

```python
Availability = Literal["available", "out_of_stock", "discontinued", "coming_soon"]

def availability(status: str, stock_quantity: int) -> Availability
def is_sellable(status: str, stock_quantity: int) -> bool
def effective_promotion(promos: Iterable[PromotionLike]) -> PromotionLike | None   # active only, max %, tie → lowest id
```
