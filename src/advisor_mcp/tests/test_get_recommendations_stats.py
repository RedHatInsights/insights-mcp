"""Test suite for the get_recommendations_stats() method."""

import pytest

from .conftest import setup_advisor_mock


class TestGetRecommendationsStats:
    """Test suite for the get_recommendations_stats() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for recommendations statistics."""
        return {
            "total": 42,
            "total_risk": {"1": 8, "2": 15, "3": 12, "4": 7},
            "category": {"Availability": 10, "Performance": 8, "Security": 15, "Stability": 9},
        }

    @pytest.mark.asyncio
    async def test_get_recommendations_stats_no_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_stats with no parameters."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method
            result = await advisor_mcp_server.get_recommendations_stats(groups=None, tags=None)

            # Verify API was called correctly
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params={})

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_stats_with_groups(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_stats with groups parameter."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with groups
            result = await advisor_mcp_server.get_recommendations_stats(groups=["workspace1", "workspace2"], tags=None)

            # Verify API was called with correct parameters
            expected_params = {"groups": "workspace1,workspace2"}
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params=expected_params)

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_stats_with_tags(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_stats with tags parameter."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with tags
            result = await advisor_mcp_server.get_recommendations_stats(
                groups=None, tags=["insights-client/group=database-servers", "satellite/env=production"]
            )

            # Verify API was called with correct parameters
            expected_params = {"tags": "insights-client/group=database-servers,satellite/env=production"}
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params=expected_params)

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_stats_with_both_params(
        self, advisor_mcp_server, advisor_mock_client, mock_api_response
    ):
        """Test get_recommendations_stats with both groups and tags."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, mock_api_response):
            # Call the method with both parameters
            result = await advisor_mcp_server.get_recommendations_stats(
                groups=["workspace1"], tags=["insights-client/group=database-servers"]
            )

            # Verify API was called with correct parameters
            expected_params = {"groups": "workspace1", "tags": "insights-client/group=database-servers"}
            advisor_mock_client.get.assert_called_once_with("stats/rules/", params=expected_params)

            # Verify the result
            assert result == mock_api_response

    @pytest.mark.asyncio
    async def test_get_recommendations_stats_invalid_tag_format(self, advisor_mcp_server, advisor_mock_client):
        """Test get_recommendations_stats with invalid tag format (should return error)."""

        # Call the method with invalid tags (missing namespace/key=value format)
        result = await advisor_mcp_server.get_recommendations_stats(groups=None, tags=["invalid-tag-format"])

        # Should return error message for invalid tag format
        assert "Error: Invalid tag format 'invalid-tag-format'" in result
        assert "expected namespace/key=value" in result

        # API should not be called when validation fails
        advisor_mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_recommendations_stats_api_error(self, advisor_mcp_server, advisor_mock_client):
        """Test get_recommendations_stats when API returns error."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, side_effect=Exception("API Error")):
            # Call the method
            result = await advisor_mcp_server.get_recommendations_stats(groups=None, tags=None)

            # Should return error message
            assert "Failed to retrieve recommendations statistics:" in result
            assert "API Error" in result

    @pytest.mark.asyncio
    async def test_get_recommendations_stats_empty_response(self, advisor_mcp_server, advisor_mock_client):
        """Test get_recommendations_stats when API returns empty response."""

        # Setup mocks
        with setup_advisor_mock(advisor_mcp_server, advisor_mock_client, None):
            # Call the method
            result = await advisor_mcp_server.get_recommendations_stats(groups=None, tags=None)

            # Should return None when API returns None
            assert result is None
