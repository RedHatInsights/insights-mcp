"""Red Hat Insights Host Inventory MCP Server.

MCP server for host inventory data via Red Hat Insights API.
Provides tools to get host inventory data for systems connected to Insights.
"""

import logging
from pathlib import Path
from typing import Annotated, Any

from fastmcp import Context
from fastmcp.apps import UI_EXTENSION_ID, AppConfig, ResourceCSP
from fastmcp.tools import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from insights_mcp.dashboard_ui import load_dashboard_html
from insights_mcp.mcp import InsightsMCP

_to_client_logger = get_logger(name="fastmcp.server.context.to_client")
_to_client_logger.setLevel(level=logging.DEBUG)

# --- MCP Apps UI resource URIs ---
INVENTORY_DASHBOARD_RESOURCE_URI = "ui://inventory-dashboard"
INVENTORY_DASHBOARD_MOUNTED_URI = "ui://inventory_/inventory-dashboard"


def _load_inventory_dashboard_html() -> str:
    """Load the inventory dashboard HTML."""
    return load_dashboard_html(
        "inventory_mcp",
        "inventory_dashboard.html",
        "inventory_dashboard.css",
        Path(__file__).parent,
        dashboard_title="Inventory",
    )


EMBEDDED_INVENTORY_DASHBOARD_HTML = _load_inventory_dashboard_html()

# For the API documentation, see:
# https://github.com/RedHatInsights/insights-host-inventory/tree/master/swagger

mcp = InsightsMCP(
    name="$container_brand_long Inventory MCP Server",
    toolset_name="inventory",
    api_path="api/inventory/v1",
    instructions="""
    This server provides tools to get host inventory data for systems connected to $container_brand_long.
    You can get information about connected systems, their operating systems, installed packages, etc.

    $container_brand_long Host Inventory requires correct RBAC permissions to be able to use the tools. Ensure that your
    Service Account has at least this role:
    - Inventory Hosts viewer

    """,
)


# --- MCP Apps resource registration ---


