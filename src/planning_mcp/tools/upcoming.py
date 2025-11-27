"""Helpers for the Planning MCP upcoming-changes tool."""

from __future__ import annotations

import json
from logging import Logger
from typing import Any

from insights_mcp.client import InsightsClient


async def get_upcoming_changes(
    insights_client: InsightsClient,
    logger: Logger | None = None,
) -> str:
    """Call GET /upcoming-changes and return a JSON-encoded response."""
    try:
        response: dict[str, Any] | str = await insights_client.get("upcoming-changes")

        # The underlying client may already return a JSON string; if so, pass it through.
        if isinstance(response, str):
            return response

        # Otherwise, encode the dict to a JSON string for the MCP client.
        return json.dumps(response)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        error_detail = f"Error retrieving upcoming changes: {exc}"
        if logger:
            logger.error(error_detail)
        return f"Error: API Error - {error_detail}"
