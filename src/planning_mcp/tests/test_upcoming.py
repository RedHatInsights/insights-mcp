"""Test suite for the get_upcoming_changes() method."""

import json
from unittest.mock import patch

import pytest

from tests.conftest import (
    assert_api_error_result,
)


class TestPlanningGetUpcomingChanges:
    """Test suite for the get_upcoming_changes() method."""

    @pytest.fixture
    def mock_upcoming_response(self):
        """Mock API response for upcoming changes (schema aligned, data anonymised)."""
        return {
            "meta": {
                "count": 3,
                "total": 3,
            },
            "data": [
                {
                    "name": "Example feature A",
                    "type": "addition",
                    "packages": ["example-package-a"],
                    "release": "10.2",
                    "os_major": 10,
                    "date": "2030-01-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "Example feature A is planned for a future RHEL release.",
                        "trainingTicket": "PLAN-0001",
                        "dateAdded": "2029-01-01",
                        "lastModified": "2029-06-01",
                    },
                    "package": "example-package-a",
                },
                {
                    "name": "Example feature B",
                    "type": "addition",
                    "packages": ["example-package-b"],
                    "release": "9.9",
                    "os_major": 9,
                    "date": "2031-05-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "Example feature B is tentatively planned.",
                        "trainingTicket": "PLAN-0002",
                        "dateAdded": "2030-02-01",
                        "lastModified": "2030-03-01",
                    },
                    "package": "example-package-b",
                },
                {
                    "name": "Example deprecation C",
                    "type": "deprecation",
                    "packages": [],
                    "release": "11.0",
                    "os_major": 11,
                    "date": "2032-10-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "Example component C is planned to be removed in a future major release.",
                        "trainingTicket": "PLAN-0003",
                        "dateAdded": "2031-04-01",
                        "lastModified": "2031-12-01",
                    },
                    "package": "",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_upcoming_changes_basic_functionality(
        self,
        planning_mcp_server,
        mock_upcoming_response,
    ):
        """Test basic functionality of get_upcoming_changes method."""
        # Patch underlying Insights client used by Planning MCP
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_upcoming_response

            # Call the MCP method (no parameters by design)
            result = await planning_mcp_server.get_upcoming_changes()

            # Backend endpoint should be invoked exactly once, with the correct path suffix
            mock_get.assert_called_once_with("upcoming-changes")

            # Tool returns a JSON-encoded string; parse and validate structure
            parsed = json.loads(result)

            assert parsed == mock_upcoming_response

            # Minimal but realistic structure checks
            assert "meta" in parsed
            assert "data" in parsed
            assert isinstance(parsed["data"], list)
            assert parsed["meta"]["count"] == 3
            assert parsed["meta"]["total"] == 3

            for item in parsed["data"]:
                # Top-level fields
                assert "name" in item
                assert "type" in item
                assert "packages" in item
                assert "release" in item
                assert "os_major" in item
                assert "date" in item
                assert "details" in item
                assert "package" in item

                # details sub-object
                details = item["details"]
                assert isinstance(details, dict)
                assert "summary" in details
                assert "dateAdded" in details
                assert "lastModified" in details
                assert "trainingTicket" in details

    @pytest.mark.asyncio
    async def test_get_upcoming_changes_api_error(self, planning_mcp_server):
        """Test get_upcoming_changes when backend raises an API error."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.side_effect = Exception("Backend unavailable")

            result = await planning_mcp_server.get_upcoming_changes()

            # Reuse common helper to validate error formatting
            assert_api_error_result(result)
