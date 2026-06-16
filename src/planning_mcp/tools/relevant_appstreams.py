"""Helpers for the Planning MCP relevant appstreams lifecycle tool."""

from __future__ import annotations

from logging import Logger

from insights_mcp.client import InsightsClient
from tools.common import RelevantLifecycleRequest, fetch_relevant_lifecycle


async def get_relevant_appstreams(
    insights_client: InsightsClient,
    logger: Logger | None = None,
    major: int | str | None = None,
    minor: int | str | None = None,
    include_related: bool = True,
) -> str:
    """Call GET relevant/lifecycle/app-streams and return a JSON-encoded response.

    Args:
        insights_client: The Insights API client to use for the request.
        logger: Optional logger for error messages.
        major: Restricts relevance evaluation to systems running this RHEL major version.
               Forwarded to the backend as a filter on the underlying inventory.
        minor: Used together with major to further restrict relevance evaluation to a specific
               minor version. Forwarded to the backend as a filter on the underlying inventory.
        include_related: If true, backend returns streams currently used plus related/successor
                        streams. If false, returns only streams currently used in inventory.

    Returns:
        A JSON-encoded string with the response data or an error message.
    """
    return await fetch_relevant_lifecycle(
        insights_client,
        RelevantLifecycleRequest(
            endpoint="relevant/lifecycle/app-streams",
            operation="relevant appstreams",
            major=major,
            minor=minor,
            include_related=include_related,
        ),
        logger,
    )
