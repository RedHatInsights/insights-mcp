"""Test suite for the get_rule_from_node_id() method."""

import pytest

from advisor_mcp.server import _kcs_entry_to_rule_ref
from insights_mcp.errors import InsightsApiError

from .conftest import TEST_NODE_ID, setup_toolset_mock


def _expected_rule_refs(urls: list[str]) -> list[dict[str, str]]:
    """Map KCS URL strings to the {rule_id, url} objects the tool returns."""
    return [{"rule_id": url.rsplit("/", 1)[-1], "url": url} for url in urls]


class TestGetRuleFromNodeId:
    """Test suite for the get_rule_from_node_id() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for rule from node ID (obfuscated real data structure)."""
        return [
            "console.redhat.com/insights/advisor/recommendations/test_kernel_issue|TEST_KERNEL_ISSUE_EDGE_WARN",
            "console.redhat.com/insights/advisor/recommendations/test_kernel_issue|TEST_KERNEL_ISSUE_EDGE_WARN_DEFAULT",
            "console.redhat.com/insights/advisor/recommendations/test_kernel_issue|TEST_KERNEL_ISSUE_WARN",
            "console.redhat.com/insights/advisor/recommendations/test_kernel_issue|TEST_KERNEL_ISSUE_WARN_BOOTC",
            "console.redhat.com/insights/advisor/recommendations/"
            "test_kernel_issue|TEST_KERNEL_ISSUE_WARN_BOOTC_DEFAULT",
            "console.redhat.com/insights/advisor/recommendations/test_kernel_issue|TEST_KERNEL_ISSUE_WARN_DEFAULT",
        ]

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_valid_node_id(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_rule_from_node_id with valid node ID."""
        node_id = int(TEST_NODE_ID)

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            advisor_mock_client.get.assert_called_once_with(f"kcs/{node_id}/")
            assert result == _expected_rule_refs(mock_api_response)

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_invalid_input(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_from_node_id with invalid node ID (negative number)."""
        node_id = -1

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("Invalid node ID")):
            with pytest.raises(InsightsApiError) as exc_info:
                await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            error_message = str(exc_info.value)
            assert f"Failed to retrieve recommendation for node ID {node_id}:" in error_message
            assert "Invalid node ID" in error_message

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_large_integer(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_rule_from_node_id with large integer node ID."""
        node_id = 999999999

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            advisor_mock_client.get.assert_called_once_with(f"kcs/{node_id}/")
            assert result == _expected_rule_refs(mock_api_response)

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_from_node_id when API returns error."""
        node_id = int(TEST_NODE_ID)

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            with pytest.raises(InsightsApiError) as exc_info:
                await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            error_message = str(exc_info.value)
            assert f"Failed to retrieve recommendation for node ID {node_id}:" in error_message
            assert "API Error" in error_message

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_from_node_id when API returns empty response."""
        node_id = int(TEST_NODE_ID)

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, None):
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_empty_list(self, advisor_mcp_server, advisor_mock_client):
        """An empty KCS list is returned as an empty list of rule refs."""
        node_id = int(TEST_NODE_ID)

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, []):
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            assert result == []

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_bare_rule_id(self, advisor_mcp_server, advisor_mock_client):
        """A bare rule_id (no path) is used for both rule_id and url."""
        node_id = int(TEST_NODE_ID)
        bare_id = "libdb_deprecated|LIBDB_DEPRECATED_WARN"

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, [bare_id]):
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            assert result == [{"rule_id": bare_id, "url": bare_id}]

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_rejects_non_string_entry(self, advisor_mcp_server, advisor_mock_client):
        """Non-string KCS entries fail with expectation and actual value."""
        node_id = int(TEST_NODE_ID)

        with setup_toolset_mock(advisor_mcp_server, advisor_mock_client, [123]):
            with pytest.raises(InsightsApiError) as exc_info:
                await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            error_message = str(exc_info.value)
            assert "expected a KCS URL string" in error_message
            assert "got int: 123" in error_message


def test_kcs_entry_to_rule_ref_splits_last_path_segment() -> None:
    """Last path segment is the Advisor rule_id; url keeps the API string."""
    url = "console.redhat.com/insights/advisor/recommendations/libdb_deprecated|LIBDB_DEPRECATED_WARN"
    assert _kcs_entry_to_rule_ref(url) == {
        "rule_id": "libdb_deprecated|LIBDB_DEPRECATED_WARN",
        "url": url,
    }
