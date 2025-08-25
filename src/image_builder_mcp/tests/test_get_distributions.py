"""Test suite for the get_distributions() method."""

import json
from unittest.mock import patch

import pytest

import image_builder_mcp.server as image_builder_mcp

from .conftest import setup_imagebuilder_mock


class TestGetDistributions:
    """Test suite for the get_distributions() method."""

    @pytest.fixture
    def mock_distributions_response(self):
        """Mock API response for distributions."""
        return [
            {"name": "rhel-8", "description": "Red Hat Enterprise Linux 8", "version": "8.10"},
            {"name": "rhel-9", "description": "Red Hat Enterprise Linux 9", "version": "9.5"},
            {"name": "rhel-10", "description": "Red Hat Enterprise Linux 10", "version": "10.0"},
            {"name": "fedora-40", "description": "Fedora Linux 40", "version": "40"},
            {"name": "centos-stream-9", "description": "CentOS Stream 9", "version": "9"},
        ]

    @pytest.mark.asyncio
    async def test_get_distributions_basic_functionality(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_distributions_response
    ):
        """Test basic functionality of get_distributions method."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_distributions_response):
            # Call the method
            result = await imagebuilder_mcp_server.get_distributions()

            # Verify API was called correctly
            imagebuilder_mock_client.get.assert_called_once_with("distributions")

            # Parse the result
            parsed_result = json.loads(result)
            assert isinstance(parsed_result, list)
            assert len(parsed_result) == 5

            # Check that all expected distributions are present
            distribution_names = [dist["name"] for dist in parsed_result]
            assert "rhel-8" in distribution_names
            assert "rhel-9" in distribution_names
            assert "rhel-10" in distribution_names
            assert "fedora-40" in distribution_names
            assert "centos-stream-9" in distribution_names

            # Verify structure of distribution objects
            for dist in parsed_result:
                assert "name" in dist
                assert "description" in dist
                assert "version" in dist

    @pytest.mark.asyncio
    async def test_get_distributions_empty_response(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_distributions with empty API response."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, []):
            # Call the method
            result = await imagebuilder_mcp_server.get_distributions()

            # Should return empty list
            parsed_result = json.loads(result)
            assert parsed_result == []

    @pytest.mark.asyncio
    async def test_get_distributions_api_error(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_distributions when API returns error."""
        # Setup mocks
        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.get_distributions()

            # Should return error message
            assert result.startswith("Error getting distributions: API Error")

    @pytest.mark.asyncio
    async def test_get_distributions_auth_error(self, imagebuilder_mcp_server):
        """Test get_distributions when authentication fails."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {}  # No auth headers
            # Mock get_client to raise ValueError
            with patch.object(imagebuilder_mcp_server, "get_client") as mock_get_client:
                mock_get_client.side_effect = ValueError("Client ID is required")

                # Call the method
                result = await imagebuilder_mcp_server.get_distributions()

                # Should return authentication error
                assert "Client ID is required" in result or "authentication" in result.lower()

    @pytest.mark.asyncio
    async def test_get_distributions_no_parameters(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_distributions_response
    ):
        """Test that get_distributions works without any parameters."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_distributions_response):
            # Call the method without any parameters
            result = await imagebuilder_mcp_server.get_distributions()

            # Should work without parameters
            parsed_result = json.loads(result)
            assert len(parsed_result) == 5
