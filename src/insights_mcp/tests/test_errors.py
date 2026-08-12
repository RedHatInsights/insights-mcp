"""Tests for InsightsClientBase error message handling."""

import httpx
import pytest

from insights_mcp.client import InsightsClientBase
from insights_mcp.config import INSIGHTS_BASE_URL


@pytest.mark.parametrize("status_code", [401, 403, 500])
def test_response_body_preserved(status_code: int) -> None:
    """Error message includes the HTTP response body."""
    body = "detailed and important error from backend"
    client = InsightsClientBase(base_url=INSIGHTS_BASE_URL)
    request = httpx.Request("POST", "https://example.com/api/v1/compose")
    response = httpx.Response(status_code, text=body, request=request)
    error = httpx.HTTPStatusError("error", request=request, response=response)

    assert body in client.get_error_message(error)
