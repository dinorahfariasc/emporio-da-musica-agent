from app.config import EmbeddingsProvider, LLMProvider, RouterProvider, Settings


def test_defaults_use_fake_providers_so_ci_needs_no_keys():
    settings = Settings(_env_file=None)

    assert settings.llm_provider is LLMProvider.FAKE
    assert settings.router_provider is RouterProvider.FAKE
    assert settings.embeddings_provider is EmbeddingsProvider.FAKE


def test_providers_are_selected_from_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ROUTER_PROVIDER", "jev")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "gemini")

    settings = Settings(_env_file=None)

    assert settings.llm_provider is LLMProvider.ANTHROPIC
    assert settings.router_provider is RouterProvider.JEV
    assert settings.embeddings_provider is EmbeddingsProvider.GEMINI
