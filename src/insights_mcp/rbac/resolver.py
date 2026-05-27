"""Resolve tool RBAC requirements at runtime from bundled manifest and live sources."""

from __future__ import annotations

import os
import re
import time
from contextlib import suppress
from dataclasses import dataclass, replace
from typing import Any

from insights_mcp.rbac.data_files import load_upstream_permissions_index
from insights_mcp.rbac.manifest import ToolRbacEntry
from insights_mcp.rbac.rbac_config import get_role_recommendations_for_runtime
from insights_mcp.rbac.requirements_format import PermissionRequirements, RequirementResolution

PERMISSION_RE = re.compile(
    r"\b([a-z][a-z0-9_-]*:[a-z0-9_.*-]+:[a-z*]+|[a-z][a-z0-9_-]*:\*:\*)\b",
    re.IGNORECASE,
)

_openapi_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_OPENAPI_TTL_SECONDS = 3600


@dataclass(frozen=True)
class ResolvedRequirements:
    """RBAC requirements resolved for one tool."""

    permissions: PermissionRequirements
    resolution: RequirementResolution

    def to_requirements_dict(self) -> dict[str, Any]:
        """Serialize for diagnostic output."""
        return self.permissions.to_diagnostic_dict(extra=self.resolution.to_diagnostic_dict())


def _extract_permissions_from_text(text: str) -> list[str]:
    return sorted(set(PERMISSION_RE.findall(text or "")))


def _openapi_cache_ttl() -> int:
    return int(os.environ.get("RBAC_OPENAPI_CACHE_TTL_SECONDS", str(_OPENAPI_TTL_SECONDS)))


def _get_cached_openapi(api_path: str) -> dict[str, Any] | None:
    api_key = api_path.rstrip("/")
    now = time.time()
    cached = _openapi_cache.get(api_key)
    if cached and now - cached[0] < _openapi_cache_ttl():
        return cached[1]
    return None


def _set_cached_openapi(api_path: str, spec: dict[str, Any]) -> None:
    _openapi_cache[api_path.rstrip("/")] = (time.time(), spec)


async def _fetch_live_openapi(insights_client: Any, api_path: str) -> dict[str, Any] | None:
    """Fetch openapi.json for an Insights API path (may differ from client's api_path)."""
    cached = _get_cached_openapi(api_path)
    if cached is not None:
        return cached

    base_url = getattr(insights_client, "insights_base_url", "").rstrip("/")
    api_segment = api_path.strip("/")
    url = f"{base_url}/{api_segment}/openapi.json"
    response: Any = None
    with suppress(Exception):
        if hasattr(insights_client, "get") and getattr(insights_client, "api_path", "").strip("/") == api_segment:
            response = await insights_client.get("openapi.json", noauth=True)
        else:
            http_client = getattr(insights_client, "client_noauth", None) or getattr(insights_client, "client", None)
            if http_client is None or not hasattr(http_client, "make_request"):
                return None
            response = await http_client.make_request(http_client.get, url=url)
    if isinstance(response, dict):
        _set_cached_openapi(api_path, response)
        return response
    return None


def _path_template_to_regex(path_template: str) -> re.Pattern[str]:
    pattern = re.sub(r"\{[^}]+\}", r"[^/]+", path_template)
    if not pattern.startswith("/"):
        pattern = "/" + pattern
    return re.compile("^" + pattern.rstrip("/") + "/?$")


def _match_openapi_operation(
    spec: dict[str, Any],
    method: str,
    path_template: str,
) -> dict[str, Any] | None:
    """Find OpenAPI operation matching method and path template."""
    paths = spec.get("paths", {})
    method_lower = method.lower()
    template_re = _path_template_to_regex(path_template)

    for path, methods in paths.items():
        if not template_re.match(path):
            continue
        operation = methods.get(method_lower)
        if isinstance(operation, dict):
            return operation
    return None


def _permissions_from_entry(entry: ToolRbacEntry) -> PermissionRequirements:
    return PermissionRequirements(
        required_v1_permissions=entry.permissions.required_v1_permissions,
        kessel_permission=entry.permissions.kessel_permission,
        kessel_note=entry.permissions.kessel_note,
        sources=tuple(entry.openapi_sources),
        recommended_roles=entry.permissions.recommended_roles,
        verified=entry.permissions.verified,
    )


def _resolved(
    permissions: PermissionRequirements,
    source: str,
    *,
    requirements_unknown: bool = False,
    rbac_config_cache: str = "",
) -> ResolvedRequirements:
    return ResolvedRequirements(
        permissions=permissions,
        resolution=RequirementResolution(
            source=source,
            requirements_unknown=requirements_unknown,
            rbac_config_cache=rbac_config_cache,
        ),
    )


