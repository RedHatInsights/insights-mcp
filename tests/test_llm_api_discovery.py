"""Unit tests for live LLM placeholder discovery."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.llm_api_discovery import discover_workspace_name


@pytest.mark.asyncio
async def test_discover_workspace_name_uses_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INSIGHTS_TEST_WORKSPACE", "mcp_test")
    client = AsyncMock()
    assert await discover_workspace_name(client) == "mcp_test"
    client.get.assert_not_called()


@pytest.mark.asyncio
async def test_discover_workspace_name_picks_standard_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INSIGHTS_TEST_WORKSPACE", raising=False)
    client = AsyncMock()
    client.get.return_value = {
        "results": [
            {"name": "Ungrouped Hosts", "ungrouped": True},
            {"name": "mcp_test", "ungrouped": False},
        ]
    }
    assert await discover_workspace_name(client) == "mcp_test"
    client.get.assert_called_once_with("groups", params={"per_page": 20, "page": 1, "group_type": "standard"})


@pytest.mark.asyncio
async def test_discover_workspace_name_skips_ungrouped_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INSIGHTS_TEST_WORKSPACE", raising=False)
    client = AsyncMock()
    client.get.return_value = {
        "results": [{"name": "Ungrouped Hosts", "ungrouped": True}],
    }
    assert await discover_workspace_name(client) is None


@pytest.mark.asyncio
async def test_discover_workspace_name_handles_string_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INSIGHTS_TEST_WORKSPACE", raising=False)
    client = MagicMock()
    client.get = AsyncMock(return_value="502 Bad Gateway")
    assert await discover_workspace_name(client) is None
