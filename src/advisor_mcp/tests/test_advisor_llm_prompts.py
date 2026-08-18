"""LLM integration tests for advisor MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from advisor_mcp.test_prompts import PROMPTS

TestAdvisorLLMPrompts = create_test_suite(
    "advisor",
    PROMPTS,
    "TestAdvisorLLMPrompts",
)
