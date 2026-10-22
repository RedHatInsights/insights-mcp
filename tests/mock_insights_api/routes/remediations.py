"""Remediations API routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from http import HTTPMethod
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import CVE, MockCatalog
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.request import request_body
from tests.mock_insights_api.types import MockRequest, MockResponse


def _cve_for_issue(catalog: MockCatalog, issue: str) -> CVE | None:
    prefix, separator, cve_id = issue.partition(":")
    if prefix != "vulnerabilities" or not separator:
        return None
    return next((cve for cve in catalog.cves if cve.id == cve_id), None)


def _resolution_risk(cve: CVE) -> int:
    if cve.cvss_score >= 9.0:
        return 4
    if cve.cvss_score >= 7.0:
        return 3
    if cve.cvss_score >= 4.0:
        return 2
    return 1


def _needs_reboot(catalog: MockCatalog, cve: CVE) -> bool:
    return any(rule.reboot_required for rule in catalog.advisor_rules if rule.id in cve.rule_ids)


def _resolutions_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    body = request_body(request)
    issues = body.get("issues", [])
    response: dict[str, Any] = {}
    for issue in issues if isinstance(issues, list) else []:
        issue_id = str(issue)
        cve = _cve_for_issue(catalog, issue_id)
        if cve is None:
            response[issue_id] = False
            continue
        risk = _resolution_risk(cve)
        response[issue_id] = {
            "id": issue_id,
            "resolution_risk": risk,
            "resolutions": [
                {
                    "description": f"Update packages affected by {cve.id}",
                    "id": "update_packages",
                    "needs_reboot": _needs_reboot(catalog, cve),
                    "resolution_risk": risk,
                }
            ],
        }
    return MockResponse(body=response)


def _remediation_id(issues: tuple[str, ...], systems: tuple[str, ...]) -> str:
    identity = "|".join(("mock-remediation", *sorted(issues), "--", *sorted(systems)))
    return str(uuid5(NAMESPACE_URL, identity))


def _remediation_create_response(request: MockRequest) -> MockResponse:
    body = request_body(request)
    add = body.get("add", {})
    add_issues = add.get("issues", []) if isinstance(add, Mapping) else []
    issues = tuple(str(item.get("id", "")) for item in add_issues if isinstance(item, Mapping))
    systems = tuple(
        str(system)
        for item in add_issues
        if isinstance(item, Mapping)
        for system in item.get("systems", [])
        if isinstance(system, str)
    )
    return MockResponse(status=201, body={"id": _remediation_id(issues, systems)})


def _remediation_request_parts(request: MockRequest) -> tuple[tuple[str, ...], tuple[str, ...]]:
    body = request_body(request)
    add = body.get("add", {})
    add_issues = add.get("issues", []) if isinstance(add, Mapping) else []
    issues = tuple(str(item.get("id", "")) for item in add_issues if isinstance(item, Mapping))
    systems = tuple(
        str(system)
        for item in add_issues
        if isinstance(item, Mapping)
        for system in item.get("systems", [])
        if isinstance(system, str)
    )
    return issues, systems


def _playbook(cves: tuple[CVE, ...], systems: tuple[str, ...]) -> str:
    cve_ids = ", ".join(cve.id for cve in cves)
    package_names = sorted({package for cve in cves for package in cve.affected_package_names})
    package_list = ", ".join(package_names)
    hosts = "\n".join(f"    - {system}" for system in systems)
    return (
        "---\n"
        f"# Mock remediation for {cve_ids}\n"
        "- name: Update vulnerable packages\n"
        "  hosts:\n"
        f"{hosts}\n"
        "  become: true\n"
        "  tasks:\n"
        "    - name: Update packages\n"
        "      ansible.builtin.dnf:\n"
        f"        name: [{package_list}]\n"
        "        state: latest\n"
    )


def _playbook_response(cves: tuple[CVE, ...], systems: tuple[str, ...]) -> MockResponse:
    return MockResponse(
        body=_playbook(cves, systems),
        headers={"Content-Type": "text/vnd.yaml"},
    )


def _playbook_factory(cves: tuple[CVE, ...], systems: tuple[str, ...]) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        _ = request
        return _playbook_response(cves, systems)

    return factory


def _remediation_create_factory(
    api: MockInsightsAPI,
    catalog: MockCatalog,
    api_path: str,
) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        response = _remediation_create_response(request)
        issues, systems = _remediation_request_parts(request)
        cves = tuple(cve for issue in issues if (cve := _cve_for_issue(catalog, issue)) is not None)
        remediation_id = response.body["id"]
        api.register(
            HTTPMethod.GET,
            f"{api_path}/remediations/{remediation_id}/playbook",
            response_factory=_playbook_factory(cves, systems),
        )
        return response

    return factory


def register_remediations_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/remediations/v1",
) -> None:
    """Register the resolution and playbook endpoints used by current LLM scenarios."""
    api.register(
        HTTPMethod.POST,
        f"{api_path}/resolutions",
        response_factory=lambda request: _resolutions_response(catalog, request),
    )
    api.register(
        HTTPMethod.POST,
        f"{api_path}/remediations",
        response_factory=_remediation_create_factory(api, catalog, api_path),
    )
