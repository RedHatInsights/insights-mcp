"""LLM integration tests for planning MCP prompts."""

from planning_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestPlanningLLMPrompts = create_test_suite(
    PROMPTS,
    "TestPlanningLLMPrompts",
)
