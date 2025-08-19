"""Integration tests for LLM functionality with MCP server using deepeval.
This includes more difficult questions to the LLM
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall
from deepeval.metrics import GEval, ToolCorrectnessMetric

from tests.utils import (
    should_skip_llm_matrix_tests,
    load_llm_configurations,
)
from tests.utils import pretty_print_chat_history


# Load LLM configurations for parametrization
llm_configurations, _ = load_llm_configurations()


@pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No valid LLM configurations found")
# pylint: disable=too-few-public-methods
class TestLLMIntegrationHard:
    """Test LLM integration with MCP server using deepeval with multiple LLM configurations."""

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self, test_agent, guardian_agent, verbose_logger, llm_config):  # pylint: disable=redefined-outer-name
        """Test complete conversation flow with proper agent behavior."""

        prompt = "Can you help me understand what blueprints are available?"

        response, _reasoning_steps, tools_executed, conversation_history = await test_agent.execute_with_reasoning(
            prompt, chat_history=[]
        )

        expected_tools = [ToolCall(name="get_blueprints"), ToolCall(name="get_openapi")]

        test_case = LLMTestCase(
            input=prompt, actual_output=response, tools_called=tools_executed, expected_tools=expected_tools
        )

        verbose_logger.info("Conversation prompt for %s: %s", llm_config["name"], prompt)
        verbose_logger.info("Tools called: %s", [tool.name for tool in tools_executed])

        pretty_print_chat_history(conversation_history, llm_config["name"], verbose_logger)

        # Define conversation flow metric using custom LLM
        conversation_quality = GEval(
            name="Conversation Flow Quality",
            criteria=(
                "The conversation should demonstrate proper agent behavior:\n"
                "1. Understanding user intent\n"
                "2. Using appropriate tools to gather information or providing helpful and informative responses\n"
                "3. The 'content' of the conversation contains only json then this is considered a failure\n"
                "4. Take care that tool calls are properly part of a 'tool_call' object\n"
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.TOOLS_CALLED,
            ],
            model=guardian_agent,
        )

        # Add a strict tool correctness check to fail when expected tools are not called
        tool_correctness = ToolCorrectnessMetric(threshold=0.6)

        # Evaluate with deepeval metrics
        assert_test(test_case, [conversation_quality, tool_correctness])

        verbose_logger.info("✓ Complete conversation flow test passed for %s", llm_config["name"])
