import json
import logging
from pathlib import Path

import pytest

from app.db import connect
from app.embeddings.fake import FakeEmbedder
from app.retrieval import search_policies
from etl.__main__ import seed
from tests.retrieval.conftest import BrokenEmbedder, CountingEmbedder

REFERENCE = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "policy_reference_queries.json").read_text()
)


async def test_returns_query_finds_4_1_in_vector_and_overall(conn, embedder):
    result = await search_policies(conn, embedder, "posso devolver meu pedido?")

    sections = [h.section for h in result.hits]
    assert result.mode == "hybrid"
    assert "4.1" in sections[:3]
    assert next(h for h in result.hits if h.section == "4.1").vector_rank <= 3
    assert result.hits[0].breadcrumb.startswith("§4")


async def test_fulltext_fallback_when_embeddings_fail(conn, caplog):
    with caplog.at_level(logging.WARNING):
        result = await search_policies(conn, BrokenEmbedder(), "posso devolver meu pedido?")

    assert result.mode == "fulltext"
    assert result.degraded_reason == "embeddings_unavailable"
    assert "4.1" in [h.section for h in result.hits][:3]
    assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1


@pytest.mark.parametrize("case", REFERENCE, ids=[c["query"] for c in REFERENCE])
async def test_reference_queries(conn, embedder, case):
    hybrid = await search_policies(conn, embedder, case["query"])
    fulltext = await search_policies(conn, BrokenEmbedder(), case["query"])

    assert set(case["expected"]) & {h.section for h in hybrid.hits[:3]}
    assert fulltext.hits


async def test_repeated_query_makes_no_embedder_call(conn, embedder):
    await search_policies(conn, embedder, "posso devolver meu pedido?")
    await search_policies(conn, embedder, "  Posso  DEVOLVER meu pedido? ")

    assert len(embedder.calls) == 1


async def test_stopword_only_query_has_no_fulltext_hits(conn):
    result = await search_policies(conn, BrokenEmbedder(), "de a o")
    assert result.hits == []


async def test_provider_mismatch_degrades(conn):
    other = FakeEmbedder()
    other.provider = "gemini"

    result = await search_policies(conn, other, "devolução")

    assert result.mode == "fulltext"
    assert result.degraded_reason == "index_provider_mismatch"


async def test_reseed_embeds_documents_once(local_database_url, tmp_path, monkeypatch):
    async with await connect(local_database_url) as c:
        await c.execute("DROP TABLE IF EXISTS embedding_cache")
        await c.commit()
    counter = CountingEmbedder()
    monkeypatch.setattr("etl.__main__.get_embedder", lambda *a, **k: counter)

    await seed(local_database_url, report_path=tmp_path / "r.md")
    first = sum(n for n, kind in counter.calls if kind == "document")
    counter.calls.clear()
    await seed(local_database_url, report_path=tmp_path / "r.md")

    assert first > 0
    assert counter.calls == []
