"""Tests for insights_mcp.cli_catalog."""

import asyncio
from unittest.mock import patch

from fastmcp import FastMCP

from insights_mcp.cli_catalog import (
    DISABLED_WRITE_TOOLS_RESOURCE_URI,
    build_disabled_write_tools_catalog,
    catalog_help_prologue,
    catalog_pointer_message,
    is_readonly_mode,
    mcp_package_version,
    register_disabled_write_tools_resource,
)


def test_mcp_package_version_respects_env(monkeypatch):
    """mcp_package_version uses INSIGHTS_MCP_VERSION when set."""
    monkeypatch.setenv("INSIGHTS_MCP_VERSION", "20250601-abc12345")
    assert mcp_package_version() == "20250601-abc12345"


def test_is_readonly_mode_follows_all_tools_env(monkeypatch):
    """is_readonly_mode is false when LIGHTSPEED_MCP_ALL_TOOLS env is truthy."""
    monkeypatch.delenv("INSIGHTS_MCP_ALL_TOOLS", raising=False)
    monkeypatch.delenv("LIGHTSPEED_MCP_ALL_TOOLS", raising=False)
    assert is_readonly_mode() is True
    monkeypatch.setenv("LIGHTSPEED_MCP_ALL_TOOLS", "true")
    assert is_readonly_mode() is False


def test_build_disabled_write_tools_catalog_formats_toolsets():
    """Catalog includes toolset sections and rw markers."""
    rw = {"image-builder": [("image-builder__create_blueprint", "Create a blueprint")]}
    body = build_disabled_write_tools_catalog(["image-builder"], rw)
    assert "image-builder__create_blueprint" in body
    assert "**(rw)**" in body
    assert "INSIGHTS_MCP_ALL_TOOLS" in body


def test_catalog_pointer_empty_when_all_tools(monkeypatch):
    """Pointer and help prologue are empty when all-tools is enabled."""
    monkeypatch.setenv("INSIGHTS_MCP_ALL_TOOLS", "true")
    assert catalog_pointer_message() == ""
    assert catalog_help_prologue() == ""


def test_catalog_pointer_includes_resource_uri(monkeypatch):
    """Pointer references the disabled-write-tools resource URI."""
    monkeypatch.delenv("INSIGHTS_MCP_ALL_TOOLS", raising=False)
    monkeypatch.delenv("LIGHTSPEED_MCP_ALL_TOOLS", raising=False)
    message = catalog_pointer_message()
    assert DISABLED_WRITE_TOOLS_RESOURCE_URI in message


@patch("insights_mcp.cli_catalog.collect_readwrite_tools_by_toolset")
def test_register_skips_when_catalog_empty(mock_collect):
    """No resource is registered when there are no read-write tools."""
    mock_collect.return_value = {}
    server = FastMCP("test")
    register_disabled_write_tools_resource(server, ["image-builder"])
    assert asyncio.run(server.list_resources()) == []


@patch("insights_mcp.cli_catalog.collect_readwrite_tools_by_toolset")
def test_register_adds_resource_when_catalog_non_empty(mock_collect):
    """Resource is registered when read-write tools exist."""
    mock_collect.return_value = {"image-builder": [("image-builder__create_blueprint", "Create")]}
    server = FastMCP("test")
    register_disabled_write_tools_resource(server, ["image-builder"])
    resources = asyncio.run(server.list_resources())
    assert len(resources) == 1
    assert str(resources[0].uri) == DISABLED_WRITE_TOOLS_RESOURCE_URI
