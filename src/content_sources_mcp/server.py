"""Red Hat Insights Content Sources MCP Server.

MCP server for content sources data via Red Hat Insights API.
Provides tools to get repository information from content sources.
"""

import json
import logging
from typing import Any

from fastmcp.tools.tool import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.mcp import InsightsMCP


class ContentSourcesMCP(InsightsMCP):
    """MCP server for Red Hat Content Sources integration.

    This server provides tools for accessing and managing content sources
    and repositories in Red Hat Insights.
    """

    def __init__(self):
        self.logger = logging.getLogger("ContentSourcesMCP")

        general_intro = """You are a Content Sources assistant that helps users access and manage
        repository information from Red Hat Insights Content Sources.

        You can help users:
        - List repositories with various filtering options
        - Search for specific repositories by name, URL, or content type
        - Filter repositories by architecture, version, origin, or enabled status
        - Get paginated results for large repository lists

        🚨 CRITICAL BEHAVIORAL RULES:

        🟢 **CALL IMMEDIATELY** (tools marked with green indicator):
        - list_repositories: For queries like "List my repositories", "Show repositories", etc.

        **Note**: Each tool description includes color-coded behavioral indicators for MCP clients
                  that ignore server instructions.

        Your goal is to help users efficiently access and filter their content sources
        repository information through the Red Hat Insights platform.

        <|function_call_library|>

        """

        super().__init__(
            name="Insights Content Sources MCP Server",
            toolset_name="content-sources",
            api_path="api/content-sources/v1.0",
            instructions=general_intro,
        )

    def register_tools(self):
        """Register all available tools with the MCP server."""
        tool_functions = [
            self.list_repositories,
        ]

        for f in tool_functions:
            tool = Tool.from_function(f)
            tool.annotations = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
            description_str = f.__doc__
            tool.description = description_str
            tool.title = description_str.split("\n", 1)[0]
            self.add_tool(tool)

    async def list_repositories(
        self,
        limit: int = Field(default=10, description="Maximum number of repositories to return (default: 10)."),
        offset: int = Field(default=0, description="Number of repositories to skip for pagination (default: 0)."),
        name: str = Field(default="", description="Filter by repository name (case-insensitive)."),
        url: str = Field(default="", description="Filter by repository URL (case-insensitive)."),
        content_type: str = Field(default="", description="Filter by content type (e.g., 'rpm', 'ostree')."),
        origin: str = Field(default="", description="Filter by origin (e.g., 'red_hat', 'external')."),
        enabled: bool = Field(default=None, description="Filter by enabled status (True/False)."),
        arch: str = Field(default="", description="Filter by architecture (e.g., 'x86_64', 'aarch64')."),
        version: str = Field(default="", description="Filter by version (e.g., '8', '9')."),
    ) -> str:
        """List repositories with filtering and pagination options.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Args:
            limit: Maximum number of repositories to return (default: 10).
            offset: Number of repositories to skip for pagination (default: 0).
            name: Filter by repository name (case-insensitive).
            url: Filter by repository URL (case-insensitive).
            content_type: Filter by content type (e.g., 'rpm', 'ostree').
            origin: Filter by origin (e.g., 'red_hat', 'external').
            enabled: Filter by enabled status (True/False).
            arch: Filter by architecture (e.g., 'x86_64', 'aarch64').
            version: Filter by version (e.g., '8', '9').
        """
        # Use self.insights_client directly

        params: dict[str, Any] = {}

        if name:
            params["name"] = name
        if url:
            params["url"] = url
        if content_type:
            params["content_type"] = content_type
        if origin:
            params["origin"] = origin
        if enabled is not None:
            params["enabled"] = enabled
        if arch:
            params["arch"] = arch
        if version:
            params["version"] = version

        params["limit"] = limit
        params["offset"] = offset

        try:
            response = await self.insights_client.get("repositories/", params=params)
            if isinstance(response, str):
                return response
            return json.dumps(response)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error listing repositories: {str(e)}"


mcp = ContentSourcesMCP()
