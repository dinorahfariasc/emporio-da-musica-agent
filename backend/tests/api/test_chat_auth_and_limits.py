"""End-to-end POST /api/chat coverage for auth and limits (contracts/service-jwt.md,
contracts/rate-limit-and-budget.md). Uses the real require_service_account dependency (a minted
JWT, not an override) so the whole chain is exercised, with a fake router/model underneath.
"""

import time
import uuid

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from app.agent.fakes import FakeToolModel
from app.agent.router import FakeRouter, Route
from app.api.chat import Runtime, get_runtime
from app.config import Settings, get_settings
from app.main import app

SECRET = "test-secret-at-least-32-bytes-long!!"


async def _no_ctx(settings, user_id, cid, emit):
    return None


def _token(user_id: str, *, secret: str = SECRET, exp_offset: int = 120) -> str:
    now = int(time.time())
    return pyjwt.encode(
        {"sub": user_id, "username": "tester", "iat": now, "exp": now + exp_offset},
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


def test_valid_token_reaches_the_agent(client):
    token = _token(str(uuid.uuid4()))
    response = client.post("/api/chat", json=_body(), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_21st_request_in_a_minute_is_rate_limited(client):
    user_id = str(uuid.uuid4())
    token = _token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(20):
        response = client.post("/api/chat", json=_body(chat_id=f"chat-{i}"), headers=headers)
        assert response.status_code == 200

    response = client.post("/api/chat", json=_body(chat_id="chat-21"), headers=headers)
    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["retryAfterSeconds"] >= 1
    assert "Retry-After" in response.headers


def test_budget_exhausted_is_429(client, database_url):
    import asyncio

    from app.db import connect
    from app.limits import enforce

    user_id = str(uuid.uuid4())
    token = _token(user_id)

    async def _exhaust():
        async with await connect(database_url) as conn:
            await enforce.record_usage(conn, user_id, 200_000, 0, "America/Campo_Grande")

    asyncio.run(_exhaust())

    response = client.post("/api/chat", json=_body(), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "budget_exhausted"


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
