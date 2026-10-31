"""Read/write-through cache over embedding_cache (research R10)."""

from collections.abc import Sequence
from hashlib import sha256

import psycopg

from app.embeddings import Embedder, InputType
from app.text import nfc, normalize_for_cache


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


def parse_vector(text: str) -> list[float]:
    return [float(v) for v in text.strip("[]").split(",")]


def text_key(text: str, input_type: InputType) -> str:
    normalized = nfc(text) if input_type == "document" else normalize_for_cache(text)
    return sha256(normalized.encode()).hexdigest()


async def embed_cached(
    conn: psycopg.AsyncConnection,
    embedder: Embedder,
    texts: Sequence[str],
    input_type: InputType,
) -> list[list[float]]:
    keys = [text_key(t, input_type) for t in texts]
    cur = await conn.execute(
        "SELECT text_key, embedding::text FROM embedding_cache "
        "WHERE provider = %s AND model = %s AND input_type = %s AND text_key = ANY(%s)",
        (embedder.provider, embedder.model, input_type, list(set(keys))),
    )
    found = {key: parse_vector(vec) for key, vec in await cur.fetchall()}
    misses = {key: text for key, text in zip(keys, texts, strict=True) if key not in found}
    if misses:
        vectors = await embedder.embed(list(misses.values()), input_type)
        async with conn.transaction(), conn.cursor() as write:
            await write.executemany(
                "INSERT INTO embedding_cache (provider, model, input_type, text_key, embedding) "
                "VALUES (%s, %s, %s, %s, %s::vector) ON CONFLICT DO NOTHING",
                [
                    (embedder.provider, embedder.model, input_type, key, vector_literal(vec))
                    for key, vec in zip(misses, vectors, strict=True)
                ],
            )
        found.update(zip(misses, vectors, strict=True))
    return [found[key] for key in keys]
