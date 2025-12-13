"""Brand-specific behavior tests for the Insights MCP server."""

import pytest

from tests.test_cli_arguments import get_mcp_tools_with_toolset


@pytest.mark.parametrize(
    ("brand", "expected_brand_long"),
    [
        ("insights", "Red Hat Insights"),
        ("red-hat-lightspeed", "Red Hat Lightspeed"),
    ],
)
def test_get_mcp_version_description_uses_container_brand(
    brand: str,
    expected_brand_long: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure get_mcp_version description uses the correct container brand."""
    monkeypatch.setenv("CONTAINER_BRAND", brand)

    tools = get_mcp_tools_with_toolset("http", toolset=None)
    tool_map = {getattr(t.metadata, "name", ""): t for t in tools}

    assert "get_mcp_version" in tool_map
    version_tool = tool_map["get_mcp_version"]

    description = getattr(version_tool.metadata, "description", "") or ""
    expected_prefix = f"Get the version of the {expected_brand_long} MCP server."

    assert description.startswith(expected_prefix)
