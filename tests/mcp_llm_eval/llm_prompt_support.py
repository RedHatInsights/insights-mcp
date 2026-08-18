"""Shared helpers for per-toolset LLM prompt integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from deepeval.test_case import ToolCall
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
) -> tuple[str, list[ToolCall]]:
    """Execute all turns and return the final response plus every tool call."""
    history: list[Any] = []
    response: str = ""
    all_tools: list[Any] = []

    for turn in turns:
        response, _, tools_executed, history = await agent.execute_with_reasoning(turn, chat_history=history)
        all_tools.extend(tools_executed)

    return response, all_tools


def _tool_names(tools: list[ToolCall]) -> set[str]:
    """Convert a list of ToolCalls to a set of their names."""
    return {tool.name for tool in tools}


def assert_at_least_one_expected_tool(tools_executed: list[ToolCall], expected_tools: tuple[str, ...]) -> None:
    """Assert at least one *expected_tools* name appears in *tools_executed*."""
    names = _tool_names(tools_executed)
    assert any(expected in names for expected in expected_tools), (
        f"expected at least one of {list(expected_tools)}, got tool calls: {sorted(names)}"
    )


def assert_no_forbidden_tool(tools_executed: list[ToolCall], forbidden_tools: tuple[str, ...]) -> None:
    """Assert no *forbidden_tools* name appears in *tools_executed*."""
    names = _tool_names(tools_executed)
    assert not any(expected in names for expected in forbidden_tools), (
        f"forbidden tools called: {sorted(names & set(forbidden_tools))}"
    )
