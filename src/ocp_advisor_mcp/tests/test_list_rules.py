"""Test suite for the OCP Advisor list_rules() tool."""

import json
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock

import pytest

from insights_mcp.errors import InsightsApiError
from ocp_advisor_mcp.server import _MAX_RULE_LIST_LIMIT, list_rules

ENDPOINT = "rule"
RULE_ID = "ccx_rules_ocp.external.rules.example.report|EXAMPLE_WARNING"
RULE_ID_2 = "ccx_rules_ocp.external.dvo.example|DVO_EXAMPLE"


@pytest.fixture(name="rules_response")
def fixture_rules_response() -> dict[str, Any]:
    """Sample Smart Proxy /rule response."""
    return {
        "status": "ok",
        "recommendations": [
            {
                "rule_id": RULE_ID,
                "description": "Example Advisor recommendation",
                "generic": "Generic Advisor explanation.",
                "publish_date": "2026-10-20T12:00:00Z",
                "total_risk": 3,
                "impact": 2,
                "likelihood": 4,
                "resolution_risk": 1,
                "tags": ["openshift", "service_availability"],
                "disabled": False,
                "impacted_clusters_count": 2,
            },
            {
                "rule_id": RULE_ID_2,
                "description": "Example DVO recommendation",
                "generic": "Generic DVO explanation.",
                "publish_date": "2026-10-21T12:00:00Z",
                "total_risk": 2,
                "impact": 2,
                "likelihood": 2,
                "resolution_risk": 0,
                "tags": ["openshift", "dvo"],
                "disabled": False,
                "impacted_clusters_count": 0,
            },
        ],
    }


@pytest.mark.asyncio
async def test_list_rules_returns_rules_with_default_bounds(
    ocp_advisor_mock_client: Mock,
    rules_response: dict[str, Any],
) -> None:
    """list_rules calls GET /rule and adds MCP-side pagination metadata."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        ENDPOINT,
        response_body=rules_response,
    )

    result = await list_rules()

    ocp_advisor_mock_client.get.assert_called_once_with(ENDPOINT, params=None)
    payload = json.loads(result)
    assert payload["recommendations"] == rules_response["recommendations"]
    assert payload["meta"] == {
        "count": 2,
        "total": 2,
        "limit": 20,
        "offset": 0,
        "has_next": False,
        "has_previous": False,
        "pagination_note": (
            "The Smart Proxy /rule endpoint does not provide native pagination; "
            "limit and offset are applied by the MCP tool after retrieving the rule list."
        ),
    }


@pytest.mark.asyncio
async def test_list_rules_passes_impacting_filter_and_slices_locally(
    ocp_advisor_mock_client: Mock,
    rules_response: dict[str, Any],
) -> None:
    """The impacting filter is passed upstream while limit/offset slice locally."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        ENDPOINT,
        query={"impacting": True},
        response_body=rules_response,
    )

    result = await list_rules(impacting=True, limit=1, offset=1)

    ocp_advisor_mock_client.get.assert_called_once_with(ENDPOINT, params={"impacting": True})
    payload = json.loads(result)
    assert payload["recommendations"] == [rules_response["recommendations"][1]]
    assert payload["meta"]["count"] == 1
    assert payload["meta"]["total"] == 2
    assert payload["meta"]["has_previous"] is True
    assert payload["meta"]["has_next"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit, offset, expected_error",
    [
        (0, 0, "limit must be between"),
        (_MAX_RULE_LIST_LIMIT + 1, 0, "limit must be between"),
        (20, -1, "offset must be greater than or equal to 0"),
    ],
)
async def test_list_rules_rejects_invalid_bounds(
    ocp_advisor_mock_client: Mock,
    limit: int,
    offset: int,
    expected_error: str,
) -> None:
    """Invalid local pagination bounds are rejected before calling the API."""
    with pytest.raises(InsightsApiError, match=expected_error):
        await list_rules(limit=limit, offset=offset)

    ocp_advisor_mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_list_rules_surfaces_upstream_errors(ocp_advisor_mock_client: Mock) -> None:
    """HTTP failures are raised, not converted to an empty list."""
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        ENDPOINT,
        error=InsightsApiError("Unexpected HTTP status code: 503, content: unavailable"),
    )

    with pytest.raises(InsightsApiError, match="503"):
        await list_rules()


@pytest.mark.asyncio
async def test_list_rules_maps_request_errors(ocp_advisor_mock_client: Mock) -> None:
    """Transport failures are wrapped with an OCP Advisor specific error message."""
    ocp_advisor_mock_client.get.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(InsightsApiError, match="Error listing OCP Advisor rules"):
        await list_rules()

    ocp_advisor_mock_client.get.assert_called_once_with(ENDPOINT, params=None)
