"""Pytest fixtures for selecting the Insights API used by LLM tests."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from tests.mock_insights_api import MockInsightsHTTPServer, create_mock_insights_api
from tests.mock_insights_api.openapi import fetch_openapi_documents

INSIGHTS_LLM_API_MODE_ENV = "INSIGHTS_LLM_API_MODE"
_LLM_API_MODES = frozenset({"live", "mock"})


def get_llm_api_mode() -> str:
    """Return the configured LLM-test API mode, defaulting to the local mock."""
    mode = os.getenv(INSIGHTS_LLM_API_MODE_ENV, "mock").strip().lower()
    if mode not in _LLM_API_MODES:
        valid_modes = ", ".join(sorted(_LLM_API_MODES))
        raise ValueError(f"{INSIGHTS_LLM_API_MODE_ENV} must be one of {valid_modes}; got {mode!r}")
    return mode


@pytest.fixture(scope="session")
def insights_llm_api_mode() -> str:
    """Select the mock API by default or the explicitly requested live API."""
    return get_llm_api_mode()


@pytest.fixture(scope="session")
def mock_insights_http_server(request: pytest.FixtureRequest) -> Iterator[MockInsightsHTTPServer | None]:
    """Run the catalog-backed Insights API when the LLM tests use mock mode."""
    api_mode = request.getfixturevalue("insights_llm_api_mode")
    if api_mode == "live":
        yield None
        return

    openapi_documents = fetch_openapi_documents()
    with MockInsightsHTTPServer(create_mock_insights_api(openapi_documents=openapi_documents)) as server:
        yield server


@pytest.fixture(scope="session")
def llm_mcp_stdio_env(request: pytest.FixtureRequest) -> dict[str, str] | None:
    """Return environment overrides for stdio MCP children in mock mode."""
    mock_server = request.getfixturevalue("mock_insights_http_server")
    if mock_server is None:
        return None
    return {"INSIGHTS_BASE_URL": mock_server.base_url}
