"""LLM integration tests for content-sources MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from content_sources_mcp.test_prompts import PROMPTS

TestContentSourcesLLMPrompts = create_test_suite(
    PROMPTS,
    "TestContentSourcesLLMPrompts",
)
