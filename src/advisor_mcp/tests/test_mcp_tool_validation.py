"""Test MCP tool validation for advisor specific tools.

This module provides parametrized tests for advisor tools using
the reusable test patterns from the top-level tests package.
"""

from typing import Any, Dict

import pytest

# Import the test pattern functions from top-level tests
from tests.test_patterns import (  # pylint: disable=import-error
    assert_mcp_tool_descriptions_and_annotations,
    assert_stdio_transport_exposes_tool,
    assert_transport_types_expose_tool,
)


@pytest.mark.parametrize(
    "tool_name, expected_desc, params",
    [
        (
            "advisor__get_active_rules",
            "Get active Advisor Recommendations for your account that help identify issues",
            {
                "impacting": {
                    "description": "Only show recommendations currently impacting systems.",
                    "default": True,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "impact": {
                    "description": "Impact level filter as comma-separated string, Example: '1,2,3'. "
                    "Accepted values: 1 (Low), 2 (Medium), 3 (High), 4 (Critical). "
                    "Use only these exact values: 1, 2, 3, or 4.",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                },
                "incident": {
                    "description": "Only show recommendations that cause incidents.",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "has_automatic_remediation": {
                    "description": "Only show recommendations that have a playbook for automatic remediation.",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "reboot": {
                    "description": "Filter recommendations that require a reboot to fix.",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "tags": {
                    "description": (
                        "Filter based on system tags. Accepts a single tag or a comma-separated list."
                        "Used only when impacting=True. "
                        "Tag format: 'namespace/key=value'. "
                        "Example: 'satellite/group=database-servers,insights-client/security=strict'"
                    ),
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
            },
        ),
        (
            "advisor__get_rule_details",
            "Get detailed information about a specific Advisor Recommendation, including",
            {
                "rule_id": {
                    "description": "Recommendation identifier in format: rule_name|ERROR_KEY.",
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_rule_from_node_id",
            "Find Advisor Recommendations related to a specific Knowledge Base article or solution.",
            {
                "node_id": {
                    "description": "Node ID of the knowledge base article or solution. Example: 123456",
                    "default": None,
                    "type": "integer",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_hosts_hitting_a_rule",
            "Get all RHEL systems affected by a specific Advisor Recommendation.",
            {
                "rule_id": {
                    "description": "Recommendation identifier in format: rule_name|ERROR_KEY.",
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_hosts_details_for_rule",
            "Get detailed information about RHEL systems affected by a specific Advisor Recommendation.",
            {
                "rule_id": {
                    "description": "Recommendation identifier in format: rule_name|ERROR_KEY.",
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                },
                "limit": {
                    "description": "Pagination: Maximum number of results per page.",
                    "default": 10,
                    "type": "integer",
                    "anyOf": None,
                },
                "rhel_version": {
                    "description": "Filter systems by RHEL version. Accepts a comma-separated string or a list. "
                    "Allowed values: 6.0-6.10, 7.0-7.10, 8.0-8.10, 9.0-9.8, 10.0-10.2. Example: '9.3,9.4,9.5'",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
            },
        ),
        (
            "advisor__get_rule_by_text_search",
            "Finds Advisor Recommendations that contain an exact text substring.",
            {
                "text": {
                    "description": "The text substring to search for. Example: 'xfs'",
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_recommendations_stats",
            "Show statistics of recommendations across categories and risks.",
            {
                "groups": {
                    "description": "Filter based on workspace names. Comma separated list of workspace names."
                    "Used only when impacting=True. "
                    "Example: 'workspace1,workspace2'",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
                "tags": {
                    "description": "Filter based on system tags. Accepts a single tag or a comma-separated list."
                    "Used only when impacting=True. "
                    "Tag format: 'namespace/key=value'. "
                    "Example: 'satellite/group=database-servers,insights-client/security=strict'",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
            },
        ),
    ],
    ids=[
        "advisor__get_active_rules",
        "advisor__get_rule_details",
        "advisor__get_rule_from_node_id",
        "advisor__get_hosts_hitting_a_rule",
        "advisor__get_hosts_details_for_rule",
        "advisor__get_rule_by_text_search",
        "advisor__get_recommendations_stats",
    ],
)
def test_mcp_tools_include_descriptions_and_annotations(
    mcp_tools,
    subtests,
    tool_name: str,
    expected_desc: str,
    params: Dict[str, Dict[str, Any]],
):  # pylint: disable=redefined-outer-name
    """Test that the advisor MCP tools include descriptions and annotations."""
    assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)


@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_get_active_rules(mcp_tools, request):
    """Test that http and sse transport types can start and expose get_active_rules tool."""
    assert_transport_types_expose_tool(mcp_tools, request, "advisor__get_active_rules")


@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_get_active_rules(mcp_tools):
    """Test stdio transport with get_active_rules tool using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, "advisor__get_active_rules")
