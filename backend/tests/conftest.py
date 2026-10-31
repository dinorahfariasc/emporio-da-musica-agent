import os
from collections.abc import Callable, Iterator
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def make_client() -> Iterator[Callable[..., TestClient]]:
    def _make(**overrides: object) -> TestClient:
        settings = Settings(_env_file=None, **overrides)
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set (run `docker compose up -d` locally)")
    return url


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@pytest.fixture
def local_database_url(database_url: str) -> str:
    """For tests that drop tables: refuse non-local hosts unless explicitly allowed."""
    host = urlsplit(database_url).hostname
    if host not in LOCAL_HOSTS and os.environ.get("ALLOW_DESTRUCTIVE_TESTS") != "1":
        pytest.skip(f"destructive test skipped on non-local host {host}")
    return database_url
