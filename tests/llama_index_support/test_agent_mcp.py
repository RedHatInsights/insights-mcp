"""Unit tests for MCPAgentWrapper helpers."""

from tests.llama_index_support.agent_mcp import format_user_message_with_mcp_instructions


def test_format_user_message_with_mcp_instructions_empty_instructions():
    """When instructions are empty, the user message is unchanged."""
    assert format_user_message_with_mcp_instructions("List blueprints", "") == "List blueprints"
    assert format_user_message_with_mcp_instructions("List blueprints", "   ") == "List blueprints"


def test_format_user_message_with_mcp_instructions_prepends_sections():
    """MCP instructions are prepended with labeled sections before the user request."""
    formatted = format_user_message_with_mcp_instructions(
        "List blueprints",
        "Always call get_blueprints first.",
    )
    assert formatted.startswith("## MCP server instructions\n")
    assert "Always call get_blueprints first." in formatted
    assert formatted.endswith("## User request\nList blueprints")
