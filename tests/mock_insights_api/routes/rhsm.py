"""RHSM routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from http import HTTPMethod
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import ActivationKey, MockCatalog
from tests.mock_insights_api.registry import MockInsightsAPI


def _activation_key_record(key: ActivationKey, catalog: MockCatalog) -> dict[str, Any]:
    """Project a catalog activation key to the RHSM API response shape."""
    return {
        "id": key.id,
        "name": key.name,
        "additionalRepositories": list(key.additional_repositories),
        "updatedAt": catalog.reference_time.isoformat().replace("+00:00", "Z"),
    }


def _activation_key_detail_record(key: ActivationKey, catalog: MockCatalog) -> dict[str, Any]:
    """Project a catalog activation key to the RHSM detail response shape."""
    return {
        "body": {
            **_activation_key_record(key, catalog),
            "description": key.description,
            "serviceLevel": key.service_level,
            "role": key.role,
            "usage": key.usage,
            "releaseVersion": key.release_version,
            "subscriptions": [dict(subscription) for subscription in key.subscriptions],
        }
    }


def register_rhsm_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/rhsm/v2",
) -> None:
    """Register the activation-key endpoint used by current LLM scenarios."""
    api.register(
        HTTPMethod.GET,
        f"{api_path}/activation_keys",
        response_body={"body": [_activation_key_record(key, catalog) for key in catalog.activation_keys]},
    )
    for key in catalog.activation_keys:
        api.register(
            HTTPMethod.GET,
            f"{api_path}/activation_keys/{key.name}",
            response_body=_activation_key_detail_record(key, catalog),
        )
