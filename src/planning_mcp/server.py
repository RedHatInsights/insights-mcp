"""Red Hat Insights Planning MCP Server.

MCP server for Planning data via Red Hat Insights API.
Provides tools to get RHEL lifecycle and roadmap information.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Callable

from fastmcp.tools.tool import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.mcp import InsightsMCP
from planning_mcp.tools.appstreams import get_appstreams_lifecycle as _get_appstreams_lifecycle
from planning_mcp.tools.relevant_appstreams import get_relevant_appstreams as _get_relevant_appstreams
from planning_mcp.tools.relevant_upcoming import get_relevant_upcoming_changes as _get_relevant_upcoming_changes
from planning_mcp.tools.rhel_lifecycle import get_rhel_lifecycle as _get_rhel_lifecycle
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

        ⚠️ **NEVER USE TRAINING DATA FOR RHEL VERSION INFORMATION**:
        - Your training data about RHEL releases may be outdated.
        - ALWAYS call the appropriate tool first and base your response ONLY on the returned data.
        - If a tool returns data for a RHEL version (e.g., RHEL 10), that version exists
          in the system regardless of what your training data says.
        - Do NOT say a version "is not released" or "does not exist" unless the tool
          explicitly returns no data for that version.

        **Note**: Each tool description includes color-coded behavioral indicators for MCP clients
                  that ignore server instructions.

        Your goal is to help users efficiently access and interpret RHEL lifecycle and
        roadmap information through the Red Hat Insights platform.
        """

        super().__init__(
            name="Insights Planning MCP Server",
            toolset_name="planning",
            api_path="api/roadmap/v1",
            instructions=general_intro,
        )

    def register_tools(self) -> None:
        """Register all available tools with the MCP server."""

        # Explicit type annotation ensures Tool.from_function passes mypy validation for callable signatures.
        tool_functions: list[Callable[..., Any]] = [
            self.get_upcoming_changes,
            self.get_appstreams_lifecycle,
            self.get_rhel_lifecycle,
            self.get_relevant_upcoming_changes,
            self.get_relevant_appstreams,
            # Future tools to add here:
            # self.get_relevant_rhel_lifecycle,
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

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def get_appstreams_lifecycle(
        self,
        mode: Annotated[
            str,
            Field(
                default="raw",
                description=(
                    "Mode for Application Streams lifecycle: 'raw' (per-major) or 'streams' (cross-major overview)."
                ),
            ),
        ] = "raw",
        major: Annotated[
            str,
            Field(
                default="",
                description="RHEL major version (e.g. '8', '9', '10'). Required when mode='raw'.",
            ),
        ] = "",
        name: Annotated[
            str,
            Field(
                default="",
                description="Module or package technical name filter (e.g. 'aspnetcore-runtime-7.0', 'postgresql').",
            ),
        ] = "",
        application_stream_name: Annotated[
            str,
            Field(
                default="",
                description="Human-friendly stream name (e.g. '.NET 7', 'PostgreSQL 16', '1.24').",
            ),
        ] = "",
        application_stream_type: Annotated[
            str,
            Field(
                default="",
                description='Application stream type (e.g. "module" or "package").',
            ),
        ] = "",
        kind: Annotated[
            str,
            Field(
                default="",
                description='Backend kind filter, e.g. "dnf_module" or "package".',
            ),
        ] = "",
    ) -> str:
        """Get Application Streams lifecycle information.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool when the user asks about Application Streams lifecycle
        (modules or packages) or wants to understand what streams exist for
        specific RHEL versions.

        Guidance:
        - For detailed lifecycle of modules/packages on a specific RHEL major,
          use mode="raw" and set 'major'.
        - For an overview across RHEL generations (e.g. "what nginx streams
          exist in 8/9/10"), use mode="streams".
        - When the user mentions a human-friendly stream name like ".NET 7",
          use 'application_stream_name'.
        - When the user mentions the technical module/package name, use 'name'.
        - Only use 'kind' when the user explicitly distinguishes between module
          and package implementations.

        Returns:
            str: A JSON-encoded response object containing:
                 - meta: Metadata including:
                     - count (int): Number of records returned in this page.
                     - total (int): Total number of matching records.
                 - data: A list of Application Stream lifecycle records. Each
                   record typically contains:
                     - name (str): Technical package or module name
                       (e.g. 'aspnetcore-runtime-8.0').
                     - display_name (str): Human-friendly display name
                       (e.g. '.NET 8').
                     - application_stream_name (str): Application Stream name
                       (e.g. '.NET 8', 'PostgreSQL 16', 'container-tools').
                     - application_stream_type (str | null): Stream type
                       label (e.g. 'Application Stream',
                       'Full Life Application Stream',
                       'Rolling Application Stream').
                     - stream (str): Stream identifier or version
                       (e.g. '8.0.13', '1.24', '1.14.0').
                     - start_date (str | null): Planned start date for the
                       stream, in ISO format (YYYY-MM-DD).
                     - end_date (str | null): Planned end-of-life date for
                       the stream, in ISO format (YYYY-MM-DD).
                     - impl (str): Implementation kind
                       (e.g. 'package' or 'dnf_module').
                     - initial_product_version (str | null): First RHEL
                       product version where this stream is available
                       (e.g. '9.4', '10.0').
                     - support_status (str): Calculated support status
                       (e.g. 'Supported', 'Near retirement', 'Retired').
                     - os_major (int | null): RHEL major version
                       (e.g. 8, 9, 10).
                     - os_minor (int | null): RHEL minor version
                       where the stream first appears (e.g. 0, 4).
                     - lifecycle (dict | null): Reserved for additional
                       lifecycle metadata (may be null).
                     - rolling (bool): Indicates whether this is a rolling
                       Application Stream (True) or a fixed-lifecycle stream
                       (False).

        """
        # Map empty strings to None so the helper doesn't send empty query params.
        _major = major or None
        _name = name or None
        _as_name = application_stream_name or None
        _as_type = application_stream_type or None
        _kind = kind or None

        return await _get_appstreams_lifecycle(
            insights_client=self.insights_client,
            mode=mode,
            major=_major,
            name=_name,
            application_stream_name=_as_name,
            application_stream_type=_as_type,
            kind=_kind,
            logger=self.logger,
        )

    async def get_rhel_lifecycle(self) -> str:
        """Returns life cycle dates for all RHEL majors and minors.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool when the user asks for RHEL versions and lifecycle timelines, including major versions,
        minor versions, or extended support types (EUS/E4S/ELS).

        For "major-only" versions and timelines (for example, "RHEL 8 lifecycle overview"), call this tool and then
        focus on rows where minor is null. Filtering is performed by you, not the MCP tool.

        For a specific minor (for example, "RHEL 9.2 EUS lifecycle"), call this tool and then
        focus on entries matching the requested major and minor. Interpretation of date windows or version
        selection is done by you.

        When the user mentions dates or "expiring within N days", call this tool and interpret
        the start_date / end_date values to identify relevant versions. Interpretation of date windows or version
        selection is done by you.

        Returns:
            dict: A response object containing:
                    - data: A list of RHEL lifecycle records
                        - name (str): System name
                        - start_date (str): Start date of support
                        - end_date (str): End date of standard support
                        - support_status (str): Status of support, e.g. retired, upcoming_release, supported
                        - display_name (str): How the system should be presented to the customer
                        - major (int): Major system version
                        - minor (int): Minor system version
                        - end_date_e4s (str | null): End date of Update Services for SAP Solutions support
                        - end_date_els (str | null): End date of Extended Life-cycle Support
                        - end_date_eus (str | null): End date of Extended Update Support
        """
        return await _get_rhel_lifecycle(self.insights_client, self.logger)

    async def get_relevant_upcoming_changes(
        self,
        major: Annotated[
            str,
            Field(
                default="",
                description="Restricts relevance evaluation to systems running this RHEL major version.",
            ),
        ] = "",
        minor: Annotated[
            str,
            Field(
                default="",
                description=(
                    "Used together with major to further restrict relevance evaluation "
                    "to a specific minor version. Requires major to be specified."
                ),
            ),
        ] = "",
    ) -> str:
        """List relevant upcoming package changes, deprecations, additions and enhancements to user's systems .

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool to answer questions about upcoming package changes, deprecations,
        additions, or enhancements in the roadmap filtered by relevance to the user's systems.
        Also to plan for future upgrades and mitigate risk.
        Use this tool over get_upcoming_changes when the user asks about upcoming changes for their systems.

        Returns:
            dict: A response object containing:
                    - meta: Metadata including 'count' and 'total'. A count of 0 means
                            no packages matches for the user's systems.
                    - data: A list of package records. Each record contains:
                        - name (str): The package name.
                        - type (str): The change type (e.g., 'addition').
                        - release (str): The target release version.
                        - details (dict): Detailed info including 'summary' and 'dateAdded'.
                        - potentiallyAffectedSystemsDetail (list): Systems that might be
                          affected by this change, including system IDs, display names,
                          and OS versions.
        """
        return await _get_relevant_upcoming_changes(
            insights_client=self.insights_client,
            logger=self.logger,
            major=major,
            minor=minor,
        )

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def get_relevant_appstreams(
        self,
        major: Annotated[
            str,
            Field(
                default="",
                description="Restricts relevance evaluation to systems running this RHEL major version.",
            ),
        ] = "",
        minor: Annotated[
            str,
            Field(
                default="",
                description=(
                    "Used together with major to further restrict relevance evaluation "
                    "to a specific minor version. Requires major to be specified."
                ),
            ),
        ] = "",
        include_related: Annotated[
            bool,
            Field(
                default=True,
                description=(
                    "If true, returns streams currently used plus related/successor streams. "
                    "If false, returns only streams currently used in inventory."
                ),
            ),
        ] = True,
    ) -> str:
        """Get Application Streams relevant to the requester's inventory (includes lifecycle/support dates).

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool when the user asks about Application Streams in their environment
        (inventory, hosts, systems...), such as:
        "Which app streams are we running on RHEL 9?"
        "What successor app streams could we move to from our current streams?"

        Use this tool over get_appstreams_lifecycle when the user asks about their
        inventory, hosts, systems...

        If the question is scoped to a specific RHEL major or minor, set major
        (and optionally minor) so that relevance is computed only from systems on
        that version.

        If the user wants only streams currently running (what is installed/in use
        in inventory), set include_related=false.
        If the user asks whether newer versions exist, wants upgrade recommendations,
        or wants successor streams to consider, set include_related=true and review
        entries where related=true as potential candidates.

        If the user needs an exhaustive catalog view of all streams available for a
        given component (e.g., "list all Node.js streams across RHEL 8/9/10"), use
        get_appstreams_lifecycle.

        The backend computes relevance based on actual host data in the user's inventory. This tool
        does not perform any client-side filtering; all evaluation is performed by the backend.

        Returns:
            str: A JSON-encoded response object containing:
                 - meta: Metadata including:
                     - count (int): Number of records returned.
                     - total (int): Total number of matching records.
                 - data: A list of Application Stream records relevant to the user's inventory.
                   Each record contains:
                     - name (str): Technical package or module name.
                     - display_name (str): Human-friendly display name.
                     - application_stream_name (str): Application Stream name.
                     - stream (str): Stream identifier or version.
                     - start_date (str | null): Planned start date (ISO format).
                     - end_date (str | null): Planned end-of-life date (ISO format).
                     - support_status (str): Support status (e.g. 'Supported', 'Retired').
                     - os_major (int | null): RHEL major version.
                     - os_minor (int | null): RHEL minor version.
                     - related (bool): Indicates if this is a related/successor stream (true)
                       or currently in use (false).
        """
        return await _get_relevant_appstreams(
            insights_client=self.insights_client,
            logger=self.logger,
            major=major,
            minor=minor,
            include_related=include_related,
        )


# Instance used by the unified Insights MCP server (`insights_mcp.server`).
mcp = PlanningMCP()
