"""RBAC routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from http import HTTPMethod
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import MockCatalog, RBACRole
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.pagination import page_params
from tests.mock_insights_api.routes.query import query_text
from tests.mock_insights_api.types import MockRequest, MockResponse

_HELD_PERMISSIONS = (
    "inventory:hosts:read",
    "content-sources:repositories:read",
    "config-manager:activation_keys:read",
    "ocp-advisor:recommendation-results:read",
)


def _permission_record(permission: str) -> dict[str, Any]:
    return {"resourceDefinitions": [], "permission": permission}


def _application_matches(permission: str, application: str) -> bool:
    if not application:
        return True
    applications = {item.strip().casefold() for item in application.split(",") if item.strip()}
    return permission.split(":", 1)[0].casefold() in applications


def _access_response(request: MockRequest) -> MockResponse:
    application = query_text(request, "application")
    records = [
        _permission_record(permission)
        for permission in _HELD_PERMISSIONS
        if _application_matches(permission, application)
    ]
    offset, limit = page_params(request, 100, minimum_limit=0)
    end = offset + limit
    return MockResponse(
        body={
            "meta": {"count": len(records), "limit": limit, "offset": offset},
            "data": records[offset:end],
        }
    )


def _role_record(role: RBACRole, index: int) -> dict[str, Any]:
    return {
        "uuid": f"00000000-0000-4000-8000-{index:012d}",
        "name": role.name,
        "display_name": role.display_name,
        "access": [_permission_record(permission) for permission in role.permissions],
    }


def register_rbac_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/rbac/v1",
) -> None:
    """Register access and role-list endpoints used by current LLM scenarios."""
    api.register(
        HTTPMethod.GET,
        f"{api_path}/access/",
        response_factory=_access_response,
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/roles/",
        response_body={
            "meta": {"count": len(catalog.rbac_roles), "limit": len(catalog.rbac_roles), "offset": 0},
            "data": [_role_record(role, index) for index, role in enumerate(catalog.rbac_roles, start=1)],
        },
    )
