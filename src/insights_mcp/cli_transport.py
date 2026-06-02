"""Stdio transport for patched fastmcp generate-cli clients."""

from __future__ import annotations

import os

from fastmcp.client.transports import StdioTransport

from insights_mcp import config

_BRAND_SERVER_CMD = {
    "insights": "insights-mcp",
    "red-hat-lightspeed": "red-hat-lightspeed-mcp",
}


def resolve_server_command() -> str:
    """Console script or override used to spawn the MCP server."""
    override = os.environ.get("INSIGHTS_MCP_SERVER_CMD")
    if override:
        return override
    brand = os.environ.get("CONTAINER_BRAND", "insights")
    return _BRAND_SERVER_CMD.get(brand, _BRAND_SERVER_CMD["insights"])


def resolve_server_argv() -> list[str]:
    """Argv for the MCP server process (transport subcommand last)."""
    argv = os.environ.get("INSIGHTS_MCP_SERVER_ARGS", "stdio").split()
    if config.all_tools_enabled() and "--all-tools" not in argv and "--readonly" not in argv:
        argv = ["--all-tools", *argv]
    return argv


def build_stdio_client_spec() -> StdioTransport:
    """Build stdio transport for the MCP server subprocess."""
    return StdioTransport(command=resolve_server_command(), args=resolve_server_argv())
