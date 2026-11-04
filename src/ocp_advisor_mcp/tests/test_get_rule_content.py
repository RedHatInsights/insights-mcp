"""Test suite for the OCP Advisor get_rule_content() tool."""

import json
from http import HTTPMethod
from typing import Any
from unittest.mock import Mock

import pytest

from insights_mcp.errors import InsightsApiError
from ocp_advisor_mcp.server import get_rule_content

RULE_ID = "ccx_rules_ocp.external.rules.example.report|EXAMPLE_WARNING"
DVO_RULE_ID = "ccx_rules_ocp.external.dvo.example|DVO_EXAMPLE"


@pytest.fixture(name="rule_content_response")
def fixture_rule_content_response() -> dict[str, Any]:
    """Sample Smart Proxy /rule/{ruleId}/content response."""
    return {
        "status": "ok",
        "groups": [
            {
                "title": "Availability",
                "description": "Availability recommendations",
                "tags": ["service_availability"],
            }
        ],
        "content": {
            "rule_id": RULE_ID,
            "description": "Example Advisor recommendation",
            "generic": "Generic cluster-independent explanation.",
            "reason": "Why this can happen.",
            "resolution": "Follow these remediation steps.",
            "more_info": "https://access.redhat.com/solutions/example",
            "total_risk": 3,
            "impact": 2,
            "likelihood": 4,
            "publish_date": "2026-10-20T12:00:00Z",
            "tags": ["openshift", "service_availability"],
        },
    }


@pytest.mark.asyncio
async def test_get_rule_content_returns_generic_static_content(
    ocp_advisor_mock_client: Mock,
    rule_content_response: dict[str, Any],
) -> None:
    """get_rule_content calls GET /rule/{ruleId}/content and marks generic content."""
    endpoint = f"rule/{RULE_ID}/content"
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        endpoint,
        response_body=rule_content_response,
    )

    result = await get_rule_content(RULE_ID)

    ocp_advisor_mock_client.get.assert_called_once_with(endpoint)
    payload = json.loads(result)
    assert payload["content"] == rule_content_response["content"]
    assert payload["groups"] == rule_content_response["groups"]
    assert payload["content_type"] == "generic_static_rule_content"
    assert "not a rendered, cluster-specific finding" in payload["content_note"]


@pytest.mark.asyncio
async def test_get_rule_content_strips_rule_id(
    ocp_advisor_mock_client: Mock,
    rule_content_response: dict[str, Any],
) -> None:
    """Leading/trailing whitespace is stripped before the endpoint is called."""
    endpoint = f"rule/{RULE_ID}/content"
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        endpoint,
        response_body=rule_content_response,
    )

    await get_rule_content(f"  {RULE_ID}  ")

    ocp_advisor_mock_client.get.assert_called_once_with(endpoint)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rule_id",
    ["", "   ", "missing-error-key", "rule|", "|ERROR_KEY", "rule-module|ERROR_KEY"],
)
async def test_get_rule_content_rejects_invalid_rule_ids(
    ocp_advisor_mock_client: Mock,
    rule_id: str,
) -> None:
    """Invalid rule identifiers are rejected before calling the API."""
    with pytest.raises(InsightsApiError, match="format rule.module\\|ERROR_KEY"):
        await get_rule_content(rule_id)

    ocp_advisor_mock_client.get.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status, content, expected_match",
    [
        (404, "Rule ID is not available", "404"),
        (503, "Content service is unavailable", "503"),
    ],
)
async def test_get_rule_content_surfaces_missing_or_unavailable_content(
    ocp_advisor_mock_client: Mock,
    status: int,
    content: str,
    expected_match: str,
) -> None:
    """Missing DVO/unsupported content is surfaced explicitly instead of empty success."""
    endpoint = f"rule/{DVO_RULE_ID}/content"
    ocp_advisor_mock_client.api.register(
        HTTPMethod.GET,
        endpoint,
        error=InsightsApiError(f"Unexpected HTTP status code: {status}, content: {content}"),
    )

    with pytest.raises(InsightsApiError, match=expected_match):
        await get_rule_content(DVO_RULE_ID)


@pytest.mark.asyncio
async def test_get_rule_content_maps_request_errors(ocp_advisor_mock_client: Mock) -> None:
    """Transport failures are wrapped with an OCP Advisor specific error message."""
    ocp_advisor_mock_client.get.side_effect = RuntimeError("backend unavailable")

    with pytest.raises(InsightsApiError, match="Error retrieving OCP Advisor rule content"):
        await get_rule_content(RULE_ID)

    ocp_advisor_mock_client.get.assert_called_once_with(f"rule/{RULE_ID}/content")
