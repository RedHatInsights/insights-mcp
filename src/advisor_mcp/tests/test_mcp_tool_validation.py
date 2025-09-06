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
                    "description": "Only show recommendations currently impacting systems. Default: true",
                    "default": True,
                    "type": "boolean",
                    "anyOf": None,
                },
                "impact": {
                    "description": "Impact level filter as comma-separated string, e.g. '1,2,3'. "
                    "Available values: 1=Low, 2=Medium, 3=High, 4=Critical. Example: '3,4'",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                },
                "tags": {
                    "description": (
                        "Used with impacting=True to filter recommendations that are relevant to the target systems. "
                        "Filter recommendations by system tags or groups using 'namespace/key=value' format. "
                        "namespace: 'satellite' or 'insights-client' "
                        "Examples: ['satellite/group=database-servers', 'insights-client/security=strict'] or "
                        "JSON string format: "
                        '\'["satellite/group=database-servers", "insights-client/security=strict"]\''
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
                    "description": "Unique identifier of the Advisor Recommendation. Must be a valid string format. "
                    "Example: 'xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL'",
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
                    "description": (
                        "Node ID of the knowledge base article or solution to find related "
                        "Advisor Recommendations. Must be a valid string format. Example: '123456'"
                    ),
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_hosts_hitting_a_rule",
            "Get all RHEL systems affected by a specific Advisor Recommendation.",
            {
                "rule_id": {
                    "description": "Unique identifier of the Advisor Recommendation. Must be a valid string "
                    "format. Example: 'xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL'",
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_hosts_details_hitting_a_rule",
            "Get detailed information about RHEL systems affected by a specific Advisor Recommendation.",
            {
                "rule_id": {
                    "description": "Unique identifier of the Advisor Recommendation. Must be a valid string format. "
                    "Example: 'xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL'",
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                },
                "limit": {
                    "description": "Pagination: Maximum number of results per page. Default: 20",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "null"}],
                },
                "rhel_version": {
                    "description": "Display only systems with these versions of RHEL. "
                    "Available values: 10.0, 10.1, 10.2, 6.0, 6.1, 6.10, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, "
                    "7.0, 7.1, 7.10, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 8.0, 8.1, 8.10, 8.2, 8.3, 8.4, 8.5, "
                    "8.6, 8.7, 8.8, 8.9, 9.0, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8. Example: '9.4'",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"type": "null"}],
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
            "advisor__get_recommendations_statistics",
            "Show statistics of recommendations across categories and risks.",
            {
                "groups": {
                    "description": "Filter recommendations by system groups. Comma separated list of workspace names. "
                    "Example: 'workspace1,workspace2'",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
                "tags": {
                    "description": "Filter recommendations by system tags in the form namespace/key=value. "
                    "namespace: 'satellite' or 'insights-client' "
                    "Examples: ['satellite/group=database-servers', 'insights-client/security=strict'] or "
                    'JSON string format: \'["satellite/group=database-servers", "insights-client/security=strict"]\'',
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
        "advisor__get_hosts_details_hitting_a_rule",
        "advisor__get_rule_by_text_search",
        "advisor__get_recommendations_statistics",
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
