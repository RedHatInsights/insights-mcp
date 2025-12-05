"""Helpers for the Planning MCP Application Streams lifecycle tool."""

from __future__ import annotations

import json
from logging import Logger
from typing import Any

from insights_mcp.client import InsightsClient


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
    """Call Application Streams lifecycle endpoints and return a JSON-encoded response.

    This helper implements the behaviour for the Planning MCP
    `get_appstreams_lifecycle` tool.

    Modes:
        - raw:
            Calls:   GET /lifecycle/app-streams/{major_version}
            Purpose: Fine-grained lifecycle rows (modules + packages) for a single RHEL major.

        - streams:
            Calls:   GET /lifecycle/app-streams/streams
            Purpose: Cross-major Application Stream overview.

    Args:
        insights_client: Initialised InsightsClient used to call the backend API.
        mode: Operating mode, either "raw" (default) or "streams".
        major: RHEL major version (e.g. 8, 9, 10). Required when mode="raw".
               May be provided as an int or as a string (e.g. "9").
        name: Technical module/package name filter (e.g. "postgresql").
        application_stream_name: Human-friendly stream name (e.g. ".NET 7").
        application_stream_type: Backend-supported stream type (e.g. "module", "package").
        kind: Backend kind filter (e.g. "dnf_module" or "package").
        logger: Optional logger for error reporting.

    Returns:
        JSON string of the backend response, or a JSON-encoded error string
        following the standard Planning MCP error format.
    """
    try:
        # Validate mode
        if mode not in ("raw", "streams"):
            raise ValueError(f"Invalid mode '{mode}'. Expected 'raw' or 'streams'.")

        # Normalise major to an int (or None) – tolerate string input from MCP clients.
        major_int: int | None
        if major is None or (isinstance(major, str) and major.strip() == ""):
            major_int = None
        elif isinstance(major, int):
            major_int = major
        elif isinstance(major, str):
            # Strip and convert; surface a clean error if it is not an integer string.
            major_str = major.strip()
            try:
                major_int = int(major_str)
            except ValueError as exc:
                raise ValueError(f"Parameter 'major' must be an integer (e.g. 8, 9, 10); got '{major}'.") from exc
        else:
            raise ValueError(f"Parameter 'major' must be an integer or string; got type {type(major).__name__}.")

        # Build query parameters (only backend-supported filters are forwarded).
        params: dict[str, Any] = {}

        if name:
            params["name"] = name
        if application_stream_name:
            params["application_stream_name"] = application_stream_name
        if application_stream_type:
            params["application_stream_type"] = application_stream_type
        if kind:
            params["kind"] = kind

        # Select endpoint based on mode
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
