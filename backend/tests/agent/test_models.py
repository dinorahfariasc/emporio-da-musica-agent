from app.agent.models import chat_model
from app.agent.router import OpenRouterRouter
from app.config import LLMProvider, RouterProvider, Settings


def _settings(**kw) -> Settings:
    return Settings(
        _env_file=None,
        llm_provider=LLMProvider.OPENROUTER,
        router_provider=RouterProvider.OPENROUTER,
        openrouter_api_key="sk-or-test",
        specialist_model="vendor/small",
        general_model="vendor/big",
        router_model="vendor/decider",
        **kw,
    )


def test_openrouter_chat_model_points_at_openrouter_with_role_model():
    settings = _settings()
    specialist = chat_model(settings, "specialist")
    general = chat_model(settings, "general")
    assert specialist.model_name == "vendor/small"
    assert general.model_name == "vendor/big"
    assert str(specialist.openai_api_base) == "https://openrouter.ai/api/v1"


def test_openrouter_router_uses_router_model_then_specialist_model():
    assert OpenRouterRouter(_settings())._chat_model().model_name == "vendor/decider"
    fallback = Settings(_env_file=None, openrouter_api_key="k", specialist_model="vendor/small")
    assert OpenRouterRouter(fallback)._chat_model().model_name == "vendor/small"
