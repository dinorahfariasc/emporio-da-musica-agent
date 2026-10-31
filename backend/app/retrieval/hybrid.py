"""Hybrid retrieval: any-term full-text + vector, fused with RRF k=60 (research R4)."""

import logging
import time
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from app.embeddings import Embedder, EmbeddingsUnavailable
from app.embeddings.cache import embed_cached, vector_literal
from app.retrieval import (
    PolicyHit,
    ProductFilters,
    ProductHit,
    SearchResult,
)
from app.text import nfc

logger = logging.getLogger(__name__)

CANDIDATES = 20
RRF_K = 60
INDEX_TTL_SECONDS = 300.0


@dataclass
class _IndexCache:
    value: tuple[str, str] | None = None
    fetched_at: float = float("-inf")


_index_cache = _IndexCache()


def reset_index_cache() -> None:
    _index_cache.fetched_at = float("-inf")


async def _index_metadata(conn: psycopg.AsyncConnection) -> tuple[str, str] | None:
    if time.monotonic() - _index_cache.fetched_at > INDEX_TTL_SECONDS:
        cur = await conn.execute("SELECT provider, model FROM index_metadata")
        row = await cur.fetchone()
        _index_cache.value = (row[0], row[1]) if row else None
        _index_cache.fetched_at = time.monotonic()
    return _index_cache.value


# Long lexemes match by their first 5 characters: the Portuguese stemmer does not unify a verb
# and its noun ("devolver" -> devolv, "devolução" -> devoluc).
_TSQUERY = (
    "(SELECT string_agg(CASE WHEN length(l) >= 6 THEN quote_literal(left(l, 5)) || ':*' "
    "ELSE quote_literal(l) END, ' | ') "
    "FROM unnest(tsvector_to_array(to_tsvector('pt_unaccent', %(query)s))) l)::tsquery"
)


def _fuse_sql(table: str, key: str, join: str, where: str, *, vector: bool) -> str:
    vec_cte = (
        f"""vec AS (
            SELECT d.{key} AS id,
                   row_number() OVER (ORDER BY d.embedding <=> %(vec)s::vector, d.{key}) AS rank
            FROM {table} d {join} WHERE {where}
            ORDER BY d.embedding <=> %(vec)s::vector, d.{key} LIMIT {CANDIDATES})"""
        if vector
        else "vec AS (SELECT NULL::int AS id, NULL::bigint AS rank WHERE false)"
    )
    return f"""
        WITH q AS (SELECT {_TSQUERY} AS tsq),
        fts AS (
            SELECT d.{key} AS id,
                   row_number() OVER (ORDER BY ts_rank_cd(d.tsv, q.tsq) DESC, d.{key}) AS rank
            FROM {table} d {join}, q
            WHERE q.tsq IS NOT NULL AND d.tsv @@ q.tsq AND {where}
            ORDER BY ts_rank_cd(d.tsv, q.tsq) DESC, d.{key} LIMIT {CANDIDATES}),
        {vec_cte}
        SELECT COALESCE(fts.id, vec.id) AS id,
               COALESCE(1.0 / ({RRF_K} + fts.rank), 0) + COALESCE(1.0 / ({RRF_K} + vec.rank), 0)
                   AS score,
               fts.rank::int AS fts_rank, vec.rank::int AS vector_rank
        FROM fts FULL OUTER JOIN vec ON fts.id = vec.id
        ORDER BY score DESC, id
    """


async def _fuse(
    conn: psycopg.AsyncConnection,
    sql: str,
    params: dict,
    limit: int,
) -> list[dict]:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(sql, params)
        return (await cur.fetchall())[:limit]


async def _query_vector(
    conn: psycopg.AsyncConnection, embedder: Embedder, query: str
) -> tuple[str | None, str | None]:
    """Returns (vector literal, degraded_reason)."""
    meta = await _index_metadata(conn)
    if meta != (embedder.provider, embedder.model):
        logger.warning("index built with %s, query embedder is %s", meta, embedder.provider)
        return None, "index_provider_mismatch"
    try:
        (vec,) = await embed_cached(conn, embedder, [query], "query")
    except EmbeddingsUnavailable as exc:
        logger.warning("embeddings unavailable, falling back to full-text: %s", exc)
        return None, "embeddings_unavailable"
    return vector_literal(vec), None


