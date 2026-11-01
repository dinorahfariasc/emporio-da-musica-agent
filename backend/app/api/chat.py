"""POST /api/chat: validates, routes, runs the agent and streams the AI SDK chunks.

Contract: specs/002-agent-core/contracts/chat-endpoint.md. LangChain/LangGraph are imported
lazily so /api/health cold starts stay fast.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import aclosing
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from app.agent.logging import mask_pii
from app.agent.prompts import error_message
from app.agent.state import CONVERSATION_ID
from app.auth.dependency import require_service_account
from app.auth.service_jwt import AccountClaims
from app.chat import protocol as p
from app.config import Settings, get_settings
from app.limits import enforce as limits

logger = logging.getLogger("app.turn")
router = APIRouter()

EMPTY_REPLY = {
    "pt": "Oi! Sou a Melody, da Empório da Música. Como posso ajudar você hoje?",
    "en": "Hi! I'm Melody from Empório da Música. How can I help you today?",
}
_ENGLISH_HINTS = {"the", "is", "are", "what", "how", "do", "can", "you", "hello", "hi", "my"}


@dataclass
class Runtime:
    """Everything the turn needs from the outside; tests replace it."""

    primary: Any
    fallback: Any
    model_factory: Callable[[str], Any] | None
    make_ctx: Callable[[Settings, str, str, Callable[[dict], None]], Any]


async def _default_ctx(
    settings: Settings, user_id: str, conversation_id: str, emit: Callable[[dict], None]
):
    from app.db import get_pool
    from app.embeddings import get_embedder
    from app.tools.context import ToolContext

    return ToolContext(
        pool=await get_pool(settings),
        embedder=get_embedder(settings, purpose="query"),
        conversation_id=conversation_id,
        user_id=user_id,
        emit=emit,
    )


def get_runtime(settings: Annotated[Settings, Depends(get_settings)]) -> Runtime:
    from app.agent.router import build_routers

    primary, fallback = build_routers(settings)
    return Runtime(primary, fallback, None, _default_ctx)


def _language(text: str) -> str:
    words = {w.strip(".,!?¿¡").lower() for w in text.split()}
    return "en" if len(words & _ENGLISH_HINTS) >= 2 else "pt"


def _text(message: p.UIMessage) -> str:
    return "".join(part.text for part in message.parts if isinstance(part, p.TextUIPart))


def prepare_history(request: p.ChatRequest, settings: Settings) -> list[tuple[str, str]]:
    """(role, text) pairs: regenerate drops the trailing answer, history is trimmed, the latest
    user text is truncated."""
    messages = list(request.messages)
    if request.trigger == "regenerate-message" and messages and messages[-1].role == "assistant":
        messages.pop()
    pairs = [
        ("human" if m.role == "user" else "ai", _text(m))
        for m in messages
        if m.role in ("user", "assistant") and _text(m).strip()
    ][-settings.history_max_messages :]
    merged: list[tuple[str, str]] = []
    for role, text in ((r, t[: settings.input_max_chars]) for r, t in pairs):
        if merged and merged[-1][0] == role:
            merged[-1] = (role, f"{merged[-1][1]}\n{text}")
        elif merged or role == "human":  # a window never starts with the assistant
            merged.append((role, text))
    return [(role, text[: settings.input_max_chars]) for role, text in merged]


def _latest_user_text(request: p.ChatRequest, settings: Settings) -> str:
    users = [m for m in request.messages if m.role == "user"]
    return _text(users[-1])[: settings.input_max_chars] if users else ""


async def _canned(text: str) -> AsyncIterator[str]:
    text_id = f"txt_{uuid.uuid4().hex}"
    route = p.Route(intent="greeting", confidence=1.0, router="fake")
    for chunk in (
        p.Start(message_id=f"msg_{uuid.uuid4().hex}"),
        p.StartStep(),
        p.TextStart(id=text_id),
        p.TextDelta(id=text_id, delta=text),
        p.TextEnd(id=text_id),
        p.FinishStep(),
        p.MessageMetadataChunk(
            message_metadata=p.MessageMetadata(
                route=route, model="none", usage=p.Usage(input_tokens=0, output_tokens=0)
            )
        ),
        p.Finish(finish_reason="stop"),
    ):
        yield p.encode(chunk)
    yield p.DONE


def _invalid(message: str) -> JSONResponse:
    body = p.ErrorResponse(error=p.ErrorBody(code="invalid_request", message=message))
    return JSONResponse(
        body.model_dump(mode="json", by_alias=True, exclude_none=True), status_code=400
    )


def _limited(code: str, message: str, retry_after_seconds: int) -> JSONResponse:
    # contracts/rate-limit-and-budget.md: rate_limited/budget_exhausted, both 429.
    body = p.ErrorResponse(
        error=p.ErrorBody(code=code, message=message, retry_after_seconds=retry_after_seconds)
    )
    return JSONResponse(
        body.model_dump(mode="json", by_alias=True, exclude_none=True),
        status_code=429,
        headers={"Retry-After": str(retry_after_seconds)},
    )


RATE_LIMITED_MESSAGE = "Muitas mensagens em pouco tempo. Aguarde alguns segundos e tente de novo."
BUDGET_EXHAUSTED_MESSAGE = "Você atingiu o limite diário de uso. Volta a funcionar à meia-noite."


async def _check_limits(settings: Settings, account: AccountClaims) -> JSONResponse | None:
    """Rate limit first (cheaper, catches the common runaway-client case), then budget."""
    from app.db import get_pool

    pool = await get_pool(settings)
    async with pool.connection() as conn:
        rate = await limits.check_rate_limit(conn, account.user_id, settings.rate_limit_per_minute)
        if not rate.allowed:
            return _limited("rate_limited", RATE_LIMITED_MESSAGE, rate.retry_after_seconds or 1)
        budget = await limits.check_budget(
            conn, account.user_id, settings.daily_token_budget, settings.budget_timezone
        )
        if not budget.allowed:
            return _limited(
                "budget_exhausted", BUDGET_EXHAUSTED_MESSAGE, budget.retry_after_seconds or 1
            )
    return None


@router.post("/api/chat")
async def chat(
    payload: dict,
    settings: Annotated[Settings, Depends(get_settings)],
    runtime: Annotated[Runtime, Depends(get_runtime)],
    account: Annotated[AccountClaims, Depends(require_service_account)],
):
    try:
        request = p.ChatRequest.model_validate(payload)
    except ValidationError:
        return _invalid("Invalid chat request.")
    if not CONVERSATION_ID.fullmatch(request.id):
        return _invalid("Invalid chat request.")
    limited = await _check_limits(settings, account)
    if limited is not None:
        return limited
    text = _latest_user_text(request, settings)
    lang = _language(text)
    if not text.strip():
        return StreamingResponse(
            _canned(EMPTY_REPLY[lang]), media_type="text/event-stream", headers=p.STREAM_HEADERS
        )
    return StreamingResponse(
        _turn(request, text, lang, settings, runtime, account),
        media_type="text/event-stream",
        headers=p.STREAM_HEADERS,
    )


async def _turn(
    request: p.ChatRequest,
    text: str,
    lang: str,
    settings: Settings,
    runtime: Runtime,
    account: AccountClaims,
) -> AsyncIterator[str]:
    from app.agent.agent import build_agent
    from app.agent.router import route as classify
    from app.agent.stream import to_ui_stream

    started = time.monotonic()
    log: dict[str, Any] = {
        "conversation_id": hashlib.sha256(request.id.encode()).hexdigest()[:16],
        "tools": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "first_token_ms": None,
        "error_code": None,
    }
    history = prepare_history(request, settings)
    context = next((t for r, t in reversed(history[:-1]) if r == "ai"), "")[:300]
    try:
        async with asyncio.timeout(settings.turn_timeout_s):
            routed = await classify(
                text, context, settings, primary=runtime.primary, fallback=runtime.fallback
            )

            def emit(event: dict) -> None:
                from langgraph.config import get_stream_writer

                get_stream_writer()(event)

            ctx = await runtime.make_ctx(settings, account.user_id, request.id, emit)
            agent, routed = build_agent(settings, ctx, routed, model_factory=runtime.model_factory)
            log.update(
                intent=routed.intent,
                confidence=routed.confidence,
                router=routed.router,
                path=routed.path,
                model=routed.model,
            )
            events = agent.astream(
                {"messages": history},
                stream_mode=["messages", "updates", "custom"],
                config={"recursion_limit": 2 * settings.agent_max_steps + 2},
            )
            async with (
                aclosing(events) as events_,
                aclosing(
                    to_ui_stream(
                        events_,
                        route=p.Route(
                            intent=routed.intent,
                            confidence=routed.confidence,
                            router=routed.router,
                        ),
                        model_name=routed.model,
                        lang=lang,
                    )
                ) as lines,
            ):
                async for line in lines:
                    _observe(line, log, started)
                    yield line
    except TimeoutError:
        log["error_code"] = "timeout"
        yield p.encode(p.Error(error_text=error_message("timeout", lang)))
        yield p.DONE
    except Exception as exc:  # noqa: BLE001 - setup failures also end as a catalog error
        log["error_code"] = "internal"
        logger.warning("turn setup failed (%s)", type(exc).__name__)
        yield p.encode(p.Error(error_text=error_message("internal", lang)))
        yield p.DONE
    finally:
        # Also runs on client disconnect (GeneratorExit from the ASGI server closing the stream);
        # logs and records whatever usage the provider already reports, even for a partial/dropped
        # stream (contracts/rate-limit-and-budget.md: "After the turn finishes"). Recording usage
        # is fired as a detached task (QA review #44): it must not be torn down along with the
        # response generator it is cleaning up after, and a failure to record it must never mask
        # whatever the turn itself raised or block the stream from closing.
        log["latency_ms"] = int((time.monotonic() - started) * 1000)
        logger.info(mask_pii(json.dumps(log, ensure_ascii=False)))
        if log["input_tokens"] or log["output_tokens"]:
            asyncio.create_task(
                _record_usage_safely(
                    settings, account.user_id, log["input_tokens"], log["output_tokens"]
                )
            )


async def _record_usage_safely(
    settings: Settings, user_id: str, input_tokens: int, output_tokens: int
) -> None:
    try:
        from app.db import get_pool

        pool = await get_pool(settings)
        async with pool.connection() as conn:
            await limits.record_usage(
                conn, user_id, input_tokens, output_tokens, settings.budget_timezone
            )
    except Exception:  # noqa: BLE001 - never let a usage-recording failure surface anywhere else
        logger.warning("failed to record usage for a finished turn", exc_info=True)


def _observe(line: str, log: dict[str, Any], started: float) -> None:
    if not line.startswith("data: {"):
        return
    event = json.loads(line.removeprefix("data: "))
    match event["type"]:
        case "tool-input-available":
            log["tools"].append(event["toolName"])
        case "text-delta" if log["first_token_ms"] is None:
            log["first_token_ms"] = int((time.monotonic() - started) * 1000)
        case "message-metadata":
            usage = event["messageMetadata"]["usage"]
            log["input_tokens"], log["output_tokens"] = usage["inputTokens"], usage["outputTokens"]
        case "error":
            log["error_code"] = "stream_error"
