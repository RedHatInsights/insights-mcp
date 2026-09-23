"""Tests for README RBAC snippet generation."""

from pathlib import Path

from generate_rbac_docs import (
    perms_by_toolset,
    render_readme_block,
    replace_marker_block,
    roles_by_toolset,
)

from insights_mcp.rbac.catalog import catalog_from_rbac_config_yaml

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "rbac_config_excerpt.yml"


def test_generated_readme_block_uses_display_names():
    """Generator emits console display names from rbac-config, not permission strings."""
    catalog = catalog_from_rbac_config_yaml(FIXTURE_PATH.read_text(encoding="utf-8"))
    toolsets = roles_by_toolset(catalog)
    assert toolsets["advisor"] == ["RHEL Advisor viewer", "Inventory Hosts viewer"]
    assert "Workspace viewer" in toolsets["inventory"]
    assert "Inventory Hosts viewer" in toolsets["inventory"]
    assert toolsets["vulnerability"] == ["Vulnerability viewer", "Inventory Hosts viewer"]
    assert toolsets["remediations"] == ["Remediations user"]
    block = render_readme_block(toolsets)
    assert "RHEL Advisor viewer" in block
    assert "advisor:*:read" not in block
    assert "BEGIN GENERATED RBAC ROLES" in block


def test_replace_marker_block():
    """Marker replacement keeps surrounding text."""
    original = "before\n<!-- BEGIN X -->\nold\n<!-- END X -->\nafter\n"
    replacement = "<!-- BEGIN X -->\nnew\n<!-- END X -->"
    updated = replace_marker_block(original, "<!-- BEGIN X -->", "<!-- END X -->", replacement)
    assert updated == "before\n<!-- BEGIN X -->\nnew\n<!-- END X -->\nafter\n"


def test_perms_by_toolset_includes_groups():
    """Inventory toolset union includes hosts and groups permissions."""
    perms = perms_by_toolset()
    assert "inventory:hosts:read" in perms["inventory"]
    assert "inventory:groups:read" in perms["inventory"]
