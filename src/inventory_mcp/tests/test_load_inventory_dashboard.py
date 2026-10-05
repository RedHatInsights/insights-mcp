"""Tests for load_inventory_dashboard MCP Apps fallback vs UI query payload."""

from typing import Any

import pytest
from fastmcp.apps import UI_EXTENSION_ID

from inventory_mcp.server import load_inventory_dashboard
from tests.mcp_apps_test_support import mcp_apps_context, tool_result_text

from .conftest import inventory_host_filter_kwargs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("ui_supported", "overrides"),
    [
        (False, {}),
        (True, {"workspace_name": "mcp_test", "per_page": 5}),
    ],
    ids=["fallback_without_mcp_apps", "ui_query_with_workspace"],
)
async def test_load_inventory_dashboard_query(ui_supported: bool, overrides: dict[str, Any]) -> None:
    ctx = mcp_apps_context(ui_supported=ui_supported)
    kwargs = inventory_host_filter_kwargs(**overrides)
    result = await load_inventory_dashboard(ctx, **kwargs)

    ctx.client_supports_extension.assert_called_once_with(UI_EXTENSION_ID)
    if not ui_supported:
        text = tool_result_text(result)
        assert "Client does not support MCP Apps" in text
        assert "list_hosts" in text
        assert result.structured_content is None
        return

    assert "Inventory Dashboard opened" in tool_result_text(result)
    assert result.structured_content == {"query": kwargs}
