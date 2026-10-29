"""Reusable, test-only route definitions for the Insights API mock."""

from collections.abc import Mapping
from http import HTTPMethod
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import MockCatalog
from tests.mock_insights_api.registry import (
    MockInsightsAPI,
    MockInsightsAPIError,
    UnknownRouteError,
)
from tests.mock_insights_api.routes import register_all_routes
from tests.mock_insights_api.server import MockInsightsHTTPServer
from tests.mock_insights_api.types import (
    BodyMatcher,
    MockRequest,
    MockResponse,
    MockRoute,
    QueryMatcher,
    ResponseFactory,
)

__all__ = [
    "BodyMatcher",
    "DEFAULT_CATALOG",
    "HTTPMethod",
    "MockInsightsAPI",
    "MockInsightsAPIError",
    "MockInsightsHTTPServer",
    "MockRequest",
    "MockResponse",
    "MockRoute",
    "QueryMatcher",
    "ResponseFactory",
    "UnknownRouteError",
    "create_mock_insights_api",
]


def create_mock_insights_api(
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    openapi_documents: Mapping[str, Mapping[str, Any]] | None = None,
) -> MockInsightsAPI:
    """Create the default route registry backed by the coherent mock catalog."""
    api = MockInsightsAPI()
    register_all_routes(api, catalog, openapi_documents=openapi_documents)
    return api
