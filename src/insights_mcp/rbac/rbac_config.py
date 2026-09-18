"""Fetch and parse Red Hat Insights rbac-config platform roles."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from insights_mcp.rbac.roles import PlatformRole

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RBAC_CONFIG_REF_PATH = REPO_ROOT / "configs" / "rbac_config_ref.txt"
RBAC_CONFIG_RAW_URL = (
    "https://raw.githubusercontent.com/RedHatInsights/rbac-config/{ref}/_private/configmaps/prod/rbac-config.yml"
)

# MCP toolsets -> rbac-config JSON blob prefixes (application segment in permission strings)
MCP_APPLICATION_PREFIXES: tuple[str, ...] = (
    "inventory",
    "vulnerability",
    "advisor",
    "config-manager",
    "content-sources",
    "roadmap",
    "image-builder",
    "rbac",
    "remediations",
    "insights",
)

_JSON_BLOB_HEADER = re.compile(r"^(\s+)([a-z0-9_.-]+\.json): \|$", re.MULTILINE)


class RbacConfigFetchError(Exception):
    """Failed to fetch or parse rbac-config."""


def read_configured_ref(path: Path | None = None) -> str:
    """Read the configured git ref from configs/rbac_config_ref.txt or RBAC_CONFIG_REF env."""
    env_ref = os.environ.get("RBAC_CONFIG_REF", "").strip()
    if env_ref:
        return env_ref
    ref_path = path or DEFAULT_RBAC_CONFIG_REF_PATH
    if ref_path.is_file():
        return ref_path.read_text(encoding="utf-8").strip()
    return "master"


def fetch_rbac_config_yaml(ref: str | None = None, timeout: float = 30.0) -> str:
    """Download prod rbac-config configmap YAML from GitHub."""
    git_ref = ref or read_configured_ref()
    url = RBAC_CONFIG_RAW_URL.format(ref=git_ref)
    request = Request(url, headers={"User-Agent": "insights-mcp-rbac-config/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except URLError as exc:
        raise RbacConfigFetchError(f"fetch rbac-config failed for ref {git_ref!r}: {exc}") from exc


def parse_role_json_blobs(yaml_text: str) -> dict[str, Any]:
    """Extract embedded *.json documents from rbac-config.yml without PyYAML."""
    blobs: dict[str, Any] = {}
    matches = list(_JSON_BLOB_HEADER.finditer(yaml_text))
    for index, match in enumerate(matches):
        key_indent = match.group(1)
        blob_name = match.group(2)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(yaml_text)
        block = yaml_text[start:end]
        lines: list[str] = []
        content_indent: str | None = None
        for line in block.splitlines():
            if not line.strip():
                continue
            if content_indent is None:
                if len(line) <= len(key_indent) or not line.startswith(key_indent + " "):
                    break
                content_indent = line[: len(line) - len(line.lstrip())]
            if not line.startswith(content_indent):
                if line.startswith(key_indent):
                    break
                continue
            lines.append(line.removeprefix(content_indent))
        if not lines:
            continue
        try:
            blobs[blob_name] = json.loads("\n".join(lines))
        except json.JSONDecodeError:
            continue
    return blobs


def _permissions_match_prefixes(perms: list[str], prefixes: tuple[str, ...], app_hint: str) -> bool:
    if not prefixes:
        return True
    if any(perm.startswith(f"{prefix}:") or perm.startswith(f"{prefix}:*:*") for perm in perms for prefix in prefixes):
        return True
    if app_hint in prefixes:
        return True
    return any(perm.split(":", 1)[0] in prefixes for perm in perms if ":" in perm)


def _permissions_from_role_dict(role: dict[str, Any]) -> list[str]:
    perms: list[str] = []
    for access in role.get("access", []):
        if not isinstance(access, dict):
            continue
        perm = access.get("permission")
        if perm and isinstance(perm, str):
            perms.append(perm)
    return perms


def _platform_role_from_dict(role: dict[str, Any]) -> PlatformRole | None:
    name = role.get("name")
    if not name or not isinstance(name, str):
        return None
    perms = _permissions_from_role_dict(role)
    if not perms:
        return None
    display_name = role.get("display_name")
    display = display_name if isinstance(display_name, str) and display_name else name
    return PlatformRole(name=name, display_name=display, permissions=frozenset(perms))


def roles_from_blobs(
    blobs: dict[str, Any],
    *,
    application_prefixes: tuple[str, ...] | None = None,
) -> list[PlatformRole]:
    """Build platform roles from parsed JSON blobs."""
    prefixes = application_prefixes if application_prefixes is not None else MCP_APPLICATION_PREFIXES
    roles: list[PlatformRole] = []
    seen_labels: set[str] = set()
    for blob_name, data in blobs.items():
        if not isinstance(data, dict):
            continue
        app_hint = blob_name.replace(".json", "").replace("_", "-")
        for role in data.get("roles", []):
            if not isinstance(role, dict):
                continue
            platform_role = _platform_role_from_dict(role)
            if platform_role is None:
                continue
            if not _permissions_match_prefixes(list(platform_role.permissions), prefixes, app_hint):
                continue
            label = platform_role.label()
            if label in seen_labels:
                continue
            seen_labels.add(label)
            roles.append(platform_role)
    return roles


def import_platform_roles(
    ref: str | None = None,
    yaml_text: str | None = None,
    *,
    application_prefixes: tuple[str, ...] | None = None,
) -> list[PlatformRole]:
    """Return platform roles from rbac-config (fetch or parse provided YAML)."""
    text = yaml_text if yaml_text is not None else fetch_rbac_config_yaml(ref)
    blobs = parse_role_json_blobs(text)
    return roles_from_blobs(blobs, application_prefixes=application_prefixes)
