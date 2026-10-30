"""Unit tests for LLM transient gateway error detection and retry settings."""

from __future__ import annotations

import httpx
import openai
import pytest

from tests.mcp_llm_eval.llm_transient_errors import (
    is_transient_llm_http_error,
    matrix_llm_http_max_retries,
    transient_llm_retry_delay_seconds,
    transient_llm_workflow_attempts,
)


def _api_status_error(status_code: int, body: str) -> openai.APIStatusError:
    request = httpx.Request("POST", "https://models.example/v1/chat/completions")
    response = httpx.Response(status_code, text=body, request=request)
    return openai.APIStatusError("error", response=response, body=body)


def test_is_transient_llm_http_error_api_status_504() -> None:
    exc = _api_status_error(504, "<html><h1>504 Gateway Time-out</h1></html>")
    assert is_transient_llm_http_error(exc)


def test_is_transient_llm_http_error_api_status_400() -> None:
    exc = _api_status_error(400, '{"error":"bad request"}')
    assert not is_transient_llm_http_error(exc)


def test_is_transient_llm_http_error_internal_server_error() -> None:
    exc = openai.InternalServerError(
        "<html><body><h1>504 Gateway Time-out</h1></body></html>",
        response=_api_status_error(504, "").response,
        body=None,
    )
    assert is_transient_llm_http_error(exc)


def test_is_transient_llm_http_error_gateway_html_in_message() -> None:
    assert is_transient_llm_http_error(RuntimeError("upstream returned 504 Gateway Time-out"))


def test_is_transient_llm_http_error_rate_limit() -> None:
    exc = openai.RateLimitError(
        "rate limited",
        response=_api_status_error(429, "").response,
        body=None,
    )
    assert is_transient_llm_http_error(exc)


def test_transient_llm_retry_delay_exponential() -> None:
    assert transient_llm_retry_delay_seconds(0) == transient_llm_retry_delay_seconds(1) / 2


def test_transient_llm_workflow_attempts_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_LLM_TRANSIENT_RETRIES", raising=False)
    assert transient_llm_workflow_attempts() == 3


def test_transient_llm_workflow_attempts_zero_disables_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_LLM_TRANSIENT_RETRIES", "0")
    assert transient_llm_workflow_attempts() == 1


def test_matrix_llm_http_max_retries_allows_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_LLM_MATRIX_MAX_RETRIES", "0")
    assert matrix_llm_http_max_retries() == 0


def test_transient_retries_rejects_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_LLM_TRANSIENT_RETRIES", "-1")
    with pytest.raises(ValueError, match="got -1, want a non-negative integer"):
        transient_llm_workflow_attempts()
