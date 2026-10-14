"""Fixtures for OCP Advisor MCP tests."""

from contextlib import contextmanager
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock, patch

import pytest

from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from ocp_advisor_mcp.server import mcp
from tests.conftest import create_mock_client, llm_api_context, mcp_tools


@pytest.fixture
def ocp_advisor_mock_client() -> Mock:
    """Create a registry-backed mock InsightsClient for OCP Advisor tests."""
    return create_mock_client(api_path=mcp.api_path)


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


@pytest.fixture(scope="session")
def mcp_server_url(request):
    """Start MCP server with only the ocp-advisor toolset for LLM integration tests."""
    transport = getattr(request, "param", "http")
    if hasattr(request.node, "callspec") and "transport" in request.node.callspec.params:
        transport = request.node.callspec.params["transport"]

    server_url, server_process = start_insights_mcp_server(transport, toolset="ocp-advisor")

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)


@contextmanager
def setup_ocp_advisor_mock(
    mock_client: Mock,
    mock_response: dict[str, Any] | str | None = None,
    side_effect: BaseException | None = None,
):
    """Patch the OCP Advisor MCP client and register the /info response."""
    mock_client.api.register(
        HTTPMethod.GET,
        "info",
        response_body=mock_response,
        error=side_effect,
    )
    with patch.object(mcp, "insights_client", mock_client):
        yield


__all__ = [
    "llm_api_context",
    "mcp_server_url",
    "mcp_tools",
    "mock_info_response",
    "ocp_advisor_mock_client",
    "setup_ocp_advisor_mock",
]
