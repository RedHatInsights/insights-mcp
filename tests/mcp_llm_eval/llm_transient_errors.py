"""Detect transient LLM gateway errors and configure workflow-level retries."""

from __future__ import annotations

import os
from typing import Final

import openai

_GATEWAY_HTML_MARKERS: Final = ("504 Gateway", "502 Bad Gateway", "503 Service Unavailable")
_TRANSIENT_HTTP_STATUS_CODES: Final = frozenset({502, 503, 504})

_DEFAULT_MATRIX_LLM_MAX_RETRIES = 6
_DEFAULT_TRANSIENT_RETRY_COUNT = 2
_DEFAULT_TRANSIENT_RETRY_BASE_SECONDS = 45.0
_DEFAULT_GUARDIAN_LLM_HTTP_TIMEOUT_SECONDS = 1800.0


def _non_negative_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid {name}: got {raw!r}, want a non-negative integer") from exc
    if value < 0:
        raise ValueError(f"invalid {name}: got {value}, want a non-negative integer")
    return value


def _positive_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid {name}: got {raw!r}, want a positive number") from exc
    if value <= 0:
        raise ValueError(f"invalid {name}: got {value}, want a positive number")
    return value


def matrix_llm_http_max_retries() -> int:
    """OpenAI SDK max_retries for matrix ``OpenAILike`` chat requests.

    ``0`` disables SDK retries. The default stays high so a slow gateway can finish.
    """
    return _non_negative_int_env("MCP_LLM_MATRIX_MAX_RETRIES", _DEFAULT_MATRIX_LLM_MAX_RETRIES)


def transient_llm_workflow_attempts() -> int:
    """Total workflow attempts (initial run plus ``MCP_LLM_TRANSIENT_RETRIES`` retries).

    ``MCP_LLM_TRANSIENT_RETRIES=0`` runs the workflow once.
    """
    extra = _non_negative_int_env("MCP_LLM_TRANSIENT_RETRIES", _DEFAULT_TRANSIENT_RETRY_COUNT)
    return 1 + extra


def transient_llm_retry_base_seconds() -> float:
    """Base delay for exponential backoff between workflow retries."""
    return _positive_float_env("MCP_LLM_TRANSIENT_RETRY_BASE_SECONDS", _DEFAULT_TRANSIENT_RETRY_BASE_SECONDS)


def guardian_llm_http_timeout_seconds() -> float:
    """HTTP timeout for DeepEval guardian ``OpenAIModel`` requests."""
    return _positive_float_env("GUARDIAN_LLM_HTTP_TIMEOUT_SECONDS", _DEFAULT_GUARDIAN_LLM_HTTP_TIMEOUT_SECONDS)


def transient_llm_retry_delay_seconds(attempt_index: int) -> float:
    """Return backoff delay before workflow retry *attempt_index* (0-based)."""
    base = transient_llm_retry_base_seconds()
    return base * (2**attempt_index)


def is_transient_llm_http_error(exc: BaseException) -> bool:
    """Return whether *exc* looks like a retryable model gateway or overload failure."""
    if isinstance(
        exc,
        (
            openai.InternalServerError,
            openai.APITimeoutError,
            openai.RateLimitError,
        ),
    ):
        return True

    if isinstance(exc, openai.APIStatusError):
        return exc.status_code in _TRANSIENT_HTTP_STATUS_CODES

    message = str(exc)
    return any(marker in message for marker in _GATEWAY_HTML_MARKERS)


__all__ = [
    "guardian_llm_http_timeout_seconds",
    "is_transient_llm_http_error",
    "matrix_llm_http_max_retries",
    "transient_llm_retry_base_seconds",
    "transient_llm_retry_delay_seconds",
    "transient_llm_workflow_attempts",
]
