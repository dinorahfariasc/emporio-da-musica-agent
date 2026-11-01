"""MCP server (#8): tool listing, parity with the direct tools, and bearer auth."""

import pytest
from fastmcp import Client
from starlette.testclient import TestClient

from app.config import EmbeddingsProvider, Settings
from app.mcp import CONTRACT_TOOL_NAMES, build_mcp, build_mcp_app
from app.tools.products import get_product


@pytest.fixture
def mcp_settings(seeded_db):
    return Settings(
        _env_file=None,
        database_url=seeded_db,
        embeddings_provider=EmbeddingsProvider.FAKE,
        mcp_api_key="test-mcp-key",
    )


async def test_tools_list_has_all_contract_tools_and_no_ctx_param(mcp_settings):
    mcp = build_mcp(mcp_settings)

    async with Client(mcp) as client:
        tools = await client.list_tools()

    names = {t.name for t in tools}
    assert names == set(CONTRACT_TOOL_NAMES)
    for t in tools:
        assert t.description
        assert "ctx" not in (t.input_schema.get("properties") or {})


async def test_get_product_matches_the_direct_tool(mcp_settings, tool_ctx):
    mcp = build_mcp(mcp_settings)

    async with Client(mcp) as client:
        via_mcp = await client.call_tool("get_product", {"product_id": 121})

    direct = await get_product(tool_ctx, product_id=121)

    assert via_mcp.data["product"]["product_id"] == direct.product.product_id
    assert via_mcp.data["product"]["name"] == direct.product.name
    assert via_mcp.data["product"]["price_brl"] == str(direct.product.price_brl)


def test_no_key_is_rejected(mcp_settings):
    app = build_mcp_app(mcp_settings)
    headers = {"accept": "application/json, text/event-stream"}
    with TestClient(app) as client:
        response = client.post("/mcp/", json={}, headers=headers)
    assert response.status_code == 401


def test_wrong_key_is_rejected(mcp_settings):
    app = build_mcp_app(mcp_settings)
    with TestClient(app) as client:
        response = client.post(
            "/mcp/",
            json={},
            headers={
                "accept": "application/json, text/event-stream",
                "authorization": "Bearer not-the-key",
            },
        )
    assert response.status_code == 401


def test_mcp_disabled_without_an_api_key(seeded_db):
    settings = Settings(
        _env_file=None, database_url=seeded_db, embeddings_provider=EmbeddingsProvider.FAKE
    )
    with pytest.raises(RuntimeError):
        build_mcp_app(settings)
