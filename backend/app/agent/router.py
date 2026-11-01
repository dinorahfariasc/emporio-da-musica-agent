"""Intent router: Jev first, Haiku structured output as fallback (research R3). Plain Python."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Literal, Protocol, get_args

import httpx
from pydantic import BaseModel, Field

from app.config import RouterProvider, Settings

logger = logging.getLogger(__name__)

Intent = Literal[
    "product_search",
    "product_details",
    "promotions",
    "payment_options",
    "order_status",
    "policy_question",
    "store_info",
    "service_request",
    "greeting",
    "out_of_scope",
    "multi_intent",
    "unclear",
]
INTENTS: tuple[str, ...] = get_args(Intent)

# Intents answered by a specialist (greeting/out_of_scope: specialist model, no tools).
NO_SPECIALIST: frozenset[str] = frozenset({"multi_intent", "unclear"})

INTENT_CRITERIA: dict[str, str] = {
    "product_search": "looking for or comparing instruments to buy, or asking for recommendations",
    "product_details": "asking about one specific product: specs, price, stock, similar ones",
    "promotions": "asking about discounts or promotions currently running",
    "payment_options": "asking how to pay, PIX discount or installments",
    "order_status": "asking where an order is, its status or tracking code",
    "policy_question": "asking about returns, exchanges, warranty, shipping or other store rules",
    "store_info": "asking about opening hours, address, phone or contact",
    "service_request": "wants to return, exchange, complain or talk to a human",
    "greeting": "a greeting or thanks with no request",
    "out_of_scope": "unrelated to the music store",
    "multi_intent": "asks for two or more different things in one message",
    "unclear": "too vague to tell",
}


class Route(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0, le=1)
    router: Literal["jev", "haiku", "fake"] = "fake"
    path: Literal["specialist", "general"] = "general"
    model: str = ""


UNCLEAR = Route(intent="unclear", confidence=0.0)


@dataclass
class RouterUsage:
    """Tokens spent routing; logged separately, never added to the answer's usage."""

    input_tokens: int = 0
    output_tokens: int = 0


class Router(Protocol):
    name: Literal["jev", "haiku", "fake"]

    async def classify(self, text: str, context: str = "") -> Route: ...


class FakeRouter:
    name = "fake"

    def __init__(self, route_by_text: dict[str, Route] | None = None, default: Route | None = None):
        self._by_text = route_by_text or {}
        self._default = default or UNCLEAR

    async def classify(self, text: str, context: str = "") -> Route:
        route = self._by_text.get(text, self._default)
        return route.model_copy(update={"router": "fake"})


class JevRouter:
    """TypeSafe AI `systemone` classifier. One attempt: a failure goes straight to the fallback."""

    name = "jev"
    URL = "https://api.typesafe.ai/v1/systemone"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_s: float = 2.5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout_s
        self._transport = transport

    async def classify(self, text: str, context: str = "") -> Route:
        state = f"{context}\n{text}".strip()
        body = {
            "model": "jev-latest",
            "state": state,
            "questions": {
                "intent": {
                    "type": "choice",
                    "criteria": "\n".join(f"- {k}: {v}" for k, v in INTENT_CRITERIA.items()),
                    "choices": list(INTENTS),
                }
            },
        }
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(
                self.URL, json=body, headers={"Authorization": f"Bearer {self._api_key}"}
            )
        response.raise_for_status()
        answer = response.json()["answers"]["intent"]
        intent = answer["choice"]
        if intent not in INTENTS:
            return UNCLEAR.model_copy(update={"router": "jev"})
        return Route(intent=intent, confidence=float(answer["confidence"]), router="jev")


class HaikuRouter:
    name = "haiku"

    def __init__(self, settings: Settings, usage: RouterUsage | None = None) -> None:
        self._settings = settings
        self.usage = usage or RouterUsage()

    async def classify(self, text: str, context: str = "") -> Route:
        from langchain_anthropic import ChatAnthropic

        model = ChatAnthropic(
            model=self._settings.specialist_model,
            temperature=0,
            max_tokens=200,
            max_retries=0,
            default_request_timeout=self._settings.router_timeout_ms / 1000,
        ).with_structured_output(Route, include_raw=True)
        criteria = "\n".join(f"- {k}: {v}" for k, v in INTENT_CRITERIA.items())
        result = await model.ainvoke(
            [
                (
                    "system",
                    "Classify the customer's latest message of a music store chat into one "
                    f"intent, with a confidence from 0 to 1.\n{criteria}",
                ),
                ("human", f"{context}\n{text}".strip()),
            ]
        )
        raw = result.get("raw")
        usage = getattr(raw, "usage_metadata", None) or {}
        self.usage.input_tokens += usage.get("input_tokens", 0)
        self.usage.output_tokens += usage.get("output_tokens", 0)
        parsed = result.get("parsed")
        if not isinstance(parsed, Route):
            return UNCLEAR.model_copy(update={"router": "haiku"})
        return parsed.model_copy(update={"router": "haiku"})


def build_routers(settings: Settings) -> tuple[Router, Router | None]:
    """(primary, fallback) for the configured provider."""
    match settings.router_provider:
        case RouterProvider.FAKE:
            return FakeRouter(), None
        case RouterProvider.HAIKU:
            return HaikuRouter(settings), None
        case RouterProvider.JEV:
            primary: Router = JevRouter(
                settings.typesafe_api_key or "", timeout_s=settings.router_timeout_ms / 1000
            )
            return primary, HaikuRouter(settings)


async def route(
    text: str,
    context: str,
    settings: Settings,
    *,
    primary: Router,
    fallback: Router | None = None,
) -> Route:
    """Primary, then fallback, inside ONE budget. On expiry the turn takes the general path."""
    try:
        async with asyncio.timeout(settings.router_timeout_ms / 1000):
            try:
                result = await primary.classify(text, context)
            except Exception as exc:  # noqa: BLE001 - any primary failure falls back (FR-004)
                logger.warning("router %s failed (%s)", primary.name, type(exc).__name__)
                if fallback is None:
                    return UNCLEAR
                result = await fallback.classify(text, context)
    except Exception as exc:  # noqa: BLE001 - budget expiry or fallback failure
        logger.warning("router unavailable (%s); using the general path", type(exc).__name__)
        return UNCLEAR
    return result


def choose_path(result: Route, settings: Settings) -> Literal["specialist", "general"]:
    if result.intent in NO_SPECIALIST or result.confidence < settings.router_confidence_threshold:
        return "general"
    return "specialist"
