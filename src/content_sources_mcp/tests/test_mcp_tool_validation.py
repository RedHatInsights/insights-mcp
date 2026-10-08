"""Test MCP tool validation for content-sources specific tools.

This module provides parametrized tests for content-sources tools using
the reusable test patterns from the top-level tests package.
"""

from typing import Any

import pytest

# Import the test pattern functions from top-level tests
from tests.test_patterns import (
    assert_mcp_tool_descriptions_and_annotations,
    assert_stdio_transport_exposes_tool,
    assert_transport_types_expose_tool,
)


@pytest.mark.parametrize(
    "tool_name, expected_desc, params",
    [
        (
            "content-sources__list_repositories",
            "List repositories with filtering and pagination options.",
            {
                "limit": {
                    "description": (
                        "Maximum number of repositories to return (default: 10, maximum: 100). "
                        "**ALWAYS use the default value of 10 for the first call.** "
                        "This default is carefully chosen for performance and context management. "
                        "Only increase this value if the user explicitly asks to see more repositories at once."
                    ),
                    "default": 10,
                    "type": "integer",
                    "anyOf": None,
                },
                "offset": {
                    "description": "Number of repositories to skip for pagination (default: 0).",
                    "default": 0,
                    "type": "integer",
                    "anyOf": None,
                },
                "name": {
                    "description": "Filter by repository name (case-insensitive).",
                    "default": "",
                    "type": "string",
                    "anyOf": None,
                },
                "url": {
                    "description": "Filter by repository URL (case-insensitive).",
                    "default": "",
                    "type": "string",
                    "anyOf": None,
                },
                "content_type": {
                    "description": "Filter by content type (e.g., 'rpm', 'ostree').",
                    "default": "",
                    "type": "string",
                    "anyOf": None,
                },
                "origin": {
                    "description": "Filter by origin (e.g., 'red_hat', 'external').",
                    "default": "",
                    "type": "string",
                    "anyOf": None,
                },
                "enabled": {
                    "description": "Filter by enabled status (True/False).",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "null"}],
                },
                "arch": {
                    "description": "Filter by architecture (e.g., 'x86_64', 'aarch64').",
                    "default": "",
                    "type": "string",
                    "anyOf": None,
                },
                "version": {
                    "description": "Filter by version (e.g., '8', '9').",
                    "default": "",
                    "type": "string",
                    "anyOf": None,
                },
            },
        ),
        (
            "content-sources__get_repository",
            "Get full details for one repository by UUID.",
            {
                "repository_uuid": {
                    "description": (
                        "UUID of a single repository. Take it from list_repositories or from the user. "
                        "Call this for one repository only."
                    ),
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                },
            },
        ),
    ],
    ids=["content-sources__list_repositories", "content-sources__get_repository"],
)
def test_mcp_tools_include_descriptions_and_annotations(
    mcp_tools,
    subtests,
    tool_name: str,
    expected_desc: str,
    params: dict[str, dict[str, Any]],
):  # pylint: disable=redefined-outer-name
    """Test that the content-sources MCP tools include descriptions and annotations."""
    assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)
    if tool_name == "content-sources__list_repositories":
        list_tool = next(tool for tool in mcp_tools if getattr(tool.metadata, "name", "") == tool_name)
        list_schema = list_tool.metadata.fn_schema.model_json_schema()
        assert "include_gpg_key" not in list_schema.get("properties", {})


@pytest.mark.parametrize(
    "tool_name",
    ["content-sources__list_repositories", "content-sources__get_repository"],
)
@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_content_sources_tools(mcp_tools, request, tool_name: str):
    """Test that http and sse transport types expose content-sources tools."""
    assert_transport_types_expose_tool(mcp_tools, request, tool_name)


@pytest.mark.parametrize(
    "tool_name",
    ["content-sources__list_repositories", "content-sources__get_repository"],
)
@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_content_sources_tools(mcp_tools, tool_name: str):
    """Test stdio transport exposes content-sources tools using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, tool_name)
