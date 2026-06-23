"""Tests for Compass catalog tool primitive collection and catalog-info generation."""

from __future__ import annotations

from fastmcp.tools import Tool
from generate_catalog_info import format_primitives_yaml

from insights_mcp.catalog_tools import catalog_tool_description, collect_tool_primitives


def _make_tool(*, docstring: str = "", title: str | None = None) -> Tool:
    """Build a FastMCP Tool for unit tests."""

    async def stub_tool() -> str:
        return ""

    stub_tool.__doc__ = docstring
    tool = Tool.from_function(stub_tool, name="stub_tool")
    if title is not None:
        tool.title = title
    return tool


def test_catalog_tool_description() -> None:
    """Title, description fallback, and brand substitution."""
    title_tool = _make_tool(docstring="Longer description line", title="Short title")
    assert catalog_tool_description(title_tool) == "Short title"

    description_tool = _make_tool(docstring="List CVEs affecting the account.")
    assert catalog_tool_description(description_tool) == "List CVEs affecting the account."

    brand_tool = _make_tool(title="Get $container_brand_long inventory")
    assert catalog_tool_description(brand_tool, brand_long="Red Hat Lightspeed") == "Get Red Hat Lightspeed inventory"


def test_catalog_tool_description_truncates_long_lines() -> None:
    """Very long descriptions are truncated at a word boundary."""
    long_text = "Word " * 30
    tool = _make_tool(title=long_text.strip())
    result = catalog_tool_description(tool)
    assert len(result) <= 100
    assert result.endswith("…")


def test_collect_tool_primitives() -> None:
    """Mounted toolsets export unique, prefixed, non-empty tool primitives."""
    primitives = collect_tool_primitives()

    assert primitives, "Expected at least one tool primitive from mounted toolsets"

    names = [primitive["name"] for primitive in primitives]
    assert len(names) == len(set(names))

    for primitive in primitives:
        assert primitive["type"] == "tool"
        assert primitive["description"]
        assert "__" in primitive["name"]

    openapi_tools = [name for name in names if name.endswith("__get_openapi")]
    assert "image-builder__get_openapi" in openapi_tools
    assert "vulnerability__get_openapi" in openapi_tools


def test_format_primitives_yaml_inserts_toolset_headings() -> None:
    """Each toolset gets one comment heading; repeated tools share it."""
    primitives = [
        {"type": "tool", "name": "advisor__get_active_rules", "description": "Get active rules"},
        {"type": "tool", "name": "advisor__get_rule_details", "description": "Get rule details"},
        {"type": "tool", "name": "image-builder__get_blueprints", "description": "Get blueprints"},
    ]

    rendered = format_primitives_yaml(primitives)

    assert rendered.count("    # advisor") == 1
    assert rendered.count("    # image-builder") == 1
    assert rendered.index("    # advisor") < rendered.index("advisor__get_active_rules")
    assert rendered.index("    # image-builder") < rendered.index("image-builder__get_blueprints")
