"""Tests for list_workspaces, get_workspace, and list_workspace_hosts."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from insights_mcp.errors import InsightsApiError
from inventory_mcp.server import get_workspace, list_workspace_hosts, list_workspaces

from .conftest import setup_inventory_mock


class TestListWorkspaces:
    """Test suite for list_workspaces()."""

    @pytest.mark.asyncio
    async def test_list_workspaces_defaults_group_type_all(
        self,
        inventory_mock_client: AsyncMock,
        mock_workspace_list_response: dict[str, Any],
    ) -> None:
        """Default group_type must be all so Ungrouped Hosts and user workspaces both appear."""
        with setup_inventory_mock(inventory_mock_client, mock_workspace_list_response):
            result = await list_workspaces()

        inventory_mock_client.get.assert_called_once_with(
            "groups",
            params={"group_type": "all", "per_page": 10, "page": 1},
        )
        assert result == mock_workspace_list_response
        names = [workspace["name"] for workspace in result["results"]]
        assert names == ["mcp_test", "Ungrouped Hosts"]

    @pytest.mark.asyncio
    async def test_list_workspaces_group_type_standard(
        self,
        inventory_mock_client: AsyncMock,
        mock_workspace_list_response: dict[str, Any],
    ) -> None:
        """group_type=standard is forwarded so the API hides Ungrouped Hosts."""
        with setup_inventory_mock(inventory_mock_client, mock_workspace_list_response):
            await list_workspaces(group_type="standard")

        inventory_mock_client.get.assert_called_once_with(
            "groups",
            params={"group_type": "standard", "per_page": 10, "page": 1},
        )

    @pytest.mark.asyncio
    async def test_list_workspaces_group_type_ungrouped_hosts(
        self,
        inventory_mock_client: AsyncMock,
        mock_workspace_list_response: dict[str, Any],
    ) -> None:
        """group_type=ungrouped-hosts is forwarded to the Inventory groups API."""
        with setup_inventory_mock(inventory_mock_client, mock_workspace_list_response):
            await list_workspaces(group_type="ungrouped-hosts")

        inventory_mock_client.get.assert_called_once_with(
            "groups",
            params={"group_type": "ungrouped-hosts", "per_page": 10, "page": 1},
        )

    @pytest.mark.asyncio
    async def test_list_workspaces_invalid_group_type(self, inventory_mock_client: AsyncMock) -> None:
        """Invalid group_type returns expectation and actual value without calling the API."""
        with setup_inventory_mock(inventory_mock_client, {"results": []}):
            result = await list_workspaces(group_type="root")

        assert result == {
            "error": "invalid group_type: got 'root', want one of all, standard, ungrouped-hosts",
        }
        inventory_mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_workspaces_name_filter(
        self,
        inventory_mock_client: AsyncMock,
        mock_workspace_list_response: dict[str, Any],
    ) -> None:
        """Name filter is passed as the Inventory groups name query parameter."""
        with setup_inventory_mock(inventory_mock_client, mock_workspace_list_response):
            await list_workspaces(name="mcp_test")

        inventory_mock_client.get.assert_called_once_with(
            "groups",
            params={"group_type": "all", "per_page": 10, "page": 1, "name": "mcp_test"},
        )

    @pytest.mark.asyncio
    async def test_list_workspaces_pagination_cap(
        self,
        inventory_mock_client: AsyncMock,
        mock_workspace_list_response: dict[str, Any],
    ) -> None:
        """per_page is capped at 100 even when a larger value is requested."""
        with setup_inventory_mock(inventory_mock_client, mock_workspace_list_response):
            await list_workspaces(per_page=500, page=2, order_by="host_count", order_how="DESC")

        inventory_mock_client.get.assert_called_once_with(
            "groups",
            params={
                "group_type": "all",
                "per_page": 100,
                "page": 2,
                "order_by": "host_count",
                "order_how": "DESC",
            },
        )

    @pytest.mark.asyncio
    async def test_list_workspaces_api_error(self, inventory_mock_client: AsyncMock) -> None:
        """API failures propagate as InsightsApiError."""
        with setup_inventory_mock(
            inventory_mock_client,
            side_effect=InsightsApiError("Failed to list groups: 403 Forbidden"),
        ):
            with pytest.raises(InsightsApiError, match="Failed to list groups: 403 Forbidden"):
                await list_workspaces()


class TestGetWorkspace:
    """Test suite for get_workspace()."""

    @pytest.mark.asyncio
    async def test_get_workspace_by_id(
        self,
        inventory_mock_client: AsyncMock,
        mock_workspace_list_response: dict[str, Any],
    ) -> None:
        """GET groups/{id} is used to fetch workspace details."""
        workspace = mock_workspace_list_response["results"][0]
        with setup_inventory_mock(inventory_mock_client, workspace):
            result = await get_workspace("7c3a1d2e-4f56-7890-abcd-ef1234567890")

        inventory_mock_client.get.assert_called_once_with("groups/7c3a1d2e-4f56-7890-abcd-ef1234567890")
        assert result == workspace

    @pytest.mark.asyncio
    async def test_get_workspace_empty_ids(self, inventory_mock_client: AsyncMock) -> None:
        """Empty workspace_ids is rejected without calling the API."""
        with setup_inventory_mock(inventory_mock_client, {"results": []}):
            result = await get_workspace("   ")

        assert result == {
            "error": "workspace_ids must be a non-empty comma-separated list of UUIDs, got an empty value",
        }
        inventory_mock_client.get.assert_not_called()


class TestListWorkspaceHosts:
    """Test suite for list_workspace_hosts()."""

    @pytest.mark.asyncio
    async def test_list_workspace_hosts(
        self,
        inventory_mock_client: AsyncMock,
        mock_host_list_response: dict[str, Any],
    ) -> None:
        """Hosts in a workspace are fetched from groups/{id}/hosts."""
        workspace_id = "7c3a1d2e-4f56-7890-abcd-ef1234567890"
        with setup_inventory_mock(inventory_mock_client, mock_host_list_response):
            result = await list_workspace_hosts(workspace_id)

        inventory_mock_client.get.assert_called_once_with(
            f"groups/{workspace_id}/hosts",
            params={"per_page": 10, "page": 1},
        )
        assert result == mock_host_list_response

    @pytest.mark.asyncio
    async def test_list_workspace_hosts_filters(
        self,
        inventory_mock_client: AsyncMock,
        mock_host_list_response: dict[str, Any],
    ) -> None:
        """Host filters and pagination are forwarded to groups/{id}/hosts."""
        workspace_id = "7c3a1d2e-4f56-7890-abcd-ef1234567890"
        with setup_inventory_mock(inventory_mock_client, mock_host_list_response):
            await list_workspace_hosts(
                workspace_id,
                hostname_or_id="web-server-prod-01",
                tags="insights-client/group=database-servers",
                per_page=250,
                page=2,
            )

        inventory_mock_client.get.assert_called_once_with(
            f"groups/{workspace_id}/hosts",
            params={
                "hostname_or_id": "web-server-prod-01",
                "tags": "insights-client/group=database-servers",
                "per_page": 100,
                "page": 2,
            },
        )

    @pytest.mark.asyncio
    async def test_list_workspace_hosts_empty_id(self, inventory_mock_client: AsyncMock) -> None:
        """Empty workspace_id is rejected without calling the API."""
        with setup_inventory_mock(inventory_mock_client, {"results": []}):
            result = await list_workspace_hosts("  ")

        assert result == {
            "error": "workspace_id must be a non-empty UUID, got an empty value",
        }
        inventory_mock_client.get.assert_not_called()
