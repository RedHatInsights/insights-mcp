"""Fixtures for inventory MCP unit tests and LLM integration tests."""

from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from inventory_mcp.server import mcp
from tests.conftest import llm_api_context
from tests.mcp_llm_eval.fixtures import test_agent, verbose_logger

__all__ = ["llm_api_context", "mcp_server_url", "test_agent", "verbose_logger"]


@pytest.fixture(scope="session")
def mcp_server_url(request):
    """Start MCP server with only the inventory toolset for LLM integration tests."""
    transport = getattr(request, "param", "http")
    if hasattr(request.node, "callspec") and "transport" in request.node.callspec.params:
        transport = request.node.callspec.params["transport"]

    server_url, server_process = start_insights_mcp_server(transport, toolset="inventory")

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)


@pytest.fixture
def inventory_mock_client() -> AsyncMock:
    """Create an async mock InsightsClient for Inventory tests."""
    return AsyncMock()


@pytest.fixture
def mock_workspace_list_response() -> dict[str, Any]:
    """Paginated Inventory groups list matching a console workspaces page."""
    return {
        "total": 2,
        "count": 2,
        "page": 1,
        "per_page": 10,
        "results": [
            {
                "id": "7c3a1d2e-4f56-7890-abcd-ef1234567890",
                "name": "mcp_test",
                "ungrouped": False,
                "host_count": 3,
                "org_id": "12345678",
                "account": "6089719",
                "created": "2025-09-10T09:00:00.000000+00:00",
                "updated": "2025-09-10T09:20:07.000000+00:00",
            },
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "name": "Ungrouped Hosts",
                "ungrouped": True,
                "host_count": 12,
                "org_id": "12345678",
                "account": "6089719",
                "created": "2024-01-15T12:00:00.000000+00:00",
                "updated": "2025-09-10T09:20:07.000000+00:00",
            },
        ],
    }


@pytest.fixture
def mock_host_list_response() -> dict[str, Any]:
    """Paginated host list for a workspace."""
    return {
        "total": 1,
        "count": 1,
        "page": 1,
        "per_page": 10,
        "results": [
            {
                "id": "11111111-2222-3333-4444-555555555555",
                "display_name": "web-server-prod-01.example.com",
                "fqdn": "web-server-prod-01.example.com",
                "groups": [
                    {
                        "id": "7c3a1d2e-4f56-7890-abcd-ef1234567890",
                        "name": "mcp_test",
                        "ungrouped": False,
                    }
                ],
            }
        ],
    }


@contextmanager
def setup_inventory_mock(
    mock_client: AsyncMock,
    mock_response: dict[str, Any] | str | None = None,
    side_effect: BaseException | None = None,
):
    """Patch the inventory MCP client's GET method."""
    if side_effect is not None:
        mock_client.get.side_effect = side_effect
    else:
        mock_client.get.return_value = mock_response
    with patch.object(mcp, "insights_client", mock_client):
        yield


def inventory_host_filter_kwargs(**overrides: Any) -> dict[str, Any]:
    """Default host-filter kwargs shared by list_hosts and dashboard unit tests."""
    params: dict[str, Any] = {
        "hostname_or_id": "",
        "display_name": "",
        "fqdn": "",
        "tags": "",
        "staleness": "",
        "registered_with": "",
        "provider_type": "",
        "workspace_id": "",
        "workspace_name": "",
        "per_page": 10,
        "page": 1,
        "order_by": "",
        "order_how": "ASC",
    }
    params.update(overrides)
    return params


def list_hosts_kwargs(**overrides: Any) -> dict[str, Any]:
    """Default arguments for calling list_hosts from unit tests."""
    params = inventory_host_filter_kwargs()
    params["updated_start"] = ""
    params["updated_end"] = ""
    params.update(overrides)
    return params
