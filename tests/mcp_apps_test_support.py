"""Shared helpers for MCP Apps dashboard tool unit tests."""

from unittest.mock import AsyncMock, MagicMock

from fastmcp.tools import ToolResult


def mcp_apps_context(*, ui_supported: bool) -> MagicMock:
    """Context mock with a synchronous MCP Apps capability check."""
    ctx = MagicMock()
    ctx.client_supports_extension.return_value = ui_supported
    ctx.info = AsyncMock()
    return ctx


def tool_result_text(result: ToolResult) -> str:
    """Return the first text payload from a FastMCP ToolResult."""
    content = result.content
    if isinstance(content, list) and content:
        return getattr(content[0], "text", str(content[0]))
    return str(content)
