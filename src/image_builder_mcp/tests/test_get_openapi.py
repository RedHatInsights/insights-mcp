"""Test suite for the get_openapi() method."""

import json
from unittest.mock import patch

import pytest

from tests.conftest import assert_api_error_result


class TestGetOpenAPI:
    """Test suite for the get_openapi() method."""

    @pytest.fixture
    def mock_openapi_response(self):
        """Mock OpenAPI response."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Image Builder API", "version": "1.0.0"},
            "components": {
                "schemas": {
                    "ImageTypes": {"enum": ["ami", "guest-image", "vhd", "vsphere", "oci"]},
                    "ImageRequest": {"properties": {"architecture": {"enum": ["x86_64", "aarch64"]}}},
                }
            },
        }

    @pytest.mark.asyncio
    async def test_get_openapi_basic_functionality(self, imagebuilder_mcp_server, mock_openapi_response):
        """Test basic functionality of get_openapi method."""
        # Setup mocks

        with patch.object(imagebuilder_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_openapi_response

            # Call the method
            result = await imagebuilder_mcp_server.get_openapi(response_size=7)

            # Verify API was called correctly
            mock_get.assert_called_once_with("openapi.json", noauth=True)

            # Parse the result
            parsed_result = json.loads(result)
            assert parsed_result == mock_openapi_response
            assert "openapi" in parsed_result
            assert "components" in parsed_result

    @pytest.mark.asyncio
    async def test_get_openapi_api_error(self, imagebuilder_mcp_server):
        """Test get_openapi when API returns error."""
        # Setup mocks
        with patch.object(imagebuilder_mcp_server.insights_client, "get") as mock_get:
            mock_get.side_effect = Exception("API Error")

            # Call the method
            result = await imagebuilder_mcp_server.get_openapi(response_size=7)

            # Should return error message
            assert_api_error_result(result)

    @pytest.mark.asyncio
    async def test_get_openapi_ignores_response_size(self, imagebuilder_mcp_server, mock_openapi_response):
        """Test that get_openapi ignores the response_size parameter."""
        # Setup mocks
        with patch.object(imagebuilder_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_openapi_response

            # Call with different response_size values
            result1 = await imagebuilder_mcp_server.get_openapi(response_size=1)
            result2 = await imagebuilder_mcp_server.get_openapi(response_size=100)

            # Should return same result regardless of response_size
            assert result1 == result2
            assert json.loads(result1) == mock_openapi_response
