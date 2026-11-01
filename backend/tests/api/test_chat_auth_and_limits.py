"""End-to-end POST /api/chat coverage for auth and limits (contracts/service-jwt.md,
contracts/rate-limit-and-budget.md). Uses the real require_service_account dependency (a minted
JWT, not an override) so the whole chain is exercised, with a fake router/model underneath.
"""

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from app.agent.fakes import FakeToolModel
from app.agent.router import FakeRouter, Route
from app.api.chat import Runtime, get_runtime
from app.config import Settings, get_settings
from app.limits import enforce
from app.main import app

SECRET = "test-secret-at-least-32-bytes-long!!"
FIXTURES = Path(__file__).parents[3] / "contracts" / "chat-stream" / "fixtures"


class _FrozenDatetime(datetime):
    """Patched onto app.limits.enforce.datetime so the 20/min test never straddles a real
    minute boundary (contracts/rate-limit-and-budget.md fixed-window semantics)."""

    _frozen: datetime

    @classmethod
    def now(cls, tz=None):
        return cls._frozen if tz is None else cls._frozen.astimezone(tz)


@pytest.fixture
def frozen_time(monkeypatch):
    frozen = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
    stub = type("_Frozen", (_FrozenDatetime,), {"_frozen": frozen})
    monkeypatch.setattr(enforce, "datetime", stub)
    return frozen


async def _no_ctx(settings, user_id, cid, emit):
    return None


def _token(user_id: str, *, secret: str = SECRET, exp_offset: int = 120) -> str:
    from app.auth.service_jwt import AUDIENCE, ISSUER

    now = int(time.time())
    return pyjwt.encode(
        {
            "sub": user_id,
            "username": "tester",
            "iat": now,
            "exp": now + exp_offset,
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def client(database_url):
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        service_jwt_secret=SECRET,
        rate_limit_per_minute=20,
        daily_token_budget=200_000,
    )
    model = FakeToolModel(script=["Olá! Como posso ajudar?"])
    runtime = Runtime(
        FakeRouter(default=Route(intent="greeting", confidence=0.99)),
        None,
        lambda r: model,
        _no_ctx,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_runtime] = lambda: runtime
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _body(text="oi", chat_id="chat-1"):
    return {
        "id": chat_id,
        "trigger": "submit-message",
        "messages": [{"id": "m1", "role": "user", "parts": [{"type": "text", "text": text}]}],
    }


def test_request_without_a_token_is_401(client):
    response = client.post("/api/chat", json=_body())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_request_with_a_bad_token_is_401(client):
    response = client.post("/api/chat", json=_body(), headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_a_token_signed_with_the_wrong_secret_is_401_not_500(client):
    """The frontend BFF and the backend must share SERVICE_JWT_SECRET exactly; a mismatch (typo,
    stale env var after rotation) must be a clean 401, never a 500 or a silent accept."""
    token = _token(str(uuid.uuid4()), secret="a-completely-different-secret-value-32b")
    response = client.post("/api/chat", json=_body(), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_valid_token_reaches_the_agent(client):
    token = _token(str(uuid.uuid4()))
    response = client.post("/api/chat", json=_body(), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_21st_request_in_a_minute_is_rate_limited(client, frozen_time, database_url):
    user_id = str(uuid.uuid4())
    token = _token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(20):
        response = client.post("/api/chat", json=_body(chat_id=f"chat-{i}"), headers=headers)
        assert response.status_code == 200

    response = client.post("/api/chat", json=_body(chat_id="chat-21"), headers=headers)
    assert response.status_code == 429
    # Exactly the #4 contract shape (fixture http-429-rate-limited.json), not just the status code.
    fixture = json.loads((FIXTURES / "http-429-rate-limited.json").read_text())
    body = response.json()
    assert body["error"]["code"] == fixture["body"]["error"]["code"]
    assert set(body["error"]) == set(fixture["body"]["error"])
    assert body["error"]["retryAfterSeconds"] == 60  # frozen at the top of the minute
    assert response.headers["Retry-After"] == "60"

    # The refused 21st request is rejected before the agent (and record_usage) ever runs.
    import asyncio

    from app.db import connect

    async def _usage() -> int:
        async with await connect(database_url) as conn:
            return await enforce.get_daily_usage(
                conn, user_id, enforce.current_local_date("America/Campo_Grande", frozen_time)
            )

    assert asyncio.run(_usage()) == 0


def test_budget_exhausted_is_429(client, database_url):
    import asyncio

    from app.db import connect

    user_id = str(uuid.uuid4())
    token = _token(user_id)

    async def _exhaust():
        async with await connect(database_url) as conn:
            await enforce.record_usage(conn, user_id, 200_000, 0, "America/Campo_Grande")

    asyncio.run(_exhaust())

    response = client.post("/api/chat", json=_body(), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 429
    fixture = json.loads((FIXTURES / "http-429-budget-exhausted.json").read_text())
    body = response.json()
    assert body["error"]["code"] == fixture["body"]["error"]["code"]
    assert set(body["error"]) == set(fixture["body"]["error"])
    assert body["error"]["retryAfterSeconds"] >= 1
    assert "Retry-After" in response.headers


def test_two_accounts_are_independent(client):
    token_a = _token(str(uuid.uuid4()))
    token_b = _token(str(uuid.uuid4()))
    for i in range(20):
        resp = client.post(
            "/api/chat",
            json=_body(chat_id=f"a-{i}"),
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 200
    refused = client.post(
        "/api/chat", json=_body(chat_id="a-21"), headers={"Authorization": f"Bearer {token_a}"}
    )
    assert refused.status_code == 429

    still_ok = client.post(
        "/api/chat", json=_body(chat_id="b-1"), headers={"Authorization": f"Bearer {token_b}"}
    )
    assert still_ok.status_code == 200
