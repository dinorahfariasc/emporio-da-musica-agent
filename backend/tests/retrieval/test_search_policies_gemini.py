import pytest

from app.config import Settings
from app.embeddings.gemini import GeminiEmbedder
from app.retrieval import search_policies
from etl.__main__ import seed

pytestmark = pytest.mark.gemini


@pytest.mark.parametrize("query", ["Can I return my order?", "¿Puedo devolver mi pedido?"])
async def test_cross_language_queries_find_4_1(local_database_url, tmp_path, monkeypatch, query):
    settings = Settings()
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY not set")
    from app.db import connect

    embedder = GeminiEmbedder(settings.gemini_api_key, settings.embeddings_model, purpose="seed")
    monkeypatch.setattr("etl.__main__.get_embedder", lambda *a, **k: embedder)
    await seed(local_database_url, report_path=tmp_path / "r.md")
    async with await connect(local_database_url) as conn:
        result = await search_policies(conn, embedder, query)
    assert "4.1" in [h.section for h in result.hits][:3]
