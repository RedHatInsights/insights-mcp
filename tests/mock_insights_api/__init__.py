"""Reusable, test-only route definitions for the Insights API mock."""

from http import HTTPMethod

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.registry import (
    MockInsightsAPI,
    MockInsightsAPIError,
    UnknownRouteError,
)
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
]