def _with_rbac_cache(resolved: ResolvedRequirements, rbac_config_cache: str) -> ResolvedRequirements:
    return replace(
        resolved,
        resolution=replace(resolved.resolution, rbac_config_cache=rbac_config_cache),
    )


def _resolve_from_live_openapi(entry: ToolRbacEntry, spec: dict[str, Any]) -> ResolvedRequirements | None:
    operation = _match_openapi_operation(spec, entry.rest.method, entry.rest.path_template)
    if not operation:
        return None
    text = " ".join(
        filter(
            None,
            [operation.get("summary", ""), operation.get("description", "")],
        )
    )
    perms = _extract_permissions_from_text(text)
    if not perms:
        return None
    sources = tuple(entry.openapi_sources) + (f"live:{entry.rest.api_path}/openapi.json",)
    permissions = PermissionRequirements(
        required_v1_permissions=(tuple(perms),),
        kessel_permission=entry.permissions.kessel_permission,
        kessel_note=entry.permissions.kessel_note,
        sources=sources,
        recommended_roles=entry.permissions.recommended_roles,
        verified=False,
    )
    return _resolved(permissions, "live_openapi")


def _resolve_from_upstream_bundle(entry: ToolRbacEntry) -> ResolvedRequirements | None:
    doc = load_upstream_permissions_index()
    endpoints = doc.get("endpoints", {})
    base = entry.rest.api_path.rstrip("/")
    path = entry.rest.path_template if entry.rest.path_template.startswith("/") else f"/{entry.rest.path_template}"
    key = f"{entry.rest.method.upper()} {base}{path}"
    upstream = endpoints.get(key)
    if not upstream or key.startswith("_"):
        return None
    perm_sets = upstream.get("required_v1_permissions", [])
    permissions = PermissionRequirements(
        required_v1_permissions=tuple(tuple(p) for p in perm_sets),
        kessel_permission=upstream.get("kessel_permission", entry.permissions.kessel_permission),
        kessel_note=upstream.get("kessel_note", entry.permissions.kessel_note),
        sources=tuple(entry.openapi_sources) + ("bundled:upstream_permissions.json",),
        recommended_roles=entry.permissions.recommended_roles,
        verified=bool(upstream.get("verified", False)),
    )
    return _resolved(permissions, "upstream_bundle")


async def resolve_tool_requirements(
    entry: ToolRbacEntry,
    insights_client: Any | None = None,
) -> ResolvedRequirements:
    """Resolve requirements: bundled verified > upstream bundle > live OpenAPI > bundled partial > unknown."""
    _, rbac_config_cache = get_role_recommendations_for_runtime()

    if entry.permissions.verified and entry.permissions.required_v1_permissions:
        return _with_rbac_cache(
            _resolved(_permissions_from_entry(entry), "bundled", requirements_unknown=False),
            rbac_config_cache,
        )

    upstream_resolved = _resolve_from_upstream_bundle(entry)
    if upstream_resolved and upstream_resolved.permissions.required_v1_permissions:
        return _with_rbac_cache(upstream_resolved, rbac_config_cache)

    if insights_client is not None:
        spec = await _fetch_live_openapi(insights_client, entry.rest.api_path)
        if spec:
            live = _resolve_from_live_openapi(entry, spec)
            if live and live.permissions.required_v1_permissions:
                return _with_rbac_cache(live, rbac_config_cache)

    bundled = _permissions_from_entry(entry)
    if bundled.required_v1_permissions:
        return _with_rbac_cache(
            _resolved(bundled, "bundled", requirements_unknown=False),
            rbac_config_cache,
        )

    unknown_permissions = PermissionRequirements(
        required_v1_permissions=(),
        kessel_permission=entry.permissions.kessel_permission,
        kessel_note=entry.permissions.kessel_note,
        sources=tuple(entry.openapi_sources),
        recommended_roles=entry.permissions.recommended_roles,
        verified=False,
    )
    return _with_rbac_cache(
        _resolved(unknown_permissions, "unknown", requirements_unknown=True),
        rbac_config_cache,
    )


def roles_covering_missing_runtime(
    missing: list[str],
    held: list[str],
) -> tuple[list[str], str]:
    """Suggest roles using live rbac-config cache with bundled fallback."""
    if not missing:
        return [], ""
    role_map, cache_status = get_role_recommendations_for_runtime()
    held_set = set(held)
    suggestions: list[str] = []
    for role_name, role_perms in role_map.items():
        role_perm_set = set(role_perms)
        if all(p in role_perm_set or p in held_set for p in missing):
            if role_name not in suggestions:
                suggestions.append(role_name)
    return suggestions, cache_status
