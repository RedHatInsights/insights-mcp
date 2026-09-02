"""Generate parametrized pytest suites for MCP LLM evaluation scenarios."""

from __future__ import annotations

import logging

import pytest
from deepeval.models import GPTModel
from mcp_llm_eval.data import PromptRegistry, PromptTestScenario
from mcp_llm_eval.deepeval_support.judges import (
    build_conversational_test_case,
    build_turn_test_case,
    evaluate_behavioral,
    evaluate_compliance,
    evaluate_tool_correctness,
)
from mcp_llm_eval.llama_index_support.agent_mcp import MCPAgentWrapper
from mcp_llm_eval.llm_prompt_support import (
    assert_at_least_one_expected_tool,
    assert_correct_tool_args,
    assert_no_forbidden_tool,
    assert_no_memory_overflow,
    resolve_scenario_turns,
    run_scenario_turns,
)
from mcp_llm_eval.utils import load_llm_configurations, pretty_print_chat_history, should_skip_llm_matrix_tests

_LLM_CONFIGURATIONS, _ = load_llm_configurations()


def create_test_suite(toolset: str, prompts: PromptRegistry, class_name: str) -> type:
    """Build a pytest class with one parametrized test per prompt in *prompts*."""
    scenarios = prompts.iter_test_scenarios(toolset)

    @pytest.mark.llm
    @pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No valid LLM configurations found")
    class _GeneratedLLMPromptTests:  # pylint: disable=too-few-public-methods
        """Parametrized LLM tests for one toolset prompt registry."""

        @pytest.mark.parametrize("llm_config", _LLM_CONFIGURATIONS, ids=[c["name"] for c in _LLM_CONFIGURATIONS])
        @pytest.mark.parametrize("scenario", scenarios, ids=lambda s: s.prompt_id)
        @pytest.mark.asyncio
        async def test_llm_eval(
            self,
            test_agent: MCPAgentWrapper,
            guardian_agent: GPTModel,
            scenario: PromptTestScenario,
            llm_api_context: dict[str, str],
            llm_config: dict[str, str],
            verbose_logger: logging.Logger,
        ):  # pylint: disable=redefined-outer-name,unused-argument,too-many-arguments,too-many-positional-arguments
            """Run an LLM eval scenario, assert tool correctness and criteria."""
            turns = resolve_scenario_turns(scenario, llm_api_context)
            responses, tools_per_turn, chat_history = await run_scenario_turns(test_agent, turns)

            for turn_idx, (request, executed_tools, turn_template, response) in enumerate(
                zip(turns, tools_per_turn, scenario.template_turns, responses)
            ):
                assert response.strip(), f"empty assistant response for {llm_config['name']} on {scenario.prompt_id}"

                verbose_logger.info("Turn %d - Expected: %s", turn_idx + 1, turn_template.expected_tools)
                verbose_logger.info("Turn %d - Forbidden: %s", turn_idx + 1, turn_template.forbidden_tools)

                if turn_template.expected_tools:
                    assert_at_least_one_expected_tool(executed_tools, turn_template.expected_tools)
                if turn_template.forbidden_tools:
                    assert_no_forbidden_tool(executed_tools, turn_template.forbidden_tools)
                if turn_template.expected_args:
                    assert_correct_tool_args(executed_tools, turn_template.expected_args)

                turn_test_case = build_turn_test_case(request, response, executed_tools, turn_template.expected_tools)

                await evaluate_tool_correctness(turn_test_case, guardian_agent, verbose_logger)

                if turn_template.turn_criteria:
                    await evaluate_compliance(
                        turn_test_case, turn_template.turn_criteria, guardian_agent, verbose_logger
                    )

            if scenario.conversation_criteria:
                conv_test_case = build_conversational_test_case(turns, responses, tools_per_turn)
                await evaluate_behavioral(conv_test_case, scenario.conversation_criteria, guardian_agent, verbose_logger)

            if any(turn.expected_args for turn in scenario.template_turns):
                pretty_print_chat_history(chat_history, llm_config["name"], verbose_logger)

            if scenario.assert_no_memory_overflow:
                await assert_no_memory_overflow(test_agent)
                active_tokens = await test_agent.get_active_memory_token_estimate()
                verbose_logger.info(
                    "Active memory estimate: %d tokens (limit %d)",
                    active_tokens,
                    test_agent.token_limit,
                )

            verbose_logger.info(
                "✓ Guardian evaluation passed for %s/%s with prompt: %s",
                llm_config["name"],
                scenario.prompt_id,
                scenario.prompt,
            )

    _GeneratedLLMPromptTests.__name__ = class_name
    _GeneratedLLMPromptTests.__qualname__ = class_name
    return _GeneratedLLMPromptTests
