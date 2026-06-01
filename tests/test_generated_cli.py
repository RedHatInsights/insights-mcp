"""Tests for fastmcp-generated tool CLI artifacts."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from insights_mcp.cli_shim import _generated_cli_path

REPO_ROOT = Path(__file__).resolve().parents[1]
INSIGHTS_CLI = REPO_ROOT / "generated" / "insights-mcp-cli.py"
LIGHTSPEED_CLI = REPO_ROOT / "generated" / "red-hat-lightspeed-mcp-cli.py"


@pytest.mark.skipif(not INSIGHTS_CLI.is_file(), reason="run make generate-cli-all first")
def test_generated_insights_cli_help():
    """Generated insights CLI prints help with list-tools subcommand."""
    result = subprocess.run(
        [sys.executable, str(INSIGHTS_CLI), "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    assert "insights-mcp-cli" in result.stdout
    assert "list-tools" in result.stdout


@pytest.mark.skipif(not INSIGHTS_CLI.is_file(), reason="run make generate-cli-all first")
def test_generated_insights_cli_call_tool_catalog():
    """call-tool help lists image-builder tool names."""
    result = subprocess.run(
        [sys.executable, str(INSIGHTS_CLI), "call-tool", "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    assert "image-builder__get_" in result.stdout


@pytest.mark.skipif(not INSIGHTS_CLI.is_file(), reason="run make generate-cli-all first")
def test_generated_cli_patched_client_spec():
    """Patch script wires stdio transport to insights-mcp and renames the cyclopts app."""
    text = INSIGHTS_CLI.read_text(encoding="utf-8")
    assert "INSIGHTS_MCP_SERVER_CMD" in text
    assert 'name="insights-mcp-cli"' in text
    assert "insights-mcp" in text
    assert "/home/" not in text.split("CLIENT_SPEC")[1][:200]


@pytest.mark.skipif(not LIGHTSPEED_CLI.is_file(), reason="run make generate-cli-all first")
def test_generated_lightspeed_cli_branding():
    """Lightspeed generated CLI uses red-hat-lightspeed-mcp-cli app name and brand default."""
    text = LIGHTSPEED_CLI.read_text(encoding="utf-8")
    assert 'name="red-hat-lightspeed-mcp-cli"' in text
    assert 'os.environ.get("CONTAINER_BRAND", "red-hat-lightspeed")' in text


@pytest.mark.skipif(not INSIGHTS_CLI.is_file(), reason="run make generate-cli-all first")
def test_generated_insights_cli_version_flag():
    """--version prints package version without starting the MCP server."""
    result = subprocess.run(
        [sys.executable, str(INSIGHTS_CLI), "--version"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env={**os.environ, "INSIGHTS_MCP_VERSION": "20250601-testversion"},
    )
    assert result.returncode == 0
    assert "20250601-testversion" in result.stdout


def test_cli_shim_resolves_insights_path():
    """cli_shim resolves the insights brand CLI under generated/."""
    if not INSIGHTS_CLI.is_file():
        pytest.skip("run make generate-cli-all first")
    assert _generated_cli_path("insights") == INSIGHTS_CLI


@pytest.mark.skipif(not (REPO_ROOT / "skills/insights-mcp/SKILL.md").is_file(), reason="run make generate-cli-all")
def test_openclaw_skill_frontmatter():
    """Merged OpenClaw skill includes expected name, CLI binary, and credential env vars."""
    skill = (REPO_ROOT / "skills/insights-mcp/SKILL.md").read_text(encoding="utf-8")
    assert "name: insights-mcp" in skill
    assert "insights-mcp-cli" in skill
    assert "INSIGHTS_CLIENT_ID" in skill
