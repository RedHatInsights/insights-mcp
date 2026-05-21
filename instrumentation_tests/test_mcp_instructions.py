"""Checks on MCP initialize instructions (no LLM calls)."""

import pytest

from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from instrumentation_tests.mcp_jsonrpc import (
    MCP_INSTRUCTIONS_RECOMMENDED_MAX_LEN,
    fetch_mcp_instructions_http,
)


@pytest.mark.instrumentation
def test_image_builder_initialize_instructions_within_recommended_budget():
    """MCP instructions for image-builder should fit common host truncation (2 KiB).

    Fails until server instructions are shortened; documents the target budget.
    """
    server_url, server_process = start_insights_mcp_server("http", toolset="image-builder")
    try:
        instructions = fetch_mcp_instructions_http(server_url)
        assert instructions.strip(), "expected non-empty initialize instructions"
        instruction_len = len(instructions)
        assert instruction_len <= MCP_INSTRUCTIONS_RECOMMENDED_MAX_LEN, (
            f"initialize instructions length {instruction_len} exceeds recommended maximum "
            f"{MCP_INSTRUCTIONS_RECOMMENDED_MAX_LEN} (Claude Code truncates at 2 KiB)"
        )
    finally:
        cleanup_server_process(server_process)
