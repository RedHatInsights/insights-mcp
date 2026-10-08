"""Data types shared by the Insights API mock adapters.

This module deliberately contains no HTTP-server or ``InsightsClient`` code.
The route and response types are the neutral contract shared by the route
registry and localhost server.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http import HTTPMethod
from typing import Any, TypeAlias

Matcher: TypeAlias = Callable[[Any], bool]
QueryMatcher: TypeAlias = Mapping[str, Any] | Matcher
BodyMatcher: TypeAlias = Mapping[str, Any] | Matcher


@dataclass(frozen=True, slots=True)
class MockRequest:
    """A normalized request presented to a registered mock route."""

    method: HTTPMethod
    path: str
    query: Mapping[str, Any] = field(default_factory=dict)
    body: Any = None
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MockResponse:
    """Response declaration returned by a mock route.

    Set ``error`` when the route should simulate a failed request instead of
    returning normal response data. Each adapter decides how to expose that
    failure to the code under test.
    """

    body: Any = None
    status: int = 200
    headers: Mapping[str, str] = field(default_factory=dict)
    error: BaseException | None = None


@dataclass(frozen=True, slots=True)
class MockRoute:
    """A method/path route with optional query and body matching."""

    method: HTTPMethod
    path: str
    response: MockResponse
    query: QueryMatcher | None = None
    body: BodyMatcher | None = None

    def matches(self, request: MockRequest) -> bool:
        """Return whether this route handles *request*."""
        return (
            self.method == request.method
            and self.path == request.path
            and _matches(self.query, request.query)
            and _matches(self.body, request.body)
        )


def _matches(matcher: Mapping[str, Any] | Matcher | None, value: Any) -> bool:
    """Apply a mapping-subset or callable matcher to a request value."""
    if matcher is None:
        return True
    if callable(matcher):
        return bool(matcher(value))
    if not isinstance(value, Mapping):
        return False
    return all(key in value and value[key] == expected for key, expected in matcher.items())
