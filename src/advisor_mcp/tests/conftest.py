"""
Conftest for advisor_mcp tests - re-exports fixtures from top-level tests.
"""

import pytest

from advisor_mcp import AdvisorMCP
from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server

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
    llm_api_context,
    mcp_tools,
    mock_http_headers,
    setup_toolset_mock,
    test_agent,
    test_client_credentials,
    verbose_logger,
)


@pytest.fixture(scope="session")
def mcp_server_url(request):
    """Start MCP server with only the advisor toolset for LLM integration tests."""
    transport = getattr(request, "param", "http")
    if hasattr(request.node, "callspec") and "transport" in request.node.callspec.params:
        transport = request.node.callspec.params["transport"]

    server_url, server_process = start_insights_mcp_server(transport, toolset="advisor")

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)


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
    """Helper function to get default parameters for get_hosts_details_for_rule with optional overrides."""
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
    "llm_api_context",
    "mcp_server_url",
    "mcp_tools",
    "mock_http_headers",
    "setup_toolset_mock",
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
