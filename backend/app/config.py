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
    VOYAGE = "voyage"
    FAKE = "fake"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Environment = Environment.LOCAL
    database_url: str | None = None

    llm_provider: LLMProvider = LLMProvider.FAKE
    router_provider: RouterProvider = RouterProvider.FAKE
    embeddings_provider: EmbeddingsProvider = EmbeddingsProvider.FAKE

    anthropic_api_key: str | None = None
    typesafe_api_key: str | None = None
    voyage_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
