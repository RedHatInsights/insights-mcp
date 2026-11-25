"""Unit tests for mock catalog integrity checks."""

from dataclasses import replace

import pytest

from tests.mock_insights_api.catalog import DEFAULT_CATALOG, CatalogValidationError, validate_catalog
from tests.mock_insights_api.catalog.models import MockCatalog


def _assert_invalid(catalog: MockCatalog, message: str) -> None:
    with pytest.raises(CatalogValidationError, match=message):
        validate_catalog(catalog)


def test_default_catalog_is_valid() -> None:
    validate_catalog(DEFAULT_CATALOG)


def test_rejects_empty_host_id() -> None:
    host = replace(DEFAULT_CATALOG.hosts[0], id="")
    catalog = replace(DEFAULT_CATALOG, hosts=(host, *DEFAULT_CATALOG.hosts[1:]))

    _assert_invalid(catalog, "host IDs must not be empty")


def test_rejects_duplicate_host_id() -> None:
    duplicate = replace(DEFAULT_CATALOG.hosts[1], id=DEFAULT_CATALOG.hosts[0].id)
    catalog = replace(DEFAULT_CATALOG, hosts=(DEFAULT_CATALOG.hosts[0], duplicate, *DEFAULT_CATALOG.hosts[2:]))

    _assert_invalid(catalog, "Duplicate host ID")


def test_rejects_unknown_profile_host() -> None:
    profile = replace(DEFAULT_CATALOG.system_profiles[0], host_id="missing-host")
    catalog = replace(DEFAULT_CATALOG, system_profiles=(profile, *DEFAULT_CATALOG.system_profiles[1:]))

    _assert_invalid(catalog, "Unknown host reference")


def test_rejects_missing_profile() -> None:
    missing_host_id = DEFAULT_CATALOG.system_profiles[0].host_id
    profiles = tuple(profile for profile in DEFAULT_CATALOG.system_profiles if profile.host_id != missing_host_id)
    catalog = replace(DEFAULT_CATALOG, system_profiles=profiles)

    _assert_invalid(catalog, "Missing system profile")


def test_rejects_unknown_profile_repository() -> None:
    profile = replace(DEFAULT_CATALOG.system_profiles[0], enabled_repository_ids=("missing-repository",))
    catalog = replace(DEFAULT_CATALOG, system_profiles=(profile, *DEFAULT_CATALOG.system_profiles[1:]))

    _assert_invalid(catalog, "Unknown repository reference")


def test_rejects_unknown_content_source_repository() -> None:
    repository = replace(DEFAULT_CATALOG.content_source_repositories[0], repository_reference_id="missing-repository")
    catalog = replace(
        DEFAULT_CATALOG,
        content_source_repositories=(repository, *DEFAULT_CATALOG.content_source_repositories[1:]),
    )

    _assert_invalid(catalog, "Unknown repository reference")


def test_rejects_unknown_workspace_host() -> None:
    workspace = replace(DEFAULT_CATALOG.workspaces[0], host_ids=("missing-host",))
    catalog = replace(DEFAULT_CATALOG, workspaces=(workspace, *DEFAULT_CATALOG.workspaces[1:]))

    _assert_invalid(catalog, "Unknown workspace host reference")


def test_rejects_unknown_tag_host() -> None:
    tag = replace(DEFAULT_CATALOG.tags[0], host_ids=("missing-host",))
    catalog = replace(DEFAULT_CATALOG, tags=(tag, *DEFAULT_CATALOG.tags[1:]))

    _assert_invalid(catalog, "Unknown tag host reference")


def test_rejects_unknown_cve_host() -> None:
    cve = replace(DEFAULT_CATALOG.cves[0], affected_host_ids=("missing-host",))
    catalog = replace(DEFAULT_CATALOG, cves=(cve, *DEFAULT_CATALOG.cves[1:]))

    _assert_invalid(catalog, "Unknown CVE host reference")


def test_rejects_unknown_cve_rule() -> None:
    cve = replace(DEFAULT_CATALOG.cves[0], rule_ids=("missing-rule",))
    catalog = replace(DEFAULT_CATALOG, cves=(cve, *DEFAULT_CATALOG.cves[1:]))

    _assert_invalid(catalog, "Unknown CVE rule reference")


def test_rejects_nonreciprocal_cve_rule_reference() -> None:
    rule = replace(DEFAULT_CATALOG.advisor_rules[0], cve_ids=())
    catalog = replace(
        DEFAULT_CATALOG,
        advisor_rules=(rule, *DEFAULT_CATALOG.advisor_rules[1:]),
    )

    _assert_invalid(catalog, "are not reciprocal")


def test_rejects_unknown_advisor_host() -> None:
    rule = replace(DEFAULT_CATALOG.advisor_rules[0], affected_host_ids=("missing-host",))
    catalog = replace(DEFAULT_CATALOG, advisor_rules=(rule, *DEFAULT_CATALOG.advisor_rules[1:]))

    _assert_invalid(catalog, "Unknown Advisor rule host reference")


def test_rejects_unknown_advisor_cve() -> None:
    rule = replace(DEFAULT_CATALOG.advisor_rules[1], cve_ids=("missing-cve",))
    catalog = replace(
        DEFAULT_CATALOG,
        advisor_rules=(DEFAULT_CATALOG.advisor_rules[0], rule, *DEFAULT_CATALOG.advisor_rules[2:]),
    )

    _assert_invalid(catalog, "Unknown Advisor rule CVE reference")


def test_rejects_nonreciprocal_advisor_cve_reference() -> None:
    cve = replace(DEFAULT_CATALOG.cves[0], rule_ids=())
    catalog = replace(DEFAULT_CATALOG, cves=(cve, *DEFAULT_CATALOG.cves[1:]))

    _assert_invalid(catalog, "are not reciprocal")


def test_rejects_unknown_ocp_advisor_cluster() -> None:
    rule = replace(DEFAULT_CATALOG.ocp_advisor_rules[0], affected_cluster_ids=("missing-cluster",))
    catalog = replace(DEFAULT_CATALOG, ocp_advisor_rules=(rule, *DEFAULT_CATALOG.ocp_advisor_rules[1:]))

    _assert_invalid(catalog, "Unknown OCP Advisor cluster reference")
