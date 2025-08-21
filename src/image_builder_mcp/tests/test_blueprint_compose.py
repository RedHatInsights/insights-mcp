"""Test suite for the blueprint_compose() method."""

import pytest

from tests.conftest import (
    TEST_BLUEPRINT_UUID,
    assert_api_error_result,
    assert_instruction_in_result,
)

from .conftest import setup_imagebuilder_mock


class TestBlueprintCompose:
    """Test suite for the blueprint_compose() method."""

    @pytest.fixture
    def mock_compose_response(self):
        """Mock API response for blueprint compose."""
        return [
            {
                "id": "abcd1234-5678-9012-3456-789012345678",
                "blueprint_id": TEST_BLUEPRINT_UUID,
                "status": "PENDING",
            }
        ]

    @pytest.mark.asyncio
    async def test_blueprint_compose_basic_functionality(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_compose_response
    ):
        """Test basic functionality of blueprint_compose method."""
        blueprint_uuid = TEST_BLUEPRINT_UUID

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_compose_response):
            # Call the method
            result = await imagebuilder_mcp_server.blueprint_compose(blueprint_uuid=blueprint_uuid)

            # Verify API was called correctly
            imagebuilder_mock_client.post.assert_called_once_with(f"blueprints/{blueprint_uuid}/compose")

            # Parse the result
            assert_instruction_in_result(result)
            assert "Use the tool get_compose_details" in result
            assert "Compose created successfully" in result
            assert "abcd1234-5678-9012-3456-789012345678" in result

            # Should contain instruction to check details
            assert "get_compose_details" in result
            assert "current build status" in result

    @pytest.mark.asyncio
    async def test_blueprint_compose_multiple_builds(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test blueprint_compose with multiple builds in response."""
        blueprint_uuid = TEST_BLUEPRINT_UUID
        multi_build_response = [
            {"id": "build1-1234-5678-9012-345678901234", "blueprint_id": blueprint_uuid, "status": "PENDING"},
            {"id": "build2-5678-9012-3456-789012345678", "blueprint_id": blueprint_uuid, "status": "PENDING"},
        ]

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, multi_build_response):
            # Call the method
            result = await imagebuilder_mcp_server.blueprint_compose(blueprint_uuid=blueprint_uuid)

            # Should contain both build IDs
            assert "build1-1234-5678-9012-345678901234" in result
            assert "build2-5678-9012-3456-789012345678" in result

    @pytest.mark.asyncio
    async def test_blueprint_compose_api_error(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test blueprint_compose when API returns error."""
        blueprint_uuid = TEST_BLUEPRINT_UUID

        # Setup mocks
        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.blueprint_compose(blueprint_uuid=blueprint_uuid)

            # Should return error message
            assert_api_error_result(result)
            assert blueprint_uuid in result

    @pytest.mark.asyncio
    async def test_blueprint_compose_unexpected_dict_response(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test blueprint_compose when API returns unexpected dict response."""
        blueprint_uuid = TEST_BLUEPRINT_UUID

        # Setup mocks
        # Return dict instead of list (unexpected)
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, {"error": "Some error"}):
            # Call the method
            result = await imagebuilder_mcp_server.blueprint_compose(blueprint_uuid=blueprint_uuid)

            # Should return error message about unexpected dict response
            assert "Error: the response of blueprint_compose is a dict" in result

    @pytest.mark.asyncio
    async def test_blueprint_compose_invalid_build_object(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test blueprint_compose with invalid build object in response."""
        blueprint_uuid = TEST_BLUEPRINT_UUID
        invalid_response = [
            {"id": "valid-build-id-1234-5678-9012-345678901234", "blueprint_id": blueprint_uuid, "status": "PENDING"},
            "invalid-build-object",  # Not a dict
        ]

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, invalid_response):
            # Call the method
            result = await imagebuilder_mcp_server.blueprint_compose(blueprint_uuid=blueprint_uuid)

            # Should handle invalid build object gracefully
            assert "valid-build-id-1234-5678-9012-345678901234" in result
            assert "Invalid build object: invalid-build-object" in result
