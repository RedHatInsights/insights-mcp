"""Shared types for RBAC requirement resolution (internal, not MCP tool output)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionRequirements:
    """V1 permission requirements for one tool or resolved endpoint."""

    required_v1_permissions: tuple[tuple[str, ...], ...]
    kessel_permission: str
    kessel_note: str
    sources: tuple[str, ...]
    verified: bool


@dataclass(frozen=True)
class RequirementResolution:
    """How requirements were resolved at runtime."""

    source: str
    requirements_unknown: bool
