"""Advisor API routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from http import HTTPMethod
from typing import Any
from urllib.parse import urlencode

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import AdvisorRule, Host, MockCatalog
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.pagination import last_offset, page_params
from tests.mock_insights_api.routes.query import query_bool, query_text, query_values
from tests.mock_insights_api.types import MockRequest, MockResponse

_CATEGORY_IDS = {"Availability": 1, "Security": 2, "Stability": 3, "Performance": 4}
_IMPACT_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Critical"}


def _rule_hosts(rule: AdvisorRule, catalog: MockCatalog) -> tuple[Host, ...]:
    return tuple(catalog.host(host_id) for host_id in rule.affected_host_ids)


def _rule_tags(rule: AdvisorRule, catalog: MockCatalog) -> set[str]:
    return {tag.qualified_name for host in _rule_hosts(rule, catalog) for tag in catalog.tags_for_host(host.id)}


def _rule_matches(  # pylint: disable=too-many-return-statements
    rule: AdvisorRule, request: MockRequest, catalog: MockCatalog
) -> bool:
    impacting = query_bool(request, "impacting")
    if impacting is not None and bool(rule.affected_host_ids) != impacting:
        return False

    incident = query_bool(request, "incident")
    if incident is not None and (rule.impact >= 3 and bool(rule.affected_host_ids)) != incident:
        return False

    for parameter, value in (
        ("impact", rule.impact),
        ("likelihood", min(rule.impact + 1, 4)),
        ("category", _CATEGORY_IDS.get(rule.category)),
    ):
        requested = {int(item) for item in query_values(request, parameter) if item.isdigit()}
        if requested and value not in requested:
            return False

    has_playbook = query_bool(request, "has_playbook")
    if has_playbook is not None and rule.playbook_available != has_playbook:
        return False
    reboot = query_bool(request, "reboot")
    if reboot is not None and rule.reboot_required != reboot:
        return False

    groups = {item.lower() for item in query_values(request, "groups")}
    if groups and not any(
        workspace.name.lower() in groups
        for host in _rule_hosts(rule, catalog)
        for workspace in catalog.workspaces_for_host(host.id)
    ):
        return False

    tags = {item.lower() for item in query_values(request, "tags")}
    if tags and not tags.issubset({tag.lower() for tag in _rule_tags(rule, catalog)}):
        return False

    text = query_text(request, "text").lower()
    searchable = f"{rule.id} {rule.description} {rule.category} {' '.join(_rule_tags(rule, catalog))}".lower()
    return not text or text in searchable


def _rule_record(rule: AdvisorRule, catalog: MockCatalog) -> dict[str, Any]:
    hosts = _rule_hosts(rule, catalog)
    risk_name = _IMPACT_NAMES.get(rule.impact, "Unknown")
    resolution = {
        "system_type": 105,
        "resolution": f"Apply the recommended remediation for {rule.description}",
        "resolution_risk": {"name": risk_name, "risk": min(rule.impact, 4)},
        "has_playbook": rule.playbook_available,
    }
    timestamp = catalog.reference_time.isoformat()
    return {
        "rule_id": rule.id,
        "created_at": (catalog.reference_time - timedelta(days=30)).isoformat(),
        "updated_at": timestamp,
        "description": rule.description,
        "active": True,
        "category": {"id": _CATEGORY_IDS.get(rule.category, 0), "name": rule.category},
        "impact": {"name": risk_name, "impact": rule.impact},
        "likelihood": min(rule.impact + 1, 4),
        "node_id": rule.node_id,
        "tags": " ".join(sorted(_rule_tags(rule, catalog))),
        "playbook_count": int(rule.playbook_available),
        "reboot_required": rule.reboot_required,
        "publish_date": (catalog.reference_time - timedelta(days=29)).isoformat(),
        "summary": rule.description,
        "generic": rule.description,
        "reason": f"The recommendation is reported by {len(hosts)} system(s).",
        "more_info": f"https://access.redhat.com/solutions/{rule.node_id}" if rule.node_id else "",
        "impacted_systems_count": len(hosts),
        "reports_shown": True,
        "rule_status": "enabled",
        "resolution_set": [resolution],
        "total_risk": rule.impact,
        "hosts_acked_count": 0,
        "rating": 0,
    }


def _page_links(path: str, request: MockRequest, total: int) -> dict[str, str | None]:
    offset, limit = page_params(request, 10)

    def link(link_offset: int) -> str:
        return f"/{path}?{urlencode({'limit': limit, 'offset': link_offset})}"

    final_offset = last_offset(total, limit)
    return {
        "first": link(0),
        "previous": link(max(offset - limit, 0)) if offset >= limit else None,
        "next": link(offset + limit) if offset + limit < total else None,
        "last": link(final_offset),
    }


def _sorted_rules(rules: list[AdvisorRule], request: MockRequest) -> list[AdvisorRule]:
    sort = query_values(request, "sort") or ("rule_id",)
    field = sort[0].removeprefix("-")
    key: Callable[[AdvisorRule], Any] = {
        "category": lambda rule: rule.category,
        "description": lambda rule: rule.description,
        "impact": lambda rule: rule.impact,
        "impacted_count": lambda rule: len(rule.affected_host_ids),
        "likelihood": lambda rule: min(rule.impact + 1, 4),
        "playbook_count": lambda rule: int(rule.playbook_available),
        "publish_date": lambda rule: rule.id,
        "rule_id": lambda rule: rule.id,
        "total_risk": lambda rule: rule.impact,
    }.get(field, lambda rule: rule.id)
    return sorted(rules, key=key, reverse=sort[0].startswith("-"))


def _rules_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    rules = [rule for rule in catalog.advisor_rules if _rule_matches(rule, request, catalog)]
    rules = _sorted_rules(rules, request)
    offset, limit = page_params(request, 10)
    end = offset + limit
    data = [_rule_record(rule, catalog) for rule in rules[offset:end]]
    path = "api/insights/v1/rule/"
    return MockResponse(
        body={
            "meta": {"count": len(rules)},
            "links": _page_links(path, request, len(rules)),
            "data": data,
        }
    )


def _system_detail(rule: AdvisorRule, host: Host, catalog: MockCatalog) -> dict[str, Any]:
    impact_counts = {"critical_hits": 0, "important_hits": 0, "moderate_hits": 0, "low_hits": 0}
    impact_counts[
        "critical_hits"
        if rule.impact == 4
        else "important_hits"
        if rule.impact == 3
        else "moderate_hits"
        if rule.impact == 2
        else "low_hits"
    ] = 1
    workspaces = catalog.workspaces_for_host(host.id)
    return {
        "id": host.id,
        "system_uuid": host.id,
        "display_name": host.hostname,
        "last_seen": host.last_seen.isoformat(),
        "stale_at": (host.last_seen + timedelta(days=3)).isoformat(),
        "hits": 1,
        **impact_counts,
        "incident_hits": int(rule.impact >= 3),
        "all_pathway_hits": 0,
        "pathway_filter_hits": 0,
        "tags": [
            {"namespace": tag.namespace, "key": tag.key, "value": tag.value} for tag in catalog.tags_for_host(host.id)
        ],
        "workspaces": [{"id": workspace.id, "name": workspace.name} for workspace in workspaces],
        "operating_system": {
            "major": int(host.rhel_version.split(".")[0]),
            "minor": int(host.rhel_version.split(".")[1]),
            "name": "RHEL",
        },
        "os_name": "Red Hat Enterprise Linux",
        "rhel_version": host.rhel_version,
        "group_name": workspaces[0].name if workspaces else None,
        "impacted_date": host.updated.isoformat(),
    }


def _systems_detail_response(catalog: MockCatalog, rule: AdvisorRule, request: MockRequest) -> MockResponse:
    versions = set(query_values(request, "rhel_version"))
    hosts = [host for host in _rule_hosts(rule, catalog) if not versions or host.rhel_version in versions]
    offset, limit = page_params(request, 10)
    end = offset + limit
    path = f"api/insights/v1/rule/{rule.id}/systems_detail/"
    return MockResponse(
        body={
            "meta": {"count": len(hosts)},
            "links": _page_links(path, request, len(hosts)),
            "data": [_system_detail(rule, host, catalog) for host in hosts[offset:end]],
        }
    )


def _stats_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    rules = [rule for rule in catalog.advisor_rules if _rule_matches(rule, request, catalog)]
    category: dict[str, int] = {}
    total_risk: dict[str, int] = {}
    for rule in rules:
        category[rule.category] = category.get(rule.category, 0) + 1
        risk = str(rule.impact)
        total_risk[risk] = total_risk.get(risk, 0) + 1
    return MockResponse(body={"total": len(rules), "total_risk": total_risk, "category": category})


def _kcs_response(catalog: MockCatalog, node_id: str) -> MockResponse:
    rules = [rule for rule in catalog.advisor_rules if rule.node_id == node_id]
    return MockResponse(
        body=[f"https://console.redhat.com/insights/advisor/recommendations/{rule.id}" for rule in rules]
    )


def _detail_factory(catalog: MockCatalog, rule: AdvisorRule) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        _ = request
        return MockResponse(body=_rule_record(rule, catalog))

    return factory


def _systems_factory(rule: AdvisorRule) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        _ = request
        return MockResponse(body={"host_ids": list(rule.affected_host_ids)})

    return factory


def _kcs_factory(catalog: MockCatalog, node_id: str) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        _ = request
        return _kcs_response(catalog, node_id)

    return factory


def _systems_detail_factory(catalog: MockCatalog, rule: AdvisorRule) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        return _systems_detail_response(catalog, rule, request)

    return factory


def register_advisor_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/insights/v1",
) -> None:
    """Register Advisor endpoints used by current LLM scenarios."""
    api.register(
        HTTPMethod.GET,
        f"{api_path}/rule/",
        response_factory=lambda request: _rules_response(catalog, request),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/stats/rules/",
        response_factory=lambda request: _stats_response(catalog, request),
    )
    for rule in catalog.advisor_rules:
        api.register(
            HTTPMethod.GET,
            f"{api_path}/rule/{rule.id}/",
            response_factory=_detail_factory(catalog, rule),
        )
        api.register(
            HTTPMethod.GET,
            f"{api_path}/rule/{rule.id}/systems/",
            response_factory=_systems_factory(rule),
        )
        api.register(
            HTTPMethod.GET,
            f"{api_path}/rule/{rule.id}/systems_detail/",
            response_factory=_systems_detail_factory(catalog, rule),
        )
        if rule.node_id is not None:
            api.register(
                HTTPMethod.GET,
                f"{api_path}/kcs/{rule.node_id}/",
                response_factory=_kcs_factory(catalog, rule.node_id),
            )
