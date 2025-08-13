"""Test the MCP API.

Test includes:
- tool descriptions and annotations
- tool parameter descriptions
"""

import asyncio
from typing import Dict

import pytest

from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

from .utils import start_mcp_server_process, cleanup_server_process


# Fixtures
@pytest.fixture(scope="module")
def mcp_server_url():
    """Start the MCP server and return the URL."""
    server_url, server_process = start_mcp_server_process()
    try:
        assert server_url and server_url.endswith("/mcp/"), f"Invalid server_url: {server_url}"
        yield server_url
    finally:
        cleanup_server_process(server_process)


@pytest.fixture()
def mcp_tools(mcp_server_url: str):  # pylint: disable=redefined-outer-name
    """Fetch the tools from the MCP server."""
    # Synchronous wrapper around async tool fetch for clearer stacktraces
    client = BasicMCPClient(mcp_server_url)
    tool_spec = McpToolSpec(client=client)

    async def _fetch():
        return await tool_spec.to_tool_list_async()

    # Use a local event loop via asyncio.run for this isolated call
    return asyncio.run(_fetch())


@pytest.mark.parametrize(
    "tool_name, expected_desc, param_descs",
    [
        (
            "get_blueprints",
            "Show user's image blueprints",
            {"limit": "Maximum number of items to return (use 7 as default)"},
        ),
        (
            "get_composes",
            "Get a list of all image builds (composes)",
            {
                "limit": "Maximum number of items to return (use 7 as default)",
                "offset": "Number of items to skip when paging (use 0 as default)",
                "search_string": "Substring to search for in the name",
            },
        ),
    ],
    ids=["get_blueprints", "get_composes"],
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
