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
                "rule_id": "test_rule_check|TEST_ERROR_KEY",
                "description": "Test rule for testing",
                "reason": "Test cluster {{=pydata.cluster_name}} has {{=pydata.nodes}} test nodes.",
                "resolution": "Apply the test resolution to cluster {{=pydata.cluster_name}}.",
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

    ocp_advisor_mock_client.get.assert_called_once_with(f"cluster/{CLUSTER_ID}/reports", params=None)
    payload = json.loads(result)
    hit = payload["report"]["data"][0]
    assert hit["reason"] == "Test cluster prod-cluster has 2 test nodes."
    assert hit["resolution"] == "Apply the test resolution to cluster prod-cluster."
    assert hit["rendering"] == {"status": "ok"}
    # identifiers and metadata are retained
    assert hit["rule_id"] == "test_rule_check|TEST_ERROR_KEY"
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
    report_response["report"]["data"][0]["reason"] = "Test reason for {{=pydata.missing.value()}}"
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"cluster/{CLUSTER_ID}/reports",
        response_body=report_response,
    )

    result = await get_recommendations(cluster_id=UUID(CLUSTER_ID))

    hit = json.loads(result)["report"]["data"][0]
    assert hit["reason"] == "Test reason for {{=pydata.missing.value()}}"
    assert hit["rendering"]["status"] == "failed"
    assert "reason" in hit["rendering"]["errors"]
    # successfully rendered fields are still substituted
    assert hit["resolution"] == "Apply the test resolution to cluster prod-cluster."


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
