"""Create the catalog-backed Insights API mock."""

from collections.abc import Mapping
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import MockCatalog
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.registration import register_all_routes


def create_mock_insights_api(
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    openapi_documents: Mapping[str, Mapping[str, Any]] | None = None,
) -> MockInsightsAPI:
    """Create the default route registry backed by the coherent mock catalog."""
    api = MockInsightsAPI()
    register_all_routes(api, catalog, openapi_documents=openapi_documents)
    return api
