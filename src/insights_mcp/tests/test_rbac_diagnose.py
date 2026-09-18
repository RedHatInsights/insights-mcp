"""Unit tests for RBAC rest map and diagnose logic."""

from pathlib import Path

from insights_mcp.rbac.catalog import catalog_from_rbac_config_yaml
from insights_mcp.rbac.diagnose import (
    AccessDeniedCall,
    AccessDeniedInput,
    build_access_denied_report,
    compare_permissions,
    permission_set_satisfied,
    required_roles_for_entry,
)
from insights_mcp.rbac.manifest import find_tool_by_rest_url, get_tool_entry, load_manifest, resolve_tool_name

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "rbac_config_excerpt.yml"


def _catalog():
    return catalog_from_rbac_config_yaml(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_manifest_loads_vulnerability_get_system_cves():
    """Rest-map entry for get_system_cves lists verified vulnerability and inventory perms."""
    entry = get_tool_entry("vulnerability__get_system_cves")
    assert entry is not None
    assert entry.rest_calls[0].permissions.verified is True
    flat = entry.all_required_v1_flat()
    assert "vulnerability:vulnerability_results:read" in flat
    assert "inventory:hosts:read" in flat
    assert "vulnerability:system.cves:read" not in flat


def test_permission_set_satisfied_and_missing():
    """Compare held permissions against required sets and report missing inventory read."""
    entry = get_tool_entry("vulnerability__get_system_cves")
    assert entry is not None
    held = ["vulnerability:vulnerability_results:read"]
    comparison = compare_permissions(entry.rest_calls[0], held)
    assert comparison["satisfied"] is False
    assert "inventory:hosts:read" in comparison["missing_permissions"]

    held_both = [
        "vulnerability:vulnerability_results:read",
        "inventory:hosts:read",
    ]
    comparison_ok = compare_permissions(entry.rest_calls[0], held_both)
    assert comparison_ok["satisfied"] is True
    assert comparison_ok["missing_permissions"] == []


def test_permission_set_satisfied_wildcard():
    """Wildcard permissions satisfy specific required permission strings."""
    assert permission_set_satisfied(("inventory:hosts:read",), {"inventory:*:read"})
    assert permission_set_satisfied(("advisor:recommendation:read",), {"advisor:*:read"})


def test_find_tool_by_rest_url():
    """Match rest-map entry from a failed vulnerability systems/cves URL."""
    entry = find_tool_by_rest_url(
        "https://console.redhat.com/api/vulnerability/v1/systems/1cd6ee42-0276-4f74-8b68-0f15fe2090f7/cves?sort=-cvss",
        method="GET",
    )
    assert entry is not None
    assert entry.tool_name == "vulnerability__get_system_cves"


def test_resolve_tool_name_alias():
    """Single-underscore tool aliases resolve to toolset__function rest-map keys."""
    assert (
        resolve_tool_name(
            "vulnerability_get_system_cves",
            "",
        )
        == "vulnerability__get_system_cves"
    )


def test_build_access_denied_report_missing_role_names_only():
    """403 report lists missing console display names and no permission strings."""
    entry = get_tool_entry("vulnerability__get_system_cves")
    assert entry is not None
    report = build_access_denied_report(
        AccessDeniedInput(
            call=AccessDeniedCall(
                failed_tool="vulnerability__get_system_cves",
                failed_url=(
                    "https://console.redhat.com/api/vulnerability/v1/systems/00000000-0000-0000-0000-000000000001/cves"
                ),
                http_status=403,
                failed_method="GET",
            ),
            entry=entry,
            access_payload={
                "data": [{"permission": "vulnerability:vulnerability_results:read", "resourceDefinitions": []}]
            },
            access_token=None,
            role_catalog=_catalog(),
        )
    )
    assert report["do_not_infer_other_permissions"] is True
    assert report["missing_roles"] == ["Inventory Hosts viewer"]
    assert "missing_permissions" not in report
    assert "v1_permission_sets" not in report
    assert "recommended_roles" not in report


def test_build_access_denied_report_empty_when_held():
    """When the caller already has required perms, missing_roles is empty with a scoping note."""
    entry = get_tool_entry("inventory__find_host_by_name")
    assert entry is not None
    report = build_access_denied_report(
        AccessDeniedInput(
            call=AccessDeniedCall(
                failed_tool="inventory__find_host_by_name",
                failed_url="https://console.redhat.com/api/inventory/v1/hosts?hostname_or_id=foo",
                http_status=403,
                failed_method="GET",
            ),
            entry=entry,
            access_payload={"data": [{"permission": "inventory:hosts:read", "resourceDefinitions": []}]},
            access_token=None,
            role_catalog=_catalog(),
        )
    )
    assert report["missing_roles"] == []  # pylint: disable=use-implicit-booleaness-not-comparison
    assert "workspace scoping" in report["note"]


def test_required_roles_for_advisor_get_active_rules():
    """lookup mapping for advisor rules uses RHEL Advisor viewer display_name."""
    entry = get_tool_entry("advisor__get_active_rules")
    assert entry is not None
    roles, unknown = required_roles_for_entry(entry, (), _catalog())
    assert unknown is False
    assert roles == ["RHEL Advisor viewer"]


def test_manifest_has_workspace_tools():
    """Rest map includes inventory workspace/groups endpoints."""
    manifest = load_manifest()
    assert "inventory__list_workspaces" in manifest
    assert "inventory__get_workspace" in manifest
    assert "inventory__list_workspace_hosts" in manifest
    groups = get_tool_entry("inventory__list_workspaces")
    assert groups is not None
    assert "inventory:groups:read" in groups.all_required_v1_flat()
