"""Test suite for the get_recommendations_statistics() method."""

import ast

import pytest

from .conftest import setup_advisor_mock


class TestGetRecommendationsStatistics:
    """Test suite for the get_recommendations_statistics() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for recommendations statistics."""
        return {
            "total": 42,
            "total_risk": {"1": 8, "2": 15, "3": 12, "4": 7},
            "category": {"Availability": 10, "Performance": 8, "Security": 15, "Stability": 9},
        }

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_no_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_statistics with no parameters."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_recommendations_statistics()

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params={})

            # Parse the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_with_groups(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_statistics with groups parameter."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with groups
            result = await advisor_mcp_server.get_recommendations_statistics(groups=["workspace1", "workspace2"])

            # Verify API was called with correct parameters
            expected_params = {"groups": "workspace1,workspace2"}
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params=expected_params)

            # Verify the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_with_tags(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_statistics with tags parameter."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with tags
            result = await advisor_mcp_server.get_recommendations_statistics(
                tags=["insights-client/group=database-servers", "satellite/env=production"]
            )

            # Verify API was called with correct parameters
            expected_params = {"tags": "insights-client/group=database-servers,satellite/env=production"}
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params=expected_params)

            # Verify the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_with_both_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_statistics with both groups and tags."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with both parameters
            result = await advisor_mcp_server.get_recommendations_statistics(
                groups=["workspace1"], tags=["insights-client/group=database-servers"]
            )

            # Verify API was called with correct parameters
            expected_params = {"groups": "workspace1", "tags": "insights-client/group=database-servers"}
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params=expected_params)

            # Verify the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_string_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_statistics with string parameters."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with string parameters
            result = await advisor_mcp_server.get_recommendations_statistics(
                groups="workspace1,workspace2", tags="insights-client/group=database-servers,satellite/env=production"
            )

            # Verify parameters are correctly parsed
            expected_params = {
                "groups": "workspace1,workspace2",
                "tags": "insights-client/group=database-servers,satellite/env=production",
            }
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params=expected_params)

            # Verify the result
            parsed_result = ast.literal_eval(result)
            assert parsed_result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_invalid_tag_format(self, advisor_mcp_server, advisor_mock_client):
        """Test get_recommendations_statistics with invalid tag format (should return error)."""

        # Call the method with invalid tags (missing namespace/key=value format)
        result = await advisor_mcp_server.get_recommendations_statistics(tags=["invalid-tag-format"])

        # Should return error message for invalid tag format
        assert result == "Error: Invalid tag format 'invalid-tag-format', expected namespace/key=value"

        # API should not be called when validation fails
        advisor_mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_mixed_valid_invalid_tags(
        self, advisor_mcp_server, advisor_mock_client
    ):
        """Test get_recommendations_statistics with mixed valid and invalid tags."""

        # Call the method with mixed tags (first invalid tag will cause error)
        result = await advisor_mcp_server.get_recommendations_statistics(
            tags=["invalid-tag", "insights-client/group=valid-tag", ""]
        )

        # Should return error message for the first invalid tag encountered
        assert result == "Error: Invalid tag format 'invalid-tag', expected namespace/key=value"

        # API should not be called when validation fails
        advisor_mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_recommendations_statistics when API returns error."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            result = await advisor_mcp_server.get_recommendations_statistics()

            # Should return error message
            assert "Failed to retrieve recommendations statistics:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    async def test_get_recommendations_statistics_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_recommendations_statistics when API returns empty response."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            result = await advisor_mcp_server.get_recommendations_statistics()

            # Should return appropriate message
            assert result == "No recommendations statistics found or empty response."
