"""Typed entities and relationship indexes for the LLM-test API catalog."""

# The catalog entities intentionally mirror several fields from their API resources.
# pylint: disable=too-many-instance-attributes

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, TypeVar

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
    installed_app_streams: tuple[str, ...] = ()


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
class ContentSourceRepository:
    """A Content Sources repository and its introspection details."""

    id: str
    name: str
    label: str
    url: str
    origin: str
    content_type: str
    distribution_versions: tuple[str, ...]
    distribution_arch: str
    package_count: int
    build_count: int
    version_count: int
    status: str
    enabled: bool
    gpg_key: str
    last_introspection_time: str | None
    last_success_introspection_time: str | None
    last_update_introspection_time: str | None
    last_introspection_error: str | None
    metadata_verification: bool
    snapshots: tuple[Mapping[str, Any], ...] = ()
    repository_reference_id: str | None = None


@dataclass(frozen=True, slots=True)
class ActivationKey:
    """An RHSM activation key available to the test account."""

    id: str
    name: str
    description: str
    service_level: str
    role: str
    usage: str
    release_version: str
    subscriptions: tuple[Mapping[str, Any], ...]
    additional_repositories: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OCPAdvisorCluster:
    """An OpenShift cluster summary returned by OCP Advisor."""

    cluster_id: str
    cluster_name: str
    total_hits: int
    hits_by_total_risk: Mapping[str, int]
    managed: bool
    cluster_version: str
    last_checked_at: str
    upgrade_recommended: bool = True
    upgrade_risks_predictors: Mapping[str, Any] = field(
        default_factory=lambda: {"alerts": [], "operator_conditions": []}
    )


@dataclass(frozen=True, slots=True)
class OCPAdvisorRule:
    """An OCP Advisor rule and the clusters it affects."""

    id: str
    description: str
    generic: str
    reason: str
    resolution: str
    more_info: str
    total_risk: int
    impact: int
    likelihood: int
    resolution_risk: int
    publish_date: str
    tags: tuple[str, ...]
    affected_cluster_ids: tuple[str, ...]
    groups: tuple[Mapping[str, Any], ...] = ()
    disabled: bool = False


@dataclass(frozen=True, slots=True)
class RBACRole:
    """A console role and the v1 permissions it grants."""

    name: str
    display_name: str
    permissions: tuple[str, ...]


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
class ImageBlueprint:
    """An Image Builder blueprint and its latest version."""

    id: str
    name: str
    description: str
    distribution: str
    version: int
    last_modified_at: str
    image_requests: tuple[Mapping[str, Any], ...]
    customizations: Mapping[str, Any]
    lint: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ImageCompose:
    """An Image Builder compose and its status."""

    id: str
    blueprint_id: str
    image_name: str
    created_at: str
    request: Mapping[str, Any]
    image_status: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ImageDistribution:
    """An Image Builder distribution available to the test account."""

    name: str
    description: str


@dataclass(frozen=True, slots=True)
class RHELLifecycleRecord:
    """A RHEL version and its lifecycle dates."""

    major: int
    minor: int | None
    start_date: str
    end_date: str
    support_status: str
    display_name: str
    name: str = "RHEL"
    end_date_e4s: str | None = None
    end_date_els: str | None = None
    end_date_eus: str | None = None


@dataclass(frozen=True, slots=True)
class ApplicationStreamRecord:
    """An Application Stream lifecycle record."""

    name: str
    stream: str
    display_name: str
    application_stream_name: str
    application_stream_type: str | None
    start_date: str | None
    end_date: str | None
    impl: str
    initial_product_version: str | None
    support_status: str
    os_major: int | None
    os_minor: int | None
    lifecycle: int | None = None
    rolling: bool = False


@dataclass(frozen=True, slots=True)
class UpcomingChange:
    """A roadmap change that can be matched to installed host data."""

    name: str
    change_type: str
    packages: tuple[str, ...]
    release: str
    os_major: int
    date: str
    summary: str
    training_ticket: str
    date_added: str
    last_modified: str
    architecture: str | None = None
    deployed_date: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogIndexes:
    """Immutable lookup tables derived from catalog relationships."""

    hosts_by_id: Mapping[str, Host]
    profiles_by_host_id: Mapping[str, SystemProfile]
    repositories_by_id: Mapping[str, RepositoryReference]
    cves_by_id: Mapping[str, CVE]
    rules_by_id: Mapping[str, AdvisorRule]
    ocp_advisor_clusters_by_id: Mapping[str, OCPAdvisorCluster]
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
    ocp_advisor_clusters_by_id = _build_index(catalog.ocp_advisor_clusters, lambda cluster: cluster.cluster_id)
    profiles_by_host_id = _build_index(catalog.system_profiles, lambda profile: profile.host_id)

    host_ids = hosts_by_id.keys()
    indexes = CatalogIndexes(
        hosts_by_id=hosts_by_id,
        profiles_by_host_id=profiles_by_host_id,
        repositories_by_id=repositories_by_id,
        cves_by_id=cves_by_id,
        rules_by_id=rules_by_id,
        ocp_advisor_clusters_by_id=ocp_advisor_clusters_by_id,
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
    rhel_lifecycle: tuple[RHELLifecycleRecord, ...] = ()
    application_streams: tuple[ApplicationStreamRecord, ...] = ()
    upcoming_changes: tuple[UpcomingChange, ...] = ()
    image_blueprints: tuple[ImageBlueprint, ...] = ()
    image_composes: tuple[ImageCompose, ...] = ()
    image_distributions: tuple[ImageDistribution, ...] = ()
    content_source_repositories: tuple[ContentSourceRepository, ...] = ()
    activation_keys: tuple[ActivationKey, ...] = ()
    ocp_advisor_info: Mapping[str, Any] = field(default_factory=dict)
    ocp_advisor_clusters: tuple[OCPAdvisorCluster, ...] = ()
    ocp_advisor_rules: tuple[OCPAdvisorRule, ...] = ()
    rbac_roles: tuple[RBACRole, ...] = ()
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

    def ocp_advisor_cluster(self, cluster_id: str) -> OCPAdvisorCluster:
        """Return an OCP Advisor cluster by ID."""
        return self._indexes.ocp_advisor_clusters_by_id[cluster_id]
