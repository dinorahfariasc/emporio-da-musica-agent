"""Senior review (#44): no public OpenAPI/docs/stream-test surface in production."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def reloaded_app(monkeypatch):
    """app.main builds `app` (and decides what to mount) at import time from the module-level
    `settings`, so exercising a different environment needs a real module reload, not a
    dependency override (same caveat as the MCP mount added in #43)."""

    def _build(env: dict[str, str]):
        from app.config import get_settings

        for key in ("ENVIRONMENT", "SERVICE_JWT_SECRET", "DATABASE_URL", "LLM_PROVIDER"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        import app.main as main_module

        importlib.reload(main_module)
        return main_module.app

    yield _build

    # Restore the normal (non-production) app for every other test module.
    from app.config import get_settings

    get_settings.cache_clear()
    import app.main as main_module

    importlib.reload(main_module)


def test_docs_and_openapi_are_disabled_in_production(reloaded_app):
    app = reloaded_app(
        {
            "ENVIRONMENT": "production",
            "SERVICE_JWT_SECRET": "s" * 32,
            "DATABASE_URL": "postgresql://x",
            "LLM_PROVIDER": "fake",
        }
    )
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/api/stream-test").status_code == 404


def test_docs_and_stream_test_are_available_outside_production(reloaded_app):
    app = reloaded_app({"ENVIRONMENT": "local"})
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").status_code == 200
        # .stream(): just the status line, without waiting for the ~3s demo SSE body.
        with client.stream("GET", "/api/stream-test") as response:
            assert response.status_code == 200
