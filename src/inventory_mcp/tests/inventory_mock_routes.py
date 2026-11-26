"""Inventory API routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from http import HTTPMethod
from itertools import permutations
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import Host, MockCatalog, SystemProfile, Workspace
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.query import query_datetime, query_int, query_text, query_values
from tests.mock_insights_api.types import MockRequest, MockResponse

_DEFAULT_ORG_ID = "mock-org-00000000"
_DEFAULT_ACCOUNT = "mock-account"
_STALE_AFTER = timedelta(days=1)
_STALE_WARNING_AFTER = timedelta(hours=12)


def _workspace_record(workspace: Workspace, catalog: MockCatalog) -> dict[str, Any]:
    timestamp = catalog.reference_time.isoformat()
    return {
        "account": _DEFAULT_ACCOUNT,
        "created": timestamp,
        "id": workspace.id,
        "name": workspace.name,
        "org_id": _DEFAULT_ORG_ID,
        "ungrouped": workspace.group_type == "ungrouped-hosts",
        "updated": timestamp,
        "host_count": len(workspace.host_ids),
    }


def _system_profile_record(profile: SystemProfile, host: Host, catalog: MockCatalog) -> dict[str, Any]:
    major, _, minor = host.rhel_version.partition(".")
    repositories = catalog.repositories_for_host(host.id)
    yum_repos = [
        {
            "base_url": repository.url,
            "enabled": repository.enabled,
            "gpgcheck": True,
            "id": repository.id,
            "mirrorlist": None,
            "name": repository.name,
        }
        for repository in repositories
    ]
    return {
        "arch": profile.architecture,
        "basearch": profile.architecture,
        "cloud_provider": profile.cloud_provider,
        "host_type": "conventional",
        "installed_packages": list(profile.installed_packages),
        "operating_system": {"major": int(major), "minor": int(minor or 0), "name": "RHEL"},
        "releasever": host.rhel_version,
        "system_memory_bytes": profile.memory_bytes,
        "system_update_method": "dnf",
        "yum_repos": yum_repos,
    }


def _host_groups(host_id: str, catalog: MockCatalog) -> list[dict[str, Any]]:
    return [_workspace_record(workspace, catalog) for workspace in catalog.workspaces_for_host(host_id)]


def _workspace_hosts_factory(catalog: MockCatalog, workspace: Workspace) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        return _host_list_response(catalog, request, (catalog.host(host_id) for host_id in workspace.host_ids))

    return factory


def _host_record(host: Host, catalog: MockCatalog) -> dict[str, Any]:
    groups = _host_groups(host.id, catalog)
    workspace = groups[0] if groups else None
    stale_timestamp = catalog.reference_time - _STALE_AFTER
    stale_warning_timestamp = catalog.reference_time - _STALE_WARNING_AFTER
    return {
        "account": _DEFAULT_ACCOUNT,
        "created": host.updated.isoformat(),
        "display_name": host.hostname,
        "fqdn": host.fqdn,
        "groups": groups,
        "id": host.id,
        "last_check_in": host.last_seen.isoformat(),
        "org_id": _DEFAULT_ORG_ID,
        "reporter": host.registered_with,
        "stale_timestamp": stale_timestamp.isoformat(),
        "stale_warning_timestamp": stale_warning_timestamp.isoformat(),
        "system_profile": _system_profile_record(catalog.profile_for_host(host.id), host, catalog),
        "updated": host.updated.isoformat(),
        "workspace": workspace,
    }


def _host_staleness(host: Host, reference_time: datetime) -> str:
    age = reference_time - host.last_seen
    if age > _STALE_AFTER:
        return "stale"
    if age > _STALE_WARNING_AFTER:
        return "stale_warning"
    return "fresh"


def _host_matches(  # pylint: disable=too-many-return-statements
    host: Host, request: MockRequest, catalog: MockCatalog
) -> bool:
    text_filters = {
        "hostname_or_id": (host.id, host.hostname, host.fqdn),
        "display_name": (host.hostname,),
        "fqdn": (host.fqdn,),
        "registered_with": (host.registered_with,),
        "provider_type": (host.provider_type,),
    }
    for parameter, values in text_filters.items():
        query = query_text(request, parameter).lower()
        if query and not any(query in value.lower() for value in values):
            return False

    requested_tags = query_values(request, "tags")
    if requested_tags:
        host_tags = {tag.qualified_name.lower() for tag in catalog.tags_for_host(host.id)}
        if not all(tag.lower() in host_tags for tag in requested_tags):
            return False

    staleness = query_text(request, "staleness")
    if staleness and staleness != _host_staleness(host, catalog.reference_time):
        return False

    workspace_id = query_text(request, "workspace_id")
    if workspace_id and not any(workspace.id == workspace_id for workspace in catalog.workspaces_for_host(host.id)):
        return False

    workspace_name = query_text(request, "workspace_name").lower()
    if workspace_name and not any(
        workspace_name in workspace.name.lower() for workspace in catalog.workspaces_for_host(host.id)
    ):
        return False

    updated_start = query_datetime(request, "updated_start")
    if updated_start and host.updated <= updated_start:
        return False
    updated_end = query_datetime(request, "updated_end")
    if updated_end and host.updated >= updated_end:
        return False
    return True


def _sort_hosts(hosts: list[Host], request: MockRequest) -> list[Host]:
    order_by = query_text(request, "order_by")
    if not order_by:
        return hosts
    key = {
        "display_name": lambda host: host.hostname.lower(),
        "updated": lambda host: host.updated,
        "created": lambda host: host.updated,
    }.get(order_by)
    if key is None:
        return hosts
    return sorted(hosts, key=key, reverse=query_text(request, "order_how", "ASC").upper() == "DESC")


def _page(results: list[dict[str, Any]], request: MockRequest, *, parameter: str = "per_page") -> dict[str, Any]:
    page = max(query_int(request, "page", 1), 1)
    per_page = max(query_int(request, parameter, 10), 1)
    start = (page - 1) * per_page
    end = start + per_page
    result_page = results[start:end]
    return {
        "count": len(result_page),
        "page": page,
        "per_page": per_page,
        "results": result_page,
        "total": len(results),
    }


def _host_list_response(catalog: MockCatalog, request: MockRequest, hosts: Iterable[Host]) -> MockResponse:
    filtered = [host for host in hosts if _host_matches(host, request, catalog)]
    filtered = _sort_hosts(filtered, request)
    return MockResponse(body=_page([_host_record(host, catalog) for host in filtered], request))


def _host_ids_from_path(path: str, prefix: str) -> tuple[str, ...]:
    return tuple(item for item in path.removeprefix(prefix).split(",") if item)


def _register_host_id_routes(api: MockInsightsAPI, catalog: MockCatalog, api_path: str) -> None:
    hosts = tuple(catalog.hosts)
    for count in range(1, len(hosts) + 1):
        for host_tuple in permutations(hosts, count):
            host_ids = tuple(host.id for host in host_tuple)
            path_suffix = ",".join(host_ids)
            for resource, factory in (
                (
                    "",
                    lambda request, path_prefix=f"{api_path}/hosts/": MockResponse(
                        body={
                            "results": [
                                _host_record(catalog.host(host_id), catalog)
                                for host_id in _host_ids_from_path(request.path, path_prefix)
                            ]
                        }
                    ),
                ),
                (
                    "/system_profile",
                    lambda request, path_prefix=f"{api_path}/hosts/": MockResponse(
                        body={
                            "results": [
                                {
                                    "id": catalog.host(host_id).id,
                                    "rhsm": {"version": catalog.host(host_id).rhel_version},
                                    "system_profile": _system_profile_record(
                                        catalog.profile_for_host(host_id), catalog.host(host_id), catalog
                                    ),
                                }
                                for host_id in _host_ids_from_path(
                                    request.path.removesuffix("/system_profile"), path_prefix
                                )
                            ]
                        }
                    ),
                ),
                (
                    "/tags",
                    lambda request, path_prefix=f"{api_path}/hosts/": MockResponse(
                        body={
                            "results": {
                                host_id: [
                                    {"key": tag.key, "namespace": tag.namespace, "value": tag.value}
                                    for tag in catalog.tags_for_host(host_id)
                                ]
                                for host_id in _host_ids_from_path(request.path.removesuffix("/tags"), path_prefix)
                            }
                        }
                    ),
                ),
            ):
                api.register(HTTPMethod.GET, f"{api_path}/hosts/{path_suffix}{resource}", response_factory=factory)


def register_inventory_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/inventory/v1",
) -> None:
    """Register the Inventory endpoints exercised by current LLM scenarios."""
    api.register(
        HTTPMethod.GET,
        f"{api_path}/hosts",
        response_factory=lambda request: _host_list_response(catalog, request, catalog.hosts),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/groups",
        response_factory=lambda request: MockResponse(
            body=_page(
                [
                    _workspace_record(workspace, catalog)
                    for workspace in catalog.workspaces
                    if (
                        not query_text(request, "name") or query_text(request, "name").lower() in workspace.name.lower()
                    )
                    and (
                        query_text(request, "group_type", "all") == "all"
                        or (
                            query_text(request, "group_type", "all") == "ungrouped-hosts"
                            and workspace.group_type == "ungrouped-hosts"
                        )
                        or (
                            query_text(request, "group_type", "all") == "standard"
                            and workspace.group_type == "standard"
                        )
                    )
                ],
                request,
            )
        ),
    )
    for workspace in catalog.workspaces:
        api.register(
            HTTPMethod.GET,
            f"{api_path}/groups/{workspace.id}",
            response_body={
                "count": 1,
                "page": 1,
                "per_page": 10,
                "results": [_workspace_record(workspace, catalog)],
                "total": 1,
            },
        )
        api.register(
            HTTPMethod.GET,
            f"{api_path}/groups/{workspace.id}/hosts",
            response_factory=_workspace_hosts_factory(catalog, workspace),
        )
    _register_host_id_routes(api, catalog, api_path)
