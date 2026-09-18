"""Load a role catalog from the live RBAC API or rbac-config fallback."""

# Pagination over RBAC list endpoints matches rbac_mcp.access.fetch_caller_access.
# pylint: disable=duplicate-code

from __future__ import annotations

import time
from typing import Any

from insights_mcp.rbac.rbac_config import RbacConfigFetchError, fetch_rbac_config_yaml, import_platform_roles
from insights_mcp.rbac.roles import PlatformRole

_CATALOG_CACHE: list[tuple[float, tuple[PlatformRole, ...]]] = []
_CATALOG_TTL_SECONDS = 3600


def _permissions_from_access(access: Any) -> list[str]:
    if not isinstance(access, list):
        return []
    perms: list[str] = []
    for item in access:
        if isinstance(item, dict):
            perm = item.get("permission")
            if isinstance(perm, str) and perm not in perms:
                perms.append(perm)
    return perms


def _role_from_payload(item: dict[str, Any]) -> PlatformRole | None:
    name = item.get("name")
    if not isinstance(name, str) or not name:
        return None
    perms = _permissions_from_access(item.get("access"))
    if not perms:
        return None
    display = item.get("display_name")
    display_name = display if isinstance(display, str) and display else name
    return PlatformRole(name=name, display_name=display_name, permissions=frozenset(perms))


async def _fetch_live_roles(insights_client: Any, page_limit: int = 100) -> list[PlatformRole] | None:
    """Paginate GET /roles/; fetch role detail when access is omitted."""
    all_items: list[dict[str, Any]] = []
    offset = 0
    total_count: int | None = None
    while True:
        response = await insights_client.get("roles/", params={"limit": page_limit, "offset": offset})
        if isinstance(response, str) or not isinstance(response, dict):
            return None
        if response.get("error") or "Unhandled error" in response:
            return None
        page_data = response.get("data", [])
        if not isinstance(page_data, list):
            return None
        all_items.extend(item for item in page_data if isinstance(item, dict))
        meta = response.get("meta", {})
        if isinstance(meta, dict) and "count" in meta:
            total_count = meta["count"]
        if not page_data or len(page_data) < page_limit:
            break
        offset += page_limit
        if total_count is not None and offset >= total_count:
            break

    roles: list[PlatformRole] = []
    for item in all_items:
        role = _role_from_payload(item)
        if role is None:
            uuid = item.get("uuid")
            if not isinstance(uuid, str) or not uuid:
                continue
            detail = await insights_client.get(f"roles/{uuid}/")
            if isinstance(detail, dict):
                role = _role_from_payload(detail)
        if role is not None:
            roles.append(role)
    return roles if roles else None


def catalog_from_rbac_config_yaml(yaml_text: str) -> tuple[PlatformRole, ...]:
    """Parse a rbac-config YAML document into platform roles."""
    return tuple(import_platform_roles(yaml_text=yaml_text))


def catalog_from_rbac_config_fetch() -> tuple[PlatformRole, ...]:
    """Download rbac-config and parse platform roles."""
    yaml_text = fetch_rbac_config_yaml()
    return catalog_from_rbac_config_yaml(yaml_text)


async def load_role_catalog(
    insights_client: Any | None = None,
    *,
    yaml_text: str | None = None,
) -> tuple[PlatformRole, ...]:
    """Prefer live GET /api/rbac/v1/roles/; fall back to rbac-config.

    yaml_text is for tests (skip network). Results are cached briefly when fetched live.
    """
    if yaml_text is not None:
        return catalog_from_rbac_config_yaml(yaml_text)

    now = time.time()
    if _CATALOG_CACHE and now - _CATALOG_CACHE[0][0] < _CATALOG_TTL_SECONDS:
        return _CATALOG_CACHE[0][1]

    live: list[PlatformRole] | None = None
    if insights_client is not None:
        try:
            live = await _fetch_live_roles(insights_client)
        except Exception:  # pylint: disable=broad-exception-caught
            live = None
    if live:
        catalog = tuple(live)
        _CATALOG_CACHE.clear()
        _CATALOG_CACHE.append((now, catalog))
        return catalog

    try:
        catalog = catalog_from_rbac_config_fetch()
    except RbacConfigFetchError:
        catalog = ()
    _CATALOG_CACHE.clear()
    _CATALOG_CACHE.append((now, catalog))
    return catalog
