"""Helpers to fetch RBAC access for the authenticated caller."""

from __future__ import annotations

from typing import Any

from insights_mcp.rbac.principal import extract_permissions_from_access_response


async def fetch_caller_access(
    insights_client: Any,
    *,
    application: str = "",
    username: str = "",
    page_limit: int = 100,
) -> dict[str, Any]:
    """Fetch all access records for the caller, paginating until complete.

    Args:
        insights_client: InsightsClient for api/rbac/v1
        application: RBAC application filter (empty = all)
        username: Optional username to query (requires RBAC admin permission)
        page_limit: Page size per request

    Returns:
        Combined access payload with meta and data list
    """
    all_data: list[dict[str, Any]] = []
    offset = 0
    total_count: int | None = None

    while True:
        params: dict[str, Any] = {
            "application": application,
            "limit": page_limit,
            "offset": offset,
        }
        if username:
            params["username"] = username

        response = await insights_client.get("access/", params=params)
        if isinstance(response, str):
            return {"error": response, "data": all_data}

        page_data = response.get("data", [])
        if isinstance(page_data, list):
            all_data.extend(page_data)

        meta = response.get("meta", {})
        if isinstance(meta, dict) and "count" in meta:
            total_count = meta["count"]

        if not page_data or len(page_data) < page_limit:
            break
        offset += page_limit
        if total_count is not None and offset >= total_count:
            break

    return {
        "meta": {"count": len(all_data), "paginated": True},
        "data": all_data,
        "permissions": extract_permissions_from_access_response({"data": all_data}),
    }


def get_access_token_from_client(insights_client: Any) -> str | None:
    """Best-effort extract bearer token from insights client after auth."""
    client = getattr(insights_client, "client", None)
    if client is None:
        return None
    token = getattr(client, "token", None)
    if token is None:
        return None
    if isinstance(token, dict):
        return token.get("access_token")
    return getattr(token, "access_token", None)
