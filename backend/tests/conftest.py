import asyncio
import os
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import AsyncConnectionPool

from app.config import Settings, get_settings
from app.embeddings.fake import FakeEmbedder
from app.main import app
from app.tools.context import STORE_TZ, FixedClock, ToolContext


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


def _local_url_or_skip() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set (run `docker compose up -d` locally)")
    host = urlsplit(url).hostname
    if host not in LOCAL_HOSTS and os.environ.get("ALLOW_DESTRUCTIVE_TESTS") != "1":
        pytest.skip(f"destructive test skipped on non-local host {host}")
    return url


@pytest.fixture(scope="session")
def seeded_db() -> str:
    """Seeds the local DB once per session with fake embeddings (skips without a local DB)."""
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from etl.__main__ import seed

    url = _local_url_or_skip()
    with TemporaryDirectory() as tmp:
        asyncio.run(seed(url, report_path=Path(tmp) / "report.md"))
    return url


@pytest.fixture
def tool_events() -> list[dict]:
    return []


@pytest.fixture
async def tool_ctx(seeded_db, tool_events):
    pool = AsyncConnectionPool(
        seeded_db, min_size=0, max_size=4, open=False, kwargs={"prepare_threshold": None}
    )
    await pool.open()
    try:
        yield ToolContext(
            pool=pool,
            embedder=FakeEmbedder(),
            conversation_id=f"test-{uuid.uuid4().hex[:12]}",
            clock=FixedClock(datetime(2026, 11, 3, 10, 0, tzinfo=STORE_TZ)),
            emit=tool_events.append,
        )
    finally:
        await pool.close()
