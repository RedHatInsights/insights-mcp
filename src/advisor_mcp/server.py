"""Advisor Recommendations MCP server for Red Hat Insights recommendations management."""

import json
import logging
from typing import Annotated, Any

from fastmcp.tools import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.errors import InsightsApiError
from insights_mcp.mcp import InsightsMCP


def _kcs_entry_to_rule_ref(item: Any) -> dict[str, str]:
    """Split a KCS retrieve string into rule_id (last path segment) and original url."""
    if not isinstance(item, str):
        raise InsightsApiError(f"expected a KCS URL string, got {type(item).__name__}: {item!r}")
    return {"rule_id": item.rsplit("/", 1)[-1], "url": item}


_RULE_LIST_OMIT_FIELDS = ("resolution_set", "reason", "more_info", "generic")
_RULE_LIST_MAX_LIMIT = 20

_GROUPS_FIELD_DESC = "Workspace names, comma-separated (impacting=true only)."
_TAGS_FIELD_DESC = "Tags as namespace/key=value, comma-separated (impacting=true only)."
_IMPACT_IDS_FIELD_DESC = "Comma-separated impact IDs 1-4 (see toolset instructions)."
_LIKELIHOOD_IDS_FIELD_DESC = "Comma-separated likelihood IDs 1-4 (see toolset instructions)."
_CATEGORY_IDS_FIELD_DESC = "Comma-separated category IDs 1-4 (see toolset instructions)."
_RULE_ID_FIELD_DESC = "Recommendation identifier: rule_name|ERROR_KEY."


def _slim_rule_list_response(response: dict[str, Any] | str) -> dict[str, Any] | str:
    """Remove detail-only fields from /rule/ list items.

    Full remediation text and playbook templates are returned by get_rule_details only.
    """
    if not isinstance(response, dict):
        return response
    for rule in response.get("data", []):
        if isinstance(rule, dict):
            for field in _RULE_LIST_OMIT_FIELDS:
                rule.pop(field, None)
    return response


