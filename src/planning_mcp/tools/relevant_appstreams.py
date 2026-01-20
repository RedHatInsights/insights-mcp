"""Helpers for the Planning MCP relevant appstreams lifecycle tool."""
# pylint: disable=duplicate-code

from __future__ import annotations

import json
from logging import Logger
from typing import Any

from insights_mcp.client import InsightsClient
from planning_mcp.common import normalise_bool as _normalise_bool
from planning_mcp.common import normalise_int as _normalise_int


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
    try:
        major_int = _normalise_int("major", major)
        minor_int = _normalise_int("minor", minor)
        include_related_bool = _normalise_bool("include_related", include_related)

        if minor_int is not None and major_int is None:
            raise ValueError("The 'minor' parameter requires 'major' to be specified")

        params: dict[str, Any] = {}
        if major_int is not None:
            params["major"] = major_int
        if minor_int is not None:
            params["minor"] = minor_int
        if include_related_bool is not None:
            params["related"] = include_related_bool

        response: dict[str, Any] | str = await insights_client.get(
            "relevant/lifecycle/app-streams",
            params=params,
            timeout=30,
        )

        # The underlying client may already return a JSON string; if so, pass it through.
        if isinstance(response, str):
            return response

        # Otherwise, encode the dict to a JSON string for the MCP client.
        return json.dumps(response)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        error_detail = f"Error retrieving relevant appstreams: {exc}"
        if logger:
            logger.error(error_detail)
        return f"Error: API Error - {error_detail}"
