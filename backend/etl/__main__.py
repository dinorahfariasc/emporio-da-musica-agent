"""Seed command: `uv run python -m etl [--yes]` (contracts/seed-cli.md)."""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

import psycopg

from app.agent.state import ensure_agent_tables
from app.config import EmbeddingsProvider, Environment, Settings
from app.db import connect
from app.embeddings import EMBEDDING_DIM, Embedder, get_embedder
from app.embeddings.cache import embed_cached, vector_literal
from etl.checksums import table_stats
from etl.documents import build_product_doc
from etl.load import ensure_cache, reload
from etl.models import ValidationFailed
from etl.pipeline import DATA_DIR, REPORT_PATH, build_payload
from etl.policies import build_chunks
from etl.report import render

logger = logging.getLogger("etl")

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class Refused(Exception):
    pass


def seed_url(settings: Settings) -> str:
    if settings.database_url_unpooled:
        return settings.database_url_unpooled
    url = settings.database_url
    if not url:
        raise Refused("DATABASE_URL (or DATABASE_URL_UNPOOLED) is not set")
    if "-pooler" in (urlsplit(url).hostname or ""):
        # A long DDL transaction should not go through PgBouncer.
        raise Refused("DATABASE_URL is Neon's pooled endpoint; set DATABASE_URL_UNPOOLED")
    return url


def describe_target(url: str) -> tuple[str, bool]:
    parts = urlsplit(url)
    host = parts.hostname or "?"
    is_local = host in LOCAL_HOSTS
    return f"{host}{parts.path or '/'} ({'local' if is_local else 'remote'})", is_local


def check_guards(settings: Settings, is_local: bool, confirmed: bool) -> None:
    if not is_local and not confirmed:
        raise Refused("target is not local; re-run with --yes to seed it")
    if settings.embeddings_provider is EmbeddingsProvider.FAKE and (
        settings.environment is Environment.PRODUCTION or not is_local
    ):
        # Keyed on the target as well: a laptop .env says "local" while pointing at Neon.
        raise Refused("EMBEDDINGS_PROVIDER=fake is not allowed for production or remote targets")


async def build_index_tables(
    conn: psycopg.AsyncConnection,
    embedder: Embedder,
    payload_tables: dict[str, list[dict]],
    data_dir: Path,
) -> dict[str, list[dict]]:
    """Embeds policy chunks and product docs (through the cache) into insert-ready rows."""
    chunks = build_chunks(data_dir / "store_policies.pdf")
    categories = {c["category_id"]: c["name"] for c in payload_tables["categories"]}
    products = payload_tables["products"]
    docs = [build_product_doc(p, categories[p["category_id"]]) for p in products]
    chunk_vectors = await embed_cached(conn, embedder, [c.search_text for c in chunks], "document")
    doc_vectors = await embed_cached(conn, embedder, docs, "document")
    await conn.commit()
    return {
        "policy_chunks": [
            {
                "chunk_id": c.chunk_id,
                "section": c.section,
                "title": c.title,
                "parent_section": c.parent_section,
                "parent_title": c.parent_title,
                "breadcrumb": c.breadcrumb,
                "body": c.body,
                "search_text": c.search_text,
                "embedding": vector_literal(v),
            }
            for c, v in zip(chunks, chunk_vectors, strict=True)
        ],
        "product_search_docs": [
            {"product_id": p["product_id"], "search_text": d, "embedding": vector_literal(v)}
            for p, d, v in zip(products, docs, doc_vectors, strict=True)
        ],
        "index_metadata": [
            {"provider": embedder.provider, "model": embedder.model, "dim": EMBEDDING_DIM}
        ],
    }


async def seed(
    url: str,
    data_dir: Path = DATA_DIR,
    report_path: Path = REPORT_PATH,
    settings: Settings | None = None,
) -> None:
    settings = settings or Settings(_env_file=None)
    payload = build_payload(data_dir)
    # Written before the reload: the report depends only on the inputs, and a failed write must
    # not leave the tables replaced while the command reports an error.
    await asyncio.to_thread(report_path.write_text, render(payload), encoding="utf-8")
    print(f"report: {report_path}")
    async with await connect(url) as conn:
        await ensure_cache(conn)
        embedder = get_embedder(settings, purpose="seed")
        index = await build_index_tables(conn, embedder, payload.tables, data_dir)
        await reload(conn, {**payload.tables, **index})
        await ensure_agent_tables(conn)
        print(f"embeddings: {embedder.provider}/{embedder.model} ({EMBEDDING_DIM} dims)")
        for table, count, checksum in await table_stats(conn):
            print(f"{table:<20} {count:>4}  {checksum}")


def main(argv: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m etl", description="Seed the store database.")
    parser.add_argument("--yes", action="store_true", help="confirm a non-local target")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(message)s")
    settings = settings or Settings()

    target = "?"
    try:
        url = seed_url(settings)
        target, is_local = describe_target(url)
        print(f"target: {target}")
        check_guards(settings, is_local, args.yes)
        asyncio.run(seed(url, settings=settings))
    except Refused as exc:
        logger.error("refused: %s", exc)
        return 1
    except ValidationFailed as exc:
        logger.error("validation failed:\n%s", exc)
        return 1
    except psycopg.OperationalError as exc:
        # Connection errors can echo the host and user; report only the masked target.
        logger.error("seed failed: %s connecting to %s", type(exc).__name__, target)
        return 1
    except Exception as exc:  # noqa: BLE001 - any failure is exit 1 with a message
        logger.error("seed failed: %s: %s", type(exc).__name__, exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
