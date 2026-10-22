"""Deterministic synthetic entities used by the LLM-test API catalog."""

from datetime import datetime, timedelta, timezone

from tests.mock_insights_api.catalog.models import (
    CVE,
    AdvisorRule,
    Host,
    MockCatalog,
    RepositoryReference,
    SystemProfile,
    Tag,
    Workspace,
)

FIXTURE_NOW = datetime.now(timezone.utc)

HOST_PRODUCTION_DB = "11111111-1111-4111-8111-111111111111"
HOST_PRODUCTION_WEB = "22222222-2222-4222-8222-222222222222"
HOST_LEGACY = "33333333-3333-4333-8333-333333333333"
HOST_DEVELOPMENT = "44444444-4444-4444-8444-444444444444"

CVE_KERNEL = "CVE-2025-12345"
CVE_OPENSSL = "CVE-2025-23456"
CVE_PYTHON = "CVE-2024-34567"

RULE_KERNEL = "kernel_security|KERNEL_SECURITY_UPDATE"
RULE_THP = "thp_disabled|DISABLE_THP"
RULE_OPENSSL = "openssl_outdated|OPENSSL_OUTDATED"


DEFAULT_CATALOG = MockCatalog(
    hosts=(
        Host(
            id=HOST_PRODUCTION_DB,
            hostname="db-prod-01",
            fqdn="db-prod-01.example.com",
            rhel_version="9.4",
            last_seen=FIXTURE_NOW - timedelta(hours=2),
            updated=FIXTURE_NOW - timedelta(hours=1),
            provider_type="aws",
            registered_with="insights-client",
        ),
        Host(
            id=HOST_PRODUCTION_WEB,
            hostname="web-prod-01",
            fqdn="web-prod-01.example.com",
            rhel_version="9.2",
            last_seen=FIXTURE_NOW - timedelta(hours=18),
            updated=FIXTURE_NOW - timedelta(hours=8),
            provider_type="bare-metal",
            registered_with="insights-client",
        ),
        Host(
            id=HOST_LEGACY,
            hostname="legacy-rhel8-01",
            fqdn="legacy-rhel8-01.example.com",
            rhel_version="8.8",
            last_seen=FIXTURE_NOW - timedelta(days=3),
            updated=FIXTURE_NOW - timedelta(days=3),
            provider_type="aws",
            registered_with="insights-client",
        ),
        Host(
            id=HOST_DEVELOPMENT,
            hostname="dev-rhel10-01",
            fqdn="dev-rhel10-01.example.com",
            rhel_version="10.1",
            last_seen=FIXTURE_NOW - timedelta(days=2),
            updated=FIXTURE_NOW - timedelta(days=2),
            provider_type="azure",
            registered_with="insights-client",
        ),
    ),
    system_profiles=(
        SystemProfile(
            host_id=HOST_PRODUCTION_DB,
            os_name="Red Hat Enterprise Linux",
            architecture="x86_64",
            memory_bytes=32 * 1024**3,
            cloud_provider="aws",
            installed_packages=("kernel", "openssl-libs", "postgresql-server"),
            enabled_repository_ids=("rhel-9-for-x86_64-baseos-rpms", "rhel-9-for-x86_64-appstream-rpms"),
        ),
        SystemProfile(
            host_id=HOST_PRODUCTION_WEB,
            os_name="Red Hat Enterprise Linux",
            architecture="x86_64",
            memory_bytes=64 * 1024**3,
            cloud_provider="bare-metal",
            installed_packages=("kernel", "openssl-libs", "httpd", "python312"),
            enabled_repository_ids=("rhel-9-for-x86_64-baseos-rpms", "rhel-9-for-x86_64-appstream-rpms"),
        ),
        SystemProfile(
            host_id=HOST_LEGACY,
            os_name="Red Hat Enterprise Linux",
            architecture="x86_64",
            memory_bytes=16 * 1024**3,
            cloud_provider="aws",
            installed_packages=("kernel", "openssl-libs", "python39"),
            enabled_repository_ids=("rhel-8-for-x86_64-baseos-rpms",),
        ),
        SystemProfile(
            host_id=HOST_DEVELOPMENT,
            os_name="Red Hat Enterprise Linux",
            architecture="aarch64",
            memory_bytes=8 * 1024**3,
            cloud_provider="azure",
            installed_packages=("kernel", "openssl-libs", "python312"),
            enabled_repository_ids=("rhel-10-for-aarch64-baseos-rpms",),
        ),
    ),
    workspaces=(
        Workspace(
            id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            name="Production",
            group_type="standard",
            host_ids=(HOST_PRODUCTION_DB, HOST_PRODUCTION_WEB),
        ),
        Workspace(
            id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            name="Security",
            group_type="standard",
            host_ids=(HOST_PRODUCTION_DB, HOST_LEGACY),
        ),
        Workspace(
            id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            name="Ungrouped Hosts",
            group_type="ungrouped-hosts",
            host_ids=(HOST_DEVELOPMENT,),
        ),
    ),
    tags=(
        Tag(
            namespace="insights-client",
            key="security",
            value="strict",
            host_ids=(HOST_PRODUCTION_DB, HOST_LEGACY),
        ),
        Tag(
            namespace="insights-client",
            key="environment",
            value="production",
            host_ids=(HOST_PRODUCTION_DB, HOST_PRODUCTION_WEB),
        ),
        Tag(
            namespace="insights-client",
            key="role",
            value="database",
            host_ids=(HOST_PRODUCTION_DB,),
        ),
    ),
    repositories=(
        RepositoryReference(
            id="rhel-9-for-x86_64-baseos-rpms",
            name="Red Hat Enterprise Linux 9 for x86_64 - BaseOS (RPMs)",
            url="https://cdn.redhat.com/content/dist/rhel9/9/x86_64/baseos/os",
            architecture="x86_64",
            content_type="rpm",
            enabled=True,
        ),
        RepositoryReference(
            id="rhel-9-for-x86_64-appstream-rpms",
            name="Red Hat Enterprise Linux 9 for x86_64 - AppStream (RPMs)",
            url="https://cdn.redhat.com/content/dist/rhel9/9/x86_64/appstream/os",
            architecture="x86_64",
            content_type="rpm",
            enabled=True,
        ),
        RepositoryReference(
            id="rhel-8-for-x86_64-baseos-rpms",
            name="Red Hat Enterprise Linux 8 for x86_64 - BaseOS (RPMs)",
            url="https://cdn.redhat.com/content/dist/rhel8/8/x86_64/baseos/os",
            architecture="x86_64",
            content_type="rpm",
            enabled=True,
        ),
        RepositoryReference(
            id="rhel-10-for-aarch64-baseos-rpms",
            name="Red Hat Enterprise Linux 10 for ARM 64 - BaseOS (RPMs)",
            url="https://cdn.redhat.com/content/dist/rhel10/10/aarch64/baseos/os",
            architecture="aarch64",
            content_type="rpm",
            enabled=True,
        ),
    ),
    cves=(
        CVE(
            id=CVE_KERNEL,
            severity="Critical",
            impact=7,
            cvss_score=9.8,
            known_exploit=True,
            advisory_available=True,
            public_date=datetime(2025, 1, 15, tzinfo=timezone.utc),
            summary="A kernel vulnerability allows privilege escalation on affected systems.",
            affected_host_ids=(HOST_PRODUCTION_DB, HOST_LEGACY),
            affected_package_names=("kernel",),
            rule_ids=(RULE_KERNEL,),
        ),
        CVE(
            id=CVE_OPENSSL,
            severity="Important",
            impact=5,
            cvss_score=7.5,
            known_exploit=False,
            advisory_available=True,
            public_date=datetime(2025, 3, 2, tzinfo=timezone.utc),
            summary="An OpenSSL vulnerability affects systems with an outdated openssl-libs package.",
            affected_host_ids=(HOST_PRODUCTION_DB, HOST_PRODUCTION_WEB),
            affected_package_names=("openssl-libs",),
            rule_ids=(RULE_OPENSSL,),
        ),
        CVE(
            id=CVE_PYTHON,
            severity="Moderate",
            impact=4,
            cvss_score=5.3,
            known_exploit=False,
            advisory_available=False,
            public_date=datetime(2024, 11, 8, tzinfo=timezone.utc),
            summary="A Python package issue requires manual remediation on affected systems.",
            affected_host_ids=(HOST_PRODUCTION_WEB, HOST_DEVELOPMENT),
            affected_package_names=("python312",),
        ),
    ),
    advisor_rules=(
        AdvisorRule(
            id=RULE_KERNEL,
            description="Update the kernel package to address a critical security issue.",
            impact=3,
            category="Security",
            reboot_required=True,
            playbook_available=True,
            affected_host_ids=(HOST_PRODUCTION_DB, HOST_LEGACY),
            cve_ids=(CVE_KERNEL,),
        ),
        AdvisorRule(
            id=RULE_THP,
            description="Disable Transparent Huge Pages for database workloads.",
            impact=2,
            category="Performance",
            reboot_required=True,
            playbook_available=True,
            affected_host_ids=(HOST_PRODUCTION_DB,),
        ),
        AdvisorRule(
            id=RULE_OPENSSL,
            description="Update openssl-libs to the latest supported release.",
            impact=2,
            category="Security",
            reboot_required=False,
            playbook_available=True,
            affected_host_ids=(HOST_PRODUCTION_DB, HOST_PRODUCTION_WEB),
            cve_ids=(CVE_OPENSSL,),
        ),
    ),
    reference_time=FIXTURE_NOW,
    rbac_username="service-account-mock-llm",
)
