"""LLM integration tests for inventory MCP prompts."""

from inventory_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestInventoryLLMPrompts = create_test_suite(
    PROMPTS,
    "TestInventoryLLMPrompts",
)
