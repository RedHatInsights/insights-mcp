"""Tests for insights_mcp.cli_transport server spawn argv."""

from insights_mcp.cli_transport import resolve_server_argv


def test_resolve_server_argv_prepends_all_tools(monkeypatch):
    """LIGHTSPEED_MCP_ALL_TOOLS adds --all-tools before the transport subcommand."""
    monkeypatch.delenv("INSIGHTS_MCP_ALL_TOOLS", raising=False)
    monkeypatch.setenv("LIGHTSPEED_MCP_ALL_TOOLS", "true")
    monkeypatch.delenv("INSIGHTS_MCP_SERVER_ARGS", raising=False)
    assert resolve_server_argv() == ["--all-tools", "stdio"]


def test_resolve_server_argv_respects_explicit_readonly(monkeypatch):
    """INSIGHTS_MCP_SERVER_ARGS with --readonly is not modified."""
    monkeypatch.setenv("LIGHTSPEED_MCP_ALL_TOOLS", "true")
    monkeypatch.setenv("INSIGHTS_MCP_SERVER_ARGS", "--readonly stdio")
    assert resolve_server_argv() == ["--readonly", "stdio"]


def test_resolve_server_argv_skips_duplicate_all_tools(monkeypatch):
    """Do not prepend --all-tools when already present in INSIGHTS_MCP_SERVER_ARGS."""
    monkeypatch.setenv("INSIGHTS_MCP_ALL_TOOLS", "true")
    monkeypatch.setenv("INSIGHTS_MCP_SERVER_ARGS", "--all-tools stdio")
    assert resolve_server_argv() == ["--all-tools", "stdio"]
