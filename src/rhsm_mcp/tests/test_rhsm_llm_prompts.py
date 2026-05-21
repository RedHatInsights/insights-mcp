"""LLM integration tests for RHSM MCP prompts."""

from rhsm_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestRhsmLLMPrompts = create_llm_prompt_test_class(
    "rhsm",
    PROMPTS,
    "TestRhsmLLMPrompts",
)
