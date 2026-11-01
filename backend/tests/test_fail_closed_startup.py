import pytest

from app.config import Environment, LLMProvider, Settings
from app.main import check_fail_closed_config


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_non_production_never_raises():
    check_fail_closed_config(_settings(environment=Environment.LOCAL))


def test_production_with_everything_configured_does_not_raise():
    check_fail_closed_config(
        _settings(
            environment=Environment.PRODUCTION,
            service_jwt_secret="s",
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
                service_jwt_secret="s",
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
                service_jwt_secret="s",
                database_url="postgresql://x",
                llm_provider=LLMProvider.OPENROUTER,
                openrouter_api_key=None,
            )
        )


def test_production_with_fake_provider_does_not_require_a_key():
    check_fail_closed_config(
        _settings(
            environment=Environment.PRODUCTION,
            service_jwt_secret="s",
            database_url="postgresql://x",
            llm_provider=LLMProvider.FAKE,
        )
    )
