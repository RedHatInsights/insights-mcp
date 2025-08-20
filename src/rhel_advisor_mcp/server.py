"""Advisor Recommendations MCP server for Red Hat Insights recommendations management."""

import logging
from typing import Annotated

from fastmcp.tools.tool import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.mcp import InsightsMCP


class RhelAdvisorMCP(InsightsMCP):
    """MCP server for Red Hat Insights Advisor Recommendations integration.

    This server provides tools for querying Red Hat Insights
    Advisor Recommendations, which identify configuration issues that might negatively
    affect the availability, stability, performance, or security of your RHEL systems.
    Includes recommendation discovery, host impact analysis, and detailed information retrieval.
    """

    def __init__(self):
        self.logger = logging.getLogger("RhelAdvisorMCP")
        super().__init__(
            name="RHEL Advisor Recommendations MCP Server",
            toolset_name="advisor",
            api_path="api/insights/v1",
            instructions=(
                """
This server provides tools to discover and inspect Red Hat Insights Advisor Recommendations for RHEL.
(A recommendation was formerly called a rule in Red Hat Insights for Red Hat Enterprise Linux.)

Available tools:
- get_active_rules: List active recommendations for your account with filters
                    (impacting, incident, has_automatic_remediation, impact 1-4, likelihood 1-4, offset, limit).
- get_rule_from_node_id: Find recommendations linked to a Knowledge Base article by node_id.
- get_rule_details: Retrieve detailed information for a recommendation by rule_id.
- get_hosts_hitting_a_rule: List systems affected by a recommendation.
- get_hosts_details_hitting_a_rule: Get detailed per-system impact information for a recommendation.

Use these tools to identify issues, assess impact, and plan remediation across your RHEL systems."""
            ),
        )

    def register_tools(self):
        """Register all available tools with the MCP server."""
        # Define tool configurations with tags and custom titles
        tool_configs = {
            "get_active_rules": {
                "function": self.get_active_rules,
                "tags": ("insights", "advisor", "recommendations", "active", "systems", "health"),
                "title": "Get Active Advisor Recommendations for Account",
                "annotations": ToolAnnotations(
                    title="Get Active Advisor Recommendations for Account",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=True,
                ),
            },
            "get_rule_from_node_id": {
                "function": self.get_rule_from_node_id,
                "tags": (
                    "insights",
                    "advisor",
                    "recommendations",
                    "knowledge-base",
                    "solution",
                    "kcs",
                    "article",
                    "kb",
                ),
                "title": "Find Advisor Recommendations by Knowledge Base Solutions or Articles by ID",
                "annotations": ToolAnnotations(
                    title="Find Advisor Recommendations by Knowledge Base Solutions or Articles by ID",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            },
            "get_rule_details": {
                "function": self.get_rule_details,
                "tags": ("insights", "advisor", "recommendations", "details", "info", "remediation"),
                "title": "Get Detailed Advisor Recommendation Information",
                "annotations": ToolAnnotations(
                    title="Get Detailed Advisor Recommendation Information",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            },
            "get_hosts_hitting_a_rule": {
                "function": self.get_hosts_hitting_a_rule,
                "tags": ("insights", "advisor", "recommendations", "hosts", "affected", "systems", "impacted"),
                "title": "Get Systems Affected by Advisor Recommendation",
                "annotations": ToolAnnotations(
                    title="Get Systems Affected by Advisor Recommendation",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            },
            "get_hosts_details_hitting_a_rule": {
                "function": self.get_hosts_details_hitting_a_rule,
                "tags": ("insights", "advisor", "recommendations", "systems", "details", "impact"),
                "title": "Get Detailed System Information for Advisor Recommendation",
                "annotations": ToolAnnotations(
                    title="Get Detailed System Information for Advisor Recommendation",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            },
        }

        for config in tool_configs.values():
            tool = Tool.from_function(config["function"])
            tool.annotations = config["annotations"]
            tool.description = config["function"].__doc__
            tool.name = config["function"].__name__
            tool.title = config["title"]
            # Add tags if available in the Tool class
            if hasattr(tool, "tags"):
                tool.tags = config["tags"]
            self.add_tool(tool)

    @staticmethod
    def _parse_int_list(value: str | list[int] | None) -> list[int] | None:
        """Parse integer list from string or list input with error handling."""
        if value is None:
            return None
        if isinstance(value, list):
            result = [int(x) for x in value if isinstance(x, (int, str)) and str(x).isdigit()]
            return result if result else None
        if isinstance(value, str):
            if not value.strip():
                return None
            try:
                result = [int(x.strip()) for x in value.split(",") if x.strip().isdigit()]
                return result if result else None
            except (ValueError, AttributeError):
                return None
        return None

    @staticmethod
    def _parse_int(value: str | int | None) -> int | None:
        """Parse integer from string or int input with error handling."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    async def get_active_rules(  # pylint: disable=too-many-arguments
        self,
        *,
        impacting: Annotated[
            bool, Field(True, description="Only show recommendations currently impacting systems. Default: true")
        ],
        incident: Annotated[
            bool, Field(False, description="Only show recommendations that cause incidents. Default: false")
        ],
        has_automatic_remediation: Annotated[
            bool,
            Field(
                False,
                description="Only show recommendations that have a playbook for automatic remediation. Default: false",
            ),
        ],
        impact: Annotated[
            str | None,
            Field(
                description="Impact level filter as comma-separated string, e.g. '1,2,3'. "
                "Levels range 1-4, higher values indicate more severe impact. Example: '3,4'"
            ),
        ],
        likelihood: Annotated[
            str | None,
            Field(
                description="Likelihood level filter as comma-separated string, e.g. '1,2,3'. "
                "Levels range 1-4, higher values indicate higher likelihood. Example: '2,3,4'"
            ),
        ],
        offset: Annotated[
            str | int | None,
            Field(description="Pagination offset to skip specified number of results. Used with limit. Example: 20"),
        ],
        limit: Annotated[
            str | int | None,
            Field(description="Pagination: Maximum number of results per page. Example: 50"),
        ],
    ) -> str:
        """
        Get active Advisor Recommendations for your account that help identify issues
        affecting system availability, stability, performance, or security.

        Use filters to find recommendations by impact level, likelihood, systems affected,
        and automatic remediation availability. Higher impact/likelihood values indicate more critical issues.

        Call examples:
            Standard call: {"impacting": true, "impact": "3,4", "offset": 0, "limit": 20}
            High impact only: {"impact": "4", "likelihood": "3,4"}
            Pagination: {"offset": 20, "limit": 20}
            With automatic remediation: {"has_automatic_remediation": true}
        """

        # Parameter validation and conversion
        impact_list = self._parse_int_list(impact)
        likelihood_list = self._parse_int_list(likelihood)
        offset_int = self._parse_int(offset)
        limit_int = self._parse_int(limit)

        params: dict[str, bool | int | str] = {}
        params["impacting"] = impacting
        params["incident"] = incident
        params["has_playbook"] = has_automatic_remediation

        if offset_int is not None:
            params["offset"] = offset_int
        if limit_int is not None:
            params["limit"] = limit_int
        if impact_list is not None:
            params["impact"] = ",".join(map(str, impact_list))
        if likelihood_list is not None:
            params["likelihood"] = ",".join(map(str, likelihood_list))

        try:
            response = await self.insights_client.get("rule/", params=params)
            return str(response) if response else "No recommendations found or empty response."
        except (ValueError, TypeError, ConnectionError) as e:
            self.logger.error("Failed to retrieve recommendations: %s", str(e))
            return f"Failed to retrieve recommendations: {str(e)}"

    async def get_rule_from_node_id(
        self,
        node_id: Annotated[
            str,
            Field(
                description="Node ID of the knowledge base article or solution to find related Advisor Recommendations."
                "Must be a valid string format. Example: '123456'",  # pylint: disable=line-too-long
            ),
        ],
    ) -> str:
        """
        Find Advisor Recommendations related to a specific Knowledge Base article or solution.

        Use this when you have a Knowledge Base article or solution ID and want to find
        corresponding Advisor Recommendations that provide system-specific remediation steps.

        Call examples:
            Standard call: {"node_id": "123456"}
        """
        if not node_id or not isinstance(node_id, str):
            return "Error: Node ID must be a non-empty string."

        # Sanitize node_id to prevent injection
        sanitized_node_id = node_id.strip()
        if not sanitized_node_id.isalnum():
            return "Error: Node ID must contain only alphanumeric characters."

        try:
            response = await self.insights_client.get(f"kcs/{sanitized_node_id}/")
            return str(response) if response else "No recommendation found for the given node ID."
        except (ValueError, TypeError, ConnectionError) as e:
            self.logger.error("Failed to retrieve recommendation for node ID %s: %s", node_id, str(e))
            return f"Failed to retrieve recommendation for node ID {node_id}: {str(e)}"

    async def get_rule_details(
        self,
        rule_id: Annotated[
            str,
            Field(
                description="Unique identifier of the Advisor Recommendation. Must be a valid string format. "
                "Example: 'xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL'"
            ),
        ],
    ) -> str:
        """
        Get detailed information about a specific Advisor Recommendation, including
        impact level, likelihood, remediation steps, and related knowledge base articles.

        Call Examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}
        """
        if not rule_id or not isinstance(rule_id, str):
            return "Error: Recommendation ID must be a non-empty string."

        # Basic sanitization for rule_id
        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            return "Error: Recommendation ID cannot be empty."

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/")
            return str(response) if response else "No recommendation details found."
        except (ValueError, TypeError, ConnectionError) as e:
            self.logger.error("Failed to retrieve recommendation details for %s: %s", rule_id, str(e))
            return f"Failed to retrieve recommendation details for {rule_id}: {str(e)}"

    async def get_hosts_hitting_a_rule(
        self,
        rule_id: Annotated[
            str,
            Field(
                description="Unique identifier of the Advisor Recommendation. Must be a valid string "
                "format. Example: 'xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL'"
            ),
        ],
    ) -> str:
        """
        Get all RHEL systems affected by a specific Advisor Recommendation.

        Shows which systems in your infrastructure have the issue identified
        by this recommendation. Use this to understand the scope of impact.

        Call Examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}
        """
        if not rule_id or not isinstance(rule_id, str):
            return "Error: Recommendation ID must be a non-empty string."

        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            return "Error: Recommendation ID cannot be empty."

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/systems/")
            return str(response) if response else "No systems found for the specified recommendation."
        except (ValueError, TypeError, ConnectionError) as e:
            self.logger.error("Failed to retrieve systems for recommendation %s: %s", rule_id, str(e))
            return f"Failed to retrieve systems for recommendation {rule_id}: {str(e)}"

    async def get_hosts_details_hitting_a_rule(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        rule_id: Annotated[
            str,
            Field(
                description="Unique identifier of the Advisor Recommendation. Must be a valid string format. "
                "Example: 'xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL'"
            ),
        ],
        *,
        limit: Annotated[
            str | int | None,
            Field(20, description="Pagination: Maximum number of results per page. Default: 20"),
        ] = None,
        offset: Annotated[
            str | int | None,
            Field(0, description="Pagination offset to skip specified number of results. Used with limit. Default: 0"),
        ] = None,
        rhel_version: Annotated[
            str | None,
            Field(
                None,
                description="Display only systems with these versions of RHEL. "
                "Available values: 10.0, 10.1, 10.2, 6.0, 6.1, 6.10, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, "
                "7.0, 7.1, 7.10, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 8.0, 8.1, 8.10, 8.2, 8.3, 8.4, 8.5, "
                "8.6, 8.7, 8.8, 8.9, 9.0, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8. Example: '9.4'",
            ),
        ] = None,
    ) -> str:
        """
        Get detailed information about RHEL systems affected by a specific Advisor Recommendation.

        Returns paginated system details with comprehensive information about each affected system,
        including system identification, impact metrics, RHEL version, and last seen timestamps.
        Each system entry contains hit counts categorized by severity level and incident status.

        Call examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}
            With pagination: {"rule_id": "rule_id", "limit": 20, "offset": 0}
            Filter by RHEL version: {"rule_id": "rule_id", "rhel_version": "9.4"}
            Combined filters: {"rule_id": "rule_id", "limit": 50, "offset": 20, "rhel_version": "8.9"}
        """
        if not rule_id or not isinstance(rule_id, str):
            return "Error: Recommendation ID must be a non-empty string."

        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            return "Error: Recommendation ID cannot be empty."

        # Parameter validation and conversion
        limit_int = self._parse_int(limit)
        offset_int = self._parse_int(offset)

        # Validate RHEL version format if provided
        valid_rhel_versions = {
            "10.0",
            "10.1",
            "10.2",
            "6.0",
            "6.1",
            "6.10",
            "6.2",
            "6.3",
            "6.4",
            "6.5",
            "6.6",
            "6.7",
            "6.8",
            "6.9",
            "7.0",
            "7.1",
            "7.10",
            "7.2",
            "7.3",
            "7.4",
            "7.5",
            "7.6",
            "7.7",
            "7.8",
            "7.9",
            "8.0",
            "8.1",
            "8.10",
            "8.2",
            "8.3",
            "8.4",
            "8.5",
            "8.6",
            "8.7",
            "8.8",
            "8.9",
            "9.0",
            "9.1",
            "9.2",
            "9.3",
            "9.4",
            "9.5",
            "9.6",
            "9.7",
            "9.8",
        }

        sanitized_rhel_version = None
        if rhel_version:
            rhel_version_stripped = rhel_version.strip()
            if rhel_version_stripped not in valid_rhel_versions:
                self.logger.error(
                    "Invalid RHEL version '%s'. Valid versions are: %s",
                    rhel_version_stripped,
                    ", ".join(sorted(valid_rhel_versions)),
                )
                valid_versions = ", ".join(sorted(valid_rhel_versions))
                return f"Error: Invalid RHEL version '{rhel_version_stripped}'. Valid versions are: {valid_versions}"
            sanitized_rhel_version = rhel_version_stripped

        # Build query parameters
        params: dict[str, int | str] = {}
        if limit_int is not None:
            params["limit"] = limit_int
        if offset_int is not None:
            params["offset"] = offset_int
        if sanitized_rhel_version is not None:
            params["rhel_version"] = sanitized_rhel_version

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/systems_detail/", params=params)
            return str(response) if response else "No detailed system information found."
        except (ValueError, TypeError, ConnectionError) as e:
            self.logger.error(
                "Failed to retrieve detailed system information for recommendation %s: %s", rule_id, str(e)
            )
            return f"Failed to retrieve detailed system information for recommendation {rule_id}: {str(e)}"


mcp_server = RhelAdvisorMCP()
