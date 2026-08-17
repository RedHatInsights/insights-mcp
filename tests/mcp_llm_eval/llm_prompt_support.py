"""Shared helpers for per-toolset LLM prompt integration tests."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any
import pytest
from mcp_llm_eval.data import PromptTestScenario

if TYPE_CHECKING:
    from mcp_llm_eval.llama_index_support.agent_mcp import MCPAgentWrapper


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
