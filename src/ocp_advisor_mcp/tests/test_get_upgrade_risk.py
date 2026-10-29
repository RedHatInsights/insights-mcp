"""Test suite for the OCP Advisor get_upgrade_risk() tool."""

import json
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock

import pytest

from insights_mcp.errors import InsightsApiError
from ocp_advisor_mcp.server import _MAX_UPGRADE_RISK_CLUSTERS, get_upgrade_risk

CLUSTER_ID = "11111111-2222-3333-4444-555555555555"
CLUSTER_ID_2 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
ENDPOINT = "upgrade-risks-prediction"


@pytest.fixture(name="upgrade_risk_response")
def fixture_upgrade_risk_response() -> dict[str, Any]:
    """Sample multi-cluster response with identified risks and an unavailable cluster."""
    return {
        "status": "ok",
        "predictions": [
            {
                "cluster_id": CLUSTER_ID,
                "prediction_status": "ok",
                "upgrade_recommended": False,
                "upgrade_risks_predictors": {
                    "alerts": [
                        {
                            "name": "Alert1",
                            "namespace": "openshift-monitoring",
                            "severity": "warning",
                            "url": "https://console.example/alerts/Alert1",
                        }
                    ],
                    "operator_conditions": [
                        {
                            "name": "authentication",
                            "condition": "Degraded",
                            "reason": "AsExpected",
                            "url": "https://console.example/operators/authentication",
                        }
                    ],
                },
                "last_checked_at": "2026-10-20T12:00:00Z",
            },
            {
                "cluster_id": CLUSTER_ID_2,
                "prediction_status": "No data for the cluster",
            },
        ],
    }


@pytest.fixture(name="no_risk_response")
def fixture_no_risk_response() -> dict[str, Any]:
    """Sample response explicitly reporting no identified upgrade risk."""
    return {
        "status": "ok",
        "predictions": [
            {
                "cluster_id": CLUSTER_ID,
                "prediction_status": "ok",
                "upgrade_recommended": True,
                "upgrade_risks_predictors": {
                    "alerts": [],
                    "operator_conditions": [],
                },
                "last_checked_at": "2026-10-20T12:00:00Z",
            }
        ],
    }


@pytest.mark.asyncio
async def test_get_upgrade_risk_returns_predictions(
    ocp_advisor_mock_client: Mock,
    upgrade_risk_response: dict[str, Any],
) -> None:
    """Successful responses keep predictors/status and pass cluster UUIDs in the POST body."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.POST,
        ENDPOINT,
        body={"clusters": [CLUSTER_ID, CLUSTER_ID_2]},
        response_body=upgrade_risk_response,
    )

    result = await get_upgrade_risk([CLUSTER_ID, CLUSTER_ID_2])

    ocp_advisor_mock_client.post.assert_called_once_with(
        ENDPOINT,
        json={"clusters": [CLUSTER_ID, CLUSTER_ID_2]},
    )
    payload = json.loads(result)
    assert payload == upgrade_risk_response
    assert payload["predictions"][0]["upgrade_recommended"] is False
    assert payload["predictions"][1]["prediction_status"] == "No data for the cluster"


@pytest.mark.asyncio
async def test_get_upgrade_risk_returns_explicit_no_risk(
    ocp_advisor_mock_client: Mock,
    no_risk_response: dict[str, Any],
) -> None:
    """An explicit no-risk prediction stays prediction_status ok and is not remapped."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.POST,
        ENDPOINT,
        body={"clusters": [CLUSTER_ID]},
        response_body=no_risk_response,
    )

    result = await get_upgrade_risk([CLUSTER_ID])

    payload = json.loads(result)
    prediction = payload["predictions"][0]
    assert prediction["prediction_status"] == "ok"
    assert prediction["upgrade_recommended"] is True
    assert prediction["upgrade_risks_predictors"]["alerts"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status, content",
    [
        (400, "cluster belongs to different organization"),
        (503, "upgrade risks service unavailable"),
    ],
)
async def test_get_upgrade_risk_surfaces_upstream_errors(
    ocp_advisor_mock_client: Mock,
    status: int,
    content: str,
) -> None:
    """HTTP failures are raised, not empty success."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.POST,
        ENDPOINT,
        body={"clusters": [CLUSTER_ID]},
        error=InsightsApiError(f"Unexpected HTTP status code: {status}, content: {content}"),
    )

    with pytest.raises(InsightsApiError, match=str(status)):
        await get_upgrade_risk([CLUSTER_ID])


@pytest.mark.asyncio
async def test_get_upgrade_risk_maps_request_errors(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Transport failures are wrapped with an OCP Advisor specific error message."""
    ocp_advisor_mock_client.post.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(InsightsApiError, match="Error retrieving upgrade-risk predictions"):
        await get_upgrade_risk([CLUSTER_ID])


@pytest.mark.asyncio
async def test_get_upgrade_risk_rejects_empty_list(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Empty cluster_ids is rejected before calling the API."""
    with pytest.raises(InsightsApiError, match="at least one cluster UUID"):
        await get_upgrade_risk([])

    ocp_advisor_mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_get_upgrade_risk_rejects_blank_cluster_id(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Whitespace-only cluster IDs are rejected before calling the API."""
    with pytest.raises(InsightsApiError, match="non-empty cluster UUIDs"):
        await get_upgrade_risk(["   "])

    ocp_advisor_mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_get_upgrade_risk_rejects_oversized_list(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Lists above Smart Proxy MaxAllowedClusters are rejected before calling the API."""
    too_many = [f"00000000-0000-0000-0000-{index:012d}" for index in range(_MAX_UPGRADE_RISK_CLUSTERS + 1)]

    with pytest.raises(InsightsApiError, match=f"at most {_MAX_UPGRADE_RISK_CLUSTERS} clusters"):
        await get_upgrade_risk(too_many)

    ocp_advisor_mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_get_upgrade_risk_strips_cluster_ids(
    ocp_advisor_mock_client: Mock,
    no_risk_response: dict[str, Any],
) -> None:
    """Leading/trailing whitespace is stripped before the POST body is sent."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.POST,
        ENDPOINT,
        body={"clusters": [CLUSTER_ID]},
        response_body=no_risk_response,
    )

    await get_upgrade_risk([f"  {CLUSTER_ID}  "])

    ocp_advisor_mock_client.post.assert_called_once_with(
        ENDPOINT,
        json={"clusters": [CLUSTER_ID]},
    )
