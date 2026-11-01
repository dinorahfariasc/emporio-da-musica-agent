from app.config import EmbeddingsProvider, LLMProvider, RouterProvider, Settings


def test_defaults_use_fake_providers_so_ci_needs_no_keys():
    settings = Settings(_env_file=None)

    assert settings.llm_provider is LLMProvider.FAKE
    assert settings.router_provider is RouterProvider.FAKE
    assert settings.embeddings_provider is EmbeddingsProvider.FAKE
    assert settings.embeddings_model == "gemini-embedding-001"
    assert settings.database_url_unpooled is None


def test_providers_are_selected_from_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ROUTER_PROVIDER", "jev")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "gemini")

    settings = Settings(_env_file=None)

    assert settings.llm_provider is LLMProvider.ANTHROPIC
    assert settings.router_provider is RouterProvider.JEV
    assert settings.embeddings_provider is EmbeddingsProvider.GEMINI


def test_agent_defaults():
    settings = Settings(_env_file=None)

    assert settings.specialist_model == "claude-haiku-4-5-20251001"
    assert settings.general_model == "claude-sonnet-5-5"
    assert settings.router_confidence_threshold == 0.75
    assert settings.router_timeout_ms == 2500
    assert settings.agent_max_steps == 8
    assert settings.llm_max_tokens == 1024
    assert settings.llm_timeout_s == 30
    assert settings.turn_timeout_s == 60
    assert settings.history_max_messages == 12
    assert settings.input_max_chars == 2000


def test_agent_settings_come_from_environment(monkeypatch):
    monkeypatch.setenv("AGENT_MAX_STEPS", "3")
    monkeypatch.setenv("ROUTER_TIMEOUT_MS", "100")

    settings = Settings(_env_file=None)

    assert settings.agent_max_steps == 3
    assert settings.router_timeout_ms == 100
