"""Test suite for the get_relevant_rhel_lifecycle() method."""
# pylint: disable=duplicate-code

import json
from unittest.mock import patch

import pytest

from tests.conftest import (
    assert_api_error_result,
)


class TestPlanningGetRelevantRhelLifecycle:
    """Test suite for the get_relevant_rhel_lifecycle() method."""

    @pytest.fixture
    def mock_lifecycle_response(self):
        """Mock API response for relevant RHEL lifecycle (schema aligned, data anonymized)."""
        return {
            "meta": {
                "count": 3,
                "total": 3,
            },
            "data": [
                {
                    "name": "RHEL",
                    "display_name": "RHEL 9.0",
                    "major": 9,
                    "minor": 0,
                    "start_date": "2022-05-17",
                    "end_date": "2027-05-31",
                    "support_status": "Supported",
                    "count": 2,
                    "lifecycle_type": "mainline",
                    "related": False,
                    "systems_detail": [
                        {
                            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                            "display_name": "server-01.example.com",
                            "os_major": 9,
                            "os_minor": 0,
                        },
                        {
                            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "display_name": "server-02.example.com",
                            "os_major": 9,
                            "os_minor": 0,
                        },
                    ],
                    "systems": [
                        "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    ],
                },
                {
                    "name": "RHEL",
                    "display_name": "RHEL 8.8",
                    "major": 8,
                    "minor": 8,
                    "start_date": "2023-05-16",
                    "end_date": "2026-05-31",
                    "support_status": "Supported",
                    "count": 1,
                    "lifecycle_type": "eus",
                    "related": False,
                    "systems_detail": [
                        {
                            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                            "display_name": "db-server.example.com",
                            "os_major": 8,
                            "os_minor": 8,
                        }
                    ],
                    "systems": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"],
                },
                {
                    "name": "RHEL",
                    "display_name": "RHEL 9.4",
                    "major": 9,
                    "minor": 4,
                    "start_date": "2024-04-30",
                    "end_date": "2026-04-30",
                    "support_status": "Supported",
                    "count": 0,
                    "lifecycle_type": "mainline",
                    "related": True,
                    "systems_detail": [],
                    "systems": [],
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_get_relevant_rhel_lifecycle_basic_functionality(
        self,
        planning_mcp_server,
        mock_lifecycle_response,
    ):
        """Test basic functionality of get_relevant_rhel_lifecycle method."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_lifecycle_response

            # Call the method with no parameters (defaults: include_related="false")
            result = await planning_mcp_server.get_relevant_rhel_lifecycle()

            # Backend endpoint should be invoked with related=False by default
            mock_get.assert_called_once_with(
                "relevant/lifecycle/rhel",
                params={"related": False},
                timeout=30,
            )

            # Tool returns a JSON-encoded string; parse and validate structure
            parsed = json.loads(result)

            # Validate meta section
            assert "meta" in parsed
            assert "count" in parsed["meta"]
            assert "total" in parsed["meta"]
            assert parsed["meta"]["count"] == 3
            assert parsed["meta"]["total"] == 3

            # Validate data section
            assert "data" in parsed
            assert isinstance(parsed["data"], list)
            assert len(parsed["data"]) == 3

            # Verify structure of first item
            item = parsed["data"][0]

            # Top-level fields per schema
            assert "name" in item
            assert "display_name" in item
            assert "major" in item
            assert "minor" in item
            assert "start_date" in item
            assert "end_date" in item
            assert "support_status" in item
            assert "count" in item
            assert "lifecycle_type" in item
            assert "related" in item
            assert "systems_detail" in item
            assert "systems" in item

            # Verify values of first item
            assert item["name"] == "RHEL"
            assert item["display_name"] == "RHEL 9.0"
            assert item["major"] == 9
            assert item["minor"] == 0
            assert item["lifecycle_type"] == "mainline"
            assert item["related"] is False

            # Verify systems_detail structure
            assert isinstance(item["systems_detail"], list)
            if item["systems_detail"]:
                system = item["systems_detail"][0]
                assert "id" in system
                assert "display_name" in system
                assert "os_major" in system
                assert "os_minor" in system

    @pytest.mark.asyncio
    async def test_get_relevant_rhel_lifecycle_with_major_version(
        self,
        planning_mcp_server,
        mock_lifecycle_response,
    ):
        """Test get_relevant_rhel_lifecycle with major version filter."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_lifecycle_response

            # Call with major version
            result = await planning_mcp_server.get_relevant_rhel_lifecycle(major="9")

            # Backend should receive the major parameter and related=False
            mock_get.assert_called_once_with(
                "relevant/lifecycle/rhel",
                params={"major": 9, "related": False},
                timeout=30,
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_get_relevant_rhel_lifecycle_with_major_and_minor(
        self,
        planning_mcp_server,
        mock_lifecycle_response,
    ):
        """Test get_relevant_rhel_lifecycle with major and minor version filters."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_lifecycle_response

            # Call with both major and minor versions
            result = await planning_mcp_server.get_relevant_rhel_lifecycle(major="9", minor="2")

            # Backend should receive both parameters and related=False
            mock_get.assert_called_once_with(
                "relevant/lifecycle/rhel",
                params={"major": 9, "minor": 2, "related": False},
                timeout=30,
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.parametrize("include_related", (True, False))
    @pytest.mark.asyncio
    async def test_get_relevant_rhel_lifecycle_with_include_related(
        self, planning_mcp_server, mock_lifecycle_response, include_related
    ):
        """Test get_relevant_rhel_lifecycle with include_related explicitly set"""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_lifecycle_response

            result = await planning_mcp_server.get_relevant_rhel_lifecycle(include_related=str(include_related))

            mock_get.assert_called_once_with(
                "relevant/lifecycle/rhel",
                params={"related": include_related},
                timeout=30,
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_get_relevant_rhel_lifecycle_with_all_parameters(
        self,
        planning_mcp_server,
        mock_lifecycle_response,
    ):
        """Test get_relevant_rhel_lifecycle with major, minor, and include_related."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_lifecycle_response

            # Call with all parameters
            result = await planning_mcp_server.get_relevant_rhel_lifecycle(
                major="9",
                minor="4",
                include_related="true",
            )

            # Backend should receive all parameters
            mock_get.assert_called_once_with(
                "relevant/lifecycle/rhel",
                params={"major": 9, "minor": 4, "related": True},
                timeout=30,
            )

            # Validate response structure
            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_get_relevant_rhel_lifecycle_minor_without_major_raises_error(
        self,
        planning_mcp_server,
    ):
        """Test that providing minor without major returns an error."""
        result = await planning_mcp_server.get_relevant_rhel_lifecycle(minor="2")

        # The error should be returned as a string, not raised
        assert "Error: API Error" in result
        assert "The 'minor' parameter requires 'major' to be specified" in result

    @pytest.mark.asyncio
    async def test_get_relevant_rhel_lifecycle_api_error(self, planning_mcp_server):
        """Test get_relevant_rhel_lifecycle when backend raises an API error."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.side_effect = Exception("Backend unavailable")

            result = await planning_mcp_server.get_relevant_rhel_lifecycle()

            # Reuse common helper to validate error formatting
            assert_api_error_result(result)
