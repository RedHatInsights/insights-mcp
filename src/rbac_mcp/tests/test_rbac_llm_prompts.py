"""LLM integration tests for RBAC MCP prompts."""

from rbac_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestRbacLLMPrompts = create_llm_prompt_test_class(
    "rbac",
    PROMPTS,
    "TestRbacLLMPrompts",
)
