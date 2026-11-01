"""LangGraph events -> AI SDK UI message stream chunks (research R2; contract in
docs/contracts/chat-stream.md). The error text is always a catalog message, never an exception."""

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.agent.prompts import error_message
from app.chat import protocol as p

logger = logging.getLogger(__name__)


def _output(content: Any) -> Any:
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return content
    return content


def _classify(exc: BaseException) -> str:
    from langgraph.errors import GraphRecursionError

    if isinstance(exc, GraphRecursionError):
        return "too_many_steps"
    if isinstance(exc, TimeoutError):
        return "timeout"
    return "internal"


async def to_ui_stream(
    events: AsyncIterator[tuple[str, Any]],
    *,
    route: p.Route,
    model_name: str,
    lang: str = "pt",
) -> AsyncIterator[str]:
    """`events` is `agent.astream(..., stream_mode=["messages", "updates", "custom"])`."""
    yield p.encode(p.Start(message_id=f"msg_{uuid.uuid4().hex}"))
    usage_in = usage_out = 0
    step_open = False
    text_id: str | None = None
    pending_tools: set[str] = set()
    buffered_cards: list[p.DataProducts] = []

    try:
        async for mode, data in events:
            if mode == "custom":
                if isinstance(data, dict) and data.get("type") == "data-products":
                    buffered_cards.append(p.DataProducts.model_validate(data))
                continue

            if mode == "updates":
                update = data.get("model") if isinstance(data, dict) else None
                if not update:
                    continue
                for message in update["messages"]:
                    meta = getattr(message, "usage_metadata", None) or {}
                    usage_in += meta.get("input_tokens", 0)
                    usage_out += meta.get("output_tokens", 0)
                    if message.tool_calls:
                        if text_id:  # text before a tool call: close that step first
                            yield p.encode(p.TextEnd(id=text_id))
                            text_id = None
                        if step_open:
                            yield p.encode(p.FinishStep())
                        yield p.encode(p.StartStep())
                        step_open = True
                        for call in message.tool_calls:
                            pending_tools.add(call["id"])
                            yield p.encode(
                                p.ToolInputAvailable(
                                    tool_call_id=call["id"],
                                    tool_name=call["name"],
                                    input=call["args"],
                                )
                            )
                    elif text_id:
                        yield p.encode(p.TextEnd(id=text_id))
                        yield p.encode(p.FinishStep())
                        text_id, step_open = None, False
                continue

            message, meta = data  # mode == "messages"
            kind = type(message).__name__
            if kind == "ToolMessage":
                call_id = message.tool_call_id
                if message.status == "error":
                    yield p.encode(
                        p.ToolOutputError(tool_call_id=call_id, error_text=str(message.content))
                    )
                else:
                    yield p.encode(
                        p.ToolOutputAvailable(tool_call_id=call_id, output=_output(message.content))
                    )
                pending_tools.discard(call_id)
                if not pending_tools:
                    for card in buffered_cards:
                        yield p.encode(card)
                    buffered_cards.clear()
                    if step_open:
                        yield p.encode(p.FinishStep())
                        step_open = False
            elif kind == "AIMessageChunk" and meta.get("langgraph_node") == "model":
                text = message.text
                if not text:
                    continue
                if text_id is None:
                    if not step_open:
                        yield p.encode(p.StartStep())
                        step_open = True
                    text_id = message.id or f"txt_{uuid.uuid4().hex}"
                    yield p.encode(p.TextStart(id=text_id))
                yield p.encode(p.TextDelta(id=text_id, delta=text))
    except Exception as exc:  # noqa: BLE001 - every failure ends as one catalog error chunk
        kind = _classify(exc)
        logger.warning(
            "turn failed: %s (%s)",
            kind,
            type(exc).__name__,
            exc_info=logger.isEnabledFor(logging.DEBUG),  # full trace only when debugging
        )
        yield p.encode(p.Error(error_text=error_message(kind, lang)))
        yield p.DONE
        return

    if text_id:
        yield p.encode(p.TextEnd(id=text_id))
    if step_open:
        yield p.encode(p.FinishStep())
    yield p.encode(
        p.MessageMetadataChunk(
            message_metadata=p.MessageMetadata(
                route=route,
                model=model_name,
                usage=p.Usage(input_tokens=usage_in, output_tokens=usage_out),
            )
        )
    )
    yield p.encode(p.Finish(finish_reason="stop"))
    yield p.DONE
