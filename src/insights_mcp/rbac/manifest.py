"""Load and query the tool RBAC manifest."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from insights_mcp.rbac.data_files import load_manifest_raw
from insights_mcp.rbac.requirements_format import PermissionRequirements


@dataclass(frozen=True)
class RestCallSpec:
    """REST endpoint invoked by an MCP tool."""

    method: str
    api_path: str
    path_template: str

    def full_path_template(self) -> str:
        """Return path under api_path (no leading slash on api_path)."""
        base = self.api_path.rstrip("/")
        path = self.path_template if self.path_template.startswith("/") else f"/{self.path_template}"
        return f"/{base}{path}"


@dataclass(frozen=True)
class UpstreamSpec:
    """Reference to upstream RBAC enforcement."""

    repo: str
    file: str
    handler: str
    rbac_decorators: tuple[str, ...] = ()
    enforcement_note: str = ""


@dataclass(frozen=True)
class ToolRbacEntry:
    """RBAC requirements for one MCP tool."""

    tool_name: str
    rest: RestCallSpec
    application: str
    permissions: PermissionRequirements
    upstream: UpstreamSpec | None
    openapi_sources: tuple[str, ...]
    user_guidance_notes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, tool_name: str, data: dict[str, Any]) -> ToolRbacEntry:
        """Build entry from manifest JSON object."""
        rest_data = data["rest"]
        upstream = None
        if "upstream" in data:
            up = data["upstream"]
            upstream = UpstreamSpec(
                repo=up["repo"],
                file=up["file"],
                handler=up["handler"],
                rbac_decorators=tuple(up.get("rbac_decorators", [])),
                enforcement_note=up.get("enforcement_note", ""),
            )
        perm_lists = data.get("required_v1_permissions", [])
        permissions = PermissionRequirements(
            required_v1_permissions=tuple(tuple(p) for p in perm_lists),
            kessel_permission=data.get("kessel_permission", ""),
            kessel_note=data.get("kessel_note", ""),
            sources=tuple(data.get("openapi_sources", [])),
            recommended_roles=tuple(data.get("recommended_roles", [])),
            verified=bool(data.get("verified", False)),
        )
        return cls(
            tool_name=tool_name,
            rest=RestCallSpec(
                method=rest_data["method"].upper(),
                api_path=rest_data["api_path"],
                path_template=rest_data["path_template"],
            ),
            application=data.get("application", ""),
            permissions=permissions,
            upstream=upstream,
            openapi_sources=tuple(data.get("openapi_sources", [])),
            user_guidance_notes=tuple(data.get("user_guidance_notes", [])),
        )

    def all_required_v1_flat(self) -> list[str]:
        """Flatten permission sets: union of permissions from any satisfied set."""
        seen: list[str] = []
        for perm_set in self.permissions.required_v1_permissions:
            for perm in perm_set:
                if perm not in seen:
                    seen.append(perm)
        return seen

    def _diagnostic_sources(self) -> list[str]:
        sources: list[str] = list(self.openapi_sources)
        if self.upstream:
            sources.append(f"https://github.com/{self.upstream.repo}/blob/master/{self.upstream.file}")
        return sources

    def to_requirements_dict(self) -> dict[str, Any]:
        """Serialize requirements for diagnostic output."""
        upstream = (
            {
                "repo": self.upstream.repo,
                "file": self.upstream.file,
                "handler": self.upstream.handler,
                "rbac_decorators": list(self.upstream.rbac_decorators),
            }
            if self.upstream
            else None
        )
        return PermissionRequirements(
            required_v1_permissions=self.permissions.required_v1_permissions,
            kessel_permission=self.permissions.kessel_permission,
            kessel_note=self.permissions.kessel_note,
            sources=tuple(self._diagnostic_sources()),
            recommended_roles=self.permissions.recommended_roles,
            verified=self.permissions.verified,
        ).to_diagnostic_dict(extra={"upstream": upstream})


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, ToolRbacEntry]:
    """Load tool_rbac_manifest.json (cached)."""
    data = load_manifest_raw()
    tools = data.get("tools", data)
    return {name: ToolRbacEntry.from_dict(name, entry) for name, entry in tools.items()}


def load_manifest_provenance() -> dict[str, Any]:
    """Return provenance block from the bundled manifest, if present."""
    data = load_manifest_raw()
    provenance = data.get("provenance")
    return provenance if isinstance(provenance, dict) else {}


def get_tool_entry(tool_name: str) -> ToolRbacEntry | None:
    """Lookup by full MCP tool name (e.g. vulnerability__get_system_cves)."""
    return load_manifest().get(tool_name)


_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _normalize_path_for_match(path: str) -> str:
    """Replace UUIDs and path parameter names for template matching."""
    normalized = _UUID_RE.sub("{id}", path)
    return re.sub(r"\{[^}]+\}", "{id}", normalized)


def _score_rest_match(entry: ToolRbacEntry, normalized: str) -> int:
    template_full = entry.rest.full_path_template()
    template_norm = _normalize_path_for_match(template_full)
    path_suffix = _normalize_path_for_match(entry.rest.path_template)
    if normalized == template_norm:
        return len(template_norm) + 1000
    if normalized.endswith(path_suffix) and path_suffix != "/":
        return len(path_suffix)
    return -1


def _prefer_entry_over_tie(current: ToolRbacEntry, candidate: ToolRbacEntry, method_upper: str) -> ToolRbacEntry:
    if candidate.permissions.verified and not current.permissions.verified:
        return candidate
    if candidate.permissions.verified == current.permissions.verified and method_upper == "GET":
        if "__get_" in candidate.tool_name and "__get_" not in current.tool_name:
            return candidate
    return current


def find_tool_by_rest_url(url: str, method: str = "GET") -> ToolRbacEntry | None:
    """Find manifest entry matching a failed request URL."""
    parsed = urlparse(url)
    path = parsed.path or url
    method_upper = method.upper()
    normalized = _normalize_path_for_match(path)

    best: ToolRbacEntry | None = None
    best_score = -1
    for entry in load_manifest().values():
        if entry.rest.method != method_upper:
            continue
        score = _score_rest_match(entry, normalized)
        if score > best_score:
            best = entry
            best_score = score
        elif score == best_score and score >= 0 and best is not None:
            best = _prefer_entry_over_tie(best, entry, method_upper)
    return best


def resolve_tool_name(failed_tool: str, failed_url: str, method: str = "GET") -> str | None:
    """Resolve tool name from explicit name or URL."""
    if failed_tool:
        name = failed_tool.strip()
        if "__" not in name and "_" in name:
            parts = name.split("_", 1)
            if len(parts) == 2:
                candidate = f"{parts[0]}__{parts[1]}"
                if candidate in load_manifest():
                    return candidate
        if name in load_manifest():
            return name
    if failed_url:
        entry = find_tool_by_rest_url(failed_url, method=method)
        if entry:
            return entry.tool_name
    return failed_tool if failed_tool in load_manifest() else None
