"""Test suite for the get_appstreams_lifecycle() Planning MCP tool."""

import json
from unittest.mock import patch

import pytest

from tests.conftest import assert_api_error_result


class TestPlanningGetAppstreamsLifecycle:
    """Test suite for the get_appstreams_lifecycle() method."""

    @pytest.fixture
    def mock_raw_response(self):
        """Mock API response for raw Application Streams lifecycle (per-major).

        Shape is aligned with the real /lifecycle/app-streams/{major_version} response.
        """
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
        """Mock API response for Application Streams overview (streams mode).

        Shape is aligned with the real /lifecycle/app-streams/streams response,
        which also returns a list of AppStreamEntity objects.
        """
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

    # -------------------------
    # Default raw mode
    # -------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_default_raw_mode(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """Default mode='raw': major is required and mapped to /lifecycle/app-streams/{major}."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            # Use default mode ("raw") and provide a major version.
            result = await planning_mcp_server.get_appstreams_lifecycle(major=10)

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/10",
                params=None,
            )

            parsed = json.loads(result)
            assert parsed == mock_raw_response
            assert "meta" in parsed
            assert "data" in parsed
            assert parsed["meta"]["count"] == 3
            assert parsed["meta"]["total"] == 3
            assert isinstance(parsed["data"], list)
            for item in parsed["data"]:
                assert "name" in item
                assert "display_name" in item
                assert "application_stream_name" in item
                assert "application_stream_type" in item
                assert "stream" in item
                assert "impl" in item
                assert "initial_product_version" in item
                assert "support_status" in item
                assert "os_major" in item
                assert "os_minor" in item
                assert "start_date" in item
                assert "end_date" in item
                assert "rolling" in item

    # ---------------------------
    # streams mode base
    # ---------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_streams_mode_basic(
        self,
        planning_mcp_server,
        mock_streams_response,
    ):
        """mode='streams': calls /lifecycle/app-streams/streams for cross-major overview."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_streams_response

            result = await planning_mcp_server.get_appstreams_lifecycle(mode="streams")

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/streams",
                params=None,
            )

            parsed = json.loads(result)
            assert parsed == mock_streams_response
            assert "meta" in parsed
            assert "data" in parsed
            assert parsed["meta"]["count"] == 2
            assert parsed["meta"]["total"] == 2
            assert isinstance(parsed["data"], list)
            for item in parsed["data"]:
                assert "name" in item
                assert "display_name" in item
                assert "application_stream_name" in item
                assert "application_stream_type" in item
                assert "stream" in item
                assert "impl" in item
                assert "os_major" in item
                assert "os_minor" in item

    # -------------------------------
    # Name filter in raw mode
    # -------------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_name_filter_raw(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """mode='raw', major=X with name filter forwards 'name' as query parameter."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            _ = await planning_mcp_server.get_appstreams_lifecycle(
                major=8,
                name="postgresql",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/8",
                params={"name": "postgresql"},
            )

    # -------------------------------------------------
    # Stream filtering with human-friendly stream
    # -------------------------------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_stream_filters_raw(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """mode='raw', stream filters forward application_stream_name and application_stream_type."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            _ = await planning_mcp_server.get_appstreams_lifecycle(
                major=9,
                application_stream_name="Node",
                application_stream_type="Application Stream",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/9",
                params={
                    "application_stream_name": "Node",
                    "application_stream_type": "Application Stream",
                },
            )

    # -----------------------------
    # Kind filter in raw mode
    # -----------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_kind_filter_raw(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """mode='raw', major=X with kind filter forwards 'kind' as query parameter."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            _ = await planning_mcp_server.get_appstreams_lifecycle(
                major=10,
                kind="package",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/10",
                params={"kind": "package"},
            )

    # ----------------------------
    # Empty result (streams)
    # ----------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_empty_streams_result(
        self,
        planning_mcp_server,
    ):
        """mode='streams' with non-matching filter should return empty data, not error."""
        empty_response = {"meta": {"count": 0, "total": 0}, "data": []}

        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = empty_response

            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="streams",
                name="aaaaaaaaaa",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/streams",
                params={"name": "aaaaaaaaaa"},
            )

            parsed = json.loads(result)
            assert parsed == empty_response
            assert parsed["meta"]["count"] == 0
            assert parsed["meta"]["total"] == 0
            assert parsed["data"] == []

    # ---------------------------------------
    # Major with streams mode ignored
    # ---------------------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_streams_ignores_major(
        self,
        planning_mcp_server,
        mock_streams_response,
    ):
        """mode='streams' should still hit streams endpoint even if major is provided."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_streams_response

            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="streams",
                major=8,
            )

            # major is intentionally not forwarded as a query parameter.
            mock_get.assert_called_once_with(
                "lifecycle/app-streams/streams",
                params=None,
            )

            parsed = json.loads(result)
            assert parsed == mock_streams_response

    # -------------------------------
    # Malformed input / 400
    # -------------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_malformed_input(
        self,
        planning_mcp_server,
    ):
        """Invalid mode or argument combinations should surface as API-style errors."""
        # Here we rely on the implementation raising a ValueError for invalid mode,
        # which is then converted into the common "Error: API Error - ..." format.
        result = await planning_mcp_server.get_appstreams_lifecycle(
            mode="0",  # invalid mode
            application_stream_name="Node",
            application_stream_type="module",
        )

        assert_api_error_result(result)

    # --------------------------------
    # Accepts major as string (common)
    # --------------------------------
    @pytest.mark.asyncio
    async def test_get_appstreams_lifecycle_accepts_string_major(
        self,
        planning_mcp_server,
        mock_raw_response,
    ):
        """Tool should accept major as a string (as many MCP clients do)."""
        with patch.object(planning_mcp_server.insights_client, "get") as mock_get:
            mock_get.return_value = mock_raw_response

            # major as string, matching typical MCP client behaviour
            result = await planning_mcp_server.get_appstreams_lifecycle(
                mode="raw",
                major="10",
            )

            mock_get.assert_called_once_with(
                "lifecycle/app-streams/10",
                params=None,
            )

            parsed = json.loads(result)
            assert parsed == mock_raw_response
