"""Tests for packaged tool REST map loading."""

import json

from insights_mcp.rbac.data_files import load_tool_rest_map, tool_rest_map_path
from insights_mcp.rbac.manifest import load_manifest


def test_packaged_rest_map_loads_without_env_override(monkeypatch):
    """Installed packages must load tool_rest_map.json from package data, not repo configs."""
    monkeypatch.delenv("INSIGHTS_MCP_TOOL_REST_MAP", raising=False)
    load_tool_rest_map.cache_clear()
    load_manifest.cache_clear()
    assert tool_rest_map_path() is None
    data = load_tool_rest_map()
    assert "tools" in data
    assert "inventory__list_hosts" in data["tools"]
    load_tool_rest_map.cache_clear()
    load_manifest.cache_clear()


def test_env_override_rest_map(monkeypatch, tmp_path):
    """INSIGHTS_MCP_TOOL_REST_MAP replaces the packaged map."""
    override = tmp_path / "tool_rest_map.json"
    override.write_text(
        json.dumps({"templates": {}, "tools": {"inventory__list_hosts": []}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("INSIGHTS_MCP_TOOL_REST_MAP", str(override))
    load_tool_rest_map.cache_clear()
    load_manifest.cache_clear()
    data = load_tool_rest_map()
    assert data["tools"] == {"inventory__list_hosts": []}
    load_tool_rest_map.cache_clear()
    load_manifest.cache_clear()
    monkeypatch.delenv("INSIGHTS_MCP_TOOL_REST_MAP", raising=False)
