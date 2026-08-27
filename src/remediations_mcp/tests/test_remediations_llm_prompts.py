"""LLM integration tests for remediations MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from remediations_mcp.test_prompts import PROMPTS

TestRemediationsLLMPrompts = create_test_suite(
    PROMPTS,
    "TestRemediationsLLMPrompts",
)
