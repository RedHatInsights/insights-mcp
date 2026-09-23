"""Reusable pytest fixtures for MCP LLM evaluation tests."""

from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from .atif_export import (
    AtifTrajectoryBuilder,
    atif_session_id,
    default_logs_dir,
    ensure_phoenix_ready,
    node_display_id,
    phoenix_collector_endpoint,
    phoenix_project_name,
    session_run_id,
    tool_definitions_from_tools,
    trace_export_disabled,
    upload_trajectories,
    write_atif_json,
)
from .llama_index_support.agent_mcp import MCPAgentWrapper
from .llm_tracing import enable_llm_test_tracing
from .utils import abbreviate_middle, gpt_model_from_config, load_llm_configurations

_, guardian_llm_config = load_llm_configurations()

_ATIF_RUN_ID = pytest.StashKey[str]()
_ATIF_RUN_DIR = pytest.StashKey[Path]()
_ATIF_AGENT = pytest.StashKey[MCPAgentWrapper]()


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
async def test_agent(  # pylint: disable=too-many-arguments,too-many-positional-arguments,redefined-outer-name
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
        _attach_atif_recorder(request.node, agent)
        yield agent
    finally:
        await agent.aclose()


def _node_requests_llm_tracing(node: pytest.Item) -> bool:
    """Return True when the test uses the LLM matrix (``llm_config`` parametrization)."""
    callspec = getattr(node, "callspec", None)
    return callspec is not None and "llm_config" in callspec.params


def _item_test_location(item: pytest.Item) -> tuple[str, int]:
    """Return (test_file, test_line) from pytest's item location (1-based line)."""
    path, lineno, _domain = item.location
    test_file = str(path)
    try:
        test_file = str(Path(path).resolve().relative_to(item.config.rootpath.resolve()))
    except ValueError:
        test_file = str(path)
    return test_file, (lineno or 0) + 1


def _attach_atif_recorder(item: pytest.Item, agent: MCPAgentWrapper) -> None:
    """Bind an ATIF recorder to the agent when this session is exporting traces."""
    run_id = item.config.stash.get(_ATIF_RUN_ID, "")
    if not run_id:
        return
    display_id = node_display_id(item.nodeid)
    test_file, test_line = _item_test_location(item)
    agent.atif_recorder = AtifTrajectoryBuilder(
        session_id=atif_session_id(run_id, display_id),
        trajectory_id=display_id,
        pytest_node_id=item.nodeid,
        model_name=agent.model_id,
        tool_definitions=tool_definitions_from_tools(agent.tools),
        test_file=test_file,
        test_line=test_line,
        testrun=run_id,
    )
    item.stash[_ATIF_AGENT] = agent


def _status_message_from_report(report: pytest.TestReport) -> str:
    """Return a pytest failure representation, abbreviated in the middle when too long."""
    if report.outcome != "failed" or report.longrepr is None:
        return ""
    return abbreviate_middle(str(report.longrepr))


def _export_atif_for_item(item: pytest.Item, report: pytest.TestReport) -> None:
    """Write ATIF JSON for an LLM test and optionally upload it to Phoenix."""
    if trace_export_disabled():
        return
    run_dir = item.config.stash.get(_ATIF_RUN_DIR, None)
    run_id = item.config.stash.get(_ATIF_RUN_ID, "")
    if run_dir is None or not run_id:
        return
    agent = item.stash.get(_ATIF_AGENT, None)
    if agent is None or agent.atif_recorder is None:
        return
    recorder = agent.atif_recorder
    if not recorder.has_steps():
        return
    trajectory = recorder.finish(
        pytest_outcome=report.outcome,
        pytest_status_message=_status_message_from_report(report),
    )
    write_atif_json(run_dir / f"{recorder.trajectory_id}.json", trajectory)
    endpoint = phoenix_collector_endpoint()
    if not endpoint:
        return
    upload_trajectories(
        [trajectory],
        project_name=phoenix_project_name(run_id),
        endpoint=endpoint,
    )


def pytest_configure(config: pytest.Config) -> None:
    """Fail fast when Phoenix live upload is requested without arize-phoenix-client."""
    _ = config
    try:
        ensure_phoenix_ready()
    except RuntimeError as exc:
        pytest.exit(str(exc), returncode=2)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Create ``tests/logs/<YYYYMMDDhhmmss>/`` when LLM tests will export traces."""
    if trace_export_disabled():
        return
    items = getattr(session, "items", None) or []
    if not any(_node_requests_llm_tracing(item) for item in items):
        return
    run_id = session_run_id()
    run_dir = default_logs_dir() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    session.config.stash[_ATIF_RUN_ID] = run_id
    session.config.stash[_ATIF_RUN_DIR] = run_dir


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Generator[None, Any, None]:
    """Export ATIF after the test call, including failures."""
    _ = call
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        _export_atif_for_item(item, report)


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
