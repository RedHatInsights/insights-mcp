"""Fixtures for inventory MCP unit tests and LLM integration tests."""

from typing import Any
from unittest.mock import Mock

import pytest

from inventory_mcp.server import mcp
from tests.conftest import create_mock_client, llm_api_context, toolset_mcp_server_url
from tests.mcp_llm_eval.fixtures import test_agent, verbose_logger

__all__ = ["llm_api_context", "mcp_server_url", "test_agent", "verbose_logger"]


mcp_server_url = toolset_mcp_server_url("inventory")


@pytest.fixture
def inventory_mock_client(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Create a registry-backed mock InsightsClient for Inventory tests."""
    client = create_mock_client(api_path="api/inventory/v1")
    monkeypatch.setattr(mcp, "insights_client", client)
    return client


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
