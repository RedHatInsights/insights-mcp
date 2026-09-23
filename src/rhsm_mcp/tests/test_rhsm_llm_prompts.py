"""LLM integration tests for RHSM MCP prompts."""

from rhsm_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestRhsmLLMPrompts = create_test_suite(
    PROMPTS,
    "TestRhsmLLMPrompts",
)
