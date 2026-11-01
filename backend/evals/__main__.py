"""`uv run python -m evals [--live] [--only ID]`: runs the YAML scenarios."""

import argparse
import sys

from app.config import Settings
from evals.runner import load_scenarios, run_scenario


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
        failures = run_scenario(scenario, settings, live=args.live)
        print(f"{'FAIL' if failures else 'PASS'}  {scenario['id']}")
        for failure in failures:
            print(f"      {failure}")
        failed += bool(failures)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
