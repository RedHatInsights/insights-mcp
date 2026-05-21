"""LLM integration tests for planning MCP prompts."""

from planning_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestPlanningLLMPrompts = create_llm_prompt_test_class(
    "planning",
    PROMPTS,
    "TestPlanningLLMPrompts",
)
