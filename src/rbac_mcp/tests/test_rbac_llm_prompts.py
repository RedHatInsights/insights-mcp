"""LLM integration tests for RBAC MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from rbac_mcp.test_prompts import PROMPTS

TestRbacLLMPrompts = create_test_suite(
    PROMPTS,
    "TestRbacLLMPrompts",
)
