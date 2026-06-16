"""Helpers for the Planning MCP relevant upcoming changes tool."""

from __future__ import annotations

from logging import Logger

from insights_mcp.client import InsightsClient
from tools.common import RelevantInventoryFilters, fetch_relevant_inventory_json


async def get_relevant_upcoming_changes(
    insights_client: InsightsClient,
    logger: Logger | None = None,
    major: int | str | None = None,
    minor: int | str | None = None,
) -> str:
    """Call GET relevant/upcoming-changes and return a JSON-encoded response.

    Args:
        insights_client: The Insights API client to use for the request.
        logger: Optional logger for error messages.
        major: Restricts relevance evaluation to systems running this RHEL major version.
               Forwarded to the backend as a filter on the underlying inventory.
        minor: Used together with major to further restrict relevance evaluation to a specific
               minor version. Forwarded to the backend as a filter on the underlying inventory.

    Returns:
        A JSON-encoded string with the response data or an error message.
    """
    return await fetch_relevant_inventory_json(
        insights_client,
        "relevant/upcoming-changes",
        operation="relevant upcoming changes",
        logger=logger,
        filters=RelevantInventoryFilters(major=major, minor=minor),
    )
