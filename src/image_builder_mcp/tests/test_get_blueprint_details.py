"""Test suite for the get_blueprint_details() method."""

import json

import pytest

from tests.conftest import (
    TEST_BLUEPRINT_UUID,
    assert_api_error_result,
)

from .conftest import setup_imagebuilder_mock


class TestGetBlueprintDetails:
    """Test suite for the get_blueprint_details() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for blueprint details."""
        return {
            "id": TEST_BLUEPRINT_UUID,
            "name": "test-blueprint",
            "description": "Test blueprint description",
            "distribution": "rhel-9",
            "version": 1,
            "last_modified_at": "2025-01-18T10:30:00Z",
            "image_request": {"architecture": "x86_64", "image_type": "guest-image"},
        }

    @pytest.mark.asyncio
    async def test_get_blueprint_details_valid_uuid(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test get_blueprint_details with valid UUID."""
        blueprint_uuid = TEST_BLUEPRINT_UUID

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call the method
            result = await imagebuilder_mcp_server.get_blueprint_details(blueprint_identifier=blueprint_uuid)

            # Verify API was called correctly
            imagebuilder_mock_client.get.assert_called_once_with(f"blueprints/{blueprint_uuid}")

            # Parse the result - should be wrapped in a list
            parsed_result = json.loads(result)
            assert isinstance(parsed_result, list)
            assert len(parsed_result) == 1
            assert parsed_result[0] == mock_api_response

    @pytest.mark.asyncio
    async def test_get_blueprint_details_invalid_uuid(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_blueprint_details with invalid UUID format."""
        invalid_uuid = "invalid-uuid-format"

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, [{"id": "test-id"}]):
            # Call the method
            result = await imagebuilder_mcp_server.get_blueprint_details(blueprint_identifier=invalid_uuid)

            # Should return error message about invalid identifier
            assert "[INSTRUCTION] Error:" in result
            assert "is not a valid blueprint identifier" in result
            assert "please use the UUID from get_blueprints" in result

    @pytest.mark.asyncio
    async def test_get_blueprint_details_empty_identifier(self, imagebuilder_mcp_server):
        """Test get_blueprint_details with empty identifier."""
        # Call the method with empty identifier
        result = await imagebuilder_mcp_server.get_blueprint_details(blueprint_identifier="")

        # Should return error message
        assert result == "Error: a blueprint identifier is required"

    @pytest.mark.asyncio
    async def test_get_blueprint_details_api_error(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_blueprint_details when API returns error."""
        blueprint_uuid = TEST_BLUEPRINT_UUID

        # Setup mocks
        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.get_blueprint_details(blueprint_identifier=blueprint_uuid)

            # Should return error message
            assert_api_error_result(result)

    @pytest.mark.asyncio
    async def test_get_blueprint_details_unexpected_list_response(
        self, imagebuilder_mcp_server, imagebuilder_mock_client
    ):
        """Test get_blueprint_details when API returns unexpected list response."""
        blueprint_uuid = TEST_BLUEPRINT_UUID

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, [{"id": "test-id"}]):
            # Call the method
            result = await imagebuilder_mcp_server.get_blueprint_details(blueprint_identifier=blueprint_uuid)

            # Should handle unexpected list response gracefully
            parsed_result = json.loads(result)
            assert isinstance(parsed_result, list)
            assert "error" in parsed_result[0]
            assert "Unexpected list response" in parsed_result[0]["error"]
