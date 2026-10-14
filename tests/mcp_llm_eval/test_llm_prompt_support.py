"""Unit tests for shared LLM prompt assertion helpers."""

from deepeval.test_case import ToolCall

from tests.mcp_llm_eval.data import PromptWithTools
from tests.mcp_llm_eval.llm_prompt_support import (
    assert_all_required_tools,
    assert_at_least_one_expected_tool,
)


def test_assert_all_required_tools_passes_when_all_present() -> None:
    tools = [
        ToolCall(name="advisor__get_rule_from_node_id", input_parameters={"node_id": 6464541}),
        ToolCall(name="advisor__get_hosts_hitting_a_rule", input_parameters={"rule_id": "rule|KEY"}),
    ]
    assert_all_required_tools(tools, ("advisor__get_rule_from_node_id",))


def test_assert_all_required_tools_fails_when_missing() -> None:
    tools = [ToolCall(name="advisor__get_active_rules", input_parameters={})]
    try:
        assert_all_required_tools(tools, ("advisor__get_rule_from_node_id",))
    except AssertionError as exc:
        assert "advisor__get_rule_from_node_id" in str(exc)
    else:
        raise AssertionError("expected AssertionError")


def test_assert_at_least_one_expected_tool_accepts_any_alternative() -> None:
    tools = [ToolCall(name="advisor__get_hosts_hitting_a_rule", input_parameters={})]
    assert_at_least_one_expected_tool(
        tools,
        ("advisor__get_hosts_hitting_a_rule", "advisor__get_active_rules"),
    )


def test_prompt_with_tools_accepts_expected_args_on_required_tools() -> None:
    PromptWithTools(
        prompt="lookup kb article",
        required_tools=("advisor__get_rule_from_node_id",),
        expected_tools=("advisor__get_active_rules",),
        expected_args={"advisor__get_rule_from_node_id": [{"node_id": 6464541}]},
    )
