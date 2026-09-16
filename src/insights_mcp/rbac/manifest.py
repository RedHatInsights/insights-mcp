"""Load and query the tool RBAC manifest."""

from __future__ import annotations

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
class ToolRbacCall:
    """RBAC requirements for one REST call made by an MCP tool."""

    rest: RestCallSpec
    application: str
    permissions: PermissionRequirements
    upstream: UpstreamSpec | None
    openapi_sources: tuple[str, ...]
    user_guidance_notes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolRbacCall:
        """Build a REST call from the manifest."""
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
            rest=RestCallSpec(
                method=data["method"].upper(),
                api_path=data["api_path"],
                path_template=data["path_template"],
            ),
            application=data.get("application", ""),
            permissions=permissions,
            upstream=upstream,
            openapi_sources=tuple(data.get("openapi_sources", [])),
            user_guidance_notes=tuple(data.get("user_guidance_notes", [])),
        )

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


@dataclass(frozen=True)
class ToolRbacEntry:
    """RBAC requirements for one MCP tool."""

    tool_name: str
    rest_calls: tuple[ToolRbacCall, ...]

    @classmethod
    def from_dict(cls, tool_name: str, data: list[dict[str, Any]]) -> ToolRbacEntry:
        """Build an entry from its required REST-call list."""
        return cls(
            tool_name=tool_name,
            rest_calls=tuple(ToolRbacCall.from_dict(call) for call in data),
        )

    def all_required_v1_flat(self) -> list[str]:
        """Return the union of permissions required by all calls."""
        seen: list[str] = []
        for call in self.rest_calls:
            for perm_set in call.permissions.required_v1_permissions:
                for perm in perm_set:
                    if perm not in seen:
                        seen.append(perm)
        return seen


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, ToolRbacEntry]:
    """Load tool_rbac_manifest.json (cached)."""
    data = load_manifest_raw()
    tools = data.get("tools", data)
    return {name: ToolRbacEntry.from_dict(name, entry) for name, entry in tools.items()}


def get_tool_entry(tool_name: str) -> ToolRbacEntry | None:
    """Lookup by full MCP tool name (e.g. vulnerability__get_system_cves)."""
    return load_manifest().get(tool_name)


def _path_matches(template: str, path: str, *, suffix: bool = False) -> bool:
    """Match each {parameter} to one non-empty path segment."""
    expected = template.strip("/").split("/")
    actual = path.strip("/").split("/")
    if suffix:
        if len(actual) < len(expected):
            return False
        offset = len(actual) - len(expected)
    else:
        if len(actual) != len(expected):
            return False
        offset = 0
    return all(
        wanted == actual[index + offset]
        or (wanted.startswith("{") and wanted.endswith("}") and bool(actual[index + offset]))
        for index, wanted in enumerate(expected)
    )


def _score_rest_match(call: ToolRbacCall, path: str) -> int:
    template_full = call.rest.full_path_template()
    if _path_matches(template_full, path):
        return len(template_full) + 1000
    path_template = call.rest.path_template
    if path_template != "/" and _path_matches(path_template, path, suffix=True):
        return len(path_template)
    return -1


def _prefer_entry_over_tie(
    current: tuple[ToolRbacEntry, ToolRbacCall],
    candidate: tuple[ToolRbacEntry, ToolRbacCall],
    method_upper: str,
) -> tuple[ToolRbacEntry, ToolRbacCall]:
    current_entry, current_call = current
    candidate_entry, candidate_call = candidate
    if candidate_call.permissions.verified and not current_call.permissions.verified:
        return candidate
    if candidate_call.permissions.verified == current_call.permissions.verified and method_upper == "GET":
        if "__get_" in candidate_entry.tool_name and "__get_" not in current_entry.tool_name:
            return candidate
    return current


def find_tool_by_rest_url(url: str, method: str = "GET") -> ToolRbacEntry | None:
    """Find manifest entry matching a failed request URL."""
    parsed = urlparse(url)
    path = parsed.path or url
    method_upper = method.upper()

    best: tuple[ToolRbacEntry, ToolRbacCall] | None = None
    best_score = -1
    for entry in load_manifest().values():
        for call in entry.rest_calls:
            if call.rest.method != method_upper:
                continue
            score = _score_rest_match(call, path)
            candidate = (entry, call)
            if score > best_score:
                best = candidate
                best_score = score
            elif score == best_score and score >= 0 and best is not None:
                best = _prefer_entry_over_tie(best, candidate, method_upper)
    return best[0] if best else None


def find_rest_call(entry: ToolRbacEntry, url: str) -> ToolRbacCall | None:
    """Find the REST call in an entry matching a failed URL."""
    parsed = urlparse(url)
    path = parsed.path or url
    scored = [(_score_rest_match(call, path), call) for call in entry.rest_calls]
    score, call = max(scored, key=lambda item: item[0])
    return call if score >= 0 else None


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
