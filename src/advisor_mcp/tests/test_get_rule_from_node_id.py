"""Test suite for the get_rule_from_node_id() method."""

import ast

import pytest

from .conftest import TEST_NODE_ID, setup_advisor_mock


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
        node_id = TEST_NODE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with(f"kcs/{node_id}/")

            # Parse the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.parametrize(
        "node_id, expected_error",
        [
            ("", "Error: Node ID must be a non-empty string."),
            (None, "Error: Node ID must be a non-empty string."),
            (123456, "Error: Node ID must be a non-empty string."),
            ("123-456", "Error: Node ID must contain only alphanumeric characters."),
            ("123@#$", "Error: Node ID must contain only alphanumeric characters."),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_invalid_input(self, advisor_mcp_server, node_id, expected_error):
        """Test get_rule_from_node_id with various invalid node IDs."""
        result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)
        assert result == expected_error

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_whitespace_handling(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_rule_from_node_id with whitespace in node ID."""
        node_id = f"  {TEST_NODE_ID}  "

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            # Verify API was called with trimmed node_id
            advisor_mock_client.get.assert_called_once_with(f"kcs/{TEST_NODE_ID}/")

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_from_node_id when API returns error."""
        node_id = TEST_NODE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            # Should return error message
            assert f"Failed to retrieve recommendation for node ID {node_id}:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    async def test_get_rule_from_node_id_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_from_node_id when API returns empty response."""
        node_id = TEST_NODE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            result = await advisor_mcp_server.get_rule_from_node_id(node_id=node_id)

            # Should return appropriate message
            assert result == "No recommendation found for the given node ID."
