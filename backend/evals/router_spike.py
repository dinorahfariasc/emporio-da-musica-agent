"""Router spike (research R3): `uv run python -m evals.router_spike` with real keys.

Runs every scenario message through Jev and Haiku and prints accuracy against the scenario's
intent, p50/p95 latency and a confidence histogram, to pick ROUTER_CONFIDENCE_THRESHOLD.
"""

import asyncio
import statistics
import time
from collections import Counter

from app.agent.router import HaikuRouter, JevRouter, Router
from app.config import Settings
from evals.runner import load_scenarios


def _messages() -> list[tuple[str, str]]:
    return [
        (turn["say"], turn["intent"])
        for scenario in load_scenarios()
        for turn in scenario["turns"]
        if "intent" in turn
    ]


async def _measure(router: Router, samples: list[tuple[str, str]]) -> None:
    hits, latencies, confidences = 0, [], []
    for text, expected in samples:
        started = time.monotonic()
        try:
            route = await router.classify(text)
        except Exception as exc:  # noqa: BLE001 - the spike reports failures, it does not raise
            print(f"  error {type(exc).__name__} on {text!r}")
            continue
        latencies.append((time.monotonic() - started) * 1000)
        confidences.append(route.confidence)
        hits += route.intent == expected
    if not latencies:
        print(f"{router.name}: no successful calls")
        return
    latencies.sort()
    p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
    histogram = Counter(round(c, 1) for c in confidences)
    print(f"{router.name}: accuracy {hits}/{len(samples)}")
    print(f"  latency p50 {statistics.median(latencies):.0f} ms, p95 {p95:.0f} ms")
    print("  confidence", dict(sorted(histogram.items())))


async def main() -> None:
    settings = Settings()
    samples = _messages()
    print(f"{len(samples)} messages")
    if settings.typesafe_api_key:
        await _measure(JevRouter(settings.typesafe_api_key, timeout_s=10), samples)
    else:
        print("jev: TYPESAFE_API_KEY not set")
    if settings.anthropic_api_key:
        await _measure(HaikuRouter(settings), samples)
    else:
        print("haiku: ANTHROPIC_API_KEY not set")


if __name__ == "__main__":
    asyncio.run(main())
