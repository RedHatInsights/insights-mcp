"""Tests for MCP tool description helpers."""

from insights_mcp.tool_description import mcp_tool_title_from_docstring


def test_mcp_tool_title_from_docstring_first_line_only() -> None:
    doc = """Line one summary.
    Line two is still part of the tool docstring body."""
    assert mcp_tool_title_from_docstring(doc) == "Line one summary."
