"""Content Sources routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from http import HTTPMethod
from typing import Any
from urllib.parse import urlencode

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import ContentSourceRepository, MockCatalog
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.pagination import last_offset, page_params
from tests.mock_insights_api.routes.query import query_bool, query_text
from tests.mock_insights_api.types import MockRequest, MockResponse

_ACCOUNT_ID = "mock-account"
_ORG_ID = "mock-org-00000000"


def _repository_matches(repository: ContentSourceRepository, request: MockRequest) -> bool:
    for parameter, value in (("name", repository.name), ("url", repository.url)):
        requested = query_text(request, parameter).casefold()
        if requested and requested not in value.casefold():
            return False

    for parameter, value in (
        ("content_type", repository.content_type),
        ("origin", repository.origin),
        ("arch", repository.distribution_arch),
    ):
        requested = query_text(request, parameter).casefold()
        if requested and requested != value.casefold():
            return False

    requested_version = query_text(request, "version").casefold()
    versions = {version.casefold() for version in repository.distribution_versions}
    if requested_version and requested_version not in versions:
        return False

    enabled = query_bool(request, "enabled")
    return enabled is None or repository.enabled == enabled


def _repository_record(repository: ContentSourceRepository, *, details: bool) -> dict[str, Any]:
    record: dict[str, Any] = {
        "uuid": repository.id,
        "name": repository.name,
        "label": repository.label,
        "url": repository.url,
        "origin": repository.origin,
        "content_type": repository.content_type,
        "distribution_versions": list(repository.distribution_versions),
        "distribution_arch": repository.distribution_arch,
        "package_count": repository.package_count,
        "build_count": repository.build_count,
        "version_count": repository.version_count,
        "status": repository.status,
        "enabled": repository.enabled,
    }
    if details:
        record.pop("enabled")
        record.update(_repository_detail_fields(repository))
    return record


def _repository_detail_fields(repository: ContentSourceRepository) -> dict[str, Any]:
    snapshot = repository.snapshots[-1] if repository.snapshots else None
    snapshot_id = str(snapshot["id"]) if snapshot else None
    snapshot_created_at = str(snapshot["created_at"]) if snapshot else None
    snapshot_package_count = int(snapshot.get("package_count", 0)) if snapshot else 0
    snapshot_url = f"{repository.url}/snapshots/{snapshot_id}" if snapshot_id else None
    task_uuid = f"{snapshot_id}-task" if snapshot_id else None

    last_snapshot = (
        {
            "added_counts": {"packages": snapshot_package_count},
            "content_counts": {"packages": snapshot_package_count},
            "created_at": snapshot_created_at,
            "detected_os_version": repository.distribution_versions[0],
            "published": True,
            "removed_counts": {"packages": 0},
            "repository_name": repository.name,
            "repository_path": repository.url,
            "repository_uuid": repository.id,
            "url": snapshot_url,
            "uuid": snapshot_id,
        }
        if snapshot_id
        else None
    )
    last_snapshot_task = (
        {
            "created_at": snapshot_created_at,
            "ended_at": snapshot_created_at,
            "error": None,
            "object_name": repository.name,
            "object_type": "repository",
            "object_uuid": repository.id,
            "org_id": _ORG_ID,
            "status": "completed",
            "type": "snapshot",
            "uuid": task_uuid,
        }
        if snapshot_id
        else None
    )

    return {
        "account_id": _ACCOUNT_ID,
        "failed_introspections_count": int(repository.last_introspection_error is not None),
        "failed_snapshot_count": 0,
        "gpg_key": repository.gpg_key,
        "last_introspection_error": repository.last_introspection_error,
        "last_introspection_status": "error" if repository.last_introspection_error else "success",
        "last_introspection_time": repository.last_introspection_time,
        "last_snapshot": last_snapshot,
        "last_snapshot_task": last_snapshot_task,
        "last_snapshot_task_uuid": task_uuid,
        "last_snapshot_uuid": snapshot_id,
        "last_success_introspection_time": repository.last_success_introspection_time,
        "last_update_introspection_time": repository.last_update_introspection_time,
        "latest_snapshot_url": snapshot_url,
        "metadata_verification": repository.metadata_verification,
        "module_hotfixes": False,
        "org_id": _ORG_ID,
        "partner": False,
        "snapshot": bool(snapshot_id),
    }


def _repositories_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    repositories = [
        repository for repository in catalog.content_source_repositories if _repository_matches(repository, request)
    ]
    offset, limit = page_params(request, 20, minimum_limit=0)
    end = offset + limit
    final_offset = last_offset(len(repositories), limit)

    def link(link_offset: int) -> str:
        query = urlencode({"limit": limit, "offset": link_offset})
        return f"/api/content-sources/v1.0/repositories/?{query}"

    links: dict[str, str] = {"first": link(0), "last": link(final_offset)}
    if offset + limit < len(repositories):
        links["next"] = link(offset + limit)
    if offset >= limit:
        links["previous"] = link(offset - limit)

    return MockResponse(
        body={
            "meta": {"count": len(repositories), "limit": limit, "offset": offset},
            "links": links,
            "data": [_repository_record(repository, details=False) for repository in repositories[offset:end]],
        }
    )


def register_content_sources_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/content-sources/v1.0",
) -> None:
    """Register repository list and detail endpoints used by current LLM scenarios."""
    repositories_path = f"{api_path}/repositories"
    api.register(
        HTTPMethod.GET,
        f"{repositories_path}/",
        response_factory=lambda request: _repositories_response(catalog, request),
    )
    for repository in catalog.content_source_repositories:
        api.register(
            HTTPMethod.GET,
            f"{repositories_path}/{repository.id}",
            response_body=_repository_record(repository, details=True),
        )
