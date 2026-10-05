"""Test suite for the OCP Advisor get_metrics() tool."""

from unittest.mock import AsyncMock

import pytest

from ocp_advisor_mcp.server import get_metrics

from .conftest import setup_ocp_advisor_mock


class TestGetMetrics:
    """Tests for get_metrics()."""

    @pytest.mark.asyncio
    async def test_get_metrics_calls_metrics_endpoint(
        self,
        ocp_advisor_mock_client: AsyncMock,
        mock_metrics_response: str,
    ) -> None:
        """get_metrics calls the authenticated /metrics endpoint and returns its response."""
        with setup_ocp_advisor_mock(ocp_advisor_mock_client, mock_metrics_response):
            result = await get_metrics()

        ocp_advisor_mock_client.get.assert_called_once_with("metrics")
        assert result == mock_metrics_response
