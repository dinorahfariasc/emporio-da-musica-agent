import pytest

from app.config import Settings
from evals.runner import load_scenarios, run_scenario

SCENARIOS = [s for s in load_scenarios() if not s.get("live_only")]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario_in_fake_mode(scenario, seeded_db):
    settings = Settings(_env_file=None, database_url=seeded_db)

    assert run_scenario(scenario, settings) == []
