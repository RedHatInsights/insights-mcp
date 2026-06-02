"""list-tools implementation for patched fastmcp generate-cli clients."""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from insights_mcp.cli_catalog import catalog_pointer_message


async def run_list_tools(console: Any, client_spec: Any) -> None:
    """List tools from the MCP server; print catalog pointer when in read-only mode."""

    pointer = catalog_pointer_message()
    if pointer:
        console.print(f"[dim]{pointer}[/dim]\n")

    async with Client(client_spec) as client:
        tools = await client.list_tools()
        if not tools:
            console.print("[dim]No tools found.[/dim]")
            return
        for tool in tools:
            sig_parts = []
            props = tool.inputSchema.get("properties", {})
            required = set(tool.inputSchema.get("required", []))
            for pname, pschema in props.items():
                ptype = pschema.get("type", "string")
                if pname in required:
                    sig_parts.append(f"{pname}: {ptype}")
                else:
                    sig_parts.append(f"{pname}: {ptype} = ...")
            sig = f"{tool.name}({', '.join(sig_parts)})"
            console.print(f"  [cyan]{sig}[/cyan]")
            if tool.description:
                console.print(f"    {tool.description}")
            console.print()
