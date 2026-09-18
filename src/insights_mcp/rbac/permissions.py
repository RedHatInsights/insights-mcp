"""V1 permission matching (wildcards) used by RBAC diagnostics."""

from __future__ import annotations


def split_permission(permission: str) -> tuple[str, str, str]:
    """Split app:resource:verb; unmatched strings become (permission, '*', '*')."""
    parts = permission.split(":", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return permission, "*", "*"


def permission_set_satisfied(required_set: tuple[str, ...], held: set[str]) -> bool:
    """True if every required permission is held directly or through a wildcard."""
    for required in required_set:
        if required in held:
            continue
        app, resource, verb = split_permission(required)
        if f"{app}:*:{verb}" in held or f"{app}:{resource}:*" in held or f"{app}:*:*" in held:
            continue
        if f"{app}:*" in held:
            continue
        return False
    return True
