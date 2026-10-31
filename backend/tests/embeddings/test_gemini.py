import json
import math

import httpx
import pytest

from app.embeddings import EMBEDDING_DIM, EmbeddingsUnavailable
from app.embeddings.gemini import GeminiEmbedder


def _ok(request: httpx.Request) -> httpx.Response:
    n = len(json.loads(request.content)["requests"])
    return httpx.Response(200, json={"embeddings": [{"values": [3.0, 4.0] * 1000}] * n})


def _embedder(handler, purpose="seed", sleeps=None):
    async def sleep(seconds):
        if sleeps is not None:
            sleeps.append(seconds)

    return GeminiEmbedder(
        "secret-key", purpose=purpose, transport=httpx.MockTransport(handler), sleep=sleep
    )


async def test_retries_after_429_with_retry_after():
    calls, sleeps = [], []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return _ok(request)

    vectors = await _embedder(handler, sleeps=sleeps).embed(["a"], "document")
    assert len(vectors) == 1
    assert sleeps == [1.0]


async def test_request_shape_and_normalization():
    seen = []

    def handler(request):
        seen.append(request)
        return _ok(request)

    (vec,) = await _embedder(handler).embed(["a"], "query")
    body = json.loads(seen[0].content)["requests"][0]
    assert body["taskType"] == "RETRIEVAL_QUERY"
    assert body["outputDimensionality"] == EMBEDDING_DIM
    assert seen[0].headers["x-goog-api-key"] == "secret-key"
    assert len(vec) == EMBEDDING_DIM
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, abs_tol=1e-6)


async def test_batches_respect_token_and_request_limits():
    sizes = []

    def handler(request):
        sizes.append(len(json.loads(request.content)["requests"]))
        return _ok(request)

    await _embedder(handler).embed(["x"] * 250, "document")
    assert sizes == [100, 100, 50]
    sizes.clear()
    await _embedder(handler).embed(["y" * 30_000] * 3, "document")  # 10,000 tokens each
    assert sizes == [2, 1]


async def test_query_profile_does_not_retry_and_hides_key():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "1"})

    with pytest.raises(EmbeddingsUnavailable) as exc:
        await _embedder(handler, purpose="query").embed(["a"], "query")
    assert len(calls) == 1
    assert "secret-key" not in str(exc.value)


@pytest.mark.gemini
async def test_real_api_smoke():
    from app.config import Settings

    settings = Settings()
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY not set")
    (vec,) = await GeminiEmbedder(settings.gemini_api_key).embed(["olá"], "query")
    assert len(vec) == EMBEDDING_DIM
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, abs_tol=1e-6)
