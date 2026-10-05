"""LLM integration tests for content-sources MCP prompts."""

from content_sources_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestContentSourcesLLMPrompts = create_test_suite(
    PROMPTS,
    "TestContentSourcesLLMPrompts",
)
