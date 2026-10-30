"""Test suite for the OCP Advisor get_recommendations() tool."""

import json
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import pytest

from insights_mcp.errors import InsightsApiError
from ocp_advisor_mcp.server import get_recommendations

CLUSTER_ID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture(name="report_response")
def fixture_report_response() -> dict[str, Any]:
    """Sample /cluster/{id}/reports response from the smart proxy."""
    report = _sample_report()
    return {"report": report, "status": "ok"}


def _sample_report() -> dict[str, Any]:
    """Inner report payload as wrapped by the smart proxy ``report`` key."""
    return {
        "meta": {
            "cluster_name": "prod-cluster",
            "count": 1,
            "last_checked_at": "2025-09-30T14:00:00Z",
        },
        "data": [
            {
                "rule_id": "nodes_requirements_check|NODES_MINIMUM_REQUIREMENTS_NOT_MET",
                "description": "Minimum cluster requirements not met",
                "reason": "Cluster {{=pydata.cluster_name}} has {{=pydata.nodes}} ready nodes.",
                "resolution": "Scale the cluster {{=pydata.cluster_name}} up.",
                "more_info": "",
                "total_risk": 3,
                "impacted": "2025-09-30T14:00:00Z",
                "disabled": False,
                "details": "Static prose, not template data.",
                "extra_data": {"cluster_name": "prod-cluster", "nodes": 2},
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_recommendations_calls_reports_endpoint(
    ocp_advisor_mock_client: Mock,
    report_response: dict[str, Any],
) -> None:
    """get_recommendations calls /cluster/{id}/reports and renders rule hits."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"cluster/{CLUSTER_ID}/reports",
        response_body=report_response,
    )

    result = await get_recommendations(cluster_id=UUID(CLUSTER_ID))

    ocp_advisor_mock_client.get.assert_called_once_with(
        f"cluster/{CLUSTER_ID}/reports", params=None
    )
    payload = json.loads(result)
    hit = payload["report"]["data"][0]
    assert hit["reason"] == "Cluster prod-cluster has 2 ready nodes."
    assert hit["resolution"] == "Scale the cluster prod-cluster up."
    assert hit["rendering"] == {"status": "ok"}
    # identifiers and metadata are retained
    assert hit["rule_id"] == "nodes_requirements_check|NODES_MINIMUM_REQUIREMENTS_NOT_MET"
    assert hit["total_risk"] == 3
    assert payload["report"]["meta"]["cluster_name"] == "prod-cluster"


@pytest.mark.asyncio
async def test_get_recommendations_include_disabled(
    ocp_advisor_mock_client: Mock,
) -> None:
    """include_disabled=true is forwarded as the get_disabled query parameter."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"cluster/{CLUSTER_ID}/reports",
        response_body={"report": {"meta": {"count": 0}, "data": []}, "status": "ok"},
    )

    await get_recommendations(cluster_id=UUID(CLUSTER_ID), include_disabled=True)

    ocp_advisor_mock_client.get.assert_called_once_with(
        f"cluster/{CLUSTER_ID}/reports", params={"get_disabled": "true"}
    )


@pytest.mark.asyncio
async def test_get_recommendations_rendering_failure_is_explicit(
    ocp_advisor_mock_client: Mock,
    report_response: dict[str, Any],
) -> None:
    """A rendering failure keeps the unresolved template and is clearly marked."""
    report_response["report"]["data"][0]["reason"] = "Node {{=pydata.missing.value()}} is not ready"
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"cluster/{CLUSTER_ID}/reports",
        response_body=report_response,
    )

    result = await get_recommendations(cluster_id=UUID(CLUSTER_ID))

    hit = json.loads(result)["report"]["data"][0]
    assert hit["reason"] == "Node {{=pydata.missing.value()}} is not ready"
    assert hit["rendering"]["status"] == "failed"
    assert "reason" in hit["rendering"]["errors"]
    # successfully rendered fields are still substituted
    assert hit["resolution"] == "Scale the cluster prod-cluster up."


@pytest.mark.asyncio
async def test_get_recommendations_golden_template_renders(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Templates captured from the live smart proxy render with real-world constructs.

    Regression test for the rendering pipeline against production rule content:
    nested loops with per-item conditionals (``version["eus_date"] != null``),
    truthiness branches, and string methods on ``pydata`` values
    (``cluster_version.split(\".", 2).join(\".")``).
    """
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"cluster/{CLUSTER_ID}/reports",
        response_body={
            "report": {
                "meta": {"cluster_name": "golden", "count": 2},
                "data": [
                    {
                        "rule_id": "ccx_rules_ocp.external.rules.ocp_version_end_of_life.report",
                        "reason": (
                            "The running OpenShift version has reached its End of Life.\n"
                            "  * Cluster version: {{=pydata.current_version}}\n"
                        ),
                        "resolution": (
                            "Currently supported OpenShift versions are:\n"
                            "{{~ pydata.supported_versions :version }}"
                            "- **{{=version[\"name\"]}}**\n"
                            "  - Maintenance Support end: {{=version[\"maintenance_end_date\"]}}"
                            "{{? version[\"eus_date\"] != null }}"
                            "\n  - Extended Update Support end: {{=version[\"eus_date\"]}}"
                            "{{?}}\n"
                            "{{~}}"
                        ),
                        "more_info": "",
                        "total_risk": 2,
                        "extra_data": {
                            "current_version": "4.18.0",
                            "supported_versions": [
                                {
                                    "name": "4.19",
                                    "maintenance_end_date": "2026-12-17",
                                    "eus_date": None,
                                },
                                {
                                    "name": "4.20",
                                    "maintenance_end_date": "2027-04-21",
                                    "eus_date": "2027-10-21",
                                },
                            ],
                        },
                    },
                    {
                        "rule_id": "ccx_rules_ocp.external.security.CVE_GOLDEN.report",
                        "reason": "This cluster is running OCP {{=pydata.cluster_version}}.",
                        "resolution": (
                            "[upgrade](.../{{=pydata.cluster_version.split('.', 2).join('.')}}"
                            "/html/updating_clusters/index) your cluster to {{=pydata.fixed_version}}"
                        ),
                        "more_info": "",
                        "total_risk": 3,
                        "extra_data": {
                            "cluster_version": "4.18.0",
                            "fixed_version": "4.18.40",
                        },
                    },
                ],
            },
            "status": "ok",
        },
    )

    result = await get_recommendations(cluster_id=UUID(CLUSTER_ID))

    hits = json.loads(result)["report"]["data"]
    assert all(hit["rendering"] == {"status": "ok"} for hit in hits)
    eol_resolution = hits[0]["resolution"]
    # loop with per-item conditionals: EUS line only for versions with eus_date
    assert "- **4.19**\n  - Maintenance Support end: 2026-12-17\n" in eol_resolution
    assert "- **4.20**\n  - Maintenance Support end: 2027-04-21\n" in eol_resolution
    assert "  - Extended Update Support end: 2027-10-21" in eol_resolution
    assert "eus" not in eol_resolution.split("**4.19**")[1].split("**4.20**")[0]
    # string methods on pydata values
    assert "Cluster version: 4.18.0" in hits[0]["reason"]
    assert ".../4.18/html/updating_clusters/index" in hits[1]["resolution"]
    assert "your cluster to 4.18.40" in hits[1]["resolution"]


@pytest.mark.asyncio
async def test_get_recommendations_empty_report(
    ocp_advisor_mock_client: Mock,
) -> None:
    """A report with no findings is returned as an explicit empty result."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"cluster/{CLUSTER_ID}/reports",
        response_body={"report": {"meta": {"cluster_name": "prod-cluster", "count": 0}, "data": []}, "status": "ok"},
    )

    result = await get_recommendations(cluster_id=UUID(CLUSTER_ID))

    payload = json.loads(result)
    assert payload["report"]["meta"]["count"] == 0
    assert payload["report"]["data"] == []


@pytest.mark.asyncio
async def test_get_recommendations_maps_request_errors(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Request failures raise InsightsApiError with a cluster-specific message."""
    ocp_advisor_mock_client.get.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(
        InsightsApiError,
        match=f"Error retrieving recommendations for cluster {CLUSTER_ID}",
    ):
        await get_recommendations(cluster_id=UUID(CLUSTER_ID))
