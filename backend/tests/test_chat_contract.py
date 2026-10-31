"""The backend's stream encoder must reproduce the shared contract fixtures byte for byte."""

import json
from pathlib import Path

import pytest

from app.chat.protocol import DONE, ChatRequest, ErrorResponse, chunk_adapter, encode

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "chat-stream" / "fixtures"
SSE_FIXTURES = sorted(FIXTURES.glob("*.sse"))
HTTP_FIXTURES = sorted(FIXTURES.glob("http-*.json"))


def _events(text: str) -> list[str]:
    return [f"{block}\n\n" for block in text.split("\n\n") if block]


def test_fixture_set_is_complete():
    assert [p.name for p in SSE_FIXTURES] == [
        "plain-text.sse",
        "stream-error.sse",
        "tool-error.sse",
        "tool-products.sse",
    ]


@pytest.mark.parametrize("fixture", SSE_FIXTURES, ids=lambda p: p.name)
def test_encoder_round_trips_fixture(fixture: Path):
    events = _events(fixture.read_text(encoding="utf-8"))
    assert events[-1] == DONE

    for event in events[:-1]:
        payload = event.removeprefix("data: ").removesuffix("\n\n")
        chunk = chunk_adapter.validate_json(payload)
        assert encode(chunk) == event


@pytest.mark.parametrize("fixture", HTTP_FIXTURES, ids=lambda p: p.name)
def test_http_error_fixtures_match_error_schema(fixture: Path):
    spec = json.loads(fixture.read_text(encoding="utf-8"))
    body = ErrorResponse.model_validate(spec["body"])
    if spec["status"] == 429:
        assert body.error.retry_after_seconds == int(spec["headers"]["Retry-After"])


def test_request_fixture_parses_as_chat_request():
    request = ChatRequest.model_validate_json((FIXTURES / "request-submit.json").read_text())
    assert request.trigger == "submit-message"
    assert request.messages[-1].parts[0].text.startswith("Quais violões")


def test_encode_includes_type_for_chunks_built_in_code():
    from app.chat.protocol import Finish, Start, StartStep

    assert encode(StartStep()) == 'data: {"type":"start-step"}\n\n'
    assert encode(Start(message_id="m1")) == 'data: {"type":"start","messageId":"m1"}\n\n'
    expected_finish = 'data: {"type":"finish","finishReason":"stop"}\n\n'
    assert encode(Finish(finish_reason="stop")) == expected_finish
