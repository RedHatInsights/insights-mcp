"""Least-privilege mapping from permission strings to console role display names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from insights_mcp.rbac.permissions import permission_set_satisfied, split_permission

# Consolidated RHEL User Access roles that grant many apps at once. Prefer app-scoped
# roles (e.g. RHEL Advisor viewer) over these when covering the same permissions.
CONSOLIDATED_ROLE_NAMES = frozenset(
    {
        "rhel viewer",
        "rhel operator",
        "rhel admin",
        "rhel administrator",
    }
)


@dataclass(frozen=True)
class PlatformRole:
    """A canned or custom Hybrid Cloud Console role."""

    name: str
    display_name: str
    permissions: frozenset[str]

    def label(self) -> str:
        """Console-facing name: display_name with name as fallback."""
        return self.display_name or self.name

    def is_consolidated(self) -> bool:
        """True for wide RHEL viewer/operator/admin roles."""
        return self.name.lower() in CONSOLIDATED_ROLE_NAMES or self.label().lower() in CONSOLIDATED_ROLE_NAMES


def _unsatisfied(required: Iterable[str], held: set[str]) -> list[str]:
    return [perm for perm in required if not permission_set_satisfied((perm,), held)]


def _covers_any(role: PlatformRole, remaining: list[str], held: set[str]) -> bool:
    available = held | set(role.permissions)
    return any(permission_set_satisfied((perm,), available) for perm in remaining)


def _newly_covered_count(role: PlatformRole, remaining: list[str], held: set[str]) -> int:
    available = held | set(role.permissions)
    return sum(1 for perm in remaining if permission_set_satisfied((perm,), available))


def _wildcard_rank(permission: str) -> int:
    """Higher rank means a broader permission (prefer specific viewer grants)."""
    _app, resource, verb = split_permission(permission)
    rank = 0
    if resource == "*":
        rank += 2
    if verb == "*":
        rank += 4
    return rank


def _role_width(role: PlatformRole) -> tuple[int, int]:
    """Sort key: wildcard breadth, then number of grants on the role."""
    return (sum(_wildcard_rank(perm) for perm in role.permissions), len(role.permissions))


def least_privilege_role_names(
    required_permissions: Iterable[str],
    catalog: Iterable[PlatformRole],
    held_permissions: Iterable[str] = (),
) -> list[str]:
    """Return display names of the smallest app-scoped roles that cover missing perms.

    Prefers non-consolidated, narrower roles (viewers over administrators). Picks
    the narrowest role that covers the first remaining permission, then repeats.
    """
    held = set(held_permissions)
    remaining = _unsatisfied(required_permissions, held)
    if not remaining:
        return []

    roles = list(catalog)
    selected: list[str] = []
    used: set[str] = set()

    def pick(pool: list[PlatformRole]) -> PlatformRole | None:
        covering = [role for role in pool if role.label() not in used and _covers_any(role, remaining, held)]
        if not covering:
            return None
        covering_first = [
            role for role in covering if permission_set_satisfied((remaining[0],), held | set(role.permissions))
        ]
        candidates = covering_first or covering

        def score(role: PlatformRole) -> tuple[int, int, int, str]:
            width_wild, width_len = _role_width(role)
            return (width_wild, width_len, -_newly_covered_count(role, remaining, held), role.label())

        return min(candidates, key=score)

    scoped = [role for role in roles if not role.is_consolidated()]
    while remaining:
        choice = pick(scoped) or pick(roles)
        if choice is None:
            break
        selected.append(choice.label())
        used.add(choice.label())
        held = held | set(choice.permissions)
        remaining = _unsatisfied(remaining, held)
    return selected


def union_required_permissions(perm_sets: Iterable[tuple[str, ...]]) -> list[str]:
    """Flatten permission sets from REST calls into a unique list (first-seen order)."""
    seen: list[str] = []
    for perm_set in perm_sets:
        for perm in perm_set:
            if perm not in seen:
                seen.append(perm)
    return seen
