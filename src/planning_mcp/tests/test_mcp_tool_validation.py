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
        (
            "planning__get_appstreams_lifecycle",
            "Get Application Streams lifecycle information.",
            {},
        ),
    ],
    ids=[
        "planning__get_upcoming_changes",
        "planning__get_appstreams_lifecycle",
    ],
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
@pytest.mark.parametrize(
    "tool_name",
    [
        "planning__get_upcoming_changes",
        "planning__get_appstreams_lifecycle",
    ],
)
def test_transport_types_with_planning_tools(mcp_tools, request, tool_name: str):
    """Test that http and sse transport types can start and expose planning tools."""
    assert_transport_types_expose_tool(mcp_tools, request, tool_name)


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
@pytest.mark.parametrize(
    "tool_name",
    [
        "planning__get_upcoming_changes",
        "planning__get_appstreams_lifecycle",
    ],
)
def test_stdio_transport_with_planning_tools(mcp_tools, tool_name: str):
    """Test stdio transport with planning tools using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, tool_name)
