"""Test suite for the get_active_rules() method."""

import pytest

from tests.conftest import (  # pylint: disable=import-error
    assert_api_error_result,
)

from .conftest import get_default_active_rules_params, setup_advisor_mock


class TestGetActiveRules:
    """Test suite for the get_active_rules() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for active rules with obfuscated test data."""
        return {
            "meta": {"count": 2},
            "links": {
                "first": "/api/insights/v1/rule/?limit=2&offset=0&sort=rule_id",
                "next": "/api/insights/v1/rule/?limit=2&offset=2&sort=rule_id",
                "previous": "/api/insights/v1/rule/?limit=2&offset=0&sort=rule_id",
                "last": "/api/insights/v1/rule/?limit=2&offset=0&sort=rule_id",
            },
            "data": [
                {
                    "rule_id": "example_advisory_rule_001|ADVISORY_RULE_HIGH_IMPACT",
                    "created_at": "2024-03-15T09:45:12.123456Z",
                    "updated_at": "2024-11-20T14:22:33.987654Z",
                    "description": "System configuration requires attention for optimal performance and security",
                    "active": True,
                    "category": {"id": 2, "name": "Security"},
                    "impact": {"name": "High Priority Issue", "impact": 3},
                    "likelihood": 4,
                    "node_id": "kb123456",
                    "tags": "security performance configuration",
                    "playbook_count": 1,
                    "reboot_required": False,
                    "publish_date": "2024-01-10T12:00:00Z",
                    "summary": "System configuration optimization recommended for enhanced security posture.",
                    "impacted_systems_count": 15,
                    "reports_shown": True,
                    "rule_status": "enabled",
                    "total_risk": 3,
                    "hosts_acked_count": 2,
                    "rating": 4,
                },
                {
                    "rule_id": "example_advisory_rule_002|ADVISORY_RULE_MEDIUM_IMPACT",
                    "created_at": "2024-05-22T16:30:45.654321Z",
                    "updated_at": "2024-12-01T11:15:20.456789Z",
                    "description": "Network configuration optimization opportunity for improved reliability",
                    "active": True,
                    "category": {"id": 4, "name": "Performance"},
                    "impact": {"name": "Medium Priority Issue", "impact": 2},
                    "likelihood": 3,
                    "node_id": "kb789012",
                    "tags": "network reliability optimization",
                    "playbook_count": 0,
                    "reboot_required": True,
                    "publish_date": "2024-02-28T08:30:00Z",
                    "summary": "Network tuning recommended to enhance overall system performance metrics.",
                    "impacted_systems_count": 8,
                    "reports_shown": True,
                    "rule_status": "enabled",
                    "total_risk": 2,
                    "hosts_acked_count": 1,
                    "rating": 3,
                },
            ],
        }

    @pytest.fixture
    def empty_api_response(self):
        """Mock empty API response."""
        return {
            "meta": {"count": 0},
            "links": {
                "first": "/api/insights/v1/rule/?limit=20&offset=0&sort=rule_id",
                "next": None,
                "previous": None,
                "last": "/api/insights/v1/rule/?limit=20&offset=0&sort=rule_id",
            },
            "data": [],
        }

    @pytest.fixture
    def large_api_response(self):
        """Mock large API response for pagination testing."""
        data = []
        for i in range(50):
            data.append(
                {
                    "rule_id": f"test_rule_{i}|TEST_RULE_{i}",
                    "created_at": f"2024-06-{(i % 28) + 1:02d}T08:33:09.858024Z",
                    "updated_at": "2025-09-03T11:03:27.275998Z",
                    "description": f"Test recommendation {i} for system analysis",
                    "active": True,
                    "category": {"id": 2 if i % 2 == 0 else 4, "name": "Security" if i % 2 == 0 else "Performance"},
                    "impact": {
                        "name": "High Impact" if i % 3 == 0 else "Medium Impact",
                        "impact": 3 if i % 3 == 0 else 2,
                    },
                    "likelihood": 3 if i % 4 == 0 else 2,
                    "node_id": f"node_{i}",
                    "tags": f"test tag_{i}",
                    "playbook_count": i % 2,
                    "reboot_required": i % 5 == 0,
                    "publish_date": f"2024-01-{(i % 28) + 1:02d}T10:00:00Z",
                    "summary": f"Summary for test recommendation {i}",
                    "impacted_systems_count": i + 1,
                    "reports_shown": True,
                    "rule_status": "enabled",
                    "total_risk": (i % 4) + 1,
                    "hosts_acked_count": 0,
                    "rating": 0,
                }
            )
        return {
            "meta": {"count": 50},
            "links": {
                "first": "/api/insights/v1/rule/?limit=20&offset=0&sort=rule_id",
                "next": "/api/insights/v1/rule/?limit=20&offset=20&sort=rule_id",
                "previous": None,
                "last": "/api/insights/v1/rule/?limit=20&offset=40&sort=rule_id",
            },
            "data": data,
        }

    # Basic functionality tests
    @pytest.mark.asyncio
    async def test_get_active_rules_default_params(self, advisor_mcp_server, advisor_mock_client, mock_api_response):
        """Test get_active_rules with default parameters."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Get default parameters and call the method
            params = get_default_active_rules_params()
            result = await advisor_mcp_server.get_active_rules(**params)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with(
                "rule/", params={"offset": 0, "limit": 10, "impacting": True, "sort": "-total_risk"}
            )

            # Verify the result
            assert result == mock_api_response

            # Verify response structure matches real API
            assert "meta" in result
            assert "links" in result
            assert "data" in result
            assert len(result["data"]) == 2

            # Verify real API structure for recommendations
            for rule in result["data"]:
                assert "rule_id" in rule
                assert "description" in rule
                assert "category" in rule
                assert "impact" in rule
                assert "likelihood" in rule
                assert "total_risk" in rule
                assert "impacted_systems_count" in rule
                assert "playbook_count" in rule
                assert "reboot_required" in rule

    @pytest.mark.asyncio
    async def test_get_active_rules_all_parameters(self, advisor_mcp_server, advisor_mock_client, mock_api_response):
        """Test get_active_rules with all available parameters."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with comprehensive filters
            params = get_default_active_rules_params(
                incident=False,
                has_automatic_remediation=True,
                impact="3,4",
                likelihood="3,4",
                category="2,4",
                reboot=True,
                sort="-impact,rule_id",
                limit=10,
                offset=5,
                groups=["workspace1", "workspace2"],
                tags=["insights-client/group=database-servers", "satellite/env=production"],
            )
            result = await advisor_mcp_server.get_active_rules(**params)

            # Verify API was called with correct parameters
            expected_params = {
                "offset": 5,
                "limit": 10,
                "impacting": True,
                "incident": False,
                "has_playbook": True,
                "impact": "3,4",
                "likelihood": "3,4",
                "category": "2,4",
                "reboot": True,
                "sort": "-impact,rule_id",
                "groups": "workspace1,workspace2",
                "tags": "insights-client/group=database-servers,satellite/env=production",
            }
            advisor_mock_client.get.assert_called_once_with("rule/", params=expected_params)

            # Verify response
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_active_rules_invalid_tags_filtering(self, advisor_mcp_server):
        """Test get_active_rules with invalid tags (should return error)."""

        # Call the method with invalid tags (missing namespace/key=value format)
        params = get_default_active_rules_params(tags=["invalid-tag", "insights-client/group=valid-tag"])
        result = await advisor_mcp_server.get_active_rules(**params)

        # Should return error message for invalid tag format
        assert "Error: Invalid tag format 'invalid-tag'" in result
        assert "Required format: namespace/key=value" in result

    # Pagination tests

    @pytest.mark.asyncio
    async def test_get_active_rules_pagination(self, advisor_mcp_server, advisor_mock_client, large_api_response):
        """Test get_active_rules with pagination parameters."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, large_api_response):
            # Call the method with pagination
            params = get_default_active_rules_params(limit=20, offset=10)
            result = await advisor_mcp_server.get_active_rules(**params)

            # Verify API was called with correct parameters
            expected_params = {
                "offset": 10,
                "limit": 20,
                "impacting": True,
                "sort": "-total_risk",
            }
            advisor_mock_client.get.assert_called_once_with("rule/", params=expected_params)

            # Verify response
            assert result == large_api_response
            assert len(result["data"]) == 50

    # Edge case tests
    @pytest.mark.asyncio
    async def test_get_active_rules_empty_response(self, advisor_mcp_server, advisor_mock_client, empty_api_response):
        """Test get_active_rules when API returns empty response."""

        # Setup mocks with empty response
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, empty_api_response):
            # Call the method
            params = get_default_active_rules_params()
            result = await advisor_mcp_server.get_active_rules(**params)

            # Verify response
            assert result == empty_api_response
            assert len(result["data"]) == 0

    @pytest.mark.asyncio
    async def test_get_active_rules_null_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_active_rules when API returns None."""

        # Setup mocks with None response
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            params = get_default_active_rules_params()
            result = await advisor_mcp_server.get_active_rules(**params)

            # Should return None when API returns None
            assert result is None

    # Error handling tests
    @pytest.mark.parametrize(
        "exception, error_message",
        [
            (Exception("API Error"), "API Error"),
            (ConnectionError("Connection failed"), "Connection failed"),
            (ValueError("Invalid response format"), "Invalid response format"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_active_rules_error_handling(
        self, advisor_mcp_server, advisor_mock_client, exception, error_message
    ):
        """Test get_active_rules error handling for various exception types."""

        # Setup mocks with exception
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=exception):
            # Call the method
            params = get_default_active_rules_params()
            result = await advisor_mcp_server.get_active_rules(**params)

            # Should return error message
            assert_api_error_result(result, error_message)
            assert f"Failed to retrieve recommendations: {error_message}" in result

    # Parameter combination tests
    @pytest.mark.parametrize(
        "filter_params, expected_params_update, test_description",
        [
            (
                {"impact": "3,4", "likelihood": "3,4"},
                {"impact": "3,4", "likelihood": "3,4"},
                "high-risk recommendations",
            ),
            ({"has_automatic_remediation": True}, {"has_playbook": True}, "recommendations with automatic remediation"),
            ({"reboot": True}, {"reboot": True}, "recommendations requiring reboot"),
            ({"category": "2"}, {"category": "2"}, "security category recommendations"),
            ({"impacting": "true"}, {"impacting": True}, "impacting as string 'true'"),
            ({"impacting": "false"}, {"impacting": False}, "impacting as string 'false'"),
            ({"incident": "true"}, {"incident": True}, "incident as string 'true'"),
            ({"incident": "false"}, {"incident": False}, "incident as string 'false'"),
            (
                {"has_automatic_remediation": "true"},
                {"has_playbook": True},
                "has_automatic_remediation as string 'true'",
            ),
            (
                {"has_automatic_remediation": "false"},
                {"has_playbook": False},
                "has_automatic_remediation as string 'false'",
            ),
            ({"reboot": "true"}, {"reboot": True}, "reboot as string 'true'"),
            ({"reboot": "false"}, {"reboot": False}, "reboot as string 'false'"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_active_rules_specific_filtering(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        advisor_mcp_server,
        advisor_mock_client,
        mock_api_response,
        filter_params,
        expected_params_update,
        test_description,  # pylint: disable=unused-argument
    ):
        """Test get_active_rules with specific filtering criteria."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with filter parameters
            params = get_default_active_rules_params(**filter_params)
            result = await advisor_mcp_server.get_active_rules(**params)

            # Build expected API parameters
            expected_params = {"offset": 0, "limit": 10, "impacting": True, "sort": "-total_risk"}
            expected_params.update(expected_params_update)

            # Verify API was called with correct parameters
            advisor_mock_client.get.assert_called_once_with("rule/", params=expected_params)

            # Verify response
            assert result == mock_api_response

    # Test string parameter parsing edge cases
    @pytest.mark.parametrize(
        "params, expected_params, test_description",
        [
            # Test various truthy string values for the 4 boolean parameters
            ({"impacting": "1"}, {"impacting": True}, "impacting as string '1'"),
            ({"impacting": "yes"}, {"impacting": True}, "impacting as string 'yes'"),
            ({"impacting": "on"}, {"impacting": True}, "impacting as string 'on'"),
            ({"incident": "TRUE"}, {"incident": True}, "incident as uppercase 'TRUE'"),
            ({"has_automatic_remediation": "Yes"}, {"has_playbook": True}, "has_automatic_remediation as 'Yes'"),
            ({"reboot": "ON"}, {"reboot": True}, "reboot as uppercase 'ON'"),
            # Test falsy string values
            ({"impacting": "0"}, {"impacting": False}, "impacting as string '0'"),
            ({"impacting": "no"}, {"impacting": False}, "impacting as string 'no'"),
            ({"impacting": "off"}, {"impacting": False}, "impacting as string 'off'"),
            ({"incident": "FALSE"}, {"incident": False}, "incident as uppercase 'FALSE'"),
            ({"has_automatic_remediation": "No"}, {"has_playbook": False}, "has_automatic_remediation as 'No'"),
            ({"reboot": "OFF"}, {"reboot": False}, "reboot as uppercase 'OFF'"),
            # Test invalid string values that should be parsed as False
            ({"impacting": "invalid"}, {"impacting": False}, "impacting as invalid string"),
            ({"incident": "random"}, {"incident": False}, "incident as random string"),
            ({"has_automatic_remediation": "maybe"}, {"has_playbook": False}, "has_automatic_remediation as 'maybe'"),
            ({"reboot": "sometimes"}, {"reboot": False}, "reboot as 'sometimes'"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_active_rules_string_boolean_parsing(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        advisor_mcp_server,
        advisor_mock_client,
        mock_api_response,
        params,
        expected_params,
        test_description,  # pylint: disable=unused-argument
    ):
        """Test get_active_rules with string boolean parameter parsing."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with string boolean parameters
            full_params = get_default_active_rules_params(**params)
            result = await advisor_mcp_server.get_active_rules(**full_params)

            # Build expected API parameters
            expected_api_params = {"offset": 0, "limit": 10, "impacting": True, "sort": "-total_risk"}
            expected_api_params.update(expected_params)

            # Verify API was called with correct parameters
            advisor_mock_client.get.assert_called_once_with("rule/", params=expected_api_params)

            # Verify response
            assert result == mock_api_response
