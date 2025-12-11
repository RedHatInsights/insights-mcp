"""Test suite for the update_blueprint() method."""

import pytest

from tests.conftest import (
    TEST_BLUEPRINT_UUID,
    assert_api_error_result,
    assert_instruction_in_result,
)

from .conftest import setup_imagebuilder_mock, setup_imagebuilder_watermark_disabled


class TestUpdateBlueprint:
    """Test suite for the update_blueprint() method."""

    @pytest.fixture
    def mock_blueprint_data(self):
        """Mock blueprint update data."""
        return {
            "name": "updated-blueprint",
            "description": "Updated blueprint description",
            "distribution": "rhel-9",
            "image_request": {"architecture": "x86_64", "image_type": "guest-image"},
        }

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for blueprint update."""
        return {
            "id": TEST_BLUEPRINT_UUID,
            "name": "updated-blueprint",
            "description": "Updated blueprint description\nBlueprint updated via insights-mcp",
            "version": 2,
        }

    @pytest.mark.asyncio
    async def test_update_blueprint_basic_functionality(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_blueprint_data, mock_api_response
    ):
        """Test basic functionality of update_blueprint method."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call the method
            result = await imagebuilder_mcp_server.update_blueprint(
                blueprint_uuid=TEST_BLUEPRINT_UUID, data=mock_blueprint_data
            )

            # Verify API was called correctly
            imagebuilder_mock_client.put.assert_called_once()
            call_args = imagebuilder_mock_client.put.call_args
            assert call_args[0][0] == f"blueprints/{TEST_BLUEPRINT_UUID}"

            # Check that watermark was added to description
            posted_data = call_args.kwargs["json"]
            assert "Blueprint updated via insights-mcp" in posted_data["description"]

            # Parse the result
            assert "Blueprint updated successfully" in result

    @pytest.mark.asyncio
    async def test_update_blueprint_with_existing_watermark(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test update_blueprint with existing watermark in description."""
        blueprint_data = {
            "name": "updated-blueprint",
            "description": "Updated description\nBlueprint created via insights-mcp",
            "distribution": "rhel-9",
        }

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call the method
            result = await imagebuilder_mcp_server.update_blueprint(
                blueprint_uuid=TEST_BLUEPRINT_UUID, data=blueprint_data
            )

            # Verify watermark was NOT duplicated
            call_args = imagebuilder_mock_client.put.call_args
            posted_data = call_args.kwargs["json"]
            # Should keep existing description without adding another watermark
            assert posted_data["description"] == blueprint_data["description"]
            assert "Blueprint updated successfully" in result  # Verify result is used

    @pytest.mark.asyncio
    async def test_update_blueprint_with_watermark_disabled(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_blueprint_data, mock_api_response
    ):
        """Test update_blueprint with watermark disabled via environment variable."""
        # Setup mocks
        with (
            setup_imagebuilder_watermark_disabled(imagebuilder_mcp_server, imagebuilder_mock_client),
            setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response),
        ):
            # Call the method
            result = await imagebuilder_mcp_server.update_blueprint(
                blueprint_uuid=TEST_BLUEPRINT_UUID, data=mock_blueprint_data
            )

            # Verify watermark was NOT added
            call_args = imagebuilder_mock_client.put.call_args
            posted_data = call_args.kwargs["json"]
            assert posted_data["description"] == mock_blueprint_data["description"]
            assert "Blueprint updated via insights-mcp" not in posted_data["description"]
            assert_instruction_in_result(result)  # Verify result is used

    @pytest.mark.asyncio
    async def test_update_blueprint_api_error(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_blueprint_data
    ):
        """Test update_blueprint when API returns error."""
        # Setup mocks
        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.update_blueprint(
                blueprint_uuid=TEST_BLUEPRINT_UUID, data=mock_blueprint_data
            )

            # Should return error message
            assert_api_error_result(result)
