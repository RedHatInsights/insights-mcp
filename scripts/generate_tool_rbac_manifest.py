#!/usr/bin/env python3
"""Generate tool_rbac_manifest.json and role_recommendations.json from upstream sources."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
DATA_DIR = REPO_ROOT / "src" / "insights_mcp" / "rbac" / "data"
TOOL_REST_MAP_PATH = REPO_ROOT / "configs" / "tool_rest_map.json"
UPSTREAM_REFS_PATH = REPO_ROOT / "configs" / "upstream_refs.json"

from insights_mcp.rbac.rbac_config import import_role_recommendations, read_pinned_ref  # noqa: E402

# Import sibling scripts
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from parse_openapi_permissions import build_openapi_permission_index, lookup_endpoint  # noqa: E402
from scrape_upstream_rbac import build_upstream_permissions, lookup_upstream  # noqa: E402


def _skeleton_entry(toolset_name: str, tool_name: str, api_path: str) -> dict[str, Any]:
    return {
        "rest": {
            "method": "GET",
            "api_path": api_path,
            "path_template": "/",
        },
        "application": toolset_name,
        "required_v1_permissions": [],
        "kessel_permission": "",
        "kessel_note": "",
        "recommended_roles": [],
        "openapi_sources": [],
        "verified": False,
    }


def _collect_readonly_tool_names() -> list[str]:
    from insights_mcp.server import MCPS

    names: list[str] = []
    for mcp_instance in MCPS:
        try:
            mcp_instance.register_tools()
        except NotImplementedError:
            pass
        tools = asyncio.run(mcp_instance.list_tools())
        for tool in tools:
            read_only = getattr(getattr(tool, "annotations", None), "readOnlyHint", True)
            if read_only is False:
                continue
            names.append(f"{mcp_instance.toolset_name}__{tool.name}")
    return sorted(set(names))


def _toolset_api_path(toolset_name: str) -> str:
    from insights_mcp.server import MCPS

    for mcp_instance in MCPS:
        if mcp_instance.toolset_name == toolset_name:
            return mcp_instance.api_path
    return f"api/{toolset_name}/v1"


def _apply_template(tool_def: dict[str, Any], templates: dict[str, Any]) -> dict[str, Any]:
    template_name = tool_def.get("template")
    if not template_name:
        return dict(tool_def)
    merged = dict(templates.get(template_name, {}))
    merged.update({k: v for k, v in tool_def.items() if k != "template"})
    return merged


def _build_entry_from_tool_def(tool_def: dict[str, Any]) -> dict[str, Any]:
    method = tool_def["method"]
    api_path = tool_def["api_path"]
    path_template = tool_def["path_template"]
    rest = {"method": method, "api_path": api_path, "path_template": path_template}
    entry: dict[str, Any] = {
        "rest": rest,
        "application": tool_def.get("application", ""),
        "required_v1_permissions": tool_def.get("required_v1_permissions", []),
        "kessel_permission": tool_def.get("kessel_permission", ""),
        "kessel_note": tool_def.get("kessel_note", ""),
        "recommended_roles": tool_def.get("recommended_roles", []),
        "openapi_sources": tool_def.get("openapi_sources", []),
        "verified": bool(tool_def.get("verified", False)),
    }
    if tool_def.get("upstream"):
        entry["upstream"] = tool_def["upstream"]
    if tool_def.get("user_guidance_notes"):
        entry["user_guidance_notes"] = tool_def["user_guidance_notes"]
    return entry


def _merge_upstream(entry: dict[str, Any], upstream_doc: dict[str, Any]) -> None:
    rest = entry["rest"]
    upstream = lookup_upstream(
        upstream_doc,
        rest["method"],
        rest["api_path"],
        rest["path_template"],
    )
    if not upstream:
        return
    for field in (
        "application",
        "required_v1_permissions",
        "kessel_permission",
        "kessel_note",
        "user_guidance_notes",
    ):
        if field in upstream and upstream[field]:
            entry[field] = upstream[field]
    if upstream.get("upstream"):
        entry["upstream"] = upstream["upstream"]
    if upstream.get("verified"):
        entry["verified"] = True


def _merge_openapi(entry: dict[str, Any], openapi_index: dict[str, dict[str, Any]]) -> None:
    if entry.get("verified") and entry.get("required_v1_permissions"):
        return
    rest = entry["rest"]
    hit = lookup_endpoint(openapi_index, rest["method"], rest["path_template"])
    if not hit:
        return
    if not entry.get("required_v1_permissions"):
        entry["required_v1_permissions"] = hit.get("required_v1_permissions", [])
    source = hit.get("openapi_source")
    if source:
        sources = list(entry.get("openapi_sources", []))
        if source not in sources:
            sources.append(source)
        entry["openapi_sources"] = sources


def build_manifest() -> tuple[dict[str, Any], dict[str, list[str]]]:
    """Build manifest dict and role recommendations."""
    rbac_ref = read_pinned_ref()
    roles = import_role_recommendations(ref=rbac_ref)

    upstream_doc = build_upstream_permissions(try_git=False)
    upstream_path = DATA_DIR / "upstream_permissions.json"
    upstream_path.write_text(json.dumps(upstream_doc, indent=2) + "\n", encoding="utf-8")

    openapi_index = build_openapi_permission_index()

    map_data = json.loads(TOOL_REST_MAP_PATH.read_text(encoding="utf-8"))
    templates = map_data.get("templates", {})
    tool_defs = map_data.get("tools", {})

    tools: dict[str, dict[str, Any]] = {}
    for tool_name, raw_def in tool_defs.items():
        merged_def = _apply_template(raw_def, templates)
        entry = _build_entry_from_tool_def(merged_def)
        _merge_upstream(entry, upstream_doc)
        _merge_openapi(entry, openapi_index)
        tools[tool_name] = entry

    for tool_name in _collect_readonly_tool_names():
        if tool_name in tools:
            continue
        toolset = tool_name.split("__", 1)[0]
        tools[tool_name] = _skeleton_entry(toolset, tool_name.split("__", 1)[-1], _toolset_api_path(toolset))

    upstream_refs: dict[str, str] = {}
    if UPSTREAM_REFS_PATH.is_file():
        upstream_refs = json.loads(UPSTREAM_REFS_PATH.read_text(encoding="utf-8"))

    manifest = {
        "schema_version": 1,
        "generated_by": "scripts/generate_tool_rbac_manifest.py",
        "provenance": {
            "rbac_config_ref": rbac_ref,
            "upstream_refs": upstream_refs,
        },
        "tools": dict(sorted(tools.items())),
    }
    return manifest, roles


def main() -> None:
    """Write manifest and role recommendation files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest, roles = build_manifest()
    manifest_path = DATA_DIR / "tool_rbac_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    roles_path = DATA_DIR / "role_recommendations.json"
    roles_path.write_text(json.dumps(roles, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {manifest_path} ({len(manifest['tools'])} tools)")
    print(f"Wrote {roles_path} ({len(roles)} roles)")
    print(f"rbac_config_ref={manifest['provenance']['rbac_config_ref']}")


if __name__ == "__main__":
    main()
