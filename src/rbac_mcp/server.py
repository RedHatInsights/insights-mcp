"""Red Hat Insights RBAC MCP Server.

MCP server for Role-Based Access Control (RBAC) via Red Hat Insights API.
Provides tools to diagnose permission issues and inspect caller access.
"""

from typing import Annotated, Any

from pydantic import Field

from insights_mcp.config import (
    BRAND_CLIENT_ID_ENV,
    BRAND_CLIENT_ID_HEADER,
    BRAND_CLIENT_SECRET_ENV,
    BRAND_CLIENT_SECRET_HEADER,
)
from insights_mcp.mcp import InsightsMCP
from insights_mcp.rbac.catalog import load_role_catalog
from insights_mcp.rbac.diagnose import (
    AccessDeniedCall,
    AccessDeniedInput,
    diagnose_missing_roles,
    required_roles_for_entry,
)
from insights_mcp.rbac.manifest import get_tool_entry, resolve_tool_name
from insights_mcp.rbac.principal import classify_principal_from_token
from insights_mcp.rbac.resolver import ResolvedRequirements, resolve_tool_requirements
from rbac_mcp.access import fetch_caller_access, get_access_token_from_client

mcp = InsightsMCP(
    name="$container_brand_long RBAC MCP Server",
    toolset_name="rbac",
    api_path="api/rbac/v1",
    instructions="""
    RBAC diagnostics for $container_brand_long MCP tools.

    On any 403 Forbidden from another toolset, call rbac__explain_access_denied with the
    failed tool name or request URL before suggesting permissions or roles.

    get_caller_access_all returns permissions for the authenticated principal (usually the
    MCP service account), not the human user unless Bearer user token is used.
    """,
)


@mcp.tool(annotations={"readOnlyHint": True})
async def explain_access_denied(
    failed_method: Annotated[
        str,
        Field(description="HTTP method used by the failed REST request, e.g. GET, POST, or PUT."),
    ],
    failed_tool: Annotated[
        str,
        Field(
            default="",
            description=("MCP tool that failed, e.g. vulnerability__get_system_cves (toolset__function_name)."),
        ),
    ],
    failed_url: Annotated[
        str,
        Field(
            default="",
            description="Full REST URL from the error message, if available.",
        ),
    ],
    http_status: Annotated[int, Field(default=403, description="HTTP status from the failure.")],
) -> dict[str, Any]:
    """Diagnose a 403 access denial for a specific MCP tool call.

    Returns only the console role names the caller is missing. Use this instead
    of guessing permission or role names.

    The authenticated principal is usually the MCP service account when using
    client ID/secret in the environment—not the console user in chat.
    """
    tool_key = resolve_tool_name(failed_tool, failed_url, method=failed_method) or failed_tool
    entry = get_tool_entry(tool_key) if tool_key else None

    access_payload = await fetch_caller_access(mcp.insights_client)
    if "error" in access_payload:
        return access_payload

    token = get_access_token_from_client(mcp.insights_client)
    resolved_calls: list[ResolvedRequirements] = []
    if entry is not None:
        for call in entry.rest_calls:
            resolved_calls.append(await resolve_tool_requirements(call, mcp.insights_client))
    return await diagnose_missing_roles(
        AccessDeniedInput(
            call=AccessDeniedCall(
                failed_tool=failed_tool,
                failed_url=failed_url,
                failed_method=failed_method,
                http_status=http_status,
                tool_name_resolved=tool_key,
            ),
            entry=entry,
            access_payload=access_payload,
            access_token=token,
            resolved_calls=tuple(resolved_calls),
        ),
        mcp.insights_client,
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def lookup_tool_requirements(
    tool_name: Annotated[
        str,
        Field(description="MCP tool name, e.g. inventory__find_host_by_name."),
    ],
) -> dict[str, Any]:
    """Return the console role names required for an MCP tool.

    This reports required roles without checking the authenticated caller's
    current access. Use ``explain_access_denied`` after a 403 response.
    """
    key = resolve_tool_name(tool_name, "") or tool_name
    entry = get_tool_entry(key)
    if entry is None:
        return {
            "error": f"No rest-map entry for tool {tool_name!r}.",
            "do_not_infer_other_permissions": True,
        }
    resolved_calls = []
    for call in entry.rest_calls:
        resolved_calls.append(await resolve_tool_requirements(call, mcp.insights_client))
    catalog = await load_role_catalog(mcp.insights_client)
    required_roles, unknown = required_roles_for_entry(entry, tuple(resolved_calls), catalog)
    result: dict[str, Any] = {
        "required_roles": required_roles,
        "do_not_infer_other_permissions": True,
    }
    if unknown:
        result["note"] = "Required roles for this tool could not be resolved; do not invent role names."
    return result


@mcp.tool(annotations={"readOnlyHint": True})
async def get_caller_access(
    application: Annotated[
        str,
        Field(
            description="Red Hat application name (e.g. vulnerability, inventory). Required.",
        ),
    ],
    username: Annotated[
        str,
        Field(
            default="",
            description=("Optional: query another principal's access (requires RBAC admin permission)."),
        ),
    ],
    limit: Annotated[int, Field(default=100, description="Maximum records per page.")],
    offset: Annotated[int, Field(default=0, description="Pagination offset.")],
) -> dict[str, Any] | str:
    """Get RBAC access for the authenticated caller for one application.

    Returns permissions for the identity used by this MCP server (service account
    or Bearer token)—not necessarily the human user.
    """
    if not application or not application.strip():
        return {"error": "application parameter is required and cannot be empty."}

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

    token = get_access_token_from_client(mcp.insights_client)
    response["caller_principal"] = classify_principal_from_token(token)
    response["do_not_infer_other_permissions"] = True
    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def get_caller_access_all(
    username: Annotated[
        str,
        Field(
            default="",
            description=("Optional: query another principal (requires RBAC admin). Default: authenticated MCP caller."),
        ),
    ],
) -> dict[str, Any]:
    """List all RBAC permissions for the authenticated MCP caller (paginated fetch).

    Permissions apply to the service account or Bearer identity used by MCP—not
    your console user unless that identity is what MCP uses.
    """
    payload = await fetch_caller_access(
        mcp.insights_client,
        application="",
        username=username,
    )
    if "error" in payload:
        return payload

    token = get_access_token_from_client(mcp.insights_client)
    principal = classify_principal_from_token(token)
    credential_hint = (
        f"{BRAND_CLIENT_ID_HEADER} / {BRAND_CLIENT_SECRET_HEADER}"
        if mcp.insights_client.mcp_transport in ["sse", "http"]
        else f"{BRAND_CLIENT_ID_ENV} / {BRAND_CLIENT_SECRET_ENV}"
    )
    return {
        "caller_principal": principal,
        "permissions": payload.get("permissions", []),
        "data": payload.get("data", []),
        "meta": payload.get("meta", {}),
        "notes": [
            "Permissions listed are for the authenticated MCP principal only.",
            "Grant roles to the MCP service account in User Access if using env credentials.",
            f"Credential configuration uses {credential_hint}.",
            "On 403 from another tool, call rbac__explain_access_denied.",
        ],
        "do_not_infer_other_permissions": True,
    }
