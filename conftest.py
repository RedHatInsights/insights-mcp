"""Root conftest — overrides mcp_llm_eval defaults for this project."""

import nest_asyncio
import pytest

from insights_mcp.config import (
    BRAND_CLIENT_ID_HEADER,
    BRAND_CLIENT_SECRET_HEADER,
    INSIGHTS_CLIENT_ID,
    INSIGHTS_CLIENT_SECRET,
)
from tests.utils import should_skip_insights_llm_tests


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip project LLM tests when Insights credentials are unavailable."""
    if not should_skip_insights_llm_tests():
        return

    skip = pytest.mark.skip(
        reason="INSIGHTS_CLIENT_ID and INSIGHTS_CLIENT_SECRET (or LIGHTSPEED_* equivalents) required"
    )
    for item in items:
        if item.get_closest_marker("llm") is not None:
            item.add_marker(skip)


# Prevent Python 3.14 event loop corruption caused by deepeval calling
# nest_asyncio.apply().
nest_asyncio.apply = lambda: None

pytest_plugins = ("mcp_llm_eval.fixtures",)


@pytest.fixture(scope="session")
def mcp_http_headers() -> dict[str, str] | None:
    """Provide project authentication headers for HTTP MCP tests."""
    if INSIGHTS_CLIENT_ID and INSIGHTS_CLIENT_SECRET:
        return {
            BRAND_CLIENT_ID_HEADER: INSIGHTS_CLIENT_ID,
            BRAND_CLIENT_SECRET_HEADER: INSIGHTS_CLIENT_SECRET,
        }
    return None


@pytest.fixture(scope="session")
def mcp_stdio_config() -> tuple[str, list[str]]:
    """Configure the project MCP server command for stdio tests."""
    return ("python", ["-m", "insights_mcp.server", "stdio"])
