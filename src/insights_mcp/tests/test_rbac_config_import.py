"""Tests for rbac-config import."""

from pathlib import Path

from insights_mcp.rbac.rbac_config import import_platform_roles, parse_role_json_blobs, roles_from_blobs

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "rbac_config_excerpt.yml"


def test_parse_fixture_roles():
    """Parse embedded JSON role blobs from the rbac-config excerpt fixture."""
    yaml_text = FIXTURE_PATH.read_text(encoding="utf-8")
    blobs = parse_role_json_blobs(yaml_text)
    roles = roles_from_blobs(blobs, application_prefixes=("inventory", "vulnerability"))
    by_name = {role.name: role for role in roles}
    assert by_name["Inventory Hosts Viewer"].permissions == frozenset({"inventory:hosts:read"})
    assert by_name["Inventory Hosts Viewer"].display_name == "Inventory Hosts viewer"
    assert "vulnerability:vulnerability_results:read" in by_name["Vulnerability viewer"].permissions


def test_import_platform_roles_from_fixture():
    """Import platform roles from fixture YAML without network."""
    yaml_text = FIXTURE_PATH.read_text(encoding="utf-8")
    roles = import_platform_roles(yaml_text=yaml_text, application_prefixes=("inventory", "vulnerability"))
    names = {role.name for role in roles}
    assert "Inventory Hosts Viewer" in names
    assert "Vulnerability viewer" in names
