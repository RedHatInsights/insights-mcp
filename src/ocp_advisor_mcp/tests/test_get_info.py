"""Test suite for the OCP Advisor get_info() tool."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from ocp_advisor_mcp.server import get_info

from .conftest import setup_ocp_advisor_mock


@pytest.mark.asyncio
async def test_get_info_calls_info_endpoint(
    ocp_advisor_mock_client: AsyncMock,
    mock_info_response: dict[str, Any],
) -> None:
    """get_info calls the /info endpoint without authentication and returns its response."""
    with setup_ocp_advisor_mock(ocp_advisor_mock_client, mock_info_response):
        result = await get_info()

    ocp_advisor_mock_client.get.assert_called_once_with("info", noauth=True)
    assert result == mock_info_response


@pytest.mark.asyncio
async def test_get_info_returns_plain_text_response(
    ocp_advisor_mock_client: AsyncMock,
) -> None:
    """get_info returns plain-text responses unchanged."""
    plain_text_response = "ok"
    with setup_ocp_advisor_mock(ocp_advisor_mock_client, plain_text_response):
        result = await get_info()

    ocp_advisor_mock_client.get.assert_called_once_with("info", noauth=True)
    assert result == plain_text_response
