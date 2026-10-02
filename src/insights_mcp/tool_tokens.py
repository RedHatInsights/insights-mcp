"""Measure input tokens consumed by MCP tool definitions sent to function-calling LLMs."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

import tiktoken
from llama_index.core.tools import BaseTool
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from insights_mcp.server import MCPS

logger = logging.getLogger(__name__)

DEFAULT_TIKTOKEN_ENCODING = "cl100k_base"
ALL_TOOLS_LABEL = "all-tools"


@dataclass(frozen=True)
class ToolCatalogMode:
    """Server configuration for one row in the tool token table."""

    label: str
    toolset: str | None
    readonly: bool


@dataclass(frozen=True)
class ToolCatalogRow:
    """Measured tool catalog for one mode."""

    label: str
    tool_count: int
    token_count: int


def fetch_mcp_tools(
    transport: str = "stdio",
    toolset: str | None = None,
    readonly: bool = False,
    container_brand: str | None = None,
) -> List[BaseTool]:
    """Load MCP tools via a subprocess server and LlamaIndex McpToolSpec."""
    server_url, server_process = start_insights_mcp_server(
        transport,
        toolset=toolset,
        readonly=readonly,
        container_brand=container_brand,
    )

    try:
        if server_url == "stdio":
            args = ["-m", "insights_mcp.server"]
            if toolset is not None:
                args.extend(["--toolset", toolset])
            if not readonly:
                args.append("--all-tools")
            args.append("stdio")
            client = BasicMCPClient("python", args=args)
        else:
            client = BasicMCPClient(server_url)

        tool_spec = McpToolSpec(client=client)

        async def _fetch() -> List[BaseTool]:
            return await tool_spec.to_tool_list_async()

        return asyncio.run(_fetch())

    finally:
        cleanup_server_process(server_process)


def tools_to_openai_specs(tools: Sequence[BaseTool]) -> List[Dict[str, Any]]:
    """Serialize tools the same way OpenAI function-calling chat does."""
    return [tool.metadata.to_openai_tool(skip_length_check=True) for tool in tools]


def count_tool_input_tokens(tools: Sequence[BaseTool], encoding: tiktoken.Encoding) -> int:
    """Count tokens in the JSON-encoded OpenAI tools payload."""
    specs = tools_to_openai_specs(tools)
    payload = json.dumps(specs, separators=(",", ":"))
    return len(encoding.encode(payload))


def resolve_encoding(
    model_id: str,
    llm_config: Optional[Mapping[str, str]] = None,
) -> tiktoken.Encoding:
    """Resolve a tiktoken encoding for the given model or config overrides."""
    if llm_config:
        tiktoken_name = llm_config.get("TIKTOKEN_ENCODING")
        if tiktoken_name:
            return tiktoken.get_encoding(tiktoken_name)

    try:
        return tiktoken.encoding_for_model(model_id)
    except KeyError:
        logger.warning(
            "No tiktoken mapping for model %r; using %s (approximate for non-OpenAI models)",
            model_id,
            DEFAULT_TIKTOKEN_ENCODING,
        )
        return tiktoken.get_encoding(DEFAULT_TIKTOKEN_ENCODING)


def all_tools_mode() -> ToolCatalogMode:
    """Catalog mode for all toolsets with write tools enabled."""
    return ToolCatalogMode(label=ALL_TOOLS_LABEL, toolset=None, readonly=False)


def default_catalog_modes() -> List[ToolCatalogMode]:
    """All-tools row plus one row per registered toolset (each with --all-tools)."""
    modes = [all_tools_mode()]
    for toolset_name in sorted(mcp.toolset_name for mcp in MCPS):
        modes.append(ToolCatalogMode(label=toolset_name, toolset=toolset_name, readonly=False))
    return modes


def sort_rows_for_table(rows: Sequence[ToolCatalogRow]) -> List[ToolCatalogRow]:
    """Keep all-tools first; sort remaining rows alphabetically by label."""
    head = [row for row in rows if row.label == ALL_TOOLS_LABEL]
    tail = sorted((row for row in rows if row.label != ALL_TOOLS_LABEL), key=lambda row: row.label)
    return head + tail


def build_catalog_rows(
    modes: Sequence[ToolCatalogMode],
    encoding: tiktoken.Encoding,
    transport: str = "stdio",
) -> List[ToolCatalogRow]:
    """Fetch tools and count input tokens for each catalog mode."""
    rows: List[ToolCatalogRow] = []
    for mode in modes:
        tools = fetch_mcp_tools(transport=transport, toolset=mode.toolset, readonly=mode.readonly)
        rows.append(
            ToolCatalogRow(
                label=mode.label,
                tool_count=len(tools),
                token_count=count_tool_input_tokens(tools, encoding),
            )
        )
    return rows


def format_markdown_table(rows: Sequence[ToolCatalogRow], *, encoding_name: str) -> str:
    """Format catalog rows as a markdown document with a table."""
    lines = [
        "# MCP tool input tokens",
        "",
        f"Encoding: `{encoding_name}`",
        "",
        "Counts cover the OpenAI-style `tools` payload only (names, descriptions, schemas).",
        "Every row uses `--all-tools` (maximum tools per mode).",
        "",
        "| Mode | Tools | Input tokens |",
        "|------|------:|-------------:|",
    ]
    for row in sort_rows_for_table(rows):
        lines.append(f"| {row.label} | {row.tool_count} | {row.token_count} |")
    lines.append("")
    return "\n".join(lines)
