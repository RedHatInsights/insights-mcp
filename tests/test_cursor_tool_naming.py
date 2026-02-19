"""Test Cursor MCP tool naming constraints.

Cursor filters out tools when the combined server name and tool name exceed 60 characters.
The format is concatenation without separator: {server_name}{tool_name}.
See README Known Issues section for user-facing documentation.
"""

import asyncio

from insights_mcp.server import MCPS
from tests.conftest import TEST_CLIENT_ID, TEST_CLIENT_SECRET

# Cursor uses the mcp.json server name as prefix; one-click install uses this.
CURSOR_SERVER_NAME = "red-hat-lightspeed-mcp"
CURSOR_COMBINED_NAME_LIMIT = 60


def _collect_mounted_tool_names() -> list[tuple[str, str, int]]:
    """Collect all mounted tool names and their combined lengths.

    Uses MCPS instances: init mock client, register tools, then get tool names.
    Mount prefix is {toolset_name}_ per server.py register_mcps.
    """
    results: list[tuple[str, str, int]] = []

    for mcp in MCPS:
        toolset_name = mcp.toolset_name
        prefix = f"{toolset_name}__"

        try:
            mcp.init_insights_client(
                client_id=TEST_CLIENT_ID,
                client_secret=TEST_CLIENT_SECRET,
            )
            try:
                mcp.register_tools()
            except NotImplementedError:
                pass  # Decorator-based toolsets (e.g. remediations) register at import time
        except (ValueError, Exception):  # pylint: disable=broad-exception-caught
            continue

        try:
            tools = asyncio.run(mcp.list_tools())
        except Exception:  # pylint: disable=broad-exception-caught
            continue

        if not tools:
            continue

        for tool in tools:
            full_tool_name = f"{prefix}{tool.name}"
            combined = f"{CURSOR_SERVER_NAME}{full_tool_name}"
            results.append((toolset_name, full_tool_name, len(combined)))

    return results


def test_cursor_tool_names_exceed_limit_when_using_default_server_name() -> None:
    """Verify all tools stay under Cursor's 60-char limit with red-hat-lightspeed-mcp.

    When using the one-click install, Cursor registers the server as 'red-hat-lightspeed-mcp'.
    The combined name is {server_name}{tool_name} with no separator.
    Tools exceeding 60 chars are filtered out by Cursor. See README Known Issues.
    This test currently fails because some tools exceed the limit; fix by using a shorter
    server name in mcp.json (e.g. lightspeed-mcp).
    """
    tool_infos = _collect_mounted_tool_names()
    assert tool_infos, "Expected at least one tool from mounted toolsets"

    exceeding = [
        (toolset_name, tool_name, length)
        for toolset_name, tool_name, length in tool_infos
        if length > CURSOR_COMBINED_NAME_LIMIT
    ]

    assert not exceeding, (
        f"All tools must be <= {CURSOR_COMBINED_NAME_LIMIT} chars when server name is '{CURSOR_SERVER_NAME}'. "
        f"{len(exceeding)} tools exceeding limit: {exceeding}"
    )