@mcp.resource(
    INVENTORY_DASHBOARD_RESOURCE_URI,
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
def inventory_dashboard_ui() -> str:
    """Inventory Dashboard UI for browsing fleet and system profiles."""
    return EMBEDDED_INVENTORY_DASHBOARD_HTML


@mcp.tool(
    annotations={"readOnlyHint": True},
    app=AppConfig(resource_uri=INVENTORY_DASHBOARD_MOUNTED_URI),
)
async def load_inventory_dashboard(ctx: Context, hosts: list[dict[str, Any]]) -> ToolResult:
    """Render host data in the interactive Inventory Dashboard.

    Call this tool with host data (the results array from a list_hosts response) to display
    it in an interactive dashboard with search, staleness filters, host details, system
    profiles, and cross-linking to CVEs affecting each host.

    Args:
        hosts: List of host objects from a list_hosts response (the 'results' array).
    """
    n = len(hosts)
    ui_supported = ctx.client_supports_extension(UI_EXTENSION_ID)
    await ctx.info(f"load_inventory_dashboard called | UI supported: {ui_supported} | hosts: {n}")
    if ui_supported:
        return ToolResult(
            content=(
                f"Dashboard rendered with {n} hosts. "
                "Do NOT print a full host table — the user can see it in the dashboard. "
                "Print only a brief summary and suggest next steps."
            ),
            structured_content={"results": hosts},
        )
    return ToolResult(
        content=(
            "Client does not support interactive dashboards. "
            "Print the full host table as markdown using the data from your previous list_hosts call."
        ),
    )


@mcp.tool(annotations={"readOnlyHint": True})
async def list_hosts(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    hostname_or_id: Annotated[str, Field("", description="Filter by display_name, fqdn, or id (case-insensitive).")],
    display_name: Annotated[str, Field("", description="Filter by display name (case-insensitive).")],
    fqdn: Annotated[str, Field("", description="Filter by FQDN (case-insensitive).")],
    tags: Annotated[str, Field("", description="Filter by tags (e.g., 'ns1/key1=val1,ns2/key2=val2').")],
    staleness: Annotated[
        str, Field("", description="Filter by staleness status (one of 'fresh', 'stale', 'stale_warning', 'unknown').")
    ],
    registered_with: Annotated[str, Field("", description="Filter by reporter that registered the host.")],
    provider_type: Annotated[str, Field("", description="Filter by provider type (e.g., 'aws', 'azure', 'gcp').")],
    updated_start: Annotated[str, Field("", description="Filter hosts updated after this timestamp (RFC3339).")],
    updated_end: Annotated[str, Field("", description="Filter hosts updated before this timestamp (RFC3339).")],
    per_page: Annotated[
        int,
        Field(
            10,
            description=(
                "Number of hosts to return per page "
                "**ALWAYS use the default value of 10 for the first call.** "
                "This default is carefully chosen for performance and context management. "
                "Only increase this value if the user explicitly asks to see more systems at once "
            ),
        ),
    ],
    page: Annotated[int, Field(1, description="Page number to return.")],
    order_by: Annotated[str, Field("", description="Field to sort by ('display_name', 'updated', 'created').")],
    order_how: Annotated[str, Field("ASC", description="Sort direction ('ASC' or 'DESC').")],
) -> dict[str, Any] | str:
    """List hosts with filtering and sorting options.
    CRITICAL: For the 'per_page' parameter, you MUST use a value of 10 on the first call to avoid performance
    degradation and context overflow.
    Only use a larger value if the user explicitly requests to see more systems at once.
    """
    params: dict[str, Any] = {}

    if hostname_or_id:
        params["hostname_or_id"] = hostname_or_id
    if display_name:
        params["display_name"] = display_name
    if fqdn:
        params["fqdn"] = fqdn
    if tags:
        params["tags"] = tags
    if staleness:
        params["staleness"] = staleness
    if registered_with:
        params["registered_with"] = registered_with
    if provider_type:
        params["provider_type"] = provider_type
    if updated_start:
        params["updated_start"] = updated_start
    if updated_end:
        params["updated_end"] = updated_end
    if order_by:
        params["order_by"] = order_by
        params["order_how"] = order_how

    params["per_page"] = min(per_page, 100)
    params["page"] = page

    response = await mcp.insights_client.get("hosts", params=params)
    if isinstance(response, str):
        return response
    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def get_host_details(host_ids: str) -> dict[str, Any] | str:
    """Get detailed information for specific hosts by their IDs.

    Returns comprehensive host data including identifiers (insights_id, satellite_id, bios_uuid),
    display names, network info (IP/MAC addresses), cloud provider details, account/org metadata,
    timestamps (created, updated, stale_timestamp), reporter info, groups, facts, and basic
    system_profile data.

    Args:
        host_ids: Comma-separated list of host IDs (UUIDs) to retrieve.
    """
    response = await mcp.insights_client.get(f"hosts/{host_ids}")
    if isinstance(response, str):
        return response
    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def get_host_system_profile(
    host_ids: Annotated[
        str,
        Field(
            "",
            description=(
                "Comma-separated list of host IDs (UUIDs) to get system profiles for. "
                "ALWAYS supply one or two UUIDs at a time! "
                "Expect really large responses which will overload your context."
            ),
        ),
    ],
) -> dict[str, Any] | str:
    """Get detailed system profile information for specific hosts.

    Returns comprehensive hardware and software configuration data including CPU details
    (model, count, cores per socket), memory info (system_memory_bytes), infrastructure
    details (type, vendor), network interfaces, disk devices, BIOS information, and
    various system state data. For RHEL hosts, also includes software information such as
    enabled repositories, installed packages, and enabled services. This provides the most
    detailed technical specifications for each host.
    """
    response = await mcp.insights_client.get(f"hosts/{host_ids}/system_profile")
    if isinstance(response, str):
        return response
    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def get_host_tags(host_ids: str) -> dict[str, Any] | str:
    """Get tags for specific hosts.

    Args:
        host_ids: Comma-separated list of host IDs (UUIDs) to get tags for.
    """
    response = await mcp.insights_client.get(f"hosts/{host_ids}/tags")
    if isinstance(response, str):
        return response
    return response


@mcp.tool(annotations={"readOnlyHint": True})
async def find_host_by_name(hostname: str) -> dict[str, Any] | str:
    """Find a host by its hostname/display name.

    Args:
        hostname: The hostname or display name to search for.
    """
    response = await mcp.insights_client.get("hosts", params={"hostname_or_id": hostname, "per_page": 1})
    if isinstance(response, str):
        return response
    return response