class AdvisorMCP(InsightsMCP):
    """MCP server for $container_brand_long Advisor Recommendations integration.

    This server provides tools for querying $container_brand_long
    Advisor Recommendations, which identify configuration issues that might negatively
    affect the availability, stability, performance, or security of your RHEL systems.
    Includes recommendation discovery, host impact analysis, and detailed information retrieval.
    """

    def __init__(self):
        self.logger = logging.getLogger("AdvisorMCP")
        super().__init__(
            name="$container_brand_long Advisor Recommendations MCP Server",
            toolset_name="advisor",
            api_path="api/insights/v1",
            # TODO: check if role should be added to failed http responses.
            instructions=(
                "This server provides tools to discover and inspect $container_brand_long Advisor "
                "Recommendations for RHEL.\n"
                "(A recommendation was formerly called a rule in Red Hat Insights.)\n\n"
                "Filters: impact/likelihood/category use IDs 1-4 "
                "(Low, Medium, High, Critical / Availability, Security, Stability, Performance).\n"
                "rule_id format: rule_name|ERROR_KEY.\n"
                "List tools omit resolution_set playbooks; call get_rule_details for remediation.\n\n"
                "$container_brand_long Advisor requires correct RBAC permissions to be able to use the tools. "
                "Ensure that your\n"
                "Service Account has at least this role:\n"
                "- RHEL Advisor viewer\n"
                "If you don't have this role, please contact your organization administrator to get it."
            ),
        )

    def register_tools(self) -> None:
        """Register all available tools with the MCP server."""

        # Define tool configurations with tags and custom titles
        tool_configs: dict[str, dict[str, Any]] = {
            "get_active_rules": {
                "function": self.get_active_rules,
                "tags": ("insights", "advisor", "recommendations", "rules", "issues", "health"),
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
                    "advisor",
                    "recommendations",
                    "knowledge-base",
                    "solution",
                    "kcs",
                    "article",
                    "kb",
                ),
                "title": "Find Advisor Recommendations using Knowledge Base solution ID or article ID",
                "annotations": ToolAnnotations(
                    title="Find Advisor Recommendations using Knowledge Base solution ID or article ID",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            },
            "get_rule_details": {
                "function": self.get_rule_details,
                "tags": ("insights", "advisor", "recommendations", "details"),
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
            "get_hosts_details_for_rule": {
                "function": self.get_hosts_details_for_rule,
                "tags": ("insights", "advisor", "recommendations", "systems", "details", "impacted", "hosts"),
                "title": "Get Detailed System Information for Advisor Recommendation",
                "annotations": ToolAnnotations(
                    title="Get Detailed System Information for Advisor Recommendation",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            },
            "get_rule_by_text_search": {
                "function": self.get_rule_by_text_search,
                "tags": ("insights", "advisor", "recommendations", "search", "text", "substring", "keyword"),
                "title": "Find Advisor Recommendations by Text Search",
                "annotations": ToolAnnotations(
                    title="Find Advisor Recommendations by Text Search",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            },
            "get_recommendations_stats": {
                "function": self.get_recommendations_stats,
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
            tool.description = config["function"].__doc__ or ""
            tool.name = config["function"].__name__
            tool.title = config["title"]
            # Add tags if available in the Tool class
            if hasattr(tool, "tags"):
                tool.tags = config["tags"]
            self.add_tool(tool)

    @staticmethod
    def _parse_bool(value: bool | str | None) -> bool | None:
        """Parse boolean value from string or boolean input with error handling."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return None

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

    async def get_active_rules(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches
        self,
        *,
        impacting: Annotated[
            bool | str | None, Field(True, description="Only recommendations currently impacting systems.")
        ],
        incident: Annotated[bool | str | None, Field(None, description="Only recommendations that cause incidents.")],
        has_automatic_remediation: Annotated[
            bool | str | None,
            Field(None, description="Only recommendations with an automatic remediation playbook."),
        ],
        impact: Annotated[str | None, Field(None, description=_IMPACT_IDS_FIELD_DESC)],
        likelihood: Annotated[str | None, Field(None, description=_LIKELIHOOD_IDS_FIELD_DESC)],
        category: Annotated[str | None, Field(None, description=_CATEGORY_IDS_FIELD_DESC)],
        reboot: Annotated[
            bool | str | None,
            Field(None, description="Only recommendations that require a reboot to fix."),
        ],
        sort: Annotated[
            str,
            Field(
                "-total_risk",
                description="Sort fields; prefix '-' for descending. Default: -total_risk.",
            ),
        ],
        offset: Annotated[int, Field(0, description="Pagination offset.")],
        limit: Annotated[int, Field(10, description="Page size (max 20).")],
        groups: Annotated[str | list[str] | None, Field(None, description=_GROUPS_FIELD_DESC)],
        tags: Annotated[str | list[str] | None, Field(None, description=_TAGS_FIELD_DESC)],
    ) -> dict[str, Any] | str:
        """Get active Advisor Recommendations affecting system health, security, or performance.

        Lists omit playbooks; use get_rule_details for remediation. impacting=true (default) is
        usually preferred; impacting=false returns the global catalog.
        """

        # Parameter validation and conversion

        # Manual string-to-boolean parsing is required because some clients,
        # like Cursor & Claude, send "true" or "false" as strings,
        # which can cause type errors despite Pydantic's automatic conversion.
        impacting = self._parse_bool(impacting)
        incident = self._parse_bool(incident)
        has_automatic_remediation = self._parse_bool(has_automatic_remediation)
        reboot = self._parse_bool(reboot)

        impact_list = self._parse_int_list(impact)
        likelihood_list = self._parse_int_list(likelihood)
        category_list = self._parse_int_list(category)
        sort_list = self._parse_string_list(sort)
        group_list = self._parse_string_list(groups)

        params: dict[str, bool | int | str] = {}
        params["offset"] = offset
        params["limit"] = min(limit, _RULE_LIST_MAX_LIMIT)

        if impacting is not None:
            params["impacting"] = impacting
        if incident is not None:
            params["incident"] = incident
        if has_automatic_remediation is not None:
            params["has_playbook"] = has_automatic_remediation
        if impact_list:
            params["impact"] = ",".join(map(str, impact_list))
        if likelihood_list:
            params["likelihood"] = ",".join(map(str, likelihood_list))
        if category_list:
            params["category"] = ",".join(map(str, category_list))
        if reboot is not None:
            params["reboot"] = reboot
        if sort is not None:
            params["sort"] = ",".join(sort_list) if sort_list else "-total_risk"
        if group_list:
            params["groups"] = ",".join(map(str, group_list))

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
                        self.logger.error("Invalid tag format '%s', Required format: namespace/key=value", tag)
                        raise InsightsApiError(
                            f"Error: Invalid tag format '{tag}', Required format: namespace/key=value"
                        )

                if tag_list:
                    params["tags"] = ",".join(tag_list)

        try:
            response = await self.insights_client.get("rule/", params=params)
            return _slim_rule_list_response(response)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendations: %s", str(e))
            raise InsightsApiError(f"Error: Failed to retrieve recommendations: {str(e)}") from e

    async def get_rule_from_node_id(
        self,
        *,
        node_id: Annotated[
            int,
            Field(description="Knowledge base article or solution node ID."),
        ],
    ) -> list[dict[str, str]] | None:
        """Find Advisor Recommendations linked to a Knowledge Base article or solution ID."""

        try:
            response = await self.insights_client.get(f"kcs/{node_id}/")
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to retrieve recommendation for node ID %s: %s", node_id, str(e))
            raise InsightsApiError(f"Error: Failed to retrieve recommendation for node ID {node_id}: {str(e)}") from e
        if response is None:
            return None
        if not isinstance(response, list):
            raise InsightsApiError(f"expected a list of KCS URL strings, got {type(response).__name__}: {response!r}")
        return [_kcs_entry_to_rule_ref(item) for item in response]

    async def get_rule_details(
        self,
        *,
        rule_id: Annotated[str, Field(description=_RULE_ID_FIELD_DESC)],
    ) -> dict[str, Any] | str:
        """Get full Advisor Recommendation details including remediation playbooks (resolution_set)."""
        if not rule_id or not isinstance(rule_id, str) or "|" not in rule_id:
            raise InsightsApiError("Error: Recommendation ID must be a non-empty string in format rule_name|ERROR_KEY.")

        # Basic sanitization for rule_id
        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            raise InsightsApiError("Error: Recommendation ID cannot be empty.")

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/")
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendation details for %s: %s", rule_id, str(e))
            raise InsightsApiError(f"Error: Failed to retrieve recommendation details for {rule_id}: {str(e)}") from e

    async def get_hosts_hitting_a_rule(
        self,
        *,
        rule_id: Annotated[str, Field(description=_RULE_ID_FIELD_DESC)],
    ) -> dict[str, Any] | str:
        """List RHEL systems affected by a specific Advisor Recommendation."""
        if not rule_id or not isinstance(rule_id, str) or "|" not in rule_id:
            raise InsightsApiError("Error: Recommendation ID must be a non-empty string.")

        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            raise InsightsApiError("Error: Recommendation ID cannot be empty.")

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/systems/")
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve systems for recommendation %s: %s", rule_id, str(e))
            raise InsightsApiError(f"Error: Failed to retrieve systems for recommendation {rule_id}: {str(e)}") from e

    async def get_hosts_details_for_rule(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        *,
        rule_id: Annotated[str, Field(description=_RULE_ID_FIELD_DESC)],
        limit: Annotated[int, Field(10, description="Page size.")],
        offset: Annotated[int, Field(0, description="Pagination offset.")],
        rhel_version: Annotated[
            str | list[str] | None,
            Field(
                None,
                description="RHEL major.minor versions, comma-separated (e.g. 9.4). Invalid values are rejected.",
            ),
        ],
    ) -> dict[str, Any] | str:
        """Get paginated detailed information about systems affected by an Advisor Recommendation."""
        if not rule_id or not isinstance(rule_id, str) or "|" not in rule_id:
            raise InsightsApiError("Error: Recommendation ID must be a non-empty string.")

        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            raise InsightsApiError("Error: Recommendation ID cannot be empty.")

        rhel_version_list = self._parse_string_list(rhel_version)

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

        if rhel_version_list:
            invalid_versions = []
            for version in rhel_version_list:
                version_stripped = str(version).strip()
                if version_stripped not in valid_rhel_versions:
                    invalid_versions.append(version_stripped)

            if invalid_versions:
                self.logger.error(
                    "Error: Invalid RHEL version(s) '%s'. Valid versions are: %s",
                    ", ".join(invalid_versions),
                    ", ".join(sorted(valid_rhel_versions)),
                )
                valid_versions = ", ".join(sorted(valid_rhel_versions))
                invalid_list = ", ".join(invalid_versions)
                raise InsightsApiError(
                    f"Error: Invalid RHEL version(s) '{invalid_list}'. Valid versions are: {valid_versions}"
                )

        # Build query parameters
        params: dict[str, int | str] = {}
        params["limit"] = limit
        params["offset"] = offset
        if rhel_version_list:
            params["rhel_version"] = ",".join(map(str, rhel_version_list))

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/systems_detail/", params=params)
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Error: Failed to retrieve detailed system information for recommendation %s: %s", rule_id, str(e)
            )
            raise InsightsApiError(
                f"Error: Failed to retrieve detailed system information for recommendation {rule_id}: {str(e)}"
            ) from e

    async def get_rule_by_text_search(
        self,
        *,
        text: Annotated[str, Field(description="Text substring to search for.")],
    ) -> dict[str, Any] | str:
        """Find Advisor Recommendations containing an exact text substring.

        Lists omit playbooks; use get_rule_details for remediation.
        """
        sanitized_text = text.strip()
        if not sanitized_text:
            raise InsightsApiError("Error: Text search query must be a non-empty string.")

        try:
            response = await self.insights_client.get("rule/", params={"text": sanitized_text})
            return _slim_rule_list_response(response)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendations for text search '%s': %s", text, str(e))
            raise InsightsApiError(f"Error: Failed to retrieve recommendations for text search {text}: {str(e)}") from e

    async def get_recommendations_stats(
        self,
        *,
        groups: Annotated[str | list[str] | None, Field(None, description=_GROUPS_FIELD_DESC)],
        tags: Annotated[str | list[str] | None, Field(None, description=_TAGS_FIELD_DESC)],
    ) -> dict[str, Any] | str:
        """Show statistics of recommendations across categories and risks."""
        params: dict[str, str] = {}

        if groups is not None:
            group_list = self._parse_string_list(groups)
            if group_list:
                params["groups"] = ",".join(group_list)

        if tags is not None and tags:
            # Parse tags input using the helper function to handle both string and list inputs
            parsed_tags = self._parse_string_list(tags)
            if parsed_tags:
                # Validate and process tags format
                tag_list = []
                for tag in parsed_tags:
                    tag_stripped = tag.strip()
                    # Validate tag format: should be in form namespace/key=value
                    if not tag_stripped:
                        continue
                    if "/" not in tag_stripped or "=" not in tag_stripped:
                        self.logger.error("Invalid tag format '%s', expected namespace/key=value", tag_stripped)
                        raise InsightsApiError(
                            f"Error: Invalid tag format '{tag_stripped}', expected namespace/key=value"
                        )
                    tag_list.append(tag_stripped)

                if tag_list:
                    params["tags"] = ",".join(tag_list)

        try:
            response = await self.insights_client.get("stats/rules/", params=params)
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendations statistics: %s", str(e))
            raise InsightsApiError(f"Error: Failed to retrieve recommendations statistics: {str(e)}") from e


mcp_server = AdvisorMCP()
