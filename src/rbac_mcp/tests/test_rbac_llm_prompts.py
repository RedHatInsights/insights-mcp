"""LLM integration tests for RBAC MCP prompts."""

from rbac_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestRbacLLMPrompts = create_test_suite(
    PROMPTS,
    "TestRbacLLMPrompts",
)
