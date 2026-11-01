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
    # Vercel sets this automatically on every deployment; used as a second signal for "are we in
    # production" so a forgotten/misconfigured ENVIRONMENT var does not fail open (research.md R7).
    vercel_env: str | None = None
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


def is_production(settings: Settings) -> bool:
    """True if `ENVIRONMENT=production` OR Vercel's own `VERCEL_ENV=production` is set.

    Relying on `ENVIRONMENT` alone would fail OPEN if that var is simply forgotten on a real
    deploy (it defaults to `local`); `VERCEL_ENV` is set automatically by the platform itself and
    cannot be forgotten the same way (research.md R7).
    """
    return settings.environment is Environment.PRODUCTION or settings.vercel_env == "production"


MIN_SERVICE_JWT_SECRET_LENGTH = 32


def check_fail_closed_config(settings: Settings | None = None) -> None:
    """Refuse to serve chat requests with missing/weak production secrets (FR-015, research.md R7).

    Called both at app startup (lifespan) and on every request through `require_service_account`
    (`app/auth/dependency.py`): a FastAPI lifespan is not guaranteed to run the same way on every
    Vercel Services deployment target, so the per-request call is the check that actually matters
    in production, not just defense in depth.
    """
    settings = settings or get_settings()
    if not is_production(settings):
        return
    required = [
        ("SERVICE_JWT_SECRET", settings.service_jwt_secret),
        ("DATABASE_URL", settings.database_url),
    ]
    # The fake provider needs no key; it is a deliberate choice, not a missing one.
    if settings.llm_provider is LLMProvider.ANTHROPIC:
        required.append(("ANTHROPIC_API_KEY", settings.anthropic_api_key))
    elif settings.llm_provider is LLMProvider.OPENROUTER:
        required.append(("OPENROUTER_API_KEY", settings.openrouter_api_key))
    missing = [name for name, value in required if not value]
    if missing:
        raise RuntimeError(
            f"Refusing to start in production with missing required config: {', '.join(missing)}"
        )
    if (
        settings.service_jwt_secret
        and len(settings.service_jwt_secret) < MIN_SERVICE_JWT_SECRET_LENGTH
    ):
        raise RuntimeError(
            f"SERVICE_JWT_SECRET must be at least {MIN_SERVICE_JWT_SECRET_LENGTH} characters in "
            "production"
        )
