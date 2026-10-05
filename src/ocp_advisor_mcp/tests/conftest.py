"""Fixtures for OCP Advisor MCP tests."""

from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from ocp_advisor_mcp.server import mcp
from tests.conftest import mcp_server_url, mcp_tools


@pytest.fixture
def ocp_advisor_mock_client() -> AsyncMock:
    """Create an async mock InsightsClient for OCP Advisor tests."""
    return AsyncMock()


@pytest.fixture
def mock_info_response() -> dict[str, Any]:
    """Sample /info response from Insights Results Smart Proxy."""
    return {
        "info": {
            "SmartProxy": {"BuildVersion": "", "UtilsVersion": "v1.28.0", "status": "ok"},
            "Aggregator": {"BuildVersion": "", "status": "ok"},
            "ContentService": {"BuildVersion": "", "status": "ok"},
        },
        "status": "ok",
    }


@contextmanager
def setup_ocp_advisor_mock(
    mock_client: AsyncMock,
    mock_response: dict[str, Any] | str | None = None,
    side_effect: BaseException | None = None,
):
    """Patch the OCP Advisor MCP client's GET method."""
    if side_effect is not None:
        mock_client.get.side_effect = side_effect
    else:
        mock_client.get.return_value = mock_response
    with patch.object(mcp, "insights_client", mock_client):
        yield


__all__ = [
    "mcp_server_url",
    "mcp_tools",
    "mock_info_response",
    "ocp_advisor_mock_client",
    "setup_ocp_advisor_mock",
]
