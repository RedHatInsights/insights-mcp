"""Fixtures for OCP Advisor MCP tests."""

from typing import Any
from unittest.mock import Mock

import pytest

from ocp_advisor_mcp.server import mcp
from tests.conftest import create_mock_client, llm_api_context, mcp_tools, toolset_mcp_server_url
from tests.mcp_llm_eval.fixtures import test_agent, verbose_logger


mcp_server_url = toolset_mcp_server_url("ocp-advisor")


@pytest.fixture
def ocp_advisor_mock_client(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Create a registry-backed mock InsightsClient for OCP Advisor tests."""
    client = create_mock_client(api_path=mcp.api_path)
    monkeypatch.setattr(mcp, "insights_client", client)
    return client


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



__all__ = [
    "llm_api_context",
    "mcp_server_url",
    "mcp_tools",
    "mock_info_response",
    "ocp_advisor_mock_client",
    "test_agent",
    "verbose_logger",
]
