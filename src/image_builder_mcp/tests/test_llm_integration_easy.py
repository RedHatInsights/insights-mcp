"""Integration tests for LLM functionality with MCP server using deepeval.
This includes easy questions to the LLM, that should work out of the box.
Updated to use the simplified agent approach with WorkflowCheckpointer.
"""

import pytest
from deepeval.test_case import LLMTestCase, ToolCall
from mcp_llm_eval.deepeval_support.judges import build_test_case, evaluate_compliance, evaluate_tool_correctness
from mcp_llm_eval.llm_prompt_support import assert_no_forbidden_tool

from image_builder_mcp.test_prompts import PROMPTS
from tests.utils import (
    load_llm_configurations,
    pretty_print_chat_history,
    should_skip_insights_llm_tests,
    should_skip_llm_matrix_tests,
)

GUARDIAN_SCENARIOS = PROMPTS.guardian_scenarios()
TOOL_USAGE_SCENARIOS = PROMPTS.tool_usage_scenarios(exclude={s["prompt_id"] for s in GUARDIAN_SCENARIOS})

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
    @pytest.mark.parametrize("scenario", GUARDIAN_SCENARIOS, ids=[s["prompt_id"] for s in GUARDIAN_SCENARIOS])
    @pytest.mark.asyncio
    # pylint: disable=redefined-outer-name
    async def test_guardian_evaluation(self, test_agent, guardian_agent, llm_config, verbose_logger, scenario):
        """Test that LLM follows behavioral rules using guardian-judged evaluation."""
        prompt = scenario["prompt"]

        response, _, tools_executed, _ = await test_agent.execute_with_reasoning(prompt, chat_history=[])

        assert_no_forbidden_tool(tools_executed, scenario["forbidden_tools"])

        test_case = build_test_case(prompt, response, tools_executed, scenario["expected_tools"])

        await evaluate_tool_correctness(test_case, guardian_agent, verbose_logger)
        await evaluate_compliance(test_case, scenario["guardian_criteria"], guardian_agent, verbose_logger)

        verbose_logger.info("✓ Guardian evaluation passed for %s with prompt: %s", llm_config["name"], prompt)

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.parametrize(
        "scenario", TOOL_USAGE_SCENARIOS, ids=[scenario["prompt"] for scenario in TOOL_USAGE_SCENARIOS]
    )
    @pytest.mark.asyncio
    # pylint: disable=redefined-outer-name
    async def test_tool_usage_patterns(self, test_agent, guardian_agent, verbose_logger, llm_config, scenario):
        """Test various tool usage patterns and their appropriateness."""
        response, _, tools_executed, _ = await test_agent.execute_with_reasoning(scenario["prompt"], chat_history=[])

        tool_names = [tool.name for tool in tools_executed]
        verbose_logger.info("  Model: %s", llm_config["name"])
        verbose_logger.info("  Prompt: %s", scenario["prompt"])
        verbose_logger.info("  Expected: %s", scenario["expected_tools"])
        verbose_logger.info("  Tools called: %s", tool_names)
        verbose_logger.info("  Response: %s", response)

        test_case = build_test_case(scenario["prompt"], response, tools_executed, scenario["expected_tools"])
        await evaluate_tool_correctness(test_case, guardian_agent, verbose_logger)

        verbose_logger.info(
            "✓ Tool usage pattern test passed for %s with prompt: %s", llm_config["name"], scenario["prompt"]
        )

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

        # Paging stays under Memory token_limit; waterfall must not drop prior turns.
        archived = await test_agent.get_archived_messages()
        assert archived == [], (
            f"Memory archived {len(archived)} message(s) for {llm_config['name']}; "
            "paging test should stay under token_limit"
        )
        active_tokens = await test_agent.get_active_memory_token_estimate()
        verbose_logger.info(
            "Active memory estimate: %d tokens (limit %d)",
            active_tokens,
            test_agent._memory.token_limit,
        )
