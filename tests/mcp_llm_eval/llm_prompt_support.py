"""Shared helpers for per-toolset LLM prompt integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from deepeval.test_case import ToolCall
from llama_index.core.base.llms.types import ChatMessage
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
) -> tuple[str, list[ToolCall], list[ChatMessage]]:
    """Execute all turns and return the final response plus every tool call."""
    history: list[ChatMessage] = []
    response: str = ""
    all_tools: list[ToolCall] = []

    for turn in turns:
        response, _, tools_executed, history = await agent.execute_with_reasoning(turn, chat_history=history)
        all_tools.extend(tools_executed)

    return response, all_tools, history


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


async def assert_no_memory_overflow(test_agent: MCPAgentWrapper) -> None:
    """Assert the agent's memory did not archive any messages (mcp_memory_token_limit)"""
    archived = await test_agent.get_archived_messages()
    assert archived == [], f"memory overflow: {len(archived)} message(s) archived, conversation exceeded token limit"


def assert_correct_tool_args(tools_executed: list[ToolCall], expected_args: dict[str, list[dict[str, Any]]]) -> None:
    """Assert each tool was called exactly N times with the expected arguments.

    Compares by order within each tool name. Only the specified keys are checked,
    so extra arguments are ignored. Only works with explicitly passed args, not server-side defaults.
    """
    executed_by_name: dict[str, list[dict[str, Any]]] = {}
    for tool in tools_executed:
        args = executed_by_name.get(tool.name, [])
        args.append(tool.input_parameters or {})
        executed_by_name[tool.name] = args

    for tool_name, args_ordered in expected_args.items():
        executed_args = executed_by_name[tool_name]
        assert len(executed_args) == len(args_ordered), (
            f"different number of the tool {tool_name} called, expected {args_ordered}, got {executed_args}"
        )
        for i, arg in enumerate(args_ordered):
            assert arg.items() <= executed_args[i].items(), (
                f"expected args for tool {tool_name} in {i + 1}. call aren't subset of the used args. "
                f"Expected: {arg}, got: {executed_args[i]}"
            )
