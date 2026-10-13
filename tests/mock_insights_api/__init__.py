"""Reusable, test-only route definitions for the Insights API mock."""

from http import HTTPMethod

from tests.mock_insights_api.registry import (
    MockInsightsAPI,
    MockInsightsAPIError,
    UnknownRouteError,
)
from tests.mock_insights_api.types import (
    BodyMatcher,
    MockRequest,
    MockResponse,
    MockRoute,
    QueryMatcher,
)

__all__ = [
    "BodyMatcher",
    "HTTPMethod",
    "MockInsightsAPI",
    "MockInsightsAPIError",
    "MockRequest",
    "MockResponse",
    "MockRoute",
    "QueryMatcher",
    "UnknownRouteError",
]
