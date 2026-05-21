"""LLM integration tests for image-builder MCP prompts."""

from image_builder_mcp.test_prompts import PROMPTS
from tests.llm_prompt_support import create_llm_prompt_test_class

TestImageBuilderLLMPrompts = create_llm_prompt_test_class(
    "image-builder",
    PROMPTS,
    "TestImageBuilderLLMPrompts",
)
