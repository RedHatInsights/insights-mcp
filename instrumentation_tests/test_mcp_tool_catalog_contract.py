"""Non-behavioral checks on mounted MCP tool catalogs (no LLM calls)."""

import asyncio

import pytest

from insights_mcp.server import InsightsMCPServer


@pytest.mark.instrumentation
def test_image_builder_readonly_tool_catalog_contract():
    """image-builder mounted read-only exposes only prefixed tools with metadata."""
    server = InsightsMCPServer(
        name="Instrumentation",
        client_id="instrumentation-placeholder",
        client_secret="instrumentation-placeholder",
    )
    server.register_mcps(["image-builder"], readonly=True)
    tools = asyncio.run(server.list_tools())
    names = [t.name for t in tools]

    assert names, "expected at least one image-builder tool"
    assert all(name.startswith("image-builder__") for name in names)
    assert "image-builder__get_blueprints" in names

    for tool in tools:
        text = ((getattr(tool, "description", None) or "") + (getattr(tool, "title", None) or "")).strip()
        assert text, f"tool {tool.name!r} must have a description or title"
