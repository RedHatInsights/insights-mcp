"""Pytest configuration and common fixtures."""

# Apply defensive patch for llama-index MCP schema violation bug
# This prevents TypeError when llama-index incorrectly generates additionalProperties: true
# (which violates MCP specification that expects explicit object properties)

import asyncio
import logging
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

# Add imports for mock client creation
from insights_mcp.client import InsightsClient
from insights_mcp.config import INSIGHTS_BASE_URL_PROD

# pylint: disable=wrong-import-position
from .llama_index_non_iterable_bool_patch import apply_llama_index_bool_patch

if apply_llama_index_bool_patch():
    print("✅ Patch applied successfully")
else:
    print("❌ Failed to apply patch")

from .utils import CustomVLLMModel, cleanup_server_process, load_llm_configurations, start_insights_mcp_server
from .utils_agent import MCPAgentWrapper

# Load LLM configurations for fixtures
_, guardian_llm_config = load_llm_configurations()


@pytest.fixture
def test_agent(mcp_server_url, verbose_logger, request):  # pylint: disable=redefined-outer-name
    """Create and configure a simplified test agent for the current LLM configuration."""
    # Get llm_config from the test's parametrization
    llm_config = request.node.callspec.params["llm_config"]

    agent = MCPAgentWrapper(
        server_url=mcp_server_url,
        api_url=llm_config["MODEL_API"],
        model_id=llm_config["MODEL_ID"],
        api_key=llm_config["USER_KEY"],
        verbose_logger=verbose_logger,
    )
    verbose_logger.info("🧪 Testing the model: %s", agent.model_id)

    return agent


@pytest.fixture
def guardian_agent(verbose_logger, request):  # pylint: disable=redefined-outer-name
    """Create and configure a guardian agent for evaluation."""
    # Get llm_config from the test's parametrization
    llm_config = request.node.callspec.params["llm_config"]

    # if there is a guardian LLM, use it for the guardian agent
    # otherwise, use the test LLM for the guardian agent
    if guardian_llm_config:
        agent = CustomVLLMModel(
            api_url=guardian_llm_config["MODEL_API"],
            model_id=guardian_llm_config["MODEL_ID"],
            api_key=guardian_llm_config["USER_KEY"],
        )
    else:
        agent = CustomVLLMModel(
            api_url=llm_config["MODEL_API"], model_id=llm_config["MODEL_ID"], api_key=llm_config["USER_KEY"]
        )

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
    if mcp_server_url == "stdio":
        # For stdio, use subprocess approach
        client = BasicMCPClient("python", args=["-m", "insights_mcp.server", "stdio"])
    else:
        # For HTTP/SSE, connect to running server
        client = BasicMCPClient(mcp_server_url)

    tool_spec = McpToolSpec(client=client)

    async def _fetch():
        return await tool_spec.to_tool_list_async()

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
    server.init_insights_client(
        client_id=client_id,
        client_secret=client_secret,
    )
    server.register_tools()
    return server


def create_mock_client(client_id=TEST_CLIENT_ID, client_secret=TEST_CLIENT_SECRET, api_path=None):
    """Create a mock InsightsClient instance for any test."""
    client = Mock(spec=InsightsClient)
    client.client_id = client_id
    client.client_secret = client_secret
    client.insights_base_url = INSIGHTS_BASE_URL_PROD
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


def assert_api_error_result(result, error_message="API Error"):
    """Helper to assert API error results."""
    assert result.startswith(f"Error: {error_message}") or error_message.lower() in result.lower()


def assert_empty_response(result):
    """Helper to assert empty response results."""
    assert "[]" in result


def assert_instruction_in_result(result, instruction="[INSTRUCTION]"):
    """Helper to assert instruction text in result."""
    assert instruction in result
