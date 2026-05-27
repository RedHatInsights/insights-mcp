"""Shared types and serialization for RBAC requirement diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

V1_PERMISSION_NOTE = "Caller needs all permissions in at least one inner list (AND within list, OR across lists)."


@dataclass(frozen=True)
class PermissionRequirements:
    """V1 and Kessel permission requirements for one tool or resolved endpoint."""

    required_v1_permissions: tuple[tuple[str, ...], ...]
    kessel_permission: str
    kessel_note: str
    sources: tuple[str, ...]
    recommended_roles: tuple[str, ...]
    verified: bool

    def to_diagnostic_dict(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Serialize for explain_access_denied and lookup_tool_requirements output."""
        result: dict[str, Any] = {
            "v1_permission_sets": [list(ps) for ps in self.required_v1_permissions],
            "v1_note": V1_PERMISSION_NOTE,
            "kessel_permission": self.kessel_permission or None,
            "kessel_note": self.kessel_note or None,
            "sources": list(self.sources),
            "recommended_roles": list(self.recommended_roles),
            "verified": self.verified,
        }
        if extra:
            result.update(extra)
        return result


@dataclass(frozen=True)
class RequirementResolution:
    """How requirements were resolved at runtime."""

    source: str
    requirements_unknown: bool
    rbac_config_cache: str = ""

    def to_diagnostic_dict(self) -> dict[str, Any]:
        """Extra keys merged into PermissionRequirements.to_diagnostic_dict."""
        return {
            "requirements_unknown": self.requirements_unknown,
            "resolution_source": self.source,
            "rbac_config_cache": self.rbac_config_cache or None,
        }
