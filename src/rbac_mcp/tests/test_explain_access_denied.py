"""Tests for rbac explain_access_denied tool."""

from unittest.mock import AsyncMock, patch

import pytest

from rbac_mcp.server import explain_access_denied


@pytest.mark.asyncio
async def test_explain_access_denied_returns_structured_report():
    """explain_access_denied returns structured JSON with missing permissions when held set is incomplete."""
    mock_access = {
        "data": [
            {"permission": "vulnerability:vulnerability_results:read", "resourceDefinitions": []},
        ],
        "permissions": ["vulnerability:vulnerability_results:read"],
    }
    with patch("rbac_mcp.server.fetch_caller_access", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_access
        with patch("rbac_mcp.server.get_access_token_from_client", return_value=None):
            result = await explain_access_denied(
                failed_tool="vulnerability__get_system_cves",
                failed_url=(
                    "https://console.redhat.com/api/vulnerability/v1/systems/00000000-0000-0000-0000-000000000001/cves"
                ),
                http_status=403,
            )

    assert result["do_not_infer_other_permissions"] is True
    assert result["failed"]["tool"] == "vulnerability__get_system_cves"
    assert "vulnerability:vulnerability_results:read" in str(result["required_permissions"])
    assert "inventory:hosts:read" in result["missing_permissions"]
