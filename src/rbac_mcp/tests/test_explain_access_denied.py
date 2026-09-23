"""Tests for rbac explain_access_denied tool."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from insights_mcp.rbac.catalog import catalog_from_rbac_config_yaml
from rbac_mcp.server import explain_access_denied, lookup_tool_requirements

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "rbac_config_excerpt.yml"


def _catalog():
    return catalog_from_rbac_config_yaml(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_explain_access_denied_returns_missing_roles_only():
    """explain_access_denied returns missing role display names without permission dumps."""
    mock_access = {
        "data": [
            {"permission": "vulnerability:vulnerability_results:read", "resourceDefinitions": []},
        ],
        "permissions": ["vulnerability:vulnerability_results:read"],
    }
    with patch("rbac_mcp.server.fetch_caller_access", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_access
        with patch("rbac_mcp.server.get_access_token_from_client", return_value=None):
            with patch(
                "insights_mcp.rbac.diagnose.load_role_catalog",
                new_callable=AsyncMock,
                return_value=_catalog(),
            ):
                result = await explain_access_denied(
                    failed_tool="vulnerability__get_system_cves",
                    failed_url=(
                        "https://console.redhat.com/api/vulnerability/v1/systems/"
                        "00000000-0000-0000-0000-000000000001/cves"
                    ),
                    http_status=403,
                    failed_method="GET",
                )

    assert result["do_not_infer_other_permissions"] is True
    assert result["missing_roles"] == ["Inventory Hosts viewer"]
    assert "missing_permissions" not in result
    assert "rest_calls" not in result


@pytest.mark.asyncio
async def test_lookup_tool_requirements_required_roles_only():
    """lookup_tool_requirements returns required_roles without permission dumps."""
    with patch(
        "rbac_mcp.server.load_role_catalog",
        new_callable=AsyncMock,
        return_value=_catalog(),
    ):
        result = await lookup_tool_requirements(tool_name="advisor__get_active_rules")

    assert result["do_not_infer_other_permissions"] is True
    assert result["required_roles"] == ["RHEL Advisor viewer"]
    assert "v1_permission_sets" not in result
    assert "recommended_roles" not in result
