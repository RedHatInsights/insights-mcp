"""Regression tests for HMS-10703: MCP CallToolResult isError on tool failures."""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

from insights_mcp.errors import InsightsApiError
from vulnerability_mcp.server import mcp as VulnerabilityMCP

HTTP_404_MESSAGE = (
    'Unexpected HTTP status code: 404, content: {"errors": [{"detail": "No such CVE ID", "status": "404"}]}'
)
AUTH_ERROR_MESSAGE = (
    "[INSTRUCTION] There seems to be a problem with the request. "
    "Without asking the user, immediately call get_insights_mcp_version() to check "
    "if we are on the latest release."
)


@pytest.fixture(name="vuln_mcp")
def vulnerability_mcp_initialized():
    """Initialize vulnerability MCP with dummy credentials for tool calls."""
    VulnerabilityMCP.init_insights_client(
        client_id="test-client-id",
        client_secret="test-client-secret",
    )
    return VulnerabilityMCP


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("side_effect", "expected_substring", "cve"),
    [
        (InsightsApiError(HTTP_404_MESSAGE), "404", "CVE-9999-9999"),
        (
            InsightsApiError(AUTH_ERROR_MESSAGE),
            "[INSTRUCTION] There seems to be a problem with the request.",
            "CVE-2024-1234",
        ),
    ],
)
async def test_tool_call_sets_is_error(vuln_mcp, side_effect, expected_substring, cve):
    """API and auth failures must surface as CallToolResult with isError=true."""
    async with Client(vuln_mcp) as client:
        with patch.object(
            vuln_mcp.insights_client,
            "get",
            new_callable=AsyncMock,
            side_effect=side_effect,
        ):
            result = await client.call_tool(
                "get_cve",
                {"cve": cve},
                raise_on_error=False,
            )

    assert result.is_error is True
    assert expected_substring in result.content[0].text
