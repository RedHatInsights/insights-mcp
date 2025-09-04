"""
Conftest for advisor_mcp tests - re-exports fixtures from top-level tests.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from advisor_mcp import AdvisorMCP

# Import directly from tests since pytest now knows where to find packages
from tests.conftest import (
    TEST_CLIENT_ID,
    TEST_CLIENT_SECRET,
    assert_api_error_result,
    assert_empty_response,
    assert_instruction_in_result,
    create_mcp_server,
    create_mock_client,
    default_response_size,
    guardian_agent,
    mcp_server_url,
    mcp_tools,
    mock_http_headers,
    setup_mcp_mock,
    test_agent,
    test_client_credentials,
    verbose_logger,
)

# Test constants specific to advisor
TEST_RULE_ID = "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"
TEST_NODE_ID = "6464541"
TEST_RHEL_VERSION = "9.4"
TEST_TAG = "insights-client/group=database-servers"


def get_default_active_rules_params(**overrides):
    """Helper function to get default parameters for get_active_rules with optional overrides."""
    default_params = {
        "impacting": True,
        "incident": None,
        "has_automatic_remediation": None,
        "impact": None,
        "likelihood": None,
        "category": None,
        "reboot": None,
        "sort": "-total_risk",
        "offset": 0,
        "limit": 10,
        "groups": None,
        "tags": None,
    }
    default_params.update(overrides)
    return default_params


def get_default_hosts_details_params(rule_id=TEST_RULE_ID, **overrides):
    """Helper function to get default parameters for get_hosts_details_hitting_a_rule with optional overrides."""
    default_params = {
        "rule_id": rule_id,
        "limit": 10,
        "offset": 0,
        "rhel_version": None,
    }
    default_params.update(overrides)
    return default_params


@pytest.fixture
def advisor_mcp_server():
    """Create Advisor MCP server for tests."""
    return create_mcp_server(AdvisorMCP)


@pytest.fixture
def advisor_mock_client():
    """Create a mock InsightsClient for Advisor tests."""
    return create_mock_client(api_path="api/insights/v1")


@contextmanager
def setup_advisor_mock(mcp_server, mock_client, mock_response=None, side_effect=None):
    """Context manager for setting up Advisor mock patterns.

    Advisor MCP uses a different architecture than Image Builder MCP:
    - No get_http_headers() function
    - Uses self.insights_client directly from InsightsMCP base class
    """

    # Set up mock responses
    if side_effect:
        mock_client.get.side_effect = side_effect
        mock_client.post.side_effect = side_effect
        mock_client.put.side_effect = side_effect
    else:
        # Set return value for all cases, including when mock_response is None
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
        mock_client.put.return_value = mock_response

    # Mock the insights_client directly on the server instance
    with patch.object(mcp_server, "insights_client", mock_client):
        yield None  # No headers needed for advisor architecture


# Make the fixtures available for import
__all__ = [
    "assert_api_error_result",
    "assert_empty_response",
    "assert_instruction_in_result",
    "advisor_mcp_server",
    "advisor_mock_client",
    "create_mcp_server",
    "create_mock_client",
    "default_response_size",
    "get_default_active_rules_params",
    "get_default_hosts_details_params",
    "guardian_agent",
    "mcp_server_url",
    "mcp_tools",
    "mock_http_headers",
    "setup_advisor_mock",
    "setup_mcp_mock",
    "test_agent",
    "test_client_credentials",
    "TEST_CLIENT_ID",
    "TEST_CLIENT_SECRET",
    "TEST_NODE_ID",
    "TEST_RHEL_VERSION",
    "TEST_RULE_ID",
    "TEST_TAG",
    "verbose_logger",
]
