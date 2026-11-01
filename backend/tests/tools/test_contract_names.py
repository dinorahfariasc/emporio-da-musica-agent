from app.tools import registry  # noqa: F401 - importing app.tools registers every tool
from app.tools.registry import CONTRACT_TOOL_NAMES, REGISTRY


def test_registered_tools_match_the_contract_exactly():
    assert set(REGISTRY) == set(CONTRACT_TOOL_NAMES)
