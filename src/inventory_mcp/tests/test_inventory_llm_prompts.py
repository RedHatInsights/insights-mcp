"""LLM integration tests for inventory MCP prompts."""

from inventory_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestInventoryLLMPrompts = create_llm_prompt_test_class(
    "inventory",
    PROMPTS,
    "TestInventoryLLMPrompts",
)
