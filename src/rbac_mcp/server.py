"""Red Hat Insights RBAC MCP Server.

MCP server for Role-Based Access Control (RBAC) via Red Hat Insights API.
Provides tools to manage permissions, roles, and access policies in Red Hat services.
"""

from typing import Annotated, Any

from pydantic import Field

from insights_mcp.mcp import InsightsMCP

mcp = InsightsMCP(
    name="Insights RBAC MCP Server",
    toolset_name="rbac",
    api_path="api/rbac/v1",
    instructions="""
    This server provides tools to manage Role-Based Access Control (RBAC) for Red Hat services.
    You can get access information, manage roles, permission policies, and conditional policies.

    Insights RBAC requires correct RBAC permissions to be able to use the tools. Ensure that your
    Service Account has at least these roles:
    - RBAC Administrator (for full access)
    - RBAC Viewer (for read-only access)

    The RBAC REST API supports managing:
    - Access policies and permissions for applications
    - Roles and role assignments
    - Permission policies
    - Conditional policies
    """,
)

# disabled for now to minimize the number of tools
# @mcp.tool()


async def get_access(
    application: Annotated[
        str,
        Field(description="Name of the Red Hat application (e.g., 'content-sources', 'advisor', 'vulnerability')."),
    ],
    username: Annotated[str, Field(default="", description="Optional username to filter access for specific user.")],
    limit: Annotated[int, Field(default=20, description="Maximum number of access records to return (default: 20).")],
    offset: Annotated[
        int, Field(default=0, description="Number of access records to skip for pagination (default: 0).")
    ],
) -> dict[str, Any] | str:
    """Get access information for a specific application.

    This endpoint returns access information for users or service accounts
    for a specific Red Hat application (e.g., content-sources, advisor, etc.).

    Note: The application parameter is required. When empty, the API returns
    gzipped responses which are now handled by the client.
    """
    if not application or application.strip() == "":
        return {"error": "Application parameter is required and cannot be empty."}

    params: dict[str, Any] = {
        "application": application,
        "limit": limit,
        "offset": offset,
    }

    if username:
        params["username"] = username

    response = await mcp.insights_client.get("access/", params=params)
    if isinstance(response, str):
        return response
    return response


# disabled for now to minimize the number of tools
# @mcp.tool()


async def get_roles(
    limit: Annotated[int, Field(default=20, description="Maximum number of roles to return (default: 20).")],
    offset: Annotated[int, Field(default=0, description="Number of roles to skip for pagination (default: 0).")],
    name: Annotated[str, Field(default="", description="Filter roles by name (partial match).")],
    system: Annotated[bool, Field(default=False, description="Include system roles in the results (default: False).")],
    order_by: Annotated[
        str, Field(default="name", description="Field to order results by ('name', 'modified', 'policyCount').")
    ],
) -> dict[str, Any] | str:
    """Get list of roles.

    Returns a list of roles with their metadata, permissions, and assignments.
    """
    params: dict[str, Any] = {
        "limit": min(limit, 1000),
        "offset": offset,
        "order_by": order_by,
    }

    if name:
        params["name"] = name
    if system:
        params["system"] = "true"

    response = await mcp.insights_client.get("roles/", params=params)
    if isinstance(response, str):
        return response
    return response


# disabled for now to minimize the number of tools
# @mcp.tool()


async def get_role_details(
    role_uuid: Annotated[str, Field(description="UUID of the role to retrieve details for.")],
) -> dict[str, Any] | str:
    """Get detailed information about a specific role.

    Returns comprehensive role information including permissions, policies,
    and assignments.
    """
    response = await mcp.insights_client.get(f"roles/{role_uuid}/")
    if isinstance(response, str):
        return response
    return response


# disabled for now to minimize the number of tools
# @mcp.tool()
async def get_policy_details(
    policy_uuid: Annotated[str, Field(description="UUID of the policy to retrieve details for.")],
) -> dict[str, Any] | str:
    """Get detailed information about a specific permission policy."""
    response = await mcp.insights_client.get(f"policies/{policy_uuid}/")
    if isinstance(response, str):
        return response
    return response


