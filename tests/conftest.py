"""Pytest configuration and common fixtures."""

import asyncio
import functools
from http import HTTPMethod
from unittest.mock import Mock

import pytest
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

from insights_mcp.client import InsightsClient, build_mounted_tool_names
from insights_mcp.config import INSIGHTS_BASE_URL
from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from tests import oauth_utils as oauth_utils_module
from tests.llm_api_discovery import build_llm_api_context
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.types import MockRequest


@pytest.fixture
def default_response_size():
    """Default response size for pagination tests."""
    return 7


@pytest.fixture
def test_client_credentials():
    """Test client credentials."""
    return {"client_id": "test-client-id", "client_secret": "test-client-secret"}


@pytest.fixture
# pylint: disable=redefined-outer-name
def mock_http_headers(test_client_credentials):
    """Mock HTTP headers with test credentials."""
    return {
        "image-builder-client-id": test_client_credentials["client_id"],
        "image-builder-client-secret": test_client_credentials["client_secret"],
    }


@pytest.fixture(scope="session")
def mcp_server_url(request):
    """Start MCP server and return the URL.

    Supports different transport types via pytest.mark.parametrize or direct specification.
    Defaults to 'http' transport for backward compatibility.
    """
    # Get transport from test parameter if available, otherwise default to http
    transport = getattr(request, "param", "http")
    if hasattr(request.node, "callspec") and "transport" in request.node.callspec.params:
        transport = request.node.callspec.params["transport"]

    server_url, server_process = start_insights_mcp_server(transport)

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)


@pytest.fixture()
def mcp_tools(mcp_server_url):  # pylint: disable=redefined-outer-name
    """Fetch tools from the MCP server.

    For stdio transport, uses BasicMCPClient subprocess approach.
    For HTTP/SSE transports, connects to the running server.
    """

    async def _fetch():
        if mcp_server_url == "stdio":
            client = BasicMCPClient("python", args=["-m", "insights_mcp.server", "stdio"])
        else:
            client = BasicMCPClient(mcp_server_url)
        try:
            tool_spec = McpToolSpec(client=client)
            return await tool_spec.to_tool_list_async()
        finally:
            if not client.client_provided:
                await client.http_client.aclose()

    return asyncio.run(_fetch())


TEST_CLIENT_ID = "test-client-id"
TEST_CLIENT_SECRET = "test-client-secret"
TEST_BLUEPRINT_UUID = "12345678-1234-1234-1234-123456789012"


def create_mcp_server(server_class, client_id=TEST_CLIENT_ID, client_secret=TEST_CLIENT_SECRET):
    """Create a mock MCP server instance for any server class."""
    server = server_class()
    mounted_tool_names = build_mounted_tool_names([server.toolset_name])
    server.init_insights_client(
        client_id=client_id,
        client_secret=client_secret,
        mounted_tool_names=mounted_tool_names,
    )
    server.register_tools()
    return server


def create_mock_client(  # pylint: disable=too-many-arguments
    client_id=TEST_CLIENT_ID,
    client_secret=TEST_CLIENT_SECRET,
    api_path=None,
    *,
    api: MockInsightsAPI | None = None,
    org_id=None,
    proxy_url=None,
    headers=None,
):
    """Create a mock InsightsClient instance for any test."""
    if api is None and api_path:
        api = MockInsightsAPI(path_prefix=api_path)

    client = Mock(spec=InsightsClient)
    client.client_id = client_id
    client.client_secret = client_secret
    client.insights_base_url = INSIGHTS_BASE_URL
    client.api_path = api_path or getattr(api, "path_prefix", "")
    client.org_id = org_id
    client.proxy_url = proxy_url
    client.headers = dict(headers or {})
    client.get_org_id.return_value = org_id

    if api is None:
        return client

    client.api = api

    def dispatch(
        method,
        endpoint,
        *,
        params=None,
        json=None,
        headers=None,
        **kwargs,
    ):
        del kwargs

        request_headers = dict(client.headers)
        if headers is not None:
            request_headers.update(headers)

        response = api.resolve(
            MockRequest(
                method=method,
                path=f"{client.api_path}/{endpoint}",
                query=params or {},
                body=json,
                headers=request_headers,
            )
        )
        if response.error is not None:
            raise response.error
        return response.body

    client.get.side_effect = lambda endpoint, params=None, **kwargs: dispatch(
        HTTPMethod.GET, endpoint, params=params, **kwargs
    )
    client.post.side_effect = lambda endpoint, json=None, **kwargs: dispatch(
        HTTPMethod.POST, endpoint, json=json, **kwargs
    )
    client.put.side_effect = lambda endpoint, json=None, **kwargs: dispatch(
        HTTPMethod.PUT, endpoint, json=json, **kwargs
    )

    return client


def assert_api_error_message(exception: BaseException, error_message: str = "API Error") -> None:
    """Assert that an InsightsApiError message matches expected API error text."""
    error_text = str(exception)
    assert error_text.startswith(f"Error: {error_message}") or error_message.lower() in error_text.lower()


def assert_api_error_result(result, error_message="API Error"):
    """Helper to assert API error results returned as strings (legacy).

    Prefer ``pytest.raises(InsightsApiError)`` with ``assert_api_error_message``.
    """
    assert result.startswith(f"Error: {error_message}") or error_message.lower() in result.lower()


def assert_empty_response(result):
    """Helper to assert empty response results."""
    assert "[]" in result


def assert_instruction_in_result(result, instruction="[INSTRUCTION]"):
    """Helper to assert instruction text in result."""
    assert instruction in result


# ============================================================================
# OAuth Testing Fixtures
# ============================================================================


@pytest.fixture
def mock_oauth_token():
    """Create a mock OAuth AccessToken for testing.

    Returns:
        FastMCP AccessToken with test claims for Red Hat SSO

    Example:
        >>> def test_with_oauth(mock_oauth_token):
        ...     assert mock_oauth_token.claims["organization"]["id"] == "test-org-123"
    """
    return oauth_utils_module.create_test_token(
        org_id="test-org-123", user_id="test-user-123", username="testuser", account_id="test-account-456"
    )


@pytest.fixture
def multi_user_tokens():
    """Create multiple user tokens for multi-user testing.

    Returns:
        Dictionary mapping user IDs to AccessTokens

    Example:
        >>> def test_multi_user(multi_user_tokens):
        ...     user1_token = multi_user_tokens["user-0"]
        ...     user2_token = multi_user_tokens["user-1"]
        ...     assert user1_token.claims["organization"]["id"] != user2_token.claims["organization"]["id"]
    """
    return oauth_utils_module.create_multi_user_tokens(num_users=3)


@functools.cache
def _build_llm_api_context() -> dict[str, str]:
    return asyncio.run(build_llm_api_context())


@pytest.fixture(scope="session")
def llm_api_context() -> dict[str, str]:
    """Live API-derived placeholder values for LLM prompt tests (session scope)."""
    return dict(_build_llm_api_context())
