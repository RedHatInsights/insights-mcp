"""Advisor Recommendations MCP server for Red Hat Insights recommendations management."""

import json
import logging
from typing import Annotated

from fastmcp.tools.tool import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.mcp import InsightsMCP


class AdvisorMCP(InsightsMCP):
    """MCP server for Red Hat Insights Advisor Recommendations integration.

    This server provides tools for querying Red Hat Insights
    Advisor Recommendations, which identify configuration issues that might negatively
    affect the availability, stability, performance, or security of your RHEL systems.
    Includes recommendation discovery, host impact analysis, and detailed information retrieval.
    """

    def __init__(self):
        self.logger = logging.getLogger("AdvisorMCP")
        super().__init__(
            name="Advisor Recommendations MCP Server",
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
- get_recommendations_statistics: Get overall risk posture statistics with breakdown by risk levels and categories.

Use these tools to identify issues, assess impact, and plan remediation across your RHEL systems.

Insights Advisor requires correct RBAC permissions to be able to use the tools. Ensure that your
Service Account has at least this role:
- RHEL Advisor viewer

If you don't have this role, please contact your organization administrator to get it.
"""
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
            "get_recommendations_statistics": {
                "function": self.get_recommendations_statistics,
                "tags": ("insights", "advisor", "statistics", "risk", "categories", "overview"),
                "title": "Get Statistics of Recommendations Across Categories and Risks",
                "annotations": ToolAnnotations(
                    title="Get Statistics of Recommendations Across Categories and Risks",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=True,
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
    def _parse_string_list(value: str | list[str] | None) -> list[str] | None:
        """Parse string list from string or list input with error handling."""
        if value is None:
            return None
        if isinstance(value, list):
            # If it's already a list, validate each item is a string
            result = [str(x).strip() for x in value if x is not None and str(x).strip()]
            return result if result else None
        if isinstance(value, str):
            if not value.strip():
                return None
            try:
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        result = [str(x).strip() for x in parsed if x is not None and str(x).strip()]
                        return result if result else None
                except json.JSONDecodeError:
                    pass

                # Handle comma-separated string format like 'item1,item2'
                result = [x.strip() for x in value.split(",") if x.strip()]
                return result if result else None
            except (ValueError, AttributeError):
                pass
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

    @staticmethod
    def _parse_bool(value: str | bool | None) -> bool | None:
        """Parse boolean from string or bool input with error handling."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value_lower = value.strip().lower()
            if value_lower in ("true", "1", "yes", "on"):
                return True
            if value_lower in ("false", "0", "no", "off"):
                return False
        return None

    async def get_active_rules(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches
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
                "Available values: 1=Low, 2=Medium, 3=High, 4=Critical. Example: '3,4'"
            ),
        ],
        likelihood: Annotated[
            str | None,
            Field(
                description="Likelihood level filter as comma-separated string, e.g. '1,2,3'. "
                "Available values: 1=Low, 2=Medium, 3=High, 4=Very High. Example: '3,4'"
            ),
        ],
        category: Annotated[
            str | None,
            Field(
                description=(
                    "Recommendation category filter as comma-separated string, e.g. '1,2,3'. "
                    "Available values: 1=Availability, 2=Security, 3=Stability, 4=Performance. Example: '2,4'"
                ),
            ),
        ],
        reboot: Annotated[
            str | bool | None,
            Field(
                None,
                description="Filter recommendations that require a reboot to fix. "
                "True shows only reboot-required recommendations, "
                "None shows all recommendations. Example: true",
            ),
        ],
        sort: Annotated[
            str | None,
            Field(
                description="Sort field as comma-separated string. Available fields: "
                "category, description, impact, impacted_count, likelihood, playbook_count, publish_date, "
                "resolution_risk, rule_id, total_risk. Use '-' prefix for descending order. "
                "Example: '-total_risk,rule_id'"
            ),
        ],
        offset: Annotated[
            str | int | None,
            Field(description="Pagination offset to skip specified number of results. Used with limit. Example: 0"),
        ],
        limit: Annotated[
            str | int | None,
            Field(description="Pagination: Maximum number of results per page. Default: 20"),
        ],
        tags: Annotated[
            str | list[str] | None,
            Field(
                None,
                description=(
                    "Used with impacting=True to filter recommendations that are relevant to the target systems. "
                    "Filter recommendations by system tags or groups using 'namespace/key=value' format. "
                    "namespace: 'satellite' or 'insights-client' "
                    "Examples: ['satellite/group=database-servers', 'insights-client/security=strict'] or "
                    'JSON string format: \'["satellite/group=database-servers", "insights-client/security=strict"]\''
                ),
            ),
        ],
    ) -> str:
        """
        Get active Advisor Recommendations for your account that help identify issues
        affecting system availability, stability, performance, or security.

        Use filters to find recommendations by impact level, likelihood, systems affected,
        and automatic remediation availability. Higher impact/likelihood values indicate more critical issues.

        Call examples:
            Standard call: {"impacting": true, "offset": 0, "limit": 20}
            High risk only: {"impacting": true, "impact": "3,4", "likelihood": "3,4"}
            Pagination: {"offset": 20, "limit": 20}
            With automatic remediation: {"has_automatic_remediation": true}
            Security and Performance categories: {"category": "2,4"}
            Reboot required to fix: {"reboot": true}
            Sorted by total risk: {"sort": "-total_risk"}
            For systems tagged 'database-servers': {
                "impacting": true,
                "tags": ["insights-client/group=database-servers"]
            }
        """  # pylint: disable=line-too-long

        # Parameter validation and conversion
        impact_list = self._parse_int_list(impact)
        likelihood_list = self._parse_int_list(likelihood)
        category_list = self._parse_int_list(category)
        offset_int = self._parse_int(offset)
        limit_int = self._parse_int(limit)
        reboot_bool = self._parse_bool(reboot)

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
        if category_list is not None:
            params["category"] = ",".join(map(str, category_list))
        if reboot_bool is not None:
            params["reboot"] = reboot_bool
        if sort is not None:
            params["sort"] = sort

        # Handle tags parameter
        if tags:
            # Parse tags input using the helper function to handle both string and list inputs
            parsed_tags = self._parse_string_list(tags)
            if parsed_tags:
                # Validate tags input - each tag should be in namespace/key=value format
                tag_list = []
                for tag in parsed_tags:
                    if tag and "/" in tag and "=" in tag:
                        tag_list.append(tag)
                    elif tag:
                        self.logger.warning("Invalid tag format '%s', expected namespace/key=value", tag)

                if tag_list:
                    params["tags"] = ",".join(tag_list)

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
                description=(
                    "Node ID of the knowledge base article or solution to find related Advisor Recommendations. "
                    "Must be a valid string format. Example: '123456'"
                ),
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

    async def get_recommendations_statistics(
        self,
        *,
        tags: Annotated[
            str | list[str] | None,
            Field(
                None,
                description="Filter recommendations by system tags in the form namespace/key=value. "
                "namespace: 'satellite' or 'insights-client' "
                "Examples: ['satellite/group=database-servers', 'insights-client/security=strict'] or "
                'JSON string format: \'["satellite/group=database-servers", "insights-client/security=strict"]\'',
            ),
        ] = None,
    ) -> str:
        """
        Show statistics of recommendations across categories and risks.

        Call examples:
            Standard call showing all recommendations: {}
            Statistics for a specific system group: {"tags": ["satellite/group=database-servers"]}
            Statistics for systems tagged 'security=strict': {"tags": ["insights-client/security=strict"]}
        """
        params: dict[str, str] = {}

        if tags is not None and tags:
            # Parse tags input using the helper function to handle both string and list inputs
            parsed_tags = self._parse_string_list(tags)
            if parsed_tags:
                # Validate and process tags format
                tag_list = []
                for tag in parsed_tags:
                    tag_stripped = tag.strip()
                    if not tag_stripped:
                        continue
                    # Validate tag format: should be in form namespace/key=value
                    if "/" not in tag_stripped or "=" not in tag_stripped:
                        return (
                            f"Error: Invalid tag format '{tag_stripped}'. Tags must be in format 'namespace/key=value'."
                        )
                    tag_list.append(tag_stripped)

                if tag_list:
                    params["tags"] = ",".join(tag_list)

        try:
            response = await self.insights_client.get("stats/rules/", params=params)
            return str(response) if response else "No recommendations statistics found or empty response."
        except (ValueError, TypeError, ConnectionError) as e:
            self.logger.error("Failed to retrieve recommendations statistics: %s", str(e))
            return f"Failed to retrieve recommendations statistics: {str(e)}"


mcp_server = AdvisorMCP()
