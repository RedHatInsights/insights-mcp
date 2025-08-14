"""
Pytest configuration and shared fixtures for image-builder-mcp tests.
"""

import logging
import pytest
from .utils import start_mcp_server_process, cleanup_server_process, load_llm_configurations
from .utils import CustomVLLMModel
from .utils_agent import MCPAgentWrapper


# Load LLM configurations for fixtures
_, guardian_llm_config = load_llm_configurations()


@pytest.fixture
def test_agent(mcp_server_thread, verbose_logger, request):  # pylint: disable=redefined-outer-name
    """Create and configure a simplified test agent for the current LLM configuration."""
    # Get llm_config from the test's parametrization
    llm_config = request.node.callspec.params["llm_config"]

    agent = MCPAgentWrapper(
        server_url=mcp_server_thread,
        api_url=llm_config["MODEL_API"],
        model_id=llm_config["MODEL_ID"],
        api_key=llm_config["USER_KEY"],
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
def mcp_server_thread():  # pylint: disable=too-many-locals
    """Start MCP server in a separate thread using HTTP streaming."""
    server_url, server_process = start_mcp_server_process()

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)


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
