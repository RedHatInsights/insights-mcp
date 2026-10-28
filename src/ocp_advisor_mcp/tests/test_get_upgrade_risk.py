"""Test suite for the OCP Advisor get_upgrade_risk() tool."""

import json
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock

import pytest

from insights_mcp.errors import InsightsApiError
from ocp_advisor_mcp.server import get_upgrade_risk

CLUSTER_ID = "11111111-2222-3333-4444-555555555555"
ENDPOINT = f"cluster/{CLUSTER_ID}/upgrade-risks-prediction"


@pytest.fixture(name="upgrade_risk_response")
def fixture_upgrade_risk_response() -> dict[str, Any]:
    """Sample successful /upgrade-risks-prediction response with identified risks."""
    return {
        "upgrade_recommendation": {
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
        },
        "meta": {"last_checked_at": "2026-10-20T12:00:00Z"},
        "status": "ok",
    }


@pytest.fixture(name="no_risk_response")
def fixture_no_risk_response() -> dict[str, Any]:
    """Sample successful response explicitly reporting no identified upgrade risk."""
    return {
        "upgrade_recommendation": {
            "upgrade_recommended": True,
            "upgrade_risks_predictors": {
                "alerts": [],
                "operator_conditions": [],
            },
        },
        "meta": {"last_checked_at": "2026-10-20T12:00:00Z"},
        "status": "ok",
    }


@pytest.mark.asyncio
async def test_get_upgrade_risk_returns_risk_findings(
    ocp_advisor_mock_client: Mock,
    upgrade_risk_response: dict[str, Any],
) -> None:
    """Successful responses keep predictors/timestamps and include the cluster id."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        ENDPOINT,
        response_body=upgrade_risk_response,
    )

    result = await get_upgrade_risk(CLUSTER_ID)

    ocp_advisor_mock_client.get.assert_called_once_with(ENDPOINT)
    payload = json.loads(result)
    assert payload["cluster_id"] == CLUSTER_ID
    assert payload["prediction_available"] is True
    assert payload["upgrade_recommendation"] == upgrade_risk_response["upgrade_recommendation"]
    assert payload["meta"] == upgrade_risk_response["meta"]


@pytest.mark.asyncio
async def test_get_upgrade_risk_returns_explicit_no_risk(
    ocp_advisor_mock_client: Mock,
    no_risk_response: dict[str, Any],
) -> None:
    """An explicit no-risk prediction remains prediction_available and is not remapped."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        ENDPOINT,
        response_body=no_risk_response,
    )

    result = await get_upgrade_risk(CLUSTER_ID)

    payload = json.loads(result)
    assert payload["prediction_available"] is True
    assert payload["upgrade_recommendation"]["upgrade_recommended"] is True
    assert payload["upgrade_recommendation"]["upgrade_risks_predictors"]["alerts"] == []


@pytest.mark.asyncio
async def test_get_upgrade_risk_maps_managed_cluster_empty_body(
    ocp_advisor_mock_client: Mock,
) -> None:
    """HTTP 204 / empty body is reported as unavailable (managed cluster), not as no risk."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        ENDPOINT,
        response_body="",
    )

    result = await get_upgrade_risk(CLUSTER_ID)

    payload = json.loads(result)
    assert payload == {
        "cluster_id": CLUSTER_ID,
        "prediction_available": False,
        "reason": "managed_cluster",
        "detail": "Upgrade-risk prediction is not available for managed clusters.",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status, content",
    [
        (404, "cluster not found in Observatorium"),
        (503, "upgrade risks service unavailable"),
    ],
)
async def test_get_upgrade_risk_surfaces_upstream_errors(
    ocp_advisor_mock_client: Mock,
    status: int,
    content: str,
) -> None:
    """HTTP failures (including 404 missing prediction) are raised, not empty success."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        ENDPOINT,
        error=InsightsApiError(f"Unexpected HTTP status code: {status}, content: {content}"),
    )

    with pytest.raises(InsightsApiError, match=str(status)):
        await get_upgrade_risk(CLUSTER_ID)


@pytest.mark.asyncio
async def test_get_upgrade_risk_maps_request_errors(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Transport failures are wrapped with an OCP Advisor specific error message."""
    ocp_advisor_mock_client.get.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(
        InsightsApiError,
        match=f"Error retrieving upgrade-risk prediction for cluster {CLUSTER_ID}",
    ):
        await get_upgrade_risk(CLUSTER_ID)


@pytest.mark.asyncio
async def test_get_upgrade_risk_rejects_empty_cluster_id(
    ocp_advisor_mock_client: Mock,
) -> None:
    """Empty cluster_id is rejected before calling the API."""
    with pytest.raises(InsightsApiError, match="non-empty cluster UUID"):
        await get_upgrade_risk("   ")

    ocp_advisor_mock_client.get.assert_not_called()
