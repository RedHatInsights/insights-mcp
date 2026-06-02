"""Tests for build_insights_mcp_server and readonly/toolset resolution."""

import asyncio

from insights_mcp import config, server_cli
from insights_mcp.server import InsightsMCPServer, _resolve_readonly, build_insights_mcp_server


def test_resolve_readonly_default():
    """Default readonly mode is enabled when no CLI or env override is set."""
    assert _resolve_readonly(None) is True


def test_resolve_readonly_cli_overrides_env(monkeypatch):
    """Explicit CLI readonly flag overrides all-tools env."""
    monkeypatch.setenv("LIGHTSPEED_MCP_ALL_TOOLS", "true")
    assert _resolve_readonly(True) is True
    assert _resolve_readonly(False) is False


def test_resolve_readonly_env_all_tools(monkeypatch):
    """LIGHTSPEED_MCP_ALL_TOOLS disables readonly when CLI does not pass readonly."""
    monkeypatch.setenv("LIGHTSPEED_MCP_ALL_TOOLS", "true")
    assert _resolve_readonly(None) is False


def test_build_insights_mcp_server_image_builder_readonly_catalog(monkeypatch):
    """Read-only image-builder server exposes only image-builder read tools plus get_mcp_version."""
    monkeypatch.setattr(config, "INSIGHTS_CLIENT_ID", "instrumentation-placeholder")
    monkeypatch.setattr(config, "INSIGHTS_CLIENT_SECRET", "instrumentation-placeholder")
    server = build_insights_mcp_server(toolset="image-builder", readonly=True)
    tools = asyncio.run(server.list_tools())
    names = [t.name for t in tools]

    assert names
    image_builder_names = [name for name in names if name.startswith("image-builder")]
    assert image_builder_names
    assert all(name.startswith("image-builder__") for name in image_builder_names)
    assert "image-builder__get_blueprints" in names
    assert "get_mcp_version" in names


def test_server_cli_exports_fastmcp_server():
    """server_cli module exposes a built InsightsMCPServer for fastmcp tooling."""
    assert isinstance(server_cli.server, InsightsMCPServer)
