"""Tests for the planning get_appstreams_lifecycle tool."""

import json
from unittest.mock import patch

import pytest

from tests.conftest import assert_api_error_result


class TestPlanningGetAppstreamsLifecycle:
    """Integration-style tests for the planning__get_appstreams_lifecycle tool."""

    @pytest.fixture
    def mock_raw_response(self):
        """Minimal raw-mode payload, shaped like /lifecycle/app-streams/{major}."""
        return {
            "meta": {"count": 3, "total": 3},
            "data": [
                {
                    "name": "aardvark-dns",
                    "display_name": "Container Tools 1.14",
                    "application_stream_name": "container-tools",
                    "application_stream_type": "Rolling Application Stream",
                    "stream": "1.14.0",
                    "start_date": "2025-05-13",
                    "end_date": "2035-05-31",
                    "impl": "package",
                    "initial_product_version": "10.0",
                    "support_status": "Supported",
                    "os_major": 10,
                    "os_minor": 0,
                    "lifecycle": None,
                    "rolling": True,
                },
                {
                    "name": "ansible-core",
                    "display_name": "Ansible Core 2.16",
                    "application_stream_name": "Ansible Core 2.16",
                    "application_stream_type": "Full Life Application Stream",
                    "stream": "2.16.14",
                    "start_date": "2025-05-13",
                    "end_date": "2035-05-31",
                    "impl": "package",
                    "initial_product_version": "10.0",
                    "support_status": "Supported",
                    "os_major": 10,
                    "os_minor": 0,
                    "lifecycle": None,
                    "rolling": False,
                },
                {
                    "name": "aspnetcore-runtime-10.0",
                    "display_name": ".NET 10",
                    "application_stream_name": ".NET 10",
                    "application_stream_type": "Application Stream",
                    "stream": "10.0",
                    "start_date": "2025-11-01",
                    "end_date": "2028-11-14",
                    "impl": "package",
                    "initial_product_version": "10.1",
                    "support_status": "Supported",
                    "os_major": 10,
                    "os_minor": 1,
                    "lifecycle": None,
                    "rolling": False,
                },
            ],
        }

    @pytest.fixture
    def mock_streams_response(self):
        """Minimal streams-mode payload, shaped like /lifecycle/app-streams/streams."""
        return {
            "meta": {"count": 2, "total": 2},
            "data": [
                {
                    "name": "example-service",
                    "display_name": "Example Stream 1.0",
                    "application_stream_name": "Example Stream",
                    "application_stream_type": "Application Stream",
                    "stream": "1.0",
                    "start_date": "2030-01-01",
                    "end_date": "2033-12-31",
                    "impl": "package",
                    "initial_product_version": "9.1",
                    "support_status": "Supported",
                    "os_major": 9,
                    "os_minor": 1,
                    "lifecycle": None,
                    "rolling": False,
                },
                {
                    "name": "example-service",
                    "display_name": "Example Stream 2.0",
                    "application_stream_name": "Example Stream",
                    "application_stream_type": "Application Stream",
                    "stream": "2.0",
                    "start_date": "2031-06-01",
                    "end_date": "2035-12-31",
                    "impl": "package",
                    "initial_product_version": "10.0",
                    "support_status": "Supported",
                    "os_major": 10,
                    "os_minor": 0,
                    "lifecycle": None,
                    "rolling": False,
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_streams_mode_nodejs_overview(
        self,
        planning_mcp_server,
        mock_streams_response,
    ):
        """Cross-major overview: Node.js streams across RHEL 8/9/10."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_streams_response

            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="streams",
                application_stream_name="Node.js",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/streams",
                params={"application_stream_name": "Node.js"},
            )

            parsed = json.loads(result)
            assert parsed["meta"]["count"] == 2
            assert isinstance(parsed["data"], list)

    @pytest.mark.asyncio
    async def test_raw_mode_modules_for_rhel9(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """Raw mode: modules on a specific major."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="raw",
                major=9,
                kind="module",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/9",
                params={"kind": "module"},
            )

            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    @pytest.mark.asyncio
    async def test_raw_mode_postgresql_rhel8(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """Specific package on a specific major (PostgreSQL on RHEL 8)."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="raw",
                major=8,
                name="postgresql",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/8",
                params={"name": "postgresql"},
            )

            parsed = json.loads(result)
            assert "meta" in parsed
            assert "data" in parsed

    # ------------------------------------------------------------------
    # Additional behaviour / edge cases
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_default_raw_mode_with_major(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """Default mode='raw' with a major hits /lifecycle/app-streams/{major}."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            result = await planning_mcp_server.get_appstreams_lifecycle(major=10)

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/10",
                params=None,
            )

            parsed = json.loads(result)
            assert parsed["meta"]["count"] == 3

    @pytest.mark.asyncio
    async def test_streams_mode_ignores_major_param(
        self,
        planning_mcp_server,
        mock_streams_response,
    ):
        """In streams mode, major is ignored."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_streams_response

            _ = await planning_mcp_server.get_appstreams_lifecycle(
                mode="streams",
                major=8,
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/streams",
                params=None,
            )

    @pytest.mark.asyncio
    async def test_streams_mode_empty_result(
        self,
        planning_mcp_server,
    ):
        """Empty result set should not be treated as error."""
        empty_response = {"meta": {"count": 0, "total": 0}, "data": []}

        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = empty_response

            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="streams",
                name="no-such-stream",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/streams",
                params={"name": "no-such-stream"},
            )

            parsed = json.loads(result)
            assert parsed["meta"]["count"] == 0
            assert parsed["data"] == []

    @pytest.mark.asyncio
    async def test_invalid_mode_surfaces_api_error(
        self,
        planning_mcp_server,
    ):
        """Invalid mode should surface as a standard API error string."""
        result = await planning_mcp_server.get_appstreams_lifecycle(
            mode="0",
            application_stream_name="Node",
        )

        assert_api_error_result(result)

    @pytest.mark.asyncio
    async def test_accepts_string_major(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """Tool should accept major as a string, not only int."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="raw",
                major="10",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/10",
                params=None,
            )

            parsed = json.loads(result)
            assert parsed["meta"]["count"] == 3
