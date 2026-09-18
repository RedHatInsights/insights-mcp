"""Ensure every read-only MCP tool has a rest-map entry."""

import asyncio

from insights_mcp.rbac.manifest import load_manifest
from insights_mcp.server import MCPS


def _collect_readonly_tool_names() -> list[str]:
    names: list[str] = []
    for mcp_instance in MCPS:
        try:
            mcp_instance.register_tools()
        except NotImplementedError:
            pass
        tools = asyncio.run(mcp_instance.list_tools())
        for tool in tools:
            read_only = getattr(getattr(tool, "annotations", None), "readOnlyHint", True)
            if read_only is False:
                continue
            prefixed = f"{mcp_instance.toolset_name}__{tool.name}"
            names.append(prefixed)
    return sorted(set(names))


def test_all_readonly_tools_have_rest_map_entry():
    """Every read-only MCP tool must have a row in configs/tool_rest_map.json."""
    manifest = load_manifest()
    missing = [name for name in _collect_readonly_tool_names() if name not in manifest]
    assert missing == [], f"Add rest-map entries for: {missing}"


def test_verified_entries_include_core_inventory_vulnerability():
    """Core inventory and vulnerability tools must be marked verified in the rest map."""
    manifest = load_manifest()
    assert manifest["inventory__find_host_by_name"].rest_calls[0].permissions.verified is True
    assert manifest["vulnerability__get_system_cves"].rest_calls[0].permissions.verified is True
