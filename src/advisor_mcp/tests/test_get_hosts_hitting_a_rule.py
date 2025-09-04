"""Test suite for the get_hosts_hitting_a_rule() method."""

import pytest

from .conftest import TEST_RULE_ID, setup_advisor_mock


class TestGetHostsHittingARule:
    """Test suite for the get_hosts_hitting_a_rule() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for hosts hitting a rule (obfuscated real data structure)."""
        return {"host_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890", "f9e8d7c6-b5a4-3210-9876-543210fedcba"]}

    @pytest.mark.asyncio
    async def test_get_hosts_hitting_a_rule_valid_rule_id(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_hitting_a_rule with valid rule ID."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_hosts_hitting_a_rule(rule_id=rule_id)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems/")

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.parametrize(
        "rule_id, expected_error",
        [
            ("", "Error: Recommendation ID must be a non-empty string."),
            (None, "Error: Recommendation ID must be a non-empty string."),
            (123, "Error: Recommendation ID must be a non-empty string."),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_hosts_hitting_a_rule_invalid_rule_id(self, advisor_mcp_server, rule_id, expected_error):
        """Test get_hosts_hitting_a_rule with various invalid rule IDs."""
        result = await advisor_mcp_server.get_hosts_hitting_a_rule(rule_id=rule_id)
        assert result == expected_error

    @pytest.mark.asyncio
    async def test_get_hosts_hitting_a_rule_whitespace_rule_id(self, advisor_mcp_server):
        """Test get_hosts_hitting_a_rule with whitespace-only rule ID."""
        # Call the method with whitespace-only rule_id
        result = await advisor_mcp_server.get_hosts_hitting_a_rule(rule_id="   ")

        # Should return error message
        assert result == "Error: Recommendation ID must be a non-empty string."

    @pytest.mark.asyncio
    async def test_get_hosts_hitting_a_rule_whitespace_handling(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_hitting_a_rule with whitespace in rule ID."""
        rule_id = f"  {TEST_RULE_ID}  "

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            await advisor_mcp_server.get_hosts_hitting_a_rule(rule_id=rule_id)

            # Verify API was called with trimmed rule_id
            advisor_mock_client.get.assert_called_once_with(f"rule/{TEST_RULE_ID}/systems/")

    @pytest.mark.asyncio
    async def test_get_hosts_hitting_a_rule_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_hosts_hitting_a_rule when API returns error."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            result = await advisor_mcp_server.get_hosts_hitting_a_rule(rule_id=rule_id)

            # Should return error message
            assert f"Failed to retrieve systems for recommendation {rule_id}:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    async def test_get_hosts_hitting_a_rule_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_hosts_hitting_a_rule when API returns empty response."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            result = await advisor_mcp_server.get_hosts_hitting_a_rule(rule_id=rule_id)

            # Should return None when API returns None
            assert result is None
