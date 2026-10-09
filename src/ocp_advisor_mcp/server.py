"""Red Hat Insights OCP Advisor MCP Server.

MCP server for OCP Advisor data via the Insights Results Smart Proxy API.
Provides tools to get OpenShift Advisor information from Red Hat Insights.
"""

from typing import Any

from insights_mcp.mcp import InsightsMCP

mcp = InsightsMCP(
    name="$container_brand_long OCP Advisor MCP Server",
    toolset_name="ocp-advisor",
    api_path="api/insights-results-aggregator/v2",
    instructions="""
    This server provides tools for OpenShift/OCP Advisor, the $container_brand_long advisor service for
    assessing and monitoring Red Hat OpenShift cluster health. OCP Advisor analyzes data collected by Insights
    Operator against recommendation content to identify conditions that can affect cluster availability, fault
    tolerance, performance, or security.

    Advisor recommendations can describe impacted clusters, risk/category, publication details, related Red Hat
    guidance, and tailored resolution information. The current tools expose service metadata from the Insights
    Results Smart Proxy /info endpoint, including Smart Proxy, Insights Results Aggregator, and Content Service
    health/status, build times, versions, commit hashes, utility version, database versions, and deployed OCP rules
    version. Use them for release verification, deployed ccx-ocp-rules checks, and backend health diagnostics.

    On permission errors (HTTP 403), call rbac__explain_access_denied with the failed tool name or URL.
    """,
)


@mcp.tool(annotations={"readOnlyHint": True})
async def get_info() -> dict[str, Any] | str:
    """Get OCP Advisor backend health, deployed OCP rules version, and release metadata.

    🟢 CALL IMMEDIATELY - No information gathering required.

    Returns internal Smart Proxy, Insights Results Aggregator, and Content Service
    status/build/version metadata from the unauthenticated /info endpoint. This is
    primarily useful for service diagnostics, release verification, and backend
    health checks; it does not return Advisor recommendations or cluster findings.
    """
    response = await mcp.insights_client.get("info", noauth=True)
    if isinstance(response, str):
        return response
    return response
