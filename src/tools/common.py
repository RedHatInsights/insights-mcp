"""Shared functions for Insights MCP tools."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from logging import Logger
from typing import Any, NoReturn

from insights_mcp.client import InsightsClient
from insights_mcp.errors import InsightsApiError

# Wrapped when mapping tool input or transport failures to InsightsApiError (not bare Exception).
TOOL_REQUEST_ERRORS = (ValueError, RuntimeError)


@dataclass(frozen=True)
class InsightsGetRequest:
    """Optional parameters for an Insights client GET call."""

    params: dict[str, Any] | None = None
    timeout: int | None = None


@dataclass(frozen=True)
class RelevantInventoryFilters:
    """Major/minor inventory filters for relevant/* planning endpoints."""

    major: int | str | None = None
    minor: int | str | None = None
    extra_params: dict[str, Any] | None = None


@dataclass(frozen=True)
class RelevantLifecycleRequest:
    """Request parameters for relevant lifecycle endpoints with optional ``related`` filter."""

    endpoint: str
    operation: str
    major: int | str | None = None
    minor: int | str | None = None
    include_related: bool | str = True


def normalise_int(name: str, value: int | str | None) -> int | None:
    """Normalise value to an int (or None) - tolerate string input from MCP clients.

    Args:
        name: The name of the parameter being validated.
        value: The value to normalise.

    Returns:
        The normalised integer value, or None if the input was None or an
        empty/whitespace string.
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, bool):  # Boolean is subclass of int
        raise ValueError(f"Parameter '{name}' must be an integer; got '{value}' of type '{type(value).__name__}'.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Strip and convert; surface a clean error if it is not an integer string.
        value_str = value.strip()
        try:
            return int(value_str)
        except ValueError as exc:
            raise ValueError(
                f"Parameter '{name}' must be convertible to integer; got '{value}' of type '{type(value).__name__}'."
            ) from exc

    # Raise exception in case of any other type provided
    raise ValueError(f"Parameter '{name}' must be an integer; got '{value}' of type '{type(value).__name__}'.")


def normalise_bool(name: str, value: bool | str | None) -> bool | None:
    """Normalise value to an boolean (or None) - tolerate string input from MCP clients."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # Strip whitechars and convert to lowercase
        value_str = value.strip().casefold()

        if value_str == "true":
            return True
        if value_str == "false":
            return False
        raise ValueError(
            f"Parameter '{name}' must be convertible to boolean ('true'/'false'); "
            f"got '{value}' of type '{type(value).__name__}'."
        )

    # Raise exception in case of any other type provided
    raise ValueError(f"Parameter '{name}' must be a boolean; got '{value}' of type '{type(value).__name__}'.")


def encode_insights_json_response(response: dict[str, Any] | str | list[Any]) -> str:
    """Encode an Insights API response as a JSON string for MCP tool output.

    Args:
        response: Dict/list from the client, or an already-serialized JSON string.

    Returns:
        JSON text suitable for returning from an MCP tool.
    """
    if isinstance(response, str):
        return response
    return json.dumps(response)


def raise_insights_tool_error(
    exc: Exception,
    message: str,
    logger: Logger | None = None,
) -> NoReturn:
    """Log and re-raise a tool failure as InsightsApiError.

    Args:
        exc: The original exception to chain.
        message: Full error message for the MCP client (caller defines wording).
        logger: Optional logger; when set, logs the message at error level.

    Raises:
        InsightsApiError: Always raised with ``message`` chained from ``exc``.
    """
    if logger:
        logger.error(message)
    raise InsightsApiError(message) from exc


def planning_api_error_message(operation: str, exc: Exception) -> str:
    """Build the standard planning toolset API error message."""
    error_detail = f"Error retrieving {operation}: {exc}"
    return f"Error: API Error - {error_detail}"


def validate_minor_requires_major(minor_int: int | None, major_int: int | None) -> None:
    """Raise when minor is set without a major version filter."""
    if minor_int is not None and major_int is None:
        raise ValueError("The 'minor' parameter requires 'major' to be specified")


def build_major_minor_params(
    major_int: int | None,
    minor_int: int | None,
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build query parameters for relevant/inventory-filtered Insights GET requests."""
    params: dict[str, Any] = dict(extra_params or {})
    if major_int is not None:
        params["major"] = major_int
    if minor_int is not None:
        params["minor"] = minor_int
    return params or None


async def run_planning_tool_with_errors(
    operation: Callable[[], Awaitable[str]],
    operation_name: str,
    logger: Logger | None = None,
) -> str:
    """Run a planning tool coroutine and map failures to InsightsApiError."""
    try:
        return await operation()
    except TOOL_REQUEST_ERRORS as exc:
        raise_insights_tool_error(
            exc,
            planning_api_error_message(operation_name, exc),
            logger,
        )


async def run_insights_tool_request(
    request: Awaitable[dict[str, Any] | str | list[Any]],
    *,
    error_message: Callable[[Exception], str],
    logger: Logger | None = None,
) -> str:
    """Await an Insights client call, encode JSON, and map failures to InsightsApiError."""
    try:
        response = await request
        return encode_insights_json_response(response)
    except TOOL_REQUEST_ERRORS as exc:
        raise_insights_tool_error(exc, error_message(exc), logger)


def build_include_related_params(include_related: bool | str) -> dict[str, Any] | None:
    """Build optional ``related`` query parameter for relevant lifecycle endpoints."""
    include_related_bool = normalise_bool("include_related", include_related)
    extra_params: dict[str, Any] = {}
    if include_related_bool is not None:
        extra_params["related"] = include_related_bool
    return extra_params or None


async def fetch_relevant_inventory_json(
    insights_client: InsightsClient,
    endpoint: str,
    *,
    operation: str,
    logger: Logger | None = None,
    filters: RelevantInventoryFilters | None = None,
) -> str:
    """GET a relevant/* endpoint with optional major/minor inventory filters."""
    inventory_filters = filters or RelevantInventoryFilters()
    major_int = normalise_int("major", inventory_filters.major)
    minor_int = normalise_int("minor", inventory_filters.minor)

    async def _load_relevant() -> str:
        validate_minor_requires_major(minor_int, major_int)
        params = build_major_minor_params(major_int, minor_int, inventory_filters.extra_params)
        return await run_insights_tool_request(
            insights_client.get(endpoint, params=params, timeout=30),
            error_message=lambda exc: planning_api_error_message(operation, exc),
            logger=logger,
        )

    return await run_planning_tool_with_errors(_load_relevant, operation, logger)


async def fetch_relevant_lifecycle(
    insights_client: InsightsClient,
    request: RelevantLifecycleRequest,
    logger: Logger | None = None,
) -> str:
    """GET a relevant lifecycle endpoint that supports the ``related`` filter."""
    return await fetch_relevant_inventory_json(
        insights_client,
        request.endpoint,
        operation=request.operation,
        logger=logger,
        filters=RelevantInventoryFilters(
            major=request.major,
            minor=request.minor,
            extra_params=build_include_related_params(request.include_related),
        ),
    )


async def fetch_insights_json(
    insights_client: InsightsClient,
    endpoint: str,
    *,
    operation: str,
    logger: Logger | None = None,
    request: InsightsGetRequest | None = None,
) -> str:
    """GET an Insights endpoint and return a JSON-encoded MCP tool response.

    Args:
        insights_client: The Insights API client to use for the request.
        endpoint: API path relative to the toolset base URL.
        operation: Human-readable operation name for error messages.
        logger: Optional logger for error messages.
        params: Optional query parameters.
        timeout: Optional request timeout in seconds.

    Returns:
        JSON-encoded response string.

    Raises:
        InsightsApiError: On API or unexpected failures.
    """
    get_request = request or InsightsGetRequest()
    request_kwargs: dict[str, Any] = {}
    if get_request.params is not None:
        request_kwargs["params"] = get_request.params
    if get_request.timeout is not None:
        request_kwargs["timeout"] = get_request.timeout
    return await run_insights_tool_request(
        insights_client.get(endpoint, **request_kwargs),
        error_message=lambda exc: planning_api_error_message(operation, exc),
        logger=logger,
    )
