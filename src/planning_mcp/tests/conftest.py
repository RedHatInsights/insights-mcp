"""
Conftest for planning_mcp tests - re-exports generic MCP fixtures and
adds a PlanningMCP-specific fixture for unit tests.
"""

import pytest
from mcp_llm_eval.fixtures import verbose_logger

from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from planning_mcp.server import PlanningMCP
from tests.conftest import (
    llm_api_context,
    mcp_tools,
    test_agent,
)


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
def planning_mcp_server() -> PlanningMCP:
    """Return a fresh PlanningMCP instance for tests.

    This instance is used by tests that call PlanningMCP methods directly
    (e.g. get_upcoming_changes) without going through the FastMCP server.
    """
    return PlanningMCP()


__all__ = [
    "llm_api_context",
    "mcp_server_url",
    "mcp_tools",
    "planning_mcp_server",
    "test_agent",
    "verbose_logger",
]
