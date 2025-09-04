"""Test suite for the get_rule_by_text_search() method."""

import pytest

from .conftest import setup_advisor_mock


class TestGetRuleByTextSearch:
    """Test suite for the get_rule_by_text_search() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for rule text search (obfuscated real data structure)."""
        return {
            "meta": {"count": 250},
            "links": {
                "first": "/api/insights/v1/rule/?limit=10&offset=0&text=test",
                "next": "/api/insights/v1/rule/?limit=10&offset=10&text=test",
                "previous": "/api/insights/v1/rule/?limit=10&offset=0&text=test",
                "last": "/api/insights/v1/rule/?limit=10&offset=240&text=test",
            },
            "data": [
                {
                    "rule_id": "test_service_failure|TEST_SERVICE_FAILURE_WARN",
                    "created_at": "2024-01-15T08:30:20.123456Z",
                    "updated_at": "2024-12-20T14:25:30.654321Z",
                    "description": "Test service fails to start due to configuration issues",
                    "active": True,
                    "category": {"id": 1, "name": "Availability"},
                    "impact": {"name": "Application Failure", "impact": 3},
                    "likelihood": 3,
                    "node_id": "1234567",
                    "tags": "test service configuration availability",
                    "playbook_count": 1,
                    "reboot_required": False,
                    "publish_date": "2024-01-20T10:15:00Z",
                    "summary": "Test service fails to start due to misconfiguration.",
                    "generic": "Test service fails to start due to misconfiguration.",
                    "reason": "This system has test service configuration issues.",
                    "more_info": "For more information, refer to documentation.",
                    "impacted_systems_count": 5,
                    "reports_shown": True,
                    "rule_status": "enabled",
                    "resolution_set": [
                        {
                            "system_type": 105,
                            "resolution": "Red Hat recommends updating the configuration.",
                            "resolution_risk": {"name": "Update Configuration", "risk": 2},
                            "has_playbook": True,
                        }
                    ],
                    "total_risk": 3,
                    "hosts_acked_count": 0,
                    "rating": 0,
                },
                {
                    "rule_id": "test_performance_issue|TEST_PERFORMANCE_DEGRADATION",
                    "created_at": "2024-02-10T12:45:15.789012Z",
                    "updated_at": "2024-11-30T16:30:45.345678Z",
                    "description": "Test application performance degradation detected",
                    "active": True,
                    "category": {"id": 4, "name": "Performance"},
                    "impact": {"name": "System Performance Loss", "impact": 2},
                    "likelihood": 3,
                    "node_id": "7654321",
                    "tags": "test performance tuning application",
                    "playbook_count": 0,
                    "reboot_required": False,
                    "publish_date": "2024-02-15T14:20:00Z",
                    "summary": "Test application shows performance degradation.",
                    "generic": "Test application shows performance degradation.",
                    "reason": "This system has performance tuning issues.",
                    "more_info": "",
                    "impacted_systems_count": 12,
                    "reports_shown": True,
                    "rule_status": "enabled",
                    "resolution_set": [
                        {
                            "system_type": 105,
                            "resolution": "Red Hat recommends performance tuning.",
                            "resolution_risk": {"name": "Performance Tuning", "risk": 1},
                            "has_playbook": False,
                        }
                    ],
                    "total_risk": 2,
                    "hosts_acked_count": 0,
                    "rating": 0,
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_rule_by_text_search_valid_text(self, advisor_mcp_server, advisor_mock_client, mock_api_response):
        """Test get_rule_by_text_search with valid search text."""
        search_text = "xfs"

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_rule_by_text_search(text=search_text)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with("rule/", params={"text": search_text})

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_rule_by_text_search_multiword_search(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_rule_by_text_search with multi-word search text."""
        search_text = "firewall zone drifting"

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            await advisor_mcp_server.get_rule_by_text_search(text=search_text)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with("rule/", params={"text": search_text})

    @pytest.mark.parametrize(
        "text, expected_error",
        [
            ("", "Error: Text search query must be a non-empty string."),
            ("   ", "Error: Text search query must be a non-empty string."),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_rule_by_text_search_invalid_text(self, advisor_mcp_server, text, expected_error):
        """Test get_rule_by_text_search with various invalid text inputs."""
        result = await advisor_mcp_server.get_rule_by_text_search(text=text)
        assert result == expected_error

    @pytest.mark.asyncio
    async def test_get_rule_by_text_search_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_by_text_search when API returns error."""
        search_text = "test"

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            result = await advisor_mcp_server.get_rule_by_text_search(text=search_text)

            # Should return error message
            assert f"Failed to retrieve recommendations for text search {search_text}:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    async def test_get_rule_by_text_search_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_rule_by_text_search when API returns empty response."""
        search_text = "nonexistent"

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            result = await advisor_mcp_server.get_rule_by_text_search(text=search_text)

            # Should return None when API returns None
            assert result is None
