"""Helpers for the Planning MCP relevant-rhel-lifecycle tool."""
# pylint: disable=duplicate-code

import json
from logging import Logger
from typing import Any

from insights_mcp.client import InsightsClient
from tools.common import normalise_bool as _normalise_bool
from tools.common import normalise_int as _normalise_int


async def get_relevant_rhel_lifecycle(
    insights_client: InsightsClient,
    logger: Logger | None = None,
    major: int | str | None = None,
    minor: int | str | None = None,
    include_related: bool | str = False,
) -> str:
    """Call GET relevant/lifecycle/rhel and return a JSON-encoded response."""
    try:
        major_int = _normalise_int("major", major)
        minor_int = _normalise_int("minor", minor)
        include_related_bool = _normalise_bool("include_related", include_related)

        if minor_int is not None and major_int is None:
            raise ValueError("The 'minor' parameter requires 'major' to be specified")

        params: dict[str, Any] = {}
        if include_related_bool is not None:
            params["related"] = include_related_bool
        if major_int is not None:
            params["major"] = major_int
        if minor_int is not None:
            params["minor"] = minor_int

        response: dict[str, Any] | str = await insights_client.get(
            "relevant/lifecycle/rhel",
            params=params or None,
            timeout=30,
        )

        # The underlying client may already return a JSON string; if so, pass it through.
        if isinstance(response, str):
            return response

        # Otherwise, encode the dict to a JSON string for the MCP client.
        return json.dumps(response)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        error_detail = f"Error retrieving relevant RHEL lifecycle: {exc}"
        if logger:
            logger.error(error_detail)
        return f"Error: API Error - {error_detail}"
