"""Discovery of read-write MCP tools for catalogs and server instructions."""

from typing import Any

from insights_mcp.async_utils import run_async
from insights_mcp.mcp import InsightsMCP
from insights_mcp.mcps import MCPS


def _get_tool_description(tool: Any) -> str:
    """Extract first line of description or title for a tool."""
    desc = getattr(tool, "description", None) or ""
    title = getattr(tool, "title", None) or ""
    text = (desc or title).strip()
    if not text:
        return ""
    first_line = text.split("\n", 1)[0].strip()
    if len(first_line) > 100:
        last_space = first_line.rfind(" ", 80, 99)
        first_line = first_line[: last_space + 1 if last_space != -1 else 99] + "…"
    return first_line


def collect_readwrite_tools_by_toolset(allowed_mcps: list[str]) -> dict[str, list[tuple[str, str]]]:
    """Collect read-write tools from a temporary InsightsMCP container.

    Mounts all allowed MCPS (shared for decorator-based, temp for register_tools-based),
    then filters for readOnlyHint is False and groups by toolset.
    """
    temp_root = InsightsMCP(name="temp", toolset_name="temp", api_path="")
    for mcp in MCPS:
        if mcp.toolset_name not in allowed_mcps:
            continue
        try:
            temp_sub = type(mcp)()  # type: ignore[call-arg]
            temp_sub.register_tools()
            temp_root.mount(temp_sub, namespace=mcp.toolset_name)
        except (NotImplementedError, TypeError):
            temp_root.mount(mcp, namespace=mcp.toolset_name)

    tools = run_async(temp_root.list_tools())
    rw_by_toolset: dict[str, list[tuple[str, str]]] = {}
    for tool in tools:
        if getattr(getattr(tool, "annotations", None), "readOnlyHint", True) is False:
            name = getattr(tool, "name", "")
            if "_" in name:
                toolset_name = name.split("_", 1)[0]
                if toolset_name not in rw_by_toolset:
                    rw_by_toolset[toolset_name] = []
                desc = _get_tool_description(tool)
                rw_by_toolset[toolset_name].append((name, desc))
    for toolset_name in rw_by_toolset:
        rw_by_toolset[toolset_name] = sorted(rw_by_toolset[toolset_name], key=lambda x: x[0])
    return rw_by_toolset
