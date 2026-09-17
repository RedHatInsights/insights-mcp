"""Helpers for the Planning MCP rhel-lifecycle tool."""

from __future__ import annotations

from logging import Logger

from insights_mcp.client import InsightsClient
from tools.common import fetch_insights_json


async def get_rhel_lifecycle(insights_client: InsightsClient, logger: Logger | None = None) -> str:
    """Call GET /lifecycle/rhel and return a JSON-encoded response."""
    return await fetch_insights_json(
        insights_client,
        "lifecycle/rhel",
        operation="RHEL lifecycle data",
        logger=logger,
    )
