"""FastMCP CLI entrypoint for ``fastmcp list`` / ``fastmcp run``.

Exposes the unified Insights MCP server as module-level ``server`` (auto-discovered
by FastMCP alongside ``mcp`` and ``app``).

Examples::

    fastmcp list src/insights_mcp/server_cli.py
    fastmcp list src/insights_mcp/server_cli.py:server
    INSIGHTS_MCP_ALL_TOOLS=true fastmcp list src/insights_mcp/server_cli.py

Toolset and readonly defaults follow ``INSIGHTS_TOOLSET`` / ``LIGHTSPEED_TOOLSET`` and
``INSIGHTS_MCP_ALL_TOOLS`` / ``LIGHTSPEED_MCP_ALL_TOOLS`` when not passed on the CLI.
"""

from insights_mcp.server import build_insights_mcp_server

server = build_insights_mcp_server()
