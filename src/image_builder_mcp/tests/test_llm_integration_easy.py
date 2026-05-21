"""Integration tests for LLM functionality with MCP server using deepeval.
This includes easy questions to the LLM, that should work out of the box.
Updated to use the simplified agent approach with WorkflowCheckpointer.
"""

import pytest
from deepeval.metrics import GEval, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams, ToolCall

from image_builder_mcp.test_prompts import PROMPTS
from tests.utils import (
    load_llm_configurations,
    pretty_print_chat_history,
    should_skip_insights_llm_tests,
    should_skip_llm_matrix_tests,
)

TOOL_USAGE_SCENARIOS = PROMPTS.tool_usage_scenarios()

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
    # pylint: disable=redefined-outer-name,too-many-locals
    async def test_rhel_initial_question(self, test_agent, guardian_agent, llm_config, verbose_logger):
        """Test that LLM follows behavioral rules and doesn't immediately call create_blueprint."""
        prompt = PROMPTS["rhel_initial_question"]

        # Execute tools and capture reasoning steps and tool calls
        response, reasoning_steps, tools_executed, _ = await test_agent.execute_with_reasoning(prompt, chat_history=[])

        # Check that create_blueprint is not called immediately
        tool_names = [tool.name for tool in tools_executed]
        assert "image-builder__create_blueprint" not in tool_names, (
            f"❌ BEHAVIORAL RULE VIOLATION for {llm_config['name']} "
            f"({llm_config['MODEL_ID']}): "
            f"LLM called image-builder__create_blueprint immediately! Tool calls: {tool_names}. "
            f"MCP instructions not working correctly.\nThe prompt was: {prompt}\n"
            f"The response was: {response}\n"
        )

        test_case = LLMTestCase(input=prompt, actual_output=response, expected_tools=[], tools_called=tools_executed)

        # Define expected behavior metric using custom LLM
        behavioral_compliance = GEval(
            name="Behavioral Compliance",
            criteria=(
                "The LLM should NOT immediately call image-builder__create_blueprint. "
                "Instead, it should either ask for more information about requirements (distributions, "
                "architectures, image types etc.) or optionally use get_openapi to understand the system first."
                "In any case the response should be targeted to the user for more information."
            ),
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.TOOLS_CALLED],
            model=guardian_agent,
        )

        verbose_logger.info("🤔 Checking response with guardian agent %s…", guardian_agent.name)

        # Measure once to get access to explanation and avoid double LLM call
        behavioral_compliance.measure(test_case)

        # Log detailed evaluation results
        verbose_logger.info(
            "📊 Behavioral Compliance Score: %.2f (threshold: %.2f)",
            behavioral_compliance.score,
            behavioral_compliance.threshold,
        )
        verbose_logger.info("📝 Guardian Agent Explanation: %s", behavioral_compliance.reason)

        # Assert using success property (no additional LLM call)
        assert behavioral_compliance.success, (
            f"Behavioral compliance test failed. Score: {behavioral_compliance.score:.2f}, "
            f"Threshold: {behavioral_compliance.threshold:.2f}. "
            f"Reason: {behavioral_compliance.reason}"
        )

        verbose_logger.info("✅ Test passed for %s", prompt)
        verbose_logger.info("Response: %s", response)
        verbose_logger.info("Tool calls executed: %s", [tool.name for tool in tools_executed])
        verbose_logger.info("Reasoning steps captured: %d", len(reasoning_steps))

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.asyncio
    # pylint: disable=redefined-outer-name,too-many-locals
    async def test_image_build_status_tool_selection(self, test_agent, verbose_logger, llm_config, guardian_agent):
        """Test that LLM selects appropriate tools for image build status queries."""
        if "mistral" in llm_config["name"].lower():
            pytest.skip("Mistral on the Lightspeed gateway does not reliably use the image-builder tool catalog")

        tool_correctness = ToolCorrectnessMetric(threshold=0.7, include_reason=True, model=guardian_agent)

        prompt = PROMPTS["image_build_status"]

        response, _, tools_executed, _ = await test_agent.execute_with_reasoning(prompt, chat_history=[])

        # first we check if there is a question in the response for the name or UUID of the compose
        contains_question = GEval(
            name="Contains Question",
            criteria=("The response should contain a question for the name or UUID of the compose"),
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            model=guardian_agent,
        )

        question_test_case = LLMTestCase(
            input=prompt,
            actual_output=response,
        )

        answered_with_question = None
        # if this fails that's ok, we can continue
        try:
            verbose_logger.info("🤔 Checking response with guardian agent %s…", guardian_agent.name)

            # Measure once to get access to explanation and avoid double LLM call
            contains_question.measure(question_test_case)
            verbose_logger.info("📊 Contains Question Score: %.2f", contains_question.score)
            verbose_logger.info("📝 Guardian Agent Explanation: %s", contains_question.reason)

            # Assert using success property (no additional LLM call)
            assert contains_question.success, (
                f"Contains question test failed. Score: {contains_question.score:.2f}, "
                f"Threshold: {contains_question.threshold:.2f}. "
                f"Reason: {contains_question.reason}"
            )
            verbose_logger.info("✓ LLM %s correctly answered with a question", llm_config["name"])
        except AssertionError as e:
            answered_with_question = e
            verbose_logger.info("Question test case failed, continuing...")

        # Define expected tools for this query
        expected_tools = [
            ToolCall(name="image-builder__get_composes"),
            # Could also include get_compose_details if compose ID is known
        ]

        test_case = LLMTestCase(
            input=prompt, actual_output=response, tools_called=tools_executed, expected_tools=expected_tools
        )

        # Check if relevant tools were selected
        tool_names = [tool.name for tool in tools_executed]
        expected_tool_names = ["image-builder__get_composes", "image-builder__get_compose_details"]

        found_relevant = any(tool in tool_names for tool in expected_tool_names)

        if found_relevant:
            verbose_logger.info("✓ LLM %s correctly selected relevant tools", llm_config["name"])
        else:
            verbose_logger.warning("LLM %s may not have selected optimal tools: %s", llm_config["name"], tool_names)

        answered_with_tools = None
        try:
            verbose_logger.info("🤔 Checking tool correctness")

            # Measure once to get access to explanation and avoid double LLM call
            tool_correctness.measure(test_case)
            verbose_logger.info(
                "📊 Tool Correctness Score: %.2f (threshold: %.2f)", tool_correctness.score, tool_correctness.threshold
            )
            verbose_logger.info("📝 Tool Correctness Explanation: %s", tool_correctness.reason)

            # Assert using success property (no additional LLM call)
            assert tool_correctness.success, (
                f"Tool correctness test failed. Score: {tool_correctness.score:.2f}, "
                f"Threshold: {tool_correctness.threshold:.2f}. "
                f"Reason: {tool_correctness.reason}"
            )
            verbose_logger.info("✓ LLM %s correctly used the tools", llm_config["name"])
        except AssertionError as e:
            answered_with_tools = e
            verbose_logger.info("Tool correctness test case failed, continuing...")

        assert answered_with_question is None or answered_with_tools is None, "One of the tests have to succeed"

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.parametrize(
        "scenario", TOOL_USAGE_SCENARIOS, ids=[scenario["prompt"] for scenario in TOOL_USAGE_SCENARIOS]
    )
    @pytest.mark.asyncio
    # pylint: disable=redefined-outer-name
    async def test_tool_usage_patterns(self, test_agent, guardian_agent, verbose_logger, llm_config, scenario):
        """Test various tool usage patterns and their appropriateness."""
        response, _, tools_executed, _ = await test_agent.execute_with_reasoning(scenario["prompt"], chat_history=[])
        expected_tools = [ToolCall(name=name) for name in scenario["expected_tools"]]

        test_case = LLMTestCase(
            input=scenario["prompt"], actual_output=response, tools_called=tools_executed, expected_tools=expected_tools
        )

        tool_names = [tool.name for tool in tools_executed]
        verbose_logger.info("  Model: %s", llm_config["name"])
        verbose_logger.info("  Prompt: %s", scenario["prompt"])
        verbose_logger.info("  Expected: %s", scenario["expected_tools"])
        verbose_logger.info("  Tools called: %s", tool_names)
        verbose_logger.info("  Response: %s", response)

        tool_correctness = ToolCorrectnessMetric(threshold=0.6, model=guardian_agent)

        # Evaluate with deepeval
        verbose_logger.info("🤔 Checking tool correctness")

        # Measure once to get access to explanation and avoid double LLM call
        tool_correctness.measure(test_case)
        verbose_logger.info(
            "📊 Tool Correctness Score: %.2f (threshold: %.2f)", tool_correctness.score, tool_correctness.threshold
        )
        verbose_logger.info("📝 Tool Correctness Explanation: %s", tool_correctness.reason)

        # Assert using success property (no additional LLM call)
        assert tool_correctness.success, (
            f"Tool correctness test failed. Score: {tool_correctness.score:.2f}, "
            f"Threshold: {tool_correctness.threshold:.2f}. "
            f"Reason: {tool_correctness.reason}"
        )

        verbose_logger.info(
            "✓ Tool usage pattern test passed for %s with prompt: %s", llm_config["name"], scenario["prompt"]
        )

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.asyncio
    async def test_llm_paging(self, test_agent, guardian_agent, verbose_logger, llm_config):  # pylint: disable=redefined-outer-name,too-many-locals
        """Test that the LLM can page through results."""
        prompt = PROMPTS["llm_paging_1"]

        response, _, tools_executed, conversation_history = await test_agent.execute_with_reasoning(
            prompt, chat_history=[]
        )
        expected_tools = [ToolCall(name="image-builder__get_blueprints")]

        test_case_initial = LLMTestCase(
            input=prompt, actual_output=response, tools_called=tools_executed, expected_tools=expected_tools
        )
        tool_correctness = ToolCorrectnessMetric(threshold=0.6, model=guardian_agent)

        # Measure once to get access to explanation and avoid double LLM call
        tool_correctness.measure(test_case_initial)
        verbose_logger.info(
            "📊 Initial Tool Correctness Score: %.2f (threshold: %.2f)",
            tool_correctness.score,
            tool_correctness.threshold,
        )
        verbose_logger.info("📝 Initial Tool Correctness Explanation: %s", tool_correctness.reason)

        # Assert using success property (no additional LLM call)
        assert tool_correctness.success, (
            f"Initial tool correctness test failed. Score: {tool_correctness.score:.2f}, "
            f"Threshold: {tool_correctness.threshold:.2f}. "
            f"Reason: {tool_correctness.reason}"
        )

        # Now ask for more with conversation context
        follow_up_prompt = PROMPTS["llm_paging_2"]

        # conversation_history from simplified agent is already ChatMessage objects
        (
            response,
            _,
            tools_executed,
            updated_chat_history,
        ) = await test_agent.execute_with_reasoning(follow_up_prompt, chat_history=conversation_history)

        pretty_print_chat_history(updated_chat_history, llm_config["name"], verbose_logger)

        expected_tools = [ToolCall(name="image-builder__get_blueprints", arguments={"limit": 3, "offset": 2})]

        test_case_subsequent = LLMTestCase(
            input=follow_up_prompt, actual_output=response, tools_called=tools_executed, expected_tools=expected_tools
        )
        tool_correctness = ToolCorrectnessMetric(threshold=0.6, model=guardian_agent)

        verbose_logger.info("🤔 Checking tool correctness")

        # Measure once to get access to explanation and avoid double LLM call
        tool_correctness.measure(test_case_subsequent)
        verbose_logger.info(
            "📊 Subsequent Tool Correctness Score: %.2f (threshold: %.2f)",
            tool_correctness.score,
            tool_correctness.threshold,
        )
        verbose_logger.info("📝 Subsequent Tool Correctness Explanation: %s", tool_correctness.reason)

        # Assert using success property (no additional LLM call)
        assert tool_correctness.success, (
            f"Subsequent tool correctness test failed. Score: {tool_correctness.score:.2f}, "
            f"Threshold: {tool_correctness.threshold:.2f}. "
            f"Reason: {tool_correctness.reason}"
        )

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

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    @pytest.mark.asyncio
    # pylint: disable=redefined-outer-name,too-many-locals
    async def test_list_image_types(self, test_agent, guardian_agent, llm_config, verbose_logger):
        """Test that LLM uses get_openapi for image type discovery instead of create_blueprint."""
        prompt = PROMPTS["list_image_types"]

        # Execute tools and capture reasoning steps and tool calls
        response, reasoning_steps, tools_executed, _ = await test_agent.execute_with_reasoning(prompt, chat_history=[])

        # Check that create_blueprint is not called immediately
        tool_names = [tool.name for tool in tools_executed]
        assert "image-builder__create_blueprint" not in tool_names, (
            f"❌ BEHAVIORAL RULE VIOLATION for {llm_config['name']} "
            f"({llm_config['MODEL_ID']}): "
            f"LLM called image-builder__create_blueprint immediately! Tool calls: {tool_names}. "
            f"MCP instructions not working correctly.\nThe prompt was: {prompt}\n"
            f"The response was: {response}\n"
        )

        test_case = LLMTestCase(input=prompt, actual_output=response, expected_tools=[], tools_called=tools_executed)

        # Define expected behavior metric using custom LLM
        behavioral_compliance = GEval(
            name="Behavioral Compliance",
            criteria=(
                "The response should list the available image types"
                "the response must not contain edge-commit, edge-installer, rhel-edge-commit, "
                "rhel-edge-installer or report them as deprecated image types"
            ),
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT],
            model=guardian_agent,
        )

        verbose_logger.info("🤔 Checking response with guardian agent %s…", guardian_agent.name)

        # Measure once to get access to explanation and avoid double LLM call
        behavioral_compliance.measure(test_case)

        # Log detailed evaluation results
        verbose_logger.info(
            "📊 Behavioral Compliance Score: %.2f (threshold: %.2f)",
            behavioral_compliance.score,
            behavioral_compliance.threshold,
        )
        verbose_logger.info("📝 Guardian Agent Explanation: %s", behavioral_compliance.reason)

        assert behavioral_compliance.success, (
            f"Behavioral compliance test failed. Score: {behavioral_compliance.score:.2f}, "
            f"Threshold: {behavioral_compliance.threshold:.2f}. "
            f"Reason: {behavioral_compliance.reason}"
        )

        verbose_logger.info("✅ Test passed for %s", prompt)
        verbose_logger.info("Response: %s", response)
        verbose_logger.info("Tool calls executed: %s", [tool.name for tool in tools_executed])
        verbose_logger.info("Reasoning steps captured: %d", len(reasoning_steps))
