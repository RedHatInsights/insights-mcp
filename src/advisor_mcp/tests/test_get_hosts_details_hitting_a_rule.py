"""Test suite for the get_hosts_details_hitting_a_rule() method."""

import ast

import pytest

from .conftest import TEST_RHEL_VERSION, TEST_RULE_ID, setup_advisor_mock


class TestGetHostsDetailsHittingARule:
    """Test suite for the get_hosts_details_hitting_a_rule() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for detailed hosts hitting a rule (obfuscated real data structure)."""
        return {
            "meta": {"count": 2},
            "links": {
                "first": "/api/insights/v1/rule/test_rule%7CTEST_RULE_WARN_V2/systems_detail/?limit=10&offset=0",
                "next": "/api/insights/v1/rule/test_rule%7CTEST_RULE_WARN_V2/systems_detail/?limit=10&offset=0",
                "previous": "/api/insights/v1/rule/test_rule%7CTEST_RULE_WARN_V2/systems_detail/?limit=10&offset=0",
                "last": "/api/insights/v1/rule/test_rule%7CTEST_RULE_WARN_V2/systems_detail/?limit=10&offset=0",
            },
            "data": [
                {
                    "system_uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "display_name": "testhost.example.internal",
                    "last_seen": "2025-09-04T01:47:29.220645Z",
                    "stale_at": "2025-09-07T01:47:28.873973Z",
                    "hits": 5,
                    "critical_hits": 1,
                    "important_hits": 4,
                    "moderate_hits": 0,
                    "low_hits": 0,
                    "incident_hits": 1,
                    "all_pathway_hits": 1,
                    "pathway_filter_hits": 4,
                    "rhel_version": "9.5",
                    "impacted_date": "2025-09-03T06:13:07.632773Z",
                },
                {
                    "system_uuid": "f9e8d7c6-b5a4-3210-9876-543210fedcba",
                    "display_name": "prodhost.example.internal",
                    "last_seen": "2025-09-04T01:15:53.542580Z",
                    "stale_at": "2025-09-07T01:15:52.797035Z",
                    "hits": 5,
                    "critical_hits": 1,
                    "important_hits": 4,
                    "moderate_hits": 0,
                    "low_hits": 0,
                    "incident_hits": 1,
                    "all_pathway_hits": 1,
                    "pathway_filter_hits": 4,
                    "rhel_version": "9.5",
                    "impacted_date": "2025-09-03T04:32:06.275715Z",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_valid_rule_id(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with valid rule ID."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params={})

            # Parse the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_with_pagination(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with pagination parameters."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with pagination
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id, limit=10, offset=5)

            # Verify API was called with correct parameters
            expected_params = {"limit": 10, "offset": 5}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_with_rhel_version(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with RHEL version filter."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with RHEL version
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id, rhel_version=TEST_RHEL_VERSION)

            # Verify API was called with correct parameters
            expected_params = {"rhel_version": TEST_RHEL_VERSION}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_with_all_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with all parameters."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with all parameters
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(
                rule_id=rule_id, limit=50, offset=20, rhel_version=TEST_RHEL_VERSION
            )

            # Verify API was called with correct parameters
            expected_params = {"limit": 50, "offset": 20, "rhel_version": TEST_RHEL_VERSION}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_string_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with string parameters."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with string parameters
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id, limit="25", offset="10")

            # Verify parameters are correctly parsed
            expected_params = {"limit": 25, "offset": 10}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_invalid_rhel_version(self, advisor_mcp_server):
        """Test get_hosts_details_hitting_a_rule with invalid RHEL version."""
        rule_id = TEST_RULE_ID

        # Call the method with invalid RHEL version
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(
            rule_id=rule_id, rhel_version="invalid.version"
        )

        # Should return error message
        assert "Error: Invalid RHEL version 'invalid.version'" in result
        assert "Valid versions are:" in result

    @pytest.mark.parametrize(
        "rule_id, expected_error",
        [
            ("", "Error: Recommendation ID must be a non-empty string."),
            (None, "Error: Recommendation ID must be a non-empty string."),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_invalid_rule_id(self, advisor_mcp_server, rule_id, expected_error):
        """Test get_hosts_details_hitting_a_rule with various invalid rule IDs."""
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id)
        assert result == expected_error

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_hosts_details_hitting_a_rule when API returns error."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id)

            # Should return error message
            assert f"Failed to retrieve detailed system information for recommendation {rule_id}:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_hosts_details_hitting_a_rule when API returns empty response."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id)

            # Should return appropriate message
            assert result == "No detailed system information found."

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_whitespace_rule_id(self, advisor_mcp_server):
        """Test get_hosts_details_hitting_a_rule with whitespace-only rule ID."""
        # Call the method with whitespace-only rule_id
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id="   ")

        # Should return error message
        assert result == "Error: Recommendation ID cannot be empty."

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_none_limit_offset(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with None limit and offset (default behavior)."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with explicit None values
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(
                rule_id=rule_id, limit=None, offset=None, rhel_version=None
            )

            # Verify API was called with empty params (None values filtered out)
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params={})

            # Parse the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_zero_limit_offset(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with zero limit and offset."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with zero values
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id, limit=0, offset=0)

            # Verify API was called with zero values
            expected_params = {"limit": 0, "offset": 0}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_invalid_string_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with invalid string parameters."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with invalid string parameters (non-numeric)
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(
                rule_id=rule_id, limit="invalid", offset="also_invalid"
            )

            # Verify API was called with empty params (invalid values filtered out)
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params={})

    @pytest.mark.parametrize(
        "exception, error_message",
        [
            (ConnectionError("Connection failed"), "Connection failed"),
            (ValueError("Invalid response format"), "Invalid response format"),
            (TypeError("Type conversion error"), "Type conversion error"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_error_handling(
        self, advisor_mcp_server, advisor_mock_client, exception, error_message
    ):
        """Test get_hosts_details_hitting_a_rule error handling for various exception types."""
        rule_id = TEST_RULE_ID

        # Setup mocks with exception
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=exception):
            # Call the method
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id)

            # Should return error message
            assert f"Failed to retrieve detailed system information for recommendation {rule_id}:" in result
            assert error_message in result

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_valid_rhel_versions(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with various valid RHEL versions."""
        rule_id = TEST_RULE_ID
        valid_versions = ["6.0", "7.0", "8.0", "9.4", "10.0", "8.10", "9.8"]

        for version in valid_versions:
            # Reset mock for each iteration
            advisor_mock_client.reset_mock()

            # Setup mocks
            with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
                # Call the method with valid RHEL version
                result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(
                    rule_id=rule_id, rhel_version=version
                )

                # Verify API was called with correct parameters
                expected_params = {"rhel_version": version}
                advisor_mock_client.get.assert_called_once_with(
                    f"rule/{rule_id}/systems_detail/", params=expected_params
                )

                # Parse the result
                parsed_result = ast.literal_eval(result)
                assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_rhel_version_with_whitespace(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with RHEL version containing whitespace."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with RHEL version with whitespace
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id, rhel_version="  9.4  ")

            # Verify API was called with trimmed version
            expected_params = {"rhel_version": "9.4"}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_empty_rhel_version(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with empty RHEL version."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with empty RHEL version
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id, rhel_version="")

            # Verify API was called without rhel_version param (empty string filtered out)
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params={})

    @pytest.mark.parametrize(
        "invalid_version",
        ["5.9", "11.0", "9.99", "8.11", "10.3"],
    )
    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_boundary_rhel_versions(self, advisor_mcp_server, invalid_version):
        """Test get_hosts_details_hitting_a_rule with boundary RHEL versions."""
        rule_id = TEST_RULE_ID

        # Call the method with invalid RHEL version
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(
            rule_id=rule_id, rhel_version=invalid_version
        )

        # Should return error message
        assert f"Error: Invalid RHEL version '{invalid_version}'" in result
        assert "Valid versions are:" in result

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_negative_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with negative limit and offset."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with negative values
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(rule_id=rule_id, limit=-1, offset=-5)

            # Verify API was called with negative values (they should pass through)
            expected_params = {"limit": -1, "offset": -5}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)
