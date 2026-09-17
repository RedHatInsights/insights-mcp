"""Helpers for the Planning MCP Application Streams lifecycle tool."""

from __future__ import annotations

from logging import Logger
from typing import Any

from insights_mcp.client import InsightsClient
from tools.common import (
    normalise_int as _normalise_int,
)
from tools.common import (
    planning_api_error_message,
    run_insights_tool_request,
    run_planning_tool_with_errors,
)


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

    async def _load_appstreams() -> str:
        if mode not in ("raw", "streams"):
            raise ValueError(f"Invalid mode '{mode}'. Expected 'raw' or 'streams'.")

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
            endpoint = "lifecycle/app-streams/streams"

        return await run_insights_tool_request(
            insights_client.get(endpoint, params=params or None),
            error_message=lambda exc: planning_api_error_message("application streams lifecycle", exc),
            logger=logger,
        )

    return await run_planning_tool_with_errors(
        _load_appstreams,
        "application streams lifecycle",
        logger,
    )
