"""Build deterministic placeholder values from the canonical catalog."""

from __future__ import annotations

from tests.mock_insights_api.catalog.data import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import MockCatalog


def build_llm_api_context(catalog: MockCatalog = DEFAULT_CATALOG) -> dict[str, str]:
    """Return all current LLM prompt placeholders with mutually consistent values."""
    cve = next((item for item in catalog.cves if item.affected_host_ids), None)
    if cve is None:
        raise ValueError("The mock catalog needs a CVE with at least one affected host")

    host_id = cve.affected_host_ids[0]
    host = catalog.host(host_id)
    host_ids = ", ".join(cve.affected_host_ids)

    workspace = next(
        (item for item in catalog.workspaces_for_host(host_id) if item.group_type == "standard"),
        None,
    )
    if workspace is None:
        raise ValueError(f"Host {host_id} must belong to a standard workspace")

    tag = next(iter(catalog.tags_for_host(host_id)), None)
    if tag is None:
        raise ValueError(f"Host {host_id} must have at least one tag")

    rule = next(iter(catalog.rules_for_host(host_id)), None)
    if rule is None:
        raise ValueError(f"Host {host_id} must be affected by an Advisor rule")

    return {
        "cve_id": cve.id,
        "system_id": host.id,
        "host_id": host.id,
        "hostname": host.hostname,
        "host_ids": host_ids,
        "rule_id": rule.id,
        "workspace": workspace.name,
        "satellite_tag": tag.qualified_name,
        "rbac_username": catalog.rbac_username,
    }
