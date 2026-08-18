"""Generate parametrized pytest suites for MCP LLM evaluation scenarios."""

from __future__ import annotations

import logging

import pytest
from deepeval.models import GPTModel
from mcp_llm_eval.data import PromptRegistry, PromptTestScenario
from mcp_llm_eval.deepeval_support.judges import (
    build_test_case,
    evaluate_behavioral,
    evaluate_compliance,
    evaluate_tool_correctness,
)
from mcp_llm_eval.llama_index_support.agent_mcp import MCPAgentWrapper
from mcp_llm_eval.llm_prompt_support import (
    assert_at_least_one_expected_tool,
    assert_no_forbidden_tool,
    assert_no_memory_overflow,
    resolve_scenario_turns,
    run_scenario_turns,
)
from mcp_llm_eval.utils import load_llm_configurations, should_skip_llm_matrix_tests

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
            response, all_tools = await run_scenario_turns(test_agent, turns)

            verbose_logger.info("Expected: %s", scenario.expected_tools)
            verbose_logger.info("Forbidden: %s", scenario.forbidden_tools)

            assert response.strip(), f"empty assistant response for {llm_config['name']} on {scenario.prompt_id}"
            assert_at_least_one_expected_tool(all_tools, scenario.expected_tools)
            if scenario.forbidden_tools:
                assert_no_forbidden_tool(all_tools, scenario.forbidden_tools)

            test_case = build_test_case(scenario.prompt, response, all_tools, list(scenario.expected_tools))

            await evaluate_tool_correctness(test_case, guardian_agent, verbose_logger)

            if scenario.turn_criteria:
                await evaluate_compliance(test_case, scenario.turn_criteria, guardian_agent, verbose_logger)
            if scenario.conversation_criteria:
                await evaluate_behavioral(test_case, scenario.conversation_criteria, guardian_agent, verbose_logger)

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
