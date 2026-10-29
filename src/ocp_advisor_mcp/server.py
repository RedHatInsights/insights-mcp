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

# Smart Proxy rejects multi-cluster upgrade-risk requests above this size.
_MAX_UPGRADE_RISK_CLUSTERS = 100

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
    health/status, build times, versions, commit hashes, utility version, database versions, and deployed OCP
    rules version. Use them for release verification, deployed ccx-ocp-rules checks, and backend health
    diagnostics.

    Use list_clusters to discover cluster IDs, then get_upgrade_risk with one or more cluster UUIDs.
    Each prediction includes prediction_status: only status "ok" is a real assessment. Other statuses
    (for example "No data for the cluster") mean unavailable data — not the same as an explicit no-risk
    result (upgrade_recommended: true / empty predictors). Do not infer upgrade safety from missing data.

    On permission errors (HTTP 403), call rbac__explain_access_denied with the failed tool name or URL.
    """,
)


def _normalize_cluster_ids(cluster_ids: list[str]) -> list[str]:
    """Strip cluster UUIDs and reject empty or oversized lists."""
    if not cluster_ids:
        raise InsightsApiError("cluster_ids must contain at least one cluster UUID, got an empty list")

    normalized: list[str] = []
    for cluster_id in cluster_ids:
        value = cluster_id.strip()
        if not value:
            raise InsightsApiError("cluster_ids must contain non-empty cluster UUIDs, got an empty value")
        normalized.append(value)

    if len(normalized) > _MAX_UPGRADE_RISK_CLUSTERS:
        raise InsightsApiError(
            f"cluster_ids supports at most {_MAX_UPGRADE_RISK_CLUSTERS} clusters per request, got {len(normalized)}"
        )
    return normalized


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
async def get_upgrade_risk(
    cluster_ids: Annotated[
        list[str],
        Field(
            description=(
                "OpenShift cluster UUIDs (1-100). Take them from list_clusters or from the user. "
                "Pass a one-element list for a single cluster."
            ),
        ),
    ],
) -> str:
    """Get upgrade-risk predictions for one or more OpenShift clusters.

    🟢 CALL IMMEDIATELY when cluster UUIDs are already known.

    Uses Insights Results Aggregator v2 ``POST /upgrade-risks-prediction`` with body
    ``{"clusters": [...]}``. Each item includes ``cluster_id``, ``prediction_status``, and
    when status is ``ok`` also ``upgrade_recommended``, ``upgrade_risks_predictors``, and
    optionally ``last_checked_at``.

    Only ``prediction_status: "ok"`` is a real assessment. Other statuses (for example
    ``"No data for the cluster"``) mean unavailable data — distinct from an explicit no-risk
    prediction (``upgrade_recommended: true`` / empty predictors). Do not treat unavailable
    data as upgrade safety. HTTP 400/403/5xx are raised as errors.
    """
    normalized = _normalize_cluster_ids(cluster_ids)
    return await run_insights_tool_request(
        mcp.insights_client.post("upgrade-risks-prediction", json={"clusters": normalized}),
        error_message=lambda exc: f"Error retrieving upgrade-risk predictions: {exc}",
    )
