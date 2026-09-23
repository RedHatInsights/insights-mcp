#!/usr/bin/env python3
"""Generate README / skill snippets of least-privilege console role display names."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

# pylint: disable=wrong-import-position
from insights_mcp.rbac.catalog import (  # noqa: E402
    catalog_from_rbac_config_fetch,
    catalog_from_rbac_config_yaml,
)
from insights_mcp.rbac.data_files import load_tool_rest_map  # noqa: E402
from insights_mcp.rbac.manifest import apply_rest_map_template  # noqa: E402
from insights_mcp.rbac.rbac_config import RbacConfigFetchError  # noqa: E402
from insights_mcp.rbac.roles import least_privilege_role_names, union_required_permissions  # noqa: E402

README_BEGIN = "<!-- BEGIN GENERATED RBAC ROLES -->"
README_END = "<!-- END GENERATED RBAC ROLES -->"
TABLE_BEGIN = "<!-- BEGIN GENERATED RBAC ROLE TABLE -->"
TABLE_END = "<!-- END GENERATED RBAC ROLE TABLE -->"

SKIP_TOOLSETS = frozenset({"rbac"})

TOOLSET_LABELS = {
    "advisor": "Advisor tools",
    "inventory": "Inventory tools",
    "vulnerability": "Vulnerability tools",
    "remediations": "Remediation tools",
    "image-builder": "Image Builder tools",
    "rhsm": "RHSM tools",
    "content-sources": "Content Sources tools",
    "planning": "Planning tools",
}

PREFERRED_ORDER = (
    "advisor",
    "inventory",
    "vulnerability",
    "remediations",
    "image-builder",
    "rhsm",
    "content-sources",
    "planning",
)

README_PATHS = (REPO_ROOT / "README.md",)

SKILL_PATHS = (
    REPO_ROOT / ".agents" / "skills" / "getting-started" / "SKILL.md",
    REPO_ROOT / ".claude" / "skills" / "getting-started" / "SKILL.md",
)


def _toolset_of(tool_name: str) -> str:
    return tool_name.split("__", 1)[0]


def perms_by_toolset() -> dict[str, list[str]]:
    """Union required v1 permissions per toolset from the rest map."""
    data = load_tool_rest_map()
    templates = data.get("templates", {})
    grouped: dict[str, list[tuple[str, ...]]] = defaultdict(list)
    for tool_name, raw_calls in data.get("tools", {}).items():
        toolset = _toolset_of(tool_name)
        if toolset in SKIP_TOOLSETS:
            continue
        for raw_call in raw_calls:
            call = apply_rest_map_template(raw_call, templates)
            for perm_set in call.get("required_v1_permissions") or []:
                if perm_set:
                    grouped[toolset].append(tuple(perm_set))
    return {toolset: union_required_permissions(sets) for toolset, sets in grouped.items() if sets}


def roles_by_toolset(catalog: tuple) -> dict[str, list[str]]:
    """Least-privilege display names covering each toolset's required permissions."""
    result: dict[str, list[str]] = {}
    for toolset, perms in perms_by_toolset().items():
        roles = least_privilege_role_names(perms, catalog)
        if roles:
            result[toolset] = roles
    return result


def _ordered_toolsets(toolsets: dict[str, list[str]]) -> list[str]:
    ordered = [name for name in PREFERRED_ORDER if name in toolsets]
    extra = sorted(name for name in toolsets if name not in PREFERRED_ORDER)
    return ordered + extra


def render_readme_block(toolsets: dict[str, list[str]]) -> str:
    """Markdown bullet list of toolset role display names."""
    lines = [
        README_BEGIN,
        "",
        "Different toolsets require specific roles for your service account:",
        "",
    ]
    for toolset in _ordered_toolsets(toolsets):
        label = TOOLSET_LABELS.get(toolset, f"{toolset} tools")
        roles = ", ".join(f"`{name}`" for name in toolsets[toolset])
        lines.append(f"- **{label}**: {roles}")
    lines.extend(["", README_END])
    return "\n".join(lines)


def render_skill_table(toolsets: dict[str, list[str]]) -> str:
    """Markdown table of toolset role display names for getting-started skills."""
    lines = [
        TABLE_BEGIN,
        "",
        "| Toolset | Required Roles |",
        "|---|---|",
    ]
    for toolset in _ordered_toolsets(toolsets):
        roles = ", ".join(toolsets[toolset])
        lines.append(f"| {toolset} | {roles} |")
    lines.extend(["", TABLE_END])
    return "\n".join(lines)


def replace_marker_block(content: str, begin: str, end: str, replacement: str) -> str:
    """Replace inclusive marker block; insert after heading if markers are missing."""
    start = content.find(begin)
    stop = content.find(end)
    if start == -1 or stop == -1 or stop < start:
        raise ValueError(f"missing markers {begin!r} / {end!r}")
    stop_end = stop + len(end)
    return content[:start] + replacement + content[stop_end:]


def load_catalog(yaml_path: Path | None):
    """Load platform roles from a YAML file or fetch rbac-config."""
    if yaml_path is not None:
        return catalog_from_rbac_config_yaml(yaml_path.read_text(encoding="utf-8"))
    try:
        return catalog_from_rbac_config_fetch()
    except RbacConfigFetchError as exc:
        raise SystemExit(f"error: failed to fetch rbac-config: {exc}") from exc


def main() -> int:
    """Rewrite generated RBAC role snippets in README and getting-started skills."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yaml",
        type=Path,
        default=None,
        help="rbac-config YAML instead of fetching from GitHub",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the README block and exit without writing files",
    )
    args = parser.parse_args()
    catalog = load_catalog(args.yaml)
    if not catalog:
        raise SystemExit("error: role catalog is empty")
    toolsets = roles_by_toolset(catalog)
    readme_block = render_readme_block(toolsets)
    table_block = render_skill_table(toolsets)
    if args.print_only:
        print(readme_block)
        return 0
    for path in README_PATHS:
        updated = replace_marker_block(path.read_text(encoding="utf-8"), README_BEGIN, README_END, readme_block)
        path.write_text(updated, encoding="utf-8")
    for path in SKILL_PATHS:
        if not path.is_file():
            continue
        updated = replace_marker_block(path.read_text(encoding="utf-8"), TABLE_BEGIN, TABLE_END, table_block)
        path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
