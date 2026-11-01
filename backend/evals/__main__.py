"""`uv run python -m evals [--live] [--only ID]`: runs the YAML scenarios."""

import argparse
import sys
from urllib.parse import urlsplit

import psycopg

from app.config import Settings
from evals.runner import load_scenarios, run_scenario

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _reset_lockouts(settings: Settings) -> None:
    """Lockouts are global per order; a local run starts clean (never on a remote database)."""
    if not settings.database_url or urlsplit(settings.database_url).hostname not in LOCAL_HOSTS:
        return
    with psycopg.connect(settings.database_url) as conn:
        conn.execute("DELETE FROM order_verification_failures")
        conn.execute("DELETE FROM conversation_state WHERE conversation_id LIKE 'eval-%'")
        conn.execute("DELETE FROM service_requests WHERE conversation_id LIKE 'eval-%'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals")
    parser.add_argument("--live", action="store_true", help="real models (needs API keys)")
    parser.add_argument("--only", help="run one scenario id")
    args = parser.parse_args(argv)
    settings = Settings()
    failed = 0
    for scenario in load_scenarios():
        if args.only and scenario["id"] != args.only:
            continue
        if scenario.get("live_only") and not args.live:
            print(f"SKIP  {scenario['id']} (live only)")
            continue
        if scenario.get("fake_only") and args.live:
            print(f"SKIP  {scenario['id']} (fake only: scripted clock)")
            continue
        _reset_lockouts(settings)
        failures = run_scenario(scenario, settings, live=args.live)
        print(f"{'FAIL' if failures else 'PASS'}  {scenario['id']}")
        for failure in failures:
            print(f"      {failure}")
        failed += bool(failures)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
