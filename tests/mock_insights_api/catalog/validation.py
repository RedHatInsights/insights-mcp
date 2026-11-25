"""Integrity checks for the canonical LLM-test API catalog."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from tests.mock_insights_api.catalog.errors import CatalogValidationError
from tests.mock_insights_api.catalog.models import (
    CVE,
    AdvisorRule,
    Host,
    MockCatalog,
    OCPAdvisorCluster,
    RepositoryReference,
)

_Entity = TypeVar("_Entity")


@dataclass(frozen=True, slots=True)
class _CatalogIndexes:
    """Indexes used to validate relationships between catalog entities."""

    hosts: Mapping[str, Host]
    repositories: Mapping[str, RepositoryReference]
    cves: Mapping[str, CVE]
    advisor_rules: Mapping[str, AdvisorRule]
    ocp_advisor_clusters: Mapping[str, OCPAdvisorCluster]


def _index(
    entities: Iterable[_Entity],
    key: Callable[[_Entity], str],
    entity_name: str,
) -> Mapping[str, _Entity]:
    """Build an ID index and reject duplicate or empty IDs."""
    indexed: dict[str, _Entity] = {}
    for entity in entities:
        entity_id = key(entity)
        if not entity_id:
            raise CatalogValidationError(f"{entity_name} IDs must not be empty")
        if entity_id in indexed:
            raise CatalogValidationError(f"Duplicate {entity_name} ID: {entity_id}")
        indexed[entity_id] = entity
    return indexed


def _validate_references(
    references: Iterable[str],
    known_ids: Mapping[str, object],
    reference_name: str,
) -> None:
    """Ensure every relationship points to an entity in the catalog."""
    for reference in references:
        if reference not in known_ids:
            raise CatalogValidationError(f"Unknown {reference_name} reference: {reference}")


def _build_indexes(catalog: MockCatalog) -> _CatalogIndexes:
    """Build the indexes and validate IDs for every referenced entity type."""
    _index(catalog.workspaces, lambda workspace: workspace.id, "workspace")
    _index(catalog.ocp_advisor_rules, lambda rule: rule.id, "OCP Advisor rule")
    return _CatalogIndexes(
        hosts=_index(catalog.hosts, lambda host: host.id, "host"),
        repositories=_index(catalog.repositories, lambda repository: repository.id, "repository"),
        cves=_index(catalog.cves, lambda cve: cve.id, "CVE"),
        advisor_rules=_index(catalog.advisor_rules, lambda rule: rule.id, "Advisor rule"),
        ocp_advisor_clusters=_index(
            catalog.ocp_advisor_clusters,
            lambda cluster: cluster.cluster_id,
            "OCP Advisor cluster",
        ),
    )


def _validate_profiles(catalog: MockCatalog, indexes: _CatalogIndexes) -> None:
    """Validate host profiles and their enabled repository references."""
    profiles_by_host_id = _index(catalog.system_profiles, lambda profile: profile.host_id, "system profile")
    _validate_references(profiles_by_host_id, indexes.hosts, "host")
    missing_profiles = set(indexes.hosts) - set(profiles_by_host_id)
    if missing_profiles:
        missing = ", ".join(sorted(missing_profiles))
        raise CatalogValidationError(f"Missing system profile for host(s): {missing}")
    for profile in catalog.system_profiles:
        _validate_references(profile.enabled_repository_ids, indexes.repositories, "repository")
    for repository in catalog.content_source_repositories:
        if repository.repository_reference_id is not None:
            _validate_references((repository.repository_reference_id,), indexes.repositories, "repository")


def _validate_host_relationships(catalog: MockCatalog, indexes: _CatalogIndexes) -> None:
    """Validate workspace and tag host references."""
    for workspace in catalog.workspaces:
        _validate_references(workspace.host_ids, indexes.hosts, "workspace host")
    for tag in catalog.tags:
        _validate_references(tag.host_ids, indexes.hosts, "tag host")


def _validate_cves(catalog: MockCatalog, indexes: _CatalogIndexes) -> None:
    """Validate CVE host and reciprocal Advisor rule references."""
    for cve in catalog.cves:
        _validate_references(cve.affected_host_ids, indexes.hosts, "CVE host")
        _validate_references(cve.rule_ids, indexes.advisor_rules, "CVE rule")
        for rule_id in cve.rule_ids:
            if cve.id not in indexes.advisor_rules[rule_id].cve_ids:
                raise CatalogValidationError(f"CVE {cve.id} and Advisor rule {rule_id} are not reciprocal")


def _validate_advisor_rules(catalog: MockCatalog, indexes: _CatalogIndexes) -> None:
    """Validate Advisor host and reciprocal CVE references."""
    for rule in catalog.advisor_rules:
        _validate_references(rule.affected_host_ids, indexes.hosts, "Advisor rule host")
        _validate_references(rule.cve_ids, indexes.cves, "Advisor rule CVE")
        for cve_id in rule.cve_ids:
            if rule.id not in indexes.cves[cve_id].rule_ids:
                raise CatalogValidationError(f"Advisor rule {rule.id} and CVE {cve_id} are not reciprocal")


def _validate_ocp_advisor_rules(catalog: MockCatalog, indexes: _CatalogIndexes) -> None:
    """Validate OCP Advisor cluster references."""
    for ocp_rule in catalog.ocp_advisor_rules:
        _validate_references(
            ocp_rule.affected_cluster_ids,
            indexes.ocp_advisor_clusters,
            "OCP Advisor cluster",
        )


def validate_catalog(catalog: MockCatalog) -> None:
    """Validate IDs and foreign-key-like relationships in a catalog."""
    indexes = _build_indexes(catalog)
    _validate_profiles(catalog, indexes)
    _validate_host_relationships(catalog, indexes)
    _validate_cves(catalog, indexes)
    _validate_advisor_rules(catalog, indexes)
    _validate_ocp_advisor_rules(catalog, indexes)
