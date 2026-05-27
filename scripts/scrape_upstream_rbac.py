#!/usr/bin/env python3
"""Build upstream_permissions.json from known service enforcement + optional git scrape."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "src" / "insights_mcp" / "rbac" / "data"
UPSTREAM_REFS_PATH = REPO_ROOT / "configs" / "upstream_refs.json"
CLONE_DIR = REPO_ROOT / ".cache" / "upstream-rbac-repos"

# Verified from upstream repos (insights-host-inventory, vulnerability-engine).
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
            "file": "manager/vuln_handler.py",
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
            "file": "manager/vuln_handler.py",
            "handler": "GetCveDetails",
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
            "file": "manager/vuln_handler.py",
            "handler": "GetCveAffectedSystems",
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

VULN_ENUM_MAP = {
    "VULNERABILITY_RESULTS": [
        "vulnerability:vulnerability_results:read",
        "inventory:hosts:read",
    ],
}


def _endpoint_key(method: str, api_path: str, path_template: str) -> str:
    base = api_path.rstrip("/")
    path = path_template if path_template.startswith("/") else f"/{path_template}"
    return f"{method.upper()} {base}{path}"


def _try_git_scrape(refs: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Shallow-clone upstream repos and scan for vulnerability RBAC enums (best-effort)."""
    discovered: dict[str, dict[str, Any]] = {}
    CLONE_DIR.mkdir(parents=True, exist_ok=True)
    vuln_repo = "RedHatInsights/vulnerability-engine"
    ref = refs.get(vuln_repo, "master")
    clone_path = CLONE_DIR / "vulnerability-engine"
    if not clone_path.is_dir():
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    ref,
                    f"https://github.com/{vuln_repo}.git",
                    str(clone_path),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.SubprocessError, OSError):
            return discovered

    rbac_file = clone_path / "common" / "rbac.py"
    if not rbac_file.is_file():
        rbac_file = clone_path / "manager" / "rbac.py"
    if rbac_file.is_file():
        text = rbac_file.read_text(encoding="utf-8", errors="replace")
        for enum_name, perms in VULN_ENUM_MAP.items():
            if enum_name in text:
                discovered[f"_enum_{enum_name}"] = {
                    "required_v1_permissions": [perms],
                    "verified": True,
                    "upstream": {"repo": vuln_repo, "file": str(rbac_file.relative_to(clone_path))},
                }
    return discovered


def build_upstream_permissions(*, try_git: bool = True) -> dict[str, Any]:
    """Merge known upstream endpoint permissions."""
    endpoints = dict(KNOWN_UPSTREAM)
    refs: dict[str, str] = {}
    if UPSTREAM_REFS_PATH.is_file():
        refs = json.loads(UPSTREAM_REFS_PATH.read_text(encoding="utf-8"))
    if try_git:
        git_extra = _try_git_scrape(refs)
        if git_extra:
            endpoints["_git_scrape_metadata"] = git_extra
    return {
        "schema_version": 1,
        "upstream_refs": refs,
        "endpoints": endpoints,
    }


def lookup_upstream(
    permissions_doc: dict[str, Any],
    method: str,
    api_path: str,
    path_template: str,
) -> dict[str, Any] | None:
    """Lookup scraped permissions for a REST call."""
    key = _endpoint_key(method, api_path, path_template)
    endpoints = permissions_doc.get("endpoints", {})
    return endpoints.get(key)


def main() -> None:
    """Write upstream_permissions.json."""
    doc = build_upstream_permissions(try_git="--no-git" not in sys.argv)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "upstream_permissions.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    count = len([k for k in doc["endpoints"] if not k.startswith("_")])
    print(f"Wrote {out} ({count} endpoints)")


if __name__ == "__main__":
    main()
