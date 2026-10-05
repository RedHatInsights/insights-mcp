"""Test MCP tool validation for OCP Advisor specific tools."""

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
            "ocp-advisor__get_info",
            "Get basic information about the OCP Advisor backend services.",
            {},
        ),
        (
            "ocp-advisor__get_metrics",
            "Get OCP Advisor backend service metrics.",
            {},
        ),
    ],
    ids=["ocp-advisor__get_info", "ocp-advisor__get_metrics"],
)
def test_mcp_tools_include_descriptions_and_annotations(
    mcp_tools,
    subtests,
    tool_name: str,
    expected_desc: str,
    params: Dict[str, Dict[str, Any]],
):  # pylint: disable=redefined-outer-name
    """Test that the OCP Advisor MCP tools include descriptions and annotations."""
    assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)


@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_get_info(mcp_tools, request):
    """Test that http and sse transport types can start and expose get_info tool."""
    assert_transport_types_expose_tool(mcp_tools, request, "ocp-advisor__get_info")


@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_get_metrics(mcp_tools, request):
    """Test that http and sse transport types can start and expose get_metrics tool."""
    assert_transport_types_expose_tool(mcp_tools, request, "ocp-advisor__get_metrics")


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_get_info(mcp_tools):
    """Test stdio transport with get_info tool using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, "ocp-advisor__get_info")


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_get_metrics(mcp_tools):
    """Test stdio transport with get_metrics tool using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, "ocp-advisor__get_metrics")
