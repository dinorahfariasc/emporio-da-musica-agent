import os
from collections.abc import Callable, Iterator

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
