"""Catalog-backed route registrars for the LLM-test API mock."""

from collections.abc import Mapping
from typing import Any

from advisor_mcp.tests.advisor_mock_routes import register_advisor_routes
from content_sources_mcp.tests.content_sources_mock_routes import register_content_sources_routes
from image_builder_mcp.tests.image_builder_mock_routes import register_image_builder_routes
from inventory_mcp.tests.inventory_mock_routes import register_inventory_routes
from ocp_advisor_mcp.tests.ocp_advisor_mock_routes import register_ocp_advisor_routes
from planning_mcp.tests.planning_mock_routes import register_planning_routes
from rbac_mcp.tests.rbac_mock_routes import register_rbac_routes
from remediations_mcp.tests.remediations_mock_routes import register_remediations_routes
from rhsm_mcp.tests.rhsm_mock_routes import register_rhsm_routes
from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import MockCatalog
from tests.mock_insights_api.registry import MockInsightsAPI
from vulnerability_mcp.tests.vulnerability_mock_routes import register_vulnerability_routes


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


__all__ = ["register_all_routes"]
