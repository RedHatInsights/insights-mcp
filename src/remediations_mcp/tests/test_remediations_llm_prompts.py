"""LLM integration tests for remediations MCP prompts."""

from remediations_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestRemediationsLLMPrompts = create_test_suite(
    PROMPTS,
    "TestRemediationsLLMPrompts",
)
