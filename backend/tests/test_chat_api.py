import json
import logging
import uuid

import pytest

from app.agent.fakes import FakeToolModel
from app.agent.router import FakeRouter, Route
from app.api.chat import Runtime, get_runtime
from app.auth.dependency import require_service_account
from app.auth.service_jwt import AccountClaims
from app.chat import protocol as p
from app.config import Settings, get_settings
from app.main import app


async def _no_ctx(settings, user_id, cid, emit):
    return None


def _client(client_factory, script, *, route=None, settings=None, **overrides):
    settings = Settings(_env_file=None, **overrides)
    model = FakeToolModel(script=script)
    runtime = Runtime(
        FakeRouter(default=route or Route(intent="greeting", confidence=0.99)),
        None,
        lambda role: model,
        _no_ctx,
    )
    client = client_factory(**overrides)
    # A fresh account per client so one test's requests never trip another's rate limit/budget.
    account = AccountClaims(user_id=str(uuid.uuid4()), username="tester")
    app.dependency_overrides[get_runtime] = lambda: runtime
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[require_service_account] = lambda: account
    return client, model


def _body(text="oi", **extra):
    return {
        "id": "chat-1",
        "trigger": "submit-message",
        "messages": [{"id": "m1", "role": "user", "parts": [{"type": "text", "text": text}]}],
        **extra,
    }


def _parse(response):
    chunks = []
    for line in response.text.split("\n\n"):
        payload = line.removeprefix("data: ").strip()
        if payload and payload != "[DONE]":
            chunks.append(p.chunk_adapter.validate_python(json.loads(payload)))
    return chunks


@pytest.fixture(autouse=True)
def _reset():
    yield
    app.dependency_overrides.clear()


def test_valid_request_streams_contract_chunks(make_client):
    client, _ = _client(make_client, ["Olá! Como posso ajudar?"])

    response = client.post("/api/chat", json=_body())

    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert response.text.endswith("data: [DONE]\n\n")
    types = [c.type for c in _parse(response)]
    assert types[0] == "start" and types[-1] == "finish" and "text-delta" in types


def test_invalid_body_is_a_400_invalid_request(make_client):
    client, _ = _client(make_client, [])

    response = client.post("/api/chat", json={"id": "x"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_empty_message_gets_a_short_reply_without_the_model(make_client):
    client, model = _client(make_client, [])

    response = client.post("/api/chat", json=_body("   "))

    chunks = _parse(response)
    assert any(c.type == "text-delta" for c in chunks)
    assert model.seen == []


def test_long_input_is_truncated(make_client):
    client, model = _client(make_client, ["ok"], input_max_chars=50)

    client.post("/api/chat", json=_body("x" * 500))

    human = [m for m in model.seen[0] if m.type == "human"][-1]
    assert len(human.content) == 50


def test_history_is_trimmed_to_the_most_recent(make_client):
    client, model = _client(make_client, ["ok"], history_max_messages=3)
    messages = [
        {
            "id": f"m{i}",
            "role": "user" if i % 2 == 0 else "assistant",
            "parts": [{"type": "text", "text": f"msg {i}"}],
        }
        for i in range(8)
    ] + [{"id": "last", "role": "user", "parts": [{"type": "text", "text": "final"}]}]

    client.post("/api/chat", json={**_body(), "messages": messages})

    sent = [m.content for m in model.seen[0] if m.type in ("human", "ai")]
    assert sent == ["msg 6", "msg 7", "final"]


def test_regenerate_drops_the_trailing_assistant_message(make_client):
    client, model = _client(make_client, ["ok"])
    messages = [
        {"id": "u", "role": "user", "parts": [{"type": "text", "text": "pergunta"}]},
        {"id": "a", "role": "assistant", "parts": [{"type": "text", "text": "resposta antiga"}]},
    ]

    client.post(
        "/api/chat", json={**_body(), "messages": messages, "trigger": "regenerate-message"}
    )

    contents = [m.content for m in model.seen[0] if m.type in ("human", "ai")]
    assert "resposta antiga" not in contents and "pergunta" in contents


def test_turn_timeout_yields_exactly_one_error_chunk(make_client):
    class Slow(FakeToolModel):
        def _stream(self, *args, **kwargs):
            import time

            time.sleep(0.5)
            return super()._stream(*args, **kwargs)

    client, _ = _client(make_client, ["ok"], turn_timeout_s=0.1)
    slow = Slow(script=["ok"])
    app.dependency_overrides[get_runtime] = lambda: Runtime(
        FakeRouter(default=Route(intent="greeting", confidence=0.99)), None, lambda r: slow, _no_ctx
    )

    response = client.post("/api/chat", json=_body())

    errors = [c for c in _parse(response) if c.type == "error"]
    assert len(errors) == 1
    assert response.text.endswith("data: [DONE]\n\n")


def test_turn_log_masks_emails(make_client, caplog):
    client, _ = _client(make_client, ["ok"])

    with caplog.at_level(logging.INFO, logger="app.turn"):
        client.post("/api/chat", json=_body("meu email é ana@jmail.com"))

    logged = " ".join(r.getMessage() for r in caplog.records if r.name == "app.turn")
    assert "ana@jmail.com" not in logged and "chat-1" not in logged
    assert '"intent"' in logged


def test_conversation_id_with_odd_characters_is_a_400(make_client):
    client, _ = _client(make_client, [])
    body = _body()
    body["id"] = "a b!"
    assert client.post("/api/chat", json=body).status_code == 400


def _turns(roles_and_texts):
    return [
        {"id": f"m{i}", "role": role, "parts": [{"type": "text", "text": text}]}
        for i, (role, text) in enumerate(roles_and_texts)
    ]


def test_history_window_never_starts_with_the_assistant_and_merges_runs():
    from app.api.chat import prepare_history

    settings = Settings(_env_file=None, history_max_messages=3, input_max_chars=5)
    request = p.ChatRequest.model_validate(
        {
            "id": "c",
            "trigger": "submit-message",
            "messages": _turns(
                [("user", "u0"), ("assistant", "a0"), ("user", "u1"), ("user", "u2-long-text")]
            ),
        }
    )
    pairs = prepare_history(request, settings)
    assert pairs[0][0] == "human"
    assert [r for r, _ in pairs] == ["human"]  # [a0, u1, u2] -> leading ai dropped, runs merged
    assert all(len(t) <= 5 for _, t in pairs)
