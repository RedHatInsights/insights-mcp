"""Compare required vs held permissions and build diagnostic reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from insights_mcp.rbac.catalog import load_role_catalog
from insights_mcp.rbac.manifest import ToolRbacCall, ToolRbacEntry, find_rest_call
from insights_mcp.rbac.permissions import permission_set_satisfied
from insights_mcp.rbac.principal import extract_permissions_from_access_response
from insights_mcp.rbac.resolver import ResolvedRequirements
from insights_mcp.rbac.roles import least_privilege_role_names, union_required_permissions


def compare_permissions(
    call: ToolRbacCall,
    held_permissions: list[str],
    *,
    required_v1_permissions: tuple[tuple[str, ...], ...] | None = None,
) -> dict[str, Any]:
    """Compare rest-map requirements against held permissions."""
    held_set = set(held_permissions)
    satisfied_any_set = False
    missing_from_best: list[str] | None = None
    perm_sets = (
        required_v1_permissions if required_v1_permissions is not None else call.permissions.required_v1_permissions
    )

    for perm_set in perm_sets:
        if permission_set_satisfied(perm_set, held_set):
            satisfied_any_set = True
            missing_from_best = []
            break
        missing = [perm for perm in perm_set if not permission_set_satisfied((perm,), held_set)]
        if missing_from_best is None or len(missing) < len(missing_from_best):
            missing_from_best = missing

    return {
        "held_permissions": held_permissions,
        "satisfied": satisfied_any_set,
        "missing_permissions": [] if satisfied_any_set else missing_from_best or [],
    }


@dataclass(frozen=True)
class AccessDeniedCall:
    """Failed MCP tool invocation."""

    failed_tool: str
    failed_url: str
    http_status: int
    failed_method: str
    tool_name_resolved: str | None = None


@dataclass(frozen=True)
class AccessDeniedInput:
    """Inputs for building an access-denied diagnostic report."""

    call: AccessDeniedCall
    entry: ToolRbacEntry | None
    access_payload: dict[str, Any] | None
    access_token: str | None
    resolved_calls: tuple[ResolvedRequirements, ...] = ()
    role_catalog: tuple[Any, ...] = ()


def _collect_missing_permissions(inp: AccessDeniedInput, held: list[str]) -> tuple[list[str], bool]:
    """Return (missing perms, requirements_unknown)."""
    if inp.entry is None:
        return [], True
    resolved_by_call = dict(zip(inp.entry.rest_calls, inp.resolved_calls))
    matched_call = (
        find_rest_call(inp.entry, inp.call.failed_url, method=inp.call.failed_method) if inp.call.failed_url else None
    )
    rest_calls = [matched_call] if matched_call else list(inp.entry.rest_calls)
    missing: list[str] = []
    any_known = False
    all_unknown = True
    for rest_call in rest_calls:
        resolved = resolved_by_call.get(rest_call)
        if resolved is not None:
            perm_sets = resolved.permissions.required_v1_permissions
            unknown = resolved.resolution.requirements_unknown
        else:
            perm_sets = rest_call.permissions.required_v1_permissions
            unknown = not perm_sets
        if unknown:
            continue
        all_unknown = False
        any_known = True
        comparison = compare_permissions(rest_call, held, required_v1_permissions=perm_sets)
        for perm in comparison["missing_permissions"]:
            if perm not in missing:
                missing.append(perm)
    if not any_known:
        return [], all_unknown
    return missing, False


def build_access_denied_report(inp: AccessDeniedInput) -> dict[str, Any]:
    """Build a role-name-only diagnostic report for explain_access_denied."""
    held: list[str] = []
    if inp.access_payload and isinstance(inp.access_payload, dict):
        held = extract_permissions_from_access_response(inp.access_payload)

    missing_perms, requirements_unknown = _collect_missing_permissions(inp, held)
    if requirements_unknown:
        return {
            "missing_roles": [],
            "note": "Required roles for this tool could not be resolved; do not invent role names.",
            "do_not_infer_other_permissions": True,
        }

    missing_roles = least_privilege_role_names(missing_perms, inp.role_catalog, held)
    result: dict[str, Any] = {
        "missing_roles": missing_roles,
        "do_not_infer_other_permissions": True,
    }
    if not missing_roles and inp.call.http_status == 403:
        if missing_perms:
            result["note"] = "No matching console role was found for the missing access; do not invent role names."
        else:
            result["note"] = "Caller already has the required roles; 403 is likely workspace scoping."
    return result


async def diagnose_missing_roles(
    inp: AccessDeniedInput,
    insights_client: Any | None = None,
    *,
    yaml_text: str | None = None,
) -> dict[str, Any]:
    """Load a role catalog then build the access-denied report."""
    catalog = inp.role_catalog or await load_role_catalog(insights_client, yaml_text=yaml_text)
    return build_access_denied_report(
        AccessDeniedInput(
            call=inp.call,
            entry=inp.entry,
            access_payload=inp.access_payload,
            access_token=inp.access_token,
            resolved_calls=inp.resolved_calls,
            role_catalog=catalog,
        )
    )


def required_roles_for_entry(
    entry: ToolRbacEntry,
    resolved_calls: tuple[ResolvedRequirements, ...],
    catalog: tuple[Any, ...],
) -> tuple[list[str], bool]:
    """Map a tool's resolved permission sets to least-privilege role display names."""
    perm_sets: list[tuple[str, ...]] = []
    if resolved_calls:
        resolved_by_call = dict(zip(entry.rest_calls, resolved_calls))
        for call in entry.rest_calls:
            resolved = resolved_by_call.get(call)
            if resolved is None:
                perm_sets.extend(ps for ps in call.permissions.required_v1_permissions if ps)
            elif not resolved.resolution.requirements_unknown:
                perm_sets.extend(ps for ps in resolved.permissions.required_v1_permissions if ps)
    else:
        for call in entry.rest_calls:
            perm_sets.extend(ps for ps in call.permissions.required_v1_permissions if ps)
    if not perm_sets:
        return [], True
    required = union_required_permissions(perm_sets)
    return least_privilege_role_names(required, catalog), False


__all__ = [
    "AccessDeniedCall",
    "AccessDeniedInput",
    "build_access_denied_report",
    "compare_permissions",
    "diagnose_missing_roles",
    "permission_set_satisfied",
    "required_roles_for_entry",
]
