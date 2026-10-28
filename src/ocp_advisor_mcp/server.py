"""Red Hat Insights OCP Advisor MCP Server.

MCP server for OCP Advisor data via the Insights Results Smart Proxy API.
Provides tools to get OpenShift Advisor information from Red Hat Insights.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from insights_mcp.errors import InsightsApiError
from insights_mcp.mcp import InsightsMCP
from tools.common import run_insights_tool_request

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

    Use list_clusters to discover cluster IDs, then get_upgrade_risk_prediction for a single cluster's
    upgrade-risk assessment. A missing or unavailable prediction is not the same as an explicit no-risk result;
    do not infer upgrade safety from missing data.

    On permission errors (HTTP 403), call rbac__explain_access_denied with the failed tool name or URL.
    """,
)


def _unavailable_prediction(cluster_id: str, reason: str, detail: str) -> dict[str, Any]:
    """Build a structured response for clusters without an upgrade-risk prediction."""
    return {
        "cluster_id": cluster_id,
        "prediction_available": False,
        "reason": reason,
        "detail": detail,
    }


def _normalize_upgrade_risk_response(
    cluster_id: str,
    response: dict[str, Any] | str | list[Any],
) -> dict[str, Any] | str | list[Any]:
    """Attach cluster_id and map empty/204 bodies to an explicit unavailable result."""
    # Smart Proxy returns HTTP 204 (no body) for managed clusters; InsightsClient yields "".
    if response == "":
        return _unavailable_prediction(
            cluster_id,
            "managed_cluster",
            "Upgrade-risk prediction is not available for managed clusters.",
        )
    if isinstance(response, dict):
        return {
            "cluster_id": cluster_id,
            "prediction_available": True,
            **response,
        }
    return response


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


@mcp.tool(annotations={"readOnlyHint": True})
async def list_clusters() -> str:
    """List clusters available to the authenticated user.

    🟢 CALL IMMEDIATELY - No information gathering required.

    Uses the Insights Results Aggregator v2 ``/clusters`` endpoint, which returns clusters
    visible to the authenticated account along with recommendation hit counts and risk summaries.
    """
    return await run_insights_tool_request(
        mcp.insights_client.get("clusters"),
        error_message=lambda exc: f"Error listing Insights Results Aggregator clusters: {exc}",
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def get_upgrade_risk_prediction(
    cluster_id: Annotated[
        str,
        Field(
            description=(
                "OpenShift cluster UUID. Take it from list_clusters or from the user. "
                "Call this for one cluster only."
            ),
        ),
    ],
) -> str:
    """Get upgrade-risk prediction for one OpenShift cluster.

    🟢 CALL IMMEDIATELY when a cluster UUID is already known.

    Uses Insights Results Aggregator v2 ``/cluster/{clusterId}/upgrade-risks-prediction``.
    Successful responses include whether an upgrade is recommended, supporting alert and
    operator-condition predictors, and ``meta.last_checked_at`` when the API supplies it.

    Managed clusters (HTTP 204 / empty body) return structured JSON with
    ``prediction_available: false``. Missing data (HTTP 404) and upstream failures are
    raised as errors — distinct from an explicit no-risk prediction
    (``upgrade_recommended: true`` / empty predictors). Do not treat unavailable data as
    upgrade safety.
    """
    normalized = cluster_id.strip()
    if not normalized:
        raise InsightsApiError("cluster_id must be a non-empty cluster UUID, got an empty value")

    endpoint = f"cluster/{normalized}/upgrade-risks-prediction"
    return await run_insights_tool_request(
        mcp.insights_client.get(endpoint),
        error_message=lambda exc: (
            f"Error retrieving upgrade-risk prediction for cluster {normalized}: {exc}"
        ),
        response_transform=lambda response: _normalize_upgrade_risk_response(normalized, response),
    )
