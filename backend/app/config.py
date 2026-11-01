from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    CI = "ci"
    PRODUCTION = "production"


class LLMProvider(StrEnum):
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    FAKE = "fake"


class RouterProvider(StrEnum):
    JEV = "jev"
    HAIKU = "haiku"
    OPENROUTER = "openrouter"
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
    # Router model for the openrouter provider; empty means specialist_model.
    router_model: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    router_confidence_threshold: float = 0.75
    router_timeout_ms: int = 2500  # whole router budget: primary + fallback
    agent_max_steps: int = 8
    llm_max_tokens: int = 1024
    llm_timeout_s: float = 30
    turn_timeout_s: float = 60
    history_max_messages: int = 12
    input_max_chars: int = 2000

    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    typesafe_api_key: str | None = None
    gemini_api_key: str | None = None
    # /mcp is mounted only when this is set (#8).
    mcp_api_key: str | None = None

    # specs/004-auth-limits-deploy
    service_jwt_secret: str | None = None
    rate_limit_per_minute: int = 20
    daily_token_budget: int = 200_000
    budget_timezone: str = "America/Campo_Grande"


@lru_cache
def get_settings() -> Settings:
    return Settings()
