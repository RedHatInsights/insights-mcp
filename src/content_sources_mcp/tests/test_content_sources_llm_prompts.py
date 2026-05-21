"""LLM integration tests for content-sources MCP prompts."""

from content_sources_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestContentSourcesLLMPrompts = create_llm_prompt_test_class(
    "content-sources",
    PROMPTS,
    "TestContentSourcesLLMPrompts",
)
