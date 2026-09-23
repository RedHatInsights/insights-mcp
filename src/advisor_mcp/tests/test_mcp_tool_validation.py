"""Test MCP tool validation for advisor specific tools.

This module provides parametrized tests for advisor tools using
the reusable test patterns from the top-level tests package.
"""

from typing import Any

import pytest

from advisor_mcp.server import (
    _GROUPS_FIELD_DESC,
    _IMPACT_IDS_FIELD_DESC,
    _RULE_ID_FIELD_DESC,
    _TAGS_FIELD_DESC,
)

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
            "Get active Advisor Recommendations affecting system health, security, or performance.",
            {
                "impacting": {
                    "description": "Only recommendations currently impacting systems.",
                    "default": True,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "impact": {
                    "description": _IMPACT_IDS_FIELD_DESC,
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                },
                "incident": {
                    "description": "Only recommendations that cause incidents.",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "has_automatic_remediation": {
                    "description": "Only recommendations with an automatic remediation playbook.",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "reboot": {
                    "description": "Only recommendations that require a reboot to fix.",
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "boolean"}, {"type": "string"}, {"type": "null"}],
                },
                "tags": {
                    "description": _TAGS_FIELD_DESC,
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
            },
        ),
        (
            "advisor__get_rule_details",
            "Get full Advisor Recommendation details including remediation playbooks (resolution_set).",
            {
                "rule_id": {
                    "description": _RULE_ID_FIELD_DESC,
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_rule_from_node_id",
            "Find Advisor Recommendations linked to a Knowledge Base article or solution ID.",
            {
                "node_id": {
                    "description": "Knowledge base article or solution node ID.",
                    "default": None,
                    "type": "integer",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_hosts_hitting_a_rule",
            "List RHEL systems affected by a specific Advisor Recommendation.",
            {
                "rule_id": {
                    "description": _RULE_ID_FIELD_DESC,
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                }
            },
        ),
        (
            "advisor__get_hosts_details_for_rule",
            "Get paginated detailed information about systems affected by an Advisor Recommendation.",
            {
                "rule_id": {
                    "description": _RULE_ID_FIELD_DESC,
                    "default": None,
                    "type": "string",
                    "anyOf": None,
                },
                "limit": {
                    "description": "Page size.",
                    "default": 10,
                    "type": "integer",
                    "anyOf": None,
                },
                "rhel_version": {
                    "description": (
                        "RHEL major.minor versions, comma-separated (e.g. 9.4). Invalid values are rejected."
                    ),
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
            },
        ),
        (
            "advisor__get_rule_by_text_search",
            "Find Advisor Recommendations containing an exact text substring.",
            {
                "text": {
                    "description": "Text substring to search for.",
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
                    "description": _GROUPS_FIELD_DESC,
                    "default": None,
                    "type": None,
                    "anyOf": [{"type": "string"}, {"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
                "tags": {
                    "description": _TAGS_FIELD_DESC,
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
    params: dict[str, dict[str, Any]],
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
