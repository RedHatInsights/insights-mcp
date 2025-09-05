"""Test suite for the get_compose_details() method."""

import json

import pytest

from tests.conftest import (
    TEST_BLUEPRINT_UUID,
    assert_api_error_result,
)

from .conftest import setup_imagebuilder_mock


class TestGetComposeDetails:
    """Test suite for the get_compose_details() method."""

    @pytest.fixture
    def mock_compose_details_success(self):
        """Mock compose details response for successful build."""
        return {
            "id": "abcd1234-5678-9012-3456-789012345678",
            "blueprint_id": TEST_BLUEPRINT_UUID,
            "image_name": "rhel-9-test-image",
            "created_at": "2025-01-18T15:30:00Z",
            "image_status": {
                "status": "SUCCESS",
                "upload_status": {
                    "type": "aws",
                    "options": {"url": "https://example.com/download/image.tar.gz", "image_name": "my-custom-image"},
                },
            },
        }

    @pytest.fixture
    def mock_compose_details_gcp(self):
        """Mock compose details response for GCP build."""
        return {
            "id": "abcd1234-5678-9012-3456-789012345678",
            "blueprint_id": TEST_BLUEPRINT_UUID,
            "image_name": "rhel-9-gcp-image",
            "created_at": "2025-01-18T15:30:00Z",
            "image_status": {
                "status": "SUCCESS",
                "upload_status": {"type": "gcp", "options": {"image_name": "my-gcp-image"}},
            },
        }

    @pytest.fixture
    def mock_compose_details_running(self):
        """Mock compose details response for running build."""
        return {
            "id": "efgh5678-9012-3456-7890-123456789012",
            "blueprint_id": "87654321-4321-4321-4321-210987654321",
            "image_name": "rhel-10-production",
            "created_at": "2025-01-18T14:15:00Z",
            "image_status": {"status": "RUNNING"},
        }

    @pytest.mark.asyncio
    async def test_get_compose_details_valid_uuid(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_compose_details_success
    ):
        """Test get_compose_details with valid UUID."""
        compose_uuid = "abcd1234-5678-9012-3456-789012345678"

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_compose_details_success):
            # Call the method
            result = await imagebuilder_mcp_server.get_compose_details(compose_identifier=compose_uuid)

            # Verify API was called correctly
            imagebuilder_mock_client.get.assert_called_once_with(f"composes/{compose_uuid}")

            # Parse the result
            assert "https://example.com/download/image.tar.gz" in result
            assert "Always present this link to the user" in result

            # Extract JSON data
            json_start = result.find('{"id"')
            parsed_result = json.loads(result[json_start:])
            assert parsed_result["compose_uuid"] == compose_uuid
            assert parsed_result["id"] == compose_uuid

    @pytest.mark.asyncio
    async def test_get_compose_details_gcp_image(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_compose_details_gcp
    ):
        """Test get_compose_details with GCP image type."""
        compose_uuid = "abcd1234-5678-9012-3456-789012345678"

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_compose_details_gcp):
            # Call the method
            result = await imagebuilder_mcp_server.get_compose_details(compose_identifier=compose_uuid)

            # Should contain GCP-specific instructions
            assert "gcloud compute instances create" in result
            assert "gcloud compute images create" in result
            assert "my-gcp-image" in result

    @pytest.mark.asyncio
    async def test_get_compose_details_invalid_uuid(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_compose_details with invalid UUID format."""
        invalid_uuid = "invalid-uuid-format"

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, [{"id": "test-id"}]):
            # Call the method
            result = await imagebuilder_mcp_server.get_compose_details(compose_identifier=invalid_uuid)

            # Should return error message about invalid identifier
            assert "[INSTRUCTION] Error:" in result
            assert "is not a valid compose identifier" in result
            assert "please use a UUID from get_composes" in result

    @pytest.mark.asyncio
    async def test_get_compose_details_empty_identifier(self, imagebuilder_mcp_server):
        """Test get_compose_details with empty identifier."""
        # Call the method with empty identifier
        result = await imagebuilder_mcp_server.get_compose_details(compose_identifier="")

        # Should return error message
        assert result == "Error: Compose UUID is required"

    @pytest.mark.asyncio
    async def test_get_compose_details_api_error(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_compose_details when API returns error."""
        compose_uuid = "abcd1234-5678-9012-3456-789012345678"

        # Setup mocks
        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.get_compose_details(compose_identifier=compose_uuid)

            # Should return error message
            assert_api_error_result(result)

    @pytest.mark.asyncio
    async def test_get_compose_details_unexpected_list_response(
        self, imagebuilder_mcp_server, imagebuilder_mock_client
    ):
        """Test get_compose_details when API returns unexpected list response."""
        compose_uuid = "abcd1234-5678-9012-3456-789012345678"

        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, [{"id": "test-id"}]):
            # Call the method
            result = await imagebuilder_mcp_server.get_compose_details(compose_identifier=compose_uuid)

            # Should handle unexpected list response gracefully
            assert f"Error: Unexpected list response for {compose_uuid}" in result
