"""Reusable pytest fixtures for MCP LLM evaluation tests."""

import logging

import pytest
import pytest_asyncio
from mcp_llm_eval.llama_index_support.agent_mcp import MCPAgentWrapper
from mcp_llm_eval.llm_tracing import enable_llm_test_tracing
from mcp_llm_eval.utils import gpt_model_from_config, load_llm_configurations

_, guardian_llm_config = load_llm_configurations()


@pytest.fixture(scope="session")
def mcp_memory_token_limit() -> int:
    """Align with OpenAILike context_window in initialize(). Large enough for tool results + follow-up turns.

    Override in conftest.
    """
    return 16384


@pytest.fixture(scope="session")
def mcp_http_headers() -> dict[str, str] | None:
    """HTTP headers for MCP server connections. Override in conftest."""
    return None


@pytest.fixture(scope="session")
def mcp_stdio_config() -> tuple[str, list[str]]:
    """Stdio command and args for MCP server. Override in conftest."""
    return ("python", ["-m", "mcp_server", "stdio"])


@pytest_asyncio.fixture
async def test_agent(
    mcp_server_url: str,
    mcp_http_headers: dict[str, str] | None,
    mcp_stdio_config: tuple[str, list[str]],
    mcp_memory_token_limit: int,
    verbose_logger: logging.Logger,
    request: pytest.FixtureRequest,
):
    """Create and configure a test agent for the current LLM configuration."""
    llm_config = request.node.callspec.params["llm_config"]
    stdio_command, stdio_args = mcp_stdio_config

    agent = MCPAgentWrapper(
        server_url=mcp_server_url,
        api_url=llm_config["MODEL_API"],
        model_id=llm_config["MODEL_ID"],
        api_key=llm_config["USER_KEY"],
        verbose_logger=verbose_logger,
        mcp_http_headers=mcp_http_headers,
        stdio_command=stdio_command,
        stdio_args=stdio_args,
        token_limit=mcp_memory_token_limit,
    )
    verbose_logger.info("🧪 Testing the model: %s", agent.model_id)

    try:
        await agent.initialize()
        yield agent
    finally:
        await agent.aclose()


def _node_requests_llm_tracing(node: pytest.Item) -> bool:
    """Return True when the test uses the LLM matrix (``llm_config`` parametrization)."""
    callspec = getattr(node, "callspec", None)
    return callspec is not None and "llm_config" in callspec.params


@pytest.fixture(scope="session", autouse=True)
def llm_test_tracing(request: pytest.FixtureRequest):
    """Enable DeepEval LlamaIndex tracing for LLM integration tests only."""
    if not request.session.items:
        yield
        return
    if not any(_node_requests_llm_tracing(item) for item in request.session.items):
        yield
        return
    enable_llm_test_tracing()
    yield


@pytest.fixture
def guardian_agent(verbose_logger: logging.Logger, request: pytest.FixtureRequest):  # pylint: disable=redefined-outer-name
    """Create and configure a guardian agent for evaluation."""
    llm_config = request.node.callspec.params["llm_config"]

    if guardian_llm_config:
        config = guardian_llm_config
    else:
        config = llm_config

    agent = gpt_model_from_config(config)

    verbose_logger.info("🧪 Verifying with the model: %s", agent.get_model_name())

    return agent


@pytest.fixture
def verbose_logger(request: pytest.FixtureRequest):
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
