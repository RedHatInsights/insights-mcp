"""Integration tests for LLM functionality with MCP server using deepeval.
This includes more difficult questions to the LLM
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall
from deepeval.metrics import GEval

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
    def test_complete_conversation_flow(self, test_agent, guardian_agent, verbose_logger, llm_config):  # pylint: disable=redefined-outer-name
        """Test complete conversation flow with proper agent behavior."""

        prompt = "Can you help me understand what blueprints are available?"

        response, tools_intended, conversation_history = test_agent.execute_tools_with_messages(prompt, verbose_logger)

        expected_tools = [ToolCall(name="get_blueprints"), ToolCall(name="get_openapi")]

        test_case = LLMTestCase(
            input=prompt, actual_output=response, tools_called=tools_intended, expected_tools=expected_tools
        )

        verbose_logger.info("Conversation prompt for %s: %s", llm_config["name"], prompt)
        verbose_logger.info("Tools called: %s", [tool.name for tool in tools_intended])
        verbose_logger.info(
            "Full conversation history:\n%s",
            pretty_print_chat_history(conversation_history, llm_config["name"], verbose_logger),
        )

        # Define conversation flow metric using custom LLM
        conversation_quality = GEval(
            name="Conversation Flow Quality",
            criteria=(
                "The conversation should demonstrate proper agent behavior:\n"
                "1. Understanding user intent\n"
                "2. Using appropriate tools to gather information or providing helpful and informative responses\n"
                "3. The 'content' of the conversation contains only json then this is considered a failure\n"
                '4. Take care that tool calls are properly part of a "tool_call" object\n'
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.TOOLS_CALLED,
            ],
            model=guardian_agent,
        )

        # Evaluate with deepeval metric
        assert_test(test_case, [conversation_quality])

        verbose_logger.info("✓ Complete conversation flow test passed for %s", llm_config["name"])
