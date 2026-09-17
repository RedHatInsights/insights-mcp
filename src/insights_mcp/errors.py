"""Shared exception types for Insights MCP."""

from fastmcp.exceptions import ToolError


class InsightsApiError(ToolError):
    """Raised when an Insights API call or auth setup fails.

    Subclassing ``ToolError`` ensures FastMCP sets ``isError: true`` on the
    MCP ``CallToolResult`` while preserving the formatted error message for agents.
    """
