"""Tests for least-privilege role set-cover."""

from insights_mcp.rbac.roles import PlatformRole, least_privilege_role_names


def _catalog() -> list[PlatformRole]:
    return [
        PlatformRole("Advisor Viewer", "RHEL Advisor viewer", frozenset({"advisor:*:read"})),
        PlatformRole("Inventory Hosts Viewer", "Inventory Hosts viewer", frozenset({"inventory:hosts:read"})),
        PlatformRole(
            "Inventory Groups Viewer",
            "Workspace viewer",
            frozenset({"inventory:groups:read", "rbac:role_binding:view"}),
        ),
        PlatformRole(
            "Vulnerability viewer",
            "Vulnerability viewer",
            frozenset({"vulnerability:vulnerability_results:read"}),
        ),
        PlatformRole(
            "RHEL viewer",
            "RHEL viewer",
            frozenset(
                {
                    "advisor:*:read",
                    "inventory:hosts:read",
                    "inventory:groups:read",
                    "vulnerability:*:read",
                }
            ),
        ),
    ]


def test_advisor_prefers_scoped_role_over_rhel_viewer():
    """advisor:*:read maps to RHEL Advisor viewer, not consolidated RHEL viewer."""
    names = least_privilege_role_names(["advisor:*:read"], _catalog())
    assert names == ["RHEL Advisor viewer"]


def test_workspace_viewer_for_groups_read():
    """inventory:groups:read maps to Workspace viewer display_name."""
    names = least_privilege_role_names(["inventory:groups:read"], _catalog())
    assert names == ["Workspace viewer"]


def test_vulnerability_and_inventory_hosts():
    """Vuln results plus inventory hosts use two app-scoped roles."""
    names = least_privilege_role_names(
        ["vulnerability:vulnerability_results:read", "inventory:hosts:read"],
        _catalog(),
    )
    assert names == ["Vulnerability viewer", "Inventory Hosts viewer"]


def test_held_permissions_omit_covered_roles():
    """Roles are not suggested for permissions the caller already holds."""
    names = least_privilege_role_names(
        ["advisor:*:read", "inventory:hosts:read"],
        _catalog(),
        held_permissions=["advisor:*:read"],
    )
    assert names == ["Inventory Hosts viewer"]


def test_viewer_preferred_over_administrator():
    """Wildcard administrator roles lose to narrower viewer roles."""
    catalog = _catalog() + [
        PlatformRole("Insights administrator", "RHEL Advisor administrator", frozenset({"advisor:*:*"})),
        PlatformRole("Inventory administrator", "Inventory administrator", frozenset({"inventory:*:*"})),
        PlatformRole(
            "Vulnerability administrator",
            "Vulnerability administrator",
            frozenset({"vulnerability:*:*", "remediations:*:read", "remediations:*:write"}),
        ),
    ]
    assert least_privilege_role_names(["advisor:*:read"], catalog) == ["RHEL Advisor viewer"]
    assert least_privilege_role_names(["inventory:hosts:read"], catalog) == ["Inventory Hosts viewer"]
    assert least_privilege_role_names(["vulnerability:vulnerability_results:read"], catalog) == ["Vulnerability viewer"]
