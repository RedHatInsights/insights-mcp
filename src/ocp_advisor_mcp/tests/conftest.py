"""Fixtures for OCP Advisor MCP tests."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from ocp_advisor_mcp.server import mcp
from tests.conftest import mcp_server_url, mcp_tools, setup_toolset_mock


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


@pytest.fixture
def mock_metrics_response() -> str:
    """Sample Prometheus metrics response from Insights Results Smart Proxy."""
    return '# HELP smart_proxy_build_info Build information\nsmart_proxy_build_info{version="test"} 1\n'


def setup_ocp_advisor_mock(
    mock_client: AsyncMock,
    mock_response: dict[str, Any] | str | None = None,
    side_effect: BaseException | None = None,
):
    """Patch the OCP Advisor MCP client for tool tests."""
    return setup_toolset_mock(mcp, mock_client, mock_response, side_effect)


__all__ = [
    "mcp_server_url",
    "mcp_tools",
    "mock_info_response",
    "mock_metrics_response",
    "ocp_advisor_mock_client",
    "setup_ocp_advisor_mock",
]
