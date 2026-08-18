"""Integration tests for LLM functionality with MCP server using deepeval.
This includes easy questions to the LLM, that should work out of the box.
Updated to use the simplified agent approach with WorkflowCheckpointer.
"""

import pytest
from deepeval.test_case import LLMTestCase, ToolCall
from mcp_llm_eval.deepeval_support.judges import build_test_case, evaluate_tool_correctness
from mcp_llm_eval.utils import (
    load_llm_configurations,
    pretty_print_chat_history,
    should_skip_llm_matrix_tests,
)

from image_builder_mcp.test_prompts import PROMPTS
from tests.utils import should_skip_insights_llm_tests

# Load LLM configurations for parametrization
llm_configurations, _ = load_llm_configurations()


@pytest.mark.skipif(
    should_skip_llm_matrix_tests(),
    reason="No valid LLM configurations found",
)
@pytest.mark.skipif(
    should_skip_insights_llm_tests(),
    reason="INSIGHTS_CLIENT_ID and INSIGHTS_CLIENT_SECRET (or LIGHTSPEED_* equivalents) required",
)
@pytest.mark.llm
class TestLLMIntegrationEasy:
    """Test LLM integration with MCP server using deepeval with multiple LLM configurations."""

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.asyncio
    async def test_llm_paging(self, test_agent, guardian_agent, verbose_logger, llm_config):  # pylint: disable=redefined-outer-name,too-many-locals
        """Test that the LLM can page through results."""
        paging_turns = PROMPTS.turns_for("llm_paging")
        prompt = paging_turns[0]

        response, _, tools_executed, conversation_history = await test_agent.execute_with_reasoning(
            prompt, chat_history=[]
        )
        test_case_initial = build_test_case(prompt, response, tools_executed, ["image-builder__get_blueprints"])
        await evaluate_tool_correctness(test_case_initial, guardian_agent, verbose_logger)

        # Now ask for more with conversation context
        follow_up_prompt = paging_turns[1]

        # conversation_history from simplified agent is already ChatMessage objects
        (
            response,
            _,
            tools_executed,
            updated_chat_history,
        ) = await test_agent.execute_with_reasoning(follow_up_prompt, chat_history=conversation_history)

        pretty_print_chat_history(updated_chat_history, llm_config["name"], verbose_logger)

        test_case_subsequent = build_test_case(follow_up_prompt, response, tools_executed, tools_executed)

        expected_tools = [ToolCall(name="image-builder__get_blueprints", arguments={"limit": 3, "offset": 2})]

        test_case_subsequent = LLMTestCase(
            input=follow_up_prompt, actual_output=response, tools_called=tools_executed, expected_tools=expected_tools
        )

        await evaluate_tool_correctness(test_case_subsequent, guardian_agent, verbose_logger)
