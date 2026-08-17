"""Shared helpers for per-toolset LLM prompt integration tests."""

from __future__ import annotations
import pytest
from mcp_llm_eval.data import PromptRegistry
from tests.utils import load_llm_configurations, should_skip_insights_llm_tests, should_skip_llm_matrix_tests
from mcp_llm_eval.llm_prompt_support import (
    resolve_scenario_turns,
    run_scenario_turns,
    assert_at_least_one_expected_tool,
)

_LLM_CONFIGURATIONS, _ = load_llm_configurations()


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
