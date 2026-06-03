"""Helpers for the Planning MCP relevant-rhel-lifecycle tool."""

from __future__ import annotations

from logging import Logger

from insights_mcp.client import InsightsClient
from tools.common import RelevantLifecycleRequest, fetch_relevant_lifecycle


async def get_relevant_rhel_lifecycle(
    insights_client: InsightsClient,
    logger: Logger | None = None,
    major: int | str | None = None,
    minor: int | str | None = None,
    include_related: bool | str = False,
) -> str:
    """Call GET relevant/lifecycle/rhel and return a JSON-encoded response."""
    return await fetch_relevant_lifecycle(
        insights_client,
        RelevantLifecycleRequest(
            endpoint="relevant/lifecycle/rhel",
            operation="relevant RHEL lifecycle",
            major=major,
            minor=minor,
            include_related=include_related,
        ),
        logger,
    )