async def search_policies(
    conn: psycopg.AsyncConnection, embedder: Embedder, query: str, *, limit: int = 5
) -> SearchResult[PolicyHit]:
    query = nfc(query)
    vec, reason = await _query_vector(conn, embedder, query) if query.strip() else (None, None)
    sql = _fuse_sql("policy_chunks", "chunk_id", "", "true", vector=vec is not None)
    fused = await _fuse(conn, sql, {"query": query, "vec": vec}, limit)
    hits: list[PolicyHit] = []
    if fused:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT chunk_id, section, title, parent_section, parent_title, breadcrumb, body "
                "FROM policy_chunks WHERE chunk_id = ANY(%s)",
                ([r["id"] for r in fused],),
            )
            rows = {r["chunk_id"]: r for r in await cur.fetchall()}
        hits = [
            PolicyHit(
                **{k: v for k, v in rows[r["id"]].items() if k != "chunk_id"},
                score=float(r["score"]),
                fts_rank=r["fts_rank"],
                vector_rank=r["vector_rank"],
            )
            for r in fused
        ]
    return SearchResult(hits=hits, mode="hybrid" if vec else "fulltext", degraded_reason=reason)


def _product_where(filters: ProductFilters) -> tuple[str, dict]:
    clauses = ["true"]
    params: dict = {}
    if filters.category_id is not None:
        clauses.append("p.category_id = %(category_id)s")
        params["category_id"] = filters.category_id
    if filters.only_sellable:
        clauses.append("p.is_sellable")
    if filters.max_price is not None:
        clauses.append("p.promo_price_brl <= %(max_price)s")
        params["max_price"] = filters.max_price
    if filters.exclude_ids:
        clauses.append("NOT (p.product_id = ANY(%(exclude_ids)s))")
        params["exclude_ids"] = sorted(filters.exclude_ids)
    return " AND ".join(clauses), params


_PRODUCT_JOIN = "JOIN products p ON p.product_id = d.product_id"


async def _product_hits(conn: psycopg.AsyncConnection, fused: list[dict]) -> list[ProductHit]:
    if not fused:
        return []
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT product_id, name, category_id, availability FROM products "
            "WHERE product_id = ANY(%s)",
            ([r["id"] for r in fused],),
        )
        rows = {r["product_id"]: r for r in await cur.fetchall()}
    return [
        ProductHit(
            **rows[r["id"]],
            score=float(r["score"]),
            fts_rank=r["fts_rank"],
            vector_rank=r["vector_rank"],
        )
        for r in fused
    ]


async def search_products(
    conn: psycopg.AsyncConnection,
    embedder: Embedder,
    query: str,
    *,
    filters: ProductFilters = ProductFilters(),  # noqa: B008 - frozen value object
    limit: int = 10,
) -> SearchResult[ProductHit]:
    query = nfc(query)
    vec, reason = await _query_vector(conn, embedder, query) if query.strip() else (None, None)
    where, params = _product_where(filters)
    sql = _fuse_sql(
        "product_search_docs", "product_id", _PRODUCT_JOIN, where, vector=vec is not None
    )
    fused = await _fuse(conn, sql, {"query": query, "vec": vec, **params}, limit)
    return SearchResult(
        hits=await _product_hits(conn, fused),
        mode="hybrid" if vec else "fulltext",
        degraded_reason=reason,
    )


async def similar_to_product(
    conn: psycopg.AsyncConnection,
    product_id: int,
    *,
    filters: ProductFilters = ProductFilters(),  # noqa: B008
    limit: int = 5,
) -> SearchResult[ProductHit]:
    where, params = _product_where(filters)
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            f"""
            SELECT d.product_id AS id,
                   1 - (d.embedding <=> ref.embedding) AS score,
                   row_number() OVER (ORDER BY d.embedding <=> ref.embedding, d.product_id)::int
                       AS vector_rank
            FROM product_search_docs d {_PRODUCT_JOIN},
                 (SELECT embedding FROM product_search_docs WHERE product_id = %(pid)s) ref
            WHERE d.product_id <> %(pid)s AND {where}
            ORDER BY d.embedding <=> ref.embedding, d.product_id LIMIT %(limit)s
            """,
            {"pid": product_id, "limit": limit, **params},
        )
        fused = [{**r, "fts_rank": None} for r in await cur.fetchall()]
    return SearchResult(hits=await _product_hits(conn, fused), mode="vector")
