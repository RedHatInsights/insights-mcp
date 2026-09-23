"""Generate parametrized pytest suites for MCP LLM evaluation scenarios."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pytest
from deepeval.models import OpenAIModel

from .data import PromptTestScenario, TestScenarioRegistry
from .deepeval_support.judges import (
    build_conversational_test_case,
    build_turn_test_case,
    evaluate_behavioral,
    evaluate_compliance,
    evaluate_tool_correctness,
)
from .llama_index_support.agent_mcp import MCPAgentWrapper
from .llm_prompt_support import (
    assert_all_required_tools,
    assert_at_least_one_expected_tool,
    assert_correct_tool_args,
    assert_no_forbidden_tool,
    assert_no_memory_overflow,
    resolve_scenario_prompts,
    run_scenario_turns,
)
from .utils import load_llm_configurations, pretty_print_chat_history, should_skip_llm_matrix_tests

_LLM_CONFIGURATIONS, _ = load_llm_configurations()


@dataclass(frozen=True)
class _LlmEvalFixtures:
    """Pytest-injected objects for one generated LLM prompt test."""

    test_agent: MCPAgentWrapper
    guardian_agent: OpenAIModel
    llm_api_context: dict[str, str]
    llm_config: dict[str, str]
    verbose_logger: logging.Logger


async def _evaluate_scenario_turns(
    scenario: PromptTestScenario,
    prompts: tuple[str, ...],
    responses: list[str],
    tools_per_turn: list[list[Any]],
    fixtures: _LlmEvalFixtures,
) -> None:
    """Assert tools and guardian metrics for each turn."""
    guardian = fixtures.guardian_agent
    logger = fixtures.verbose_logger
    llm_name = fixtures.llm_config["name"]
    for turn_idx, (request, executed_tools, turn, response) in enumerate(
        zip(prompts, tools_per_turn, scenario.turns, responses)
    ):
        assert response.strip(), f"empty assistant response for {llm_name} on {scenario.prompt_id}"
        logger.info("Turn %d - Required: %s", turn_idx + 1, turn.required_tools)
        logger.info("Turn %d - Expected: %s", turn_idx + 1, turn.expected_tools)
        logger.info("Turn %d - Forbidden: %s", turn_idx + 1, turn.forbidden_tools)
        if turn.required_tools:
            assert_all_required_tools(executed_tools, turn.required_tools)
        if turn.expected_tools:
            assert_at_least_one_expected_tool(executed_tools, turn.expected_tools)
        if turn.forbidden_tools:
            assert_no_forbidden_tool(executed_tools, turn.forbidden_tools)
        if turn.expected_args:
            assert_correct_tool_args(executed_tools, turn.expected_args)
        turn_test_case = build_turn_test_case(
            request,
            response,
            executed_tools,
            tuple(turn.required_tools) + tuple(turn.expected_tools),
        )
        if scenario.threshold > 0:
            await evaluate_tool_correctness(turn_test_case, guardian, logger, scenario.threshold)
        if turn.turn_criteria:
            await evaluate_compliance(turn_test_case, turn.turn_criteria, guardian, logger)


async def _run_llm_eval(scenario: PromptTestScenario, fixtures: _LlmEvalFixtures) -> None:
    """Execute one prompt scenario against the live MCP agent and guardian model."""
    agent = fixtures.test_agent
    logger = fixtures.verbose_logger
    llm_config = fixtures.llm_config
    prompts = resolve_scenario_prompts(scenario, fixtures.llm_api_context)
    responses, tools_per_turn, chat_history = await run_scenario_turns(agent, prompts)
    await _evaluate_scenario_turns(scenario, prompts, responses, tools_per_turn, fixtures)

    if scenario.conversation_criteria:
        conv_test_case = build_conversational_test_case(prompts, responses, tools_per_turn)
        await evaluate_behavioral(conv_test_case, scenario.conversation_criteria, fixtures.guardian_agent, logger)

    if any(turn.expected_args for turn in scenario.turns):
        pretty_print_chat_history(chat_history, llm_config["name"], logger)

    if scenario.assert_no_memory_overflow:
        await assert_no_memory_overflow(agent)
        active_tokens = await agent.get_active_memory_token_estimate()
        logger.info(
            "Active memory estimate: %d tokens (limit %d)",
            active_tokens,
            agent.token_limit,
        )

    logger.info(
        "✓ Guardian evaluation passed for %s/%s with prompt: %s",
        llm_config["name"],
        scenario.prompt_id,
        scenario.prompt,
    )


def create_test_suite(prompts: TestScenarioRegistry, class_name: str) -> type:
    """Build a pytest class with one parametrized test per prompt in *prompts*."""
    scenarios = prompts.iter_test_scenarios()

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
            guardian_agent: OpenAIModel,
            scenario: PromptTestScenario,
            llm_api_context: dict[str, str],
            llm_config: dict[str, str],
            verbose_logger: logging.Logger,
        ):  # pylint: disable=redefined-outer-name,too-many-arguments,too-many-positional-arguments
            """Run an LLM eval scenario, assert tool correctness and criteria."""
            await _run_llm_eval(
                scenario,
                _LlmEvalFixtures(
                    test_agent=test_agent,
                    guardian_agent=guardian_agent,
                    llm_api_context=llm_api_context,
                    llm_config=llm_config,
                    verbose_logger=verbose_logger,
                ),
            )

    _GeneratedLLMPromptTests.__name__ = class_name
    _GeneratedLLMPromptTests.__qualname__ = class_name
    return _GeneratedLLMPromptTests
