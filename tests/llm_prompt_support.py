"""Shared helpers for per-toolset LLM prompt integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from insights_mcp.test_prompts_data import PromptRegistry, PromptTestScenario
from tests.utils import load_llm_configurations, should_skip_insights_llm_tests, should_skip_llm_matrix_tests

if TYPE_CHECKING:
    from tests.llama_index_support.agent_mcp import MCPAgentWrapper

_LLM_CONFIGURATIONS, _ = load_llm_configurations()


def resolve_scenario_turns(scenario: PromptTestScenario, context: dict[str, str]) -> tuple[str, ...]:
    """Format scenario templates; skip the test when required API data is missing."""
    missing = scenario.required_keys - frozenset(context.keys())
    if missing:
        pytest.skip(f"no API data for {sorted(missing)!r} in this account")
    return scenario.format_turns(context)


async def run_scenario_turns(
    agent: MCPAgentWrapper,
    turns: tuple[str, ...],
) -> tuple[str, list[Any]]:
    """Execute all turns and return the final response plus every tool call."""
    history: list[Any] = []
    response: str = ""
    all_tools: list[Any] = []

    for turn in turns:
        response, _, tools_executed, history = await agent.execute_with_reasoning(turn, chat_history=history)
        all_tools.extend(tools_executed)

    return response, all_tools


def assert_at_least_one_expected_tool(tools_executed: list[Any], expected_tools: tuple[str, ...]) -> None:
    """Assert at least one *expected_tools* name appears in *tools_executed*."""
    actual_names = {getattr(tool, "name", str(tool)) for tool in tools_executed}
    if any(expected in actual_names for expected in expected_tools):
        return
    raise AssertionError(f"expected at least one of {list(expected_tools)!r}, got tool calls: {sorted(actual_names)!r}")


def create_llm_prompt_test_class(toolset: str, prompts: PromptRegistry, class_name: str) -> type:
    """Build a pytest class with one parametrized test per prompt in *prompts*."""
    scenarios = prompts.iter_test_scenarios(toolset)

    @pytest.mark.llm
    @pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No valid LLM configurations found")
    @pytest.mark.skipif(
        should_skip_insights_llm_tests(),
        reason="INSIGHTS_CLIENT_ID and INSIGHTS_CLIENT_SECRET (or LIGHTSPEED_* equivalents) required",
    )
    class _GeneratedLLMPromptTests:  # pylint: disable=too-few-public-methods
        """Parametrized LLM tests for one toolset prompt registry."""

        @pytest.mark.parametrize("llm_config", _LLM_CONFIGURATIONS, ids=[c["name"] for c in _LLM_CONFIGURATIONS])
        @pytest.mark.parametrize("scenario", scenarios, ids=lambda s: s.prompt_id)
        @pytest.mark.asyncio
        async def test_prompt_calls_expected_tool(
            self,
            test_agent,
            scenario,
            llm_api_context,
            llm_config,
            verbose_logger,
        ):  # pylint: disable=redefined-outer-name,unused-argument,too-many-arguments,too-many-positional-arguments
            turns = resolve_scenario_turns(scenario, llm_api_context.as_dict())
            response, all_tools = await run_scenario_turns(test_agent, turns)
            assert response.strip(), f"empty assistant response for {llm_config['name']} on {scenario.prompt_id}"
            assert_at_least_one_expected_tool(all_tools, scenario.expected_tools)
            verbose_logger.info(
                "✓ %s / %s: tools=%s",
                toolset,
                scenario.prompt_id,
                [getattr(tool, "name", str(tool)) for tool in all_tools],
            )

    _GeneratedLLMPromptTests.__name__ = class_name
    _GeneratedLLMPromptTests.__qualname__ = class_name
    return _GeneratedLLMPromptTests
