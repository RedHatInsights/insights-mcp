"""Tests for OCP Advisor MCP server configuration."""

from ocp_advisor_mcp.server import mcp


def test_ocp_advisor_mcp_configuration() -> None:
    """The OCP Advisor toolset uses the expected public name and API path."""
    assert mcp.toolset_name == "ocp-advisor"
    assert mcp.api_path == "api/insights-results-aggregator/v2"
