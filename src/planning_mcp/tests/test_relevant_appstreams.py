"""Test suite for the get_relevant_appstreams() method."""
# pylint: disable=duplicate-code

import json
from unittest.mock import patch

import pytest

from tests.conftest import (
    assert_api_error_result,
)


class TestPlanningGetRelevantAppstreams:
    """Test suite for the get_relevant_appstreams() method."""

    @pytest.fixture
    def mock_appstreams_response(self):
        """Mock API response for relevant appstreams with varied data."""
        return {
            "meta": {
                "count": 3,
                "total": 3,
            },
            "data": [
                {
                    "name": "nodejs:18",
                    "display_name": "Node.js 18",
                    "application_stream_name": "Node.js 18",
                    "stream": "18",
                    "start_date": "2023-05-01",
                    "end_date": "2025-04-30",
                    "support_status": "Supported",
                    "os_major": 9,
                    "os_minor": 2,
                    "related": False,
                },
                {
                    "name": "nodejs:20",
                    "display_name": "Node.js 20",
                    "application_stream_name": "Node.js 20",
                    "stream": "20",
                    "start_date": "2024-04-01",
                    "end_date": "2026-04-30",
                    "support_status": "Supported",
                    "os_major": 9,
                    "os_minor": 4,
                    "related": True,
                },
                {
                    "name": "postgresql:15",
                    "display_name": "PostgreSQL 15",
                    "application_stream_name": "PostgreSQL 15",
                    "stream": "15",
                    "start_date": "2023-11-01",
                    "end_date": "2025-11-13",
                    "support_status": "Supported",
                    "os_major": 9,
                    "os_minor": 3,
                    "related": False,
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_relevant_appstreams_basic_functionality(
        self,
        planning_mcp_server,
        mock_appstreams_response,
    ):
        """Test basic functionality of get_relevant_appstreams method."""
        # Patch underlying Insights client used by Planning MCP
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_appstreams_response

            # Call the method with include_related=True (default)
            result = await planning_mcp_server.get_relevant_appstreams()

            # Backend endpoint should be invoked with related=true
            mock_get.assert_called_once_with(
                "relevant/lifecycle/app-streams",
                params={"related": "true"},
            )

            # Tool returns a JSON-encoded string; parse and validate structure
            parsed = json.loads(result)

            # Minimal but realistic structure checks
            assert "meta" in parsed
            assert "data" in parsed
            assert isinstance(parsed["data"], list)
            assert parsed["meta"]["count"] == 3
            assert parsed["meta"]["total"] == 3
            assert len(parsed["data"]) == 3

            # Verify structure of first item (nodejs:18)
            item = parsed["data"][0]

            # Top-level fields
            assert "name" in item
            assert "display_name" in item
            assert "application_stream_name" in item
            assert "stream" in item
            assert "start_date" in item
            assert "end_date" in item
            assert "support_status" in item
            assert "os_major" in item
            assert "os_minor" in item
            assert "related" in item

            # Verify it's the nodejs:18 item
            assert item["name"] == "nodejs:18"
            assert item["display_name"] == "Node.js 18"
            assert item["stream"] == "18"
            assert item["support_status"] == "Supported"
            assert item["related"] is False

    @pytest.mark.asyncio
    async def test_get_relevant_appstreams_with_major_version(
        self,
        planning_mcp_server,
        mock_appstreams_response,
    ):
        """Test get_relevant_appstreams with major version filter."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_appstreams_response

            # Call with major version
            result = await planning_mcp_server.get_relevant_appstreams(major="9")

            # Backend should receive the major parameter and related=true
            mock_get.assert_called_once_with(
                "relevant/lifecycle/app-streams",
                params={"major": 9, "related": "true"},
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_get_relevant_appstreams_with_major_and_minor(
        self,
        planning_mcp_server,
        mock_appstreams_response,
    ):
        """Test get_relevant_appstreams with major and minor version filters."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_appstreams_response

            # Call with both major and minor versions
            result = await planning_mcp_server.get_relevant_appstreams(major="9", minor="2")

            # Backend should receive both parameters and related=true
            mock_get.assert_called_once_with(
                "relevant/lifecycle/app-streams",
                params={"major": 9, "minor": 2, "related": "true"},
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_get_relevant_appstreams_include_related_false(
        self,
        planning_mcp_server,
        mock_appstreams_response,
    ):
        """Test get_relevant_appstreams with include_related=False."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            # Return only non-related streams
            filtered_response = {
                "meta": {"count": 2, "total": 2},
                "data": [item for item in mock_appstreams_response["data"] if not item["related"]],
            }
            mock_get.return_value = filtered_response

            # Call with include_related=False
            result = await planning_mcp_server.get_relevant_appstreams(include_related=False)

            # Backend should receive related=false
            mock_get.assert_called_once_with(
                "relevant/lifecycle/app-streams",
                params={"related": "false"},
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed
            assert parsed["meta"]["count"] == 2
            # All returned items should have related=False
            for item in parsed["data"]:
                assert item["related"] is False

    @pytest.mark.asyncio
    async def test_get_relevant_appstreams_include_related_true(
        self,
        planning_mcp_server,
        mock_appstreams_response,
    ):
        """Test get_relevant_appstreams with include_related=True."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_appstreams_response

            # Call with include_related=True (explicit)
            result = await planning_mcp_server.get_relevant_appstreams(include_related=True)

            # Backend should receive related=true
            mock_get.assert_called_once_with(
                "relevant/lifecycle/app-streams",
                params={"related": "true"},
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed
            assert parsed["meta"]["count"] == 3
            # Response should include both related and non-related items
            related_items = [item for item in parsed["data"] if item["related"]]
            non_related_items = [item for item in parsed["data"] if not item["related"]]
            assert len(related_items) > 0
            assert len(non_related_items) > 0

    @pytest.mark.asyncio
    async def test_get_relevant_appstreams_minor_without_major_raises_error(
        self,
        planning_mcp_server,
    ):
        """Test that providing minor without major returns an error."""
        result = await planning_mcp_server.get_relevant_appstreams(minor="2")

        # The error should be returned as a string, not raised
        assert "Error: API Error" in result
        assert "The 'minor' parameter requires 'major' to be specified" in result

    @pytest.mark.asyncio
    async def test_get_relevant_appstreams_api_error(self, planning_mcp_server):
        """Test get_relevant_appstreams when backend raises an API error."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.side_effect = Exception("Backend unavailable")

            result = await planning_mcp_server.get_relevant_appstreams()

            # Reuse common helper to validate error formatting
            assert_api_error_result(result)
