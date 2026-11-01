import pytest

from app.config import Settings
from app.db import connect
from evals.runner import load_scenarios, run_scenario

SCENARIOS = [s for s in load_scenarios() if not s.get("live_only")]


@pytest.fixture(autouse=True)
async def _fresh_lockouts(seeded_db):
    """Order lockouts are global per order, so each scenario starts from a clean slate."""
    async with await connect(seeded_db) as conn:
        await conn.execute("DELETE FROM order_verification_failures")
        await conn.execute("DELETE FROM conversation_state WHERE conversation_id LIKE 'eval-%'")
        await conn.commit()


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario_in_fake_mode(scenario, seeded_db):
    settings = Settings(_env_file=None, database_url=seeded_db)

    assert run_scenario(scenario, settings) == []
