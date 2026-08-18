"""LLM integration tests for RHSM MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from rhsm_mcp.test_prompts import PROMPTS

TestRhsmLLMPrompts = create_test_suite(
    "rhsm",
    PROMPTS,
    "TestRhsmLLMPrompts",
)
