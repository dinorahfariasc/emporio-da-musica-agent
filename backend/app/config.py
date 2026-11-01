from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    CI = "ci"
    PRODUCTION = "production"


class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    FAKE = "fake"


class RouterProvider(StrEnum):
    JEV = "jev"
    HAIKU = "haiku"
    FAKE = "fake"


class EmbeddingsProvider(StrEnum):
    GEMINI = "gemini"
    FAKE = "fake"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Environment = Environment.LOCAL
    database_url: str | None = None
    # Direct (non-pooled) URL; used by the seed when set.
    database_url_unpooled: str | None = None

    llm_provider: LLMProvider = LLMProvider.FAKE
    router_provider: RouterProvider = RouterProvider.FAKE
    embeddings_provider: EmbeddingsProvider = EmbeddingsProvider.FAKE
    embeddings_model: str = "gemini-embedding-001"

    specialist_model: str = "claude-haiku-4-5-20251001"
    general_model: str = "claude-sonnet-5-5"
    router_confidence_threshold: float = 0.75
    router_timeout_ms: int = 2500  # whole router budget: primary + fallback
    agent_max_steps: int = 8
    llm_max_tokens: int = 1024
    llm_timeout_s: float = 30
    turn_timeout_s: float = 60
    history_max_messages: int = 12
    input_max_chars: int = 2000

    anthropic_api_key: str | None = None
    typesafe_api_key: str | None = None
    gemini_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
