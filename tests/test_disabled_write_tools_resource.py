"""Tests for disabled-write-tools MCP resource on InsightsMCPServer."""

from unittest.mock import patch

import pytest

from insights_mcp.cli_catalog import DISABLED_WRITE_TOOLS_RESOURCE_URI
from insights_mcp.server import build_insights_mcp_server


@pytest.mark.asyncio
@patch("insights_mcp.server.setup_credentials")
@patch("insights_mcp.cli_catalog.collect_readwrite_tools_by_toolset")
async def test_readonly_server_exposes_disabled_write_tools_resource(
    mock_collect,
    _mock_setup_credentials,
    monkeypatch,
):
    """Read-only server registers catalog resource when write tools exist."""
    monkeypatch.setattr(
        "insights_mcp.config.INSIGHTS_CLIENT_ID",
        "instrumentation-placeholder",
    )
    monkeypatch.setattr(
        "insights_mcp.config.INSIGHTS_CLIENT_SECRET",
        "instrumentation-placeholder",
    )
    monkeypatch.setattr("insights_mcp.config.INSIGHTS_MCP_ALL_TOOLS", False)
    mock_collect.return_value = {
        "image-builder": [("image-builder__create_blueprint", "Create a blueprint")],
    }
    server = build_insights_mcp_server(toolset="image-builder", readonly=True)
    resources = await server.list_resources()
    uris = {str(resource.uri) for resource in resources}
    assert DISABLED_WRITE_TOOLS_RESOURCE_URI in uris
    result = await server.read_resource(DISABLED_WRITE_TOOLS_RESOURCE_URI)
    catalog_text = "".join(content.content for content in result.contents if hasattr(content, "content"))
    assert "image-builder__create_blueprint" in catalog_text


@pytest.mark.asyncio
@patch("insights_mcp.server.setup_credentials")
@patch("insights_mcp.cli_catalog.collect_readwrite_tools_by_toolset")
async def test_all_tools_server_hides_disabled_write_tools_resource(
    mock_collect,
    _mock_setup_credentials,
    monkeypatch,
):
    """All-tools server does not register the disabled-write-tools resource."""
    monkeypatch.setattr(
        "insights_mcp.config.INSIGHTS_CLIENT_ID",
        "instrumentation-placeholder",
    )
    monkeypatch.setattr(
        "insights_mcp.config.INSIGHTS_CLIENT_SECRET",
        "instrumentation-placeholder",
    )
    monkeypatch.setattr("insights_mcp.config.INSIGHTS_MCP_ALL_TOOLS", True)
    mock_collect.return_value = {
        "image-builder": [("image-builder__create_blueprint", "Create a blueprint")],
    }
    server = build_insights_mcp_server(toolset="image-builder", readonly=False)
    resources = await server.list_resources()
    uris = {str(resource.uri) for resource in resources}
    assert DISABLED_WRITE_TOOLS_RESOURCE_URI not in uris
