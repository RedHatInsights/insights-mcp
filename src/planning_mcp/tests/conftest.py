"""
Conftest for planning_mcp tests - re-exports generic MCP fixtures and
adds a PlanningMCP-specific fixture for unit tests.
"""

import pytest

from planning_mcp.server import PlanningMCP

# Import directly from tests since pytest now knows where to find packages
from tests.conftest import (  # pylint: disable=import-error
    mcp_server_url,
    mcp_tools,
    test_agent,
    verbose_logger,
)


@pytest.fixture
def planning_mcp_server() -> PlanningMCP:
    """Return a fresh PlanningMCP instance for tests.

    This instance is used by tests that call PlanningMCP methods directly
    (e.g. get_upcoming_changes) without going through the FastMCP server.
    """
    return PlanningMCP()


# Make the fixtures available for import
__all__ = [
    "mcp_server_url",
    "mcp_tools",
    "planning_mcp_server",
    "test_agent",
    "verbose_logger",
]
