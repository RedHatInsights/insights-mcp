"""Shared catalog helpers for generated tool CLIs and the MCP disabled-write-tools resource."""

from __future__ import annotations

import os

from fastmcp import FastMCP

from insights_mcp import __version__, config
from insights_mcp.mcps import MCPS
from insights_mcp.readwrite_tools import collect_readwrite_tools_by_toolset

DISABLED_WRITE_TOOLS_RESOURCE_URI = "insights-mcp://catalog/disabled-write-tools"

_ENABLE_WRITES_FOOTER = (
    "Enable write tools with `INSIGHTS_MCP_ALL_TOOLS=true` / `LIGHTSPEED_MCP_ALL_TOOLS=true` "
    "or start the MCP server with `--all-tools`."
)


def mcp_package_version() -> str:
    """Deploy/package version (respects INSIGHTS_MCP_VERSION at call time)."""
    env_version = os.environ.get("INSIGHTS_MCP_VERSION")
    if env_version:
        return env_version
    return __version__


def is_readonly_mode() -> bool:
    """True when write tools are excluded (default server/CLI behavior)."""
    return not config.all_tools_enabled()


def build_disabled_write_tools_catalog(
    allowed_mcps: list[str],
    rw_by_toolset: dict[str, list[tuple[str, str]]] | None = None,
) -> str:
    """Markdown body for the disabled-write-tools MCP resource."""
    if rw_by_toolset is None:
        rw_by_toolset = collect_readwrite_tools_by_toolset(allowed_mcps)
    display_names = {mcp.toolset_name: mcp.name for mcp in MCPS}
    sections: list[str] = [
        "# Read-write tools (not enabled in this session)",
        "",
        "These tools are available when the server runs with write access enabled. "
        "They are omitted from `list_tools` in the default read-only configuration.",
        "",
    ]
    for mcp in MCPS:
        if mcp.toolset_name not in allowed_mcps:
            continue
        rw_tools = rw_by_toolset.get(mcp.toolset_name, [])
        if not rw_tools:
            continue
        heading = display_names.get(mcp.toolset_name, mcp.toolset_name)
        sections.append(f"## {heading}")
        sections.append("")
        for name, desc in rw_tools:
            if desc:
                sections.append(f"- `{name}` **(rw)**: {desc}")
            else:
                sections.append(f"- `{name}` **(rw)**")
        sections.append("")
    sections.append(_ENABLE_WRITES_FOOTER)
    sections.append("")
    return "\n".join(sections)


def catalog_pointer_message() -> str:
    """One-line pointer for CLI help / list-tools (empty when all-tools mode)."""
    if not is_readonly_mode():
        return ""
    return (
        f"Read-only mode: write tools are disabled. "
        f"Full catalog: {DISABLED_WRITE_TOOLS_RESOURCE_URI} "
        f"(use read-resource). {_ENABLE_WRITES_FOOTER}"
    )


def catalog_help_prologue() -> str:
    """Cyclopts help_prologue text (evaluated at CLI import time)."""
    message = catalog_pointer_message()
    if not message:
        return ""
    return message + "\n\n"


def register_disabled_write_tools_resource(server: FastMCP, allowed_mcps: list[str]) -> None:
    """Register the disabled-write-tools resource when readonly and catalog is non-empty."""
    rw_by_toolset = collect_readwrite_tools_by_toolset(allowed_mcps)
    if not rw_by_toolset:
        return
    body = build_disabled_write_tools_catalog(allowed_mcps, rw_by_toolset)

    @server.resource(
        DISABLED_WRITE_TOOLS_RESOURCE_URI,
        name="disabled-write-tools",
        description="Read-write tools not enabled in this read-only server session",
        mime_type="text/markdown",
    )
    def disabled_write_tools_catalog() -> str:
        return body
