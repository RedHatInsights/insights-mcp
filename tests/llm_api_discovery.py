"""Discover real Insights API values for LLM prompt template placeholders."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from insights_mcp.client import InsightsClient
from insights_mcp.config import INSIGHTS_BASE_URL, INSIGHTS_CLIENT_ID, INSIGHTS_CLIENT_SECRET


def _insights_credentials() -> tuple[str, str]:
    client_id = os.getenv("INSIGHTS_CLIENT_ID") or os.getenv("LIGHTSPEED_CLIENT_ID") or INSIGHTS_CLIENT_ID or ""
    client_secret = (
        os.getenv("INSIGHTS_CLIENT_SECRET") or os.getenv("LIGHTSPEED_CLIENT_SECRET") or INSIGHTS_CLIENT_SECRET or ""
    )
    return client_id, client_secret


def _api_data(response: dict[str, Any] | str) -> list[dict[str, Any]]:
    if isinstance(response, str):
        return []
    for key in ("data", "results"):
        payload = response.get(key)
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            return [payload]
    return []


def _first_item_id(items: list[dict[str, Any]], *keys: str) -> str | None:
    if not items:
        return None
    item = items[0]
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    attributes = item.get("attributes")
    if isinstance(attributes, dict):
        for key in keys:
            value = attributes.get(key)
            if isinstance(value, str) and value:
                return value
    return None


@dataclass
class LlmApiContext:
    """Resolved placeholder values from live Insights APIs (optional per field)."""

    cve_id: str | None = None
    system_id: str | None = None
    host_id: str | None = None
    hostname: str | None = None
    host_ids: str | None = None
    rule_id: str | None = None
    workspace: str | None = None
    satellite_tag: str | None = None
    rbac_username: str | None = None
    _extra: dict[str, str] = field(default_factory=dict)

    def available_keys(self) -> frozenset[str]:
        """Return placeholder names that have non-empty values."""
        keys: set[str] = set()
        for name in (
            "cve_id",
            "system_id",
            "host_id",
            "hostname",
            "host_ids",
            "rule_id",
            "workspace",
            "satellite_tag",
            "rbac_username",
        ):
            if getattr(self, name):
                keys.add(name)
        keys.update(self._extra.keys())
        return frozenset(keys)

    def as_dict(self) -> dict[str, str]:
        """Mapping for str.format on prompt templates."""
        result: dict[str, str] = {}
        for name in (
            "cve_id",
            "system_id",
            "host_id",
            "hostname",
            "host_ids",
            "rule_id",
            "workspace",
            "satellite_tag",
            "rbac_username",
        ):
            value = getattr(self, name)
            if value:
                result[name] = value
        result.update(self._extra)
        return result


async def _client_for_api_path(api_path: str) -> InsightsClient:
    client_id, client_secret = _insights_credentials()
    return InsightsClient(
        api_path=api_path,
        base_url=INSIGHTS_BASE_URL,
        client_id=client_id,
        client_secret=client_secret,
    )


async def discover_cve_id(client: InsightsClient) -> str | None:
    """Pick a CVE with at least one affected system."""
    response = await client.get(
        "vulnerabilities/cves",
        params={"limit": 20, "offset": 0, "sort": "-systems_affected"},
    )
    for item in _api_data(response):
        cve_id = item.get("id")
        if not isinstance(cve_id, str):
            continue
        affected = item.get("systems_affected")
        if affected is None and isinstance(item.get("attributes"), dict):
            affected = item["attributes"].get("systems_affected")
        if affected is None or (isinstance(affected, int) and affected > 0):
            return cve_id
    return _first_item_id(_api_data(response), "id")


async def discover_system_id_for_cve(client: InsightsClient, cve_id: str) -> str | None:
    """Pick an inventory system UUID affected by *cve_id*."""
    response = await client.get(
        f"cves/{cve_id}/affected_systems",
        params={"limit": 5, "offset": 0},
    )
    return _first_item_id(_api_data(response), "id", "uuid")


async def discover_inventory_hosts(client: InsightsClient) -> tuple[str | None, str | None, str | None]:
    """Return host_id, hostname (display_name or fqdn), and comma-separated two host_ids."""
    response = await client.get("hosts", params={"per_page": 5, "page": 1})
    hosts = _api_data(response)
    if not hosts:
        return None, None, None
    host_id = _first_item_id(hosts, "id")
    first = hosts[0]
    hostname = first.get("display_name") or first.get("fqdn")
    if not isinstance(hostname, str) or not hostname:
        hostname = host_id
    ids: list[str] = []
    for host in hosts[:2]:
        hid = host.get("id")
        if isinstance(hid, str) and hid:
            ids.append(hid)
    host_ids = ", ".join(ids) if ids else None
    return host_id, hostname if isinstance(hostname, str) else None, host_ids


async def discover_satellite_tag(client: InsightsClient, host_id: str) -> str | None:
    """Return namespace/key=value for the first tag on *host_id*, if any."""
    response = await client.get(f"hosts/{host_id}/tags")
    if isinstance(response, str):
        return None
    results = response.get("results")
    if not isinstance(results, list) or not results:
        return None
    tag = results[0]
    if not isinstance(tag, dict):
        return None
    namespace = tag.get("namespace")
    key = tag.get("key")
    value = tag.get("value")
    if isinstance(namespace, str) and isinstance(key, str) and value is not None:
        return f"{namespace}/{key}={value}"
    return None


async def discover_rule_id(client: InsightsClient) -> str | None:
    """Pick an active advisor rule id from the account."""
    response = await client.get("rule/", params={"impacting": True, "limit": 5, "offset": 0})
    return _first_item_id(_api_data(response), "rule_id")


async def discover_rbac_username(client: InsightsClient) -> str | None:
    """Pick a username from cross-application access data, if present."""
    response = await client.get("access/", params={"application": "", "limit": 50, "offset": 0})
    if isinstance(response, str):
        return None
    for key in ("data", "items", "results"):
        items = response.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for f in ("username", "principal", "account_username"):
                value = item.get(f)
                if isinstance(value, str) and value and value != "service-account":
                    return value
    return None


async def build_llm_api_context() -> LlmApiContext:
    """Populate context from live APIs (fields stay None when discovery fails)."""
    workspace = os.getenv("INSIGHTS_TEST_WORKSPACE") or None

    vuln_client = await _client_for_api_path("api/vulnerability/v1")
    inventory_client = await _client_for_api_path("api/inventory/v1")
    advisor_client = await _client_for_api_path("api/insights/v1")
    rbac_client = await _client_for_api_path("api/rbac/v1")

    cve_id = await discover_cve_id(vuln_client)
    system_id = await discover_system_id_for_cve(vuln_client, cve_id) if cve_id else None
    host_id, hostname, host_ids = await discover_inventory_hosts(inventory_client)
    satellite_tag = await discover_satellite_tag(inventory_client, host_id) if host_id else None
    rule_id = await discover_rule_id(advisor_client)
    rbac_username = await discover_rbac_username(rbac_client)

    return LlmApiContext(
        cve_id=cve_id,
        system_id=system_id,
        host_id=host_id,
        hostname=hostname,
        host_ids=host_ids,
        rule_id=rule_id,
        workspace=workspace,
        satellite_tag=satellite_tag,
        rbac_username=rbac_username,
    )
