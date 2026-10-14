"""
Conftest for planning_mcp tests - re-exports generic MCP fixtures and
adds a PlanningMCP-specific fixture for unit tests.
"""

import pytest

from planning_mcp.server import PlanningMCP
from tests.conftest import (
    create_mcp_server,
    create_mock_client,
    llm_api_context,
    mcp_tools,
    toolset_mcp_server_url,
)
from tests.mcp_llm_eval.fixtures import test_agent, verbose_logger

mcp_server_url = toolset_mcp_server_url("planning")


@pytest.fixture
def planning_mcp_server(planning_mock_client) -> PlanningMCP:  # pylint: disable=redefined-outer-name
    """Return a fresh PlanningMCP instance for tests.

    This instance is used by tests that call PlanningMCP methods directly
    (e.g. get_upcoming_changes) without going through the FastMCP server.
    """
    server = create_mcp_server(PlanningMCP)
    server.insights_client = planning_mock_client
    return server


@pytest.fixture
def planning_mock_client():
    """Create a registry-backed mock InsightsClient for Planning tests."""
    return create_mock_client(api_path="api/roadmap/v1")


__all__ = [
    "llm_api_context",
    "mcp_server_url",
    "mcp_tools",
    "create_mcp_server",
    "create_mock_client",
    "planning_mcp_server",
    "planning_mock_client",
    "test_agent",
    "verbose_logger",
]
