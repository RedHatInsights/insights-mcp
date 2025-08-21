"""Test suite for the get_composes() method."""

import json

import pytest

from tests.conftest import (
    TEST_BLUEPRINT_UUID,
    assert_api_error_result,
    assert_empty_response,
    assert_instruction_in_result,
)

from .conftest import setup_imagebuilder_mock


class TestGetComposes:
    """Test suite for the get_composes() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response based on typical compose data."""
        return {
            "data": [
                {
                    "id": "abcd1234-5678-9012-3456-789012345678",
                    "blueprint_id": TEST_BLUEPRINT_UUID,
                    "image_name": "rhel-9-test-image",
                    "created_at": "2025-01-18T15:30:00Z",
                    "image_status": {"status": "SUCCESS"},
                },
                {
                    "id": "efgh5678-9012-3456-7890-123456789012",
                    "blueprint_id": "87654321-4321-4321-4321-210987654321",
                    "image_name": "rhel-10-production",
                    "created_at": "2025-01-18T14:15:00Z",
                    "image_status": {"status": "RUNNING"},
                },
                {
                    "id": "ijkl9012-3456-7890-1234-567890123456",
                    "blueprint_id": "11111111-2222-3333-4444-555555555555",
                    "image_name": "fedora-test-build",
                    "created_at": "2025-01-18T13:00:00Z",
                    "image_status": {"status": "FAILED"},
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_get_composes_basic_functionality(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test basic functionality of get_composes method."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call the method
            result = await imagebuilder_mcp_server.get_composes(limit=7, offset=0, search_string="")

            # Verify API was called correctly
            imagebuilder_mock_client.get.assert_called_once_with("composes", params={"limit": 7, "offset": 0})

            # Parse the result
            assert_instruction_in_result(result)
            assert "Present a bulleted list" in result
            assert "There could be more entries" in result

            # Extract JSON data from result
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            composes = json.loads(json_data)

            # Verify structure and content
            assert len(composes) == 3
            assert all(isinstance(compose, dict) for compose in composes)

            # Check required fields exist
            required_fields = ["reply_id", "compose_uuid", "blueprint_id", "image_name", "blueprint_url"]
            for compose in composes:
                for field in required_fields:
                    assert field in compose

            # Verify sorting by created_at (descending - most recent first)
            expected_order = [
                "rhel-9-test-image",  # 2025-01-18T15:30:00Z
                "rhel-10-production",  # 2025-01-18T14:15:00Z
                "fedora-test-build",  # 2025-01-18T13:00:00Z
            ]
            actual_order = [compose["image_name"] for compose in composes]
            assert actual_order == expected_order

    @pytest.mark.asyncio
    async def test_get_composes_with_search_string(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test get_composes with search string filtering."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with search string for "rhel"
            result = await imagebuilder_mcp_server.get_composes(limit=10, offset=0, search_string="rhel")

            # Extract JSON data from result
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            composes = json.loads(json_data)

            # Should return only composes containing "rhel"
            assert len(composes) == 2
            for compose in composes:
                assert "rhel" in compose["image_name"].lower()

    @pytest.mark.asyncio
    async def test_get_composes_with_limit_and_offset(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test get_composes with limit and offset parameters."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with limit=2, offset=1
            result = await imagebuilder_mcp_server.get_composes(limit=2, offset=1, search_string="")

            # Verify API was called with correct parameters
            imagebuilder_mock_client.get.assert_called_once_with("composes", params={"limit": 2, "offset": 1})

            # Extract JSON data from result
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            composes = json.loads(json_data)

            # Should return all 3 composes since filtering is client-side
            assert len(composes) == 3

            # Verify reply_id sequence starts from offset + 1
            reply_ids = [compose["reply_id"] for compose in composes]
            assert reply_ids == [2, 3, 4]  # offset=1, so starts from 2

    @pytest.mark.asyncio
    async def test_get_composes_empty_response(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_composes with empty API response."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, {"data": []}):
            # Call the method
            result = await imagebuilder_mcp_server.get_composes(limit=7, offset=0, search_string="")

            # Should return empty list
            assert_empty_response(result)

    @pytest.mark.asyncio
    async def test_get_composes_api_error(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_composes when API returns error."""
        # Setup mocks
        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.get_composes(limit=7, offset=0, search_string="")

            # Should return error message
            assert_api_error_result(result)

    @pytest.mark.asyncio
    async def test_get_composes_zero_limit_uses_default(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test that zero limit uses default response size."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with zero limit
            result = await imagebuilder_mcp_server.get_composes(limit=0, offset=0, search_string="")

            # Should use default response size (10)
            imagebuilder_mock_client.get.assert_called_once_with("composes", params={"limit": 10, "offset": 0})
            assert_instruction_in_result(result)  # Verify result is used
