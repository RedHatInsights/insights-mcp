"""Test the MCP API.

Test includes:
- Generic MCP server functionality and transport validation
- Blueprint pattern tests are now in module-specific test files
"""


def test_mcp_server_provides_tools(mcp_tools):
    """Test that the MCP server provides some tools."""
    assert len(mcp_tools) > 0, "MCP server should provide at least one tool"


def test_all_tools_have_metadata(mcp_tools):
    """Test that all tools have proper metadata."""
    for tool in mcp_tools:
        assert hasattr(tool, "metadata"), f"Tool {tool} missing metadata"
        assert hasattr(tool.metadata, "name"), f"Tool {tool} missing name in metadata"
        assert hasattr(tool.metadata, "description"), f"Tool {tool} missing description in metadata"
