import asyncio
import json

import httpx

from app.agent.router import (
    FakeRouter,
    JevRouter,
    Route,
    build_routers,
    choose_path,
    route,
)
from app.config import RouterProvider, Settings

SETTINGS = Settings(_env_file=None, router_timeout_ms=200)


def _jev(handler) -> JevRouter:
    return JevRouter("k", transport=httpx.MockTransport(handler))


def _ok(intent="order_status", confidence=0.93):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer k"
        return httpx.Response(
            200, json={"answers": {"intent": {"choice": intent, "confidence": confidence}}}
        )

    return handler


class Slow:
    name = "haiku"

    async def classify(self, text, context=""):
        await asyncio.sleep(5)


class Broken:
    name = "jev"

    async def classify(self, text, context=""):
        raise RuntimeError("boom")


async def test_jev_success():
    result = await route("cadê meu pedido 4?", "", SETTINGS, primary=_jev(_ok()))
    assert (result.intent, result.router) == ("order_status", "jev")
    assert result.confidence == 0.93


async def test_jev_sends_the_message_and_every_intent():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return _ok()(request)

    await _jev(handler).classify("oi")
    assert "oi" in seen["state"]
    assert len(seen["questions"]["intent"]["criteria"]) == 12


async def test_jev_error_falls_back_to_the_second_router():
    fallback = FakeRouter(default=Route(intent="policy_question", confidence=0.9))
    result = await route(
        "x", "", SETTINGS, primary=_jev(lambda r: httpx.Response(500)), fallback=fallback
    )
    assert result.intent == "policy_question"


async def test_slow_primary_and_slow_fallback_end_inside_the_budget():
    started = asyncio.get_running_loop().time()
    result = await route("x", "", SETTINGS, primary=Slow(), fallback=Slow())
    assert result.intent == "unclear" and result.confidence == 0
    assert asyncio.get_running_loop().time() - started < 1


async def test_everything_failing_is_unclear_not_an_error():
    result = await route("x", "", SETTINGS, primary=Broken(), fallback=Broken())
    assert result.intent == "unclear"


async def test_unknown_label_is_unclear():
    result = await route("x", "", SETTINGS, primary=_jev(_ok(intent="banana")))
    assert result.intent == "unclear"


def test_multi_intent_goes_to_general_even_when_confident():
    assert choose_path(Route(intent="multi_intent", confidence=0.99), SETTINGS) == "general"


def test_low_confidence_goes_to_general():
    assert choose_path(Route(intent="order_status", confidence=0.5), SETTINGS) == "general"


def test_confident_single_intent_goes_to_specialist():
    assert choose_path(Route(intent="order_status", confidence=0.9), SETTINGS) == "specialist"
    assert choose_path(Route(intent="greeting", confidence=0.9), SETTINGS) == "specialist"


def test_provider_selection():
    primary, fallback = build_routers(Settings(_env_file=None, router_provider=RouterProvider.JEV))
    assert (primary.name, fallback.name) == ("jev", "haiku")
    primary, fallback = build_routers(Settings(_env_file=None))
    assert (primary.name, fallback) == ("fake", None)


def test_build_routers_openrouter_has_no_fallback():
    settings = Settings(_env_file=None, router_provider=RouterProvider.OPENROUTER)
    primary, fallback = build_routers(settings)
    assert (primary.name, fallback) == ("openrouter", None)


class Fast:
    name = "haiku"

    async def classify(self, text, context=""):
        from app.agent.router import Route

        return Route(intent="store_info", confidence=0.9, router="haiku")


async def test_hung_primary_still_leaves_time_for_the_fallback():
    result = await route("x", "", SETTINGS, primary=Slow(), fallback=Fast())
    assert (result.intent, result.router) == ("store_info", "haiku")
