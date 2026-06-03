"""Helpers for the Planning MCP upcoming-changes tool."""

from __future__ import annotations

from logging import Logger

from insights_mcp.client import InsightsClient
from tools.common import fetch_insights_json


async def get_upcoming_changes(
    insights_client: InsightsClient,
    logger: Logger | None = None,
) -> str:
    """Call GET /upcoming-changes and return a JSON-encoded response."""
    return await fetch_insights_json(
        insights_client,
        "upcoming-changes",
        operation="upcoming changes",
        logger=logger,
    )
