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
            "Get upgrade-risk prediction for one OpenShift cluster.",
            {
                "cluster_id": {
                    "description": "OpenShift cluster UUID. Take it from list_clusters or from the user. Call this for one cluster only.",
                    "type": "string",
                    "anyOf": None,
                },
            },
        ),
    ],
    ids=[
        "ocp-advisor__get_info",
        "ocp-advisor__list_clusters",
        "ocp-advisor__get_upgrade_risk",
    ],
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


@pytest.mark.parametrize(
    "tool_name",
    [
        "ocp-advisor__get_info",
        "ocp-advisor__list_clusters",
        "ocp-advisor__get_upgrade_risk",
    ],
)
@pytest.mark.parametrize("mcp_server_url", ["http", "sse"], indirect=True)
def test_transport_types_with_ocp_advisor_tools(mcp_tools, request, tool_name: str):
    """Test that http and sse transport types expose OCP Advisor tools."""
    assert_transport_types_expose_tool(mcp_tools, request, tool_name)


@pytest.mark.parametrize(
    "tool_name",
    [
        "ocp-advisor__get_info",
        "ocp-advisor__list_clusters",
        "ocp-advisor__get_upgrade_risk",
    ],
)
@pytest.mark.parametrize("mcp_server_url", ["stdio"], indirect=True)
def test_stdio_transport_with_ocp_advisor_tools(mcp_tools, tool_name: str):
    """Test stdio transport exposes OCP Advisor tools using BasicMCPClient subprocess."""
    assert_stdio_transport_exposes_tool(mcp_tools, tool_name)
