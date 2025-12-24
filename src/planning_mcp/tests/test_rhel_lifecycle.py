"""Test suite for the get_rhel_lifecycle() method."""

import json
from unittest.mock import patch

import pytest

from tests.conftest import (
    assert_api_error_result,
)


class TestPlanningGetRhelLifecycle:
    """Test suite for the get_rhel_lifecycle() method."""

    @pytest.fixture
    def mock_lifecycle_response(self):
        """Mock API response for RHEL lifecycle (schema aligned, data anonymized)."""
        return {
            "data": [
                {
                    "name": "RHEL",
                    "start_date": "2050-01-01",
                    "end_date": "2060-12-31",
                    "support_status": "Upcoming release",
                    "display_name": "Example OS 99",
                    "major": 99,
                    "minor": None,
                    "end_date_e4s": None,
                    "end_date_els": "2063-12-31",
                    "end_date_eus": None,
                },
                {
                    "name": "RHEL",
                    "start_date": "2040-01-01",
                    "end_date": "2040-06-30",
                    "support_status": "Supported",
                    "display_name": "Example OS 98.5",
                    "major": 98,
                    "minor": 5,
                    "end_date_e4s": "2044-12-31",
                    "end_date_els": None,
                    "end_date_eus": "2042-12-31",
                },
                {
                    "name": "RHEL",
                    "start_date": "2030-01-01",
                    "end_date": "2030-06-30",
                    "support_status": "Retired",
                    "display_name": "Example OS 97.0",
                    "major": 97,
                    "minor": 0,
                    "end_date_e4s": None,
                    "end_date_els": None,
                    "end_date_eus": None,
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_rhel_lifecycle_basic_functionality(
        self,
        planning_mcp_server,
        mock_lifecycle_response,
    ):
        """Test basic functionality of get_rhel_lifecycle method."""
        # Patch underlying Insights client used by Planning MCP
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_lifecycle_response

            # Call the MCP method (no parameters by design)
            result = await planning_mcp_server.get_rhel_lifecycle()

            # Backend endpoint should be invoked exactly once, with the correct path suffix
            mock_get.assert_called_once_with("lifecycle/rhel")

            # Tool returns a JSON-encoded string; parse and validate structure
            parsed = json.loads(result)

            assert parsed == mock_lifecycle_response

            # Minimal but realistic structure checks
            assert "data" in parsed
            assert isinstance(parsed["data"], list)
            assert len(parsed["data"]) == 3

            for item in parsed["data"]:
                # Top-level fields
                assert "name" in item
                assert "start_date" in item
                assert "end_date" in item
                assert "support_status" in item
                assert "display_name" in item
                assert "major" in item
                assert "minor" in item
                assert "end_date_e4s" in item
                assert "end_date_els" in item
                assert "end_date_eus" in item

    @pytest.mark.asyncio
    async def test_get_rhel_lifecycle_api_error(self, planning_mcp_server):
        """Test get_rhel_lifecycle when backend raises an API error."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.side_effect = Exception("Backend unavailable")

            result = await planning_mcp_server.get_rhel_lifecycle()

            # Reuse common helper to validate error formatting
            assert_api_error_result(result)
