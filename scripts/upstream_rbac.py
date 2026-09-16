#!/usr/bin/env python3
"""Build upstream_permissions.json from curated upstream service enforcement mappings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "src" / "insights_mcp" / "rbac" / "data"
UPSTREAM_REFS_PATH = REPO_ROOT / "configs" / "upstream_refs.json"

# Source-reviewed mappings from insights-host-inventory and vulnerability-engine.
# Source links intentionally track the branches configured in upstream_refs.json.
KNOWN_UPSTREAM: dict[str, dict[str, Any]] = {
    "GET api/inventory/v1/hosts": {
        "application": "inventory",
        "required_v1_permissions": [["inventory:hosts:read"]],
        "kessel_permission": "inventory_host_view",
        "kessel_note": "",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/insights-host-inventory",
            "file": "api/host.py",
            "handler": "get_host_list",
            "rbac_decorators": ["KesselResourceTypes.HOST.view"],
        },
    },
    "GET api/inventory/v1/hosts/{host_ids}": {
        "application": "inventory",
        "required_v1_permissions": [["inventory:hosts:read"]],
        "kessel_permission": "inventory_host_view",
        "kessel_note": "",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/insights-host-inventory",
            "file": "api/host.py",
            "handler": "get_host_list",
            "rbac_decorators": ["KesselResourceTypes.HOST.view"],
        },
    },
    "GET api/inventory/v1/hosts/{host_ids}/system_profile": {
        "application": "inventory",
        "required_v1_permissions": [["inventory:hosts:read"]],
        "kessel_permission": "inventory_host_view",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/insights-host-inventory",
            "file": "api/host.py",
            "handler": "get_host_list",
            "rbac_decorators": ["KesselResourceTypes.HOST.view"],
        },
    },
    "GET api/inventory/v1/hosts/{host_ids}/tags": {
        "application": "inventory",
        "required_v1_permissions": [["inventory:hosts:read"]],
        "kessel_permission": "inventory_host_view",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/insights-host-inventory",
            "file": "api/host.py",
            "handler": "get_host_list",
            "rbac_decorators": ["KesselResourceTypes.HOST.view"],
        },
    },
    "GET api/vulnerability/v1/systems/{inventory_id}/cves": {
        "application": "vulnerability",
        "required_v1_permissions": [
            ["vulnerability:vulnerability_results:read", "inventory:hosts:read"],
        ],
        "kessel_permission": "vulnerability_vulnerability_results_view",
        "kessel_note": (
            "Kessel: vulnerability_vulnerability_results_view requires inventory_host_view "
            "on the host workspace (see RedHatInsights/rbac-config vulnerability.ksl)."
        ),
        "user_guidance_notes": [
            "Do not suggest vulnerability:system.cves:read; it is not a valid permission.",
        ],
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/vulnerability-engine",
            "file": "manager/system_handler.py",
            "handler": "GetSystemsCves.handle_get",
            "rbac_decorators": ["RbacRoutePermissions.VULNERABILITY_RESULTS"],
        },
    },
    "GET api/vulnerability/v1/vulnerabilities/cves": {
        "application": "vulnerability",
        "required_v1_permissions": [["vulnerability:vulnerability_results:read", "inventory:hosts:read"]],
        "kessel_permission": "vulnerability_vulnerability_results_view",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/vulnerability-engine",
            "file": "manager/vulnerabilities_handler.py",
            "handler": "GetCves",
            "rbac_decorators": ["RbacRoutePermissions.VULNERABILITY_RESULTS"],
        },
    },
    "GET api/vulnerability/v1/cves/{cve}": {
        "application": "vulnerability",
        "required_v1_permissions": [["vulnerability:vulnerability_results:read", "inventory:hosts:read"]],
        "kessel_permission": "vulnerability_vulnerability_results_view",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/vulnerability-engine",
            "file": "manager/cve_handler.py",
            "handler": "GetCves",
            "rbac_decorators": ["RbacRoutePermissions.VULNERABILITY_RESULTS"],
        },
    },
    "GET api/vulnerability/v1/cves/{cve}/affected_systems": {
        "application": "vulnerability",
        "required_v1_permissions": [["vulnerability:vulnerability_results:read", "inventory:hosts:read"]],
        "kessel_permission": "vulnerability_vulnerability_results_view",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/vulnerability-engine",
            "file": "manager/cve_handler.py",
            "handler": "GetCvesAffectedSystems",
            "rbac_decorators": ["RbacRoutePermissions.VULNERABILITY_RESULTS"],
        },
    },
    "GET api/vulnerability/v1/systems": {
        "application": "vulnerability",
        "required_v1_permissions": [["vulnerability:vulnerability_results:read", "inventory:hosts:read"]],
        "kessel_permission": "vulnerability_vulnerability_results_view",
        "verified": True,
        "upstream": {
            "repo": "RedHatInsights/vulnerability-engine",
            "file": "manager/system_handler.py",
            "handler": "GetSystems",
            "rbac_decorators": ["RbacRoutePermissions.VULNERABILITY_RESULTS"],
        },
    },
}


def _endpoint_key(method: str, api_path: str, path_template: str) -> str:
    base = api_path.rstrip("/")
    path = path_template if path_template.startswith("/") else f"/{path_template}"
    return f"{method.upper()} {base}{path}"


def build_upstream_permissions() -> dict[str, Any]:
    """Return curated endpoint permissions and their configured source branches."""
    refs: dict[str, str] = {}
    if UPSTREAM_REFS_PATH.is_file():
        refs = json.loads(UPSTREAM_REFS_PATH.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "upstream_refs": refs,
        "endpoints": KNOWN_UPSTREAM,
    }


def lookup_upstream(
    permissions_doc: dict[str, Any],
    method: str,
    api_path: str,
    path_template: str,
) -> dict[str, Any] | None:
    """Lookup curated permissions for a REST call."""
    key = _endpoint_key(method, api_path, path_template)
    endpoints = permissions_doc.get("endpoints", {})
    return endpoints.get(key)


def main() -> None:
    """Write upstream_permissions.json."""
    doc = build_upstream_permissions()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "upstream_permissions.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    count = len([k for k in doc["endpoints"] if not k.startswith("_")])
    print(f"Wrote {out} ({count} endpoints)")


if __name__ == "__main__":
    main()
