"""Query-parameter helpers shared by the mock API route projections."""

from __future__ import annotations

from datetime import datetime
from typing import overload

from tests.mock_insights_api.types import MockRequest


def query_text(request: MockRequest, name: str, default: str = "") -> str:
    """Return one query parameter as text."""
    return str(request.query.get(name, default))


def query_values(request: MockRequest, name: str) -> tuple[str, ...]:
    """Return comma-separated query values with surrounding whitespace removed."""
    value = query_text(request, name)
    return tuple(item.strip() for item in value.split(",") if item.strip())


@overload
def query_int(request: MockRequest, name: str, default: int) -> int: ...


@overload
def query_int(request: MockRequest, name: str, default: None) -> int | None: ...


def query_int(request: MockRequest, name: str, default: int | None) -> int | None:
    """Return one query parameter as an integer or the supplied default."""
    try:
        return int(query_text(request, name, str(default)))
    except ValueError:
        return default


def query_bool(request: MockRequest, name: str, default: bool | None = None) -> bool | None:
    """Return one query parameter as a boolean or the supplied default."""
    value = query_text(request, name).casefold()
    return {"true": True, "false": False}.get(value, default)


def query_float(request: MockRequest, name: str, default: float) -> float:
    """Return one query parameter as a float or the supplied default."""
    try:
        return float(query_text(request, name, str(default)))
    except ValueError:
        return default


def query_datetime(request: MockRequest, name: str) -> datetime | None:
    """Return one ISO datetime query parameter or ``None``."""
    value = query_text(request, name)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def query_bool_values(request: MockRequest, name: str) -> set[bool]:
    """Return recognized comma-separated boolean query values."""
    return {
        value.casefold() == "true" for value in query_values(request, name) if value.casefold() in {"true", "false"}
    }
