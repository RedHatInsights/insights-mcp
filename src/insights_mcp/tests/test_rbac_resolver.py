"""Tests for runtime RBAC requirements resolver."""

import pytest

from insights_mcp.rbac.manifest import get_tool_entry
from insights_mcp.rbac.resolver import resolve_tool_requirements


@pytest.mark.asyncio
async def test_resolver_prefers_verified_bundled():
    """Verified bundled manifest entries are used without live OpenAPI fetch."""
    entry = get_tool_entry("vulnerability__get_system_cves")
    assert entry is not None
    resolved = await resolve_tool_requirements(entry, insights_client=None)
    assert resolved.resolution.source == "bundled"
    assert resolved.permissions.verified is True
    assert resolved.resolution.requirements_unknown is False
    flat = [p for ps in resolved.permissions.required_v1_permissions for p in ps]
    assert "vulnerability:vulnerability_results:read" in flat
    assert "inventory:hosts:read" in flat


@pytest.mark.asyncio
async def test_resolver_unknown_does_not_invent():
    """Tools without requirements return requirements_unknown instead of guessing."""
    entry = get_tool_entry("rbac__lookup_tool_requirements")
    assert entry is not None
    resolved = await resolve_tool_requirements(entry, insights_client=None)
    assert resolved.resolution.requirements_unknown is True
    assert resolved.permissions.required_v1_permissions == ()
