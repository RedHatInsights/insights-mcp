"""Pytest configuration and common fixtures."""

import asyncio
import logging
from contextlib import contextmanager
from typing import Dict
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio

# pylint: disable=wrong-import-position
from deepeval.models import GPTModel
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

# Add imports for mock client creation
from insights_mcp.client import InsightsClient, build_mounted_tool_names
from insights_mcp.config import (
    BRAND_CLIENT_ID_HEADER,
    BRAND_CLIENT_SECRET_HEADER,
    INSIGHTS_BASE_URL,
    INSIGHTS_CLIENT_ID,
    INSIGHTS_CLIENT_SECRET,
)
from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server
from tests import oauth_utils as oauth_utils_module
from tests.llama_index_support.agent_mcp import MCPAgentWrapper
from tests.llm_tracing import enable_llm_test_tracing
from tests.utils import load_llm_configurations


def gpt_model_from_config(config: Dict[str, str]) -> GPTModel:
    """Build deepeval GPTModel for OpenAI-compatible endpoints from test config."""
    return GPTModel(
        model=config["MODEL_ID"],
        base_url=config["MODEL_API"],
        api_key=config["USER_KEY"],
        temperature=0,
    )


# Load LLM configurations for fixtures
_, guardian_llm_config = load_llm_configurations()


def _node_requests_llm_tracing(node: pytest.Item) -> bool:
    """Return True when the test uses the LLM matrix (``llm_config`` parametrization)."""
    callspec = getattr(node, "callspec", None)
    return callspec is not None and "llm_config" in callspec.params


@pytest.fixture(scope="session", autouse=True)
def llm_test_tracing(request):
    """Enable DeepEval and Phoenix LlamaIndex tracing for LLM integration tests only."""
    if not request.session.items:
        yield
        return
    if not any(_node_requests_llm_tracing(item) for item in request.session.items):
        yield
        return
    enable_llm_test_tracing()
    yield


def _insights_mcp_http_headers() -> Dict[str, str] | None:
    """HTTP headers for Insights MCP when service account credentials are in the environment."""
    if INSIGHTS_CLIENT_ID and INSIGHTS_CLIENT_SECRET:
        return {
            BRAND_CLIENT_ID_HEADER: INSIGHTS_CLIENT_ID,
            BRAND_CLIENT_SECRET_HEADER: INSIGHTS_CLIENT_SECRET,
        }
    return None


@pytest_asyncio.fixture
async def test_agent(mcp_server_url, verbose_logger, request):  # pylint: disable=redefined-outer-name
    """Create and configure a simplified test agent for the current LLM configuration."""
    # Get llm_config from the test's parametrization
    llm_config = request.node.callspec.params["llm_config"]

    agent = MCPAgentWrapper(
        server_url=mcp_server_url,
        api_url=llm_config["MODEL_API"],
        model_id=llm_config["MODEL_ID"],
        api_key=llm_config["USER_KEY"],
        verbose_logger=verbose_logger,
        mcp_http_headers=_insights_mcp_http_headers(),
    )
    verbose_logger.info("🧪 Testing the model: %s", agent.model_id)

    await agent.initialize()
    try:
        yield agent
    finally:
        await agent.aclose()


@pytest.fixture
def guardian_agent(verbose_logger, request):  # pylint: disable=redefined-outer-name
    """Create and configure a guardian agent for evaluation."""
    # Get llm_config from the test's parametrization
    llm_config = request.node.callspec.params["llm_config"]

    # if there is a guardian LLM, use it for the guardian agent
    # otherwise, use the test LLM for the guardian agent
    if guardian_llm_config:
        config = guardian_llm_config
    else:
        config = llm_config

    agent = gpt_model_from_config(config)

    verbose_logger.info("🧪 Verifying with the model: %s", agent.get_model_name())

    return agent


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


@pytest.fixture
def verbose_logger(request):
    """Get a logger that respects pytest verbosity."""
    logger = logging.getLogger(__name__)

    verbosity = request.config.getoption("verbose", default=0)

    if verbosity >= 3:
        logger.setLevel(logging.DEBUG)
    elif verbosity == 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)

    return logger


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


def create_mock_client(client_id=TEST_CLIENT_ID, client_secret=TEST_CLIENT_SECRET, api_path=None):
    """Create a mock InsightsClient instance for any test."""
    client = Mock(spec=InsightsClient)
    client.client_id = client_id
    client.client_secret = client_secret
    client.insights_base_url = INSIGHTS_BASE_URL
    if api_path:
        client.api_path = api_path
    return client


# No server-specific fixtures needed!
# Tests can import the server class directly and use create_mcp_server(ServerClass)


@contextmanager
# pylint: disable=too-many-arguments,too-many-positional-arguments
def setup_mcp_mock(
    server_module,
    mcp_server,
    mock_client,
    mock_response=None,
    side_effect=None,
    client_id=TEST_CLIENT_ID,
    brand="insights",
):
    """Generic context manager for setting up MCP server mock patterns.

    Args:
        server_module: The server module to patch get_http_headers on
        mcp_server: The MCP server instance
        mock_client: The mock client to use
        mock_response: Optional response to return from client methods
        side_effect: Optional side effect for client methods
        client_id: Client ID to use (default: TEST_CLIENT_ID)
        brand: Brand for header names (default: "insights"). Use "red-hat-lightspeed" for lightspeed.
    """
    # Derive headers from brand (same logic as config.py)
    brand_prefix = brand.replace("red-hat-", "")
    id_header = f"{brand_prefix.lower()}-client-id"
    secret_header = f"{brand_prefix.lower()}-client-secret"

    with patch.object(server_module, "get_http_headers") as mock_headers:
        mock_headers.return_value = {
            id_header: client_id,
            secret_header: TEST_CLIENT_SECRET,
        }

        if side_effect:
            mock_client.get.side_effect = side_effect
            mock_client.post.side_effect = side_effect
            mock_client.put.side_effect = side_effect
        elif mock_response is not None:
            mock_client.get.return_value = mock_response
            mock_client.post.return_value = mock_response
            mock_client.put.return_value = mock_response

        mcp_server.clients[client_id] = mock_client
        yield mock_headers


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


@pytest.fixture(scope="session")
def llm_api_context():
    """Live API-derived placeholder values for LLM prompt tests (session scope)."""
    from tests.llm_api_discovery import build_llm_api_context

    return asyncio.run(build_llm_api_context())
