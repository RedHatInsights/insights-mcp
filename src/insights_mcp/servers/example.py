"""Example MCP server."""

from typing import Any
from insights_mcp.mcp import InsightsMCP


class ExampleMCP(InsightsMCP):  # pylint: disable=abstract-method
    """Example MCP server.

    This is a simple MCP server that demonstrates the basic structure of an Insights MCP server.
    """

    def __init__(self, **kwargs):
        super().__init__(
            name="Example MCP Server",
            toolset_name="example",
            api_path="api/example/v1",
            **kwargs,
        )


mcp = ExampleMCP()


@mcp.tool()
def example_tool(_, message: str) -> str:
    """Example tool."""
    return f"Hello, {message}!"


@mcp.tool()
def get_without_auth(self) -> dict[str, Any]:
    """Send GET request to Insights API without authentication."""
    return self.insights_client.get("/endpoint", no_auth=True)


@mcp.tool()
def get_with_auth(self) -> dict[str, Any]:
    """Send GET request to Insights API with authentication."""
    return self.insights_client.get("/endpoint")


# To include this server in Insights MCP server, add the following to the server.py file:
#
# from insights_mcp.servers.example import mcp as example_mcp
# MCPS = [example_mcp]
#
# This server (toolset) can be enabled using --toolset command line argument:
#   insights-mcp --toolset=example
# or using INSIGHTS_TOOLSET environment variable:
#   INSIGHTS_TOOLSET=example
