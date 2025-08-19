"""Test the MCP API.

Test includes:
- tool descriptions and annotations
- tool parameter descriptions
"""

from typing import Dict

import pytest


@pytest.mark.parametrize(
    "tool_name, expected_desc, param_descs",
    [
        (
            "image-builder__get_blueprints",
            "Show user's image blueprints",
            {"limit": "Maximum number of items to return (use 7 as default)"},
        ),
        (
            "image-builder__get_composes",
            "Get a list of all image builds (composes)",
            {
                "limit": "Maximum number of items to return (use 7 as default)",
                "offset": "Number of items to skip when paging (use 0 as default)",
                "search_string": "Substring to search for in the name",
            },
        ),
    ],
    ids=["image-builder__get_blueprints", "image-builder__get_composes"],
)
def test_mcp_tools_include_descriptions_and_annotations(
    mcp_tools,
    subtests,
    tool_name: str,
    expected_desc: str,
    param_descs: Dict[str, str],
):  # pylint: disable=redefined-outer-name
    """Test that the MCP tools include descriptions and annotations."""
    tools = mcp_tools

    # Build map for quick lookup
    name_to_tool = {getattr(t.metadata, "name", ""): t for t in tools}
    assert tool_name in name_to_tool, f"Tool not found: {tool_name}"
    tool = name_to_tool[tool_name]

    # Description check
    desc = getattr(tool.metadata, "description", "") or ""
    assert desc.startswith(expected_desc)

    fn_schema = getattr(tool.metadata, "fn_schema", None)
    assert fn_schema is not None, f"{tool_name}: fn_schema is None"
    assert hasattr(fn_schema, "model_json_schema"), f"{tool_name}: fn_schema.model_json_schema missing"
    schema_obj = fn_schema.model_json_schema()  # type: ignore[attr-defined]
    assert isinstance(schema_obj, dict), f"{tool_name}: invalid fn_schema (model_json_schema not dict)"

    props = schema_obj.get("properties", {}) or {}
    for param_name, expected_param_desc in param_descs.items():
        with subtests.test(param=param_name):
            assert props.get(param_name, {}).get("description") == expected_param_desc
    # Note: Testing defaults would be ideal but
    # default is null in FastMCP schema by design; actual defaulting occurs server-side


@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_get_blueprints(mcp_tools, request):
    """Test that http and sse transport types can start and expose get_blueprints tool."""
    # Get transport from the fixture parameter
    transport = request.node.callspec.params["mcp_server_url"]

    # Build map for quick lookup
    tool_names = {getattr(t.metadata, "name", "") for t in mcp_tools}

    # Verify get_blueprints is available (with image-builder prefix)
    assert "image-builder__get_blueprints" in tool_names, (
        f"image-builder__get_blueprints not found in tools for {transport} transport. Available tools: {tool_names}"
    )


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_get_blueprints(mcp_tools):
    """Test stdio transport with get_blueprints tool using BasicMCPClient subprocess."""
    # Build map for quick lookup
    tool_names = {getattr(t.metadata, "name", "") for t in mcp_tools}

    # Verify get_blueprints is available (with image-builder prefix)
    assert "image-builder__get_blueprints" in tool_names, (
        f"image-builder__get_blueprints not found in tools for stdio transport. Available tools: {tool_names}"
    )
