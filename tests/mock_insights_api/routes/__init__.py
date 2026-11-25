"""Catalog-backed route registrars for the LLM-test API mock."""

from collections.abc import Mapping
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import MockCatalog
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.advisor import register_advisor_routes
from tests.mock_insights_api.routes.content_sources import register_content_sources_routes
from tests.mock_insights_api.routes.image_builder import register_image_builder_routes
from tests.mock_insights_api.routes.inventory import register_inventory_routes
from tests.mock_insights_api.routes.ocp_advisor import register_ocp_advisor_routes
from tests.mock_insights_api.routes.planning import register_planning_routes
from tests.mock_insights_api.routes.rbac import register_rbac_routes
from tests.mock_insights_api.routes.remediations import register_remediations_routes
from tests.mock_insights_api.routes.rhsm import register_rhsm_routes
from tests.mock_insights_api.routes.vulnerability import register_vulnerability_routes


def register_all_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    openapi_documents: Mapping[str, Mapping[str, Any]] | None = None,
) -> None:
    """Register every route currently required by the LLM-test catalog."""
    register_inventory_routes(api, catalog)
    register_vulnerability_routes(api, catalog, openapi=(openapi_documents or {}).get("vulnerability"))
    register_advisor_routes(api, catalog)
    register_remediations_routes(api, catalog)
    register_planning_routes(api, catalog)
    register_image_builder_routes(api, catalog, openapi=(openapi_documents or {}).get("image_builder"))
    register_content_sources_routes(api, catalog)
    register_rhsm_routes(api, catalog)
    register_ocp_advisor_routes(api, catalog)
    register_rbac_routes(api, catalog)


__all__ = [
    "register_advisor_routes",
    "register_all_routes",
    "register_content_sources_routes",
    "register_image_builder_routes",
    "register_inventory_routes",
    "register_ocp_advisor_routes",
    "register_planning_routes",
    "register_remediations_routes",
    "register_rbac_routes",
    "register_rhsm_routes",
    "register_vulnerability_routes",
]
