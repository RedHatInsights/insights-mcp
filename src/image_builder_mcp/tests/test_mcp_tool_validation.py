"""Test MCP tool validation for image-builder specific tools.

This module provides parametrized tests for image-builder tools using
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
            "image-builder__get_blueprints",
            "Show user's image blueprints",
            {
                "limit": {
                    "description": "Maximum number of items to return (use 7 as default)",
                    "default": 7,
                    "type": "integer",
                    "anyOf": None,
                }
            },
        ),
        (
            "image-builder__get_composes",
            "Get a list of all image builds (composes)",
            {
                "limit": {
                    "description": "Maximum number of items to return (use 7 as default)",
                    "default": 7,
                    "type": "integer",
                    "anyOf": None,
                },
                "offset": {
                    "description": "Number of items to skip when paging (use 0 as default)",
                    "default": 0,
                    "type": "integer",
                    "anyOf": None,
                },
                "search_string": {
                    "description": "Substring to search for in the name",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                },
            },
        ),
        (
            "image-builder__get_openapi",
            "Get OpenAPI spec. Use this to get details e.g for a new blueprint",
            {
                "response_size": {
                    "description": "Number of items returned (use 7 as default)",
                    "default": 7,
                    "type": "integer",
                    "anyOf": None,
                }
            },
        ),
    ],
    ids=["image-builder__get_blueprints", "image-builder__get_composes", "image-builder__get_openapi"],
)
def test_mcp_tools_include_descriptions_and_annotations(
    mcp_tools,
    subtests,
    tool_name: str,
    expected_desc: str,
    params: Dict[str, Dict[str, Any]],
):  # pylint: disable=redefined-outer-name
    """Test that the image-builder MCP tools include descriptions and annotations."""
    assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)


@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_get_blueprints(mcp_tools, request):
    """Test that http and sse transport types can start and expose get_blueprints tool."""
    assert_transport_types_expose_tool(mcp_tools, request, "image-builder__get_blueprints")


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_get_blueprints(mcp_tools):
    """Test stdio transport with get_blueprints tool using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, "image-builder__get_blueprints")
