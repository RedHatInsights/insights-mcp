"""LLM integration tests for inventory MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from inventory_mcp.test_prompts import PROMPTS

TestInventoryLLMPrompts = create_test_suite(
    "inventory",
    PROMPTS,
    "TestInventoryLLMPrompts",
)
