"""Red Hat Subscription Management (RHSM) MCP Server.

MCP server for Red Hat Subscription Management via Red Hat Insights API.
Provides tools to manage activation keys and subscription information in Red Hat services.
"""

from typing import Annotated, Any

from pydantic import Field

from insights_mcp.mcp import InsightsMCP

mcp = InsightsMCP(
    name="Red Hat Insights RHSM MCP Server",
    toolset_name="rhsm",
    api_path="api/rhsm/v2",
    instructions="""This server provides tools to manage Red Hat Subscription Management (RHSM) for Red Hat services.
    You can get activation keys and subscription information.

    Insights RHSM requires correct RBAC permissions to be able to use the tools. Ensure that your
    Service Account has at least these roles:
    - Subscription Viewer (for read-only access)
    If this permission is missing in RBAC write this in bold that this is missing.

    The RHSM REST API supports managing:
    - Activation keys for system registration
    - Subscription information
    - Organization details
    """,
)


@mcp.tool(annotations={"readOnlyHint": True})
async def get_activation_keys(
    limit: Annotated[int, Field(default=20, description="Maximum number of activation keys to return (default: 20).")],
    offset: Annotated[
        int, Field(default=0, description="Number of activation keys to skip for pagination (default: 0).")
    ],
) -> dict[str, Any] | str:
    """Get the list of activation keys available to the authenticated user.

    🟢 CALL IMMEDIATELY - No information gathering required.

    This endpoint returns activation keys that can be used for RHEL system registration.
    Activation keys contain subscription and configuration information needed to register
    systems with Red Hat Subscription Management.

    If the user has more questions about the activation keys,
    ask the user to go to https://console.redhat.com/insights/connector/activation-keys

    Returns:
        List of activation keys with their details including names, descriptions,
        and associated subscriptions.
    """
    # Get all activation keys from the API (no pagination parameters)
    response = await mcp.insights_client.get("activation_keys")
    if isinstance(response, str):
        response += """

        """
        return response

    # Extract the body from the API response
    if isinstance(response, dict) and "body" in response:
        activation_keys = response["body"]
    else:
        activation_keys = response

    # Apply client-side pagination
    if isinstance(activation_keys, list):
        total_count = len(activation_keys)

        # Ensure offset and limit are non-negative
        offset = max(0, offset)
        limit = max(0, limit)

        # Ensure offset doesn't exceed total count
        offset = min(offset, total_count)

        # Calculate end index ensuring it doesn't exceed total count
        start_idx = offset
        end_idx = min(offset + limit, total_count)
        paginated_keys = activation_keys[start_idx:end_idx]

        return {
            "body": paginated_keys,
            "pagination": {"count": len(paginated_keys), "limit": limit, "offset": offset, "total": total_count},
        }

    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def get_activation_key(
    name: Annotated[str, Field(description="The name of the activation key to retrieve.")],
) -> dict[str, Any] | str:
    """Get a specific activation key by name.

    🟢 CALL IMMEDIATELY - No information gathering required.

    This endpoint returns details for a specific activation key including its name,
    description, service level, role, usage, release version, and additional repositories.

    Returns:
        Activation key details including configuration and subscription information.
    """
    response = await mcp.insights_client.get(f"activation_keys/{name}")

    return response


# DISABLED for now as the list returned
# contains many entries, not compatible with current rhel versions
# and there doesn't seem to be a way to filter by release version
# @mcp.tool(annotations={"readOnlyHint": True})
# pylint: disable=too-many-arguments,too-many-positional-arguments
async def get_activation_key_available_repositories(
    name: Annotated[str, Field(description="The name of the activation key.")],
    limit: Annotated[
        int, Field(default=20, description="Maximum number of repositories to return (default: 20).")
    ] = 20,
    offset: Annotated[
        int, Field(default=0, description="Number of repositories to skip for pagination (default: 0).")
    ] = 0,
    default: Annotated[
        str | None,
        Field(
            default=None,
            description='Filter available repos based off default status. Use "Disabled" to filter.',
        ),
    ] = None,
    repo_name: Annotated[str | None, Field(default=None, description="Repository name to search by.")] = None,
    repo_label: Annotated[str | None, Field(default=None, description="Repository label to search by.")] = None,
    architecture: Annotated[
        str | None,
        Field(default=None, description="Comma-separated list of architectures to filter by."),
    ] = None,
    sort_by: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Field to search by. Supported options are repo_name and repo_label. "
                "Must be used in combination with sort_direction."
            ),
        ),
    ] = None,
    sort_direction: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Direction to sort available repositories by. Supported options are asc and desc. "
                "Must be used in combination with sort_by."
            ),
        ),
    ] = None,
    rpm_type: Annotated[
        str | None, Field(default=None, description="Comma-separated list of rpm types to filter by.")
    ] = None,
) -> dict[str, Any] | str:
    """Get the list of RPM repositories available to an activation key.

    🟢 CALL IMMEDIATELY - No information gathering required.

    This endpoint returns the list of RPM repositories that can be added as additional
    repositories to an activation key. Available repositories are calculated by excluding
    repositories already added to the activation key from the total set of RPM repositories.

    Returns:
        List of available repositories with pagination information.
    """
    # Build query parameters dict
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }
    # Add optional parameters only if provided
    if default is not None:
        params["default"] = default
    if repo_name is not None:
        params["repo_name"] = repo_name
    if repo_label is not None:
        params["repo_label"] = repo_label
    if architecture is not None:
        params["architecture"] = architecture
    if sort_by is not None:
        params["sort_by"] = sort_by
    if sort_direction is not None:
        params["sort_direction"] = sort_direction
    if rpm_type is not None:
        params["rpm_type"] = rpm_type

    response = await mcp.insights_client.get(f"activation_keys/{name}/available_repositories", params=params)

    return response
