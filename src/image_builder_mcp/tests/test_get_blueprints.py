"""Test suite for the get_blueprints() method."""

import json

import pytest

from .conftest import setup_imagebuilder_mock


class TestGetBlueprints:
    """Test suite for the get_blueprints() method."""

    @pytest.fixture
    def mock_api_response(self):
        """Mock API response based on the provided sample."""
        return {
            "data": [
                {
                    "description": "",
                    "id": "69ca10f4-f245-4226-ae99-83f3f02d7271",
                    "last_modified_at": "2025-07-02T21:12:12Z",
                    "name": "rhel-10-x86_64-07022025-1708",
                    "version": 1,
                },
                {
                    "description": "",
                    "id": "bd5bd5b7-2028-4371-9bf9-90b54565d549",
                    "last_modified_at": "2025-07-02T18:14:17Z",
                    "name": "test-rhel-9-x86_64-07022025-1708",
                    "version": 1,
                },
                {
                    "description": "",
                    "id": "32f14279-3db8-441b-8f91-9d84b0229787",
                    "last_modified_at": "2025-07-01T15:27:11Z",
                    "name": "test-rhel-10-x86_64-07012025-1726",
                    "version": 1,
                },
                {
                    "description": "",
                    "id": "7fb574ff-4c8e-4f97-8d1f-0f646d4f4597",
                    "last_modified_at": "2025-06-30T11:12:15Z",
                    "name": "rhel-9-x86_64-06302025-1310",
                    "version": 1,
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_get_blueprints_basic_functionality(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):  # pylint: disable=too-many-locals
        """Test basic functionality of get_blueprints method."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call the method with new interface
            result = await imagebuilder_mcp_server.get_blueprints(limit=7, offset=0, search_string="")

            # Verify API was called correctly with limit and offset parameters
            imagebuilder_mock_client.get.assert_called_once_with("blueprints", params={"limit": 7, "offset": 0})

            # Parse the result
            assert result.startswith("[INSTRUCTION]")
            assert "Use the UI_URL to link to the blueprint" in result
            # check paging reminder
            assert "There could be more entries" in result

            # Extract JSON data from result
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            blueprints = json.loads(json_data)

            # Verify structure and content
            assert len(blueprints) == 4
            assert all(isinstance(bp, dict) for bp in blueprints)

            # Check required fields exist
            required_fields = ["reply_id", "blueprint_uuid", "UI_URL", "name"]
            for blueprint in blueprints:
                for field in required_fields:
                    assert field in blueprint

            # Verify sorting by last_modified_at (descending)
            expected_order = [
                "rhel-10-x86_64-07022025-1708",  # 2025-07-02T21:12:12Z
                "test-rhel-9-x86_64-07022025-1708",  # 2025-07-02T18:14:17Z
                "test-rhel-10-x86_64-07012025-1726",  # 2025-07-01T15:27:11Z
                "rhel-9-x86_64-06302025-1310",  # 2025-06-30T11:12:15Z
            ]
            actual_order = [bp["name"] for bp in blueprints]
            assert actual_order == expected_order

            # Verify reply_id sequence (starts from offset + 1)
            reply_ids = [bp["reply_id"] for bp in blueprints]
            assert reply_ids == [1, 2, 3, 4]

            # Verify UI_URL format
            for blueprint in blueprints:
                expected_url = (
                    f"https://console.redhat.com/insights/image-builder/imagewizard/{blueprint['blueprint_uuid']}"
                )
                assert blueprint["UI_URL"] == expected_url

    @pytest.mark.asyncio
    async def test_get_blueprints_with_limit_and_offset(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test get_blueprints with limit and offset parameters."""
        # Setup mocks
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with limit=2, offset=1
            result = await imagebuilder_mcp_server.get_blueprints(limit=2, offset=1, search_string="")

            # Verify API was called with correct parameters
            # Note: search_string is not passed to the Image Builder API
            imagebuilder_mock_client.get.assert_called_once_with("blueprints", params={"limit": 2, "offset": 1})

            # Extract JSON data from result
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            blueprints = json.loads(json_data)

            # Should return all 4 blueprints since we're filtering client-side
            assert len(blueprints) == 4

            # Verify reply_id sequence starts from offset + 1
            reply_ids = [bp["reply_id"] for bp in blueprints]
            assert reply_ids == [2, 3, 4, 5]  # offset=1, so starts from 2

    @pytest.mark.asyncio
    async def test_get_blueprints_with_search_string(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test get_blueprints with search string filtering."""
        # Setup mocks

        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with search string
            result = await imagebuilder_mcp_server.get_blueprints(limit=10, offset=0, search_string="rhel-10")

            # Note: search_string is not passed to the Image Builder API
            imagebuilder_mock_client.get.assert_called_once_with("blueprints", params={"limit": 10, "offset": 0})

            # Extract JSON data from result
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            blueprints = json.loads(json_data)

            # Should return only blueprints containing "rhel-10"
            assert len(blueprints) == 2
            for blueprint in blueprints:
                assert "rhel-10" in blueprint["name"].lower()

    @pytest.mark.asyncio
    async def test_get_blueprints_case_insensitive_search(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test get_blueprints search is case insensitive."""
        # Setup mocks

        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with uppercase search string
            result = await imagebuilder_mcp_server.get_blueprints(limit=10, offset=0, search_string="TEST")

            # Extract JSON data from result
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            blueprints = json.loads(json_data)

            # Should find the blueprint with "TEST" in name (case insensitive search)
            assert len(blueprints) == 2
            blueprint_names = [bp["name"] for bp in blueprints]
            assert "test-rhel-9-x86_64-07022025-1708" in blueprint_names
            assert "test-rhel-10-x86_64-07012025-1726" in blueprint_names

    @pytest.mark.asyncio
    async def test_get_blueprints_empty_response(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_blueprints with empty API response."""
        # Setup mocks

        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, {"data": []}):
            # Call the method
            result = await imagebuilder_mcp_server.get_blueprints(limit=7, offset=0, search_string="")

            # Should return empty list
            assert "[]" in result

    @pytest.mark.asyncio
    async def test_get_blueprints_api_error(self, imagebuilder_mcp_server, imagebuilder_mock_client):
        """Test get_blueprints when API returns error."""
        # Setup mocks

        with setup_imagebuilder_mock(
            imagebuilder_mcp_server, imagebuilder_mock_client, side_effect=Exception("API Error")
        ):
            # Call the method
            result = await imagebuilder_mcp_server.get_blueprints(limit=7, offset=0, search_string="")

            # Should return error message
            assert result.startswith("Error: API Error")

    @pytest.mark.asyncio
    async def test_get_blueprints_null_search_string_handling(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test handling of 'null' string as search parameter."""
        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with "null" string (workaround for LLama 3.3 70B Instruct)
            result = await imagebuilder_mcp_server.get_blueprints(limit=10, offset=0, search_string="null")

            # Should treat "null" string as None and return all blueprints
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            blueprints = json.loads(json_data)

            assert len(blueprints) == 4  # All blueprints should be returned

    @pytest.mark.asyncio
    async def test_get_blueprints_zero_limit_uses_default(
        self, imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response
    ):
        """Test that zero or negative limit uses default response size."""
        # Setup mocks

        with setup_imagebuilder_mock(imagebuilder_mcp_server, imagebuilder_mock_client, mock_api_response):
            # Call with zero limit
            result = await imagebuilder_mcp_server.get_blueprints(limit=0, offset=0, search_string="")

            # Should use default response size (10)
            imagebuilder_mock_client.get.assert_called_once_with("blueprints", params={"limit": 10, "offset": 0})

            # Should return result
            assert "[INSTRUCTION]" in result
            # check paging reminder
            assert "There could be more entries" in result
