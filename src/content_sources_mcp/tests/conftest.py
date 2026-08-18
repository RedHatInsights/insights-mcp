"""Conftest for content_sources_mcp tests."""

import pytest
from mcp_llm_eval.fixtures import test_agent, verbose_logger

from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from tests.conftest import (
    llm_api_context,
    mcp_tools,
)

__all__ = [
    "llm_api_context",
    "mcp_server_url",
    "mcp_tools",
    "test_agent",
    "verbose_logger",
]


@pytest.fixture(scope="session")
def mcp_server_url(request):
    """Start MCP server with only the content-sources toolset for LLM integration tests."""
    transport = getattr(request, "param", "http")
    if hasattr(request.node, "callspec") and "transport" in request.node.callspec.params:
        transport = request.node.callspec.params["transport"]

    server_url, server_process = start_insights_mcp_server(transport, toolset="content-sources")

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)
