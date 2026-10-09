"""LLM integration tests for OCP Advisor MCP prompts."""

from ocp_advisor_mcp.test_prompts import PROMPTS
from tests.mcp_llm_eval.generators import create_test_suite

TestOcpAdvisorLLMPrompts = create_test_suite(
    PROMPTS,
    "TestOcpAdvisorLLMPrompts",
)
