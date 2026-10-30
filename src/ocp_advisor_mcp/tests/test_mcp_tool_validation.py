"""Test MCP tool validation for OCP Advisor specific tools."""

from typing import Any, Dict

import pytest

from tests.test_patterns import (
    assert_mcp_tool_descriptions_and_annotations,
    assert_stdio_transport_exposes_tool,
    assert_transport_types_expose_tool,
)

#: All OCP Advisor tools: (name, expected description prefix, expected params).
#: Parameter schemas pin only keys, types and defaults -- not description prose,
#: so wording changes in Field(...) declarations do not break these tests.
OCP_ADVISOR_TOOLS: list[tuple[str, str, Dict[str, Dict[str, Any]]]] = [
    (
        "ocp-advisor__get_info",
        "Get OCP Advisor backend health, deployed OCP rules version, and release metadata.",
        {},
    ),
    (
        "ocp-advisor__list_clusters",
        "List clusters available to the authenticated user.",
        {},
    ),
    (
        "ocp-advisor__get_upgrade_risk",
        "Get upgrade-risk predictions for one or more OpenShift clusters.",
        {
            "cluster_ids": {"type": "array"},
        },
    ),
    (
        "ocp-advisor__get_recommendations",
        "Get Insights Advisor recommendations (rule hits) for a cluster, with rendered details.",
        {
            "cluster_id": {"type": "string"},
            "include_disabled": {"default": False, "type": "boolean"},
        },
    ),
    (
        "ocp-advisor__get_dvo_namespaces",
        "List DVO workload namespaces with recommendation counts and severities.",
        {},
    ),
    (
        "ocp-advisor__get_dvo_recommendations",
        "Get DVO workload recommendations for a cluster namespace, with rendered details.",
        {
            "cluster_id": {"type": "string"},
            "namespace_id": {"type": "string"},
        },
    ),
]

OCP_ADVISOR_TOOL_NAMES = [tool[0] for tool in OCP_ADVISOR_TOOLS]


@pytest.mark.parametrize(
    "tool_name, expected_desc, params",
    OCP_ADVISOR_TOOLS,
    ids=OCP_ADVISOR_TOOL_NAMES,
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


@pytest.mark.parametrize("tool_name", OCP_ADVISOR_TOOL_NAMES)
@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_ocp_advisor_tools(mcp_tools, request, tool_name: str):
    """Test that http and sse transport types expose OCP Advisor tools."""
    assert_transport_types_expose_tool(mcp_tools, request, tool_name)


@pytest.mark.parametrize("tool_name", OCP_ADVISOR_TOOL_NAMES)
@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_ocp_advisor_tools(mcp_tools, tool_name: str):
    """Test stdio transport exposes OCP Advisor tools using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, tool_name)
