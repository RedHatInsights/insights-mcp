"""Tests for list_hosts workspace filters."""

from http import HTTPMethod
from typing import Any
from unittest.mock import Mock

import pytest

from inventory_mcp.server import list_hosts

from .conftest import list_hosts_kwargs


class TestListHostsWorkspaceFilters:
    """Test suite for workspace_id and workspace_name filters on list_hosts()."""

    @pytest.mark.asyncio
    async def test_list_hosts_without_workspace_filters(
        self,
        inventory_mock_client: Mock,
        mock_host_list_response: dict[str, Any],
    ) -> None:
        """Workspace filters are omitted when unset."""
        endpoint = "hosts"
        query = {"per_page": 10, "page": 1}
        inventory_mock_client.api.register(HTTPMethod.GET, endpoint, query=query, response_body=mock_host_list_response)
        await list_hosts(**list_hosts_kwargs())

        inventory_mock_client.get.assert_called_once_with(endpoint, params=query)

    @pytest.mark.asyncio
    async def test_list_hosts_workspace_id_filter(
        self,
        inventory_mock_client: Mock,
        mock_host_list_response: dict[str, Any],
    ) -> None:
        """workspace_id is passed as the non-deprecated Inventory query parameter."""
        workspace_id = "7c3a1d2e-4f56-7890-abcd-ef1234567890"
        endpoint = "hosts"
        query = {"workspace_id": workspace_id, "per_page": 10, "page": 1}
        inventory_mock_client.api.register(HTTPMethod.GET, endpoint, query=query, response_body=mock_host_list_response)
        await list_hosts(**list_hosts_kwargs(workspace_id=workspace_id))

        inventory_mock_client.get.assert_called_once_with(endpoint, params=query)

    @pytest.mark.asyncio
    async def test_list_hosts_workspace_name_filter(
        self,
        inventory_mock_client: Mock,
        mock_host_list_response: dict[str, Any],
    ) -> None:
        """workspace_name is passed as the non-deprecated Inventory query parameter."""
        endpoint = "hosts"
        query = {"workspace_name": "mcp_test", "per_page": 10, "page": 1}
        inventory_mock_client.api.register(HTTPMethod.GET, endpoint, query=query, response_body=mock_host_list_response)
        await list_hosts(**list_hosts_kwargs(workspace_name="mcp_test"))

        inventory_mock_client.get.assert_called_once_with(endpoint, params=query)
