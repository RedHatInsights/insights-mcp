"""LLM integration tests for planning MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from planning_mcp.test_prompts import PROMPTS

TestPlanningLLMPrompts = create_test_suite(
    PROMPTS,
    "TestPlanningLLMPrompts",
)
