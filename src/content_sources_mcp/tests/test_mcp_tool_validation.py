"""Test MCP tool validation for content-sources specific tools.

This module provides parametrized tests for content-sources tools using
the reusable test patterns from the top-level tests package.
"""

from typing import Any, Dict

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
                    "description": "Maximum number of repositories to return (default: 10).",
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
    ],
    ids=["content-sources__list_repositories"],
)
def test_mcp_tools_include_descriptions_and_annotations(
    mcp_tools,
    subtests,
    tool_name: str,
    expected_desc: str,
    params: Dict[str, Dict[str, Any]],
):  # pylint: disable=redefined-outer-name
    """Test that the content-sources MCP tools include descriptions and annotations."""
    assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)


@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_list_repositories(mcp_tools, request):
    """Test that http and sse transport types can start and expose list_repositories tool."""
    assert_transport_types_expose_tool(mcp_tools, request, "content-sources__list_repositories")


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_list_repositories(mcp_tools):
    """Test stdio transport with list_repositories tool using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, "content-sources__list_repositories")
