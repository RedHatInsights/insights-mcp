"""Integration tests for LLM functionality with MCP server using deepeval.
This includes more difficult questions to the LLM
"""

import pytest
from mcp_llm_eval.deepeval_support.judges import build_test_case, evaluate_behavioral, evaluate_tool_correctness
from mcp_llm_eval.utils import (
    load_llm_configurations,
    should_skip_llm_matrix_tests,
)

from image_builder_mcp.test_prompts import PROMPTS
from tests.utils import should_skip_insights_llm_tests

# Load LLM configurations for parametrization
llm_configurations, _ = load_llm_configurations()


@pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No valid LLM configurations found")
@pytest.mark.skipif(
    should_skip_insights_llm_tests(),
    reason="INSIGHTS_CLIENT_ID and INSIGHTS_CLIENT_SECRET (or LIGHTSPEED_* equivalents) required",
)
@pytest.mark.llm
# pylint: disable=too-few-public-methods
class TestLLMIntegrationHard:
    """Test LLM integration with MCP server using deepeval with multiple LLM configurations."""

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self, test_agent, guardian_agent, verbose_logger, llm_config):  # pylint: disable=redefined-outer-name
        """Test complete conversation flow with proper agent behavior."""
        prompt = PROMPTS["complete_conversation_flow"]

        response, _, tools_executed, _ = await test_agent.execute_with_reasoning(prompt, chat_history=[])

        test_case = build_test_case(prompt, response, tools_executed, ["image-builder__get_blueprints"])

        await evaluate_tool_correctness(test_case, guardian_agent, verbose_logger)

        # Define conversation flow metric using custom LLM
        await evaluate_behavioral(
            test_case,
            (
                "The conversation should demonstrate proper agent behavior:\n"
                "1. Understanding user intent\n"
                "2. Using appropriate tools to gather information or providing helpful and informative responses\n"
                "3. The 'content' of the conversation contains only json then this is considered a failure\n"
                "4. Take care that tool calls are properly part of a 'tool_call' object\n"
            ),
            guardian_agent,
            verbose_logger,
        )

        verbose_logger.info("✓ Complete conversation flow test passed for %s", llm_config["name"])
