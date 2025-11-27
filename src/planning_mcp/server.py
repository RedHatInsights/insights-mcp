"""Red Hat Insights Planning MCP Server.

MCP server for Planning data via Red Hat Insights API.
Provides tools to get RHEL lifecycle and roadmap information.
"""

from __future__ import annotations

import logging

from fastmcp.tools.tool import Tool
from mcp.types import ToolAnnotations

from insights_mcp.mcp import InsightsMCP
from planning_mcp.tools.upcoming import get_upcoming_changes as _get_upcoming_changes


class PlanningMCP(InsightsMCP):
    """MCP server for Red Hat Insights Planning integration.

    This server provides tools for accessing RHEL lifecycle and roadmap data,
    including upcoming package changes across RHEL releases.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("PlanningMCP")

        general_intro = """You are an Insights Planning assistant that helps users understand
        and plan for RHEL lifecycle and roadmap changes using Red Hat Insights Planning data.

        You can help users:
        - See upcoming package changes (deprecations, additions, enhancements)
        - Identify what is planned for specific RHEL releases (e.g. "What is coming in RHEL 9.4?")
        - Understand RHEL lifecycle timelines for major and minor versions
        - Use lifecycle and roadmap information to plan upgrades and mitigate risk

        🚨 CRITICAL BEHAVIORAL RULES:

        🟢 **CALL IMMEDIATELY** (tools marked with green indicator):
        - get_upcoming_changes: For questions about upcoming or future package changes,
          deprecations, additions, enhancements, or roadmap plans where a full list of
          upcoming items is acceptable.

        **Note**: Each tool description includes color-coded behavioral indicators for MCP clients
                  that ignore server instructions.

        Your goal is to help users efficiently access and interpret RHEL lifecycle and
        roadmap information through the Red Hat Insights platform.

        <|function_call_library|>
        """

        super().__init__(
            name="Insights Planning MCP Server",
            toolset_name="planning",
            api_path="api/roadmap/v1",
            instructions=general_intro,
        )

    def register_tools(self) -> None:
        """Register all available tools with the MCP server."""

        tool_functions = [
            self.get_upcoming_changes,
            # Future tools to add here:
            # self.get_rhel_lifecycle,
            # self.get_appstreams_lifecycle,
            # self.get_relevant_rhel_lifecycle,
            # self.get_relevant_appstreams,
            # self.get_relevant_upcoming_changes,
        ]

        for f in tool_functions:
            tool = Tool.from_function(f)
            tool.annotations = ToolAnnotations(readOnlyHint=True, openWorldHint=True, idempotentHint=True)
            description_str = f.__doc__ or ""
            tool.description = description_str
            tool.title = description_str.split("\n", 1)[0]
            self.add_tool(tool)

    async def get_upcoming_changes(self) -> str:
        """List upcoming package changes, deprecations, additions and enhancements.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool to answer questions about upcoming package changes, deprecations,
        additions, or enhancements in the roadmap when a full list of upcoming items
        is acceptable. When the user asks about a specific RHEL version (for example,
        "What is coming in RHEL 9.4?"), call this tool without parameters and then
        filter and summarize the entries relevant to that version in your response.

        Returns:
            dict: A response object containing:
                    - meta: Metadata including 'count' and 'total'.
                    - data: A list of package records. Each record contains:
                        - name (str): The package name.
                        - type (str): The change type (e.g., 'addition').
                        - release (str): The target release version.
                        - details (dict): Detailed info including 'summary' and 'dateAdded'.
        """
        return await _get_upcoming_changes(self.insights_client, self.logger)


# Instance used by the unified Insights MCP server (`insights_mcp.server`).
mcp = PlanningMCP()
