"""Typed entities and relationship indexes for the LLM-test API catalog."""

# The catalog entities intentionally mirror several fields from their API resources.
# pylint: disable=too-many-instance-attributes

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import TypeVar

_Entity = TypeVar("_Entity")


@dataclass(frozen=True, slots=True)
class Host:
    """A host exposed by the Inventory API."""

    id: str
    hostname: str
    fqdn: str
    rhel_version: str
    last_seen: datetime
    updated: datetime
    provider_type: str
    registered_with: str


@dataclass(frozen=True, slots=True)
class SystemProfile:
    """The system-profile data associated with one host."""

    host_id: str
    os_name: str
    architecture: str
    memory_bytes: int
    cloud_provider: str
    installed_packages: tuple[str, ...]
    enabled_repository_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Workspace:
    """An Inventory workspace and its host membership."""

    id: str
    name: str
    group_type: str
    host_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Tag:
    """A tag and the hosts to which it is attached."""

    namespace: str
    key: str
    value: str
    host_ids: tuple[str, ...]

    @property
    def qualified_name(self) -> str:
        """Return the Inventory API's namespace/key=value representation."""
        return f"{self.namespace}/{self.key}={self.value}"


@dataclass(frozen=True, slots=True)
class RepositoryReference:
    """A repository referenced by one or more system profiles."""

    id: str
    name: str
    url: str
    architecture: str
    content_type: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class CVE:
    """A vulnerability and the hosts affected by it."""

    id: str
    severity: str
    impact: int
    cvss_score: float
    known_exploit: bool
    advisory_available: bool
    public_date: datetime
    summary: str
    affected_host_ids: tuple[str, ...]
    affected_package_names: tuple[str, ...]
    rule_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AdvisorRule:
    """An Advisor recommendation and its affected hosts."""

    id: str
    description: str
    impact: int
    category: str
    reboot_required: bool
    playbook_available: bool
    affected_host_ids: tuple[str, ...]
    cve_ids: tuple[str, ...] = ()
    node_id: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogIndexes:
    """Immutable lookup tables derived from catalog relationships."""

    hosts_by_id: Mapping[str, Host]
    profiles_by_host_id: Mapping[str, SystemProfile]
    repositories_by_id: Mapping[str, RepositoryReference]
    cves_by_id: Mapping[str, CVE]
    rules_by_id: Mapping[str, AdvisorRule]
    workspaces_by_host_id: Mapping[str, tuple[Workspace, ...]]
    tags_by_host_id: Mapping[str, tuple[Tag, ...]]
    cves_by_host_id: Mapping[str, tuple[CVE, ...]]
    rules_by_host_id: Mapping[str, tuple[AdvisorRule, ...]]


def _group_by_host(
    entities: Iterable[_Entity],
    members: Callable[[_Entity], Iterable[str]],
    host_ids: Iterable[str],
) -> Mapping[str, tuple[_Entity, ...]]:
    """Build an immutable inverse index for an entity-to-host relationship."""
    grouped: dict[str, list[_Entity]] = {host_id: [] for host_id in host_ids}
    for entity in entities:
        for host_id in members(entity):
            grouped.setdefault(host_id, []).append(entity)
    return MappingProxyType({host_id: tuple(items) for host_id, items in grouped.items()})


def _build_index(entities: Iterable[_Entity], key: Callable[[_Entity], str]) -> Mapping[str, _Entity]:
    """Build an immutable lookup index for route execution."""
    return MappingProxyType({key(entity): entity for entity in entities})


def build_catalog_indexes(catalog: MockCatalog) -> CatalogIndexes:  # pylint: disable=too-many-locals
    """Build all derived lookup tables for route execution."""
    hosts_by_id = _build_index(catalog.hosts, lambda host: host.id)
    repositories_by_id = _build_index(catalog.repositories, lambda repository: repository.id)
    cves_by_id = _build_index(catalog.cves, lambda cve: cve.id)
    rules_by_id = _build_index(catalog.advisor_rules, lambda rule: rule.id)
    profiles_by_host_id = _build_index(catalog.system_profiles, lambda profile: profile.host_id)

    host_ids = hosts_by_id.keys()
    indexes = CatalogIndexes(
        hosts_by_id=hosts_by_id,
        profiles_by_host_id=profiles_by_host_id,
        repositories_by_id=repositories_by_id,
        cves_by_id=cves_by_id,
        rules_by_id=rules_by_id,
        workspaces_by_host_id=_group_by_host(catalog.workspaces, lambda workspace: workspace.host_ids, host_ids),
        tags_by_host_id=_group_by_host(catalog.tags, lambda tag: tag.host_ids, host_ids),
        cves_by_host_id=_group_by_host(catalog.cves, lambda cve: cve.affected_host_ids, host_ids),
        rules_by_host_id=_group_by_host(catalog.advisor_rules, lambda rule: rule.affected_host_ids, host_ids),
    )
    return indexes


@dataclass(frozen=True, slots=True)
class MockCatalog:
    """Canonical data shared by mock API routes."""

    hosts: tuple[Host, ...]
    system_profiles: tuple[SystemProfile, ...]
    workspaces: tuple[Workspace, ...]
    tags: tuple[Tag, ...]
    repositories: tuple[RepositoryReference, ...]
    cves: tuple[CVE, ...]
    advisor_rules: tuple[AdvisorRule, ...]
    reference_time: datetime
    rbac_username: str
    _indexes: CatalogIndexes = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Build immutable relationship indexes for route execution."""
        object.__setattr__(self, "_indexes", build_catalog_indexes(self))

    def host(self, host_id: str) -> Host:
        """Return a host by ID, raising ``KeyError`` for an unknown ID."""
        return self._indexes.hosts_by_id[host_id]

    def profile_for_host(self, host_id: str) -> SystemProfile:
        """Return the system profile for a host."""
        return self._indexes.profiles_by_host_id[host_id]

    def workspaces_for_host(self, host_id: str) -> tuple[Workspace, ...]:
        """Return all workspaces containing a host."""
        return self._indexes.workspaces_by_host_id[host_id]

    def tags_for_host(self, host_id: str) -> tuple[Tag, ...]:
        """Return all tags attached to a host."""
        return self._indexes.tags_by_host_id[host_id]

    def cves_for_host(self, host_id: str) -> tuple[CVE, ...]:
        """Return all CVEs affecting a host."""
        return self._indexes.cves_by_host_id[host_id]

    def rules_for_host(self, host_id: str) -> tuple[AdvisorRule, ...]:
        """Return all Advisor rules affecting a host."""
        return self._indexes.rules_by_host_id[host_id]

    def hosts_for_cve(self, cve_id: str) -> tuple[Host, ...]:
        """Return all hosts affected by a CVE."""
        cve = self._indexes.cves_by_id[cve_id]
        return tuple(self.host(host_id) for host_id in cve.affected_host_ids)

    def hosts_for_rule(self, rule_id: str) -> tuple[Host, ...]:
        """Return all hosts affected by an Advisor rule."""
        rule = self._indexes.rules_by_id[rule_id]
        return tuple(self.host(host_id) for host_id in rule.affected_host_ids)

    def workspaces_named(self, name: str) -> tuple[Workspace, ...]:
        """Return workspaces with a matching name."""
        return tuple(workspace for workspace in self.workspaces if workspace.name == name)

    def repositories_for_host(self, host_id: str) -> tuple[RepositoryReference, ...]:
        """Return repositories enabled in a host's system profile."""
        profile = self.profile_for_host(host_id)
        return tuple(
            self._indexes.repositories_by_id[repository_id] for repository_id in profile.enabled_repository_ids
        )
