"""Request helpers shared by the mock API route projections."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tests.mock_insights_api.types import MockRequest


def request_body(request: MockRequest) -> Mapping[str, Any]:
    """Return the request body when it is a mapping, otherwise an empty one."""
    return request.body if isinstance(request.body, Mapping) else {}
