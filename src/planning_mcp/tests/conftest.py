"""
Conftest for planning_mcp tests - re-exports generic MCP fixtures and
adds a PlanningMCP-specific fixture for unit tests.
"""

import pytest

from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from planning_mcp.server import PlanningMCP
from tests.conftest import (
    create_mcp_server,
    create_mock_client,
    llm_api_context,
    mcp_tools,
)
from tests.mcp_llm_eval.fixtures import test_agent, verbose_logger


@pytest.fixture(scope="session")
def mcp_server_url(request):
    """Start MCP server with only the planning toolset for LLM integration tests."""
    transport = getattr(request, "param", "http")
    if hasattr(request.node, "callspec") and "transport" in request.node.callspec.params:
        transport = request.node.callspec.params["transport"]

    server_url, server_process = start_insights_mcp_server(transport, toolset="planning")

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)


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
