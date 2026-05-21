"""LLM integration tests for remediations MCP prompts."""

from remediations_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestRemediationsLLMPrompts = create_llm_prompt_test_class(
    "remediations",
    PROMPTS,
    "TestRemediationsLLMPrompts",
)
