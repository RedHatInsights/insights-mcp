"""Test suite for the get_hosts_details_hitting_a_rule() method."""

import pytest

from .conftest import TEST_RHEL_VERSION, TEST_RULE_ID, get_default_hosts_details_params, setup_advisor_mock


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
            params = get_default_hosts_details_params(rule_id=rule_id)
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with(
                f"rule/{rule_id}/systems_detail/", params={"limit": 10, "offset": 0}
            )

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_with_pagination(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with pagination parameters."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with pagination
            params = get_default_hosts_details_params(rule_id=rule_id, limit=10, offset=5)
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

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
            params = get_default_hosts_details_params(rule_id=rule_id, rhel_version=TEST_RHEL_VERSION)
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

            # Verify API was called with correct parameters
            expected_params = {"limit": 10, "offset": 0, "rhel_version": TEST_RHEL_VERSION}
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
            params = get_default_hosts_details_params(
                rule_id=rule_id, limit=50, offset=20, rhel_version=TEST_RHEL_VERSION
            )
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

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
            params = get_default_hosts_details_params(rule_id=rule_id, limit="25", offset="10")
            await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

            # Verify parameters are correctly parsed
            expected_params = {"limit": "25", "offset": "10"}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_invalid_rhel_version(self, advisor_mcp_server):
        """Test get_hosts_details_hitting_a_rule with invalid RHEL version."""
        rule_id = TEST_RULE_ID

        # Call the method with invalid RHEL version
        params = get_default_hosts_details_params(rule_id=rule_id, rhel_version="invalid.version")
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

        # Should return error message
        assert "Error: Invalid RHEL version(s) 'invalid.version'" in result
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
        params = get_default_hosts_details_params(rule_id=rule_id)
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)
        assert result == expected_error

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_hosts_details_hitting_a_rule when API returns error."""
        rule_id = TEST_RULE_ID

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            params = get_default_hosts_details_params(rule_id=rule_id)
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

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
            params = get_default_hosts_details_params(rule_id=rule_id)
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

            # Should return None when API returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_whitespace_rule_id(self, advisor_mcp_server):
        """Test get_hosts_details_hitting_a_rule with whitespace-only rule ID."""
        # Call the method with whitespace-only rule_id
        params = get_default_hosts_details_params(rule_id="   ")
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

        # Should return error message
        assert result == "Error: Recommendation ID must be a non-empty string."

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
            params = get_default_hosts_details_params(rule_id=rule_id)
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

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
                params = get_default_hosts_details_params(rule_id=rule_id, rhel_version=version)
                result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

                # Verify API was called with correct parameters
                expected_params = {"limit": 10, "offset": 0, "rhel_version": version}
                advisor_mock_client.get.assert_called_once_with(
                    f"rule/{rule_id}/systems_detail/", params=expected_params
                )

                # Verify the result
                assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_with_multiple_rhel_versions(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with multiple RHEL versions."""
        rule_id = TEST_RULE_ID
        rhel_versions = ["9.3", "9.4", "9.5"]

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with list of RHEL versions
            params = get_default_hosts_details_params(rule_id=rule_id, rhel_version=rhel_versions)
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

            # Verify API was called correctly with comma-separated versions
            expected_params = {"limit": 10, "offset": 0, "rhel_version": "9.3,9.4,9.5"}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_with_multiple_rhel_versions_string(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_hosts_details_hitting_a_rule with multiple RHEL versions as comma-separated string."""
        rule_id = TEST_RULE_ID
        rhel_versions = "9.3,9.4,9.5"

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with comma-separated RHEL versions
            params = get_default_hosts_details_params(rule_id=rule_id, rhel_version=rhel_versions)
            result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

            # Verify API was called correctly
            expected_params = {"limit": 10, "offset": 0, "rhel_version": "9.3,9.4,9.5"}
            advisor_mock_client.get.assert_called_once_with(f"rule/{rule_id}/systems_detail/", params=expected_params)

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_hosts_details_hitting_a_rule_multiple_invalid_rhel_versions(self, advisor_mcp_server):
        """Test get_hosts_details_hitting_a_rule with multiple invalid RHEL versions."""
        rule_id = TEST_RULE_ID
        invalid_versions = ["5.9", "11.0", "9.99"]

        # Call the method with invalid RHEL versions
        params = get_default_hosts_details_params(rule_id=rule_id, rhel_version=invalid_versions)
        result = await advisor_mcp_server.get_hosts_details_hitting_a_rule(**params)

        # Should return error message with all invalid versions
        assert "Error: Invalid RHEL version(s) '5.9, 11.0, 9.99'" in result
        assert "Valid versions are:" in result
