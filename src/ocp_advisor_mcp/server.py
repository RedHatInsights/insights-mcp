"""Red Hat Insights OCP Advisor MCP Server.

MCP server for OCP Advisor data via the Insights Results Smart Proxy API.
Provides tools to get OpenShift Advisor information from Red Hat Insights.
"""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import UUID

from pydantic import Field

from insights_mcp.errors import InsightsApiError
from insights_mcp.mcp import InsightsMCP
from ocp_advisor_mcp.rendering import (
    ADVISOR_TEMPLATE_FIELDS,
    apply_rendering_status,
    render_recommendation_fields,
)
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


def _render_advisor_report(
    response: dict[str, Any] | str | list[Any],
) -> dict[str, Any] | str | list[Any]:
    """Render the DoT.js template fields of every rule hit in an Advisor report."""
    response = cast(dict[str, Any], response)
    for hit in response["report"]["data"]:
        # The smart-proxy report puts the per-hit template data (``pydata``
        # values) in ``extra_data``; the ``details`` field is static prose.
        rendered, errors = render_recommendation_fields(
            hit, hit.get("extra_data") or {}, fields=ADVISOR_TEMPLATE_FIELDS
        )
        hit.update(rendered)
        apply_rendering_status(hit, errors)
    return response


def _render_dvo_recommendations(
    response: dict[str, Any] | str | list[Any],
) -> dict[str, Any] | str | list[Any]:
    """Render the DoT.js template fields of every DVO recommendation."""
    response = cast(dict[str, Any], response)
    for recommendation in response["recommendations"]:
        rendered, errors = render_recommendation_fields(
            recommendation, recommendation.get("extra_data") or {}
        )
        recommendation.update(rendered)
        apply_rendering_status(recommendation, errors)
    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def get_recommendations(
    cluster_id: Annotated[UUID, Field(description="Cluster UUID, e.g. from list_clusters")],
    include_disabled: Annotated[bool, Field(description="Include disabled recommendations")] = False,
) -> str:
    """Get Insights Advisor recommendations (rule hits) for a cluster, with rendered details.

    🔴 GATHER INFO FIRST - Use a supplied cluster UUID or find one with list_clusters.

    Returns cluster metadata, rule hits, risk levels, and cluster-specific guidance.
    Set include_disabled=true to include disabled recommendations.
    Fields that fail to render retain template text and are flagged by
    ``rendering: {"status": "failed"}``; do not treat them as rendered guidance.
    """
    cluster = str(cluster_id)
    params: dict[str, Any] | None = {"get_disabled": "true"} if include_disabled else None
    return await run_insights_tool_request(
        mcp.insights_client.get(f"cluster/{cluster}/reports", params=params),
        error_message=lambda exc: f"Error retrieving recommendations for cluster {cluster}: {exc}",
        response_transform=_render_advisor_report,
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def get_dvo_namespaces() -> str:
    """List DVO workload namespaces with recommendation counts and severities.

    🟢 CALL IMMEDIATELY - No information gathering required.

    Returns cluster and namespace UUIDs with recommendation counts and severity summaries.
    Use the UUIDs with get_dvo_recommendations.
    """
    return await run_insights_tool_request(
        mcp.insights_client.get("namespaces/dvo"),
        error_message=lambda exc: f"Error listing DVO namespaces: {exc}",
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def get_dvo_recommendations(
    cluster_id: Annotated[UUID, Field(description="Cluster UUID from get_dvo_namespaces")],
    namespace_id: Annotated[UUID, Field(description="Namespace UUID from get_dvo_namespaces")],
) -> str:
    """Get DVO workload recommendations for a cluster namespace, with rendered details.

    🔴 GATHER INFO FIRST - Use supplied cluster and namespace UUIDs or find them with get_dvo_namespaces.

    Returns workload findings, risk levels, affected objects, and rendered guidance.
    Fields that fail to render retain template text and are flagged by
    ``rendering: {"status": "failed"}``; do not treat them as rendered guidance.
    """
    cluster = str(cluster_id)
    namespace = str(namespace_id)
    return await run_insights_tool_request(
        mcp.insights_client.get(f"namespaces/dvo/{namespace}/cluster/{cluster}"),
        error_message=lambda exc: (
            f"Error retrieving DVO recommendations for namespace {namespace} "
            f"of cluster {cluster}: {exc}"
        ),
        response_transform=_render_dvo_recommendations,
    )
