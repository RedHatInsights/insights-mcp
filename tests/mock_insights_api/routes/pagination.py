"""Pagination primitives shared by the mock API route projections."""

from __future__ import annotations

from tests.mock_insights_api.routes.query import query_int
from tests.mock_insights_api.types import MockRequest


def page_params(request: MockRequest, default_limit: int, *, minimum_limit: int = 1) -> tuple[int, int]:
    """Return a non-negative offset and a limit constrained by the route policy."""
    offset = max(query_int(request, "offset", 0), 0)
    limit = max(query_int(request, "limit", default_limit), minimum_limit)
    return offset, limit


def last_offset(total: int, limit: int) -> int:
    """Return the offset of the last page for an offset-based collection."""
    page_limit = max(limit, 1)
    return max(((max(total, 1) - 1) // page_limit) * page_limit, 0)
