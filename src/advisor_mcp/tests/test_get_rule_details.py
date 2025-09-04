"""Test suite for the get_rule_details() method."""

import pytest

from .conftest import TEST_RULE_ID, setup_advisor_mock


class TestGetRuleDetails:
    """Test suite for the get_rule_details() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for rule details (obfuscated real data structure)."""
        return {
            "rule_id": "test_boot_failure|TEST_BOOT_FAILURE_WARN_V2",
            "created_at": "2023-11-03T08:33:48.373300Z",
            "updated_at": "2025-05-22T10:33:07.549451Z",
            "description": "The system is unable to boot when test configuration is missing",
            "active": True,
            "category": {"id": 1, "name": "Availability"},
            "impact": {"name": "Boot Failure", "impact": 4},
            "likelihood": 4,
            "node_id": "1234567",
            "tags": "test configuration boot availability",
            "playbook_count": 0,
            "reboot_required": False,
            "publish_date": "2023-11-05T02:41:00Z",
            "summary": "The system is unable to boot when test configuration is missing.",
            "generic": "The system is unable to boot when test configuration is missing.",
            "reason": "This host is running RHEL and the test configuration is missing. "
            "As a result, the system is unable to boot properly next time.",
            "more_info": "",
            "impacted_systems_count": 2,
            "reports_shown": True,
            "rule_status": "enabled",
            "resolution_set": [
                {
                    "system_type": 105,
                    "resolution": "Red Hat recommends that you reinstall the missing configuration. "
                    "Remove and reinstall the test package to regenerate the configuration.",
                    "resolution_risk": {"name": "Install Package", "risk": 1},
                    "has_playbook": False,
                }
            ],
            "total_risk": 4,
            "hosts_acked_count": 3,
            "rating": 0,
        }

    @pytest.mark.asyncio
    async def test_get_rule_details_valid_rule_id(self, advisor_mcp_server, advisor_mock_client, mock_api_response):
        """Test get_rule_details with valid rule ID."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_rule_details(rule_id=rule_id)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/")

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.parametrize(
        "rule_id, expected_error",
        [
            ("", "Error: Recommendation ID must be a non-empty string in format rule_name|ERROR_KEY."),
            (None, "Error: Recommendation ID must be a non-empty string in format rule_name|ERROR_KEY."),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_rule_details_invalid_rule_id(self, advisor_mcp_server, rule_id, expected_error):
        """Test get_rule_details with various invalid rule IDs."""
        result = await advisor_mcp_server.get_rule_details(rule_id=rule_id)
        assert result == expected_error

    @pytest.mark.asyncio
    async def test_get_rule_details_whitespace_rule_id(self, advisor_mcp_server):
        """Test get_rule_details with whitespace-only rule ID."""
        # Call the method with whitespace-only rule_id
        result = await advisor_mcp_server.get_rule_details(rule_id="   ")

        # Should return error message
        assert result == "Error: Recommendation ID must be a non-empty string in format rule_name|ERROR_KEY."

    @pytest.mark.asyncio
    async def test_get_rule_details_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_details when API returns error."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            result = await advisor_mcp_server.get_rule_details(rule_id=rule_id)

            # Should return error message
            assert f"Failed to retrieve recommendation details for {rule_id}:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    async def test_get_rule_details_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_details when API returns empty response."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            result = await advisor_mcp_server.get_rule_details(rule_id=rule_id)

            # Should return None when API returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_get_rule_details_with_special_characters(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_rule_details with rule ID containing special characters."""
        rule_id = "special_rule|WITH_SPECIAL_CHARS_123"

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_rule_details(rule_id=rule_id)

            # Verify API was called correctly with sanitized rule_id
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/")

            # Verify the result
            assert result == mock_api_response
