"""LLM integration tests for image-builder MCP prompts."""

from mcp_llm_eval.generators import create_test_suite

from image_builder_mcp.test_prompts import PROMPTS

TestImageBuilderLLMPrompts = create_test_suite(
    "image-builder",
    PROMPTS,
    "TestImageBuilderLLMPrompts",
)
