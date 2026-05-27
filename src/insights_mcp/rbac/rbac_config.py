"""Fetch and parse Red Hat Insights rbac-config platform roles."""

from __future__ import annotations

import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from insights_mcp.rbac.data_files import load_role_recommendations

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


def read_pinned_ref(path: Path | None = None) -> str:
    """Read pinned git ref from configs/rbac_config_ref.txt or RBAC_CONFIG_REF env."""
    env_ref = os.environ.get("RBAC_CONFIG_REF", "").strip()
    if env_ref:
        return env_ref
    ref_path = path or DEFAULT_RBAC_CONFIG_REF_PATH
    if ref_path.is_file():
        return ref_path.read_text(encoding="utf-8").strip()
    return "master"


def fetch_rbac_config_yaml(ref: str | None = None, timeout: float = 30.0) -> str:
    """Download prod rbac-config configmap YAML from GitHub."""
    git_ref = ref or read_pinned_ref()
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


def roles_from_blobs(
    blobs: dict[str, Any],
    *,
    application_prefixes: tuple[str, ...] | None = None,
) -> dict[str, list[str]]:
    """Build role name -> flat permission list from parsed JSON blobs."""
    prefixes = application_prefixes or MCP_APPLICATION_PREFIXES
    role_map: dict[str, list[str]] = {}
    for blob_name, data in blobs.items():
        if not isinstance(data, dict):
            continue
        app_hint = blob_name.replace(".json", "").replace("_", "-")
        for role in data.get("roles", []):
            if not isinstance(role, dict):
                continue
            name = role.get("name")
            if not name:
                continue
            perms: list[str] = []
            for access in role.get("access", []):
                if not isinstance(access, dict):
                    continue
                perm = access.get("permission")
                if perm and isinstance(perm, str):
                    perms.append(perm)
            if not perms:
                continue
            if prefixes:
                if not any(
                    perm.startswith(f"{prefix}:") or perm.startswith(f"{prefix}:*:*")
                    for perm in perms
                    for prefix in prefixes
                ):
                    if app_hint not in prefixes and not any(p.split(":", 1)[0] in prefixes for p in perms if ":" in p):
                        continue
            role_map[name] = sorted(set(perms))
    return role_map


def import_role_recommendations(
    ref: str | None = None,
    yaml_text: str | None = None,
    *,
    application_prefixes: tuple[str, ...] | None = None,
) -> dict[str, list[str]]:
    """Return role -> permissions map from rbac-config (fetch or parse provided YAML)."""
    text = yaml_text if yaml_text is not None else fetch_rbac_config_yaml(ref)
    blobs = parse_role_json_blobs(text)
    return roles_from_blobs(blobs, application_prefixes=application_prefixes)


_cache_state: dict[str, Any] = {"fetched_at": 0.0, "ref": "", "roles": {}}


def get_cached_role_recommendations(
    *,
    force_refresh: bool = False,
    ttl_seconds: int | None = None,
) -> tuple[dict[str, list[str]], str]:
    """Fetch rbac-config roles with in-memory TTL cache.

    Returns:
        (role_map, cache_status) where cache_status is fresh, stale, or unavailable.
    """
    ttl = ttl_seconds if ttl_seconds is not None else int(os.environ.get("RBAC_CONFIG_CACHE_TTL_SECONDS", "86400"))
    ref = read_pinned_ref()
    now = time.time()
    if (
        not force_refresh
        and _cache_state.get("roles")
        and _cache_state.get("ref") == ref
        and now - float(_cache_state.get("fetched_at", 0)) < ttl
    ):
        return dict(_cache_state["roles"]), "fresh"

    try:
        roles = import_role_recommendations(ref=ref)
        _cache_state["roles"] = roles
        _cache_state["ref"] = ref
        _cache_state["fetched_at"] = now
        return roles, "fresh"
    except RbacConfigFetchError:
        if _cache_state.get("roles"):
            return dict(_cache_state["roles"]), "stale"
        return {}, "unavailable"


@lru_cache(maxsize=1)
def load_bundled_role_recommendations() -> dict[str, list[str]]:
    """Load shipped role_recommendations.json."""
    return load_role_recommendations()


def get_role_recommendations_for_runtime() -> tuple[dict[str, list[str]], str]:
    """Prefer live rbac-config cache; fall back to bundled JSON."""
    live, status = get_cached_role_recommendations()
    if live:
        return live, status
    bundled = load_bundled_role_recommendations()
    if bundled:
        return bundled, "bundled" if status == "unavailable" else status
    return {}, status
