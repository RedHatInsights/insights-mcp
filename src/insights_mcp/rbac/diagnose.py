"""Compare required vs held permissions and build diagnostic reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from insights_mcp.rbac.manifest import ToolRbacEntry, resolve_tool_name
from insights_mcp.rbac.principal import classify_principal_from_token, extract_permissions_from_access_response
from insights_mcp.rbac.resolver import ResolvedRequirements, roles_covering_missing_runtime


def permission_set_satisfied(required_set: tuple[str, ...], held: set[str]) -> bool:
    """True if caller holds every permission in the set (or a wildcard superset)."""
    for req in required_set:
        if req in held:
            continue
        app, resource, verb = _split_permission(req)
        if f"{app}:*:{verb}" in held or f"{app}:{resource}:*" in held or f"{app}:*:*" in held:
            continue
        if f"{app}:*" in held:
            continue
        return False
    return True


def _split_permission(perm: str) -> tuple[str, str, str]:
    parts = perm.split(":", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return perm, "*", "*"


def compare_permissions(
    entry: ToolRbacEntry,
    held_permissions: list[str],
    *,
    required_v1_permissions: tuple[tuple[str, ...], ...] | None = None,
) -> dict[str, Any]:
    """Compare manifest requirements against held permissions."""
    held_set = set(held_permissions)
    satisfied_any_set = False
    missing_from_best: list[str] = []
    perm_sets = (
        required_v1_permissions if required_v1_permissions is not None else entry.permissions.required_v1_permissions
    )

    for perm_set in perm_sets:
        if permission_set_satisfied(perm_set, held_set):
            satisfied_any_set = True
            missing_from_best = []
            break
        missing = [p for p in perm_set if not permission_set_satisfied((p,), held_set)]
        if len(missing) > len(missing_from_best):
            missing_from_best = missing

    return {
        "held_permissions": held_permissions,
        "satisfied": satisfied_any_set,
        "missing_permissions": [] if satisfied_any_set else missing_from_best,
    }


@dataclass(frozen=True)
class AccessDeniedCall:
    """Failed MCP tool invocation."""

    failed_tool: str
    failed_url: str
    http_status: int
    tool_name_resolved: str | None = None


@dataclass(frozen=True)
class AccessDeniedInput:
    """Inputs for building an access-denied diagnostic report."""

    call: AccessDeniedCall
    entry: ToolRbacEntry | None
    access_payload: dict[str, Any] | None
    access_token: str | None
    resolved: ResolvedRequirements | None = None


@dataclass
class EntryDiagnosis:
    """RBAC diagnosis derived from a manifest entry."""

    requirements: dict[str, Any] | None
    comparison: dict[str, Any]
    recommended_roles: list[str]
    rbac_config_cache: str
    extra_guidance: list[str]


def _default_user_guidance() -> list[str]:
    return [
        "Assign roles in Red Hat Hybrid Cloud Console → Settings → User Access.",
        (
            "If MCP uses a service account (client ID/secret in mcp.json or environment), "
            "grant roles to that service account—not only your personal user."
        ),
        "https://console.redhat.com/iam/user-access/overview",
    ]


def _diagnose_entry(
    entry: ToolRbacEntry,
    held: list[str],
    resolved: ResolvedRequirements | None,
) -> EntryDiagnosis:
    if resolved:
        requirements = resolved.to_requirements_dict()
        comparison = compare_permissions(
            entry,
            held,
            required_v1_permissions=resolved.permissions.required_v1_permissions,
        )
        recommended_roles = list(resolved.permissions.recommended_roles or entry.permissions.recommended_roles)
        rbac_config_cache = resolved.resolution.rbac_config_cache
        extra_guidance: list[str] = []
        if resolved.permissions.kessel_note:
            extra_guidance.append(resolved.permissions.kessel_note)
    else:
        requirements = entry.to_requirements_dict()
        comparison = compare_permissions(entry, held)
        recommended_roles = list(entry.permissions.recommended_roles)
        rbac_config_cache = ""
        extra_guidance = []

    extra_roles, cache_status = roles_covering_missing_runtime(comparison.get("missing_permissions", []), held)
    if cache_status and not rbac_config_cache:
        rbac_config_cache = cache_status
    for role in extra_roles:
        if role not in recommended_roles:
            recommended_roles.append(role)

    extra_guidance.extend(entry.user_guidance_notes)
    if entry.permissions.kessel_note and not (resolved and resolved.permissions.kessel_note):
        extra_guidance.append(entry.permissions.kessel_note)
    if resolved and resolved.resolution.requirements_unknown:
        extra_guidance.append(
            "Required permissions for this tool could not be resolved from bundled or live sources; "
            "do not invent permission names."
        )

    return EntryDiagnosis(
        requirements=requirements,
        comparison=comparison,
        recommended_roles=recommended_roles,
        rbac_config_cache=rbac_config_cache,
        extra_guidance=extra_guidance,
    )


def _rest_call_dict(entry: ToolRbacEntry | None, failed_url: str) -> dict[str, Any]:
    if entry is None:
        return {"method": "GET", "url": failed_url or None}
    return {
        "method": entry.rest.method,
        "api_path": entry.rest.api_path,
        "path_template": entry.rest.path_template,
        "url": failed_url or None,
    }


def build_access_denied_report(inp: AccessDeniedInput) -> dict[str, Any]:
    """Build structured diagnostic report for explain_access_denied."""
    call = inp.call
    tool_resolved = call.tool_name_resolved or resolve_tool_name(call.failed_tool, call.failed_url)
    principal = classify_principal_from_token(inp.access_token)
    held: list[str] = []
    if inp.access_payload and isinstance(inp.access_payload, dict):
        held = extract_permissions_from_access_response(inp.access_payload)

    user_guidance = _default_user_guidance()
    comparison: dict[str, Any] = {}
    requirements: dict[str, Any] | None = None
    recommended_roles: list[str] = []
    rbac_config_cache = ""

    if inp.entry:
        diagnosis = _diagnose_entry(inp.entry, held, inp.resolved)
        requirements = diagnosis.requirements
        comparison = diagnosis.comparison
        recommended_roles = diagnosis.recommended_roles
        rbac_config_cache = diagnosis.rbac_config_cache
        user_guidance.extend(diagnosis.extra_guidance)
    else:
        user_guidance.append(
            "No manifest entry for this tool; call rbac__lookup_tool_requirements after updating insights-mcp."
        )

    if comparison.get("satisfied") and call.http_status == 403:
        user_guidance.append(
            "Caller has required v1 permission strings but still received 403. "
            "Likely workspace/group scoping (Kessel): ensure access to the host workspace."
        )

    return {
        "failed": {
            "tool": tool_resolved or call.failed_tool or None,
            "http_status": call.http_status,
        },
        "rest_call": _rest_call_dict(inp.entry, call.failed_url),
        "required_permissions": requirements,
        "caller_permissions": {
            "principal": principal["principal_type"],
            "client_id": principal.get("client_id"),
            "username_hint": principal.get("username_hint"),
            "permissions": held,
            "principal_note": principal.get("note"),
        },
        "comparison": comparison,
        "missing_permissions": comparison.get("missing_permissions", []),
        "recommended_roles": recommended_roles,
        "user_guidance": user_guidance,
        "rbac_config_cache": rbac_config_cache or None,
        "do_not_infer_other_permissions": True,
    }
