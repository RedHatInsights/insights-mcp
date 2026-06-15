"""Tests for Compass catalog tool primitive collection."""

from __future__ import annotations

from types import SimpleNamespace

from insights_mcp.catalog_tools import catalog_tool_description, collect_tool_primitives


def _make_tool(
    *,
    name: str = "example_tool",
    title: str = "",
    description: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(name=name, title=title, description=description)


def test_catalog_tool_description_prefers_title() -> None:
    """Title is used when both title and description are present."""
    tool = _make_tool(title="Short title", description="Longer description line")
    assert catalog_tool_description(tool) == "Short title"


def test_catalog_tool_description_uses_description_when_title_missing() -> None:
    """Description first line is used when title is not set."""
    tool = _make_tool(description="List CVEs affecting the account.")
    assert catalog_tool_description(tool) == "List CVEs affecting the account."


def test_catalog_tool_description_substitutes_brand_long() -> None:
    """$container_brand_long placeholders are substituted for catalog output."""
    tool = _make_tool(title="Get $container_brand_long inventory")
    assert catalog_tool_description(tool, brand_long="Red Hat Lightspeed") == "Get Red Hat Lightspeed inventory"


def test_catalog_tool_description_truncates_long_lines() -> None:
    """Very long descriptions are truncated at a word boundary."""
    long_text = "Word " * 30
    tool = _make_tool(title=long_text.strip())
    result = catalog_tool_description(tool)
    assert len(result) <= 100
    assert result.endswith("…")


def test_collect_tool_primitives_shape_and_uniqueness() -> None:
    """Collected primitives have required fields, unique prefixed names."""
    primitives = collect_tool_primitives()

    assert primitives, "Expected at least one tool primitive from mounted toolsets"

    names = [primitive["name"] for primitive in primitives]
    assert len(names) == len(set(names))

    for primitive in primitives:
        assert primitive == {
            "type": "tool",
            "name": primitive["name"],
            "description": primitive["description"],
        }
        assert primitive["type"] == "tool"
        assert primitive["description"]
        assert "__" in primitive["name"]


def test_collect_tool_primitives_includes_inventory_list_hosts() -> None:
    """A known inventory tool is exported with a non-empty description."""
    primitives = collect_tool_primitives()
    inventory_list_hosts = next(
        (primitive for primitive in primitives if primitive["name"] == "inventory__list_hosts"),
        None,
    )
    assert inventory_list_hosts is not None
    assert inventory_list_hosts["description"]


def test_collect_tool_primitives_includes_distinct_openapi_tools() -> None:
    """Toolsets with duplicate bare names are exported with unique prefixes."""
    primitives = collect_tool_primitives()
    openapi_tools = [primitive["name"] for primitive in primitives if primitive["name"].endswith("__get_openapi")]
    assert "image-builder__get_openapi" in openapi_tools
    assert "vulnerability__get_openapi" in openapi_tools
