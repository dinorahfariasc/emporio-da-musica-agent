"""Gemini embeddings over plain HTTP (research R2). The API key only travels in a header."""

import asyncio
import math
import re
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Literal

import httpx

from app.embeddings import EMBEDDING_DIM, EmbeddingsUnavailable, InputType

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MAX_BATCH_TOKENS = 20_000
MAX_BATCH_REQUESTS = 100
DEFAULT_RETRY_DELAY = 30.0
TASK_TYPES = {"document": "RETRIEVAL_DOCUMENT", "query": "RETRIEVAL_QUERY"}

# purpose -> (attempts per batch, total seconds, per-request timeout)
PROFILES = {"seed": (5, 120.0, 60.0), "query": (1, 3.0, 3.0)}


def _estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / 3)


def _batches(texts: Sequence[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    tokens = 0
    for text in texts:
        cost = _estimate_tokens(text)
        if current and (tokens + cost > MAX_BATCH_TOKENS or len(current) >= MAX_BATCH_REQUESTS):
            batches.append(current)
            current, tokens = [], 0
        current.append(text)
        tokens += cost
    if current:
        batches.append(current)
    return batches


def _normalize(vector: Sequence[float]) -> list[float]:
    values = list(vector)[:EMBEDDING_DIM]
    norm = math.sqrt(sum(v * v for v in values))
    return [v / norm for v in values] if norm else values


def _retry_delay(response: httpx.Response) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return float(header)
        except ValueError:
            pass
    try:
        for detail in response.json().get("error", {}).get("details", []):
            match = re.fullmatch(r"([\d.]+)s", str(detail.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    except ValueError:
        pass
    return DEFAULT_RETRY_DELAY


class GeminiEmbedder:
    provider = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        *,
        purpose: Literal["seed", "query"] = "query",
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._attempts, self._budget, self._timeout = PROFILES[purpose]
        self._transport = transport
        self._sleep = sleep

    async def embed(self, texts: Sequence[str], input_type: InputType) -> list[list[float]]:
        if not texts:
            return []
        deadline = time.monotonic() + self._budget
        out: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            for batch in _batches(texts):
                out.extend(await self._embed_batch(client, batch, input_type, deadline))
        return out

    async def _embed_batch(
        self, client: httpx.AsyncClient, batch: list[str], input_type: InputType, deadline: float
    ) -> list[list[float]]:
        body = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": TASK_TYPES[input_type],
                    "outputDimensionality": EMBEDDING_DIM,
                }
                for text in batch
            ]
        }
        url = f"{BASE_URL}/models/{self.model}:batchEmbedContents"
        for attempt in range(1, self._attempts + 1):
            try:
                response = await client.post(
                    url, json=body, headers={"x-goog-api-key": self._api_key}
                )
            except httpx.HTTPError as exc:
                # Message only the exception type: it must never echo request details.
                raise EmbeddingsUnavailable(
                    f"Gemini request failed: {type(exc).__name__}"
                ) from None
            if response.status_code == 200:
                vectors = [_normalize(e["values"]) for e in response.json()["embeddings"]]
                if len(vectors) != len(batch):
                    raise EmbeddingsUnavailable("Gemini returned an unexpected number of vectors")
                return vectors
            retryable = response.status_code in (429, 503)
            delay = _retry_delay(response) if retryable else 0.0
            if not retryable or attempt == self._attempts or time.monotonic() + delay > deadline:
                raise EmbeddingsUnavailable(f"Gemini returned HTTP {response.status_code}")
            await self._sleep(delay)
        raise EmbeddingsUnavailable("Gemini retries exhausted")  # pragma: no cover
