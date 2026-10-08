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
    This server provides tools to access OCP Advisor data from $container_brand_long.

    Use these tools when the user asks about OpenShift/OCP Advisor service status,
    backend information, or service metrics.

    On permission errors (HTTP 403), call rbac__explain_access_denied with the failed tool name or URL.
    """,
)


@mcp.tool(annotations={"readOnlyHint": True})
async def get_info() -> dict[str, Any] | str:
    """Get basic information about the OCP Advisor backend services.

    🟢 CALL IMMEDIATELY - No information gathering required.

    Returns Smart Proxy, Insights Results Aggregator, and Content Service version,
    commit, and status information from the /info endpoint.
    """
    response = await mcp.insights_client.get("info", noauth=True)
    if isinstance(response, str):
        return response
    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def get_metrics() -> dict[str, Any] | str:
    """Get OCP Advisor backend service metrics.

    🟢 CALL IMMEDIATELY - No information gathering required.

    Returns Prometheus metrics from the authenticated /metrics endpoint.
    """
    response = await mcp.insights_client.get("metrics")
    if isinstance(response, str):
        return response
    return response
