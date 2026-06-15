"""Collect MCP tool metadata for Compass catalog-info.yaml generation."""

from __future__ import annotations

import asyncio
from string import Template

from fastmcp.tools import Tool

from insights_mcp.mcp import InsightsMCP
from insights_mcp.toolsets import MCPS

_DESCRIPTION_MAX_LENGTH = 100


def catalog_tool_description(tool: Tool, *, brand_long: str | None = None) -> str:
    """Extract a short catalog description from an MCP tool.

    Uses ``tool.title`` when set by the toolset, otherwise the first line of
    ``tool.description``. When ``brand_long`` is provided, ``$container_brand_long``
    placeholders are substituted.

    Args:
        tool: MCP tool with title and/or description from toolset registration.
        brand_long: Optional long brand name for template substitution.

    Returns:
        A single-line description suitable for catalog ``spec.primitives``.
    """
    text = (tool.title or tool.description or "").strip()
    first_line = text.split("\n", 1)[0].strip()
    if brand_long is not None:
        first_line = Template(first_line).safe_substitute(container_brand_long=brand_long)
    return _truncate_description(first_line)


def _truncate_description(first_line: str) -> str:
    """Truncate long descriptions at a word boundary."""
    if len(first_line) <= _DESCRIPTION_MAX_LENGTH:
        return first_line
    last_space = first_line.rfind(" ", 80, 99)
    truncate_at = last_space + 1 if last_space != -1 else 99
    return first_line[:truncate_at] + "…"


def _list_mounted_tools() -> list[Tool]:
    """Register, mount, and list tools using the same naming as InsightsMCPServer."""
    temp_root = InsightsMCP(name="temp", toolset_name="temp", api_path="")
    for mcp in MCPS:
        try:
            temp_sub = type(mcp)()  # type: ignore[call-arg]
            temp_sub.register_tools()
            temp_root.mount(temp_sub, prefix=f"{mcp.toolset_name}_")
        except (NotImplementedError, TypeError, ValueError):
            temp_root.mount(mcp, prefix=f"{mcp.toolset_name}_")

    return list(asyncio.run(temp_root.list_tools()))


def collect_tool_primitives(*, brand_long: str = "Red Hat Lightspeed") -> list[dict[str, str]]:
    """Collect tool primitives from all registered MCP toolsets.

    Compass ``spec.primitives`` entries only support ``type``, ``name``, and
    ``description`` — there is no separate toolset/group field. Toolset context
    is encoded in ``name`` only (e.g. ``planning__get_upcoming_changes``).

    Args:
        brand_long: Brand name substituted for ``$container_brand_long`` in descriptions.

    Returns:
        Sorted list of primitive dicts with ``type``, ``name``, and ``description`` keys.
    """
    return [
        {
            "type": "tool",
            "name": tool.name,
            "description": catalog_tool_description(tool, brand_long=brand_long),
        }
        for tool in sorted(_list_mounted_tools(), key=lambda tool_item: tool_item.name)
    ]
