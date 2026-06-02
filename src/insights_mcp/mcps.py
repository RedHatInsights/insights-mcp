"""Registered Insights MCP toolset servers and toolset list resolution."""

from advisor_mcp.server import mcp_server as AdvisorMCP
from content_sources_mcp.server import mcp as ContentSourcesMCP
from image_builder_mcp.server import mcp_server as ImageBuilderMCP
from insights_mcp.mcp import InsightsMCP
from inventory_mcp.server import mcp as InventoryMCP
from planning_mcp.server import mcp as PlanningMCP
from rbac_mcp.server import mcp as RbacMCP
from remediations_mcp.server import mcp as RemediationsMCP
from rhsm_mcp.server import mcp as RhsmMCP
from vulnerability_mcp.server import mcp as VulnerabilityMCP

MCPS: list[InsightsMCP] = [
    ImageBuilderMCP,
    RhsmMCP,
    VulnerabilityMCP,
    RemediationsMCP,
    AdvisorMCP,
    InventoryMCP,
    ContentSourcesMCP,
    RbacMCP,
    PlanningMCP,
]


def resolve_toolset_list(toolset: str) -> list[str]:
    """Return toolset names for a comma-separated list or ``all``."""
    if toolset == "all":
        return [mcp.toolset_name for mcp in MCPS]
    return [t.strip() for t in toolset.split(",")]
