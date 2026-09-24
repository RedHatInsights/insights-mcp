"""LLM integration tests for image-builder MCP prompts."""

from image_builder_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestImageBuilderLLMPrompts = create_test_suite(
    PROMPTS,
    "TestImageBuilderLLMPrompts",
)
