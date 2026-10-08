"""Route registry for the reusable Insights API mock."""

from __future__ import annotations

from collections.abc import Generator, Iterable, Mapping, Sequence
from contextlib import contextmanager
from http import HTTPMethod
from typing import Any

from tests.mock_insights_api.types import (
    BodyMatcher,
    MockRequest,
    MockResponse,
    MockRoute,
    QueryMatcher,
)


class MockInsightsAPIError(Exception):
    """Base error raised by the test-only Insights API route registry."""


class UnknownRouteError(MockInsightsAPIError):
    """Raised when a request has no registered mock endpoint."""

    def __init__(self, request: MockRequest) -> None:
        self.request = request
        super().__init__(f"No Insights API mock route registered for {request.method} {request.path}")


class MockInsightsAPI:
    """Register and resolve routes for the test-only Insights API mock."""

    def __init__(self, routes: Iterable[MockRoute] | None = None, *, path_prefix: str = "") -> None:
        self._routes: dict[tuple[HTTPMethod, str], list[MockRoute]] = {}
        self._requests: list[MockRequest] = []
        self.path_prefix = path_prefix.strip("/")
        for route in routes or ():
            self._add_route(route)

    def _add_route(self, route: MockRoute) -> None:
        """Add a route to the method/path bucket."""
        key = (route.method, route.path)
        self._routes.setdefault(key, []).append(route)

    def register(  # pylint: disable=too-many-arguments
        self,
        method: HTTPMethod,
        path: str,
        *,
        query: QueryMatcher | None = None,
        body: BodyMatcher | None = None,
        response_body: Any = None,
        status: int = 200,
        headers: Mapping[str, str] | None = None,
        error: BaseException | None = None,
    ) -> MockRoute:
        """Register a route and return its immutable declaration.

        Mapping matchers are subset matches. Callable matchers receive the
        complete query mapping or decoded request body and can implement
        exact or domain-specific matching when needed.
        """
        route_path = path.lstrip("/")
        if self.path_prefix:
            route_path = f"{self.path_prefix}/{route_path}"
        route = MockRoute(
            method=method,
            path=route_path,
            query=query,
            body=body,
            response=MockResponse(
                body=response_body,
                status=status,
                headers=dict(headers or {}),
                error=error,
            ),
        )
        self._add_route(route)
        return route

    def resolve(self, request: MockRequest) -> MockResponse:
        """Resolve and record a request, failing loudly for unknown routes."""
        self._requests.append(request)
        routes = self._routes.get((request.method, request.path), ())
        for route in reversed(routes):
            if route.matches(request):
                return route.response
        raise UnknownRouteError(request)

    def routes(self) -> Sequence[MockRoute]:
        """Return the currently registered routes grouped by endpoint."""
        return [route for routes in self._routes.values() for route in routes]

    def requests(self) -> Sequence[MockRequest]:
        """Return requests received since construction or the last scope."""
        return self._requests

    @contextmanager
    def scope(self) -> Generator["MockInsightsAPI"]:
        """Temporarily isolate routes and request history for one test."""
        route_snapshot = {key: list(routes) for key, routes in self._routes.items()}
        request_snapshot = list(self._requests)
        try:
            yield self
        finally:
            self._routes = route_snapshot
            self._requests = request_snapshot

    def clear_requests(self) -> None:
        """Discard recorded requests without changing registered routes."""
        self._requests.clear()
