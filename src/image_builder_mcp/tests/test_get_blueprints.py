"""Test suite for the get_blueprints() method."""

import json
from unittest.mock import Mock, patch

import pytest

import image_builder_mcp.server as image_builder_mcp

# Clean import - no sys.path.insert needed with proper package structure!
from image_builder_mcp import ImageBuilderMCP
from insights_mcp.client import InsightsClient
from insights_mcp.mcp import INSIGHTS_BASE_URL


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

    @pytest.fixture
    def mcp_server(self):
        """Create a mock MCP server instance."""
        server = ImageBuilderMCP()
        server.init_insights_client(
            client_id="test-client-id",
            client_secret="test-client-secret",
        )
        server.register_tools()
        return server

    @pytest.fixture
    def mock_client(self):
        """Create a mock InsightsClient."""
        client = Mock(spec=InsightsClient)
        client.client_id = "test-client-id"
        client.client_secret = "test-client-secret"
        client.insights_base_url = INSIGHTS_BASE_URL
        client.api_path = "api/v1/image-builder"
        return client

    @pytest.mark.asyncio
    async def test_get_blueprints_basic_functionality(self, mcp_server, mock_client, mock_api_response):  # pylint: disable=too-many-locals
        """Test basic functionality of get_blueprints method."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = mock_api_response
            mcp_server.clients["test-client-id"] = mock_client

            # Call the method with new interface
            result = await mcp_server.get_blueprints(limit=7, offset=0)

            # Verify API was called correctly with limit and offset parameters
            mock_client.get.assert_called_once_with("blueprints", params={"limit": 7, "offset": 0})

            # Parse the result
            assert result.startswith("[INSTRUCTION]")
            assert "Use the UI_URL to link to the blueprint" in result
            assert "[ANSWER]" in result

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
    async def test_get_blueprints_with_limit_and_offset(self, mcp_server, mock_client, mock_api_response):
        """Test get_blueprints with limit and offset parameters."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = mock_api_response
            mcp_server.clients["test-client-id"] = mock_client

            # Call with limit=2, offset=1
            result = await mcp_server.get_blueprints(limit=2, offset=1)

            # Verify API was called with correct parameters
            mock_client.get.assert_called_once_with("blueprints", params={"limit": 2, "offset": 1})

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
    async def test_get_blueprints_with_search_string(self, mcp_server, mock_client, mock_api_response):
        """Test get_blueprints with search string filtering."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = mock_api_response
            mcp_server.clients["test-client-id"] = mock_client

            # Call with search string
            result = await mcp_server.get_blueprints(limit=10, offset=0, search_string="rhel-10")

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
    async def test_get_blueprints_case_insensitive_search(self, mcp_server, mock_client, mock_api_response):
        """Test get_blueprints search is case insensitive."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = mock_api_response
            mcp_server.clients["test-client-id"] = mock_client

            # Call with uppercase search string
            result = await mcp_server.get_blueprints(limit=10, offset=0, search_string="TEST")

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
    async def test_get_blueprints_empty_response(self, mcp_server, mock_client):
        """Test get_blueprints with empty API response."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = {"data": []}
            mcp_server.clients["test-client-id"] = mock_client

            # Call the method
            result = await mcp_server.get_blueprints(limit=7, offset=0)

            # Should return empty list
            assert "[]" in result

    @pytest.mark.asyncio
    async def test_get_blueprints_api_error(self, mcp_server, mock_client):
        """Test get_blueprints when API returns error."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.side_effect = Exception("API Error")
            mcp_server.clients["test-client-id"] = mock_client

            # Call the method
            result = await mcp_server.get_blueprints(limit=7, offset=0)

            # Should return error message
            assert result.startswith("Error: API Error")

    @pytest.mark.asyncio
    async def test_get_blueprints_default_parameters(self, mcp_server, mock_client, mock_api_response):
        """Test get_blueprints uses default parameters correctly."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = mock_api_response
            mcp_server.clients["test-client-id"] = mock_client

            # Call the method without parameters (should use defaults)
            result = await mcp_server.get_blueprints()

            # Verify API was called with default parameters
            mock_client.get.assert_called_once_with("blueprints", params={"limit": 7, "offset": 0})

            # Should return result
            assert "[INSTRUCTION]" in result
            assert "[ANSWER]" in result

    @pytest.mark.asyncio
    async def test_get_blueprints_null_search_string_handling(self, mcp_server, mock_client, mock_api_response):
        """Test handling of 'null' string as search parameter."""
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = mock_api_response
            mcp_server.clients["test-client-id"] = mock_client

            # Call with "null" string (workaround for LLama 3.3 70B Instruct)
            result = await mcp_server.get_blueprints(limit=10, offset=0, search_string="null")

            # Should treat "null" string as None and return all blueprints
            json_start = result.find('[{"reply_id"')
            json_end = result.rfind("}]") + 2
            json_data = result[json_start:json_end]
            blueprints = json.loads(json_data)

            assert len(blueprints) == 4  # All blueprints should be returned

    @pytest.mark.asyncio
    async def test_get_blueprints_zero_limit_uses_default(self, mcp_server, mock_client, mock_api_response):
        """Test that zero or negative limit uses default response size."""
        # Setup mocks
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "test-client-id",
                "insights-client-secret": "test-client-secret",
            }
            mock_client.get.return_value = mock_api_response
            mcp_server.clients["test-client-id"] = mock_client

            # Call with zero limit
            result = await mcp_server.get_blueprints(limit=0)

            # Should use default response size (10)
            mock_client.get.assert_called_once_with("blueprints", params={"limit": 10, "offset": 0})

            # Should return result
            assert "[INSTRUCTION]" in result
            assert "[ANSWER]" in result
