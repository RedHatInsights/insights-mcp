"""Unit tests for RBAC manifest and diagnose logic."""

from insights_mcp.rbac.diagnose import (
    AccessDeniedCall,
    AccessDeniedInput,
    build_access_denied_report,
    compare_permissions,
    permission_set_satisfied,
)
from insights_mcp.rbac.manifest import find_tool_by_rest_url, get_tool_entry, load_manifest, resolve_tool_name


def test_manifest_loads_vulnerability_get_system_cves():
    """Manifest entry for get_system_cves lists verified vulnerability and inventory perms."""
    entry = get_tool_entry("vulnerability__get_system_cves")
    assert entry is not None
    assert entry.permissions.verified is True
    flat = entry.all_required_v1_flat()
    assert "vulnerability:vulnerability_results:read" in flat
    assert "inventory:hosts:read" in flat
    assert "vulnerability:system.cves:read" not in flat


def test_permission_set_satisfied_and_missing():
    """Compare held permissions against required sets and report missing inventory read."""
    entry = get_tool_entry("vulnerability__get_system_cves")
    assert entry is not None
    held = ["vulnerability:vulnerability_results:read"]
    comparison = compare_permissions(entry, held)
    assert comparison["satisfied"] is False
    assert "inventory:hosts:read" in comparison["missing_permissions"]

    held_both = [
        "vulnerability:vulnerability_results:read",
        "inventory:hosts:read",
    ]
    comparison_ok = compare_permissions(entry, held_both)
    assert comparison_ok["satisfied"] is True
    assert comparison_ok["missing_permissions"] == []


def test_permission_set_satisfied_wildcard():
    """Wildcard permissions satisfy specific required permission strings."""
    assert permission_set_satisfied(("inventory:hosts:read",), {"inventory:*:read"})
    assert permission_set_satisfied(("advisor:recommendation:read",), {"advisor:*:read"})


def test_find_tool_by_rest_url():
    """Match manifest entry from a failed vulnerability systems/cves URL."""
    entry = find_tool_by_rest_url(
        "https://console.redhat.com/api/vulnerability/v1/systems/1cd6ee42-0276-4f74-8b68-0f15fe2090f7/cves?sort=-cvss",
        method="GET",
    )
    assert entry is not None
    assert entry.tool_name == "vulnerability__get_system_cves"


def test_resolve_tool_name_alias():
    """Single-underscore tool aliases resolve to toolset__function manifest keys."""
    assert (
        resolve_tool_name(
            "vulnerability_get_system_cves",
            "",
        )
        == "vulnerability__get_system_cves"
    )


def test_build_access_denied_report_structure():
    """403 report includes comparison, caller permissions, and anti-hallucination flag."""
    entry = get_tool_entry("inventory__find_host_by_name")
    assert entry is not None
    report = build_access_denied_report(
        AccessDeniedInput(
            call=AccessDeniedCall(
                failed_tool="inventory__find_host_by_name",
                failed_url="https://console.redhat.com/api/inventory/v1/hosts?hostname_or_id=foo",
                http_status=403,
            ),
            entry=entry,
            access_payload={"data": [{"permission": "inventory:hosts:read", "resourceDefinitions": []}]},
            access_token=None,
        )
    )
    assert report["do_not_infer_other_permissions"] is True
    assert report["comparison"]["satisfied"] is True
    assert "inventory:hosts:read" in report["caller_permissions"]["permissions"]


def test_manifest_has_all_expected_toolsets():
    """Bundled manifest covers core inventory, vulnerability, and rbac diagnostic tools."""
    manifest = load_manifest()
    assert len(manifest) >= 35
    assert "inventory__find_host_by_name" in manifest
    assert "rbac__explain_access_denied" in manifest
