"""Test suite for the get_openapi() method."""

import json
from http import HTTPMethod

import pytest

from insights_mcp.errors import InsightsApiError
from tests.conftest import assert_api_error_message


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
                    "Blueprint": {"properties": {"name": {"type": "string"}}},
                }
            },
            "paths": {
                "/blueprints": {
                    "get": {"summary": "Get a list of blueprints", "responses": {"200": {"description": "OK"}}},
                    "post": {
                        "summary": "Create a new blueprint",
                        "responses": {"200": {"description": "OK"}},
                        "requestBody": {
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Blueprint"}}}
                        },
                    },
                },
                "/distributions": {
                    "get": {"summary": "Get a list of distributions", "responses": {"200": {"description": "OK"}}},
                },
            },
        }

    @pytest.mark.asyncio
    async def test_get_openapi_basic_functionality(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_openapi_response
    ):
        """Test basic functionality of get_openapi method."""
        endpoint = "openapi.json"
        query = {}
        imagebuilder_mock_client.api.register(
            HTTPMethod.GET, endpoint, response_body=mock_openapi_response, query=query
        )
        # Call the method
        result = await imagebuilder_mcp_server.get_openapi(endpoints="")

        # Verify API was called correctly
        imagebuilder_mock_client.get.assert_called_once_with(endpoint, noauth=True)

        # Parse the result
        parsed_result = json.loads(result)
        assert parsed_result == mock_openapi_response
        assert "openapi" in parsed_result
        assert "components" in parsed_result

    @pytest.mark.asyncio
    async def test_get_openapi_api_error(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_openapi when API returns error."""
        endpoint = "openapi.json"
        query = {}
        imagebuilder_mock_client.api.register(HTTPMethod.GET, endpoint, query=query, error=Exception("API Error"))
        # Call the method
        with pytest.raises(InsightsApiError) as exc_info:
            await imagebuilder_mcp_server.get_openapi(endpoints="GET:/blueprints")

        assert_api_error_message(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_openapi_reduces_by_endpoints(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_openapi_response
    ):
        """Test that get_openapi reduces the spec based on the endpoints parameter."""
        endpoint = "openapi.json"
        query = {}
        imagebuilder_mock_client.api.register(
            HTTPMethod.GET, endpoint, response_body=mock_openapi_response, query=query
        )
        # Call with different endpoint filters
        result_small = await imagebuilder_mcp_server.get_openapi(endpoints="GET:/distributions")
        result_large = await imagebuilder_mcp_server.get_openapi(endpoints="POST:/blueprints")

        # Should return different results depending on endpoints
        assert result_small != result_large
        assert len(result_small) < len(result_large)

        assert "/distributions" in result_small
        assert "/blueprints" not in result_small

        assert "/blueprints" in result_large
        assert "/distributions" not in result_large

        assert "ImageTypes" not in result_small
        assert "ImageTypes" not in result_large

    @pytest.mark.asyncio
    async def test_get_openapi_omits_deprecated_image_types(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """get_openapi must not expose deprecated edge image types from the upstream enum."""
        mock_openapi_response = {
            "openapi": "3.0.0",
            "components": {
                "schemas": {
                    "ImageTypes": {
                        "enum": [
                            "guest-image",
                            "edge-commit",
                            "edge-installer",
                            "rhel-edge-commit",
                            "rhel-edge-installer",
                            "ami",
                        ]
                    }
                }
            },
        }
        endpoint = "openapi.json"
        query = {}
        imagebuilder_mock_client.api.register(
            HTTPMethod.GET, endpoint, response_body=mock_openapi_response, query=query
        )
        result = await imagebuilder_mcp_server.get_openapi(endpoints="")

        parsed = json.loads(result)
        image_type_enum = parsed["components"]["schemas"]["ImageTypes"]["enum"]
        assert image_type_enum == ["guest-image", "ami"]
        assert "edge-commit" not in result
