"""LLM integration tests for advisor MCP prompts."""

from advisor_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestAdvisorLLMPrompts = create_llm_prompt_test_class(
    "advisor",
    PROMPTS,
    "TestAdvisorLLMPrompts",
)
