"""Test suite for the create_blueprint() method."""

import pytest

from tests.conftest import (
    TEST_BLUEPRINT_UUID,
    TEST_CLIENT_ID,
    assert_api_error_result,
    assert_instruction_in_result,
)

from .conftest import setup_imagebuilder_mock, setup_imagebuilder_watermark_disabled


class TestCreateBlueprint:
    """Test suite for the create_blueprint() method."""

    @pytest.fixture
    def mock_blueprint_data(self):
        """Mock blueprint creation data."""
        return {
            "name": "test-blueprint",
            "description": "Test blueprint description",
            "distribution": "rhel-9",
            "image_request": {"architecture": "x86_64", "image_type": "guest-image"},
        }

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for blueprint creation."""
        return {
            "id": TEST_BLUEPRINT_UUID,
            "name": "test-blueprint",
            "description": "Test blueprint description\nBlueprint created via insights-mcp",
            "version": 1,
        }

    @pytest.mark.asyncio
    async def test_create_blueprint_basic_functionality(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_blueprint_data, mock_api_response
    ):
        """Test basic functionality of create_blueprint method."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call the method
            result = await imagebuilder_mcp_server.create_blueprint(data=mock_blueprint_data)

            # Verify API was called correctly
            imagebuilder_mock_client.post.assert_called_once()
            call_args = imagebuilder_mock_client.post.call_args
            assert call_args[0][0] == "blueprints"

            # Check that watermark was added to description
            posted_data = call_args.kwargs["json"]
            assert "Blueprint created via insights-mcp" in posted_data["description"]

            # Parse the result
            assert_instruction_in_result(result)
            assert "Blueprint created successfully" in result
            assert mock_api_response["id"] in result
            assert "get_blueprint_details" in result

    @pytest.mark.asyncio
    async def test_create_blueprint_with_watermark_disabled(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_blueprint_data, mock_api_response
    ):
        """Test create_blueprint with watermark disabled via environment variable."""
        # Setup mocks
        with setup_imagebuilder_watermark_disabled():
            imagebuilder_mock_client.post.return_value = mock_api_response
            imagebuilder_mcp_server.clients[TEST_CLIENT_ID] = imagebuilder_mock_client

            # Call the method
            result = await imagebuilder_mcp_server.create_blueprint(data=mock_blueprint_data)

            # Verify watermark was NOT added
            call_args = imagebuilder_mock_client.post.call_args
            posted_data = call_args.kwargs["json"]
            assert posted_data["description"] == mock_blueprint_data["description"]
            assert "Blueprint created via insights-mcp" not in posted_data["description"]
            assert_instruction_in_result(result)  # Verify result is used

    @pytest.mark.asyncio
    async def test_create_blueprint_api_error(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_blueprint_data
    ):
        """Test create_blueprint when API returns error."""
        # Setup mocks
        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.create_blueprint(data=mock_blueprint_data)

            # Should return error message
            assert_api_error_result(result)

    @pytest.mark.asyncio
    async def test_create_blueprint_unexpected_list_response(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_blueprint_data
    ):
        """Test create_blueprint when API returns unexpected list response."""
        # Setup mocks
        list_response = [{"id": "test-id"}]
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, list_response):
            # Call the method
            result = await imagebuilder_mcp_server.create_blueprint(data=mock_blueprint_data)

            # Should return error message about unexpected list response
            assert "Error: the response of blueprint creation is a list" in result
