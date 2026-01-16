"""Helpers for the Planning MCP relevant appstreams lifecycle tool."""
# pylint: disable=duplicate-code

from __future__ import annotations

import json
from logging import Logger
from typing import Any

from insights_mcp.client import InsightsClient


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

        def _normalise_int(name: str, value: int | str | None) -> int | None:
            if value is None:
                return None
            if isinstance(value, int):
                return value
            s = value.strip()
            if not s:
                return None
            try:
                return int(s)
            except ValueError as exc:
                raise ValueError(f"Parameter '{name}' must be an integer (e.g. 8, 9, 10); got '{value}'.") from exc

        major_int = _normalise_int("major", major)
        minor_int = _normalise_int("minor", minor)

        if minor_int is not None and major_int is None:
            raise ValueError("The 'minor' parameter requires 'major' to be specified")

        params: dict[str, Any] = {}
        if major_int is not None:
            params["major"] = major_int
        if minor_int is not None:
            params["minor"] = minor_int
        # Map include_related to the backend's 'related' parameter
        params["related"] = "true" if include_related else "false"

        response: dict[str, Any] | str = await insights_client.get(
            "relevant/lifecycle/app-streams",
            params=params,
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
