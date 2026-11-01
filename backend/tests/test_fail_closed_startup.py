import pytest
from fastapi.testclient import TestClient

from app.config import Environment, LLMProvider, Settings, check_fail_closed_config, get_settings
from app.main import app

VALID_SECRET = "s" * 32


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_non_production_never_raises():
    check_fail_closed_config(_settings(environment=Environment.LOCAL))


def test_production_with_everything_configured_does_not_raise():
    check_fail_closed_config(
        _settings(
            environment=Environment.PRODUCTION,
            service_jwt_secret=VALID_SECRET,
            database_url="postgresql://x",
            llm_provider=LLMProvider.ANTHROPIC,
            anthropic_api_key="k",
        )
    )


def test_production_without_service_jwt_secret_raises():
    with pytest.raises(RuntimeError, match="SERVICE_JWT_SECRET"):
        check_fail_closed_config(
            _settings(
                environment=Environment.PRODUCTION,
                service_jwt_secret=None,
                database_url="postgresql://x",
                llm_provider=LLMProvider.ANTHROPIC,
                anthropic_api_key="k",
            )
        )


def test_production_without_database_url_raises():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        check_fail_closed_config(
            _settings(
                environment=Environment.PRODUCTION,
                service_jwt_secret=VALID_SECRET,
                database_url=None,
                llm_provider=LLMProvider.ANTHROPIC,
                anthropic_api_key="k",
            )
        )


def test_production_with_openrouter_but_no_key_raises():
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        check_fail_closed_config(
            _settings(
                environment=Environment.PRODUCTION,
                service_jwt_secret=VALID_SECRET,
                database_url="postgresql://x",
                llm_provider=LLMProvider.OPENROUTER,
                openrouter_api_key=None,
            )
        )


def test_production_with_fake_provider_does_not_require_a_key():
    check_fail_closed_config(
        _settings(
            environment=Environment.PRODUCTION,
            service_jwt_secret=VALID_SECRET,
            database_url="postgresql://x",
            llm_provider=LLMProvider.FAKE,
        )
    )


def test_a_short_service_jwt_secret_raises_in_production():
    with pytest.raises(RuntimeError, match="SERVICE_JWT_SECRET must be at least"):
        check_fail_closed_config(
            _settings(
                environment=Environment.PRODUCTION,
                service_jwt_secret="too-short",
                database_url="postgresql://x",
                llm_provider=LLMProvider.FAKE,
            )
        )


def test_a_short_service_jwt_secret_is_fine_outside_production():
    check_fail_closed_config(
        _settings(environment=Environment.LOCAL, service_jwt_secret="x", database_url=None)
    )


def test_vercel_env_production_is_treated_as_production_even_if_environment_is_not_set():
    # ENVIRONMENT defaults to "local"; a deploy that only ever gets Vercel's own VERCEL_ENV set
    # (easy to do by forgetting the app-specific var) must still fail closed.
    with pytest.raises(RuntimeError, match="SERVICE_JWT_SECRET"):
        check_fail_closed_config(
            _settings(
                environment=Environment.LOCAL,
                vercel_env="production",
                service_jwt_secret=None,
                database_url="postgresql://x",
                llm_provider=LLMProvider.FAKE,
            )
        )


def test_vercel_preview_env_is_not_treated_as_production():
    check_fail_closed_config(
        _settings(environment=Environment.LOCAL, vercel_env="preview", service_jwt_secret=None)
    )


@pytest.fixture
def fresh_settings_cache(monkeypatch):
    """The lifespan calls the module-level `get_settings()` directly (not a FastAPI dependency),
    so a dependency override does not reach it; monkeypatching the env and clearing the lru_cache
    is what actually exercises a different configuration through the real startup path."""
    get_settings.cache_clear()
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("SERVICE_JWT_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    yield
    get_settings.cache_clear()


def test_app_startup_through_the_real_lifespan_raises_in_production(
    monkeypatch, fresh_settings_cache
):
    """QA: exercise check_fail_closed_config through the actual app lifespan, not just the
    function in isolation — TestClient as a context manager runs FastAPI's startup/shutdown."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    # SERVICE_JWT_SECRET deliberately left unset.
    with pytest.raises(RuntimeError, match="SERVICE_JWT_SECRET"), TestClient(app):
        pass


def test_app_startup_through_the_real_lifespan_does_not_raise_when_configured(
    monkeypatch, fresh_settings_cache
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("SERVICE_JWT_SECRET", VALID_SECRET)
    with TestClient(app):
        pass
