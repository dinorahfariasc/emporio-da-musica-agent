from collections.abc import Sequence
from typing import Final, Literal, Protocol

from app.config import EmbeddingsProvider, Settings

EMBEDDING_DIM: Final = 768
InputType = Literal["document", "query"]


class EmbeddingsUnavailable(Exception):
    """The provider failed (after the profile's retries); callers degrade to full-text."""


class Embedder(Protocol):
    provider: str
    model: str

    async def embed(self, texts: Sequence[str], input_type: InputType) -> list[list[float]]: ...


def get_embedder(settings: Settings, *, purpose: Literal["seed", "query"]) -> Embedder:
    if settings.embeddings_provider is EmbeddingsProvider.FAKE:
        from app.embeddings.fake import FakeEmbedder

        return FakeEmbedder()
    from app.embeddings.gemini import GeminiEmbedder

    if not settings.gemini_api_key:
        raise EmbeddingsUnavailable("GEMINI_API_KEY is not set")
    return GeminiEmbedder(settings.gemini_api_key, settings.embeddings_model, purpose=purpose)
