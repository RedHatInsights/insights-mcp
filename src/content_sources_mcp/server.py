"""Red Hat Insights Content Sources MCP Server.

MCP server for content sources data via Red Hat Insights API.
Provides tools to get repository information from content sources.
"""

import logging
import uuid
from typing import Annotated, Any, Callable, Optional

from fastmcp.tools import Tool
from mcp.types import ToolAnnotations
from pydantic import Field

from insights_mcp.errors import InsightsApiError
from insights_mcp.mcp import InsightsMCP
from tools.common import run_insights_tool_request

# List responses omit bulky fields (gpg_key, snapshots, introspection). Fetch those with get_repository.
REPOSITORY_SUMMARY_FIELDS = (
    "uuid",
    "name",
    "label",
    "url",
    "origin",
    "content_type",
    "distribution_versions",
    "distribution_arch",
    "package_count",
    "build_count",
    "version_count",
    "status",
)


class ContentSourcesMCP(InsightsMCP):
    """MCP server for Red Hat Content Sources integration.

    This server provides tools for accessing and managing content sources
    and repositories in $container_brand_long.
    """

    def __init__(self):
        self.logger = logging.getLogger("ContentSourcesMCP")

        general_intro = """You are a Content Sources assistant that helps users access and manage
        repository information from $container_brand_long Content Sources.

        You can help users:
        - List repositories with various filtering options
        - Search for specific repositories by name, URL, or content type
        - Filter repositories by architecture, version, origin, or enabled status
        - Get paginated results for large repository lists
        - Fetch full details for one repository when the user asks about a single UUID

        🚨 CRITICAL BEHAVIORAL RULES:

        🟢 **CALL IMMEDIATELY** (tools marked with green indicator):
        - list_repositories: For queries like "List my repositories", "Show repositories", etc.
          Returns a short summary per repository. Do not request details for every row.

        🔴 **ONE REPOSITORY ONLY**:
        - get_repository: Call only when a single repository UUID is already known
          (from list_repositories or from the user). Never call it once per list item.

        **Note**: Each tool description includes color-coded behavioral indicators for MCP clients
                  that ignore server instructions.

        Your goal is to help users efficiently access and filter their content sources
        repository information through the $container_brand_long platform.

        <|function_call_library|>

        """

        super().__init__(
            name="$container_brand_long Content Sources MCP Server",
            toolset_name="content-sources",
            api_path="api/content-sources/v1.0",
            instructions=general_intro,
        )

    def register_tools(self) -> None:
        """Register all available tools with the MCP server."""

        # Explicit type annotation ensures Tool.from_function passes mypy validation for callable signatures.
        tool_functions: list[Callable[..., Any]] = [
            self.list_repositories,
            self.get_repository,
        ]

        for f in tool_functions:
            tool = Tool.from_function(f)
            tool.annotations = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
            description_str = f.__doc__ or ""
            tool.description = description_str
            tool.title = description_str.split("\n", 1)[0]
            self.add_tool(tool)

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def list_repositories(
        self,
        enabled: Annotated[Optional[bool], Field(default=None, description="Filter by enabled status (True/False).")],
        limit: Annotated[
            int,
            Field(
                default=10,
                description=(
                    "Maximum number of repositories to return (default: 10, maximum: 100). "
                    "**ALWAYS use the default value of 10 for the first call.** "
                    "This default is carefully chosen for performance and context management. "
                    "Only increase this value if the user explicitly asks to see more repositories at once."
                ),
            ),
        ],
        offset: Annotated[
            int, Field(default=0, description="Number of repositories to skip for pagination (default: 0).")
        ],
        name: Annotated[str, Field(default="", description="Filter by repository name (case-insensitive).")],
        url: Annotated[str, Field(default="", description="Filter by repository URL (case-insensitive).")],
        content_type: Annotated[str, Field(default="", description="Filter by content type (e.g., 'rpm', 'ostree').")],
        origin: Annotated[str, Field(default="", description="Filter by origin (e.g., 'red_hat', 'external').")],
        arch: Annotated[str, Field(default="", description="Filter by architecture (e.g., 'x86_64', 'aarch64').")],
        version: Annotated[str, Field(default="", description="Filter by version (e.g., '8', '9').")],
    ) -> str:
        """List repositories with filtering and pagination options.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Each repository is a summary (identity, URL, origin, distribution, counts, and status).
        GPG keys, snapshots, and introspection details are omitted. Use get_repository for one UUID.
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

        params["limit"] = min(limit, 100)
        params["offset"] = offset

        return await run_insights_tool_request(
            self.insights_client.get("repositories/", params=params),
            error_message=lambda exc: f"Error listing repositories: {exc}",
            response_transform=project_repository_summaries,
        )

    async def get_repository(
        self,
        repository_uuid: Annotated[
            str,
            Field(
                description=(
                    "UUID of a single repository. Take it from list_repositories or from the user. "
                    "Call this for one repository only."
                ),
            ),
        ],
    ) -> str:
        """Get full details for one repository by UUID.

        🔴 Call only for a single repository UUID from list_repositories or supplied by the user.
        Returns the complete repository, including the GPG key, snapshot, and introspection fields.
        """
        canonical_uuid = _canonical_repository_uuid(repository_uuid)
        return await run_insights_tool_request(
            self.insights_client.get(f"repositories/{canonical_uuid}"),
            error_message=lambda exc: f"Error fetching repository {canonical_uuid}: {exc}",
        )


def project_repository_summaries(
    response: dict[str, Any] | str | list[Any],
) -> dict[str, Any] | str | list[Any]:
    """Keep collection metadata and a short field set on each listed repository.

    Args:
        response: Content Sources list payload, or a non-dict body left unchanged.

    Returns:
        The same response with each ``data`` item reduced to summary fields.
        Responses that are not a repository collection are returned unchanged.
    """
    if not isinstance(response, dict):
        return response
    repositories = response.get("data")
    if not isinstance(repositories, list):
        return response

    projected_repositories: list[Any] = []
    for repository in repositories:
        if isinstance(repository, dict):
            projected_repositories.append(
                {field: repository[field] for field in REPOSITORY_SUMMARY_FIELDS if field in repository}
            )
        else:
            projected_repositories.append(repository)
    response["data"] = projected_repositories
    return response


def _canonical_repository_uuid(repository_uuid: str) -> str:
    """Return a canonical UUID string, or raise InsightsApiError when the value is not a UUID.

    Args:
        repository_uuid: UUID text supplied by the caller.

    Returns:
        The canonical 8-4-4-4-12 UUID string.

    Raises:
        InsightsApiError: When repository_uuid is not a UUID.
    """
    try:
        parsed_uuid = uuid.UUID(repository_uuid)
    except ValueError as exc:
        raise InsightsApiError(f"repository_uuid must be a UUID; got '{repository_uuid}'.") from exc
    return str(parsed_uuid)


mcp = ContentSourcesMCP()
