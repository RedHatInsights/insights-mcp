"""Tests for rbac-config import and manifest provenance."""

from pathlib import Path

from insights_mcp.rbac.manifest import load_manifest_provenance
from insights_mcp.rbac.rbac_config import import_role_recommendations, parse_role_json_blobs, roles_from_blobs

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "rbac_config_excerpt.yml"


def test_parse_fixture_roles():
    """Parse embedded JSON role blobs from the rbac-config excerpt fixture."""
    yaml_text = FIXTURE_PATH.read_text(encoding="utf-8")
    blobs = parse_role_json_blobs(yaml_text)
    roles = roles_from_blobs(blobs, application_prefixes=("inventory", "vulnerability"))
    assert roles["Inventory Hosts Viewer"] == ["inventory:hosts:read"]
    assert "vulnerability:vulnerability_results:read" in roles["Vulnerability viewer"]


def test_import_role_recommendations_from_fixture():
    """Import role recommendations from fixture YAML without network."""
    yaml_text = FIXTURE_PATH.read_text(encoding="utf-8")
    roles = import_role_recommendations(yaml_text=yaml_text, application_prefixes=("inventory", "vulnerability"))
    assert "Inventory Hosts Viewer" in roles
    assert "Vulnerability viewer" in roles


def test_manifest_provenance_present():
    """Bundled manifest includes provenance with rbac_config_ref and upstream_refs."""
    provenance = load_manifest_provenance()
    assert provenance.get("rbac_config_ref")
    assert isinstance(provenance.get("upstream_refs"), dict)
