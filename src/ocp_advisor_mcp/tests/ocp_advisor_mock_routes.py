"""OCP Advisor routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from http import HTTPMethod
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import MockCatalog, OCPAdvisorCluster, OCPAdvisorRule
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.query import query_bool
from tests.mock_insights_api.routes.request import request_body
from tests.mock_insights_api.types import MockRequest, MockResponse


def _cluster_record(cluster: OCPAdvisorCluster) -> dict[str, Any]:
    return {
        "cluster_id": cluster.cluster_id,
        "cluster_name": cluster.cluster_name,
        "total_hits": cluster.total_hits,
        "hits_by_total_risk": dict(cluster.hits_by_total_risk),
        "managed": cluster.managed,
        "cluster_version": cluster.cluster_version,
        "last_checked_at": cluster.last_checked_at,
    }


def _rule_record(rule: OCPAdvisorRule) -> dict[str, Any]:
    return {
        "rule_id": rule.id,
        "description": rule.description,
        "generic": rule.generic,
        "publish_date": rule.publish_date,
        "total_risk": rule.total_risk,
        "impact": rule.impact,
        "likelihood": rule.likelihood,
        "resolution_risk": rule.resolution_risk,
        "tags": list(rule.tags),
        "disabled": rule.disabled,
        "impacted_clusters_count": len(rule.affected_cluster_ids),
    }


def _rule_content(rule: OCPAdvisorRule) -> dict[str, Any]:
    return {
        "status": "ok",
        "groups": [dict(group) for group in rule.groups],
        "content": {
            **_rule_record(rule),
            "reason": rule.reason,
            "resolution": rule.resolution,
            "more_info": rule.more_info,
        },
    }


def _rules_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    impacting = query_bool(request, "impacting")
    rules = [
        rule for rule in catalog.ocp_advisor_rules if impacting is None or bool(rule.affected_cluster_ids) == impacting
    ]
    return MockResponse(body={"status": "ok", "recommendations": [_rule_record(rule) for rule in rules]})


def _upgrade_risk_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    body = request_body(request)
    cluster_ids = body.get("clusters", [])
    predictions = []
    for cluster_id in cluster_ids:
        try:
            cluster = catalog.ocp_advisor_cluster(str(cluster_id))
        except KeyError:
            predictions.append({"cluster_id": cluster_id, "prediction_status": "No data for the cluster"})
            continue

        predictions.append(
            {
                "cluster_id": cluster.cluster_id,
                "prediction_status": "ok",
                "upgrade_recommended": cluster.upgrade_recommended,
                "upgrade_risks_predictors": dict(cluster.upgrade_risks_predictors),
                "last_checked_at": cluster.last_checked_at,
            }
        )
    return MockResponse(body={"status": "ok", "predictions": predictions})


def register_ocp_advisor_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/insights-results-aggregator/v2",
) -> None:
    """Register the OCP Advisor endpoints used by current LLM scenarios."""
    api.register(
        HTTPMethod.GET,
        f"{api_path}/info",
        response_body=dict(catalog.ocp_advisor_info),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/clusters",
        response_body={"clusters": [_cluster_record(cluster) for cluster in catalog.ocp_advisor_clusters]},
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/rule",
        response_factory=lambda request: _rules_response(catalog, request),
    )
    api.register(
        HTTPMethod.POST,
        f"{api_path}/upgrade-risks-prediction",
        response_factory=lambda request: _upgrade_risk_response(catalog, request),
    )
    for rule in catalog.ocp_advisor_rules:
        api.register(
            HTTPMethod.GET,
            f"{api_path}/rule/{rule.id}/content",
            response_body=_rule_content(rule),
        )
