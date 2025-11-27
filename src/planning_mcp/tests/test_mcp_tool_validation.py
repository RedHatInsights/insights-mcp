"""Test MCP tool validation for planning specific tools.

This module provides parametrized tests for planning tools using
the reusable test patterns from the top-level tests package.
"""

from typing import Any, Dict

import pytest

from tests.test_patterns import (
    assert_mcp_tool_descriptions_and_annotations,
    assert_stdio_transport_exposes_tool,
    assert_transport_types_expose_tool,
)


@pytest.mark.parametrize(
    "tool_name, expected_desc, params",
    [
        (
            "planning__get_upcoming_changes",
            "List upcoming package changes, deprecations, additions and enhancements.",
            {},
        ),
    ],
    ids=["planning__get_upcoming_changes"],
)
def test_mcp_tools_include_descriptions_and_annotations(
    mcp_tools,
    subtests,
    tool_name: str,
    expected_desc: str,
    params: Dict[str, Dict[str, Any]],
):  # pylint: disable=redefined-outer-name
    """Test that the planning MCP tools include descriptions and annotations."""
    assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)


@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_get_upcoming_changes(mcp_tools, request):
    """Test that http and sse transport types can start and expose get_upcoming_changes tool."""
    assert_transport_types_expose_tool(mcp_tools, request, "planning__get_upcoming_changes")


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_get_upcoming_changes(mcp_tools):
    """Test stdio transport with get_upcoming_changes using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, "planning__get_upcoming_changes")
