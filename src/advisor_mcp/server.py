"""Advisor Recommendations MCP server for Red Hat Insights recommendations management."""

import json
import logging
from typing import Annotated, Any

from fastmcp.tools.tool import Tool
from fastmcp.server.dependencies import get_access_token, get_http_headers
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
            # TODO: check if role should be added to failed http responses.
            instructions=(
                "This server provides tools to discover and inspect Red Hat Insights Advisor "
                "Recommendations for RHEL.\n"
                "(A recommendation was formerly called a rule in Red Hat Insights.)\n\n"
                "Insights Advisor requires correct RBAC permissions to be able to use the tools. Ensure that your\n"
                "Service Account has at least this role:\n"
                "- RHEL Advisor viewer\n"
                "If you don't have this role, please contact your organization administrator to get it."
            ),
        )

    async def log_request_and_token_info(self, tool_name: str) -> dict[str, Any]:
        """Helper method to log request headers and extract token information for any MCP tool.
        
        This demonstrates the complete flow of:
        1. Extracting FastMCP access token from request
        2. Logging request headers (with security masking)
        3. Accessing Red Hat SSO claims and scopes
        4. Using enhanced OAuth client for token exchange debugging
        
        Args:
            tool_name: Name of the MCP tool being called
            
        Returns:
            Dictionary containing extracted token and request information
        """
        info = {
            "tool_name": tool_name,
            "request_headers": {},
            "access_token_info": {},
            "redhat_sso_claims": {},
            "enhanced_client_debug": {},
        }
        
        self.logger.info("=== MCP Tool Call: %s ===", tool_name)
        
        # 1. Extract and log request headers
        try:
            request_headers = get_http_headers()
            info["request_headers"] = {}
            
            self.logger.info("Request headers received:")
            for header_name, header_value in request_headers.items():
                # Security: mask sensitive headers but keep them in debug info
                if header_name.lower() in ['authorization', 'x-api-key', 'bearer']:
                    if len(header_value) > 20:
                        masked_value = f"{header_value[:10]}...{header_value[-6:]}"
                    else:
                        masked_value = "***MASKED***"
                    self.logger.info("  %s: %s", header_name, masked_value)
                    info["request_headers"][header_name] = masked_value
                else:
                    self.logger.info("  %s: %s", header_name, header_value)
                    info["request_headers"][header_name] = header_value
                

        except Exception as e:
            self.logger.warning("Failed to get request headers: %s", e)
            info["request_headers"]["error"] = str(e)

        # 2. Extract FastMCP access token
        try:
            access_token = get_access_token()
            if access_token:
                info["access_token_info"] = {
                    "client_id": access_token.client_id,
                    "scopes": access_token.scopes,
                    "expires_at": access_token.expires_at,
                    "token_length": len(access_token.token),
                }
                
                self.logger.info("FastMCP Access token extracted:")
                self.logger.info("  Client ID: %s", access_token.client_id)
                self.logger.info("  Scopes: %s", access_token.scopes)
                self.logger.info("  Expires at: %s", access_token.expires_at)
                
                # 3. Extract Red Hat SSO claims if available
                if hasattr(access_token, 'claims') and access_token.claims:
                    claims = access_token.claims
                    redhat_claims = {
                        "issuer": claims.get('iss'),
                        "subject": claims.get('sub'),
                        "org_id": claims.get('org_id'),
                        "account_id": claims.get('account_id'),
                        "username": claims.get('preferred_username'),
                        "email": claims.get('email'),
                        "realm_roles": claims.get('realm_access', {}).get('roles', []),
                        "resource_access": list(claims.get('resource_access', {}).keys()),
                        "groups": claims.get('groups', []),
                    }
                    info["redhat_sso_claims"] = redhat_claims
                    
                    self.logger.info("Red Hat SSO claims:")
                    for key, value in redhat_claims.items():
                        if value:  # Only log non-empty values
                            self.logger.info("  %s: %s", key, value)
                            
            else:
                self.logger.warning("No access token found in request")
                info["access_token_info"]["error"] = "No token found"
                
        except Exception as e:
            self.logger.error("Failed to extract access token: %s", e)
            info["access_token_info"]["error"] = str(e)

        # 4. Get enhanced OAuth client debug info (shows token exchange process)
        try:
            if hasattr(self.insights_client, 'client') and hasattr(self.insights_client.client, 'debug_token_info'):
                debug_info = await self.insights_client.client.debug_token_info()
                info["enhanced_client_debug"] = debug_info
                
                self.logger.info("Enhanced OAuth client debug info:")
                self.logger.info("  OAuth enabled: %s", debug_info.get('oauth_enabled'))
                self.logger.info("  FastMCP token present: %s", debug_info.get('fastmcp_token_present'))
                self.logger.info("  Is Red Hat token: %s", debug_info.get('is_redhat_token'))
                self.logger.info("  Current auth header set: %s", 
                               'Yes' if debug_info.get('current_auth_header', 'Not set') != 'Not set' else 'No')
                
                # Log FastMCP payload details if available
                fastmcp_payload = debug_info.get('fastmcp_payload')
                if fastmcp_payload:
                    self.logger.info("  FastMCP token details:")
                    self.logger.info("    Issuer: %s", fastmcp_payload.get('iss'))
                    self.logger.info("    Audience: %s", fastmcp_payload.get('aud'))
                    self.logger.info("    Organization: %s", 
                                   fastmcp_payload.get('org_id') or fastmcp_payload.get('rh-org-id'))
                    
        except Exception as e:
            self.logger.debug("Enhanced client debug not available: %s", e)
            info["enhanced_client_debug"]["error"] = str(e)
        
        self.logger.debug("The returned info: %s", info)
        self.logger.info("=== End Request/Token Logging ===")
        return info

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
            "get_hosts_details_hitting_a_rule": {
                "function": self.get_hosts_details_hitting_a_rule,
                "tags": ("insights", "advisor", "recommendations", "systems", "details", "impactted", "hosts"),
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
            bool | str | None, Field(True, description="Only show recommendations currently impacting systems.")
        ],
        incident: Annotated[
            bool | str | None, Field(None, description="Only show recommendations that cause incidents.")
        ],
        has_automatic_remediation: Annotated[
            bool | str | None,
            Field(
                None,
                description="Only show recommendations that have a playbook for automatic remediation.",
            ),
        ],
        impact: Annotated[
            str | None,
            Field(
                None,
                description="Impact level filter as comma-separated string, Example: '1,2,3'. "
                "Accepted values: 1 (Low), 2 (Medium), 3 (High), 4 (Critical). "
                "Use only these exact values: 1, 2, 3, or 4.",
            ),
        ],
        likelihood: Annotated[
            str | None,
            Field(
                None,
                description="Likelihood level filter as comma-separated string, Example: '1,2,3'. "
                "Accepted values: 1 (Low), 2 (Medium), 3 (High), 4 (Very High). "
                "Use only these exact values: 1, 2, 3, or 4.",
            ),
        ],
        category: Annotated[
            str | None,
            Field(
                None,
                description=(
                    "Recommendation category filter as comma-separated string, Example: '1,2,3'. "
                    "Accepted values: 1 (Availability), 2 (Security), 3 (Stability), 4 (Performance). "
                ),
            ),
        ],
        reboot: Annotated[
            bool | str | None,
            Field(None, description="Filter recommendations that require a reboot to fix."),
        ],
        sort: Annotated[
            str,
            Field(
                "-total_risk",
                description="Sort field as comma-separated string. Example: '-total_risk,rule_id'. "
                "Available fields: category, description, impact, impacted_count, likelihood, "
                "playbook_count, publish_date, resolution_risk, rule_id, total_risk. "
                "Use '-' prefix for descending order.",
            ),
        ],
        offset: Annotated[
            int,
            Field(
                0,
                description="Pagination offset to skip specified number of results. Used with limit.",
            ),
        ],
        limit: Annotated[
            int,
            Field(
                10,
                description="Pagination: Maximum number of results per page.",
            ),
        ],
        groups: Annotated[
            str | list[str] | None,
            Field(
                None,
                description=(
                    "Filter based on workspace names. Comma separated list of workspace names."
                    "Used only when impacting=True. "
                    "Example: 'workspace1,workspace2'"
                ),
            ),
        ],
        tags: Annotated[
            str | list[str] | None,
            Field(
                None,
                description=(
                    "Filter based on system tags. Accepts a single tag or a comma-separated list."
                    "Used only when impacting=True. "
                    "Tag format: 'namespace/key=value'. "
                    "Example: 'satellite/group=database-servers,insights-client/security=strict'"
                ),
            ),
        ],
    ) -> dict[str, Any] | str:
        """Get active Advisor Recommendations for your account that help identify issues
        affecting system availability, stability, performance, or security.

        Use filters to find recommendations by impact level, likelihood, systems affected, workspace, tags,
        and automatic remediation availability. Higher impact/likelihood values indicate more critical issues.

        Call examples:
            Standard call: {"impacting": true, "offset": 0, "limit": 20}
            High risk only: {"impacting": true, "impact": "3,4", "likelihood": "3,4"}
            Pagination: {"offset": 20, "limit": 20}
            With automatic remediation: {"has_automatic_remediation": true}
            Security and Performance categories: {"category": "2,4"}
            Reboot required: {"reboot": true}
            Sorted by total risk: {"sort": "-total_risk"}
            For workspaces 'workspace1': {"impacting": true, "groups": "workspace1"}
            For systems tagged 'database-servers': {
                "impacting": true,
                "tags": ["insights-client/group=database-servers"]
            }
        """  # pylint: disable=line-too-long

        # ================================================================
        # REQUEST LOGGING AND TOKEN EXTRACTION EXAMPLE
        # ================================================================
        
        # Use the helper method to log request headers and extract token information
        token_info = await self.log_request_and_token_info("get_active_rules")
        
        # Log tool-specific parameters
        self.logger.info("Tool parameters:")
        self.logger.info("  impacting: %s", impacting)
        self.logger.info("  limit: %d, offset: %d", limit, offset)
        self.logger.info("  filters: impact=%s, likelihood=%s, category=%s", impact, likelihood, category)
        if groups:
            self.logger.info("  groups: %s", groups)
        if tags:
            self.logger.info("  tags: %s", tags)
        
        # Example: Use extracted token information for business logic
        if token_info.get("redhat_sso_claims", {}).get("org_id"):
            org_id = token_info["redhat_sso_claims"]["org_id"]
            self.logger.info("Processing request for Red Hat organization: %s", org_id)
        
        # ================================================================
        # ORIGINAL TOOL LOGIC CONTINUES BELOW  
        # ================================================================

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
        params["limit"] = limit

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
                        return f"Error: Invalid tag format '{tag}', Required format: namespace/key=value"

                if tag_list:
                    params["tags"] = ",".join(tag_list)

        try:
            response = await self.insights_client.get("rule/", params=params)
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendations: %s", str(e))
            return f"Error: Failed to retrieve recommendations: {str(e)}"

    async def get_rule_from_node_id(
        self,
        *,
        node_id: Annotated[
            int,
            Field(description="Node ID of the knowledge base article or solution. Example: 123456"),
        ],
    ) -> dict[str, Any] | list[str] | str:
        """Find Advisor Recommendations related to a specific Knowledge Base article or solution.

        Use this when you have a Knowledge Base article or solution ID and want to find
        corresponding Advisor Recommendations that provide system-specific remediation steps.

        Call examples:
            Standard call: {"node_id": 123456}
        """

        try:
            response = await self.insights_client.get(f"kcs/{node_id}/")
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to retrieve recommendation for node ID %s: %s", node_id, str(e))
            return f"Error: Failed to retrieve recommendation for node ID {node_id}: {str(e)}"

    async def get_rule_details(
        self,
        *,
        rule_id: Annotated[
            str,
            Field(description="Recommendation identifier in format: rule_name|ERROR_KEY."),
        ],
    ) -> dict[str, Any] | str:
        """Get detailed information about a specific Advisor Recommendation, including
        impact level, likelihood, remediation steps, and related knowledge base articles.

        Call Examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}
        """
        
        # Example: Use the helper method in any tool for consistent logging
        # (This is optional - you can choose which tools need detailed logging)
        token_info = await self.log_request_and_token_info("get_rule_details")
        
        # Example: Access extracted information for authorization/business logic
        if token_info.get("access_token_info", {}).get("scopes"):
            required_scopes = {"api.insights", "api.console"}
            user_scopes = set(token_info["access_token_info"]["scopes"])
            if not required_scopes.intersection(user_scopes):
                self.logger.warning("User may lack required scopes for detailed rule access")
        
        if not rule_id or not isinstance(rule_id, str) or "|" not in rule_id:
            return "Error: Recommendation ID must be a non-empty string in format rule_name|ERROR_KEY."

        # Basic sanitization for rule_id
        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            return "Error: Recommendation ID cannot be empty."

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/")
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendation details for %s: %s", rule_id, str(e))
            return f"Error: Failed to retrieve recommendation details for {rule_id}: {str(e)}"

    async def get_hosts_hitting_a_rule(
        self,
        *,
        rule_id: Annotated[
            str,
            Field(description="Recommendation identifier in format: rule_name|ERROR_KEY."),
        ],
    ) -> dict[str, Any] | str:
        """Get all RHEL systems affected by a specific Advisor Recommendation.

        Shows which systems in your infrastructure have the issue identified
        by this recommendation. Use this to understand the scope of impact.

        Call Examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}
        """
        if not rule_id or not isinstance(rule_id, str) or "|" not in rule_id:
            return "Error: Recommendation ID must be a non-empty string."

        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            return "Error: Recommendation ID cannot be empty."

        try:
            response = await self.insights_client.get(f"rule/{sanitized_rule_id}/systems/")
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve systems for recommendation %s: %s", rule_id, str(e))
            return f"Error: Failed to retrieve systems for recommendation {rule_id}: {str(e)}"

    async def get_hosts_details_hitting_a_rule(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        *,
        rule_id: Annotated[
            str,
            Field(description="Recommendation identifier in format: rule_name|ERROR_KEY."),
        ],
        limit: Annotated[
            int,
            Field(10, description="Pagination: Maximum number of results per page."),
        ],
        offset: Annotated[
            int,
            Field(0, description="Pagination offset to skip specified number of results. Used with limit."),
        ],
        rhel_version: Annotated[
            str | list[str] | None,
            Field(
                None,
                description="Filter systems by RHEL version. Accepts a comma-separated string or a list. "
                "Allowed values: 6.0-6.10, 7.0-7.10, 8.0-8.10, 9.0-9.8, 10.0-10.2. Example: '9.3,9.4,9.5'",
            ),
        ],
    ) -> dict[str, Any] | str:
        """Get detailed information about RHEL systems affected by a specific Advisor Recommendation.

        Returns paginated system details with comprehensive information about each affected system,
        including system identification, impact metrics, RHEL version, and last seen timestamps.
        Each system entry contains hit counts categorized by severity level and incident status.

        Call examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}
            With pagination: {"rule_id": "rule_id", "limit": 20, "offset": 0}
            Filter by RHEL version: {"rule_id": "rule_id", "rhel_version": "9.4"}
            Combined filters: {"rule_id": "rule_id", "limit": 50, "offset": 20, "rhel_version": "8.9"}
        """
        if not rule_id or not isinstance(rule_id, str) or "|" not in rule_id:
            return "Error: Recommendation ID must be a non-empty string."

        sanitized_rule_id = rule_id.strip()
        if not sanitized_rule_id:
            return "Error: Recommendation ID cannot be empty."

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
                return f"Error: Invalid RHEL version(s) '{invalid_list}'. Valid versions are: {valid_versions}"

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
            return f"Error: Failed to retrieve detailed system information for recommendation {rule_id}: {str(e)}"

    async def get_rule_by_text_search(
        self,
        *,
        text: Annotated[
            str,
            Field(description="The text substring to search for. Example: 'xfs'"),
        ],
    ) -> dict[str, Any] | str:
        """Finds Advisor Recommendations that contain an exact text substring.

        Call examples:
            Standard call: {"text": "xfs"}
        """
        sanitized_text = text.strip()
        if not sanitized_text:
            return "Error: Text search query must be a non-empty string."

        try:
            response = await self.insights_client.get("rule/", params={"text": sanitized_text})
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendations for text search '%s': %s", text, str(e))
            return f"Error: Failed to retrieve recommendations for text search {text}: {str(e)}"

    async def get_recommendations_statistics(
        self,
        *,
        groups: Annotated[
            str | list[str] | None,
            Field(
                None,
                description=(
                    "Filter based on workspace names. Comma separated list of workspace names."
                    "Used only when impacting=True. "
                    "Example: 'workspace1,workspace2'"
                ),
            ),
        ],
        tags: Annotated[
            str | list[str] | None,
            Field(
                None,
                description=(
                    "Filter based on system tags. Accepts a single tag or a comma-separated list."
                    "Used only when impacting=True. "
                    "Tag format: 'namespace/key=value'. "
                    "Example: 'satellite/group=database-servers,insights-client/security=strict'"
                ),
            ),
        ],
    ) -> dict[str, Any] | str:
        """Show statistics of recommendations across categories and risks.

        Call examples:
            Standard call showing all recommendations: {}
            Statistics for the workspace 'workspace1': {"groups": "workspace1"}
            Statistics for systems tagged 'insights-client/security=strict': {"tags": "insights-client/security=strict"}
        """
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
                        return f"Error: Invalid tag format '{tag_stripped}', expected namespace/key=value"
                    tag_list.append(tag_stripped)

                if tag_list:
                    params["tags"] = ",".join(tag_list)

        try:
            response = await self.insights_client.get("stats/rules/", params=params)
            return response
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Error: Failed to retrieve recommendations statistics: %s", str(e))
            return f"Error: Failed to retrieve recommendations statistics: {str(e)}"


mcp_server = AdvisorMCP()
