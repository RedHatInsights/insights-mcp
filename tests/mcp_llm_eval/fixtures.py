"""Reusable pytest fixtures for MCP LLM evaluation tests."""

import logging

import pytest
from mcp_llm_eval.llm_tracing import enable_llm_test_tracing
from mcp_llm_eval.utils import gpt_model_from_config, load_llm_configurations

# Load LLM configurations for fixtures
_, guardian_llm_config = load_llm_configurations()


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
