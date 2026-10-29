"""Service-specific entities used by the LLM-test API catalog."""

from datetime import datetime, timedelta

from tests.mock_insights_api.catalog.models import ActivationKey, OCPAdvisorCluster, OCPAdvisorRule, RBACRole

ACTIVATION_KEYS = (
    ActivationKey(
        id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        name="production-rhel9",
        description="Production registration key for RHEL 9 systems.",
        service_level="Self-Support",
        role="Red Hat Enterprise Linux Server",
        usage="Production",
        release_version="9",
        subscriptions=({"name": "Red Hat Enterprise Linux Server", "quantity": 25},),
        additional_repositories=(
            "rhel-9-for-x86_64-baseos-rpms",
            "rhel-9-for-x86_64-appstream-rpms",
        ),
    ),
    ActivationKey(
        id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        name="development-rhel10",
        description="Development registration key for RHEL 10 systems.",
        service_level="Self-Support",
        role="Red Hat Enterprise Linux Server",
        usage="Development",
        release_version="10",
        subscriptions=({"name": "Red Hat Enterprise Linux Server", "quantity": 10},),
        additional_repositories=("rhel-10-for-aarch64-baseos-rpms",),
    ),
)


def _timestamp(reference_time: datetime, hours_from_now: int = 0) -> str:
    return (reference_time + timedelta(hours=hours_from_now)).isoformat().replace("+00:00", "Z")


OCP_CLUSTER_PRODUCTION = "11111111-2222-3333-4444-555555555555"
OCP_CLUSTER_DEVELOPMENT = "22222222-3333-4444-5555-666666666666"


OCP_ADVISOR_RULES = (
    OCPAdvisorRule(
        id="ccx_rules_ocp.external.rules.example.report|EXAMPLE_WARNING",
        description="An example warning recommendation affects the production cluster.",
        generic="The production cluster has an example warning condition.",
        reason="The example warning condition was reported by the OpenShift cluster.",
        resolution="Review the condition and apply the recommended OpenShift configuration change.",
        more_info="https://access.redhat.com/solutions/ocp-example-warning",
        total_risk=3,
        impact=2,
        likelihood=4,
        resolution_risk=1,
        publish_date="2026-10-20T12:00:00Z",
        tags=("openshift", "service_availability"),
        affected_cluster_ids=(OCP_CLUSTER_PRODUCTION,),
        groups=(
            {
                "title": "Availability",
                "description": "Availability recommendations",
                "tags": ["service_availability"],
            },
        ),
    ),
    OCPAdvisorRule(
        id="ccx_rules_ocp.external.rules.example.report|EXAMPLE_CRITICAL",
        description="An example critical recommendation affects the development cluster.",
        generic="The development cluster has an example critical condition.",
        reason="The example critical condition was reported by the OpenShift cluster.",
        resolution="Resolve the degraded cluster condition before continuing maintenance.",
        more_info="https://access.redhat.com/solutions/ocp-example-critical",
        total_risk=4,
        impact=4,
        likelihood=4,
        resolution_risk=4,
        publish_date="2026-10-21T12:00:00Z",
        tags=("openshift", "cluster_health"),
        affected_cluster_ids=(OCP_CLUSTER_DEVELOPMENT,),
        groups=(
            {
                "title": "Stability",
                "description": "Cluster stability recommendations",
                "tags": ["cluster_health"],
            },
        ),
    ),
)


def build_ocp_advisor_info(reference_time: datetime) -> dict[str, object]:
    """Build an OCP Advisor info response relative to the catalog clock."""
    build_time = _timestamp(reference_time)
    return {
        "info": {
            "SmartProxy": {
                "BuildBranch": "main",
                "BuildCommit": "mock-smart-proxy-commit",
                "BuildTime": build_time,
                "BuildVersion": "mock-smart-proxy-1.0.0",
                "UtilsVersion": "mock-utils-1.0.0",
                "status": "ok",
            },
            "Aggregator": {
                "BuildBranch": "main",
                "BuildCommit": "mock-aggregator-commit",
                "BuildTime": build_time,
                "BuildVersion": "mock-aggregator-1.0.0",
                "DB_version": "mock-db-1",
                "UtilsVersion": "mock-utils-1.0.0",
                "status": "ok",
            },
            "ContentService": {
                "BuildBranch": "main",
                "BuildCommit": "mock-content-service-commit",
                "BuildTime": build_time,
                "BuildVersion": "ccx-ocp-rules-2026.10.0",
                "UtilsVersion": "mock-utils-1.0.0",
                "status": "ok",
            },
        },
        "status": "ok",
    }


def build_ocp_advisor_clusters(reference_time: datetime) -> tuple[OCPAdvisorCluster, ...]:
    """Build OCP Advisor cluster summaries relative to the catalog clock."""
    return (
        OCPAdvisorCluster(
            cluster_id=OCP_CLUSTER_PRODUCTION,
            cluster_name="production-cluster",
            total_hits=1,
            hits_by_total_risk={"1": 0, "2": 0, "3": 1, "4": 0},
            managed=False,
            cluster_version="4.16.18",
            last_checked_at=_timestamp(reference_time, -1),
            upgrade_recommended=False,
            upgrade_risks_predictors={
                "alerts": [
                    {
                        "name": "ClusterVersionOperatorDegraded",
                        "namespace": "openshift-cluster-version",
                        "severity": "warning",
                        "url": "https://console.example/alerts/ClusterVersionOperatorDegraded",
                    }
                ],
                "operator_conditions": [
                    {
                        "name": "authentication",
                        "condition": "Degraded",
                        "reason": "ExampleCondition",
                        "url": "https://console.example/operators/authentication",
                    }
                ],
            },
        ),
        OCPAdvisorCluster(
            cluster_id=OCP_CLUSTER_DEVELOPMENT,
            cluster_name="development-cluster",
            total_hits=1,
            hits_by_total_risk={"1": 0, "2": 0, "3": 0, "4": 1},
            managed=True,
            cluster_version="4.17.6",
            last_checked_at=_timestamp(reference_time, -12),
            upgrade_recommended=True,
        ),
    )


RBAC_ROLES = (
    RBACRole(
        name="insights-mcp-viewer",
        display_name="Insights MCP viewer",
        permissions=(
            "inventory:hosts:read",
            "content-sources:repositories:read",
            "config-manager:activation_keys:read",
            "ocp-advisor:recommendation-results:read",
        ),
    ),
    RBACRole(
        name="vulnerability-viewer",
        display_name="Vulnerability viewer",
        permissions=("vulnerability:vulnerability_results:read",),
    ),
    RBACRole(
        name="advisor-viewer",
        display_name="RHEL Advisor viewer",
        permissions=("advisor:*:read",),
    ),
)
