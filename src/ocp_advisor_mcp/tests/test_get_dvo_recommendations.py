"""Test suite for the OCP Advisor get_dvo_namespaces() and get_dvo_recommendations() tools."""

import json
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import pytest

from insights_mcp.errors import InsightsApiError
from ocp_advisor_mcp.server import get_dvo_namespaces, get_dvo_recommendations

CLUSTER_ID = "11111111-2222-3333-4444-555555555555"
NAMESPACE_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture(name="dvo_namespaces_response")
def fixture_dvo_namespaces_response() -> dict[str, Any]:
    """Sample /namespaces/dvo response from the smart proxy."""
    return {
        "status": "ok",
        "workloads": [
            {
                "cluster": {"uuid": CLUSTER_ID, "display_name": "prod-cluster"},
                "namespace": {"uuid": NAMESPACE_ID, "name": "test-namespace"},
                "metadata": {
                    "recommendations": 1,
                    "objects": 1,
                    "reported_at": "2025-09-30T14:00:00Z",
                    "last_checked_at": "2025-09-30T15:00:00Z",
                    "highest_severity": 3,
                    "hits_by_severity": {"3": 1},
                },
            }
        ],
    }


@pytest.fixture(name="dvo_recommendations_response")
def fixture_dvo_recommendations_response() -> dict[str, Any]:
    """Sample /namespaces/dvo/{ns}/cluster/{cluster} response from the smart proxy."""
    return {
        "status": "ok",
        "cluster": {"uuid": CLUSTER_ID, "display_name": "prod-cluster"},
        "namespace": {"uuid": NAMESPACE_ID, "name": "test-namespace"},
        "metadata": {"recommendations": 1, "highest_severity": 3},
        "recommendations": [
            {
                "check": "CPU limits not set",
                "details": "Workload {{=pydata.name}} ({{=pydata.kind}}) in namespace {{=pydata.namespace}} has no CPU limits",
                "reason": "CPU limits are not set for {{=pydata.kind}} {{=pydata.name}}",
                "resolution": "Set CPU limits on the {{=pydata.kind}} {{=pydata.name}}",
                "more_info": "",
                "total_risk": 3,
                "extra_data": {
                    "name": "my-test-app",
                    "kind": "Deployment",
                    "namespace": "test-namespace",
                },
                "objects": [
                    {"kind": "Deployment", "uid": "deployment-uid-456", "display_name": "my-test-app"}
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_dvo_namespaces_returns_workloads(
    ocp_advisor_mock_client: Mock,
    dvo_namespaces_response: dict[str, Any],
) -> None:
    """get_dvo_namespaces returns the smart proxy workloads overview unchanged."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        "namespaces/dvo",
        response_body=dvo_namespaces_response,
    )

    result = await get_dvo_namespaces()

    ocp_advisor_mock_client.get.assert_called_once_with("namespaces/dvo")
    assert json.loads(result) == dvo_namespaces_response


@pytest.mark.asyncio
async def test_get_dvo_namespaces_maps_request_errors(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Request failures raise InsightsApiError with a DVO-specific message."""
    ocp_advisor_mock_client.get.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(InsightsApiError, match="Error listing DVO namespaces"):
        await get_dvo_namespaces()


@pytest.mark.asyncio
async def test_get_dvo_recommendations_renders_with_extra_data(
    ocp_advisor_mock_client: Mock,
    dvo_recommendations_response: dict[str, Any],
) -> None:
    """get_dvo_recommendations renders templates with resource-specific extra data."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"namespaces/dvo/{NAMESPACE_ID}/cluster/{CLUSTER_ID}",
        response_body=dvo_recommendations_response,
    )

    result = await get_dvo_recommendations(cluster_id=UUID(CLUSTER_ID), namespace_id=UUID(NAMESPACE_ID))

    ocp_advisor_mock_client.get.assert_called_once_with(
        f"namespaces/dvo/{NAMESPACE_ID}/cluster/{CLUSTER_ID}"
    )
    payload = json.loads(result)
    recommendation = payload["recommendations"][0]
    assert recommendation["reason"] == "CPU limits are not set for Deployment my-test-app"
    assert recommendation["resolution"] == "Set CPU limits on the Deployment my-test-app"
    assert recommendation["details"] == (
        "Workload my-test-app (Deployment) in namespace test-namespace has no CPU limits"
    )
    assert recommendation["rendering"] == {"status": "ok"}
    # affected objects and metadata are retained
    assert recommendation["objects"][0]["uid"] == "deployment-uid-456"
    assert recommendation["check"] == "CPU limits not set"


@pytest.mark.asyncio
async def test_get_dvo_recommendations_rendering_failure_is_explicit(
    ocp_advisor_mock_client: Mock,
    dvo_recommendations_response: dict[str, Any],
) -> None:
    """A rendering failure keeps the unresolved template and is clearly marked."""
    dvo_recommendations_response["recommendations"][0]["reason"] = "{{=pydata.missing.value()}}"
    dvo_recommendations_response["recommendations"][0]["extra_data"] = {}
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"namespaces/dvo/{NAMESPACE_ID}/cluster/{CLUSTER_ID}",
        response_body=dvo_recommendations_response,
    )

    result = await get_dvo_recommendations(cluster_id=UUID(CLUSTER_ID), namespace_id=UUID(NAMESPACE_ID))

    recommendation = json.loads(result)["recommendations"][0]
    assert recommendation["reason"] == "{{=pydata.missing.value()}}"
    assert recommendation["rendering"]["status"] == "failed"
    assert "reason" in recommendation["rendering"]["errors"]


@pytest.mark.asyncio
async def test_get_dvo_recommendations_no_findings(
    ocp_advisor_mock_client: Mock,
) -> None:
    """A namespace with no DVO findings returns an explicit empty list."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        f"namespaces/dvo/{NAMESPACE_ID}/cluster/{CLUSTER_ID}",
        response_body={
            "status": "ok",
            "cluster": {"uuid": CLUSTER_ID, "display_name": "prod-cluster"},
            "namespace": {"uuid": NAMESPACE_ID, "name": "test-namespace"},
            "metadata": {"recommendations": 0},
            "recommendations": [],
        },
    )

    result = await get_dvo_recommendations(cluster_id=UUID(CLUSTER_ID), namespace_id=UUID(NAMESPACE_ID))

    assert json.loads(result)["recommendations"] == []


@pytest.mark.asyncio
async def test_get_dvo_recommendations_maps_request_errors(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Request failures raise InsightsApiError with a namespace-specific message."""
    ocp_advisor_mock_client.get.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(
        InsightsApiError,
        match=f"Error retrieving DVO recommendations for namespace {NAMESPACE_ID}",
    ):
        await get_dvo_recommendations(cluster_id=UUID(CLUSTER_ID), namespace_id=UUID(NAMESPACE_ID))
