"""Test suite for the OCP Advisor list_clusters() tool."""

import json
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock

import pytest

from insights_mcp.errors import InsightsApiError
from ocp_advisor_mcp.server import list_clusters


@pytest.fixture(name="clusters_response")
def fixture_clusters_response() -> dict[str, Any]:
    """Sample /clusters response from Insights Results Aggregator."""
    return {
        "clusters": [
            {
                "cluster_id": "11111111-2222-3333-4444-555555555555",
                "cluster_name": "prod-cluster",
                "total_hits": 3,
                "hits_by_total_risk": {
                    "1": 0,
                    "2": 1,
                    "3": 2,
                    "4": 0,
                },
            }
        ]
    }


@pytest.mark.asyncio
async def test_list_clusters_calls_clusters_endpoint(
    ocp_advisor_mock_client: Mock,
    clusters_response: dict[str, Any],
) -> None:
    """list_clusters calls the authenticated /clusters endpoint and returns JSON."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        "clusters",
        response_body=clusters_response,
    )

    result = await list_clusters()

    ocp_advisor_mock_client.get.assert_called_once_with("clusters")
    assert json.loads(result) == clusters_response


@pytest.mark.asyncio
async def test_list_clusters_maps_request_errors(
    ocp_advisor_mock_client: Mock,
) -> None:
    """list_clusters wraps request failures with an OCP Advisor specific error message."""
    ocp_advisor_mock_client.get.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(InsightsApiError, match="Error listing Insights Results Aggregator clusters"):
        await list_clusters()

    ocp_advisor_mock_client.get.assert_called_once_with("clusters")
