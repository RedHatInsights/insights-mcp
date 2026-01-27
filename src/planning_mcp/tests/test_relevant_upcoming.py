"""Test suite for the get_relevant_upcoming_changes() method."""
# pylint: disable=duplicate-code

import json
from unittest.mock import patch

import pytest

from tests.conftest import (
    assert_api_error_result,
)


class TestPlanningGetRelevantUpcomingChanges:
    """Test suite for the get_relevant_upcoming_changes() method."""

    @pytest.fixture
    def mock_upcoming_response(self):
        """Mock API response for upcoming changes with varied data."""
        return {
            "meta": {
                "count": 5,
                "total": 5,
            },
            "data": [
                {
                    "name": "Add Node.js to RHEL8 AppStream",
                    "type": "addition",
                    "packages": ["nodejs", "npm"],
                    "release": "8.1",
                    "date": "2023-08-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "Node.js runtime and npm package manager",
                        "trainingTicket": "RHELBU-1234",
                        "dateAdded": "2025-03-10",
                        "lastModified": "2025-03-10",
                        "potentiallyAffectedSystemsCount": 1,
                        "potentiallyAffectedSystemsDetail": [
                            {
                                "id": "3796c1ce-aae4-4945-bb3d-9bbe9285a12b",
                                "display_name": "email-42.serrano.com",
                                "os_major": 8,
                                "os_minor": 1,
                            }
                        ],
                    },
                    "package": "nodejs",
                },
                {
                    "name": "Deprecate Python 2.7 in RHEL 9.4",
                    "type": "deprecation",
                    "packages": ["python27"],
                    "release": "9.4",
                    "date": "2024-05-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "Python 2.7 end of life",
                        "trainingTicket": "RHELBU-5678",
                        "dateAdded": "2025-01-15",
                        "lastModified": "2025-01-15",
                    },
                    "package": "python27",
                },
                {
                    "name": "Kernel enhancement for RHEL 10.0",
                    "type": "enhancement",
                    "packages": ["kernel"],
                    "release": "10.0",
                    "date": "2025-06-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "Improved kernel performance",
                        "trainingTicket": "RHELBU-9999",
                        "dateAdded": "2025-02-20",
                        "lastModified": "2025-02-20",
                    },
                    "package": "kernel",
                },
                {
                    "name": "Add systemd enhancement in RHEL 9.4",
                    "type": "enhancement",
                    "packages": ["systemd"],
                    "release": "9.4",
                    "date": "2024-05-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "systemd improvements",
                        "trainingTicket": "RHELBU-1111",
                        "dateAdded": "2025-01-10",
                        "lastModified": "2025-01-10",
                    },
                    "package": "systemd",
                },
                {
                    "name": "Add podman to RHEL 8.1",
                    "type": "addition",
                    "packages": ["podman"],
                    "release": "8.1",
                    "date": "2023-08-01",
                    "details": {
                        "architecture": "",
                        "detailFormat": 0,
                        "summary": "Container management tool",
                        "trainingTicket": "RHELBU-2222",
                        "dateAdded": "2025-03-05",
                        "lastModified": "2025-03-05",
                    },
                    "package": "podman",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_relevant_upcoming_changes_basic_functionality(
        self,
        planning_mcp_server,
        mock_upcoming_response,
    ):
        """Test basic functionality of get_relevant_upcoming_changes method."""
        # Patch underlying Insights client used by Planning MCP
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_upcoming_response

            # Call the method
            result = await planning_mcp_server.get_relevant_upcoming_changes()

            # Backend endpoint should be invoked exactly once with no parameters
            mock_get.assert_called_once_with("relevant/upcoming-changes", params=None, timeout=30)

            # Tool returns a JSON-encoded string; parse and validate structure
            parsed = json.loads(result)

            # Minimal but realistic structure checks
            assert "meta" in parsed
            assert "data" in parsed
            assert isinstance(parsed["data"], list)
            # The mock returns all 5 items; in production the API filters server-side
            assert parsed["meta"]["count"] == 5
            assert parsed["meta"]["total"] == 5
            assert len(parsed["data"]) == 5

            # Verify structure of first item (nodejs)
            item = parsed["data"][0]

            # Top-level fields
            assert "name" in item
            assert "type" in item
            assert "packages" in item
            assert "release" in item
            assert "date" in item
            assert "details" in item
            assert "package" in item

            # Verify it's the nodejs item
            assert item["package"] == "nodejs"
            assert item["name"] == "Add Node.js to RHEL8 AppStream"
            assert item["type"] == "addition"
            assert item["release"] == "8.1"

            # details sub-object
            details = item["details"]
            assert isinstance(details, dict)
            assert "summary" in details
            assert "dateAdded" in details
            assert "lastModified" in details
            assert "trainingTicket" in details

    @pytest.mark.asyncio
    async def test_get_relevant_upcoming_changes_with_major_version(
        self,
        planning_mcp_server,
        mock_upcoming_response,
    ):
        """Test get_relevant_upcoming_changes with major version filter."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_upcoming_response

            # Call with major version
            result = await planning_mcp_server.get_relevant_upcoming_changes(major=9)

            # Backend should receive the major parameter
            mock_get.assert_called_once_with("relevant/upcoming-changes", params={"major": 9}, timeout=30)

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_get_relevant_upcoming_changes_with_major_and_minor(
        self,
        planning_mcp_server,
        mock_upcoming_response,
    ):
        """Test get_relevant_upcoming_changes with major and minor version filters."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_upcoming_response

            # Call with both major and minor versions
            result = await planning_mcp_server.get_relevant_upcoming_changes(major=9, minor=2)

            # Backend should receive both parameters
            mock_get.assert_called_once_with("relevant/upcoming-changes", params={"major": 9, "minor": 2}, timeout=30)

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_get_relevant_upcoming_changes_minor_without_major_raises_error(
        self,
        planning_mcp_server,
    ):
        """Test that providing minor without major returns an error."""
        result = await planning_mcp_server.get_relevant_upcoming_changes(minor="2")

        # The error should be returned as a string, not raised
        assert "Error: API Error" in result
        assert "The 'minor' parameter requires 'major' to be specified" in result

    @pytest.mark.asyncio
    async def test_get_relevant_upcoming_changes_api_error(self, planning_mcp_server):
        """Test get_relevant_upcoming_changes when backend raises an API error."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.side_effect = Exception("Backend unavailable")

            result = await planning_mcp_server.get_relevant_upcoming_changes()

            # Reuse common helper to validate error formatting
            assert_api_error_result(result)
