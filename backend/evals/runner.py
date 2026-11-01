"""Scenario runner. Fake mode scripts the router and the model, so it proves the tools, the
wiring and the stream contract (not routing or behaviour). `live_only` expectations are checked
with --live, against the real models (review H2)."""

import functools
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from app.agent.fakes import FakeToolModel
from app.agent.router import FakeRouter, Route
from app.api.chat import Runtime, _default_ctx, get_runtime
from app.chat import protocol as p
from app.config import Settings, get_settings
from app.main import app

SCENARIO_DIR = Path(__file__).parent / "scenarios"


@dataclass
class TurnResult:
    tools: list[dict] = field(default_factory=list)  # {name, input}
    outputs: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # tool-output-error codes
    text: str = ""
    route: dict = field(default_factory=dict)
    stream_error: str | None = None


@functools.cache
def _live_client() -> TestClient:
    """One client, so one event loop: provider HTTP clients are cached across requests, and a
    fresh loop per request leaves them bound to a closed one."""
    return TestClient(app).__enter__()


def load_scenarios(path: Path = SCENARIO_DIR) -> list[dict]:
    scenarios: list[dict] = []
    for file in sorted(path.glob("*.yaml")):
        scenarios.extend(yaml.safe_load(file.read_text(encoding="utf-8")))
    return scenarios


def _scripted_model(calls: list[dict]) -> FakeToolModel:
    """One AIMessage per scripted tool call, then an answer quoting only the tool outputs."""
    script: list[Any] = [
        AIMessage(
            content="",
            tool_calls=[{"name": c["name"], "args": c.get("args", {}), "id": f"call_{i}"}],
        )
        for i, c in enumerate(calls)
    ]

    def answer(messages: list) -> str:
        outputs = [str(m.content) for m in messages if isinstance(m, ToolMessage)]
        return "Resultado: " + " | ".join(outputs) if outputs else "Olá! Como posso ajudar?"

    return FakeToolModel(script=[*script, answer])


def _parse(sse: str) -> TurnResult:
    result = TurnResult()
    for block in sse.split("\n\n"):
        payload = block.removeprefix("data: ").strip()
        if not payload or payload == "[DONE]":
            continue
        chunk = p.chunk_adapter.validate_python(json.loads(payload))  # contract check
        match chunk.type:
            case "tool-input-available":
                result.tools.append({"name": chunk.tool_name, "input": chunk.input})
            case "tool-output-available":
                result.outputs.append(chunk.output)
            case "tool-output-error":
                result.errors.append(chunk.error_text)
            case "text-delta":
                result.text += chunk.delta
            case "message-metadata":
                result.route = chunk.message_metadata.route.model_dump()
            case "error":
                result.stream_error = chunk.error_text
    return result


def _check_turn(turn: dict, result: TurnResult, *, live: bool) -> list[str]:
    expect = turn.get("expect", {})
    failures: list[str] = []
    dumped = json.dumps(result.outputs, ensure_ascii=False, default=str, separators=(",", ":"))
    if result.stream_error:
        failures.append(f"stream error: {result.stream_error}")
    if "intent" in expect and not live and result.route.get("intent") != expect["intent"]:
        failures.append(f"intent {result.route.get('intent')} != {expect['intent']}")
    called = [t["name"] for t in result.tools]
    for name in expect.get("tools", []):
        if name not in called:
            failures.append(f"tool {name} not called (called: {called})")
    for name in expect.get("tools_not_called", []):
        if name in called:
            failures.append(f"tool {name} was called")
    for code in expect.get("errors", []):
        if code not in result.errors:
            failures.append(f"error code {code} missing (got {result.errors})")
    # Facts are checked on tool outputs (raw JSON, pre-formatting) and, with --live, also on the
    # answer text: the model must have called the right tools, and may quote them formatted.
    haystack = f"{dumped}\n{result.text}" if live else dumped
    for fact in expect.get("required_facts", []):
        if str(fact) not in haystack:
            failures.append(f"required fact {fact!r} missing")
    for fact in expect.get("forbidden_facts", []):
        if str(fact) in haystack:
            failures.append(f"forbidden fact {fact!r} present")
    if live:
        for fact in expect.get("answer_contains", []):
            if str(fact).casefold() not in result.text.casefold():
                failures.append(f"answer lacks {fact!r}")
        for fact in expect.get("answer_excludes", []):
            if str(fact).casefold() in result.text.casefold():
                failures.append(f"answer contains {fact!r}")
    return failures


def run_scenario(scenario: dict, settings: Settings, *, live: bool = False) -> list[str]:
    """Runs every turn of a scenario through POST /api/chat; returns the failures."""
    if scenario.get("live_only") and not live:
        return []
    conversation = f"eval-{uuid.uuid4().hex[:12]}"
    history: list[dict] = []
    failures: list[str] = []
    client = _live_client() if live else TestClient(app)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        for index, turn in enumerate(scenario["turns"]):
            if not live:
                route = Route(intent=turn["intent"], confidence=0.95)
                model = _scripted_model(turn.get("calls", []))
                runtime = Runtime(
                    FakeRouter(default=route), None, lambda role, m=model: m, _default_ctx
                )
                app.dependency_overrides[get_runtime] = lambda r=runtime: r
            history.append(
                {
                    "id": f"u{index}",
                    "role": "user",
                    "parts": [{"type": "text", "text": turn["say"]}],
                }
            )
            body = {"id": conversation, "trigger": "submit-message", "messages": history}
            result = _parse(client.post("/api/chat", json=body).text)
            failures += [f"turn {index + 1}: {f}" for f in _check_turn(turn, result, live=live)]
            history.append(
                {
                    "id": f"a{index}",
                    "role": "assistant",
                    "parts": [{"type": "text", "text": result.text}],
                }
            )
    finally:
        app.dependency_overrides.clear()
    return failures
