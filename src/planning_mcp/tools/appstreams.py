"""Helpers for the Planning MCP Application Streams lifecycle tool."""

from __future__ import annotations

import json
from logging import Logger
from typing import Any

from insights_mcp.client import InsightsClient
from planning_mcp.common import normalise_int as _normalise_int


async def get_appstreams_lifecycle(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-branches
    insights_client: InsightsClient,
    mode: str = "raw",
    major: int | str | None = None,
    name: str | None = None,
    application_stream_name: str | None = None,
    application_stream_type: str | None = None,
    kind: str | None = None,
    logger: Logger | None = None,
) -> str:
    """Call Application Streams lifecycle endpoints and return a JSON-encoded response."""
    try:
        if mode not in ("raw", "streams"):
            raise ValueError(f"Invalid mode '{mode}'. Expected 'raw' or 'streams'.")

        # Normalise major to an int (or None) – tolerate string input from MCP clients.
        major_int = _normalise_int("major", major)

        params: dict[str, Any] = {}

        if name:
            params["name"] = name
        if application_stream_name:
            params["application_stream_name"] = application_stream_name
        if application_stream_type:
            params["application_stream_type"] = application_stream_type
        if kind:
            params["kind"] = kind

        if mode == "raw":
            if major_int is None:
                raise ValueError("Parameter 'major' is required when mode='raw'.")
            endpoint = f"lifecycle/app-streams/{major_int}"
        else:
            # mode == "streams"
            # Major is intentionally ignored in streams mode; overview is cross-major.
            endpoint = "lifecycle/app-streams/streams"

        # Call backend
        response = await insights_client.get(endpoint, params=params or None)

        # Pass through JSON strings; otherwise encode dict/list to JSON.
        if isinstance(response, str):
            return response

        return json.dumps(response)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        error_detail = f"Error retrieving application streams lifecycle: {exc}"
        if logger:
            logger.error(error_detail)
        # Keep the same error shape convention as upcoming.py
        return f"Error: API Error - {error_detail}"
