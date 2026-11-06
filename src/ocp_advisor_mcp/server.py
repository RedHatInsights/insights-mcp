"""Red Hat Insights OCP Advisor MCP Server.

MCP server for OCP Advisor data via the Insights Results Smart Proxy API.
Provides tools to get OpenShift Advisor information from Red Hat Insights.
"""

from __future__ import annotations

import re
from typing import Annotated, Any

from pydantic import Field

from insights_mcp.errors import InsightsApiError
from insights_mcp.mcp import InsightsMCP
from tools.common import run_insights_tool_request

# Smart Proxy rejects multi-cluster upgrade-risk requests above this size.
_MAX_UPGRADE_RISK_CLUSTERS = 100
_DEFAULT_RULE_LIST_LIMIT = 20
_MAX_RULE_LIST_LIMIT = 100
_RULE_ID_PATTERN = re.compile(r"^([a-zA-Z_0-9.]+)[|]([a-zA-Z_0-9.]+)$")

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


def _normalize_rule_id(rule_id: str) -> str:
    """Strip and validate a Smart Proxy composite rule ID."""
    if not isinstance(rule_id, str):
        raise InsightsApiError("rule_id must be a string in format rule.module|ERROR_KEY")

    normalized = rule_id.strip()
    if not normalized or not _RULE_ID_PATTERN.match(normalized):
        raise InsightsApiError("rule_id must be a non-empty string in format rule.module|ERROR_KEY")
    return normalized


def _normalize_rule_list_bounds(limit: int, offset: int) -> tuple[int, int]:
    """Validate and normalize local rule-list pagination bounds."""
    if limit < 1 or limit > _MAX_RULE_LIST_LIMIT:
        raise InsightsApiError(f"limit must be between 1 and {_MAX_RULE_LIST_LIMIT}, got {limit}")
    if offset < 0:
        raise InsightsApiError(f"offset must be greater than or equal to 0, got {offset}")
    return limit, offset


def _slice_rule_list_response(
    response: dict[str, Any] | str | list[Any],
    *,
    limit: int,
    offset: int,
) -> dict[str, Any] | str | list[Any]:
    """Apply MCP-level pagination to the Smart Proxy recommendation list response."""
    if not isinstance(response, dict) or not isinstance(response.get("recommendations"), list):
        return response

    recommendations = response["recommendations"]
    total = len(recommendations)
    sliced_response = dict(response)
    end = offset + limit
    sliced_response["recommendations"] = recommendations[offset:end]
    sliced_response["meta"] = {
        "count": len(sliced_response["recommendations"]),
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_next": end < total,
        "has_previous": offset > 0,
        "pagination_note": (
            "The Smart Proxy /rule endpoint does not provide native pagination; "
            "limit and offset are applied by the MCP tool after retrieving the rule list."
        ),
    }
    return sliced_response


def _mark_rule_content_response(response: dict[str, Any] | str | list[Any]) -> dict[str, Any] | str | list[Any]:
    """Annotate rule content responses as generic static content."""
    if not isinstance(response, dict):
        return response

    marked_response = dict(response)
    marked_response["content_type"] = "generic_static_rule_content"
    marked_response["content_note"] = (
        "This is generic rule content from Smart Proxy /rule/{ruleId}/content. It is not a rendered, "
        "cluster-specific finding; use cluster/namespace recommendation tools for rendered findings."
    )
    return marked_response


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
async def list_rules(
    impacting: Annotated[
        bool | None,
        Field(
            description=(
                "Optional Smart Proxy impacting filter. Omit to list all available rules; true lists only rules "
                "currently impacting clusters; false lists rules that are not currently impacting clusters."
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description=(
                "Maximum number of rules to return after MCP-side slicing. Range 1-100. Default 20. "
                "The upstream /rule endpoint has no native pagination."
            ),
            ge=1,
            le=_MAX_RULE_LIST_LIMIT,
        ),
    ] = _DEFAULT_RULE_LIST_LIMIT,
    offset: Annotated[
        int,
        Field(
            description=(
                "Zero-based rule offset for MCP-side slicing. Default 0. "
                "The upstream /rule endpoint has no native pagination."
            ),
            ge=0,
        ),
    ] = 0,
) -> str:
    """List available OCP Advisor rules and recommendation metadata.

    🟢 CALL IMMEDIATELY - No information gathering required.

    Uses Insights Results Smart Proxy v2 ``GET /rule``. Returned rule identifiers are
    composite IDs such as ``ccx_rules_ocp.external.rules.example.report|ERROR_KEY`` and
    are suitable for ``get_rule_content``. Each recommendation can include title/description,
    generic text, publication date, risk/impact/likelihood, tags, disabled state, and impacted
    cluster counts.

    The upstream endpoint does not expose native pagination. ``limit`` and ``offset`` are
    documented MCP-side collection bounds applied after retrieving the list. Unknown upstream
    failures, authorization failures, and malformed ``impacting`` values are raised as errors;
    failed retrieval is not returned as an empty successful list.
    """
    normalized_limit, normalized_offset = _normalize_rule_list_bounds(limit, offset)
    params = {"impacting": impacting} if impacting is not None else None
    return await run_insights_tool_request(
        mcp.insights_client.get("rule", params=params),
        error_message=lambda exc: f"Error listing OCP Advisor rules: {exc}",
        response_transform=lambda response: _slice_rule_list_response(
            response,
            limit=normalized_limit,
            offset=normalized_offset,
        ),
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def get_rule_content(
    rule_id: Annotated[
        str,
        Field(
            description=(
                "Composite OCP Advisor rule identifier in format rule.module|ERROR_KEY. "
                "Use the rule_id/check returned by list_rules or by OCP Advisor/DVO recommendation results."
            ),
        ),
    ],
) -> str:
    """Get generic static content for one OCP Advisor or DVO-backed rule.

    🟢 CALL IMMEDIATELY when rule_id is already known.

    Uses Insights Results Smart Proxy v2 ``GET /rule/{ruleId}/content``. The response is generic,
    cluster-independent static content: title/description, generic description, reason, resolution,
    more_info/documentation links, total risk, impact, likelihood, publish date, tags, and groups.

    This tool intentionally does not return cluster-specific rendered findings or DVO object details.
    Recommendation/report tools remain responsible for presenting rendered cluster or namespace details.
    If static content for a DVO or other source rule is unavailable, the upstream 404/503 is surfaced
    explicitly instead of being treated as an empty successful result.
    """
    normalized_rule_id = _normalize_rule_id(rule_id)
    return await run_insights_tool_request(
        mcp.insights_client.get(f"rule/{normalized_rule_id}/content"),
        error_message=lambda exc: f"Error retrieving OCP Advisor rule content for {normalized_rule_id}: {exc}",
        response_transform=_mark_rule_content_response,
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