# disabled for now to minimize the number of tools
# @mcp.tool()
async def get_groups(
    limit: Annotated[int, Field(default=20, description="Maximum number of groups to return (default: 20).")],
    offset: Annotated[int, Field(default=0, description="Number of groups to skip for pagination (default: 0).")],
    name: Annotated[str, Field(default="", description="Filter groups by name (partial match).")],
    scope: Annotated[
        str, Field(default="account", description="Scope of groups to retrieve ('account', 'principal').")
    ],
    order_by: Annotated[str, Field(default="name", description="Field to order results by ('name', 'modified').")],
) -> dict[str, Any] | str:
    """Get list of groups.

    Returns groups that can be used for role assignments and access management.
    """
    params: dict[str, Any] = {
        "limit": min(limit, 1000),
        "offset": offset,
        "scope": scope,
        "order_by": order_by,
    }

    if name:
        params["name"] = name

    response = await mcp.insights_client.get("groups/", params=params)
    if isinstance(response, str):
        return response
    return response


# disabled for now to minimize the number of tools
# @mcp.tool()
async def get_group_details(
    group_uuid: Annotated[str, Field(description="UUID of the group to retrieve details for.")],
) -> dict[str, Any] | str:
    """Get detailed information about a specific group.

    Returns group information including members and assigned roles.
    """
    response = await mcp.insights_client.get(f"groups/{group_uuid}/")
    if isinstance(response, str):
        return response
    return response


# disabled for now to minimize the number of tools
# @mcp.tool()
async def get_principals(
    limit: Annotated[int, Field(default=20, description="Maximum number of principals to return (default: 20).")],
    offset: Annotated[int, Field(default=0, description="Number of principals to skip for pagination (default: 0).")],
    username: Annotated[str, Field(default="", description="Filter principals by username (partial match).")],
    email: Annotated[str, Field(default="", description="Filter principals by email (partial match).")],
    order_by: Annotated[str, Field(default="username", description="Field to order results by ('username', 'email').")],
) -> dict[str, Any] | str:
    """Get list of principals (users/service accounts).

    Returns principals that can be assigned roles and permissions.
    """
    params: dict[str, Any] = {
        "limit": min(limit, 1000),
        "offset": offset,
        "order_by": order_by,
    }

    if username:
        params["username"] = username
    if email:
        params["email"] = email

    response = await mcp.insights_client.get("principals/", params=params)
    if isinstance(response, str):
        return response
    return response


@mcp.tool()
async def get_all_access(
    username: Annotated[str, Field(default="", description="Optional username to filter access for specific user.")],
    limit: Annotated[int, Field(default=20, description="Maximum number of access records to return (default: 20).")],
    offset: Annotated[
        int, Field(default=0, description="Number of access records to skip for pagination (default: 0).")
    ],
) -> dict[str, Any] | str:
    """Get access information for all applications.

    This endpoint returns access information across all applications.
    The API returns gzipped responses for this endpoint, which are handled by the client.
    Use this when you need to see access permissions across all applications.
    """
    params: dict[str, Any] = {
        "application": "",
        "limit": limit,
        "offset": offset,
    }

    if username:
        params["username"] = username

    response = await mcp.insights_client.get("access/", params=params)
    intro = "[INSTRUCTIONS] if just data is empty, tell the user that no permissions are assigned to them."
    intro += " a user with organization admin role should assign proper permissions to the user.\n"
    intro += "Emphasize that the RBAC permissions are DIFFERENT between the user and a possible "
    intro += "service account which is in use by the MCP server.\n"
    intro += "If we get a json object back explain that it's NOT a "
    intro += "problem with INSIGHTS_CLIENT_ID or INSIGHTS_CLIENT_SECRET but only a problem with RBAC permissions.\n"

    return f"{intro}{response}"
