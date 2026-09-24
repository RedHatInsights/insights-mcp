"""LLM integration tests for advisor MCP prompts."""

from advisor_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestAdvisorLLMPrompts = create_test_suite(
    PROMPTS,
    "TestAdvisorLLMPrompts",
)
